"""Stable RED for migration-to-deploy evidence continuity."""

from __future__ import annotations

import hashlib
import json
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest

OLD_IMAGE = "ghcr.io/ywyz/kindergartenmanager@sha256:" + "a" * 64
TARGET_IMAGE = "ghcr.io/ywyz/kindergartenmanager@sha256:" + "b" * 64
SOURCE_SHA = "c" * 40
IDENTITY = "d" * 64
BEFORE_REVISION = "before-revision"
AFTER_REVISION = "after-revision"


def test_migration_receipt_is_closed_owner_only_and_self_validating(
    tmp_path: Path,
) -> None:
    from app.core.migration_receipt import (
        create_migration_receipt,
        validate_migration_receipt,
    )

    evidence = tmp_path / "backup-evidence.json"
    evidence.write_text('{"synthetic":"evidence"}', encoding="utf-8")
    evidence.chmod(0o600)
    output = tmp_path / "migration-receipt.json"

    create_migration_receipt(
        output,
        evidence_path=evidence,
        backup_artifact_sha256="e" * 64,
        database_identity_sha256=IDENTITY,
        before_revision=BEFORE_REVISION,
        after_revision=AFTER_REVISION,
        protected_image=OLD_IMAGE,
        target_image=TARGET_IMAGE,
        source_sha=SOURCE_SHA,
        now=datetime(2026, 9, 1, 0, 0, tzinfo=UTC),
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert set(payload) == {
        "schema_version",
        "status",
        "created_at",
        "backup_evidence_sha256",
        "backup_artifact_sha256",
        "database_identity_sha256",
        "before_revision",
        "after_revision",
        "protected_image",
        "target_image",
        "source_sha",
    }
    assert (
        payload["backup_evidence_sha256"]
        == hashlib.sha256(evidence.read_bytes()).hexdigest()
    )
    assert stat.S_IMODE(output.stat().st_mode) == 0o600

    receipt = validate_migration_receipt(
        output,
        evidence_path=evidence,
        expected_protected_image=OLD_IMAGE,
        expected_target_image=TARGET_IMAGE,
        expected_source_sha=SOURCE_SHA,
        expected_database_identity_sha256=IDENTITY,
        expected_after_revision=AFTER_REVISION,
    )
    assert receipt.before_revision == BEFORE_REVISION
    assert receipt.after_revision == AFTER_REVISION


def test_migration_job_re_reads_database_and_writes_bound_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.jobs import migrate_database

    revisions = iter([BEFORE_REVISION, AFTER_REVISION])
    calls: list[str] = []
    evidence = type(
        "Evidence",
        (),
        {
            "database_revision": BEFORE_REVISION,
            "artifact_sha256": "e" * 64,
        },
    )()
    monkeypatch.setattr(
        migrate_database,
        "validate_backup_evidence",
        lambda *args, **kwargs: evidence,
    )
    monkeypatch.setattr(
        migrate_database, "configured_database_identity_sha256", lambda: IDENTITY
    )
    monkeypatch.setattr(
        migrate_database,
        "read_configured_database_revision",
        lambda: next(revisions),
    )
    monkeypatch.setattr(
        migrate_database, "run_migrations", lambda **kwargs: calls.append("upgrade")
    )
    monkeypatch.setattr(migrate_database, "get_migration_head", lambda: AFTER_REVISION)
    monkeypatch.setattr(
        migrate_database,
        "create_migration_receipt",
        lambda path, **kwargs: calls.append(
            "receipt:" + kwargs["before_revision"] + "->" + kwargs["after_revision"]
        ),
    )
    monkeypatch.setattr(
        migrate_database,
        "_validate_target_release",
        lambda *args, **kwargs: calls.append("release"),
    )

    assert (
        migrate_database.main(
            [
                "--backup-evidence",
                str(tmp_path / "backup-evidence.json"),
                "--protected-image",
                OLD_IMAGE,
                "--target-image",
                TARGET_IMAGE,
                "--source-sha",
                SOURCE_SHA,
                "--receipt-output",
                str(tmp_path / "migration-receipt.json"),
                "--release-descriptor",
                str(tmp_path / "docker-image.json"),
                "--release-repo",
                "ywyz/kindergartenManager",
                "--release-id",
                "123",
            ]
        )
        == 0
    )
    assert calls == [
        "release",
        "upgrade",
        f"receipt:{BEFORE_REVISION}->{AFTER_REVISION}",
    ]


def test_migration_job_rejects_target_tuple_before_alembic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.jobs import migrate_database

    evidence = type(
        "Evidence",
        (),
        {"database_revision": BEFORE_REVISION, "artifact_sha256": "e" * 64},
    )()
    monkeypatch.setattr(
        migrate_database, "validate_backup_evidence", lambda *args, **kwargs: evidence
    )
    monkeypatch.setattr(
        migrate_database, "configured_database_identity_sha256", lambda: IDENTITY
    )
    monkeypatch.setattr(
        migrate_database,
        "read_configured_database_revision",
        lambda: BEFORE_REVISION,
    )
    monkeypatch.setattr(migrate_database, "get_migration_head", lambda: AFTER_REVISION)
    monkeypatch.setattr(
        migrate_database,
        "_validate_target_release",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("bad tuple")),
    )
    monkeypatch.setattr(
        migrate_database,
        "run_migrations",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("Alembic must not run before release validation")
        ),
    )

    assert (
        migrate_database.main(
            [
                "--backup-evidence",
                str(tmp_path / "backup-evidence.json"),
                "--protected-image",
                OLD_IMAGE,
                "--target-image",
                TARGET_IMAGE,
                "--source-sha",
                SOURCE_SHA,
                "--receipt-output",
                str(tmp_path / "migration-receipt.json"),
                "--release-descriptor",
                str(tmp_path / "docker-image.json"),
                "--release-repo",
                "ywyz/kindergartenManager",
                "--release-id",
                "123",
            ]
        )
        == 1
    )


def test_migration_job_rejects_malformed_source_sha_before_alembic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.jobs import migrate_database

    evidence = type(
        "Evidence",
        (),
        {"database_revision": BEFORE_REVISION, "artifact_sha256": "e" * 64},
    )()
    monkeypatch.setattr(
        migrate_database, "validate_backup_evidence", lambda *args, **kwargs: evidence
    )
    monkeypatch.setattr(
        migrate_database, "configured_database_identity_sha256", lambda: IDENTITY
    )
    monkeypatch.setattr(
        migrate_database,
        "read_configured_database_revision",
        lambda: BEFORE_REVISION,
    )
    monkeypatch.setattr(migrate_database, "get_migration_head", lambda: AFTER_REVISION)
    monkeypatch.setattr(
        migrate_database,
        "run_migrations",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("Alembic must not run for malformed source SHA")
        ),
    )

    assert (
        migrate_database.main(
            [
                "--backup-evidence",
                str(tmp_path / "backup-evidence.json"),
                "--protected-image",
                OLD_IMAGE,
                "--target-image",
                TARGET_IMAGE,
                "--source-sha",
                "not-a-source-sha",
                "--receipt-output",
                str(tmp_path / "migration-receipt.json"),
                "--release-descriptor",
                str(tmp_path / "docker-image.json"),
                "--release-repo",
                "ywyz/kindergartenManager",
                "--release-id",
                "123",
            ]
        )
        == 1
    )


def test_isolation_candidate_requires_loopback_images_and_bound_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.jobs import migrate_database

    run_id = "synthetic-1234"
    monkeypatch.setattr(
        migrate_database.settings,
        "DATABASE_URL",
        "mysql+pymysql://user:pass@127.0.0.1/r5_p_synthetic_1234",
    )
    local_old = "localhost:5001/kg/old@sha256:" + "a" * 64
    local_target = "localhost:5001/kg/target@sha256:" + "b" * 64
    migrate_database._validate_isolation_scope(
        run_id=run_id,
        protected_image=local_old,
        target_image=local_target,
        release_tag=f"r5p-isolation-{run_id}",
    )

    with pytest.raises(Exception, match="Isolation database"):
        monkeypatch.setattr(
            migrate_database.settings,
            "DATABASE_URL",
            "mysql+pymysql://user:pass@production/r5_p_wrong",
        )
        migrate_database._validate_isolation_scope(
            run_id=run_id,
            protected_image=local_old,
            target_image=local_target,
            release_tag=f"r5p-isolation-{run_id}",
        )


def test_local_migration_source_mismatch_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.jobs import migrate_database

    results = iter(
        [
            type("Result", (), {"stdout": "e" * 40 + "\n"})(),
            type("Result", (), {"stdout": ""})(),
        ]
    )
    monkeypatch.setattr(
        migrate_database.subprocess, "run", lambda *args, **kwargs: next(results)
    )
    with pytest.raises(Exception, match="does not match source SHA"):
        migrate_database._validate_local_migration_source("d" * 40)


def test_deploy_accepts_pre_migration_evidence_only_with_matching_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import deploy

    verified = type(
        "Evidence",
        (),
        {
            "database_identity_sha256": IDENTITY,
            "database_revision": BEFORE_REVISION,
            "artifact_sha256": "e" * 64,
        },
    )()
    receipt = type(
        "Receipt",
        (),
        {
            "database_identity_sha256": IDENTITY,
            "before_revision": BEFORE_REVISION,
            "after_revision": AFTER_REVISION,
            "backup_artifact_sha256": "e" * 64,
        },
    )()
    monkeypatch.setattr(
        deploy, "validate_generated_attestation", lambda *args, **kwargs: verified
    )
    monkeypatch.setattr(
        deploy, "validate_migration_receipt", lambda *args, **kwargs: receipt
    )
    monkeypatch.setattr(deploy, "configured_database_identity_sha256", lambda: IDENTITY)
    monkeypatch.setattr(
        deploy, "read_configured_database_revision", lambda: AFTER_REVISION
    )

    deploy._require_post_migration_backup(
        tmp_path / "backup-evidence.json",
        OLD_IMAGE,
        tmp_path / "migration-receipt.json",
        TARGET_IMAGE,
        SOURCE_SHA,
    )


def test_post_migration_binding_mismatch_fails_before_docker_or_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import deploy

    monkeypatch.setattr(
        deploy,
        "_require_post_migration_backup",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            deploy.DeployError("migration receipt invalid")
        ),
    )
    monkeypatch.setattr(
        deploy,
        "_run_command",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Docker must not run")
        ),
    )
    monkeypatch.setattr(
        deploy,
        "_write_atomic_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("state must not be written")
        ),
    )

    with pytest.raises(SystemExit, match="migration receipt invalid"):
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                "--backup-evidence",
                str(tmp_path / "backup-evidence.json"),
                "--protected-image",
                OLD_IMAGE,
                "--migration-receipt",
                str(tmp_path / "migration-receipt.json"),
                "--source-sha",
                SOURCE_SHA,
                "--acceptance-runner",
                str(tmp_path / "acceptance-runner"),
                "--health-url",
                "https://manager.ywyz.tech/api/v1/health",
                "--readiness-url",
                "https://manager.ywyz.tech/api/v1/readiness",
                "deploy",
                TARGET_IMAGE,
            ]
        )


@pytest.mark.parametrize("command", ["rollback", "migrate-legacy"])
def test_non_deploy_commands_reject_post_migration_options(
    tmp_path: Path, command: str
) -> None:
    from scripts import deploy

    arguments = [
        "--project-dir",
        str(tmp_path),
        "--migration-receipt",
        str(tmp_path / "migration-receipt.json"),
        "--source-sha",
        SOURCE_SHA,
        "--acceptance-runner",
        str(tmp_path / "runner"),
        "--health-url",
        "https://manager.ywyz.tech/api/v1/health",
        "--readiness-url",
        "https://manager.ywyz.tech/api/v1/readiness",
        command,
    ]
    if command == "migrate-legacy":
        arguments.extend([OLD_IMAGE, TARGET_IMAGE])

    with pytest.raises(SystemExit, match="Post-migration deploy options"):
        deploy.main(arguments)
