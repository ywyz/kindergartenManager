"""W008 helper audit findings fixed as reproducible RED behavior."""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest


MANUAL_ROOT = Path(__file__).parents[1] / "manual"
MYSQL_HELPER = MANUAL_ROOT / "w008_mysql.py"
BROWSER_HELPER = MANUAL_ROOT / "w008_browser.py"
MANUAL_README = MANUAL_ROOT / "README.md"


def _load(path: Path, name: str):
    assert path.is_file()
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _mysql():
    return _load(MYSQL_HELPER, "w008_mysql_green_findings_red")


def _browser():
    return _load(BROWSER_HELPER, "w008_browser_green_findings_red")


def test_mysql_repository_import_is_explicitly_nonpersisting_and_ordered(
    tmp_path: Path,
) -> None:
    helper = _mysql()
    installer = getattr(helper, "_install_nonpersisting_app_config", None)
    assert callable(installer), (
        "the live MySQL helper must install a nonpersisting app.config stub"
    )

    tree = ast.parse(MYSQL_HELPER.read_text(encoding="utf-8"))
    runner = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_run_real_backend"
    )
    install_index = next(
        index
        for index, statement in enumerate(runner.body)
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Name)
        and statement.value.func.id == "_install_nonpersisting_app_config"
    )
    app_import_index = next(
        index
        for index, statement in enumerate(runner.body)
        if isinstance(statement, ast.ImportFrom)
        and statement.module is not None
        and statement.module.startswith("app.")
    )
    assert install_index < app_import_index

    probe = f"""
import importlib.util
import json
import os
from pathlib import Path
import sys

root = Path({str(Path(__file__).parents[3])!r})
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location('w008_mysql_probe', Path({str(MYSQL_HELPER)!r}))
module = importlib.util.module_from_spec(spec)
sys.modules['w008_mysql_probe'] = module
spec.loader.exec_module(module)
os.chdir({str(tmp_path)!r})
module._install_nonpersisting_app_config()
import app.repository.confirmed_write_repository
import app.repository.user_repository
print(json.dumps({{
    'secret': Path('.kindergarten_secrets').exists(),
    'lock': Path('.kindergarten_secrets.lock').exists(),
}}))
"""
    result = subprocess.run(
        (sys.executable, "-c", probe),
        cwd=Path(__file__).parents[3],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"secret": False, "lock": False}


class _SeedSession:
    def __init__(self, captured: list[dict[str, object]]) -> None:
        self._captured = captured

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def execute(
        self,
        _statement: object,
        parameters: dict[str, object],
    ) -> object:
        self._captured.append(dict(parameters))
        return object()

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def test_mysql_synthetic_seed_fits_the_real_schema_widths() -> None:
    helper = _mysql()
    captured: list[dict[str, object]] = []
    backend = object.__new__(helper.LiveMySQLBackend)
    backend._sessions = lambda: _SeedSession(captured)
    backend._actor_plan_seeded = False

    asyncio.run(backend._ensure_actor_and_plan())

    assert len(captured) == 2
    user, plan = captured
    assert len(str(user["username"])) <= 64
    assert len(str(user["hashed_password"])) <= 256
    assert len(str(user["display_name"])) <= 64
    assert len(str(plan["weekday_cn"])) <= 4
    assert len(str(plan["grade"])) <= 16
    assert len(str(plan["class_name"])) <= 32


def test_browser_launcher_is_real_writer_only_loopback_composition() -> None:
    helper = _browser()
    source = inspect.getsource(helper._launch_product_app)
    assert "browser launcher is not configured" not in source
    for required in (
        "ConfirmedDailyPlanWriteService",
        "create_daily_plan_patch_confirmation_controller",
        "writer_session_factory",
        "AsyncSessionLocal",
        "ENCRYPTION_KEY",
        "JWT_SECRET",
        "ui.run",
        'host="127.0.0.1"',
    ):
        assert required in source
    assert source.index(
        "create_daily_plan_patch_confirmation_controller"
    ) < source.index("import app.main")


def test_browser_database_is_owner_only_w008_tmp_regular_file() -> None:
    helper = _browser()
    resolver = getattr(helper, "_database_path", None)
    assert callable(resolver), "browser helper must validate its disposable database"

    with tempfile.TemporaryDirectory(prefix="km-w008.", dir="/tmp") as raw:
        run_dir = Path(raw)
        run_dir.chmod(0o700)
        database = run_dir / "scenario.db"
        descriptor = os.open(database, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        assert resolver(str(database)) == database.resolve()

        link = run_dir / "linked.db"
        link.symlink_to(database)
        with pytest.raises(helper.ManualHelperError):
            resolver(str(link))

        database.chmod(0o644)
        with pytest.raises(helper.ManualHelperError):
            resolver(str(database))

    outside = Path(tempfile.gettempdir()) / "w008-outside.db"
    with pytest.raises(helper.ManualHelperError):
        resolver(str(outside))


def test_mysql_migration_roundtrip_keeps_config_files_outside_worktree() -> None:
    procedure = MANUAL_README.read_text(encoding="utf-8")
    start = procedure.index('MYSQL_URL="mysql+aiomysql://')
    end = procedure.index('W008_MYSQL_DATABASE_URL="$MYSQL_URL"', start)
    migration_block = procedure[start:end]

    for required in (
        "MYSQL_MIGRATION_RUNTIME=$(mktemp -d /tmp/km-w008-mysql-migrations.XXXXXX)",
        'cd "$MYSQL_MIGRATION_RUNTIME"',
        'PYTHONPATH="$TESTED_WORKTREE"',
        'ENCRYPTION_KEY="f009-fictional-encryption-key-do-not-use"',
        'JWT_SECRET="f009-fictional-jwt-secret-do-not-use"',
        '-c "$TESTED_WORKTREE/alembic.ini"',
    ):
        assert required in migration_block

    assert migration_block.count("run_w008_alembic upgrade head") == 2
    assert migration_block.count("run_w008_alembic current") == 3
    assert "run_w008_alembic downgrade a6c4d8e2f9b1" in migration_block
    assert 'DATABASE_URL="$MYSQL_URL" "$ABS_PYTHON" -m alembic' not in (migration_block)
