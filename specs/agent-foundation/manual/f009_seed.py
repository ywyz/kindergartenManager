"""F009 isolated seed, loopback launcher, and redacted logical snapshots.

No application module is imported until fixed-SHA linked-worktree checks pass
and explicit synthetic process configuration has been installed.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import sqlite3
import stat
import subprocess
import sys
import tempfile


MOCK_API_KEY = "f009-fictional-text-key-do-not-use"
MOCK_ENCRYPTION_KEY = "f009-fictional-encryption-key-do-not-use"
MOCK_JWT_SECRET = "f009-fictional-jwt-secret-do-not-use"
MOCK_MODEL = "f009-mock-model"
MOCK_API_BASE_URL = "http://127.0.0.1:18081/v1"
MOCK_HOLIDAY_URL = "http://127.0.0.1:18081/holiday/info/"
APP_PORT = 18080
MOCK_PORT = 18081
PLAN_DATES = (date(2026, 9, 7), date(2026, 9, 8))
_MAX_UI_BYTES = 1_048_576
_PLAN_FIELDS = {
    "activity_goal": "目标",
    "activity_prep": "准备",
    "activity_key": "重点",
    "activity_difficult": "难点",
    "activity_process_original": "过程原文",
    "activity_process_adapted": "过程建议",
    "morning_activity": "晨间活动",
    "indoor_area": "区域活动",
    "outdoor_activity": "户外活动",
    "morning_talk_topic": "谈话",
    "morning_talk_questions": "问题",
    "daily_reflection": "反思",
}
_UI_FIELDS = frozenset(_PLAN_FIELDS) - {"morning_talk_questions"}
_PROTECTED_NAMES = (
    ".env",
    ".kindergarten_secrets",
    ".kindergarten_secrets.lock",
)


class ManualHelperError(RuntimeError):
    """A fail-closed refusal with no configuration contents."""


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


def _sha(value: str) -> str:
    value = value.strip().lower()
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise ManualHelperError("tested SHA must be complete 40-character hex")
    return value


def _lstat(path: Path) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ManualHelperError(f"cannot inspect runtime entry: {path.name}") from exc


def _secret_safe(path: Path, *, absent: bool) -> None:
    metadata = _lstat(path)
    if metadata is None:
        return
    if absent:
        raise ManualHelperError(f"refusing existing runtime entry: {path.name}")
    if not stat.S_ISREG(metadata.st_mode):
        raise ManualHelperError("secrets entry is not an ordinary file")
    if os.name == "posix" and stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ManualHelperError("secrets file mode is not 0600")


def require_isolated_worktree(
    tested_sha: str,
    *,
    secrets_absent: bool,
    lock_absent: bool,
    clean: bool = True,
) -> Path:
    """Verify the linked fixed-SHA root before any application import."""
    expected = _sha(tested_sha)
    root = Path.cwd().resolve()
    top = Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    git_entry = _lstat(root / ".git")
    if root != top or git_entry is None or not stat.S_ISREG(git_entry.st_mode):
        raise ManualHelperError("run from a linked worktree root")
    if _git(root, "rev-parse", "HEAD").decode().strip().lower() != expected:
        raise ManualHelperError("HEAD does not match tested SHA")
    if _lstat(root / ".env") is not None:
        raise ManualHelperError("refusing existing runtime entry: .env")
    secret = root / ".kindergarten_secrets"
    lock = root / ".kindergarten_secrets.lock"
    _secret_safe(secret, absent=secrets_absent)
    _secret_safe(lock, absent=lock_absent)
    if clean:
        status = _git(
            root,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        )
        records = {record for record in status.split(b"\0") if record}
        allowed = set()
        if not secrets_absent:
            allowed.add(b"?? .kindergarten_secrets")
        if not lock_absent:
            allowed.add(b"?? .kindergarten_secrets.lock")
        if not records <= allowed:
            raise ManualHelperError("isolated worktree is not clean")
    return root


def _secure_run_dir(path: Path) -> None:
    metadata = _lstat(path)
    if metadata is None or not stat.S_ISDIR(metadata.st_mode):
        raise ManualHelperError("temporary run directory does not exist")
    if os.name == "posix" and (
        metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077
    ):
        raise ManualHelperError("temporary run directory must be owner-only")


def _database_path(raw: str, *, exists: bool) -> Path:
    path = Path(raw).expanduser().resolve()
    if path.parent.parent != Path("/tmp") or not path.parent.name.startswith(
        "km-f009."
    ):
        raise ManualHelperError("database must be inside /tmp/km-f009.*")
    _secure_run_dir(path.parent)
    entry = _lstat(path)
    if exists and (entry is None or not stat.S_ISREG(entry.st_mode)):
        raise ManualHelperError("SQLite database is not an ordinary file")
    if not exists and entry is not None:
        raise ManualHelperError("refusing to seed an existing database entry")
    return path


def _reserve_database(path: Path) -> None:
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    if os.name == "posix" and not no_follow:
        raise ManualHelperError("platform lacks safe no-follow database creation")
    try:
        fd = os.open(
            path,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | no_follow
            | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        os.close(fd)
    except OSError as exc:
        raise ManualHelperError("cannot reserve temporary SQLite database") from exc


def _synthetic_env(database: Path, *, mock: bool) -> None:
    os.environ.update(
        DATABASE_URL=f"sqlite+aiosqlite:///{database.as_posix()}",
        ENCRYPTION_KEY=MOCK_ENCRYPTION_KEY,
        JWT_SECRET=MOCK_JWT_SECRET,
        PORT=str(APP_PORT),
    )
    if mock:
        os.environ["HOLIDAY_API_URL"] = MOCK_HOLIDAY_URL


async def _seed_rows(*, mock: bool) -> None:
    from sqlalchemy import select

    from app.core.bootstrap import ensure_default_user
    from app.core.database import AsyncSessionLocal
    from app.core.models.user import User
    from app.repository.ai_key_repository import save_ai_key
    from app.repository.class_repository import upsert_class_config
    from app.repository.daily_plan_repository import save_daily_plan
    from app.repository.semester_repository import upsert_active_semester

    async with AsyncSessionLocal() as session:
        await ensure_default_user(session)
        user = (
            await session.execute(
                select(User).where(User.tenant_id == 1, User.username == "admin")
            )
        ).scalar_one()
        if user.id != 1:
            raise ManualHelperError("synthetic default user id is not 1")
        await upsert_class_config(
            session,
            1,
            1,
            "大班",
            "F009合成班",
            "F009 合成积木区、阅读区",
            "F009 合成户外观察区",
            "F009合成教师",
        )
        await upsert_active_semester(
            session,
            1,
            1,
            "F009 合成学期",
            date(2026, 9, 1),
            date(2027, 1, 31),
        )
        for plan_date, suffix in zip(PLAN_DATES, ("A", "B"), strict=True):
            await save_daily_plan(
                session,
                1,
                1,
                plan_date,
                2,
                "周一" if suffix == "A" else "周二",
                "大班",
                "F009合成班",
                **{
                    field: f"F009 合成{label} {suffix}"
                    for field, label in _PLAN_FIELDS.items()
                },
            )
        await session.commit()
        if mock:
            await save_ai_key(
                session,
                1,
                1,
                MOCK_API_BASE_URL,
                MOCK_API_KEY,
                MOCK_MODEL,
                key_type="text",
            )


def _seed(args: argparse.Namespace) -> None:
    mock = args.mode == "mock"
    require_isolated_worktree(
        args.tested_sha,
        secrets_absent=True,
        lock_absent=True,
    )
    database = _database_path(args.database, exists=False)
    _reserve_database(database)
    _synthetic_env(database, mock=mock)
    from app.core.startup import run_startup_migrations  # delayed by gate

    run_startup_migrations()
    asyncio.run(_seed_rows(mock=mock))
    print(
        json.dumps(
            {
                "mode": args.mode,
                "plan_dates": [value.isoformat() for value in PLAN_DATES],
                "seed": "PASS",
                "tested_code_sha": _sha(args.tested_sha),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


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


def _real_config(database: Path) -> dict[str, object]:
    with sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True) as connection:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ai_api_key'"
        ).fetchone()
        rows = (
            connection.execute(
                "SELECT model_name FROM ai_api_key WHERE tenant_id=1 AND user_id=1 "
                "AND key_type='text' AND is_active=1 ORDER BY model_name"
            ).fetchall()
            if exists
            else []
        )
    return {
        "active_text_config_count": len(rows),
        "model_names": [row[0] for row in rows],
    }


def _preflight(args: argparse.Namespace) -> None:
    real = args.mode == "real"
    root = require_isolated_worktree(
        args.tested_sha,
        secrets_absent=not real,
        lock_absent=False,
    )
    database = _database_path(args.database, exists=True)
    app_ready = _port_listening(APP_PORT) if real else _port_free(APP_PORT)
    provider_config = _real_config(database)
    model_names = provider_config["model_names"]
    one_named_model = (
        isinstance(model_names, list)
        and len(model_names) == 1
        and type(model_names[0]) is str
        and bool(model_names[0])
    )
    secret_metadata = _safe_metadata(root / ".kindergarten_secrets")
    lock_metadata = _safe_metadata(root / ".kindergarten_secrets.lock")
    result: dict[str, object] = {
        "app_ready": app_ready,
        "mode": args.mode,
        "network_requests_made_by_helper": 0,
        "preflight": "PASS",
        "tested_code_sha": _sha(args.tested_sha),
        "worktree": "isolated",
    }
    if real:
        result.update(
            provider_config=provider_config,
            secrets=secret_metadata,
            secrets_lock=lock_metadata,
        )
        ready = (
            app_ready
            and provider_config["active_text_config_count"] == 1
            and one_named_model
            and secret_metadata.get("state") == "regular"
            and secret_metadata.get("mode") == "0600"
            and lock_metadata.get("state") == "regular"
            and lock_metadata.get("mode") == "0600"
        )
    else:
        mock_port_free = _port_free(MOCK_PORT)
        result.update(
            mock_port_free=mock_port_free,
            provider_config=provider_config,
            secrets=secret_metadata,
            secrets_lock=lock_metadata,
        )
        ready = (
            app_ready
            and mock_port_free
            and provider_config
            == {
                "active_text_config_count": 1,
                "model_names": [MOCK_MODEL],
            }
            and secret_metadata == {"state": "absent"}
            and lock_metadata.get("state") == "regular"
            and lock_metadata.get("mode") == "0600"
        )
    if not ready:
        result["preflight"] = "BLOCKED"
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if not ready:
        raise SystemExit(1)


def _run_app(args: argparse.Namespace) -> None:
    mock = args.mode == "mock"
    require_isolated_worktree(
        args.tested_sha,
        secrets_absent=mock,
        lock_absent=False,
    )
    database = _database_path(args.database, exists=True)
    if not _port_free(APP_PORT) or mock and not _port_listening(MOCK_PORT):
        raise ManualHelperError("required loopback port state is not ready")
    if mock:
        _synthetic_env(database, mock=True)
    else:
        os.environ.update(
            DATABASE_URL=f"sqlite+aiosqlite:///{database.as_posix()}",
            PORT=str(APP_PORT),
        )
        os.environ.pop("ENCRYPTION_KEY", None)
        os.environ.pop("JWT_SECRET", None)

    import app.main  # noqa: F401 - delayed registration of product pages
    from nicegui import app, ui

    from app.api import create_api_router
    from app.core.bootstrap import run_bootstrap
    from app.core.config import settings
    from app.core.startup import run_startup_migrations

    run_startup_migrations()
    app.on_startup(run_bootstrap)
    app.include_router(create_api_router())
    ui.run(
        host="127.0.0.1",
        port=APP_PORT,
        title="幼儿园教学管理系统 · F009",
        storage_secret=settings.JWT_SECRET,
        reload=False,
        show=False,
        favicon="📚",
    )


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def _scalar(value: object) -> object:
    if isinstance(value, bytes):
        return {"bytes": len(value), "sha256": _digest(value)}
    if isinstance(value, float) and not math.isfinite(value):
        return {"float": repr(value)}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise ManualHelperError("unsupported SQLite value")


def _database_summary(path: Path) -> dict[str, object]:
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as connection:
        connection.execute("BEGIN")
        definitions = connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        tables: dict[str, object] = {}
        for raw_name, schema in definitions:
            name = str(raw_name)
            quoted = '"' + name.replace('"', '""') + '"'
            columns = [
                row[1]
                for row in connection.execute(f"PRAGMA table_xinfo({quoted})")
                if row[6] == 0
            ]
            rows = [
                [_scalar(value) for value in row]
                for row in connection.execute(f"SELECT * FROM {quoted}")
            ]
            rows.sort(key=_canonical)
            tables[name] = {
                "columns_sha256": _digest(_canonical(columns)),
                "row_count": len(rows),
                "rows_sha256": _digest(_canonical(rows)),
                "schema_sha256": _digest(str(schema or "").encode()),
            }
        connection.rollback()
    return {"table_count": len(tables), "tables": tables}


def _regular_digest(path: Path, expected: os.stat_result) -> tuple[int, str]:
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    if os.name == "posix" and not no_follow:
        raise ManualHelperError("platform lacks safe no-follow file open")
    try:
        fd = os.open(
            path,
            os.O_RDONLY
            | no_follow
            | getattr(os, "O_NONBLOCK", 0)
            | getattr(os, "O_CLOEXEC", 0),
        )
        try:
            actual = os.fstat(fd)
            if not stat.S_ISREG(actual.st_mode) or (actual.st_dev, actual.st_ino) != (
                expected.st_dev,
                expected.st_ino,
            ):
                raise ManualHelperError("file changed during snapshot")
            digest, length = hashlib.sha256(), 0
            while chunk := os.read(fd, 65_536):
                digest.update(chunk)
                length += len(chunk)
            return length, digest.hexdigest()
        finally:
            os.close(fd)
    except OSError as exc:
        raise ManualHelperError("cannot safely summarize file") from exc


def _entry(path: Path) -> dict[str, object]:
    metadata = _lstat(path)
    if metadata is None:
        return {"state": "absent"}
    mode = f"{stat.S_IMODE(metadata.st_mode):04o}"
    if stat.S_ISREG(metadata.st_mode):
        length, sha256 = _regular_digest(path, metadata)
        return {
            "length": length,
            "mode": mode,
            "sha256": sha256,
            "state": "regular",
        }
    kind = (
        "directory"
        if stat.S_ISDIR(metadata.st_mode)
        else "symlink"
        if stat.S_ISLNK(metadata.st_mode)
        else "other"
    )
    return {"mode": mode, "state": kind}


def _safe_metadata(path: Path) -> dict[str, object]:
    metadata = _lstat(path)
    if metadata is None:
        return {"state": "absent"}
    if not stat.S_ISREG(metadata.st_mode):
        return {"state": "not_regular"}
    return {
        "length": metadata.st_size,
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
        "state": "regular",
    }


def _tree(root: Path) -> dict[str, object]:
    metadata = _lstat(root)
    if metadata is None:
        return {
            "entry_count": 0,
            "state": "absent",
            "tree_sha256": _digest(b"[]"),
        }
    if not stat.S_ISDIR(metadata.st_mode):
        raise ManualHelperError("exports entry is not a directory")
    entries: list[dict[str, object]] = []
    for current_raw, directories, files in os.walk(root, followlinks=False):
        current, kept = Path(current_raw), []
        for name in sorted(directories):
            path, kind = current / name, "directory"
            child = path.lstat()
            if stat.S_ISLNK(child.st_mode):
                kind = "symlink"
            elif stat.S_ISDIR(child.st_mode):
                kept.append(name)
            else:
                kind = "other"
            entries.append(
                {
                    "path_sha256": _digest(path.relative_to(root).as_posix().encode()),
                    "state": kind,
                }
            )
        directories[:] = kept
        for name in sorted(files):
            path = current / name
            child = path.lstat()
            item: dict[str, object] = {
                "path_sha256": _digest(path.relative_to(root).as_posix().encode()),
                "state": "regular" if stat.S_ISREG(child.st_mode) else "other",
            }
            if stat.S_ISREG(child.st_mode):
                item["length"], item["sha256"] = _regular_digest(path, child)
            entries.append(item)
    entries.sort(key=_canonical)
    return {
        "entry_count": len(entries),
        "state": "directory",
        "tree_sha256": _digest(_canonical(entries)),
    }


def _ui_summary() -> dict[str, object]:
    raw = sys.stdin.buffer.read(_MAX_UI_BYTES + 1)
    if len(raw) > _MAX_UI_BYTES:
        raise ManualHelperError("UI JSON exceeds limit")
    try:
        value = json.loads(
            raw,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ManualHelperError("UI stdin is not valid JSON") from exc
    if (
        not isinstance(value, dict)
        or frozenset(value) != _UI_FIELDS
        or not all(type(item) is str for item in value.values())
    ):
        raise ManualHelperError("UI JSON must contain exactly 11 visible body fields")
    canonical = _canonical(value)
    return {
        "canonical_utf8_length": len(canonical),
        "field_count": len(value),
        "sha256": _digest(canonical),
    }


def _write_new(path: Path, value: object) -> None:
    if path.parent.parent != Path("/tmp") or not path.parent.name.startswith(
        "km-f009."
    ):
        raise ManualHelperError("output must be inside /tmp/km-f009.*")
    _secure_run_dir(path.parent)
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    )
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            view = memoryview(payload)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise OSError("no write progress")
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise ManualHelperError("cannot create output") from exc


def _read_json(raw: str) -> object:
    try:
        return json.loads(Path(raw).expanduser().resolve().read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManualHelperError("cannot read summary JSON") from exc


def _ui_digest(args: argparse.Namespace) -> None:
    value = _ui_summary()
    output = Path(args.output).expanduser().resolve()
    _write_new(output, value)
    print(
        json.dumps(
            {"output": output.name, "sha256": value["sha256"]},
            sort_keys=True,
        )
    )


def _snapshot(args: argparse.Namespace) -> None:
    root = require_isolated_worktree(
        args.tested_sha,
        secrets_absent=False,
        lock_absent=False,
        clean=False,
    )
    database = _database_path(args.database, exists=True)
    exports = Path(args.exports)
    if exports.is_absolute() or ".." in exports.parts:
        raise ManualHelperError("exports path escapes worktree")
    ui = _read_json(args.ui_body_digest)
    if (
        not isinstance(ui, dict)
        or set(ui) != {"canonical_utf8_length", "field_count", "sha256"}
        or ui.get("field_count") != len(_UI_FIELDS)
    ):
        raise ManualHelperError("invalid 11-field UI digest")
    git_status = _git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    value: dict[str, object] = {
        "database": _database_summary(database),
        "exports": _tree(root / exports),
        "git": {
            "record_count": len([item for item in git_status.split(b"\0") if item]),
            "status_sha256": _digest(git_status),
        },
        "protected": {
            name: (
                _safe_metadata(root / name)
                if name.endswith(".lock")
                else _entry(root / name)
            )
            for name in _PROTECTED_NAMES
        },
        "tested_code_sha": _sha(args.tested_sha),
        "ui_body": ui,
    }
    value["snapshot_sha256"] = _digest(_canonical(value))
    output = Path(args.output).expanduser().resolve()
    _write_new(output, value)
    print(
        json.dumps(
            {"output": output.name, "snapshot_sha256": value["snapshot_sha256"]},
            sort_keys=True,
        )
    )


def _compare(args: argparse.Namespace) -> None:
    before, after = _read_json(args.baseline), _read_json(args.final)
    changed = (
        sorted(
            key for key in set(before) | set(after) if before.get(key) != after.get(key)
        )
        if isinstance(before, dict) and isinstance(after, dict)
        else ["document"]
    )
    print(json.dumps({"changed_sections": changed, "equal": not changed}))
    if changed:
        raise SystemExit(1)


def _self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="km-f009.selftest.", dir="/tmp") as raw:
        root = Path(raw)
        path = root / "probe.db"
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE probe (id INTEGER, payload BLOB)")
            connection.execute("INSERT INTO probe VALUES (1, ?)", (b"synthetic",))
        if _database_summary(path) != _database_summary(path):
            raise ManualHelperError("snapshot self-test failed")
        if os.name == "posix":
            expected_path, fifo_path = root / "expected", root / "fifo"
            expected_path.write_bytes(b"synthetic")
            os.mkfifo(fifo_path, 0o600)
            try:
                _regular_digest(fifo_path, expected_path.stat())
            except ManualHelperError:
                pass
            else:
                raise ManualHelperError("non-regular summary input was accepted")
    print('{"self_test":"PASS"}')


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, handler in (
        ("seed", _seed),
        ("preflight", _preflight),
        ("run-app", _run_app),
    ):
        command = commands.add_parser(name)
        command.add_argument("--mode", choices=("mock", "real"), required=True)
        command.add_argument("--database", required=True)
        command.add_argument("--tested-sha", required=True)
        command.set_defaults(handler=handler)
    digest = commands.add_parser("ui-digest")
    digest.add_argument("--output", required=True)
    digest.set_defaults(handler=_ui_digest)
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--database", required=True)
    snapshot.add_argument("--exports", default="exports")
    snapshot.add_argument("--output", required=True)
    snapshot.add_argument("--tested-sha", required=True)
    snapshot.add_argument("--ui-body-digest", required=True)
    snapshot.set_defaults(handler=_snapshot)
    compare = commands.add_parser("compare")
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--final", required=True)
    compare.set_defaults(handler=_compare)
    commands.add_parser("self-test").set_defaults(handler=lambda _args: _self_test())
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        args.handler(args)
    except ManualHelperError as exc:
        print(f"F009 helper refused: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
