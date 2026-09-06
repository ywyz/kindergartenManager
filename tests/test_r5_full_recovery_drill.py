"""Stable RED contract for the complete local R5-R recovery rehearsal.

The rehearsal itself is intentionally a script seam: it owns synthetic data
creation, the existing backup producer, corruption simulation, isolated
restore, and application-level checks.  This test only consumes its report
and independently checks the persisted artifacts, so a hand-written
``passed`` JSON cannot satisfy the contract.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import sqlite3
import stat
from pathlib import Path
from typing import Any

import pytest
from docx import Document

PROTECTED_IMAGE = "ghcr.io/ywyz/kindergartenmanager@sha256:" + "a" * 64
SYNTHETIC_LOGIN_PASSWORD = "R5-R-local-login-2026!"
SYNTHETIC_AI_KEY = "sk-r5-r-local-synthetic-no-network"
MODULE_TABLES = (
    "daily_plan",
    "game_observation",
    "listening_record",
    "homemade_teaching_toy",
    "course_review_activity",
)
IMAGE_TABLES = ("game_observation_image", "listening_image")


def _drill_module():
    """Load the not-yet-implemented full recovery drill seam."""
    return importlib.import_module("scripts.r5_recovery_drill")


def _report_value(report: Any, key: str) -> Any:
    if isinstance(report, dict):
        return report[key]
    return getattr(report, key)


def _sqlite_snapshot(path: Path) -> dict[str, list[tuple[Any, ...]]]:
    """Return a deterministic, secret-safe snapshot of every user table."""

    def safe(value: Any) -> Any:
        if isinstance(value, bytes):
            return {
                "length": len(value),
                "sha256": hashlib.sha256(value).hexdigest(),
            }
        return value

    with sqlite3.connect(path) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            )
        ]
        result: dict[str, list[tuple[Any, ...]]] = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            rows = connection.execute(f"SELECT * FROM {quoted}").fetchall()
            result[table] = sorted(
                [tuple(safe(value) for value in row) for row in rows],
                key=repr,
            )
        return result


def test_complete_sqlite_recovery_rehearsal_is_zero_loss_and_application_ready(
    tmp_path: Path,
) -> None:
    """Corruption is simulated, then the producer archive proves full recovery."""
    report = _drill_module().run_full_recovery_drill(
        work_root=tmp_path / "r5-r-recovery",
        protected_image=PROTECTED_IMAGE,
        synthetic_login_password=SYNTHETIC_LOGIN_PASSWORD,
        synthetic_ai_key=SYNTHETIC_AI_KEY,
    )

    assert _report_value(report, "status") == "verified"
    assert _report_value(report, "environment") == "synthetic-local"
    checks = _report_value(report, "checks")
    assert checks == {
        "database_corruption": "passed",
        "asset_corruption": "passed",
        "isolated_restore": "passed",
        "readiness": "passed",
        "login": "passed",
        "module_records": "passed",
        "blob_images": "passed",
        "ai_key_decryption": "passed",
        "word_reexport": "passed",
        "zero_data_loss": "passed",
    }

    source_database = Path(_report_value(report, "source_database"))
    restore_root = Path(_report_value(report, "restore_root"))
    restored_database = restore_root / "database.sqlite3"
    artifact = Path(_report_value(report, "artifact_path"))
    evidence = Path(_report_value(report, "evidence_path"))
    assert source_database.is_absolute()
    assert restore_root.is_absolute()
    assert restored_database.is_file()
    assert artifact.is_file()
    assert evidence.is_file()
    assert source_database != restored_database
    assert source_database.parent != restore_root

    # The deploy-consumer validator must accept only the producer-generated
    # evidence and independently bind its manifest identity/revision.
    from app.jobs.backup_restore import validate_generated_attestation

    verified = validate_generated_attestation(
        evidence,
        expected_protected_image=PROTECTED_IMAGE,
    )
    assert verified.artifact_path == artifact.resolve()
    assert verified.database_revision == _report_value(report, "database_revision")

    module_counts = _report_value(report, "module_counts")
    assert set(module_counts) == set(MODULE_TABLES)
    assert all(module_counts[table] >= 1 for table in MODULE_TABLES)
    assert _report_value(report, "tenant_ids") == [17]

    blob_hashes = _report_value(report, "blob_sha256")
    assert set(blob_hashes) == set(IMAGE_TABLES)
    assert all(len(digest) == 64 for digest in blob_hashes.values())
    assert all(
        _report_value(report, "blob_counts")[table] >= 1 for table in IMAGE_TABLES
    )

    # The report carries only an opaque success marker for decryption.  The
    # cleartext AI key and login password must not appear in any evidence or
    # report serialization, while the restored DB still contains decryptable
    # ciphertext (the script performs the real repository decrypt check).
    serialized_report = json.dumps(report, default=str, ensure_ascii=False)
    assert SYNTHETIC_AI_KEY not in serialized_report
    assert SYNTHETIC_LOGIN_PASSWORD not in serialized_report
    evidence_bytes = evidence.read_bytes()
    assert SYNTHETIC_AI_KEY.encode() not in evidence_bytes
    assert SYNTHETIC_LOGIN_PASSWORD.encode() not in evidence_bytes
    assert b"api_key_encrypted" not in evidence_bytes

    word_exports = _report_value(report, "word_exports")
    assert set(word_exports) == set(MODULE_TABLES)
    for metadata in word_exports.values():
        output = Path(metadata["path"])
        assert output.is_file()
        assert output.read_bytes()[:2] == b"PK"
        Document(str(output))
        assert metadata["size_bytes"] == output.stat().st_size

    # Source is deliberately damaged by the rehearsal; all rows must instead
    # match the pre-corruption snapshot captured by the producer/report.
    assert _report_value(report, "source_corrupted") is True
    assert _report_value(report, "assets_corrupted") is True
    source_snapshot = _report_value(report, "source_snapshot")
    restored_snapshot = _sqlite_snapshot(restored_database)
    assert restored_snapshot == source_snapshot
    assert _sqlite_snapshot(source_database) != source_snapshot


def test_recovery_drill_rejects_non_producer_evidence_without_writing_restore(
    tmp_path: Path,
) -> None:
    """An invalid evidence path fails closed before any isolated restore output."""
    evidence = tmp_path / "handwritten-evidence.json"
    evidence.write_text('{"status":"verified"}', encoding="utf-8")
    restore_root = tmp_path / "restore"

    with pytest.raises(
        Exception,
        match="invalid|provenance|manifest|evidence|module|not found",
    ):
        _drill_module().run_full_recovery_drill(
            work_root=tmp_path / "r5-r-recovery",
            protected_image=PROTECTED_IMAGE,
            synthetic_login_password=SYNTHETIC_LOGIN_PASSWORD,
            synthetic_ai_key=SYNTHETIC_AI_KEY,
            evidence_path=evidence,
            restore_root=restore_root,
        )

    assert not restore_root.exists()


def test_recovery_ai_key_check_uses_the_restored_secrets(tmp_path: Path) -> None:
    module = _drill_module()
    report = module.run_full_recovery_drill(
        work_root=tmp_path / "r5-r-recovery",
        protected_image=PROTECTED_IMAGE,
        synthetic_login_password=SYNTHETIC_LOGIN_PASSWORD,
        synthetic_ai_key=SYNTHETIC_AI_KEY,
    )
    restore_root = Path(_report_value(report, "restore_root"))
    restored_secrets = restore_root / "secrets" / ".kindergarten_secrets"
    restored_secrets.write_text(
        "ENCRYPTION_KEY=wrong-restored-key\nJWT_SECRET=synthetic\n",
        encoding="utf-8",
    )
    restored_secrets.chmod(0o600)

    with pytest.raises(module.RecoveryDrillError, match="AI key|decrypt|crypto"):
        module._verify_ai_key(
            restore_root / "database.sqlite3",
            restored_secrets,
            SYNTHETIC_AI_KEY,
        )


def test_recovery_migration_environment_is_confined_to_work_root(
    tmp_path: Path,
) -> None:
    module = _drill_module()
    database = tmp_path / "source" / "kindergarten.db"
    environment = module._migration_environment(database, "synthetic-encryption")

    assert environment["KINDERGARTEN_DATA_DIR"] == str(database.parent.resolve())
    assert environment["DATABASE_URL"].endswith(database.as_posix())
    assert environment["ENCRYPTION_KEY"] == "synthetic-encryption"
    assert len(environment["JWT_SECRET"]) >= 32


def test_secure_write_creates_owner_only_file_without_following_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sensitive drill artifacts are private from the instant they exist."""
    module = _drill_module()
    target = tmp_path / "sensitive.bin"
    calls: list[tuple[int, int, int]] = []
    real_open = module.os.open

    def inspect_open(
        path: Path,
        flags: int,
        mode: int = 0o777,
        *args: Any,
        **kwargs: Any,
    ) -> int:
        descriptor = real_open(path, flags, mode, *args, **kwargs)
        calls.append((flags, mode, stat.S_IMODE(os.fstat(descriptor).st_mode)))
        return descriptor

    monkeypatch.setattr(module.os, "open", inspect_open)
    module._write_secure(target, b"synthetic-sensitive-payload")

    assert target.read_bytes() == b"synthetic-sensitive-payload"
    assert calls, "_write_secure must create through the low-level open API"
    flags, mode, creation_mode = calls[0]
    assert flags & os.O_CREAT
    assert flags & os.O_EXCL
    assert mode == 0o600
    if os.name == "posix":
        assert flags & os.O_NOFOLLOW
        assert creation_mode == 0o600


def test_secure_write_rejects_existing_file_and_symlink_without_modification(
    tmp_path: Path,
) -> None:
    """A secure-create helper must never overwrite or follow an existing entry."""
    module = _drill_module()
    target = tmp_path / "sensitive.bin"
    target.write_bytes(b"original")

    with pytest.raises(module.RecoveryDrillError, match="secure|Secure|create"):
        module._write_secure(target, b"replacement")
    assert target.read_bytes() == b"original"

    if os.name != "posix":
        return
    link_target = tmp_path / "link-target.bin"
    link_target.write_bytes(b"link-target")
    symlink = tmp_path / "sensitive-link.bin"
    symlink.symlink_to(link_target)

    with pytest.raises(module.RecoveryDrillError, match="secure|Secure|create"):
        module._write_secure(symlink, b"must-not-follow")
    assert symlink.is_symlink()
    assert link_target.read_bytes() == b"link-target"


def test_secure_write_removes_partial_file_after_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An interrupted write cannot leave a sensitive partial artifact behind."""
    module = _drill_module()
    target = tmp_path / "sensitive.bin"
    real_write = module.os.write
    write_count = 0

    def fail_after_partial_write(descriptor: int, payload: Any) -> int:
        nonlocal write_count
        write_count += 1
        if write_count == 1:
            return real_write(descriptor, payload[:4])
        raise OSError("injected write failure")

    monkeypatch.setattr(module.os, "write", fail_after_partial_write)
    with pytest.raises(module.RecoveryDrillError, match="secure|Secure|create"):
        module._write_secure(target, b"payload-that-must-not-remain")

    assert write_count >= 2
    assert not target.exists()
    assert not list(tmp_path.iterdir())


def test_secure_write_fails_closed_when_owner_only_creation_is_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Platforms without the proven POSIX primitive must not persist secrets."""
    module = _drill_module()
    target = tmp_path / "sensitive.bin"
    opened = False

    def unexpected_open(*_args: Any, **_kwargs: Any) -> int:
        nonlocal opened
        opened = True
        raise AssertionError("unsupported platforms must fail before opening")

    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setattr(module.os, "open", unexpected_open)

    with pytest.raises(module.RecoveryDrillError, match="unsupported"):
        module._write_secure(target, b"synthetic-sensitive-payload")

    assert opened is False
    assert not target.exists()


def test_secure_replace_is_private_and_rejects_symlinks(tmp_path: Path) -> None:
    """Atomic synthetic corruption keeps 0600 and never follows its target."""
    module = _drill_module()
    target = tmp_path / "asset.bin"
    target.write_bytes(b"original")
    module._replace_secure(target, b"replacement")
    assert target.read_bytes() == b"replacement"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert list(tmp_path.iterdir()) == [target]

    link_target = tmp_path / "link-target.bin"
    link_target.write_bytes(b"link-target")
    symlink = tmp_path / "asset-link.bin"
    symlink.symlink_to(link_target)
    with pytest.raises(module.RecoveryDrillError, match="cannot be corrupted"):
        module._replace_secure(symlink, b"must-not-follow")
    assert symlink.is_symlink()
    assert link_target.read_bytes() == b"link-target"


def test_secure_replace_cleans_temporary_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed atomic replace preserves the target and removes its temp file."""
    module = _drill_module()
    target = tmp_path / "asset.bin"
    target.write_bytes(b"original")

    def fail_replace(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr(module.os, "replace", fail_replace)
    with pytest.raises(module.RecoveryDrillError, match="replacement failed"):
        module._replace_secure(target, b"replacement")

    assert target.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [target]
