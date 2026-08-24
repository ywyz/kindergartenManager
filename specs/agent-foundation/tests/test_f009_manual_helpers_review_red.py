"""F009 Review RED: verified worktree imports must precede app imports."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
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
