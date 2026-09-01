"""The migration must be explicit and backup-gated."""

from pathlib import Path

import pytest


def test_application_main_has_no_migration_side_effect() -> None:
    source = Path("app/main.py").read_text(encoding="utf-8")
    assert "run_startup_migrations" not in source
    assert "command.upgrade" not in source


def test_bootstrap_admin_has_no_migration_side_effect() -> None:
    source = Path("app/jobs/bootstrap_admin.py").read_text(encoding="utf-8")
    assert "run_startup_migrations" not in source
    assert "command.upgrade" not in source


def test_explicit_migration_validates_backup_before_upgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.jobs import migrate_database

    calls: list[str] = []
    monkeypatch.setattr(
        migrate_database,
        "validate_backup_evidence",
        lambda path, *, expected_protected_image: calls.append("validate"),
    )
    monkeypatch.setattr(
        migrate_database,
        "run_migrations",
        lambda **kwargs: calls.append("upgrade"),
    )

    assert (
        migrate_database.main(
            [
                "--backup-evidence",
                str(tmp_path / "proof.json"),
                "--protected-image",
                "no-running-image",
            ]
        )
        == 0
    )
    assert calls == ["validate", "upgrade"]


def test_explicit_migration_invalid_evidence_never_calls_upgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.backup_evidence import BackupEvidenceError
    from app.jobs import migrate_database

    monkeypatch.setattr(
        migrate_database,
        "validate_backup_evidence",
        lambda *args, **kwargs: (_ for _ in ()).throw(BackupEvidenceError("bad")),
    )
    monkeypatch.setattr(
        migrate_database,
        "run_migrations",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not migrate")),
    )

    assert (
        migrate_database.main(
            [
                "--backup-evidence",
                str(tmp_path / "bad.json"),
                "--protected-image",
                "no-running-image",
            ]
        )
        == 1
    )
