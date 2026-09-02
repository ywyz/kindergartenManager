"""Stable RED contracts for the R5-R deploy backup attestation seam.

These tests exercise the deploy consumer against the producer-owned SQLite
evidence format.  They intentionally keep imports of the producer inside
helpers so a missing provenance seam is reported as an ordinary test failure,
not a collection error.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import sqlite3
import zipfile
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts import deploy

IMAGE = "ghcr.io/ywyz/kindergartenmanager@sha256:" + "a" * 64
TEMPLATE_NAMES = (
    "teacherplan.docx",
    "ObservationRecord.docx",
    "OneOnOneListeningSmallSecond.docx",
    "homemadeteaching.docx",
    "coursereviewactivity.docx",
)


def _seed_sqlite(path: Path, *, revision: str = "r5-r-synthetic-1") -> None:
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        connection.executescript(
            """
            CREATE TABLE alembic_version (version_num VARCHAR(128) NOT NULL);
            CREATE TABLE synthetic_records (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                value TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO alembic_version(version_num) VALUES (?)", (revision,)
        )
        connection.execute(
            "INSERT INTO synthetic_records(tenant_id, value) VALUES (?, ?)",
            (17, "committed synthetic row"),
        )
    finally:
        connection.close()


def _make_assets(tmp_path: Path) -> dict[str, Path]:
    data_root = tmp_path / "inputs"
    exports_root = data_root / "exports"
    templates_root = data_root / "templates"
    exports_root.mkdir(parents=True)
    templates_root.mkdir(parents=True)

    secrets_file = data_root / ".kindergarten_secrets"
    secrets_file.write_bytes(b"synthetic-only-secret-material\n")
    secrets_file.chmod(0o600)

    export_file = exports_root / "synthetic-plan.docx"
    export_file.write_bytes(b"synthetic export")
    for index, name in enumerate(TEMPLATE_NAMES, start=1):
        (templates_root / name).write_bytes(f"template-{index}".encode("ascii"))

    return {
        "secrets_file": secrets_file,
        "exports_root": exports_root,
        "templates_root": templates_root,
    }


def _produce_sqlite_evidence(tmp_path: Path) -> Path:
    """Run the real producer so the consumer test cannot handwrite ``passed``."""
    from app.jobs.backup_restore import create_sqlite_backup_attestation

    database = tmp_path / "target.sqlite3"
    _seed_sqlite(database)
    assets = _make_assets(tmp_path)
    return create_sqlite_backup_attestation(
        source_database=database,
        backup_root=tmp_path / "backups",
        secrets_file=assets["secrets_file"],
        exports_root=assets["exports_root"],
        templates_root=assets["templates_root"],
        protected_image=IMAGE,
        now=datetime.now(UTC),
    )


def _write_handwritten_evidence(tmp_path: Path) -> Path:
    """Create consumer-shaped JSON over bytes that are not a producer archive."""
    artifact = tmp_path / "handwritten-artifact.bin"
    artifact.write_bytes(b"not-a-kindergarten-manager-backup-archive")
    artifact.chmod(0o600)

    created = datetime.now(UTC).replace(microsecond=0)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "verified",
        "created_at": created.isoformat().replace("+00:00", "Z"),
        "expires_at": (created + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "protected_image": IMAGE,
        "database_identity_sha256": "b" * 64,
        "database_revision": "r5-r-handwritten",
        "artifact": {
            "path": str(artifact),
            "size_bytes": artifact.stat().st_size,
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        },
        "checks": {
            "database_integrity": "passed",
            "isolated_restore": "passed",
            "required_assets": "passed",
        },
    }
    evidence = tmp_path / "handwritten-evidence.json"
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    evidence.chmod(0o600)
    return evidence


def _rewrite_manifest(
    evidence: Path,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    artifact = Path(payload["artifact"]["path"])
    with zipfile.ZipFile(artifact, mode="r") as source:
        members = [(info, source.read(info.filename)) for info in source.infolist()]

    manifest = json.loads(
        next(data for info, data in members if info.filename == "manifest.json")
    )
    mutate(manifest)
    rewritten_manifest = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    temporary = artifact.with_name(".sqlite-backup-v1.zip.tmp")
    with zipfile.ZipFile(temporary, mode="w") as target:
        for info, data in members:
            target.writestr(
                info,
                rewritten_manifest if info.filename == "manifest.json" else data,
            )
    temporary.chmod(0o600)
    temporary.replace(artifact)
    artifact.chmod(0o600)

    artifact_bytes = artifact.read_bytes()
    payload["artifact"]["size_bytes"] = len(artifact_bytes)
    payload["artifact"]["sha256"] = hashlib.sha256(artifact_bytes).hexdigest()
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    evidence.chmod(0o600)


def test_deploy_parser_rejects_removed_database_identity_option() -> None:
    with pytest.raises(SystemExit) as caught:
        deploy._build_parser().parse_args(
            [
                "--database-identity-sha256",
                "b" * 64,
                "--health-url",
                "https://manager.ywyz.tech/api/v1/health",
                "--readiness-url",
                "https://manager.ywyz.tech/api/v1/readiness",
                "deploy",
                IMAGE,
            ]
        )
    assert caught.value.code == 2


def test_verified_backup_gate_has_no_operator_database_identity_parameter() -> None:
    parameters = inspect.signature(deploy._require_verified_backup).parameters
    assert list(parameters) == ["evidence_path", "protected_image"]


def test_handwritten_passed_json_over_nonproducer_artifact_is_rejected(
    tmp_path: Path,
) -> None:
    evidence = _write_handwritten_evidence(tmp_path)

    with pytest.raises(deploy.DeployError) as caught:
        deploy._require_verified_backup(evidence, IMAGE)

    message = str(caught.value).casefold()
    assert any(
        marker in message
        for marker in ("invalid", "provenance", "manifest", "producer")
    ), message


def test_invalid_backup_fails_before_docker_or_state_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("services:\n  app:\n    image: example.invalid/app:latest\n")
    evidence = _write_handwritten_evidence(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(
        deploy,
        "_run_command",
        lambda *args, **kwargs: calls.append("docker"),
    )

    with pytest.raises(
        SystemExit,
        match="invalid|provenance|manifest|producer",
    ):
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                "--backup-evidence",
                str(evidence),
                "--protected-image",
                IMAGE,
                "--health-url",
                "https://manager.ywyz.tech/api/v1/health",
                "--readiness-url",
                "https://manager.ywyz.tech/api/v1/readiness",
                "deploy",
                IMAGE,
            ]
        )

    assert calls == []
    assert not (tmp_path / ".deploy").exists()


def test_artifact_manifest_identity_and_revision_must_match_evidence(
    tmp_path: Path,
) -> None:
    evidence = _produce_sqlite_evidence(tmp_path)

    def mismatch(manifest: dict[str, Any]) -> None:
        manifest["database"]["identity_sha256"] = "c" * 64
        manifest["database"]["revision"] = "r5-r-conflicting-revision"

    _rewrite_manifest(evidence, mismatch)
    with pytest.raises(deploy.DeployError) as caught:
        deploy._require_verified_backup(evidence, IMAGE)

    message = str(caught.value).casefold()
    assert any(
        marker in message
        for marker in ("invalid", "provenance", "manifest", "mismatch")
    ), message


def test_producer_generated_sqlite_evidence_passes_deploy_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = _produce_sqlite_evidence(tmp_path)
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        deploy,
        "configured_database_identity_sha256",
        lambda: payload["database_identity_sha256"],
    )
    monkeypatch.setattr(
        deploy,
        "read_configured_database_revision",
        lambda: payload["database_revision"],
    )
    deploy._require_verified_backup(evidence, IMAGE)


def test_deploy_gate_rejects_attestation_for_a_different_configured_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = _produce_sqlite_evidence(tmp_path)
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    monkeypatch.setattr(deploy, "configured_database_identity_sha256", lambda: "e" * 64)
    monkeypatch.setattr(
        deploy,
        "read_configured_database_revision",
        lambda: payload["database_revision"],
    )

    with pytest.raises(deploy.DeployError, match="provenance"):
        deploy._require_verified_backup(evidence, IMAGE)


def test_generated_attestation_provenance_verifier_is_explicit() -> None:
    from app.jobs import backup_restore

    verifier = getattr(backup_restore, "validate_generated_attestation", None)
    assert callable(verifier), (
        "backup producer must expose a manifest provenance verifier"
    )


def test_dry_run_reports_not_image_bound_without_live_inspect_or_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("services:\n  app:\n    image: example.invalid/app:latest\n")
    monkeypatch.setattr(
        deploy,
        "_require_verified_backup",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(deploy, "_validate_oci_index_ref", lambda *args, **kwargs: None)

    def forbidden_live_inspect(*args: object, **kwargs: object) -> None:
        raise AssertionError("dry-run must not inspect the live container")

    monkeypatch.setattr(deploy, "_snapshot_current_state", forbidden_live_inspect)

    result = deploy.main(
        [
            "--project-dir",
            str(tmp_path),
            "--dry-run",
            "--protected-image",
            IMAGE,
            "--health-url",
            "https://manager.ywyz.tech/api/v1/health",
            "--readiness-url",
            "https://manager.ywyz.tech/api/v1/readiness",
            "deploy",
            IMAGE,
        ]
    )
    assert result == 0
    output = capsys.readouterr().out
    proof = f"{output}\n{result}"
    assert "NOT_IMAGE_BOUND" in proof or "BLOCKED" in proof
    assert "actual image binding passed" not in proof.casefold()
    assert not (tmp_path / ".deploy").exists()
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert b"actual image binding passed" not in path.read_bytes().lower()


def test_non_dry_run_requires_exact_live_image_binding() -> None:
    with pytest.raises(deploy.DeployError, match="not bound"):
        deploy._require_live_image_binding(
            IMAGE, IMAGE.replace("a" * 64, "b" * 64), dry_run=False
        )

    deploy._require_live_image_binding(IMAGE, IMAGE, dry_run=False)


@pytest.mark.parametrize("command", ["deploy", "rollback", "migrate-legacy"])
def test_backup_evidence_is_rechecked_before_and_inside_deploy_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("services:\n  app:\n    image: example.invalid/app:latest\n")
    current_image = IMAGE
    previous_image = IMAGE.replace("a" * 64, "b" * 64)
    target_image = IMAGE.replace("a" * 64, "c" * 64)
    evidence_calls: list[bool] = []
    lock_held = False

    @contextmanager
    def fake_lock(*args: object, **kwargs: object):
        nonlocal lock_held
        lock_held = True
        try:
            yield
        finally:
            lock_held = False

    def fake_backup_gate(*args: object, **kwargs: object) -> None:
        evidence_calls.append(lock_held)

    monkeypatch.setattr(deploy, "_deploy_lock", fake_lock)
    monkeypatch.setattr(deploy, "_require_verified_backup", fake_backup_gate)
    monkeypatch.setattr(
        deploy, "_require_acceptance_runner", lambda path: tmp_path / "runner"
    )
    monkeypatch.setattr(
        deploy, "_run_login_and_business_acceptance", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(deploy, "_validate_oci_index_ref", lambda *a, **k: None)
    monkeypatch.setattr(
        deploy,
        "_snapshot_current_state",
        lambda *args, **kwargs: current_image,
    )
    monkeypatch.setattr(
        deploy,
        "_deploy_once",
        lambda *args, image_ref, **kwargs: image_ref,
    )

    args = [
        "--project-dir",
        str(tmp_path),
        "--protected-image",
        current_image,
        "--health-url",
        "https://manager.ywyz.tech/api/v1/health",
        "--readiness-url",
        "https://manager.ywyz.tech/api/v1/readiness",
    ]
    if command == "deploy":
        args += ["deploy", target_image]
    elif command == "rollback":
        deploy._ensure_file_permissions(tmp_path / ".deploy" / "state.json")
        deploy._update_service_state(
            tmp_path / ".deploy" / "state.json",
            "app",
            current_image=current_image,
            previous_image=previous_image,
        )
        args += ["rollback", previous_image]
    else:
        args += ["migrate-legacy", current_image, target_image]

    deploy.main(args)
    assert evidence_calls == [False, True]
