"""Auditable W008 acceptance against one disposable, migrated MySQL 8 database.

The command is intentionally single-shot.  Migrations are exercised by the
surrounding acceptance procedure; this helper only accepts the final current
head and never retries a failed check.  Application imports are delayed until
the exact-SHA linked-worktree gate has passed.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from typing import Any, Protocol
import uuid

from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


MYSQL_URL_ENV = "W008_MYSQL_DATABASE_URL"
CURRENT_HEAD = "e5f7a9c2d4b6"
TRIGGER_CASES = frozenset(
    {
        ("daily_plan_operation_version", "UPDATE"),
        ("daily_plan_operation_version", "DELETE"),
        ("agent_write_audit", "UPDATE"),
        ("agent_write_audit", "DELETE"),
    }
)
_EXPECTED_TRIGGER_ROWS = frozenset(
    {
        (
            f"trg_{table_name}_no_{operation.casefold()}",
            table_name,
            operation,
            "BEFORE",
        )
        for table_name, operation in TRIGGER_CASES
    }
)
_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
_MYSQL_8_PATTERN = re.compile(r"8(?:\.\d+){1,}")
_MYSQL_DATABASE_PATTERN = re.compile(r"[A-Za-z0-9]+")
_TENANT_ID = 8_008_001
_USER_ID = 8_008_002
_PLAN_ID = 8_008_003


class ManualHelperError(RuntimeError):
    """A fail-closed error whose message never contains connection details."""


class AcceptanceBackend(Protocol):
    """Narrow backend seam used by the deterministic report validator."""

    async def server_version(self) -> str: ...

    async def app_principal_is_schema_scoped(self) -> bool: ...

    async def current_alembic_heads(self) -> tuple[str, ...]: ...

    async def immutable_trigger_rejections(self) -> set[tuple[str, str]]: ...

    async def revision_cas_race(self) -> tuple[bool, bool, int]: ...

    async def actor_lock_contention_errno(self) -> int: ...


CasApply = Callable[..., Awaitable[bool]]
GetUserById = Callable[..., Awaitable[object | None]]


def _sha(value: str) -> str:
    normalized = value.strip().casefold()
    if _SHA_PATTERN.fullmatch(normalized) is None:
        raise ManualHelperError("tested SHA must be complete 40-character hex")
    return normalized


def load_mysql_url(env: Mapping[str, str]) -> URL:
    """Load the sole accepted URL without ever rendering its password."""
    raw = env.get(MYSQL_URL_ENV)
    if not raw:
        raise ManualHelperError(f"{MYSQL_URL_ENV} is required")
    try:
        database_url = make_url(raw)
    except Exception:
        raise ManualHelperError("invalid W008 MySQL configuration") from None

    if database_url.drivername != "mysql+aiomysql":
        raise ManualHelperError("W008 acceptance requires MySQL with aiomysql")
    if not database_url.username or database_url.username.casefold() == "root":
        raise ManualHelperError("W008 MySQL principal must be a non-root app user")
    if not _is_loopback(database_url.host):
        raise ManualHelperError("W008 MySQL host must be loopback")
    if (
        not database_url.database
        or _MYSQL_DATABASE_PATTERN.fullmatch(database_url.database) is None
    ):
        raise ManualHelperError("W008 MySQL database name is not grant-safe")
    return database_url


def _is_loopback(host: str | None) -> bool:
    if host is None:
        return False
    normalized = host.strip().casefold().rstrip(".")
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _principal_grants_are_schema_scoped(
    *,
    principal: str,
    expected_username: str,
    expected_database: str,
    grants: tuple[str, ...],
) -> bool:
    """Accept only USAGE plus grants on the one documented app schema."""
    username, separator, _host = principal.partition("@")
    if (
        separator != "@"
        or username != expected_username
        or not username
        or username.casefold() == "root"
        or not expected_database
        or not grants
    ):
        return False

    escaped_database = (
        expected_database.replace("\\", "\\\\")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("`", "``")
    )
    allowed_schema_scope = f" ON `{escaped_database}`.* TO "
    for grant in grants:
        normalized = " ".join(grant.split())
        if " WITH GRANT OPTION" in normalized:
            return False
        if normalized.startswith("GRANT USAGE ON *.* TO "):
            continue
        if normalized.startswith("GRANT ") and allowed_schema_scope in normalized:
            continue
        return False
    return True


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ("git", *args),
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise ManualHelperError("git verification failed")
    return result.stdout


def require_isolated_worktree(tested_sha: str, *, clean: bool = True) -> Path:
    """Require a clean linked worktree whose exact HEAD is being reported."""
    expected = _sha(tested_sha)
    root = Path.cwd().resolve()
    top = Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    try:
        git_entry = (root / ".git").lstat()
    except OSError:
        raise ManualHelperError("run from a linked worktree root") from None
    if root != top or not stat.S_ISREG(git_entry.st_mode):
        raise ManualHelperError("run from a linked worktree root")
    actual = _git(root, "rev-parse", "HEAD").decode().strip().casefold()
    if actual != expected:
        raise ManualHelperError("HEAD does not match tested SHA")
    for protected_name in (
        ".env",
        ".kindergarten_secrets",
        ".kindergarten_secrets.lock",
    ):
        try:
            (root / protected_name).lstat()
        except FileNotFoundError:
            continue
        except OSError:
            raise ManualHelperError("cannot inspect protected runtime entry") from None
        raise ManualHelperError("refusing protected runtime entry")
    if clean and _git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ):
        raise ManualHelperError("isolated worktree is not clean")
    return root


def _activate_worktree_imports(root: Path) -> None:
    """Make the verified worktree authoritative for delayed app imports."""
    verified = str(root.resolve())
    sys.path[:] = [
        verified,
        *(
            entry
            for entry in sys.path
            if str(Path(entry or Path.cwd()).resolve()) != verified
        ),
    ]


async def validate_mysql8(backend: AcceptanceBackend) -> None:
    """Accept Oracle MySQL major version 8 and reject MariaDB explicitly."""
    version = (await backend.server_version()).strip()
    if "mariadb" in version.casefold() or _MYSQL_8_PATTERN.match(version) is None:
        raise ManualHelperError("W008 acceptance requires a real MySQL 8 server")


async def run_live_acceptance(
    backend: AcceptanceBackend,
    *,
    tested_sha: str,
) -> dict[str, object]:
    """Run each independent live check once and emit only sanitized evidence."""
    normalized_sha = _sha(tested_sha)
    await validate_mysql8(backend)

    if await backend.app_principal_is_schema_scoped() is not True:
        raise ManualHelperError("MySQL principal is not schema-scoped")

    heads = await backend.current_alembic_heads()
    if heads != (CURRENT_HEAD,):
        raise ManualHelperError("live database is not at the exact current head")

    trigger_rejections = await backend.immutable_trigger_rejections()
    if trigger_rejections != set(TRIGGER_CASES):
        raise ManualHelperError("append-only trigger evidence is incomplete")

    first_cas, second_cas, revision = await backend.revision_cas_race()
    cas_results = [first_cas, second_cas]
    if (
        any(type(result) is not bool for result in cas_results)
        or sorted(cas_results) != [False, True]
        or revision != 2
    ):
        raise ManualHelperError("revision CAS evidence is incomplete")

    lock_errno = await backend.actor_lock_contention_errno()
    if lock_errno != 1205:
        raise ManualHelperError("administrator row-lock evidence is incomplete")

    return {
        "tested_code_sha": normalized_sha,
        "head": CURRENT_HEAD,
        "trigger_rejections": len(trigger_rejections),
        "cas": sorted(cas_results),
        "revision": revision,
        "admin_lock_errno": lock_errno,
    }


class LiveMySQLBackend:
    """Real MySQL implementation of every W008 acceptance check."""

    def __init__(
        self,
        database_url: URL,
        *,
        cas_apply: CasApply,
        get_user_by_id: GetUserById,
    ) -> None:
        self._expected_username = database_url.username or ""
        self._expected_database = database_url.database or ""
        self._engine = create_async_engine(
            database_url,
            poolclass=NullPool,
            pool_pre_ping=False,
        )
        self._sessions = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        self._cas_apply = cas_apply
        self._get_user_by_id = get_user_by_id
        self._actor_plan_seeded = False

    async def dispose(self) -> None:
        await self._engine.dispose()

    async def server_version(self) -> str:
        try:
            async with self._sessions() as session:
                result = await session.execute(text("SELECT VERSION()"))
                return str(result.scalar_one())
        except Exception:
            raise ManualHelperError("MySQL version check failed") from None

    async def app_principal_is_schema_scoped(self) -> bool:
        """Reject root, global privileges, roles and cross-schema grants."""
        try:
            async with self._sessions() as session:
                principal = str(
                    (await session.execute(text("SELECT CURRENT_USER()"))).scalar_one()
                )
                grant_rows = (await session.execute(text("SHOW GRANTS"))).all()
            return _principal_grants_are_schema_scoped(
                principal=principal,
                expected_username=self._expected_username,
                expected_database=self._expected_database,
                grants=tuple(str(row[0]) for row in grant_rows),
            )
        except Exception:
            raise ManualHelperError("MySQL principal check failed") from None

    async def current_alembic_heads(self) -> tuple[str, ...]:
        try:
            async with self._sessions() as session:
                result = await session.execute(
                    text("SELECT version_num FROM alembic_version ORDER BY version_num")
                )
                return tuple(str(value) for value in result.scalars())
        except Exception:
            raise ManualHelperError("MySQL migration-head check failed") from None

    async def immutable_trigger_rejections(self) -> set[tuple[str, str]]:
        try:
            trigger_rows = await self._trigger_rows()
            if trigger_rows != _EXPECTED_TRIGGER_ROWS:
                raise ManualHelperError("MySQL trigger inventory is not exact")
            row_ids = await self._insert_synthetic_evidence()
            before = await self._evidence_digest()
            rejected: set[tuple[str, str]] = set()
            for table_name, operation in sorted(TRIGGER_CASES):
                await self._assert_trigger_rejection(
                    table_name,
                    operation,
                    row_id=row_ids[table_name],
                )
                rejected.add((table_name, operation))
            after = await self._evidence_digest()
            if before != after:
                raise ManualHelperError("append-only evidence rows changed")
            return rejected
        except ManualHelperError:
            raise
        except Exception:
            raise ManualHelperError("MySQL trigger acceptance failed") from None

    async def _trigger_rows(self) -> frozenset[tuple[str, str, str, str]]:
        async with self._sessions() as session:
            result = await session.execute(
                text(
                    "SELECT TRIGGER_NAME, EVENT_OBJECT_TABLE, "
                    "EVENT_MANIPULATION, ACTION_TIMING "
                    "FROM information_schema.TRIGGERS "
                    "WHERE TRIGGER_SCHEMA = DATABASE() "
                    "AND EVENT_OBJECT_TABLE IN "
                    "('daily_plan_operation_version', 'agent_write_audit')"
                )
            )
            return frozenset(
                (
                    str(row[0]),
                    str(row[1]),
                    str(row[2]).upper(),
                    str(row[3]).upper(),
                )
                for row in result.all()
            )

    async def _insert_synthetic_evidence(self) -> dict[str, int]:
        confirmation_id = str(uuid.uuid4())
        patch_id = str(uuid.uuid4())
        operation_id = str(uuid.uuid4())
        turn_id = str(uuid.uuid4())
        patch_sha256 = _token_digest("w008-patch")
        snapshot_sha256 = _token_digest("w008-snapshot")
        nonce_sha256 = _token_digest("w008-nonce")
        session_sha256 = _token_digest("w008-session")
        async with self._sessions() as session:
            try:
                version_result = await session.execute(
                    text(
                        "INSERT INTO daily_plan_operation_version "
                        "(tenant_id, user_id, daily_plan_id, confirmation_id, "
                        "patch_id, patch_sha256, operation_id, turn_id, "
                        "before_revision, field_paths_json, snapshot_json, "
                        "snapshot_sha256, created_at) VALUES "
                        "(:tenant_id, :user_id, :daily_plan_id, :confirmation_id, "
                        ":patch_id, :patch_sha256, :operation_id, :turn_id, 1, "
                        ":field_paths_json, :snapshot_json, :snapshot_sha256, "
                        "UTC_TIMESTAMP(6))"
                    ),
                    {
                        "tenant_id": _TENANT_ID,
                        "user_id": _USER_ID,
                        "daily_plan_id": _PLAN_ID,
                        "confirmation_id": confirmation_id,
                        "patch_id": patch_id,
                        "patch_sha256": patch_sha256,
                        "operation_id": operation_id,
                        "turn_id": turn_id,
                        "field_paths_json": '["activity_goal"]',
                        "snapshot_json": "{}",
                        "snapshot_sha256": snapshot_sha256,
                    },
                )
                version_id = int(getattr(version_result, "lastrowid"))
                audit_result = await session.execute(
                    text(
                        "INSERT INTO agent_write_audit "
                        "(confirmation_id, nonce_sha256, session_sha256, "
                        "tenant_id, user_id, daily_plan_id, patch_id, "
                        "patch_sha256, operation_id, turn_id, field_paths_json, "
                        "before_version_id, before_revision, after_revision, "
                        "action, created_at) VALUES "
                        "(:confirmation_id, :nonce_sha256, :session_sha256, "
                        ":tenant_id, :user_id, :daily_plan_id, :patch_id, "
                        ":patch_sha256, :operation_id, :turn_id, "
                        ":field_paths_json, :before_version_id, 1, 2, "
                        ":action, UTC_TIMESTAMP(6))"
                    ),
                    {
                        "confirmation_id": confirmation_id,
                        "nonce_sha256": nonce_sha256,
                        "session_sha256": session_sha256,
                        "tenant_id": _TENANT_ID,
                        "user_id": _USER_ID,
                        "daily_plan_id": _PLAN_ID,
                        "patch_id": patch_id,
                        "patch_sha256": patch_sha256,
                        "operation_id": operation_id,
                        "turn_id": turn_id,
                        "field_paths_json": '["activity_goal"]',
                        "before_version_id": version_id,
                        "action": "daily_plan.apply_confirmed_patch",
                    },
                )
                audit_id = int(getattr(audit_result, "lastrowid"))
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        return {
            "daily_plan_operation_version": version_id,
            "agent_write_audit": audit_id,
        }

    async def _evidence_digest(self) -> str:
        summary: dict[str, list[dict[str, object]]] = {}
        async with self._sessions() as session:
            for table_name in (
                "daily_plan_operation_version",
                "agent_write_audit",
            ):
                result = await session.execute(
                    text(f"SELECT * FROM {table_name} ORDER BY id")
                )
                summary[table_name] = [dict(row) for row in result.mappings().all()]
        encoded = json.dumps(
            summary,
            default=_json_scalar,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    async def _assert_trigger_rejection(
        self,
        table_name: str,
        operation: str,
        *,
        row_id: int,
    ) -> None:
        if (table_name, operation) not in TRIGGER_CASES:
            raise ManualHelperError("invalid trigger acceptance case")
        if operation == "UPDATE":
            statement = text(
                f"UPDATE {table_name} SET patch_id = :patch_id WHERE id = :row_id"
            )
            parameters = {"patch_id": str(uuid.uuid4()), "row_id": row_id}
        else:
            statement = text(f"DELETE FROM {table_name} WHERE id = :row_id")
            parameters = {"row_id": row_id}

        async with self._sessions() as session:
            try:
                await session.execute(statement, parameters)
            except DBAPIError as exc:
                await session.rollback()
                if _mysql_errno(exc) != 1644:
                    raise ManualHelperError(
                        "append-only trigger returned an unexpected errno"
                    ) from None
                return
            except Exception:
                await session.rollback()
                raise ManualHelperError(
                    "append-only trigger was not observed"
                ) from None
            await session.rollback()
        raise ManualHelperError("append-only trigger allowed a mutation")

    async def revision_cas_race(self) -> tuple[bool, bool, int]:
        try:
            await self._ensure_actor_and_plan()

            async def contender() -> bool:
                async with self._sessions() as session:
                    try:
                        updated = await self._cas_apply(
                            session,
                            tenant_id=_TENANT_ID,
                            user_id=_USER_ID,
                            daily_plan_id=_PLAN_ID,
                            expected_revision=1,
                            field_values={"activity_goal": "w008-synthetic-goal"},
                            updated_at=datetime.now(timezone.utc),
                        )
                        await session.commit()
                        return updated
                    except Exception:
                        await session.rollback()
                        raise

            first, second = await asyncio.gather(contender(), contender())
            async with self._sessions() as session:
                result = await session.execute(
                    text(
                        "SELECT revision FROM daily_plan "
                        "WHERE tenant_id = :tenant_id AND user_id = :user_id "
                        "AND id = :daily_plan_id"
                    ),
                    {
                        "tenant_id": _TENANT_ID,
                        "user_id": _USER_ID,
                        "daily_plan_id": _PLAN_ID,
                    },
                )
                revision = int(result.scalar_one())
            return first, second, revision
        except Exception:
            raise ManualHelperError("MySQL revision CAS acceptance failed") from None

    async def _ensure_actor_and_plan(self) -> None:
        if self._actor_plan_seeded:
            return
        async with self._sessions() as session:
            try:
                await session.execute(
                    text(
                        "INSERT INTO `user` "
                        "(id, tenant_id, username, hashed_password, role, "
                        "is_active, display_name, created_at, updated_at) VALUES "
                        "(:id, :tenant_id, :username, :hashed_password, "
                        "'sys_admin', TRUE, :display_name, "
                        "UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))"
                    ),
                    {
                        "id": _USER_ID,
                        "tenant_id": _TENANT_ID,
                        "username": "w008-synthetic-admin",
                        "hashed_password": "w008-synthetic-hash",
                        "display_name": "W008 Synthetic Admin",
                    },
                )
                await session.execute(
                    text(
                        "INSERT INTO daily_plan "
                        "(id, tenant_id, user_id, revision, plan_date, "
                        "week_number, weekday_cn, grade, class_name, "
                        "activity_goal, created_at, updated_at) VALUES "
                        "(:id, :tenant_id, :user_id, 1, '2099-08-08', 1, "
                        ":weekday_cn, :grade, :class_name, :activity_goal, "
                        "UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))"
                    ),
                    {
                        "id": _PLAN_ID,
                        "tenant_id": _TENANT_ID,
                        "user_id": _USER_ID,
                        "weekday_cn": "周一",
                        "grade": "大班",
                        "class_name": "合成班",
                        "activity_goal": "w008-synthetic-before",
                    },
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        self._actor_plan_seeded = True

    async def actor_lock_contention_errno(self) -> int:
        try:
            await self._ensure_actor_and_plan()
            errno = await self._observe_actor_lock_timeout()
            await self._assert_actor_lock_released()
            return errno
        except ManualHelperError:
            raise
        except Exception:
            raise ManualHelperError("MySQL actor-lock acceptance failed") from None

    async def _observe_actor_lock_timeout(self) -> int:
        async with self._sessions() as holder:
            held = await self._get_user_by_id(
                holder,
                tenant_id=_TENANT_ID,
                user_id=_USER_ID,
                for_update=True,
            )
            if held is None:
                raise ManualHelperError("synthetic administrator is unavailable")
            try:
                async with self._sessions() as contender:
                    await contender.execute(
                        text("SET SESSION innodb_lock_wait_timeout = 1")
                    )
                    try:
                        await self._get_user_by_id(
                            contender,
                            tenant_id=_TENANT_ID,
                            user_id=_USER_ID,
                            for_update=True,
                        )
                    except DBAPIError as exc:
                        await contender.rollback()
                        errno = _mysql_errno(exc)
                    else:
                        await contender.rollback()
                        raise ManualHelperError(
                            "administrator contender unexpectedly acquired the lock"
                        )
            finally:
                await holder.rollback()
        if errno != 1205:
            raise ManualHelperError("administrator contention errno was not 1205")
        return errno

    async def _assert_actor_lock_released(self) -> None:
        async with self._sessions() as session:
            try:
                actor = await self._get_user_by_id(
                    session,
                    tenant_id=_TENANT_ID,
                    user_id=_USER_ID,
                    for_update=True,
                )
                if actor is None:
                    raise ManualHelperError(
                        "synthetic administrator disappeared after lock release"
                    )
            finally:
                await session.rollback()


def _token_digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _json_scalar(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _mysql_errno(exc: DBAPIError) -> int | None:
    original: Any = exc.orig
    args = getattr(original, "args", ())
    if args and isinstance(args[0], int):
        return args[0]
    return None


def _install_nonpersisting_app_config() -> None:
    """Provide the model import chain with a file-free synthetic config.

    Importing either repository normally imports ``app.core.database`` and the
    process-wide Settings singleton.  That singleton always creates its POSIX
    lifecycle lock in the current worktree.  The MySQL acceptance only needs
    the shared declarative Base; its live sessions are bound to the dedicated
    URL below, so an in-memory synthetic database setting is sufficient and
    avoids touching configuration files or unrelated ``DATABASE_URL`` state.
    """
    if "app.core.config" in sys.modules:
        raise ManualHelperError("application config was imported before the W008 gate")
    module = ModuleType("app.core.config")
    setattr(
        module,
        "settings",
        SimpleNamespace(DATABASE_URL="sqlite+aiosqlite:///:memory:"),
    )
    sys.modules["app.core.config"] = module


async def _run_real_backend(database_url: URL, tested_sha: str) -> dict[str, object]:
    _install_nonpersisting_app_config()
    from app.repository.confirmed_write_repository import (
        cas_apply_daily_plan_fields,
    )
    from app.repository.user_repository import get_user_by_id

    backend = LiveMySQLBackend(
        database_url,
        cas_apply=cas_apply_daily_plan_fields,
        get_user_by_id=get_user_by_id,
    )
    try:
        return await run_live_acceptance(backend, tested_sha=tested_sha)
    finally:
        await backend.dispose()


def _launch_live(tested_sha: str, env: Mapping[str, str]) -> dict[str, object]:
    database_url = load_mysql_url(env)
    return asyncio.run(_run_real_backend(database_url, tested_sha))


def prepare_run(args: argparse.Namespace) -> dict[str, object]:
    """Cross into application imports only after the fixed-SHA gate."""
    root = require_isolated_worktree(args.tested_sha, clean=True)
    _activate_worktree_imports(root)
    return _launch_live(_sha(args.tested_sha), os.environ)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one sanitized W008 live-MySQL acceptance",
    )
    parser.add_argument("--tested-sha", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = prepare_run(args)
    except Exception:
        print("W008 MySQL acceptance failed", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
