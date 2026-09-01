"""Stable RED contract for the SQLite backup/restore evidence producer.

The public seam exercised here deliberately does not exist until the R5-R
backup producer is implemented.  Keeping imports inside each test makes the
file collection-clean while every RED failure points at that missing seam.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import os
import sqlite3
import stat
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

ALEMBIC_HEAD = "2b7f3d5e9c8a"
PROTECTED_IMAGE = "ghcr.io/ywyz/kindergartenmanager@sha256:" + "a" * 64
NOW = datetime(2026, 9, 1, 4, 0, tzinfo=UTC)
TEMPLATE_NAMES = (
    "teacherplan.docx",
    "ObservationRecord.docx",
    "OneOnOneListeningSmallSecond.docx",
    "homemadeteaching.docx",
    "coursereviewactivity.docx",
)


def _backup_restore_module():
    """Load the not-yet-implemented public backup/restore module at test time."""
    return importlib.import_module("app.jobs.backup_restore")


def _seed_sqlite(path: Path, *, revision: str = ALEMBIC_HEAD) -> sqlite3.Connection:
    """Create a tiny WAL database with a revision and one committed row."""
    connection = sqlite3.connect(path, isolation_level=None)
    connection.execute("PRAGMA journal_mode=WAL")
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
        (17, "committed"),
    )
    return connection


def _make_assets(tmp_path: Path) -> dict[str, Path]:
    """Build the required synthetic secrets/export/template input tree."""
    secrets_file = tmp_path / "data" / ".kindergarten_secrets"
    exports_root = tmp_path / "data" / "exports"
    templates_root = tmp_path / "data" / "templates"
    exports_root.mkdir(parents=True)
    templates_root.mkdir(parents=True)
    secrets_file.write_bytes(
        b"ENCRYPTION_KEY=synthetic-only\nJWT_SECRET=synthetic-jwt\n"
    )
    secrets_file.chmod(0o600)

    export_file = exports_root / "synthetic-plan.docx"
    export_file.write_bytes(b"synthetic export; no real child data")
    for index, name in enumerate(TEMPLATE_NAMES, start=1):
        (templates_root / name).write_bytes(f"template-{index}".encode("ascii"))

    # These files model the lock/cache debris that must never enter a backup.
    (templates_root / ".~lock.ObservationRecord.docx#").write_bytes(b"office lock")
    cache_root = exports_root / ".cache"
    cache_root.mkdir()
    (cache_root / "transient.bin").write_bytes(b"cache")
    return {
        "secrets_file": secrets_file,
        "exports_root": exports_root,
        "templates_root": templates_root,
        "export_file": export_file,
    }


def _expected_sqlite_identity(database: Path) -> str:
    """Mirror the credential-free identity normalization in startup.py."""
    normalized = f"sqlite:///{database.resolve().as_posix()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _create_evidence(
    database: Path,
    backup_root: Path,
    assets: dict[str, Path],
    *,
    now: datetime = NOW,
) -> Path:
    """Call the intentionally narrow producer API frozen by this test module."""
    module = _backup_restore_module()
    result = module.create_sqlite_backup_attestation(
        source_database=database,
        backup_root=backup_root,
        secrets_file=assets["secrets_file"],
        exports_root=assets["exports_root"],
        templates_root=assets["templates_root"],
        protected_image=PROTECTED_IMAGE,
        now=now,
    )
    assert isinstance(result, Path), "producer must return the generated evidence Path"
    return result


def _read_evidence(evidence: Path) -> tuple[dict[str, Any], Path]:
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    artifact = Path(payload["artifact"]["path"])
    return payload, artifact


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_sqlite_online_backup_is_a_consistent_committed_snapshot(
    tmp_path: Path,
) -> None:
    """An open transaction is excluded while committed rows survive restore."""
    database = tmp_path / "source.sqlite3"
    connection = _seed_sqlite(database)
    writer = sqlite3.connect(database, isolation_level=None)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("BEGIN")
    writer.execute(
        "INSERT INTO synthetic_records(tenant_id, value) VALUES (?, ?)",
        (17, "must-not-be-in-snapshot"),
    )
    assets = _make_assets(tmp_path)
    backup_root = tmp_path / "backups"

    try:
        evidence = _create_evidence(database, backup_root, assets)
    finally:
        writer.rollback()
        writer.close()
        connection.close()

    payload, artifact = _read_evidence(evidence)
    assert payload["status"] == "verified"
    assert payload["database_identity_sha256"] == _expected_sqlite_identity(database)
    assert payload["database_revision"] == ALEMBIC_HEAD
    assert payload["checks"] == {
        "database_integrity": "passed",
        "isolated_restore": "passed",
        "required_assets": "passed",
    }

    with zipfile.ZipFile(artifact) as archive:
        assert "database.sqlite3" in archive.namelist()
        assert not any(
            name.endswith(("-wal", "-shm", "-journal")) for name in archive.namelist()
        )

    restore_root = tmp_path / "isolated-restore"
    _backup_restore_module().restore_backup_artifact(artifact, restore_root)
    restored_database = restore_root / "database.sqlite3"
    with sqlite3.connect(restored_database) as restored:
        assert restored.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert restored.execute(
            "SELECT COUNT(*) FROM synthetic_records"
        ).fetchone() == (1,)
        assert restored.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (ALEMBIC_HEAD,)


def test_generated_evidence_is_accepted_and_binds_actual_identity_and_revision(
    tmp_path: Path,
) -> None:
    """The existing consumer accepts only the program-produced target facts."""
    database = tmp_path / "actual-target.sqlite3"
    connection = _seed_sqlite(database, revision="synthetic-revision-42")
    connection.close()
    assets = _make_assets(tmp_path)
    evidence = _create_evidence(database, tmp_path / "backups", assets)
    payload, _ = _read_evidence(evidence)

    from app.core.backup_evidence import validate_backup_evidence

    verified = validate_backup_evidence(
        evidence,
        expected_protected_image=PROTECTED_IMAGE,
        expected_database_identity_sha256=_expected_sqlite_identity(database),
        now=NOW + timedelta(minutes=30),
    )
    assert verified.database_identity_sha256 == _expected_sqlite_identity(database)
    assert verified.database_revision == "synthetic-revision-42"
    assert payload["database_revision"] == "synthetic-revision-42"


def test_sqlite_identity_changes_with_the_actual_target_path(tmp_path: Path) -> None:
    """Identical contents at different paths cannot share a target identity."""
    first = tmp_path / "first.sqlite3"
    second = tmp_path / "second.sqlite3"
    first_connection = _seed_sqlite(first)
    first_connection.close()
    second_connection = _seed_sqlite(second)
    second_connection.close()
    assets = _make_assets(tmp_path)

    first_payload, _ = _read_evidence(
        _create_evidence(first, tmp_path / "backups-first", assets)
    )
    second_payload, _ = _read_evidence(
        _create_evidence(second, tmp_path / "backups-second", assets)
    )

    assert first_payload["database_identity_sha256"] == _expected_sqlite_identity(first)
    assert second_payload["database_identity_sha256"] == _expected_sqlite_identity(
        second
    )
    assert (
        first_payload["database_identity_sha256"]
        != second_payload["database_identity_sha256"]
    )


def test_manifest_checksums_required_assets_and_excludes_locks_and_caches(
    tmp_path: Path,
) -> None:
    """All required files are checksummed; Office locks and transient caches are absent."""
    database = tmp_path / "source.sqlite3"
    connection = _seed_sqlite(database)
    connection.close()
    assets = _make_assets(tmp_path)
    evidence = _create_evidence(database, tmp_path / "backups", assets)
    payload, artifact = _read_evidence(evidence)

    with zipfile.ZipFile(artifact) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        assert names == {
            "manifest.json",
            "database.sqlite3",
            "secrets/.kindergarten_secrets",
            "exports/synthetic-plan.docx",
            *(f"templates/{name}" for name in TEMPLATE_NAMES),
        }

    assert (
        manifest["database"]["identity_sha256"] == payload["database_identity_sha256"]
    )
    assert manifest["database"]["revision"] == ALEMBIC_HEAD
    indexed_assets = {entry["path"]: entry for entry in manifest["assets"]}
    for archive_name, source in {
        "secrets/.kindergarten_secrets": assets["secrets_file"],
        "exports/synthetic-plan.docx": assets["export_file"],
        **{
            f"templates/{name}": assets["templates_root"] / name
            for name in TEMPLATE_NAMES
        },
    }.items():
        assert indexed_assets[archive_name]["size_bytes"] == source.stat().st_size
        assert (
            indexed_assets[archive_name]["sha256"]
            == hashlib.sha256(source.read_bytes()).hexdigest()
        )
    assert not any(
        "lock" in path.lower() or ".cache" in path for path in indexed_assets
    )


def test_secrets_restore_exactly_but_never_appear_in_evidence_json(
    tmp_path: Path,
) -> None:
    """The restore set carries synthetic secrets while the attestation stays redacted."""
    database = tmp_path / "source.sqlite3"
    connection = _seed_sqlite(database)
    connection.close()
    assets = _make_assets(tmp_path)
    secret_bytes = assets["secrets_file"].read_bytes()
    evidence = _create_evidence(database, tmp_path / "backups", assets)
    payload, artifact = _read_evidence(evidence)

    evidence_bytes = evidence.read_bytes()
    assert secret_bytes not in evidence_bytes
    assert b"synthetic-only" not in evidence_bytes
    assert "api_key_encrypted" not in evidence.read_text(encoding="utf-8")
    assert payload["checks"]["required_assets"] == "passed"

    restore_root = tmp_path / "isolated-restore"
    _backup_restore_module().restore_backup_artifact(artifact, restore_root)
    restored_secret = restore_root / "secrets" / ".kindergarten_secrets"
    assert restored_secret.read_bytes() == secret_bytes


def test_backup_restore_permissions_are_owner_only(tmp_path: Path) -> None:
    """The backup root/run directory are 0700; archive/evidence/files are 0600."""
    database = tmp_path / "source.sqlite3"
    connection = _seed_sqlite(database)
    connection.close()
    assets = _make_assets(tmp_path)
    backup_root = tmp_path / "backups"
    evidence = _create_evidence(database, backup_root, assets)
    _, artifact = _read_evidence(evidence)

    assert _mode(backup_root) == 0o700
    assert _mode(evidence.parent) == 0o700
    assert _mode(evidence) == 0o600
    assert _mode(artifact) == 0o600

    restore_root = tmp_path / "isolated-restore"
    _backup_restore_module().restore_backup_artifact(artifact, restore_root)
    assert _mode(restore_root) == 0o700
    assert _mode(restore_root / "database.sqlite3") == 0o600
    assert _mode(restore_root / "secrets" / ".kindergarten_secrets") == 0o600


def test_failed_production_leaves_no_partial_artifact_or_evidence(
    tmp_path: Path,
) -> None:
    """A failed input validation removes the random run directory completely."""
    database = tmp_path / "source.sqlite3"
    connection = _seed_sqlite(database)
    connection.close()
    assets = _make_assets(tmp_path)
    missing_template = assets["templates_root"] / "teacherplan.docx"
    missing_template.unlink()
    backup_root = tmp_path / "backups"
    module = _backup_restore_module()

    with pytest.raises(module.BackupRestoreError):
        module.create_sqlite_backup_attestation(
            source_database=database,
            backup_root=backup_root,
            secrets_file=assets["secrets_file"],
            exports_root=assets["exports_root"],
            templates_root=assets["templates_root"],
            protected_image=PROTECTED_IMAGE,
            now=NOW,
        )

    assert backup_root.exists()
    assert _mode(backup_root) == 0o700
    assert list(backup_root.iterdir()) == []


def test_tampered_artifact_is_rejected_by_consumer_and_restore(tmp_path: Path) -> None:
    """Changing the artifact invalidates both evidence consumption and restore."""
    database = tmp_path / "source.sqlite3"
    connection = _seed_sqlite(database)
    connection.close()
    assets = _make_assets(tmp_path)
    evidence = _create_evidence(database, tmp_path / "backups", assets)
    payload, artifact = _read_evidence(evidence)
    artifact.write_bytes(b"tampered-not-a-backup")
    artifact.chmod(0o600)

    from app.core.backup_evidence import BackupEvidenceError, validate_backup_evidence

    with pytest.raises(BackupEvidenceError, match="checksum|size"):
        validate_backup_evidence(
            evidence,
            expected_protected_image=PROTECTED_IMAGE,
            expected_database_identity_sha256=_expected_sqlite_identity(database),
            now=NOW + timedelta(minutes=30),
        )
    with pytest.raises(_backup_restore_module().BackupRestoreError):
        _backup_restore_module().restore_backup_artifact(artifact, tmp_path / "restore")
    assert not (tmp_path / "restore" / "database.sqlite3").exists()
    assert (
        payload["artifact"]["sha256"]
        != hashlib.sha256(artifact.read_bytes()).hexdigest()
    )


def test_producer_does_not_accept_handwritten_status_checks_or_database_facts(
    tmp_path: Path,
) -> None:
    """The producer derives status/checks/identity/revision and has no open kwargs."""
    module = _backup_restore_module()
    signature = inspect.signature(module.create_sqlite_backup_attestation)
    parameter_names = set(signature.parameters)
    assert not parameter_names.intersection(
        {
            "passed",
            "status",
            "checks",
            "database_identity_sha256",
            "database_revision",
        }
    )
    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )

    database = tmp_path / "source.sqlite3"
    connection = _seed_sqlite(database)
    connection.close()
    assets = _make_assets(tmp_path)
    with pytest.raises(TypeError):
        module.create_sqlite_backup_attestation(
            source_database=database,
            backup_root=tmp_path / "backups",
            secrets_file=assets["secrets_file"],
            exports_root=assets["exports_root"],
            templates_root=assets["templates_root"],
            protected_image=PROTECTED_IMAGE,
            now=NOW,
            checks={"database_integrity": "passed"},
        )


def test_restore_isolated_and_repeatable_without_mutating_source(
    tmp_path: Path,
) -> None:
    """Two fresh restores are independent and leave the source database unchanged."""
    database = tmp_path / "source.sqlite3"
    connection = _seed_sqlite(database)
    connection.close()
    source_digest_before = hashlib.sha256(database.read_bytes()).hexdigest()
    assets = _make_assets(tmp_path)
    _, artifact = _read_evidence(
        _create_evidence(database, tmp_path / "backups", assets)
    )

    first_root = tmp_path / "restore-one"
    second_root = tmp_path / "restore-two"
    module = _backup_restore_module()
    module.restore_backup_artifact(artifact, first_root)
    module.restore_backup_artifact(artifact, second_root)

    assert hashlib.sha256(database.read_bytes()).hexdigest() == source_digest_before
    assert not os.path.samefile(database, first_root / "database.sqlite3")
    assert not os.path.samefile(database, second_root / "database.sqlite3")
    for restored_root in (first_root, second_root):
        with sqlite3.connect(restored_root / "database.sqlite3") as restored:
            assert restored.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert restored.execute(
                "SELECT COUNT(*) FROM synthetic_records"
            ).fetchone() == (1,)


def test_restore_rejects_archive_path_traversal_without_escape_or_partial_files(
    tmp_path: Path,
) -> None:
    """Archive extraction must stay in its fresh destination directory."""
    database = tmp_path / "source.sqlite3"
    connection = _seed_sqlite(database)
    connection.close()
    assets = _make_assets(tmp_path)
    _, artifact = _read_evidence(
        _create_evidence(database, tmp_path / "backups", assets)
    )
    malicious = tmp_path / "malicious.zip"
    with zipfile.ZipFile(artifact) as source, zipfile.ZipFile(malicious, "w") as target:
        for info in source.infolist():
            target.writestr(info, source.read(info.filename))
        target.writestr("../escaped.txt", b"must not escape")
    malicious.chmod(0o600)

    restore_root = tmp_path / "isolated-restore"
    module = _backup_restore_module()
    with pytest.raises(module.BackupRestoreError):
        module.restore_backup_artifact(malicious, restore_root)

    assert not (tmp_path / "escaped.txt").exists()
    assert not restore_root.exists() or list(restore_root.iterdir()) == []
