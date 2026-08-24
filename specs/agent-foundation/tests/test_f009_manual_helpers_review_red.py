"""F009 Review RED: verified worktree imports must precede app imports."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys

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
