"""Stable contracts for the production MySQL backup producer.

The tests use a list-form Docker runner.  No real production container or
network is touched; the success case models the complete source snapshot,
dump, isolated restore, and cleanup sequence.
"""

from __future__ import annotations

import importlib
import inspect
import json
import subprocess
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

IMAGE = "ghcr.io/ywyz/kindergartenmanager@sha256:" + "a" * 64
MYSQL_IMAGE = "mysql@sha256:" + "b" * 64
TEMPLATE_NAMES = (
    "teacherplan.docx",
    "ObservationRecord.docx",
    "OneOnOneListeningSmallSecond.docx",
    "homemadeteaching.docx",
    "coursereviewactivity.docx",
)


def _module():
    return importlib.import_module("scripts.r5_mysql_production_backup")


def _completed(
    command: list[str], stdout: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=b"")


def _assets(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    secrets = tmp_path / "app-secrets"
    secrets.write_bytes(b"ENCRYPTION_KEY=redacted-test-value\n")
    secrets.chmod(0o600)
    exports = tmp_path / "exports"
    exports.mkdir(mode=0o700)
    (exports / "plan.docx").write_bytes(b"export")
    templates = tmp_path / "templates"
    templates.mkdir(mode=0o700)
    for name in TEMPLATE_NAMES:
        (templates / name).write_bytes(name.encode())
    root = tmp_path / "backup-root"
    return root, secrets, exports, templates


def _inspect_payload(image: str = IMAGE) -> bytes:
    return json.dumps(
        [
            {
                "Id": "d" * 64,
                "Config": {
                    "Image": image,
                    "Env": [
                        "DATABASE_URL=mysql+aiomysql://kindergarten:source-secret@db:3306/kindergarten_db"
                    ],
                },
                "State": {"Running": True, "Paused": True},
                "NetworkSettings": {
                    "Networks": {"kindergarten_prod": {"NetworkID": "e" * 64}}
                },
            }
        ]
    ).encode()


def test_public_signature_never_accepts_operator_database_facts() -> None:
    module = _module()
    signature = inspect.signature(module.create_mysql_production_backup_attestation)
    forbidden = {
        "database_identity_sha256",
        "database_revision",
        "identity",
        "revision",
        "status",
        "checks",
        "passed",
    }
    assert not forbidden.intersection(signature.parameters)
    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def test_dump_command_uses_env_file_and_consistent_hex_options(tmp_path: Path) -> None:
    module = _module()
    command = module.build_mysqldump_command(
        network="kindergarten_prod",
        mysql_image=MYSQL_IMAGE,
        credentials_file=tmp_path / "mysql.env",
        host="db",
        port=3306,
        user="kindergarten",
        database="kindergarten_db",
    )
    assert set(module._DUMP_OPTIONS).issubset(command)
    assert "--env-file" in command
    assert "--password" not in " ".join(command)
    assert "MYSQL_PWD" not in " ".join(command)
    assert "secret" not in " ".join(command)


def test_database_identity_strips_credentials_and_query_values() -> None:
    module = _module()
    first = module.database_identity_sha256(
        "mysql+aiomysql://user:first-secret@DB.:3306/kindergarten_db"
    )
    second = module.database_identity_sha256(
        "mysql+aiomysql://user:second-secret@db:3306/kindergarten_db"
    )
    assert first == second
    with_charset = module.database_identity_sha256(
        "mysql+aiomysql://user:first-secret@db:3306/kindergarten_db?charset=utf8mb4"
    )
    from app.core.startup import database_identity_sha256 as app_identity

    assert with_charset == app_identity(
        "mysql+aiomysql://user:first-secret@db:3306/kindergarten_db?charset=utf8mb4"
    )
    with pytest.raises(module.ProductionMySQLBackupError):
        module.database_identity_sha256(
            "mysql+aiomysql://user:secret@db:3306/kindergarten_db?password=leak"
        )


def test_snapshot_mismatch_reports_only_table_and_category() -> None:
    module = _module()
    source = {
        "tables": {
            "users": {
                "type": "BASE TABLE",
                "engine": "InnoDB",
                "columns": [{"name": "secret", "data_type": "varchar"}],
                "rows": [["V73656E736974697665"]],
            }
        },
        "tenant_ids": [],
        "blob_sha256": [],
    }
    restored = {
        **source,
        "tables": {
            "users": {
                **source["tables"]["users"],
                "rows": [["V646966666572656E74"]],
            }
        },
    }
    with pytest.raises(
        module.ProductionMySQLBackupError,
        match=r"^Restored row contents do not match source table users$",
    ) as raised:
        module._compare_snapshots(source, restored)
    assert "73656E736974697665" not in str(raised.value)
    assert "646966666572656E74" not in str(raised.value)


def test_snapshot_inventory_mismatch_reports_only_table_names() -> None:
    module = _module()
    source = {"tables": {"expected_table": {}}, "tenant_ids": [], "blob_sha256": []}
    restored = {
        "tables": {"unexpected_table": {}},
        "tenant_ids": [],
        "blob_sha256": [],
    }
    with pytest.raises(
        module.ProductionMySQLBackupError,
        match=(r"missing=expected_table unexpected=unexpected_table"),
    ):
        module._compare_snapshots(source, restored)


def test_rejects_mutable_or_unsafe_inputs() -> None:
    module = _module()
    with pytest.raises(module.ProductionMySQLBackupError):
        module._validate_image("ghcr.io/acme/app:latest", label="Protected image")
    with pytest.raises(module.ProductionMySQLBackupError):
        module._validate_mysql_image("mysql:8.4")
    with pytest.raises(module.ProductionMySQLBackupError):
        module._validate_network("kindergarten_prod;docker network rm x")
    with pytest.raises(module.ProductionMySQLBackupError):
        module._validate_container("app\n--privileged", label="Application container")


def test_temporary_credentials_are_owner_only_and_not_argv(tmp_path: Path) -> None:
    module = _module()
    credentials = tmp_path / "credentials.env"
    module._write_mysql_env(credentials, {"MYSQL_PWD": "temporary-secret"})
    assert credentials.stat().st_mode & 0o777 == 0o600
    command = module.build_mysqldump_command(
        network="kindergarten_prod",
        mysql_image=MYSQL_IMAGE,
        credentials_file=credentials,
        host="db",
        port=3306,
        user="kindergarten",
        database="kindergarten_db",
    )
    assert "temporary-secret" not in command
    credentials.unlink()


def test_restore_cleanup_continues_after_credentials_unlink_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _module()
    dump = tmp_path / "database.sql"
    dump.write_bytes(b"-- isolated restore test\n")
    calls: list[list[str]] = []
    original_unlink = Path.unlink

    def fail_server_credentials_unlink(path: Path, *, missing_ok: bool = False) -> None:
        if path.name == ".restore-mysql-server.env.tmp":
            raise OSError("injected unlink failure")
        original_unlink(path, missing_ok=missing_ok)

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        if "mysqladmin" in command:
            return _completed(command)
        if "--execute" in command:
            return _completed(command, b"already_present\n")
        return _completed(command, b"resource-id")

    monkeypatch.setattr(Path, "unlink", fail_server_credentials_unlink)
    with pytest.raises(module.ProductionMySQLBackupError, match="cleanup failed"):
        module._restore_mysql(
            dump=dump,
            source_snapshot={},
            source_revision="2b7f3d5e9c8a",
            production_network="kindergarten_prod",
            mysql_image=MYSQL_IMAGE,
            run_dir=tmp_path,
            runner=runner,
        )
    assert any(command[:3] == ["docker", "rm", "--force"] for command in calls)
    assert any(command[:3] == ["docker", "network", "rm"] for command in calls)


def test_docker_runner_uses_non_conflicting_subprocess_stream_arguments() -> None:
    module = _module()
    observed: dict[str, Any] = {}

    def strict_runner(
        command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        observed.update(kwargs)
        if kwargs.get("capture_output") and (
            kwargs.get("stdout") is not None or kwargs.get("stderr") is not None
        ):
            raise ValueError("conflicting subprocess stream arguments")
        return _completed(command, b"ok")

    result = module._run_command(["docker", "version"], runner=strict_runner)
    assert result.stdout == b"ok"
    assert "capture_output" not in observed
    assert observed["stdout"] is subprocess.PIPE
    assert observed["stderr"] is subprocess.PIPE


def test_failure_removes_run_directory_and_never_leaves_evidence(
    tmp_path: Path,
) -> None:
    module = _module()
    root, secrets, exports, templates = _assets(tmp_path)
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        if command[:2] == ["docker", "inspect"]:
            return _completed(command, _inspect_payload())
        raise subprocess.CalledProcessError(1, command, stderr=b"redacted")

    with pytest.raises(module.ProductionMySQLBackupError):
        module.create_mysql_production_backup_attestation(
            app_container="kindergarten-manager",
            network="kindergarten_prod",
            mysql_image=MYSQL_IMAGE,
            backup_root=root,
            secrets_path=secrets,
            exports_source=exports,
            templates_source=templates,
            protected_image=IMAGE,
            runner=runner,
        )
    assert list(root.glob("run-*")) == []
    assert all("source-secret" not in word for call in calls for word in call)


def test_rejects_protected_image_not_running_in_app_container(tmp_path: Path) -> None:
    module = _module()
    root, secrets, exports, templates = _assets(tmp_path)
    other_image = "ghcr.io/ywyz/kindergartenmanager@sha256:" + "c" * 64

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        if command[:2] == ["docker", "inspect"]:
            return _completed(command, _inspect_payload(other_image))
        raise AssertionError(f"unexpected command after image mismatch: {command}")

    with pytest.raises(
        module.ProductionMySQLBackupError,
        match="Protected image does not match",
    ):
        module.create_mysql_production_backup_attestation(
            app_container="kindergarten-manager",
            network="kindergarten_prod",
            mysql_image=MYSQL_IMAGE,
            backup_root=root,
            secrets_path=secrets,
            exports_source=exports,
            templates_source=templates,
            protected_image=IMAGE,
            runner=runner,
        )
    assert not root.exists() or list(root.glob("run-*")) == []


def test_cleanup_failure_is_explicit_and_keeps_no_false_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _module()
    root, secrets, exports, templates = _assets(tmp_path)

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        if command[:2] == ["docker", "inspect"]:
            return _completed(command, _inspect_payload())
        raise subprocess.CalledProcessError(1, command, stderr=b"redacted")

    monkeypatch.setattr(module.shutil, "rmtree", lambda _path: None)
    with pytest.raises(module.ProductionMySQLBackupError, match="cleanup required"):
        module.create_mysql_production_backup_attestation(
            app_container="kindergarten-manager",
            network="kindergarten_prod",
            mysql_image=MYSQL_IMAGE,
            backup_root=root,
            secrets_path=secrets,
            exports_source=exports,
            templates_source=templates,
            protected_image=IMAGE,
            runner=runner,
        )
    assert not list(root.glob("run-*/backup-evidence.json"))


def test_complete_chain_uses_a_new_network_and_writes_consumer_shape(
    tmp_path: Path,
) -> None:
    module = _module()
    root, secrets, exports, templates = _assets(tmp_path)
    calls: list[list[str]] = []
    restore_server_payloads: list[bytes] = []
    revision = "2b7f3d5e9c8a"
    controlled_now = datetime(2026, 9, 2, tzinfo=UTC)
    table_inventory = (
        b"alembic_version\tBASE TABLE\tInnoDB\nusers\tBASE TABLE\tInnoDB\n"
    )

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        if kwargs.get("stdout") not in (None, subprocess.PIPE):
            kwargs["stdout"].write(b"-- transaction-safe dump\n")
            return _completed(command)
        if command[:2] == ["docker", "inspect"]:
            return _completed(command, _inspect_payload())
        if "network" in command and "create" in command:
            return _completed(command, b"network-id")
        if "--detach" in command:
            restore_server_payloads.append(
                Path(command[command.index("--env-file") + 1]).read_bytes()
            )
            return _completed(command, b"container-id")
        if "mysqladmin" in command:
            return _completed(command)
        if (
            "mysql" in command
            and "--execute" not in command
            and "mysqldump" not in command
        ):
            return _completed(command)
        if "--execute" in command:
            query = command[command.index("--execute") + 1]
            if query == "SELECT DATABASE()":
                return _completed(command, b"kindergarten_db\n")
            if query == "SELECT version_num FROM alembic_version":
                return _completed(command, f"{revision}\n".encode())
            if query == "SHOW TABLES":
                return _completed(command)
            if "information_schema.TABLES" in query:
                return _completed(command, table_inventory)
            if "information_schema.COLUMNS" in query:
                if "alembic_version" in query:
                    return _completed(command, b"version_num\tvarchar\n")
                return _completed(command, b"id\tint\ntenant_id\tint\nblob\tblob\n")
            if "FROM `alembic_version`" in query:
                return _completed(command, f"V{revision.encode().hex()}\n".encode())
            if "FROM `users`" in query:
                return _completed(command, b"V31\x1fV31\x1fV424c4f42\n")
            raise AssertionError(f"unmodeled query: {query}")
        if "network" in command and "rm" in command:
            return _completed(command)
        if "rm" in command and "--force" in command:
            return _completed(command)
        raise AssertionError(f"unmodeled Docker command: {command}")

    evidence = module.create_mysql_production_backup_attestation(
        app_container="kindergarten-manager",
        network="kindergarten_prod",
        mysql_image=MYSQL_IMAGE,
        backup_root=root,
        secrets_path=secrets,
        exports_source=exports,
        templates_source=templates,
        protected_image=IMAGE,
        now=controlled_now,
        runner=runner,
    )
    assert evidence.is_file()
    assert evidence.stat().st_mode & 0o777 == 0o600
    artifact = evidence.with_name("mysql-backup-v1.zip")
    assert artifact.stat().st_mode & 0o777 == 0o600
    payload = json.loads(evidence.read_text())
    assert payload["status"] == "verified"
    assert payload["protected_image"] == IMAGE
    assert payload["database_revision"] == revision
    assert set(payload["checks"]) == {
        "database_integrity",
        "isolated_restore",
        "required_assets",
    }
    assert all(value == "passed" for value in payload["checks"].values())
    with zipfile.ZipFile(artifact) as archive:
        members = set(archive.namelist())
    assert "database.sql" in members
    assert "manifest.json" in members
    assert {f"templates/{name}" for name in TEMPLATE_NAMES} <= members
    assert "exports/plan.docx" in members
    assert "secrets/.kindergarten_secrets" in members
    assert any(
        "--network" in command
        and command[command.index("--network") + 1] != "kindergarten_prod"
        for command in calls
        if "--network" in command
    )
    assert all("source-secret" not in word for command in calls for word in command)
    assert not list(evidence.parent.glob(".*.tmp"))
    assert sum(command[:2] == ["docker", "inspect"] for command in calls) == 3
    detached = next(command for command in calls if "--detach" in command)
    server_env = detached[detached.index("--env-file") + 1]
    client_envs = {
        command[command.index("--env-file") + 1]
        for command in calls
        if "--env-file" in command
        and "restore-mysql-client" in command[command.index("--env-file") + 1]
    }
    assert client_envs == {server_env.replace("server", "client")}
    assert server_env not in client_envs
    assert restore_server_payloads
    assert all(b"MYSQL_PWD=" not in payload for payload in restore_server_payloads)
    import_commands = [
        command
        for command in calls
        if "mysql" in command
        and "--binary-mode" in command
        and "--interactive" in command
    ]
    assert len(import_commands) == 1
    snapshot_queries = [
        command[command.index("--execute") + 1]
        for command in calls
        if "--execute" in command
        and "CONCAT_WS" in command[command.index("--execute") + 1]
    ]
    assert snapshot_queries
    assert all("HEX(CAST(" in query for query in snapshot_queries)
    from app.jobs.backup_restore import validate_generated_attestation

    validated = validate_generated_attestation(
        evidence,
        expected_protected_image=IMAGE,
        now=controlled_now + timedelta(minutes=1),
    )
    assert validated.database_revision == revision
    from app.core.backup_evidence import BackupEvidenceError

    with pytest.raises(BackupEvidenceError, match="expired"):
        validate_generated_attestation(
            evidence,
            expected_protected_image=IMAGE,
            now=controlled_now + timedelta(hours=25),
        )
