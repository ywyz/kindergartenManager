"""W008 fixed-SHA browser fault-injection acceptance helper.

Application and NiceGUI imports are deliberately delayed until the linked
worktree gate succeeds.  ``writer_session_factory`` wraps only the confirmed
writer's sessions; ordinary application sessions remain untouched.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
from threading import Lock
from typing import Any

from sqlalchemy.exc import DisconnectionError
from sqlalchemy.sql.dml import Update


_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
_MOCK_ENCRYPTION_KEY = "f009-fictional-encryption-key-do-not-use"
_MOCK_JWT_SECRET = "f009-fictional-jwt-secret-do-not-use"
_MOCK_HOLIDAY_URL = "http://127.0.0.1:18081/holiday/info/"
_MOCK_PORT = 18081


class ManualHelperError(RuntimeError):
    """A content-free, fail-closed launcher refusal."""


class FaultPoint(str, Enum):
    """The exact transaction stages accepted by the W008 browser matrix."""

    AFTER_VERSION = "after_version"
    AFTER_CAS = "after_cas"
    AFTER_AUDIT = "after_audit"
    KNOWN_BEFORE_COMMIT = "known_before_commit"
    UNKNOWN_BEFORE_COMMIT = "unknown_before_commit"
    UNKNOWN_AFTER_COMMIT = "unknown_after_commit"


@dataclass(slots=True)
class FaultCounters:
    """Closed public-operation counts used to prove retry freedom."""

    issue: int = 0
    apply: int = 0
    reconcile: int = 0


class _CountingWriteService:
    """Count the three frozen public calls without exposing their arguments."""

    def __init__(
        self,
        delegate: Any,
        *,
        counters: FaultCounters,
        tested_sha: str,
        fault: FaultPoint | None,
    ) -> None:
        self._delegate = delegate
        self._counters = counters
        self._tested_sha = tested_sha
        self._fault = fault.value if fault is not None else "none"

    def _record(self, name: str) -> None:
        value = getattr(self._counters, name) + 1
        if value > 1:
            raise ManualHelperError("automatic retry detected")
        setattr(self._counters, name, value)
        print(
            json.dumps(
                {
                    "event": "w008_writer_call",
                    "tested_code_sha": self._tested_sha,
                    "fault": self._fault,
                    "counters": {
                        "issue": self._counters.issue,
                        "apply": self._counters.apply,
                        "reconcile": self._counters.reconcile,
                    },
                },
                ensure_ascii=True,
                sort_keys=True,
            ),
            flush=True,
        )

    async def issue_confirmation(
        self,
        ui_session: Any,
        patch: Any,
        *,
        expected_revision: int,
    ) -> Any:
        self._record("issue")
        return await self._delegate.issue_confirmation(
            ui_session,
            patch,
            expected_revision=expected_revision,
        )

    async def apply(self, ui_session: Any, confirmation_id: Any) -> Any:
        self._record("apply")
        return await self._delegate.apply(ui_session, confirmation_id)

    async def reconcile(self, ui_session: Any, confirmation_id: Any) -> Any:
        self._record("reconcile")
        return await self._delegate.reconcile(ui_session, confirmation_id)


class _OneShotFault:
    def __init__(self, fault: FaultPoint) -> None:
        self.fault = fault
        self._fired = False
        self._lock = Lock()

    def fire(self, candidate: FaultPoint) -> bool:
        if candidate is not self.fault:
            return False
        with self._lock:
            if self._fired:
                return False
            self._fired = True
            return True


def _table_name(value: object) -> str | None:
    table = getattr(value, "__table__", None)
    name = getattr(table, "name", None)
    return name if type(name) is str else None


class _WriterSession:
    """Transparent session proxy with one post-stage fault."""

    def __init__(self, session: Any, injector: _OneShotFault) -> None:
        self._session = session
        self._injector = injector
        self._pending_tables: set[str] = set()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)

    async def __aenter__(self) -> _WriterSession:
        enter = getattr(self._session, "__aenter__")
        entered = await enter()
        self._session = entered
        return self

    async def __aexit__(self, *args: object) -> object:
        return await getattr(self._session, "__aexit__")(*args)

    def add(self, value: object) -> None:
        self._session.add(value)
        name = _table_name(value)
        if name is not None:
            self._pending_tables.add(name)

    async def flush(self) -> object:
        result = await self._session.flush()
        tables = frozenset(self._pending_tables)
        self._pending_tables.clear()
        candidate = None
        if "daily_plan_operation_version" in tables:
            candidate = FaultPoint.AFTER_VERSION
        elif "agent_write_audit" in tables:
            candidate = FaultPoint.AFTER_AUDIT
        if candidate is not None and self._injector.fire(candidate):
            raise RuntimeError("injected write fault")
        return result

    async def execute(
        self, statement: object, *args: object, **kwargs: object
    ) -> object:
        result = await self._session.execute(statement, *args, **kwargs)
        table = getattr(statement, "table", None)
        if (
            isinstance(statement, Update)
            and getattr(table, "name", None) == "daily_plan"
            and self._injector.fire(FaultPoint.AFTER_CAS)
        ):
            raise RuntimeError("injected write fault")
        return result

    async def commit(self) -> object:
        if self._injector.fire(FaultPoint.KNOWN_BEFORE_COMMIT):
            raise RuntimeError("injected write fault")
        if self._injector.fire(FaultPoint.UNKNOWN_BEFORE_COMMIT):
            raise DisconnectionError("injected write disconnect")
        result = await self._session.commit()
        if self._injector.fire(FaultPoint.UNKNOWN_AFTER_COMMIT):
            raise DisconnectionError("injected write disconnect")
        return result


class _WriterSessionFactory:
    def __init__(self, base_factory: Any, fault: FaultPoint) -> None:
        self._base_factory = base_factory
        self._injector = _OneShotFault(fault)

    def __call__(self) -> _WriterSession:
        return _WriterSession(self._base_factory(), self._injector)


def writer_session_factory(base_factory: Any, fault: FaultPoint) -> Any:
    """Return a writer-only factory sharing one process-local injection."""
    if not callable(base_factory) or type(fault) is not FaultPoint:
        raise TypeError("invalid writer session factory")
    return _WriterSessionFactory(base_factory, fault)


def _sha(value: object) -> str:
    if type(value) is not str:
        raise ManualHelperError("tested SHA must be complete 40-character hex")
    normalized = value.strip().casefold()
    if _SHA_PATTERN.fullmatch(normalized) is None:
        raise ManualHelperError("tested SHA must be complete 40-character hex")
    return normalized


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
    """Require a clean linked worktree at the exact reported SHA."""
    expected = _sha(tested_sha)
    root = Path.cwd().resolve()
    top = Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    try:
        git_entry = (root / ".git").lstat()
    except OSError:
        raise ManualHelperError("run from a linked worktree root") from None
    if root != top or not stat.S_ISREG(git_entry.st_mode):
        raise ManualHelperError("run from a linked worktree root")
    if _git(root, "rev-parse", "HEAD").decode().strip().casefold() != expected:
        raise ManualHelperError("HEAD does not match tested SHA")
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
    verified = str(root.resolve())
    sys.path[:] = [
        verified,
        *(
            entry
            for entry in sys.path
            if str(Path(entry or Path.cwd()).resolve()) != verified
        ),
    ]


def _database_path(raw: str) -> Path:
    """Accept one existing 0600 SQLite file in an owner-only W008 run dir."""
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    absolute = candidate.absolute()
    try:
        metadata = absolute.lstat()
        parent_metadata = absolute.parent.lstat()
    except OSError:
        raise ManualHelperError("cannot inspect W008 SQLite database") from None
    if absolute.resolve() != absolute or not stat.S_ISREG(metadata.st_mode):
        raise ManualHelperError("W008 SQLite database must be an ordinary file")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ManualHelperError("W008 SQLite database must be mode 0600")
    if (
        absolute.parent.parent != Path("/tmp")
        or not absolute.parent.name.startswith("km-w008.")
        or not stat.S_ISDIR(parent_metadata.st_mode)
        or parent_metadata.st_uid != os.getuid()
        or stat.S_IMODE(parent_metadata.st_mode) & 0o077
    ):
        raise ManualHelperError("database must be inside an owner-only /tmp/km-w008.*")
    if absolute.parent.resolve() != absolute.parent:
        raise ManualHelperError("W008 run directory must not be a symbolic link")
    return absolute


def _require_mock_protected_state(root: Path) -> None:
    for name in (".env", ".kindergarten_secrets"):
        try:
            (root / name).lstat()
        except FileNotFoundError:
            continue
        except OSError:
            raise ManualHelperError("cannot inspect protected runtime entry") from None
        raise ManualHelperError("refusing protected runtime entry")
    lock = root / ".kindergarten_secrets.lock"
    try:
        metadata = lock.lstat()
    except OSError:
        raise ManualHelperError("synthetic secrets lock must already exist") from None
    if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ManualHelperError("synthetic secrets lock must be an ordinary 0600 file")


def _port_free(port: int) -> bool:
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _port_listening(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.25)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def _launch_product_app(args: argparse.Namespace) -> None:
    """Compose the real page with a page-local, writer-only acceptance service."""
    tested_sha = _sha(args.tested_sha)
    database = _database_path(args.database)
    root = Path.cwd().resolve()
    _require_mock_protected_state(root)
    if type(args.ttl) is not int or not 1 <= args.ttl <= 300:
        raise ManualHelperError("confirmation TTL must be between 1 and 300 seconds")
    if type(args.port) is not int or not 1024 <= args.port <= 65535:
        raise ManualHelperError("application port is invalid")
    if not _port_free(args.port) or not _port_listening(_MOCK_PORT):
        raise ManualHelperError("required loopback port state is not ready")
    fault = FaultPoint(args.fault) if args.fault is not None else None

    os.environ.update(
        DATABASE_URL=f"sqlite+aiosqlite:///{database.as_posix()}",
        ENCRYPTION_KEY=_MOCK_ENCRYPTION_KEY,
        JWT_SECRET=_MOCK_JWT_SECRET,
        HOLIDAY_API_URL=_MOCK_HOLIDAY_URL,
        PORT=str(args.port),
    )

    from app.core.database import AsyncSessionLocal
    from app.service.agent import confirmation_flow
    from app.service.agent.confirmation_flow import (
        create_daily_plan_patch_confirmation_controller,
    )
    from app.service.agent.confirmed_write import ConfirmedDailyPlanWriteService

    def w008_create_daily_plan_patch_confirmation_controller(
        *,
        agent_controller: Any,
    ) -> Any:
        session_factory = (
            AsyncSessionLocal
            if fault is None
            else writer_session_factory(AsyncSessionLocal, fault)
        )
        writer = ConfirmedDailyPlanWriteService(
            session_factory=session_factory,
            confirmation_ttl=timedelta(seconds=args.ttl),
        )
        counted_writer = _CountingWriteService(
            writer,
            counters=FaultCounters(),
            tested_sha=tested_sha,
            fault=fault,
        )
        return create_daily_plan_patch_confirmation_controller(
            agent_controller=agent_controller,
            write_service=counted_writer,
        )

    confirmation_flow.create_daily_plan_patch_confirmation_controller = (
        w008_create_daily_plan_patch_confirmation_controller
    )

    import app.main  # noqa: F401 - registers pages after the factory patch
    from nicegui import app, ui

    from app.api import create_api_router
    from app.auth.middleware import AuthMiddleware
    from app.core.bootstrap import run_bootstrap
    from app.core.config import settings
    from app.core.startup import run_startup_migrations

    run_startup_migrations()
    app.on_startup(run_bootstrap)
    app.add_middleware(AuthMiddleware)
    app.include_router(create_api_router())
    ui.run(
        host="127.0.0.1",
        port=args.port,
        title="幼儿园教学管理系统 · W008",
        storage_secret=settings.JWT_SECRET,
        reload=False,
        show=False,
        favicon="📚",
    )


def prepare_run(args: argparse.Namespace) -> object:
    root = require_isolated_worktree(args.tested_sha, clean=True)
    _activate_worktree_imports(root)
    return _launch_product_app(args)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tested-sha", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--fault", choices=tuple(item.value for item in FaultPoint))
    parser.add_argument("--ttl", type=int, default=300)
    parser.add_argument("--port", type=int, default=18080)
    return parser


def main() -> None:
    try:
        prepare_run(_parser().parse_args())
    except ManualHelperError as exc:
        print(f"W008 browser helper refused: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
