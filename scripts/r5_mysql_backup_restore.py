"""Isolated MySQL backup/restore contract and R5-R live-drill entry point."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import uuid
import zipfile
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from alembic.config import Config
from cryptography.fernet import Fernet
from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from alembic import command as alembic_command
from app.core.models.ai_key import AiApiKey
from app.core.models.course_review_activity import CourseReviewActivity
from app.core.models.daily_plan import DailyPlan
from app.core.models.game_observation import GameObservation
from app.core.models.game_observation_image import GameObservationImage
from app.core.models.homemade_teaching import HomemadeTeachingToy
from app.core.models.listening_image import ListeningImage
from app.core.models.listening_record import ListeningRecord
from app.core.models.user import User, UserRole
from app.core.startup import database_identity_sha256, get_migration_head
from app.jobs.backup_restore import validate_generated_attestation


class MySQLBackupRestoreError(RuntimeError):
    """The isolated MySQL backup/restore contract was violated."""


_PROJECT_PART = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
_PROJECT = re.compile(r"^r5-r-[a-z0-9-]+-(?:source|restore)$")
_ROLES = {"source", "restore"}
_ACTIONS = {"up", "down", "ps", "exec", "config"}
_DUMP_OPTIONS = (
    "--single-transaction",
    "--quick",
    "--skip-lock-tables",
    "--hex-blob",
    "--triggers",
    "--routines",
    "--events",
    "--set-gtid-purged=OFF",
    "--no-tablespaces",
)
_REQUIRED_ENV = tuple(
    f"R5_MYSQL_{role}_{field}"
    for role in ("SOURCE", "RESTORE")
    for field in ("ROOT_PASSWORD", "DATABASE", "USER", "PASSWORD")
)
_SUBPROCESS_ENV_ALLOWLIST = (
    "PATH",
    "LANG",
    "LC_ALL",
    "DOCKER_HOST",
    "DOCKER_CONTEXT",
    "DOCKER_CONFIG",
)
_LIVE_TIMEOUT = 180
_CONTROLLED_COMPOSE_FILE = (
    Path(__file__).parents[1] / "specs" / "operations-r5" / "mysql-compose.yml"
).resolve()


def compose_project_name(*, role: str, run_id: str) -> str:
    """Return a closed, disposable Compose project name."""
    normalized = run_id.casefold().strip("-")
    if role not in _ROLES or not _PROJECT_PART.fullmatch(normalized):
        raise MySQLBackupRestoreError("Invalid isolated Compose project identity")
    name = f"r5-r-{normalized}-{role}"
    if "production" in name or _PROJECT.fullmatch(name) is None:
        raise MySQLBackupRestoreError("Unsafe isolated Compose project identity")
    return name


def _validate_compose_inputs(compose_file: Path, project_name: str) -> tuple[Path, str]:
    path = Path(compose_file)
    if not path.is_absolute() or path != _CONTROLLED_COMPOSE_FILE:
        raise MySQLBackupRestoreError(
            "Only the isolated MySQL Compose manifest is allowed"
        )
    try:
        info = path.lstat()
    except OSError:
        raise MySQLBackupRestoreError(
            "The isolated MySQL Compose manifest is unavailable"
        ) from None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise MySQLBackupRestoreError("The isolated MySQL Compose manifest is unsafe")
    if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        raise MySQLBackupRestoreError(
            "The isolated MySQL Compose manifest has an unsafe owner"
        )
    if _PROJECT.fullmatch(project_name) is None or "production" in project_name:
        raise MySQLBackupRestoreError("Compose project is not an isolated R5-R project")
    return path, project_name


def build_compose_command(
    *,
    compose_file: Path,
    project_name: str,
    action: str,
    service: str | None = None,
) -> list[str]:
    """Build a command scoped to one explicit project and drill manifest."""
    manifest, project = _validate_compose_inputs(compose_file, project_name)
    if action not in _ACTIONS:
        raise MySQLBackupRestoreError("Unsupported Compose action")
    if service is not None and service not in _ROLES:
        raise MySQLBackupRestoreError("Unsupported isolated MySQL service")
    command = [
        "docker",
        "compose",
        "--project-name",
        project,
        "-f",
        str(manifest),
        action,
    ]
    if action == "up":
        command.extend(["-d", "--wait"])
    if service is not None:
        command.append(service)
    if action == "down":
        command.extend(["--volumes", "--remove-orphans"])
    return command


def build_cleanup_command(*, compose_file: Path, project_name: str) -> list[str]:
    """Build the sole permitted cleanup operation."""
    return build_compose_command(
        compose_file=compose_file,
        project_name=project_name,
        action="down",
    )


def build_mysqldump_args(
    *,
    host: str,
    port: int,
    database: str,
    user: str,
    output_path: Path,
) -> list[str]:
    """Build password-free, transaction-consistent mysqldump arguments."""
    if not host or not database or not user or not 1 <= port <= 65535:
        raise MySQLBackupRestoreError("Invalid MySQL dump target")
    destination = Path(output_path)
    if not destination.is_absolute():
        raise MySQLBackupRestoreError("MySQL dump output must be absolute")
    return [
        "mysqldump",
        *_DUMP_OPTIONS,
        f"--host={host}",
        f"--port={port}",
        f"--user={user}",
        f"--result-file={destination}",
        database,
    ]


def mysql_identity_digest(database_url: str) -> str:
    """Hash a credential-free MySQL location identity."""
    try:
        url = make_url(database_url)
    except Exception as exc:
        raise MySQLBackupRestoreError("Invalid MySQL target") from exc
    if url.get_backend_name() != "mysql" or not url.host or not url.database:
        raise MySQLBackupRestoreError("Invalid MySQL target")
    return database_identity_sha256(database_url)


def validate_innodb_tables(engines: Mapping[str, str | None]) -> None:
    """Reject a logical snapshot when any included table is non-transactional."""
    if not engines or any(engine != "InnoDB" for engine in engines.values()):
        raise MySQLBackupRestoreError("Every backed-up table must use InnoDB")


def validate_fresh_restore_target(path: Path) -> Path:
    """Require a destination that does not exist yet."""
    candidate = Path(path)
    if not candidate.is_absolute() or candidate.exists() or candidate.is_symlink():
        raise MySQLBackupRestoreError("Restore target must be fresh, empty, and new")
    return candidate


def _normalise_value(name: str, value: Any) -> tuple[str, Any]:
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        return f"{name}_sha256", hashlib.sha256(raw).hexdigest()
    if isinstance(value, (datetime, date)):
        return name, value.isoformat()
    if isinstance(value, Decimal):
        return name, str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return name, value
    return name, str(value)


def normalize_mysql_snapshot(
    rows: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Create a deterministic, redacted logical snapshot of every table."""
    tables: dict[str, list[dict[str, Any]]] = {}
    counts: dict[str, int] = {}
    for table_name in sorted(rows):
        if not table_name or not isinstance(table_name, str):
            raise MySQLBackupRestoreError("Invalid table name in snapshot")
        normalized_rows: list[dict[str, Any]] = []
        for row in rows[table_name]:
            normalized: dict[str, Any] = {}
            for column in sorted(row):
                target, value = _normalise_value(column, row[column])
                normalized[target] = value
            normalized_rows.append(normalized)
        normalized_rows.sort(
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"))
        )
        tables[table_name] = normalized_rows
        counts[table_name] = len(normalized_rows)
    return {"table_counts": counts, "tables": tables}


def compare_mysql_snapshots(
    source: Mapping[str, Any],
    restored: Mapping[str, Any],
    *,
    expected_revision: str,
    expected_tenant_ids: set[int],
) -> None:
    """Verify zero loss, revision, and the exact synthetic tenant set."""
    if source != restored:
        raise MySQLBackupRestoreError(
            "Restored snapshot does not match source snapshot"
        )
    tables = restored.get("tables")
    if not isinstance(tables, Mapping):
        raise MySQLBackupRestoreError("Restored snapshot is invalid")
    revisions = tables.get("alembic_version")
    if revisions != [{"version_num": expected_revision}]:
        raise MySQLBackupRestoreError("Restored database revision does not match")
    actual_tenants: set[int] = set()
    for table_rows in tables.values():
        if not isinstance(table_rows, list):
            raise MySQLBackupRestoreError("Restored snapshot is invalid")
        for row in table_rows:
            tenant_id = row.get("tenant_id")
            if isinstance(tenant_id, int):
                actual_tenants.add(tenant_id)
            elif isinstance(tenant_id, str) and tenant_id.isdecimal():
                actual_tenants.add(int(tenant_id))
    if actual_tenants != expected_tenant_ids:
        raise MySQLBackupRestoreError(
            f"Restored tenant boundary does not match: {sorted(actual_tenants)}"
        )


def _snapshot_tenant_ids(snapshot: Mapping[str, Any]) -> set[int]:
    tenants: set[int] = set()
    tables = snapshot.get("tables", {})
    if not isinstance(tables, Mapping):
        return tenants
    for rows in tables.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            value = row.get("tenant_id")
            if isinstance(value, int):
                tenants.add(value)
            elif isinstance(value, str) and value.isdecimal():
                tenants.add(int(value))
    return tenants


def cleanup_compose_project(
    *,
    compose_file: Path,
    project_name: str,
    runner: Callable[[list[str]], Any] | None = None,
) -> None:
    """Clean exactly one disposable Compose project."""
    command = build_cleanup_command(
        compose_file=compose_file,
        project_name=project_name,
    )
    if runner is not None:
        runner(command)
        return
    subprocess.run(command, check=True, capture_output=True, text=True)


def create_mysql_backup_attestation(
    *,
    compose_file: Path,
    backup_root: Path,
    protected_image: str,
    source_project: str | None = None,
    restore_project: str | None = None,
) -> Path:
    """Run the controlled live producer using only explicit synthetic env."""
    root = _prepare_backup_root(backup_root)
    run_id = uuid.uuid4().hex
    source = source_project or compose_project_name(role="source", run_id=run_id)
    restore = restore_project or compose_project_name(role="restore", run_id=run_id)
    run_dir = root / f"run-{run_id}"
    run_dir.mkdir(mode=0o700)
    evidence = run_dir / "backup-evidence.json"
    try:
        result = run_live_drill(
            compose_file=compose_file,
            source_project=source,
            restore_project=restore,
            protected_image=protected_image,
            evidence_path=evidence,
            env={
                name: os.environ[name] for name in _REQUIRED_ENV if name in os.environ
            },
            verify_uncommitted_transaction=True,
        )
        if result["status"] != "verified":
            raise MySQLBackupRestoreError(
                "Live MySQL backup producer is ENV_UNAVAILABLE"
            )
        return evidence
    except BaseException:
        shutil.rmtree(run_dir, ignore_errors=True)
        raise


def _prepare_backup_root(backup_root: Path) -> Path:
    root = Path(backup_root)
    if not root.is_absolute():
        raise MySQLBackupRestoreError("Backup root must be absolute")
    if root.exists() or root.is_symlink():
        try:
            info = root.lstat()
        except OSError:
            raise MySQLBackupRestoreError("Backup root is unavailable") from None
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise MySQLBackupRestoreError("Backup root is unsafe")
        if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
            raise MySQLBackupRestoreError("Backup root has an unsafe owner")
        if os.name == "posix" and stat.S_IMODE(info.st_mode) != 0o700:
            raise MySQLBackupRestoreError("Backup root must have mode 0700")
    else:
        root.mkdir(mode=0o700, parents=True)
    return root.resolve()


def _live_env(values: Mapping[str, str] | None) -> dict[str, str]:
    supplied = dict(values or {})
    if set(supplied) != set(_REQUIRED_ENV) or any(
        not supplied[name] for name in _REQUIRED_ENV
    ):
        raise MySQLBackupRestoreError("Synthetic MySQL environment is incomplete")
    combined = {
        name: os.environ[name]
        for name in _SUBPROCESS_ENV_ALLOWLIST
        if os.environ.get(name)
    }
    combined.update(supplied)
    return combined


def _run_command(
    command: Sequence[str],
    *,
    env: Mapping[str, str],
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            list(command),
            check=True,
            capture_output=True,
            input=input_bytes,
            env=dict(env),
            timeout=_LIVE_TIMEOUT,
        )
    except subprocess.CalledProcessError as exc:
        match = re.search(rb"ERROR\s+(\d+)", exc.stderr or b"")
        error_code = match.group(1).decode() if match else "unknown"
        raise MySQLBackupRestoreError(
            f"Isolated MySQL command failed (errno={error_code})"
        ) from None
    except (OSError, subprocess.SubprocessError):
        raise MySQLBackupRestoreError("Isolated MySQL command failed") from None


def _assert_project_absent(
    compose_file: Path,
    project: str,
    env: Mapping[str, str],
) -> None:
    if any(
        _run_command(command, env=env).stdout.strip()
        for command in _project_resource_commands(compose_file, project)
    ):
        raise MySQLBackupRestoreError(
            "Isolated MySQL Compose project already contains resources"
        )


def _project_resource_commands(
    compose_file: Path, project: str
) -> tuple[list[str], ...]:
    return (
        [
            *build_compose_command(
                compose_file=compose_file,
                project_name=project,
                action="ps",
            ),
            "--all",
            "--quiet",
        ],
        [
            "docker",
            "network",
            "ls",
            "--quiet",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ],
        [
            "docker",
            "volume",
            "ls",
            "--quiet",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ],
    )


def _cleanup_and_verify_project(
    compose_file: Path,
    project: str,
    env: Mapping[str, str],
) -> None:
    _run_command(
        build_cleanup_command(compose_file=compose_file, project_name=project),
        env=env,
    )
    if any(
        _run_command(command, env=env).stdout.strip()
        for command in _project_resource_commands(compose_file, project)
    ):
        raise MySQLBackupRestoreError(
            "Isolated MySQL Compose cleanup left project resources"
        )


def _start_project(
    compose_file: Path,
    project: str,
    role: str,
    env: Mapping[str, str],
) -> None:
    _run_command(
        build_compose_command(
            compose_file=compose_file,
            project_name=project,
            action="up",
            service=role,
        ),
        env=env,
    )


def _container_ip(
    compose_file: Path,
    project: str,
    role: str,
    env: Mapping[str, str],
) -> str:
    ps = build_compose_command(
        compose_file=compose_file,
        project_name=project,
        action="ps",
        service=role,
    )
    ps.extend(["-q"])
    container_id = _run_command(ps, env=env).stdout.decode().strip()
    if not re.fullmatch(r"[0-9a-f]{12,64}", container_id):
        raise MySQLBackupRestoreError(
            "Isolated MySQL container identity is unavailable"
        )
    inspected = (
        _run_command(
            [
                "docker",
                "inspect",
                "--format",
                "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                container_id,
            ],
            env=env,
        )
        .stdout.decode()
        .strip()
    )
    if not re.fullmatch(r"[0-9a-fA-F:.]+", inspected):
        raise MySQLBackupRestoreError("Isolated MySQL address is unavailable")
    return inspected


def _role_url(env: Mapping[str, str], role: str, host: str) -> URL:
    prefix = f"R5_MYSQL_{role.upper()}_"
    return URL.create(
        "mysql+pymysql",
        username=env[f"{prefix}USER"],
        password=env[f"{prefix}PASSWORD"],
        host=host,
        port=3306,
        database=env[f"{prefix}DATABASE"],
    )


def _migrate_source(url: URL) -> None:
    from app.core.config import settings

    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option(
        "script_location", str(Path(__file__).parents[1] / "alembic")
    )
    rendered = url.render_as_string(hide_password=False)
    previous_url = settings.DATABASE_URL
    try:
        # alembic/env.py intentionally resolves the application Settings
        # object. Bind that same object to this disposable source only for the
        # duration of the isolated migration.
        settings.DATABASE_URL = rendered
        alembic_command.upgrade(config, "head")
    except Exception as exc:  # noqa: BLE001 - redact driver/Alembic connection details
        error_args = getattr(getattr(exc, "orig", None), "args", ())
        error_code = (
            error_args[0] if error_args and isinstance(error_args[0], int) else None
        )
        raise MySQLBackupRestoreError(
            f"Synthetic source migration failed ({type(exc).__name__}, errno={error_code})"
        ) from None
    finally:
        settings.DATABASE_URL = previous_url


def _seed_source(engine: Engine, fernet_key: bytes) -> None:
    now = datetime(2026, 9, 1, 4, 0, tzinfo=UTC).replace(tzinfo=None)
    with Session(engine) as session:
        users = [
            User(
                tenant_id=tenant,
                username=f"synthetic-{tenant}",
                hashed_password=f"synthetic-hash-{tenant}",
                role=UserRole.teacher,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            for tenant in (17, 18)
        ]
        session.add_all(users)
        session.flush()
        user17, user18 = users
        plan17 = DailyPlan(
            tenant_id=17,
            user_id=user17.id,
            plan_date=date(2026, 9, 1),
            week_number=1,
            weekday_cn="周二",
            grade="小班",
            class_name="合成一班",
            activity_goal="synthetic-daily-plan",
            created_at=now,
            updated_at=now,
        )
        plan18 = DailyPlan(
            tenant_id=18,
            user_id=user18.id,
            plan_date=date(2026, 9, 2),
            week_number=1,
            weekday_cn="周三",
            grade="中班",
            class_name="合成二班",
            activity_goal="synthetic-second-tenant",
            created_at=now,
            updated_at=now,
        )
        observation = GameObservation(
            tenant_id=17,
            user_id=user17.id,
            obs_date=date(2026, 9, 1),
            big_env="室内",
            observation_record="synthetic-observation",
            created_at=now,
            updated_at=now,
        )
        listening = ListeningRecord(
            tenant_id=17,
            user_id=user17.id,
            obs_year=2026,
            obs_month=9,
            child_name="合成幼儿",
            created_at=now,
            updated_at=now,
        )
        session.add_all([plan17, plan18, observation, listening])
        session.flush()
        session.add_all(
            [
                GameObservationImage(
                    tenant_id=17,
                    user_id=user17.id,
                    observation_id=observation.id,
                    image_index=1,
                    storage_backend="mysql_blob",
                    blob_content=b"synthetic-game-image-r5-r",
                    mime_type="image/png",
                    file_size=25,
                    width=2,
                    height=2,
                    created_at=now,
                    updated_at=now,
                ),
                ListeningImage(
                    tenant_id=17,
                    user_id=user17.id,
                    record_id=listening.id,
                    domain="语言",
                    image_index=1,
                    storage_backend="mysql_blob",
                    blob_content=b"synthetic-listening-image-r5-r",
                    mime_type="image/png",
                    file_size=30,
                    width=2,
                    height=2,
                    created_at=now,
                    updated_at=now,
                ),
                HomemadeTeachingToy(
                    tenant_id=17,
                    user_id=user17.id,
                    grade="小班",
                    class_name="合成一班",
                    teacher_name="合成教师",
                    toy_name="合成教玩具",
                    materials="纸板",
                    play_methods="合成玩法",
                    created_at=now,
                    updated_at=now,
                ),
                CourseReviewActivity(
                    tenant_id=17,
                    user_id=user17.id,
                    grade="小班",
                    class_name="合成一班",
                    teacher_name="合成教师",
                    activity_name="合成课程",
                    child_count="20",
                    activity_time="30分钟",
                    lesson_plan_original="合成原教案",
                    activity_goal="目标",
                    activity_prep="准备",
                    activity_process="过程",
                    goal_adjusted=False,
                    goal_adjustment="",
                    activity_goal_revised="目标",
                    prep_adjusted=False,
                    prep_adjustment="",
                    activity_prep_revised="准备",
                    process_adjustment="",
                    activity_process_revised="过程",
                    review_reason="合成复核",
                    revised_lesson_plan="合成修订教案",
                    created_at=now,
                    updated_at=now,
                ),
                AiApiKey(
                    tenant_id=17,
                    user_id=user17.id,
                    api_base_url="https://synthetic.invalid/v1",
                    model_name="synthetic-model",
                    api_key_encrypted=Fernet(fernet_key)
                    .encrypt(b"synthetic-ai-key-r5-r")
                    .decode(),
                    key_type="text",
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.commit()


def _table_rows(engine: Engine) -> dict[str, list[dict[str, Any]]]:
    metadata = MetaData()
    metadata.reflect(engine)
    result: dict[str, list[dict[str, Any]]] = {}
    with engine.connect() as connection:
        for name in sorted(metadata.tables):
            table = metadata.tables[name]
            result[name] = [
                dict(row) for row in connection.execute(select(table)).mappings()
            ]
    return result


def _innodb_engines(engine: Engine) -> dict[str, str | None]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'"
            )
        )
        return {row[0]: row[1] for row in rows}


def _compose_exec(
    compose_file: Path,
    project: str,
    role: str,
    shell: str,
) -> list[str]:
    command = build_compose_command(
        compose_file=compose_file,
        project_name=project,
        action="exec",
    )
    command.extend(["-T", role, "sh", "-c", shell])
    return command


def _dump_source(
    compose_file: Path,
    project: str,
    env: Mapping[str, str],
) -> bytes:
    options = " ".join(_DUMP_OPTIONS)
    shell = (
        'MYSQL_PWD="$MYSQL_PASSWORD" exec mysqldump '
        f'{options} --user="$MYSQL_USER" --host=localhost "$MYSQL_DATABASE"'
    )
    return _run_command(
        _compose_exec(compose_file, project, "source", shell), env=env
    ).stdout


def _source_transaction_is_active(
    compose_file: Path,
    project: str,
    env: Mapping[str, str],
    connection_id: int,
) -> bool:
    if connection_id < 1:
        raise MySQLBackupRestoreError("Invalid synthetic transaction identity")
    shell = (
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --batch --skip-column-names '
        "--user=root --host=localhost -e "
        f'"SELECT COUNT(*) FROM information_schema.innodb_trx '
        f'WHERE trx_mysql_thread_id={connection_id}"'
    )
    output = (
        _run_command(_compose_exec(compose_file, project, "source", shell), env=env)
        .stdout.decode()
        .strip()
    )
    return output == "1"


def _import_restore(
    compose_file: Path,
    project: str,
    env: Mapping[str, str],
    dump: bytes,
) -> None:
    shell = (
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql '
        '--user=root --host=localhost "$MYSQL_DATABASE"'
    )
    _run_command(
        _compose_exec(compose_file, project, "restore", shell),
        env=env,
        input_bytes=dump,
    )


def _secure_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)


def _write_mysql_artifact(
    artifact: Path,
    dump: bytes,
    fernet_key: bytes,
    *,
    database_identity: str,
    revision: str,
) -> None:
    members: dict[str, bytes] = {
        "database.sql": dump,
        "secrets/.kindergarten_secrets": (
            b"ENCRYPTION_KEY=" + fernet_key + b"\nJWT_SECRET=synthetic-r5-r\n"
        ),
        "exports/synthetic-r5-r.docx": b"synthetic export",
    }
    template_root = Path(__file__).parents[1] / "templates"
    for name in (
        "teacherplan.docx",
        "ObservationRecord.docx",
        "OneOnOneListeningSmallSecond.docx",
        "homemadeteaching.docx",
        "coursereviewactivity.docx",
    ):
        members[f"templates/{name}"] = (template_root / name).read_bytes()
    manifest = {
        "schema_version": 1,
        "kind": "kindergarten-manager-backup",
        "database": {
            "backend": "mysql",
            "path": "database.sql",
            "identity_sha256": database_identity,
            "revision": revision,
            "size_bytes": len(dump),
            "sha256": hashlib.sha256(dump).hexdigest(),
        },
        "assets": [
            {
                "path": name,
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for name, payload in sorted(members.items())
            if name != "database.sql"
        ],
    }
    temp = artifact.with_name(f".{artifact.name}.{uuid.uuid4().hex}.tmp")
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "manifest.json",
                json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
            )
            for name, payload in sorted(members.items()):
                archive.writestr(name, payload)
        os.chmod(temp, 0o600)
        os.replace(temp, artifact)
    except BaseException as exc:
        temp.unlink(missing_ok=True)
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise MySQLBackupRestoreError(
            "MySQL backup archive cannot be written"
        ) from None


def _write_evidence(
    path: Path,
    *,
    artifact: Path,
    protected_image: str,
    database_identity: str,
    revision: str,
) -> None:
    created = datetime.now(UTC)
    artifact_bytes = artifact.read_bytes()
    payload = {
        "schema_version": 1,
        "status": "verified",
        "created_at": created.isoformat().replace("+00:00", "Z"),
        "expires_at": (created + timedelta(hours=24))
        .isoformat()
        .replace("+00:00", "Z"),
        "protected_image": protected_image,
        "database_identity_sha256": database_identity,
        "database_revision": revision,
        "artifact": {
            "path": str(artifact.resolve()),
            "size_bytes": len(artifact_bytes),
            "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        },
        "checks": {
            "database_integrity": "passed",
            "isolated_restore": "passed",
            "required_assets": "passed",
        },
    }
    _secure_write(path, json.dumps(payload, sort_keys=True).encode())


def run_live_drill(
    *,
    compose_file: Path,
    source_project: str,
    restore_project: str,
    protected_image: str,
    evidence_path: Path,
    dry_run: bool = False,
    env: Mapping[str, str] | None = None,
    verify_uncommitted_transaction: bool = False,
) -> dict[str, Any]:
    """Run the disposable live drill; dry-run can never emit attestation."""
    _validate_compose_inputs(compose_file, source_project)
    _validate_compose_inputs(compose_file, restore_project)
    if source_project == restore_project:
        raise MySQLBackupRestoreError("Source and restore projects must be distinct")
    evidence = Path(evidence_path)
    if not evidence.is_absolute():
        raise MySQLBackupRestoreError("Evidence output path must be absolute")
    parent = evidence.parent
    try:
        parent_info = parent.lstat()
    except OSError:
        raise MySQLBackupRestoreError(
            "Evidence output directory is unavailable"
        ) from None
    if (
        stat.S_ISLNK(parent_info.st_mode)
        or not stat.S_ISDIR(parent_info.st_mode)
        or (hasattr(os, "geteuid") and parent_info.st_uid != os.geteuid())
        or (os.name == "posix" and stat.S_IMODE(parent_info.st_mode) != 0o700)
        or parent.resolve() != parent
    ):
        raise MySQLBackupRestoreError("Evidence output directory is unsafe")
    if evidence.exists() or evidence.is_symlink():
        raise MySQLBackupRestoreError("Evidence output must not already exist")
    artifact = evidence.with_name("mysql-backup-v1.zip")
    if artifact.exists() or artifact.is_symlink():
        raise MySQLBackupRestoreError("Backup artifact output must not already exist")
    if dry_run:
        return {
            "status": "BLOCKED",
            "protected_image": protected_image,
            "source_project": source_project,
            "restore_project": restore_project,
            "evidence_generated": False,
        }

    live_env = _live_env(env)
    source_engine: Engine | None = None
    restore_engine: Engine | None = None
    transaction_connection = None
    transaction = None
    dump = b""
    stage = "start_source"
    started_projects: list[str] = []
    try:
        _assert_project_absent(compose_file, source_project, live_env)
        _assert_project_absent(compose_file, restore_project, live_env)
        started_projects.append(source_project)
        _start_project(compose_file, source_project, "source", live_env)
        stage = "source_address"
        source_url = _role_url(
            live_env,
            "source",
            _container_ip(compose_file, source_project, "source", live_env),
        )
        stage = "source_migration"
        _migrate_source(source_url)
        source_engine = create_engine(source_url, pool_pre_ping=True)
        fernet_key = Fernet.generate_key()
        stage = "source_seed"
        _seed_source(source_engine, fernet_key)
        stage = "source_snapshot"
        validate_innodb_tables(_innodb_engines(source_engine))
        source_rows = _table_rows(source_engine)
        source_snapshot = normalize_mysql_snapshot(source_rows)
        source_tenants = _snapshot_tenant_ids(source_snapshot)
        if not {17, 18}.issubset(source_tenants):
            raise MySQLBackupRestoreError("Synthetic tenant seed is incomplete")

        if verify_uncommitted_transaction:
            stage = "uncommitted_transaction"
            transaction_connection = source_engine.connect()
            transaction = transaction_connection.begin()
            connection_id = transaction_connection.execute(
                text("SELECT CONNECTION_ID()")
            ).scalar_one()
            transaction_connection.execute(
                text(
                    "INSERT INTO daily_plan "
                    "(tenant_id,user_id,revision,plan_date,week_number,weekday_cn,"
                    "grade,class_name,activity_goal,created_at,updated_at) "
                    "VALUES (17,1,1,'2026-09-03',1,'周四','小班','合成一班',"
                    "'r5-r-uncommitted-marker',NOW(),NOW())"
                )
            )
            if not _source_transaction_is_active(
                compose_file,
                source_project,
                live_env,
                int(connection_id),
            ):
                raise MySQLBackupRestoreError(
                    "Uncommitted transaction was not observable"
                )

        stage = "source_dump"
        dump = _dump_source(compose_file, source_project, live_env)
        if not dump:
            raise MySQLBackupRestoreError("MySQL dump is empty")
        if transaction is not None:
            transaction.rollback()
            transaction = None
            transaction_connection.close()
            transaction_connection = None

        stage = "start_restore"
        started_projects.append(restore_project)
        _start_project(compose_file, restore_project, "restore", live_env)
        stage = "restore_address"
        restore_url = _role_url(
            live_env,
            "restore",
            _container_ip(compose_file, restore_project, "restore", live_env),
        )
        restore_engine = create_engine(restore_url, pool_pre_ping=True)
        stage = "restore_freshness"
        if inspect(restore_engine).get_table_names():
            raise MySQLBackupRestoreError("Restore target is not fresh")
        stage = "restore_import"
        _import_restore(compose_file, restore_project, live_env, dump)
        stage = "restore_snapshot"
        restored_rows = _table_rows(restore_engine)
        restored_snapshot = normalize_mysql_snapshot(restored_rows)
        revision = get_migration_head()
        compare_mysql_snapshots(
            source_snapshot,
            restored_snapshot,
            expected_revision=revision,
            expected_tenant_ids=source_tenants,
        )
        uncommitted_rows = sum(
            1
            for row in restored_rows.get("daily_plan", [])
            if row.get("activity_goal") == "r5-r-uncommitted-marker"
        )
        if uncommitted_rows:
            raise MySQLBackupRestoreError(
                "Uncommitted rows appeared in restored database"
            )

        stage = "attestation"
        identity = mysql_identity_digest(
            f"mysql://source:3306/{live_env['R5_MYSQL_SOURCE_DATABASE']}"
        )
        _write_mysql_artifact(
            artifact,
            dump,
            fernet_key,
            database_identity=identity,
            revision=revision,
        )
        _write_evidence(
            evidence,
            artifact=artifact,
            protected_image=protected_image,
            database_identity=identity,
            revision=revision,
        )
        validate_generated_attestation(
            evidence,
            expected_protected_image=protected_image,
        )
        return {
            "status": "verified",
            "source_project": source_project,
            "restore_project": restore_project,
            "database_revision": revision,
            "table_names": sorted(restored_rows),
            "tenant_boundary": "verified",
            "blob_sha256": "verified",
            "uncommitted_rows_in_dump": uncommitted_rows,
            "evidence_generated": True,
        }
    except MySQLBackupRestoreError:
        evidence.unlink(missing_ok=True)
        artifact.unlink(missing_ok=True)
        raise
    except Exception as exc:  # noqa: BLE001 - one redacted boundary for DB/Docker drivers
        evidence.unlink(missing_ok=True)
        artifact.unlink(missing_ok=True)
        error_args = getattr(getattr(exc, "orig", None), "args", ())
        error_code = (
            error_args[0] if error_args and isinstance(error_args[0], int) else None
        )
        raise MySQLBackupRestoreError(
            f"Isolated live MySQL drill failed at {stage} "
            f"({type(exc).__name__}, errno={error_code})"
        ) from None
    finally:
        if transaction is not None:
            transaction.rollback()
        if transaction_connection is not None:
            transaction_connection.close()
        if source_engine is not None:
            source_engine.dispose()
        if restore_engine is not None:
            restore_engine.dispose()
        cleanup_failed = False
        for project in reversed(started_projects):
            try:
                _cleanup_and_verify_project(compose_file, project, live_env)
            except MySQLBackupRestoreError:
                cleanup_failed = True
        if cleanup_failed:
            evidence.unlink(missing_ok=True)
            artifact.unlink(missing_ok=True)
            raise MySQLBackupRestoreError("Isolated MySQL cleanup failed")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the isolated R5-R live MySQL backup/restore drill."
    )
    parser.add_argument("--compose-file", type=Path)
    parser.add_argument("--source-project")
    parser.add_argument("--restore-project")
    parser.add_argument("--protected-image")
    parser.add_argument("--evidence-path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not all(
        (
            args.compose_file,
            args.source_project,
            args.restore_project,
            args.protected_image,
            args.evidence_path,
        )
    ):
        return 0
    controlled_env = {name: os.environ.get(name, "") for name in _REQUIRED_ENV}
    result = run_live_drill(**vars(args), env=controlled_env)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
