"""F009 Review RED: verified worktree imports must precede app imports."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest


class _StopBeforeApplicationImport(RuntimeError):
    """Sentinel proving the test did not cross into application imports."""


def _load_seed_helper():
    path = Path(__file__).parents[1] / "manual" / "f009_seed.py"
    spec = importlib.util.spec_from_file_location("f009_manual_seed_review", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_mock_helper(monkeypatch):
    seed = _load_seed_helper()
    monkeypatch.setitem(sys.modules, "f009_seed", seed)
    path = Path(__file__).parents[1] / "manual" / "f009_mock_server.py"
    spec = importlib.util.spec_from_file_location("f009_manual_mock_review", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mock_payload(mock, intent: str) -> dict[str, object]:
    sections = [
        {"content": "synthetic", "field_path": path, "truncated": False}
        for path in mock._PATHS
    ]
    system = {
        "base_fingerprint": "a" * 64,
        "facts": [
            {
                "class_name": "synthetic",
                "content_sha256": "b" * 64,
                "grade": "大班",
                "plan_date": "2026-09-07",
                "plan_id": 1,
                "sections": sections,
                "updated_at_utc": "2026-09-01T00:00:00+00:00",
                "week_number": 2,
                "weekday_cn": "周一",
            }
        ],
        "operation_id": "11111111-1111-1111-1111-111111111111",
        "policy_version": "agent-foundation-v1",
        "scope": {"daily_plan_id": None, "plan_date": "2026-09-07"},
        "turn_id": "22222222-2222-2222-2222-222222222222",
    }
    return {
        "max_tokens": 4096,
        "messages": [
            {"role": "system", "content": json.dumps(system)},
            {"role": "user", "content": intent},
        ],
        "model": mock.MOCK_MODEL,
        "tool_choice": "auto",
        "tools": mock._TOOLS,
    }


@pytest.mark.parametrize("handler_name", ("_seed", "_run_app"))
def test_verified_worktree_is_activated_before_database_or_app_import(
    tmp_path,
    monkeypatch,
    handler_name,
):
    helper = _load_seed_helper()
    verified_root = tmp_path / "verified-worktree"
    events: list[str] = []

    def verified_gate(*_args, **_kwargs):
        events.append("gate")
        return verified_root

    def activate(root: Path) -> None:
        assert root == verified_root
        events.append("activate")

    def stop_at_database(*_args, **_kwargs):
        events.append("database")
        raise _StopBeforeApplicationImport

    monkeypatch.setattr(helper, "require_isolated_worktree", verified_gate)
    monkeypatch.setattr(helper, "_activate_worktree_imports", activate, raising=False)
    monkeypatch.setattr(helper, "_database_path", stop_at_database)
    args = argparse.Namespace(
        database=str(tmp_path / "database.sqlite"),
        mode="mock",
        tested_sha="a" * 40,
    )

    with pytest.raises(_StopBeforeApplicationImport):
        getattr(helper, handler_name)(args)

    assert events == ["gate", "activate", "database"]


def test_verified_worktree_becomes_first_import_root(tmp_path, monkeypatch):
    helper = _load_seed_helper()
    verified_root = tmp_path / "verified-worktree"
    foreign_root = tmp_path / "foreign-worktree"
    monkeypatch.setattr(sys, "path", [str(foreign_root), *sys.path])

    helper._activate_worktree_imports(verified_root)

    assert Path(sys.path[0]).resolve() == verified_root.resolve()


def test_manual_seed_adds_explicit_synthetic_user_without_bootstrap(monkeypatch):
    helper = _load_seed_helper()
    bootstrap_calls: list[object] = []
    added_users: list[object] = []
    repository_calls: list[str] = []

    class _Column:
        def __eq__(self, _other):
            return object()

    class _User:
        tenant_id = _Column()
        username = _Column()

        def __init__(self, **values):
            for name, value in values.items():
                setattr(self, name, value)

    class _UserRole:
        sys_admin = "sys_admin"

    class _Select:
        def where(self, *_conditions):
            return self

    class _Result:
        def scalar_one(self):
            return _User(id=1)

    class _Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def add(self, value):
            added_users.append(value)

        async def execute(self, _statement):
            return _Result()

        async def commit(self):
            repository_calls.append("commit")

    async def ensure_default_user(session):
        bootstrap_calls.append(session)

    async def repository_call(*_args, **_kwargs):
        repository_calls.append("repository")

    def module(name: str, **members):
        value = types.ModuleType(name)
        for member_name, member_value in members.items():
            setattr(value, member_name, member_value)
        return value

    replacements = {
        "sqlalchemy": module("sqlalchemy", select=lambda _model: _Select()),
        "app.auth.password": module(
            "app.auth.password",
            hash_password=lambda _plain: "fictional-hash",
        ),
        "app.core.bootstrap": module(
            "app.core.bootstrap",
            ensure_default_user=ensure_default_user,
        ),
        "app.core.database": module(
            "app.core.database",
            AsyncSessionLocal=_Session,
        ),
        "app.core.models.user": module(
            "app.core.models.user",
            User=_User,
            UserRole=_UserRole,
        ),
        "app.repository.ai_key_repository": module(
            "app.repository.ai_key_repository",
            save_ai_key=repository_call,
        ),
        "app.repository.class_repository": module(
            "app.repository.class_repository",
            upsert_class_config=repository_call,
        ),
        "app.repository.daily_plan_repository": module(
            "app.repository.daily_plan_repository",
            save_daily_plan=repository_call,
        ),
        "app.repository.semester_repository": module(
            "app.repository.semester_repository",
            upsert_active_semester=repository_call,
        ),
    }
    for name, replacement in replacements.items():
        monkeypatch.setitem(sys.modules, name, replacement)

    asyncio.run(helper._seed_rows(mock=False))

    assert bootstrap_calls == []
    assert len(added_users) == 1
    assert added_users[0].id == 1
    assert repository_calls.count("commit") == 1


@pytest.mark.parametrize(
    "intent",
    (
        "UNRECOGNIZED PREFIX F009_TEXT",
        "F009_TEXT UNRECOGNIZED SUFFIX",
    ),
)
def test_closed_mock_rejects_marker_embedded_in_unknown_intent(monkeypatch, intent):
    mock = _load_mock_helper(monkeypatch)

    with pytest.raises(mock.MockRejected):
        mock._prepare(
            _mock_payload(mock, intent),
            f"Bearer {mock.MOCK_API_KEY}",
            0.01,
        )
