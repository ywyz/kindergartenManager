"""W008 RED: auditable browser fault-acceptance helper contract."""

from __future__ import annotations

import argparse
import ast
from dataclasses import fields
import importlib.util
import json
from pathlib import Path
import sys

import pytest
from sqlalchemy import column, table, update
from sqlalchemy.exc import DisconnectionError


HELPER_PATH = Path(__file__).parents[1] / "manual" / "w008_browser.py"
TESTED_SHA = "a" * 40
FAULT_VALUES = {
    "after_version",
    "after_cas",
    "after_audit",
    "known_before_commit",
    "unknown_before_commit",
    "unknown_after_commit",
}


def _load_helper():
    assert HELPER_PATH.is_file(), (
        "W008 browser acceptance helper is missing: "
        "specs/agent-write/manual/w008_browser.py"
    )
    module_name = "w008_manual_browser_red_contract"
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


def _top_level_imports() -> set[str]:
    tree = ast.parse(HELPER_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names


class _SyntheticRow:
    def __init__(self, table_name: str) -> None:
        self.__table__ = table(table_name)


class _BaseSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flush_calls = 0
        self.execute_calls = 0
        self.commit_calls = 0

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        self.flush_calls += 1

    async def execute(self, _statement: object) -> object:
        self.execute_calls += 1
        return object()

    async def commit(self) -> None:
        self.commit_calls += 1


class _BaseFactory:
    def __init__(self) -> None:
        self.sessions: list[_BaseSession] = []

    def __call__(self) -> _BaseSession:
        session = _BaseSession()
        self.sessions.append(session)
        return session


def test_fault_point_is_an_exact_closed_six_value_enum() -> None:
    helper = _load_helper()

    assert {member.value for member in helper.FaultPoint} == FAULT_VALUES
    assert {member.name for member in helper.FaultPoint} == {
        value.upper() for value in FAULT_VALUES
    }


def test_helper_has_no_application_import_before_verified_delayed_launch(
    tmp_path,
    monkeypatch,
) -> None:
    helper = _load_helper()
    assert not {
        name
        for name in _top_level_imports()
        if name == "app" or name.startswith(("app.", "nicegui"))
    }

    verified_root = tmp_path / "verified-exact-sha-worktree"
    events: list[tuple[str, object]] = []

    def gate(tested_sha: str, **kwargs: object) -> Path:
        events.append(("gate", (tested_sha, kwargs)))
        return verified_root

    def activate(root: Path) -> None:
        events.append(("activate", root))

    def delayed_launch(*args: object, **kwargs: object) -> str:
        events.append(("launch", (args, kwargs)))
        return "launched"

    monkeypatch.setattr(helper, "require_isolated_worktree", gate)
    monkeypatch.setattr(helper, "_activate_worktree_imports", activate)
    monkeypatch.setattr(helper, "_launch_product_app", delayed_launch)
    args = argparse.Namespace(
        tested_sha=TESTED_SHA,
        fault="after_version",
    )

    assert helper.prepare_run(args) == "launched"
    assert [name for name, _value in events] == ["gate", "activate", "launch"]
    gated_sha, gate_kwargs = events[0][1]
    assert gated_sha == TESTED_SHA
    assert gate_kwargs.get("clean") is True
    assert events[1][1] == verified_root


@pytest.mark.parametrize(
    ("fault", "row_table", "operation", "base_calls"),
    [
        ("after_version", "daily_plan_operation_version", "flush", 1),
        ("after_cas", None, "execute", 1),
        ("after_audit", "agent_write_audit", "flush", 1),
        ("known_before_commit", None, "commit", 0),
    ],
)
@pytest.mark.asyncio
async def test_known_faults_are_injected_once_only_in_writer_sessions(
    fault: str,
    row_table: str | None,
    operation: str,
    base_calls: int,
) -> None:
    helper = _load_helper()
    base_factory = _BaseFactory()
    writer_factory = helper.writer_session_factory(
        base_factory,
        helper.FaultPoint(fault),
    )

    ordinary = base_factory()
    await ordinary.commit()
    assert ordinary.commit_calls == 1

    writer = writer_factory()
    with pytest.raises(RuntimeError, match="injected write fault") as raised:
        if operation == "flush":
            assert row_table is not None
            writer.add(_SyntheticRow(row_table))
            await writer.flush()
        elif operation == "execute":
            daily_plan = table("daily_plan", column("revision"))
            await writer.execute(update(daily_plan).values(revision=2))
        else:
            await writer.commit()

    assert fault not in repr(raised.value)
    injected_base = base_factory.sessions[-1]
    if operation == "flush":
        assert injected_base.flush_calls == base_calls
    elif operation == "execute":
        assert injected_base.execute_calls == base_calls
    else:
        assert injected_base.commit_calls == base_calls
    assert ordinary.commit_calls == 1


@pytest.mark.parametrize(
    ("fault", "base_commit_calls"),
    [
        ("unknown_before_commit", 0),
        ("unknown_after_commit", 1),
    ],
)
@pytest.mark.asyncio
async def test_commit_unknown_faults_never_retry_or_touch_ordinary_sessions(
    fault: str,
    base_commit_calls: int,
) -> None:
    helper = _load_helper()
    base_factory = _BaseFactory()
    writer_factory = helper.writer_session_factory(
        base_factory,
        helper.FaultPoint(fault),
    )

    writer = writer_factory()
    with pytest.raises(DisconnectionError, match="injected write disconnect"):
        await writer.commit()

    assert base_factory.sessions[-1].commit_calls == base_commit_calls
    ordinary = base_factory()
    await ordinary.commit()
    assert ordinary.commit_calls == 1


@pytest.mark.asyncio
async def test_fault_counters_emit_only_closed_retry_free_runtime_events(
    capsys: pytest.CaptureFixture[str],
) -> None:
    helper = _load_helper()
    assert {field.name for field in fields(helper.FaultCounters)} == {
        "issue",
        "apply",
        "reconcile",
    }

    class _Delegate:
        async def issue_confirmation(self, *_args, **_kwargs):
            return object()

        async def apply(self, *_args, **_kwargs):
            return object()

        async def reconcile(self, *_args, **_kwargs):
            return object()

    counted = helper._CountingWriteService(
        _Delegate(),
        counters=helper.FaultCounters(),
        tested_sha=TESTED_SHA,
        fault=helper.FaultPoint.UNKNOWN_AFTER_COMMIT,
    )
    await counted.issue_confirmation(
        "sk-synthetic-must-not-appear",
        "provider-response-body-must-not-appear",
        expected_revision=1,
    )
    event = json.loads(capsys.readouterr().out)
    assert set(event) == {"event", "tested_code_sha", "fault", "counters"}
    assert event == {
        "event": "w008_writer_call",
        "tested_code_sha": TESTED_SHA,
        "fault": "unknown_after_commit",
        "counters": {"issue": 1, "apply": 0, "reconcile": 0},
    }
    rendered = json.dumps(event, ensure_ascii=False, sort_keys=True)
    for forbidden in (
        "synthetic-password",
        "provider-response-body",
        "provider.invalid",
        "sk-synthetic",
    ):
        assert forbidden not in rendered

    with pytest.raises(RuntimeError, match="automatic retry"):
        await counted.issue_confirmation(object(), object(), expected_revision=1)

    assert not hasattr(helper, "sanitize_report"), (
        "the launcher must not retain a disconnected free-form result sanitizer"
    )
