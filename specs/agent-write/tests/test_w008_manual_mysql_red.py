"""W008 RED: auditable live-MySQL acceptance helper contract."""

from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
import sys

import pytest


HELPER_PATH = Path(__file__).parents[1] / "manual" / "w008_mysql.py"
TESTED_SHA = "a" * 40
CURRENT_HEAD = "e5f7a9c2d4b6"
TRIGGER_CASES = {
    ("daily_plan_operation_version", "UPDATE"),
    ("daily_plan_operation_version", "DELETE"),
    ("agent_write_audit", "UPDATE"),
    ("agent_write_audit", "DELETE"),
}
EXPECTED_REPORT = {
    "tested_code_sha": TESTED_SHA,
    "head": CURRENT_HEAD,
    "trigger_rejections": 4,
    "cas": [False, True],
    "revision": 2,
    "admin_lock_errno": 1205,
}


def _load_helper():
    assert HELPER_PATH.is_file(), (
        "W008 MySQL acceptance helper is missing: "
        "specs/agent-write/manual/w008_mysql.py"
    )
    module_name = "w008_manual_mysql_red_contract"
    spec = importlib.util.spec_from_file_location(module_name, HELPER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


class _FakeBackend:
    def __init__(
        self,
        *,
        version: str = "8.0.43",
        schema_scoped_principal: bool = True,
        heads: tuple[str, ...] = (CURRENT_HEAD,),
        triggers: set[tuple[str, str]] | None = None,
        cas: tuple[bool, bool, int] = (True, False, 2),
        lock_errno: int = 1205,
    ) -> None:
        self.version = version
        self.schema_scoped_principal = schema_scoped_principal
        self.heads = heads
        self.triggers = TRIGGER_CASES if triggers is None else triggers
        self.cas = cas
        self.lock_errno = lock_errno
        self.calls: list[str] = []
        self.database_url = "mysql://synthetic-password@localhost/private"
        self.provider_body = "provider-body-must-not-appear"

    async def server_version(self) -> str:
        self.calls.append("version")
        return self.version

    async def app_principal_is_schema_scoped(self) -> bool:
        self.calls.append("principal")
        return self.schema_scoped_principal

    async def current_alembic_heads(self) -> tuple[str, ...]:
        self.calls.append("head")
        return self.heads

    async def immutable_trigger_rejections(self) -> set[tuple[str, str]]:
        self.calls.append("triggers")
        return self.triggers

    async def revision_cas_race(self) -> tuple[bool, bool, int]:
        self.calls.append("cas")
        return self.cas

    async def actor_lock_contention_errno(self) -> int:
        self.calls.append("actor-lock")
        return self.lock_errno


def test_mysql_url_is_only_loaded_from_the_dedicated_environment_mapping() -> None:
    helper = _load_helper()
    assert list(inspect.signature(helper.load_mysql_url).parameters) == ["env"]
    source = HELPER_PATH.read_text(encoding="utf-8")
    for forbidden_option in ("--url", "--database-url", "--mysql-url"):
        assert forbidden_option not in source

    password = "w008-synthetic-password"
    loaded = helper.load_mysql_url(
        {
            "W008_MYSQL_DATABASE_URL": (
                f"mysql+aiomysql://w008-user:{password}@127.0.0.1:3306/w008_db"
            ),
            "DATABASE_URL": "sqlite+aiosqlite:///must-not-be-used.sqlite3",
        }
    )
    assert getattr(loaded, "drivername").startswith("mysql+")
    assert password not in str(loaded)
    assert password not in repr(loaded)

    with pytest.raises(RuntimeError, match="W008_MYSQL_DATABASE_URL") as missing:
        helper.load_mysql_url(
            {
                "DATABASE_URL": (
                    "mysql+aiomysql://fallback:must-not-leak@localhost/fallback"
                )
            }
        )
    assert "must-not-leak" not in repr(missing.value)


@pytest.mark.parametrize("username", ("root", "ROOT"))
def test_mysql_url_loader_rejects_the_root_principal(username: str) -> None:
    helper = _load_helper()
    password = "w008-root-password-must-not-leak"

    with pytest.raises(helper.ManualHelperError, match="principal") as raised:
        helper.load_mysql_url(
            {
                "W008_MYSQL_DATABASE_URL": (
                    f"mysql+aiomysql://{username}:{password}@127.0.0.1:3306/w008_db"
                )
            }
        )

    assert password not in repr(raised.value)


@pytest.mark.parametrize(
    "database_url",
    (
        "sqlite+aiosqlite:///synthetic.sqlite3",
        "postgresql+asyncpg://synthetic:password@localhost/synthetic",
        "mariadb+aiomysql://synthetic:password@localhost/synthetic",
    ),
)
def test_mysql_url_loader_rejects_every_non_mysql_scheme(database_url: str) -> None:
    helper = _load_helper()

    with pytest.raises(RuntimeError, match="MySQL") as raised:
        helper.load_mysql_url({"W008_MYSQL_DATABASE_URL": database_url})

    assert database_url not in repr(raised.value)


@pytest.mark.asyncio
async def test_validate_mysql8_accepts_only_a_real_mysql_8_server() -> None:
    helper = _load_helper()
    accepted = _FakeBackend(version="8.0.43")
    await helper.validate_mysql8(accepted)
    assert accepted.calls == ["version"]

    for rejected_version in ("5.7.44", "10.11.6-MariaDB", "8.0.36-MariaDB"):
        backend = _FakeBackend(version=rejected_version)
        with pytest.raises(RuntimeError, match="MySQL 8"):
            await helper.validate_mysql8(backend)
        assert backend.calls == ["version"]


@pytest.mark.asyncio
async def test_live_runner_reports_current_head_four_triggers_cas_and_actor_lock() -> (
    None
):
    helper = _load_helper()
    backend = _FakeBackend()

    report = await helper.run_live_acceptance(
        backend,
        tested_sha=TESTED_SHA,
    )

    assert report == EXPECTED_REPORT
    assert backend.calls == [
        "version",
        "principal",
        "head",
        "triggers",
        "cas",
        "actor-lock",
    ]
    rendered = json.dumps(report, sort_keys=True)
    for forbidden in (
        "synthetic-password",
        "provider-body",
        "mysql://",
        "w008_db",
    ):
        assert forbidden not in rendered


@pytest.mark.asyncio
async def test_live_runner_rejects_a_globally_privileged_principal() -> None:
    helper = _load_helper()
    backend = _FakeBackend(schema_scoped_principal=False)

    with pytest.raises(helper.ManualHelperError, match="principal"):
        await helper.run_live_acceptance(backend, tested_sha=TESTED_SHA)

    assert backend.calls == ["version", "principal"]


@pytest.mark.parametrize(
    "backend",
    (
        _FakeBackend(heads=("old-head",)),
        _FakeBackend(
            triggers={
                ("daily_plan_operation_version", "UPDATE"),
                ("daily_plan_operation_version", "DELETE"),
                ("agent_write_audit", "UPDATE"),
            }
        ),
        _FakeBackend(cas=(True, True, 3)),
        _FakeBackend(lock_errno=0),
    ),
    ids=("wrong-head", "missing-trigger", "invalid-cas", "no-lock-contention"),
)
@pytest.mark.asyncio
async def test_live_runner_fails_closed_on_incomplete_or_conflicting_evidence(
    backend: _FakeBackend,
) -> None:
    helper = _load_helper()

    with pytest.raises(RuntimeError) as raised:
        await helper.run_live_acceptance(backend, tested_sha=TESTED_SHA)

    rendered = repr(raised.value)
    assert "synthetic-password" not in rendered
    assert "provider-body" not in rendered
