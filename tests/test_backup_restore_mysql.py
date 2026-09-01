"""Stable RED contracts for the isolated MySQL R5-R backup drill.

The producer is intentionally not imported at collection time.  Until the
public ``scripts.r5_mysql_backup_restore`` seam exists, every contract test
therefore fails as an ordinary test failure (rather than making collection
error).  The static Compose contracts remain executable without Docker.

The frozen producer surface is deliberately narrow:

* ``compose_project_name`` and ``build_compose_command`` construct closed,
  project-scoped Docker Compose commands;
* ``build_mysqldump_args`` constructs a password-free, transaction-safe dump;
* ``mysql_identity_digest`` and the snapshot helpers derive facts from the
  actual target and normalized table rows; and
* ``create_mysql_backup_attestation`` owns backup -> fresh restore -> evidence
  production.  It must not accept caller supplied status, checks, identity,
  revision, or arbitrary ``**kwargs``.

The optional live test is intentionally gated by ``R5_MYSQL_LIVE=1``.  It is
not part of the stable RED run and, when enabled, is restricted to this
manifest and synthetic credentials supplied by the caller's environment.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).parents[1]
COMPOSE_FILE = ROOT / "specs" / "operations-r5" / "mysql-compose.yml"
ALEMBIC_HEAD = "2b7f3d5e9c8a"
IMAGE = "ghcr.io/ywyz/kindergartenmanager@sha256:" + "a" * 64
REQUIRED_DUMP_OPTIONS = {
    "--single-transaction",
    "--quick",
    "--skip-lock-tables",
    "--hex-blob",
    "--triggers",
    "--routines",
    "--events",
    "--set-gtid-purged=OFF",
    "--no-tablespaces",
}
TABLE_NAMES = {
    "alembic_version",
    "daily_plan",
    "game_observation",
    "listening_record",
}


def _mysql_module():
    """Load the public seam only while a contract test is running."""
    return importlib.import_module("scripts.r5_mysql_backup_restore")


def _manifest() -> dict[str, Any]:
    payload = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _assert_project_scoped_command(
    command: list[str] | tuple[str, ...],
    *,
    project: str,
    action: str,
) -> None:
    words = [str(item) for item in command]
    assert words[:2] == ["docker", "compose"]
    assert "--project-name" in words
    assert words[words.index("--project-name") + 1] == project
    assert "-f" in words
    assert words[words.index("-f") + 1] == str(COMPOSE_FILE)
    assert action in words
    assert "prune" not in words
    assert not any("docker-compose.yml" == word for word in words)


def test_mysql_compose_has_only_isolated_source_and_restore_services() -> None:
    """The drill manifest cannot accidentally start the production stack."""
    compose = _manifest()
    services = compose.get("services")
    assert isinstance(services, dict)
    assert set(services) == {"source", "restore"}
    assert not set(services) & {"app", "db", "caddy", "production"}

    networks = compose.get("networks")
    assert isinstance(networks, dict)
    assert set(networks) == {"source_net", "restore_net"}

    for role, service in services.items():
        assert isinstance(service, dict)
        assert service["image"] in {"mysql:8.4", "mysql:8.4.11"}
        assert service.get("ports") is None
        assert service.get("volumes") is None
        tmpfs = service.get("tmpfs")
        assert isinstance(tmpfs, list) and tmpfs
        assert any("/var/lib/mysql" in str(entry) for entry in tmpfs)
        assert service.get("networks") == [f"{role}_net"]
        assert set(service["networks"]) == {f"{role}_net"}

    # A named-volume declaration anywhere in this file would make cleanup
    # ambiguous and could accidentally point at production state.
    assert compose.get("volumes") is None


def test_mysql_compose_requires_external_synthetic_credentials_and_redacted_healthcheck() -> (
    None
):
    """Secrets are injected only by the caller; health checks never echo them."""
    compose = _manifest()
    for role, service in compose["services"].items():
        environment = service.get("environment")
        assert isinstance(environment, dict)
        expected_prefix = f"${{R5_MYSQL_{role.upper()}_"
        for key in (
            "MYSQL_ROOT_PASSWORD",
            "MYSQL_DATABASE",
            "MYSQL_USER",
            "MYSQL_PASSWORD",
        ):
            value = environment.get(key)
            assert isinstance(value, str)
            assert value.startswith(expected_prefix)
            assert ":?set R5_MYSQL_" in value

        healthcheck = service.get("healthcheck")
        assert isinstance(healthcheck, dict)
        test_command = healthcheck.get("test")
        assert isinstance(test_command, list)
        health_text = " ".join(str(part) for part in test_command)
        assert "mysqladmin ping" in health_text
        assert "MYSQL_PWD" in health_text
        assert "$${MYSQL_ROOT_PASSWORD}" in health_text
        assert "echo" not in health_text.casefold()
        assert "SELECT" not in health_text.upper()
        assert "password" not in health_text.casefold().replace(
            "mysql_root_password", ""
        )


def test_mysql_compose_uses_short_healthcheck_without_fixed_sleep() -> None:
    """Readiness uses healthcheck polling, never a shell sleep or long delay."""
    compose = _manifest()
    for service in compose["services"].values():
        healthcheck = service["healthcheck"]
        text = " ".join(str(part) for part in healthcheck["test"])
        assert "sleep" not in text.casefold()
        assert int(str(healthcheck["timeout"]).rstrip("s")) <= 10
        assert int(str(healthcheck["start_period"]).rstrip("s")) <= 60


def test_compose_project_names_are_unique_and_closed() -> None:
    module = _mysql_module()
    source = module.compose_project_name(role="source", run_id="run123")
    restore = module.compose_project_name(role="restore", run_id="run123")
    assert source != restore
    assert re.fullmatch(r"r5-r-[a-z0-9-]+-(source|restore)", source)
    assert re.fullmatch(r"r5-r-[a-z0-9-]+-(source|restore)", restore)
    assert "production" not in source.casefold()
    assert "production" not in restore.casefold()
    with pytest.raises(module.MySQLBackupRestoreError):
        module.compose_project_name(role="db", run_id="run123")


def test_compose_commands_are_project_scoped_and_use_only_drill_manifest() -> None:
    module = _mysql_module()
    project = "r5-r-contract-source"
    up = module.build_compose_command(
        compose_file=COMPOSE_FILE,
        project_name=project,
        action="up",
        service="source",
    )
    down = module.build_compose_command(
        compose_file=COMPOSE_FILE,
        project_name=project,
        action="down",
    )
    _assert_project_scoped_command(up, project=project, action="up")
    _assert_project_scoped_command(down, project=project, action="down")
    assert "source" in [str(item) for item in up]
    assert "--volumes" in [str(item) for item in down]
    assert "--remove-orphans" in [str(item) for item in down]
    assert "--all" not in [str(item) for item in down]


def test_arbitrary_same_named_compose_manifest_is_rejected(tmp_path: Path) -> None:
    module = _mysql_module()
    impostor = tmp_path / "mysql-compose.yml"
    impostor.write_text("services:\n  production:\n    image: mysql:8\n")

    with pytest.raises(module.MySQLBackupRestoreError, match="isolated|manifest"):
        module.build_compose_command(
            compose_file=impostor,
            project_name="r5-r-impostor-source",
            action="up",
            service="source",
        )


def test_cleanup_command_is_exact_project_scoped_and_never_prunes() -> None:
    module = _mysql_module()
    project = "r5-r-contract-restore"
    command = module.build_cleanup_command(
        compose_file=COMPOSE_FILE,
        project_name=project,
    )
    _assert_project_scoped_command(command, project=project, action="down")
    words = [str(item) for item in command]
    assert "--volumes" in words
    assert "--remove-orphans" in words
    assert "system" not in words
    assert "volume" not in words
    assert "prune" not in words


def test_mysqldump_args_have_all_consistency_and_binary_safe_options() -> None:
    module = _mysql_module()
    args = module.build_mysqldump_args(
        host="source",
        port=3306,
        database="synthetic_db",
        user="synthetic_app",
        output_path=Path("/run/r5/dump.sql.zst"),
    )
    words = [str(item) for item in args]
    assert words[0] == "mysqldump"
    assert REQUIRED_DUMP_OPTIONS <= set(words)
    assert {"--host=source", "--port=3306", "--user=synthetic_app"} <= set(words)
    assert "synthetic_db" in words
    assert any(word.endswith("dump.sql.zst") for word in words)
    assert not any(
        word == "--password" or word.startswith("--password=") for word in words
    )
    assert not any(word == "-p" or word.startswith("-p") for word in words[1:])
    assert all("MYSQL_PWD" not in word for word in words)


def test_mysqldump_builder_does_not_accept_a_password_or_open_kwargs() -> None:
    module = _mysql_module()
    signature = inspect.signature(module.build_mysqldump_args)
    assert not {
        "password",
        "mysql_password",
        "root_password",
        "password_file",
    }.intersection(signature.parameters)
    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def test_mysql_identity_strips_credentials_and_query_but_binds_location() -> None:
    module = _mysql_module()
    first = module.mysql_identity_digest(
        "mysql+aiomysql://app:first-secret@source.example:3306/synthetic_db"
        "?charset=utf8mb4&connect_timeout=3"
    )
    same_target = module.mysql_identity_digest(
        "mysql+aiomysql://other:second-secret@source.example:3306/synthetic_db?ssl=true"
    )
    different_host = module.mysql_identity_digest(
        "mysql+aiomysql://app:first-secret@other.example:3306/synthetic_db"
    )
    different_port = module.mysql_identity_digest(
        "mysql+aiomysql://app:first-secret@source.example:3307/synthetic_db"
    )
    different_database = module.mysql_identity_digest(
        "mysql+aiomysql://app:first-secret@source.example:3306/other_db"
    )
    assert first == same_target
    assert first not in {different_host, different_port, different_database}
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert all(secret not in first for secret in ("first-secret", "second-secret"))


def test_mysql_identity_builder_has_no_password_or_query_parameter_inputs() -> None:
    module = _mysql_module()
    signature = inspect.signature(module.mysql_identity_digest)
    assert not {
        "password",
        "query",
        "username",
        "database_identity_sha256",
    }.intersection(signature.parameters)
    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def test_mysql_producer_identity_matches_migration_job_identity() -> None:
    module = _mysql_module()
    from app.core.startup import database_identity_sha256

    database_url = (
        "mysql+aiomysql://app:secret@source.example:3306/synthetic_db"
        "?charset=utf8mb4"
    )

    assert module.mysql_identity_digest(database_url) == database_identity_sha256(
        database_url
    )


def test_innodb_preflight_accepts_real_engines_and_rejects_non_innodb() -> None:
    module = _mysql_module()
    engines = {
        "alembic_version": "InnoDB",
        "daily_plan": "InnoDB",
        "game_observation": "InnoDB",
        "listening_record": "InnoDB",
    }
    assert module.validate_innodb_tables(engines) is None
    broken = dict(engines)
    broken["game_observation"] = "MyISAM"
    with pytest.raises(module.MySQLBackupRestoreError, match="InnoDB"):
        module.validate_innodb_tables(broken)


def test_restore_target_must_be_absent_and_fresh(tmp_path: Path) -> None:
    module = _mysql_module()
    fresh = tmp_path / "new-restore"
    assert module.validate_fresh_restore_target(fresh) == fresh

    fresh.mkdir()
    with pytest.raises(module.MySQLBackupRestoreError, match="fresh|empty|new"):
        module.validate_fresh_restore_target(fresh)

    existing_file = tmp_path / "existing-file"
    existing_file.write_bytes(b"not a restore")
    with pytest.raises(module.MySQLBackupRestoreError, match="fresh|empty|new"):
        module.validate_fresh_restore_target(existing_file)


def test_normalized_snapshot_is_ordered_and_replaces_blob_bytes_with_sha256() -> None:
    module = _mysql_module()
    rows = {
        "z_records": [
            {
                "tenant_id": 17,
                "id": 2,
                "blob_content": b"second-image",
                "value": "b",
            },
            {
                "tenant_id": 17,
                "id": 1,
                "blob_content": b"first-image",
                "value": "a",
            },
        ],
        "a_records": [{"tenant_id": 18, "id": 3, "blob_content": None, "value": "c"}],
    }
    normalized = module.normalize_mysql_snapshot(rows)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    assert list(normalized["tables"]) == ["a_records", "z_records"]
    assert normalized["table_counts"] == {"a_records": 1, "z_records": 2}
    assert "second-image" not in encoded
    assert hashlib.sha256(b"second-image").hexdigest() in encoded
    assert hashlib.sha256(b"first-image").hexdigest() in encoded
    assert "blob_content_sha256" in encoded
    assert "tenant_id" in encoded
    assert "blob_content" not in normalized["tables"]["z_records"][0]


def test_snapshot_comparison_binds_all_tables_revision_blobs_and_tenants() -> None:
    module = _mysql_module()
    source = module.normalize_mysql_snapshot(
        {
            "alembic_version": [{"version_num": ALEMBIC_HEAD}],
            "records": [
                {"id": 1, "tenant_id": 17, "blob": b"image-a", "value": "ok"},
                {"id": 2, "tenant_id": 18, "blob": None, "value": "other"},
            ],
        }
    )
    restored = module.normalize_mysql_snapshot(
        {
            "records": [
                {"value": "other", "blob": None, "tenant_id": 18, "id": 2},
                {"blob": b"image-a", "id": 1, "value": "ok", "tenant_id": 17},
            ],
            "alembic_version": [{"version_num": ALEMBIC_HEAD}],
        }
    )
    assert (
        module.compare_mysql_snapshots(
            source,
            restored,
            expected_revision=ALEMBIC_HEAD,
            expected_tenant_ids={17, 18},
        )
        is None
    )

    wrong_tenant = module.normalize_mysql_snapshot(
        {
            "alembic_version": [{"version_num": ALEMBIC_HEAD}],
            "records": [
                {"id": 1, "tenant_id": 99, "blob": b"image-a", "value": "ok"},
                {"id": 2, "tenant_id": 18, "blob": None, "value": "other"},
            ],
        }
    )
    with pytest.raises(module.MySQLBackupRestoreError, match="tenant|snapshot"):
        module.compare_mysql_snapshots(
            source,
            wrong_tenant,
            expected_revision=ALEMBIC_HEAD,
            expected_tenant_ids={17, 18},
        )


def test_attestation_producer_derives_facts_and_rejects_handwritten_fields() -> None:
    module = _mysql_module()
    signature = inspect.signature(module.create_mysql_backup_attestation)
    forbidden = {
        "passed",
        "status",
        "checks",
        "database_identity_sha256",
        "database_revision",
        "identity",
        "revision",
    }
    assert not forbidden.intersection(signature.parameters)
    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    with pytest.raises(TypeError):
        module.create_mysql_backup_attestation(
            compose_file=COMPOSE_FILE,
            backup_root=Path("/tmp/r5-backups"),
            protected_image=IMAGE,
            checks={"isolated_restore": "passed"},
        )


def test_mysql_archive_is_accepted_by_generated_attestation_gate(
    tmp_path: Path,
) -> None:
    from app.jobs.backup_restore import validate_generated_attestation

    module = _mysql_module()
    artifact = tmp_path / "mysql-backup-v1.zip"
    evidence = tmp_path / "backup-evidence.json"
    identity = "d" * 64
    module._write_mysql_artifact(
        artifact,
        b"-- synthetic transaction-consistent dump\n",
        b"synthetic-fernet-key",
        database_identity=identity,
        revision=ALEMBIC_HEAD,
    )
    module._write_evidence(
        evidence,
        artifact=artifact,
        protected_image=IMAGE,
        database_identity=identity,
        revision=ALEMBIC_HEAD,
    )

    verified = validate_generated_attestation(
        evidence,
        expected_protected_image=IMAGE,
    )
    assert verified.database_identity_sha256 == identity
    assert verified.database_revision == ALEMBIC_HEAD


def test_mysql_archive_write_failure_removes_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _mysql_module()
    artifact = tmp_path / "mysql-backup-v1.zip"
    monkeypatch.setattr(
        module.os,
        "replace",
        lambda *args: (_ for _ in ()).throw(OSError("synthetic failure")),
    )

    with pytest.raises(module.MySQLBackupRestoreError, match="cannot be written"):
        module._write_mysql_artifact(
            artifact,
            b"-- synthetic dump\n",
            b"synthetic-fernet-key",
            database_identity="d" * 64,
            revision=ALEMBIC_HEAD,
        )

    assert not artifact.exists()
    assert list(tmp_path.glob(".mysql-backup-v1.zip.*.tmp")) == []


def test_cleanup_uses_runner_and_cleans_only_the_failed_project() -> None:
    module = _mysql_module()
    calls: list[tuple[str, ...]] = []

    def runner(command: list[str] | tuple[str, ...]) -> None:
        calls.append(tuple(str(part) for part in command))

    module.cleanup_compose_project(
        compose_file=COMPOSE_FILE,
        project_name="r5-r-failed-source",
        runner=runner,
    )
    assert len(calls) == 1
    _assert_project_scoped_command(
        calls[0], project="r5-r-failed-source", action="down"
    )
    assert all("prune" not in word for word in calls[0])
    assert all("r5-r-failed-restore" not in word for word in calls[0])


def test_failed_mysql_producer_removes_its_run_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _mysql_module()
    backup_root = tmp_path / "backups"
    monkeypatch.delenv("R5_MYSQL_SOURCE_ROOT_PASSWORD", raising=False)

    with pytest.raises(module.MySQLBackupRestoreError, match="environment"):
        module.create_mysql_backup_attestation(
            compose_file=COMPOSE_FILE,
            backup_root=backup_root,
            protected_image=IMAGE,
        )

    assert backup_root.is_dir()
    assert list(backup_root.iterdir()) == []


def test_mysql_backup_root_rejects_symlink(tmp_path: Path) -> None:
    module = _mysql_module()
    target = tmp_path / "target"
    target.mkdir(mode=0o700)
    link = tmp_path / "backups"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(module.MySQLBackupRestoreError, match="unsafe"):
        module.create_mysql_backup_attestation(
            compose_file=COMPOSE_FILE,
            backup_root=link,
            protected_image=IMAGE,
        )


def test_cleanup_failure_cannot_leave_verified_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _mysql_module()
    evidence = tmp_path / "backup-evidence.json"
    synthetic_env = {
        name: f"synthetic-{index}" for index, name in enumerate(module._REQUIRED_ENV)
    }

    monkeypatch.setattr(module, "_assert_project_absent", lambda *args: None)
    monkeypatch.setattr(module, "_start_project", lambda *args: None)
    monkeypatch.setattr(
        module,
        "_container_ip",
        lambda *args: (_ for _ in ()).throw(module.MySQLBackupRestoreError("stop")),
    )
    monkeypatch.setattr(
        module,
        "_cleanup_and_verify_project",
        lambda *args: (_ for _ in ()).throw(module.MySQLBackupRestoreError("cleanup")),
    )

    with pytest.raises(module.MySQLBackupRestoreError, match="cleanup"):
        module.run_live_drill(
            compose_file=COMPOSE_FILE,
            source_project="r5-r-cleanup-source",
            restore_project="r5-r-cleanup-restore",
            protected_image=IMAGE,
            evidence_path=evidence,
            env=synthetic_env,
        )

    assert not evidence.exists()
    assert not evidence.with_name("mysql-backup-v1.zip").exists()


def test_partial_compose_start_is_still_cleaned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _mysql_module()
    evidence = tmp_path / "backup-evidence.json"
    synthetic_env = {
        name: f"synthetic-{index}" for index, name in enumerate(module._REQUIRED_ENV)
    }
    cleaned: list[str] = []

    monkeypatch.setattr(module, "_assert_project_absent", lambda *args: None)
    monkeypatch.setattr(
        module,
        "_start_project",
        lambda *args: (_ for _ in ()).throw(
            module.MySQLBackupRestoreError("partial start")
        ),
    )
    monkeypatch.setattr(
        module,
        "_cleanup_and_verify_project",
        lambda compose_file, project, env: cleaned.append(project),
    )

    with pytest.raises(module.MySQLBackupRestoreError, match="partial start"):
        module.run_live_drill(
            compose_file=COMPOSE_FILE,
            source_project="r5-r-partial-source",
            restore_project="r5-r-partial-restore",
            protected_image=IMAGE,
            evidence_path=evidence,
            env=synthetic_env,
        )

    assert cleaned == ["r5-r-partial-source"]


def test_dry_run_cannot_emit_actual_image_bound_evidence(tmp_path: Path) -> None:
    module = _mysql_module()
    evidence_path = tmp_path / "dry-run-evidence.json"
    result = module.run_live_drill(
        compose_file=COMPOSE_FILE,
        source_project="r5-r-dry-source",
        restore_project="r5-r-dry-restore",
        protected_image=IMAGE,
        evidence_path=evidence_path,
        dry_run=True,
    )
    assert result["status"] in {"ENV_UNAVAILABLE", "BLOCKED"}
    assert result.get("evidence_generated") is False
    assert not evidence_path.exists()


def test_live_drill_refuses_to_overwrite_existing_artifact(tmp_path: Path) -> None:
    module = _mysql_module()
    evidence = tmp_path / "backup-evidence.json"
    artifact = tmp_path / "mysql-backup-v1.zip"
    artifact.write_bytes(b"existing")

    with pytest.raises(module.MySQLBackupRestoreError, match="must not already exist"):
        module.run_live_drill(
            compose_file=COMPOSE_FILE,
            source_project="r5-r-existing-source",
            restore_project="r5-r-existing-restore",
            protected_image=IMAGE,
            evidence_path=evidence,
            dry_run=True,
        )

    assert artifact.read_bytes() == b"existing"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission contract")
def test_live_drill_rejects_non_owner_only_output_directory(tmp_path: Path) -> None:
    module = _mysql_module()
    output = tmp_path / "shared"
    output.mkdir(mode=0o755)

    with pytest.raises(module.MySQLBackupRestoreError, match="unsafe"):
        module.run_live_drill(
            compose_file=COMPOSE_FILE,
            source_project="r5-r-permissions-source",
            restore_project="r5-r-permissions-restore",
            protected_image=IMAGE,
            evidence_path=output / "backup-evidence.json",
            dry_run=True,
        )


@pytest.mark.skipif(
    os.environ.get("R5_MYSQL_LIVE") != "1",
    reason="live isolated MySQL Compose drill requires R5_MYSQL_LIVE=1",
)
def test_live_mysql_backup_restore_drill_isolated_and_zero_loss(tmp_path: Path) -> None:
    """Run only when explicitly requested with synthetic, caller-owned env."""
    module = _mysql_module()
    required_env = {
        "R5_MYSQL_SOURCE_ROOT_PASSWORD",
        "R5_MYSQL_SOURCE_DATABASE",
        "R5_MYSQL_SOURCE_USER",
        "R5_MYSQL_SOURCE_PASSWORD",
        "R5_MYSQL_RESTORE_ROOT_PASSWORD",
        "R5_MYSQL_RESTORE_DATABASE",
        "R5_MYSQL_RESTORE_USER",
        "R5_MYSQL_RESTORE_PASSWORD",
    }
    missing = sorted(name for name in required_env if not os.environ.get(name))
    if missing:
        pytest.fail("R5_MYSQL_LIVE=1 requires synthetic credential env names")

    result = module.run_live_drill(
        compose_file=COMPOSE_FILE,
        source_project="r5-r-live-source",
        restore_project="r5-r-live-restore",
        protected_image=IMAGE,
        evidence_path=tmp_path / "live-evidence.json",
        env={name: os.environ[name] for name in required_env},
        # The helper coordinates the open transaction with an Event/barrier;
        # this test intentionally contains no fixed sleep or retry loop.
        verify_uncommitted_transaction=True,
    )
    assert result["status"] == "verified"
    assert result["source_project"] != result["restore_project"]
    assert result["database_revision"] == ALEMBIC_HEAD
    assert result["table_names"] == sorted(result["table_names"])
    assert set(TABLE_NAMES) <= set(result["table_names"])
    assert result["tenant_boundary"] == "verified"
    assert result["blob_sha256"] == "verified"
    assert result["uncommitted_rows_in_dump"] == 0
    assert result["evidence_generated"] is True


def test_live_cli_help_is_a_real_entrypoint_without_running_docker() -> None:
    """The live drill must be callable as ``python -m`` without side effects."""
    completed = subprocess.run(
        [
            os.fspath(Path(os.sys.executable)),
            "-m",
            "scripts.r5_mysql_backup_restore",
            "--help",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0
    assert "live" in (completed.stdout + completed.stderr).casefold()
    assert "prune" not in (completed.stdout + completed.stderr).casefold()
