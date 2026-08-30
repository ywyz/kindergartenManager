"""NiceGUI 同步点击与异步副作用之间的可信操作 seam。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from importlib import import_module
from importlib.util import find_spec
import inspect
from uuid import uuid4

import pytest

from app.ui.auth_context import TrustedUiSession


def _session(*, session_id=None) -> TrustedUiSession:
    now = datetime.now(timezone.utc)
    return TrustedUiSession(
        session_id=session_id or uuid4(),
        tenant_id=3,
        user_id=7,
        role="teacher",
        username="teacher",
        display_name=None,
        issued_at_utc=now,
        expires_at_utc=now + timedelta(minutes=30),
    )


@dataclass(frozen=True, slots=True)
class _Payload:
    value: str


def _operation_symbols(*names: str):
    assert find_spec("app.ui.bound_operation") is not None, (
        "the bound UI operation seam must exist"
    )
    module = import_module("app.ui.bound_operation")
    return tuple(getattr(module, name) for name in names)


def test_ui_operation_guard_tracks_monotonic_generation() -> None:
    (UiOperationGuard,) = _operation_symbols("UiOperationGuard")

    guard = UiOperationGuard()
    generation = guard.capture_generation()
    assert generation == 0
    assert guard.is_current(generation) is True

    guard.advance(object())
    assert guard.capture_generation() == 1
    assert guard.is_current(generation) is False


def test_ui_operation_guard_releases_only_the_exact_slot_owner() -> None:
    (UiOperationGuard,) = _operation_symbols("UiOperationGuard")

    guard = UiOperationGuard()
    save_owner = guard.claim("save")
    export_owner = guard.claim("export")
    assert save_owner is not None
    assert export_owner is not None
    assert export_owner is not save_owner
    assert guard.claim("save") is None
    assert guard.owns("save", save_owner) is True

    wrong_owner = object()
    assert guard.owns("save", wrong_owner) is False
    guard.release("save", wrong_owner)
    assert guard.claim("save") is None

    guard.release("save", save_owner)
    replacement_owner = guard.claim("save")
    assert replacement_owner is not None
    assert replacement_owner is not save_owner
    assert guard.owns("export", export_owner) is True


async def test_trigger_captures_payload_synchronously_before_authentication() -> None:
    BoundUiOperationScope, UiOperationPhase, UiOperationStatus = _operation_symbols(
        "BoundUiOperationScope",
        "UiOperationPhase",
        "UiOperationStatus",
    )

    opened = _session()
    auth_entered = asyncio.Event()
    release_auth = asyncio.Event()
    control = {"value": "A"}
    captured: list[str] = []
    effects: list[str] = []
    events = []

    def capture() -> _Payload:
        captured.append(control["value"])
        return _Payload(control["value"])

    async def authorize(_expected):
        auth_entered.set()
        await release_auth.wait()
        return opened

    async def effect(_current, payload):
        effects.append(payload.value)
        return payload.value

    scope = BoundUiOperationScope(opened, authorize=authorize)
    handler = scope.bind(
        slot="save",
        capture=capture,
        effect=effect,
        present=events.append,
    )

    assert inspect.iscoroutinefunction(handler) is False
    pending = handler()
    assert captured == ["A"]
    control["value"] = "B"

    task = asyncio.create_task(pending)
    await auth_entered.wait()
    release_auth.set()
    await task

    assert effects == ["A"]
    assert [event.phase for event in events] == [
        UiOperationPhase.STARTED,
        UiOperationPhase.FINISHED,
    ]
    assert events[-1].outcome.status is UiOperationStatus.SUCCEEDED
    assert events[-1].outcome.value == "A"


async def test_relogin_during_pre_auth_discards_without_effect_or_ui() -> None:
    (BoundUiOperationScope,) = _operation_symbols("BoundUiOperationScope")

    opened = _session()
    new_login = _session()
    auth_entered = asyncio.Event()
    release_auth = asyncio.Event()
    effects: list[str] = []
    events = []

    async def authorize(_expected):
        auth_entered.set()
        await release_auth.wait()
        return new_login

    async def effect(_current, payload):
        effects.append(payload.value)
        return payload.value

    scope = BoundUiOperationScope(opened, authorize=authorize)
    handler = scope.bind(
        slot="save",
        capture=lambda: _Payload("secret-click-value"),
        effect=effect,
        present=events.append,
    )

    task = asyncio.create_task(handler())
    await auth_entered.wait()
    release_auth.set()
    await task

    assert effects == []
    assert events == []


async def test_late_result_is_discarded_after_generation_changes() -> None:
    BoundUiOperationScope, UiOperationPhase = _operation_symbols(
        "BoundUiOperationScope",
        "UiOperationPhase",
    )

    opened = _session()
    effect_entered = asyncio.Event()
    release_effect = asyncio.Event()
    effects = 0
    events = []

    async def authorize(_expected):
        return opened

    async def effect(_current, _payload):
        nonlocal effects
        effects += 1
        effect_entered.set()
        await release_effect.wait()
        return "late"

    scope = BoundUiOperationScope(opened, authorize=authorize)
    handler = scope.bind(
        slot="generate",
        capture=lambda: _Payload("A"),
        effect=effect,
        present=events.append,
    )

    task = asyncio.create_task(handler())
    await effect_entered.wait()
    scope.invalidate()
    release_effect.set()
    await task

    assert effects == 1
    assert [event.phase for event in events] == [UiOperationPhase.STARTED]


async def test_double_click_is_single_flight_and_never_queued_or_retried() -> None:
    (BoundUiOperationScope,) = _operation_symbols("BoundUiOperationScope")

    opened = _session()
    effect_entered = asyncio.Event()
    release_effect = asyncio.Event()
    effects = 0
    events = []

    async def authorize(_expected):
        return opened

    async def effect(_current, _payload):
        nonlocal effects
        effects += 1
        effect_entered.set()
        await release_effect.wait()
        return "saved"

    scope = BoundUiOperationScope(opened, authorize=authorize)
    handler = scope.bind(
        slot="save",
        capture=lambda: _Payload("A"),
        effect=effect,
        present=events.append,
    )

    first = handler()
    second = handler()
    assert second is None

    task = asyncio.create_task(first)
    await effect_entered.wait()
    release_effect.set()
    await task

    assert effects == 1
    assert len(events) == 2


async def test_unexpected_failure_exposes_only_a_closed_error_code() -> None:
    BoundUiOperationScope, UiOperationPhase, UiOperationStatus = _operation_symbols(
        "BoundUiOperationScope",
        "UiOperationPhase",
        "UiOperationStatus",
    )

    opened = _session()
    secret = "sk-private-provider-secret"
    effects = 0
    events = []

    async def authorize(_expected):
        return opened

    async def effect(_current, _payload):
        nonlocal effects
        effects += 1
        raise RuntimeError(secret)

    scope = BoundUiOperationScope(opened, authorize=authorize)
    handler = scope.bind(
        slot="verify",
        capture=lambda: _Payload(secret),
        effect=effect,
        present=events.append,
    )

    await handler()

    assert effects == 1
    assert [event.phase for event in events] == [
        UiOperationPhase.STARTED,
        UiOperationPhase.FINISHED,
    ]
    outcome = events[-1].outcome
    assert outcome.status is UiOperationStatus.FAILED
    assert outcome.error_code == "operation.failed"
    assert secret not in repr(outcome)
    assert secret not in repr(events[-1])


async def test_post_auth_change_discards_effect_result_without_cleanup() -> None:
    BoundUiOperationScope, UiOperationPhase = _operation_symbols(
        "BoundUiOperationScope",
        "UiOperationPhase",
    )

    opened = _session()
    new_login = _session()
    authorizations = 0
    effects = 0
    events = []

    async def authorize(_expected):
        nonlocal authorizations
        authorizations += 1
        return opened if authorizations == 1 else new_login

    async def effect(_current, _payload):
        nonlocal effects
        effects += 1
        return "saved"

    scope = BoundUiOperationScope(opened, authorize=authorize)
    handler = scope.bind(
        slot="save",
        capture=lambda: _Payload("A"),
        effect=effect,
        present=events.append,
    )

    await handler()

    assert effects == 1
    assert [event.phase for event in events] == [UiOperationPhase.STARTED]


async def test_mutable_capture_is_deeply_frozen_before_authentication() -> None:
    (BoundUiOperationScope,) = _operation_symbols("BoundUiOperationScope")

    opened = _session()
    auth_entered = asyncio.Event()
    release_auth = asyncio.Event()
    control = {"domains": ["language"]}
    effects: list[dict[str, list[str]]] = []

    async def authorize(_expected):
        auth_entered.set()
        await release_auth.wait()
        return opened

    async def effect(_current, payload):
        effects.append(payload)

    scope = BoundUiOperationScope(opened, authorize=authorize)
    handler = scope.bind(
        slot="save",
        capture=lambda: control,
        effect=effect,
        present=lambda _event: None,
    )

    pending = handler()
    task = asyncio.create_task(pending)
    await auth_entered.wait()
    control["domains"].append("science")
    release_auth.set()
    await task

    assert effects == [{"domains": ["language"]}]


class _Uncopyable:
    def __deepcopy__(self, _memo):
        raise RuntimeError("copy failed")


@pytest.mark.parametrize("failure", ["capture", "deepcopy"])
async def test_capture_failure_does_not_invalidate_an_existing_operation(
    failure: str,
) -> None:
    BoundUiOperationScope, UiOperationPhase = _operation_symbols(
        "BoundUiOperationScope",
        "UiOperationPhase",
    )

    opened = _session()
    effect_entered = asyncio.Event()
    release_effect = asyncio.Event()
    events = []

    async def authorize(_expected):
        return opened

    async def effect(_current, _payload):
        effect_entered.set()
        await release_effect.wait()
        return "saved"

    scope = BoundUiOperationScope(opened, authorize=authorize)
    existing = scope.bind(
        slot="save",
        capture=lambda: _Payload("A"),
        effect=effect,
        present=events.append,
    )

    def failed_capture():
        if failure == "capture":
            raise RuntimeError("capture failed")
        return _Uncopyable()

    rejected = scope.bind(
        slot="other",
        capture=failed_capture,
        effect=effect,
        present=events.append,
    )

    task = asyncio.create_task(existing())
    await effect_entered.wait()
    try:
        try:
            result = rejected()
        except Exception as exc:
            result = exc
    finally:
        release_effect.set()
        await task

    assert result is None
    assert [event.phase for event in events] == [
        UiOperationPhase.STARTED,
        UiOperationPhase.FINISHED,
    ]
