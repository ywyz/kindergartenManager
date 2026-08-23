"""F007 public RED tests for cancellation, time bounds, and stale-result discard."""

import asyncio
from dataclasses import FrozenInstanceError, dataclass, field, fields, replace
from datetime import date, datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path
import subprocess
import sys
from typing import Any
from uuid import UUID

import pytest

from app.service.agent.contracts import (
    FOUNDATION_ALLOWED_PERMISSIONS,
    AgentContext,
    ClassAreasProjection,
    DailyPlanProjection,
    DailyPlanScope,
    Permission,
    PlanSection,
    TrustedActor,
)


OPERATION_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TURN_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PLAN_DATE = date(2026, 9, 7)
PLAN_SECTION_PATHS = (
    "activity_goal",
    "activity_prep",
    "activity_key",
    "activity_difficult",
    "activity_process_original",
    "activity_process_adapted",
    "morning_activity",
    "indoor_area",
    "outdoor_activity",
    "morning_talk_topic",
    "morning_talk_questions",
    "daily_reflection",
)
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _runtime_module():
    return import_module("app.service.agent.runtime")


def _context() -> AgentContext:
    created_at = datetime(2026, 9, 6, 9, 0, tzinfo=timezone.utc)
    projection = DailyPlanProjection(
        plan_id=7,
        plan_date=PLAN_DATE,
        week_number=2,
        weekday_cn="周一",
        grade="大班",
        class_name="星星班",
        sections=tuple(
            PlanSection(
                field_path=field_path,
                content="认识秋天" if field_path == "activity_goal" else "",
                truncated=False,
            )
            for field_path in PLAN_SECTION_PATHS
        ),
        updated_at_utc=datetime(2026, 9, 6, 8, 30, tzinfo=timezone.utc),
        content_sha256="e" * 64,
    )
    return AgentContext(
        context_id=UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        operation_id=OPERATION_ID,
        turn_id=TURN_ID,
        created_at_utc=created_at,
        expires_at_utc=created_at + timedelta(minutes=5),
        locale="zh-CN",
        actor=TrustedActor(tenant_id=1, user_id=10),
        active_scope=DailyPlanScope(daily_plan_id=7),
        facts=(projection,),
        base_fingerprint="d" * 64,
        allowed_permissions=FOUNDATION_ALLOWED_PERMISSIONS,
    )


def _next_context() -> AgentContext:
    return replace(
        _context(),
        context_id=UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
        operation_id=UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"),
        turn_id=UUID("ffffffff-ffff-4fff-8fff-ffffffffffff"),
    )


def _provider_result(
    runtime: Any,
    *,
    content: str | None = None,
    tool_calls: tuple[object, ...] = (),
    finish_reason: str = "completed",
):
    return runtime.ProviderTurnResult(
        assistant_content=content,
        tool_calls=tool_calls,
        finish_reason=runtime.ProviderFinishReason(finish_reason),
        provider_request_id="fictional-request-id",
    )


def _tool_call(runtime: Any, *, permission: Permission = Permission.READ):
    tool_name = (
        "settings.read_class_areas"
        if permission is Permission.READ
        else "daily_plan.draft_section_patch"
    )
    arguments: dict[str, object] = {}
    if permission is Permission.DRAFT:
        arguments = {
            "operation_id": str(OPERATION_ID),
            "turn_id": str(TURN_ID),
            "target": {
                "daily_plan_id": 7,
                "plan_date": PLAN_DATE.isoformat(),
            },
            "base_fingerprint": "d" * 64,
            "operations": [
                {
                    "field_path": "activity_goal",
                    "before_value": "认识秋天",
                    "after_value": "探索秋天",
                }
            ],
        }
    return runtime.ProviderToolCall(
        call_id=UUID(int=91 if permission is Permission.READ else 92),
        operation_id=OPERATION_ID,
        turn_id=TURN_ID,
        tool_name=tool_name,
        permission=permission,
        arguments=arguments,
    )


def _plan_patch(context: AgentContext):
    patch = import_module("app.service.agent.patch")
    return patch.build_plan_patch(
        context=context,
        proposal=patch.DraftPatchProposal(
            operation_id=context.operation_id,
            turn_id=context.turn_id,
            tool_name="daily_plan.draft_section_patch",
            target=patch.PlanPatchTarget(
                daily_plan_id=7,
                plan_date=PLAN_DATE,
            ),
            base_fingerprint=context.base_fingerprint,
            operations=(
                patch.DraftPatchOperation(
                    field_path="activity_goal",
                    before_value="认识秋天",
                    after_value="探索秋天",
                ),
            ),
        ),
    )


@dataclass
class MutableClock:
    now: datetime

    def __call__(self) -> datetime:
        return self.now


@dataclass
class MutableContextState:
    stamp: object | None
    failure: BaseException | None = None

    def current_stamp(self) -> object | None:
        if self.failure is not None:
            raise self.failure
        return self.stamp


@dataclass
class ImmediateProvider:
    content: str = "完成"
    requests: list[object] = field(default_factory=list)

    async def complete(self, request: object) -> object:
        self.requests.append(request)
        return _provider_result(_runtime_module(), content=self.content)


@dataclass
class BlockingThenSuccessProvider:
    entered: asyncio.Event
    calls: int = 0

    async def complete(self, request: object) -> object:
        self.calls += 1
        if self.calls == 1:
            self.entered.set()
            await asyncio.Event().wait()
        return _provider_result(_runtime_module(), content="下一次完成")


@dataclass
class CancellationDefyingProvider:
    entered: asyncio.Event
    cancellation_seen: asyncio.Event
    release: asyncio.Event
    calls: int = 0

    async def complete(self, request: object) -> object:
        self.calls += 1
        if self.calls == 1:
            self.entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancellation_seen.set()
                await self.release.wait()
            return _provider_result(_runtime_module(), content="取消后的迟到正文")
        return _provider_result(_runtime_module(), content="排空后完成")


@dataclass
class ReleasableProvider:
    entered: asyncio.Event
    release: asyncio.Event
    requests: list[object] = field(default_factory=list)

    async def complete(self, request: object) -> object:
        self.requests.append(request)
        self.entered.set()
        await self.release.wait()
        return _provider_result(_runtime_module(), content="迟到的敏感正文")


@dataclass
class ReleasableFailingProvider:
    entered: asyncio.Event
    release: asyncio.Event
    secret: str

    async def complete(self, request: object) -> object:
        self.entered.set()
        await self.release.wait()
        raise RuntimeError(self.secret)


@dataclass
class ToolCallingProvider:
    call: object
    requests: list[object] = field(default_factory=list)

    async def complete(self, request: object) -> object:
        self.requests.append(request)
        if len(self.requests) == 1:
            return _provider_result(
                _runtime_module(),
                tool_calls=(self.call,),
                finish_reason="tool_calls",
            )
        return _provider_result(_runtime_module(), content="不应回填")


@dataclass
class DraftThenBlockingProvider:
    call: object
    entered: asyncio.Event
    release: asyncio.Event
    requests: list[object] = field(default_factory=list)

    async def complete(self, request: object) -> object:
        self.requests.append(request)
        if len(self.requests) == 1:
            return _provider_result(
                _runtime_module(),
                tool_calls=(self.call,),
                finish_reason="tool_calls",
            )
        self.entered.set()
        await self.release.wait()
        return _provider_result(_runtime_module(), content="带部分草案的迟到正文")


@dataclass
class ImmediateExecutor:
    draft_patch: object | None = None
    calls: list[object] = field(default_factory=list)

    async def execute(self, call: object, context: AgentContext) -> object:
        runtime = _runtime_module()
        self.calls.append(call)
        value = (
            self.draft_patch
            if call.permission is Permission.DRAFT
            else ClassAreasProjection(
                grade="大班",
                class_name="星星班",
                indoor_areas="建构区",
                outdoor_content="平衡木",
            )
        )
        return runtime.ToolExecutionResult(
            call_id=call.call_id,
            operation_id=context.operation_id,
            turn_id=context.turn_id,
            tool_name=call.tool_name,
            permission=call.permission,
            status=runtime.ToolExecutionStatus.OK,
            value=value,
            error_code=None,
        )


@dataclass
class ReleasableExecutor:
    entered: asyncio.Event
    release: asyncio.Event
    calls: list[object] = field(default_factory=list)

    async def execute(self, call: object, context: AgentContext) -> object:
        runtime = _runtime_module()
        self.calls.append(call)
        self.entered.set()
        await self.release.wait()
        return runtime.ToolExecutionResult(
            call_id=call.call_id,
            operation_id=context.operation_id,
            turn_id=context.turn_id,
            tool_name=call.tool_name,
            permission=call.permission,
            status=runtime.ToolExecutionStatus.OK,
            value=ClassAreasProjection(
                grade="大班",
                class_name="星星班",
                indoor_areas="迟到区域",
                outdoor_content="迟到内容",
            ),
            error_code=None,
        )


@dataclass
class CancellationDefyingExecutor:
    entered: asyncio.Event
    cancellation_seen: asyncio.Event
    release: asyncio.Event

    async def execute(self, call: object, context: AgentContext) -> object:
        runtime = _runtime_module()
        self.entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancellation_seen.set()
            await self.release.wait()
        return runtime.ToolExecutionResult(
            call_id=call.call_id,
            operation_id=context.operation_id,
            turn_id=context.turn_id,
            tool_name=call.tool_name,
            permission=call.permission,
            status=runtime.ToolExecutionStatus.OK,
            value=ClassAreasProjection(
                grade="大班",
                class_name="星星班",
                indoor_areas="迟到区域",
                outdoor_content="迟到内容",
            ),
            error_code=None,
        )


@dataclass
class ReleasableFailingExecutor:
    entered: asyncio.Event
    release: asyncio.Event
    secret: str

    async def execute(self, call: object, context: AgentContext) -> object:
        self.entered.set()
        await self.release.wait()
        raise RuntimeError(self.secret)


@dataclass
class InternalStopMimickingProvider:
    secret: str

    async def complete(self, request: object) -> object:
        raise _runtime_module()._OperationStopped(self.secret)


@dataclass
class InternalStopMimickingExecutor:
    secret: str

    async def execute(self, call: object, context: AgentContext) -> object:
        raise _runtime_module()._OperationStopped(self.secret)


@dataclass
class CancelledClock:
    def __call__(self) -> datetime:
        raise asyncio.CancelledError


def _agent(
    runtime: Any,
    provider: object,
    *,
    executor: object | None = None,
    context: AgentContext | None = None,
    state: MutableContextState | None = None,
    clock: MutableClock | None = None,
    limits: object | None = None,
):
    active_context = context or _context()
    active_state = state or MutableContextState(
        runtime.AgentContextStamp.from_context(active_context)
    )
    active_clock = clock or MutableClock(active_context.created_at_utc)
    registry = import_module("app.service.agent.registry").build_foundation_registry()
    return runtime.AgentRuntime(
        provider=provider,
        executor=executor or ImmediateExecutor(),
        registry=registry,
        context_state=active_state,
        clock=active_clock,
        limits=limits or runtime.RuntimeLimits(),
    )


async def _run_after_drain(
    runtime: Any,
    agent: object,
    state: MutableContextState,
):
    next_context = _next_context()
    state.stamp = runtime.AgentContextStamp.from_context(next_context)
    async with asyncio.timeout(1):
        while True:
            outcome = await agent.run_turn(context=next_context, intent="排空后重试")
            if outcome.error_code != "agent.busy":
                return outcome
            await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_runtime_cancels_only_the_exact_active_operation_and_recovers():
    runtime = _runtime_module()
    entered = asyncio.Event()
    provider = BlockingThenSuccessProvider(entered)
    state = MutableContextState(runtime.AgentContextStamp.from_context(_context()))
    agent = _agent(runtime, provider, state=state)

    first = asyncio.create_task(agent.run_turn(context=_context(), intent="运行"))
    await asyncio.wait_for(entered.wait(), 1)

    wrong_context = replace(_context(), operation_id=UUID(int=999))
    assert (
        await agent.cancel(runtime.AgentContextStamp.from_context(wrong_context))
        is False
    )
    busy = await agent.run_turn(context=_context(), intent="并发请求")
    assert busy.error_code == "agent.busy"
    assert (
        await agent.cancel(runtime.AgentContextStamp.from_context(_context())) is True
    )

    cancelled = await asyncio.wait_for(first, 1)
    assert cancelled.status is runtime.AgentTurnStatus.CANCELLED
    assert cancelled.error_code == "agent.cancelled"
    assert cancelled.assistant_content is None
    assert cancelled.patches == ()

    next_context = _next_context()
    state.stamp = runtime.AgentContextStamp.from_context(next_context)
    recovered = await agent.run_turn(context=next_context, intent="下一次")
    assert recovered.status is runtime.AgentTurnStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_runtime_keeps_busy_until_a_cancel_defying_provider_is_drained():
    runtime = _runtime_module()
    provider = CancellationDefyingProvider(
        asyncio.Event(),
        asyncio.Event(),
        asyncio.Event(),
    )
    state = MutableContextState(runtime.AgentContextStamp.from_context(_context()))
    agent = _agent(runtime, provider, state=state)

    pending = asyncio.create_task(agent.run_turn(context=_context(), intent="运行"))
    await asyncio.wait_for(provider.entered.wait(), 1)
    assert (
        await agent.cancel(runtime.AgentContextStamp.from_context(_context())) is True
    )
    await asyncio.wait_for(provider.cancellation_seen.wait(), 1)

    busy = await agent.run_turn(context=_context(), intent="排空前请求")
    assert busy.error_code == "agent.busy"
    provider.release.set()

    outcome = await asyncio.wait_for(pending, 1)
    assert outcome.status is runtime.AgentTurnStatus.CANCELLED
    assert outcome.assistant_content is None
    assert "取消后的迟到正文" not in repr(outcome)
    next_context = _next_context()
    state.stamp = runtime.AgentContextStamp.from_context(next_context)
    recovered = await agent.run_turn(context=next_context, intent="排空后请求")
    assert recovered.status is runtime.AgentTurnStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_host_task_cancellation_propagates_and_releases_busy():
    runtime = _runtime_module()
    provider = BlockingThenSuccessProvider(asyncio.Event())
    state = MutableContextState(runtime.AgentContextStamp.from_context(_context()))
    agent = _agent(runtime, provider, state=state)

    pending = asyncio.create_task(agent.run_turn(context=_context(), intent="宿主关闭"))
    await asyncio.wait_for(provider.entered.wait(), 1)
    pending.cancel()

    with pytest.raises(asyncio.CancelledError):
        await pending
    next_context = _next_context()
    state.stamp = runtime.AgentContextStamp.from_context(next_context)
    recovered = await agent.run_turn(context=next_context, intent="重新进入")
    assert recovered.status is runtime.AgentTurnStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_runtime_total_timeout_is_sanitized_and_releases_busy():
    runtime = _runtime_module()
    provider = BlockingThenSuccessProvider(asyncio.Event())
    state = MutableContextState(runtime.AgentContextStamp.from_context(_context()))
    agent = _agent(
        runtime,
        provider,
        state=state,
        limits=runtime.RuntimeLimits(max_total_duration_ms=50),
    )

    timed_out = await asyncio.wait_for(
        agent.run_turn(context=_context(), intent="等待超时"),
        1,
    )

    assert timed_out.status is runtime.AgentTurnStatus.FAILED
    assert timed_out.error_code == "agent.timeout"
    assert timed_out.assistant_content is None
    assert timed_out.patches == ()
    next_context = _next_context()
    state.stamp = runtime.AgentContextStamp.from_context(next_context)
    recovered = await agent.run_turn(context=next_context, intent="超时后重试")
    assert recovered.status is runtime.AgentTurnStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_runtime_single_provider_timeout_stops_before_any_tool():
    runtime = _runtime_module()
    provider = BlockingThenSuccessProvider(asyncio.Event())
    executor = ImmediateExecutor()
    state = MutableContextState(runtime.AgentContextStamp.from_context(_context()))
    agent = _agent(
        runtime,
        provider,
        executor=executor,
        state=state,
        limits=runtime.RuntimeLimits(
            max_provider_duration_ms=50,
            max_total_duration_ms=500,
        ),
    )

    timed_out = await asyncio.wait_for(
        agent.run_turn(context=_context(), intent="单次 Provider 超时"),
        1,
    )

    assert timed_out.status is runtime.AgentTurnStatus.FAILED
    assert timed_out.error_code == "agent.timeout"
    assert timed_out.assistant_content is None
    assert timed_out.patches == ()
    assert executor.calls == []
    next_context = _next_context()
    state.stamp = runtime.AgentContextStamp.from_context(next_context)
    recovered = await agent.run_turn(context=next_context, intent="Provider 超时后")
    assert recovered.status is runtime.AgentTurnStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_runtime_single_tool_timeout_stops_before_provider_reentry():
    runtime = _runtime_module()
    call = _tool_call(runtime)
    provider = ToolCallingProvider(call)
    executor = ReleasableExecutor(asyncio.Event(), asyncio.Event())
    state = MutableContextState(runtime.AgentContextStamp.from_context(_context()))
    agent = _agent(
        runtime,
        provider,
        executor=executor,
        state=state,
        limits=runtime.RuntimeLimits(
            max_tool_duration_ms=50,
            max_total_duration_ms=500,
        ),
    )

    timed_out = await asyncio.wait_for(
        agent.run_turn(context=_context(), intent="读取区域"),
        1,
    )

    assert timed_out.error_code == "agent.timeout"
    assert timed_out.assistant_content is None
    assert timed_out.patches == ()
    assert len(provider.requests) == 1
    next_context = _next_context()
    state.stamp = runtime.AgentContextStamp.from_context(next_context)
    recovered = await agent.run_turn(context=next_context, intent="Tool 超时后")
    assert recovered.status is runtime.AgentTurnStatus.SUCCEEDED


@pytest.mark.parametrize(
    "invalid_state", (None, object(), RuntimeError("state-secret"))
)
@pytest.mark.asyncio
async def test_runtime_fails_closed_when_current_context_is_unavailable(
    invalid_state: object,
):
    runtime = _runtime_module()
    provider = ImmediateProvider()
    state = (
        MutableContextState(None, failure=invalid_state)
        if isinstance(invalid_state, BaseException)
        else MutableContextState(invalid_state)
    )
    agent = _agent(runtime, provider, state=state)

    outcome = await agent.run_turn(context=_context(), intent="检查 current state")

    assert outcome.error_code == "agent.context_stale"
    assert outcome.assistant_content is None
    assert provider.requests == []
    assert "state-secret" not in repr(outcome)


@pytest.mark.parametrize(
    "clock_offset", (-timedelta(microseconds=1), timedelta(minutes=5))
)
@pytest.mark.asyncio
async def test_runtime_rejects_a_future_or_expired_context_before_provider_entry(
    clock_offset: timedelta,
):
    runtime = _runtime_module()
    context = _context()
    provider = ImmediateProvider()
    clock = MutableClock(context.created_at_utc + clock_offset)
    agent = _agent(runtime, provider, context=context, clock=clock)

    outcome = await agent.run_turn(context=context, intent="过期请求")

    assert outcome.error_code == "agent.context_stale"
    assert provider.requests == []


@pytest.mark.parametrize(
    "context_change",
    (
        {"context_id": UUID(int=201)},
        {"operation_id": UUID(int=202)},
        {"turn_id": UUID(int=203)},
        {"actor": TrustedActor(tenant_id=1, user_id=11)},
        {"active_scope": DailyPlanScope(plan_date=date(2026, 9, 8))},
        {"base_fingerprint": "f" * 64},
    ),
)
@pytest.mark.asyncio
async def test_runtime_treats_any_context_stamp_change_as_stale(
    context_change: dict[str, object],
):
    runtime = _runtime_module()
    context = _context()
    provider = ImmediateProvider()
    changed_context = replace(context, **context_change)
    state = MutableContextState(runtime.AgentContextStamp.from_context(changed_context))
    agent = _agent(runtime, provider, context=context, state=state)

    outcome = await agent.run_turn(context=context, intent="检查 stamp 变化")

    assert outcome.error_code == "agent.context_stale"
    assert provider.requests == []


@pytest.mark.asyncio
async def test_runtime_discards_provider_result_after_scope_or_fingerprint_change():
    runtime = _runtime_module()
    context = _context()
    entered = asyncio.Event()
    release = asyncio.Event()
    provider = ReleasableProvider(entered, release)
    state = MutableContextState(runtime.AgentContextStamp.from_context(context))
    agent = _agent(runtime, provider, context=context, state=state)

    pending = asyncio.create_task(agent.run_turn(context=context, intent="读取计划"))
    await asyncio.wait_for(entered.wait(), 1)
    changed_context = replace(
        context,
        active_scope=DailyPlanScope(plan_date=date(2026, 9, 8)),
        base_fingerprint="f" * 64,
    )
    state.stamp = runtime.AgentContextStamp.from_context(changed_context)
    release.set()

    outcome = await asyncio.wait_for(pending, 1)
    assert outcome.error_code == "agent.context_stale"
    assert outcome.assistant_content is None
    assert outcome.patches == ()
    assert "迟到的敏感正文" not in repr(outcome)


@pytest.mark.asyncio
async def test_runtime_discards_late_tool_result_before_provider_reentry():
    runtime = _runtime_module()
    context = _context()
    call = _tool_call(runtime)
    provider = ToolCallingProvider(call)
    entered = asyncio.Event()
    release = asyncio.Event()
    executor = ReleasableExecutor(entered, release)
    state = MutableContextState(runtime.AgentContextStamp.from_context(context))
    agent = _agent(
        runtime,
        provider,
        executor=executor,
        context=context,
        state=state,
    )

    pending = asyncio.create_task(agent.run_turn(context=context, intent="读取区域"))
    await asyncio.wait_for(entered.wait(), 1)
    state.stamp = runtime.AgentContextStamp.from_context(
        replace(context, base_fingerprint="f" * 64)
    )
    release.set()

    outcome = await asyncio.wait_for(pending, 1)
    assert outcome.error_code == "agent.context_stale"
    assert outcome.assistant_content is None
    assert outcome.patches == ()
    assert len(provider.requests) == 1


@pytest.mark.asyncio
async def test_runtime_cancellation_drops_an_inflight_tool_result():
    runtime = _runtime_module()
    call = _tool_call(runtime)
    provider = ToolCallingProvider(call)
    entered = asyncio.Event()
    executor = ReleasableExecutor(entered, asyncio.Event())
    agent = _agent(runtime, provider, executor=executor)

    pending = asyncio.create_task(agent.run_turn(context=_context(), intent="读取区域"))
    await asyncio.wait_for(entered.wait(), 1)
    assert (
        await agent.cancel(runtime.AgentContextStamp.from_context(_context())) is True
    )

    outcome = await asyncio.wait_for(pending, 1)
    assert outcome.status is runtime.AgentTurnStatus.CANCELLED
    assert outcome.error_code == "agent.cancelled"
    assert outcome.assistant_content is None
    assert outcome.patches == ()
    assert len(provider.requests) == 1


@pytest.mark.asyncio
async def test_runtime_discards_all_partial_patches_when_context_becomes_stale():
    runtime = _runtime_module()
    context = _context()
    call = _tool_call(runtime, permission=Permission.DRAFT)
    entered = asyncio.Event()
    release = asyncio.Event()
    provider = DraftThenBlockingProvider(call, entered, release)
    state = MutableContextState(runtime.AgentContextStamp.from_context(context))
    executor = ImmediateExecutor(draft_patch=_plan_patch(context))
    agent = _agent(
        runtime,
        provider,
        executor=executor,
        context=context,
        state=state,
    )

    pending = asyncio.create_task(agent.run_turn(context=context, intent="生成草案"))
    await asyncio.wait_for(entered.wait(), 1)
    state.stamp = runtime.AgentContextStamp.from_context(
        replace(context, base_fingerprint="f" * 64)
    )
    release.set()

    outcome = await asyncio.wait_for(pending, 1)
    assert outcome.error_code == "agent.context_stale"
    assert outcome.assistant_content is None
    assert outcome.patches == ()


def test_foundation_tool_descriptors_publish_positive_local_timeouts():
    registry = import_module("app.service.agent.registry").build_foundation_registry()

    assert all(
        type(descriptor.timeout_ms) is int and descriptor.timeout_ms > 0
        for descriptor in registry.descriptors()
    )


def test_context_stamp_is_a_closed_frozen_copy_of_the_live_binding():
    runtime = _runtime_module()
    context = _context()
    stamp = runtime.AgentContextStamp.from_context(context)

    assert {item.name for item in fields(stamp)} == {
        "context_id",
        "operation_id",
        "turn_id",
        "actor",
        "active_scope",
        "base_fingerprint",
    }
    assert stamp.operation_id == context.operation_id
    assert stamp.active_scope == context.active_scope
    with pytest.raises(FrozenInstanceError):
        stamp.base_fingerprint = "f" * 64


@pytest.mark.asyncio
async def test_runtime_rechecks_context_ttl_before_publishing_terminal_output():
    runtime = _runtime_module()
    context = _context()
    entered = asyncio.Event()
    release = asyncio.Event()
    provider = ReleasableProvider(entered, release)
    clock = MutableClock(context.created_at_utc)
    agent = _agent(runtime, provider, context=context, clock=clock)

    pending = asyncio.create_task(agent.run_turn(context=context, intent="读取计划"))
    await asyncio.wait_for(entered.wait(), 1)
    clock.now = context.expires_at_utc
    release.set()

    outcome = await asyncio.wait_for(pending, 1)
    assert outcome.error_code == "agent.context_stale"
    assert outcome.assistant_content is None
    assert outcome.patches == ()


@pytest.mark.asyncio
async def test_provider_cannot_forge_runtime_stop_control_flow_or_public_error_codes():
    runtime = _runtime_module()
    secret = "secret-provider-payload"
    agent = _agent(runtime, InternalStopMimickingProvider(secret))

    outcome = await agent.run_turn(context=_context(), intent="检查 Provider 异常")

    assert outcome.status is runtime.AgentTurnStatus.FAILED
    assert outcome.error_code == "agent.provider_failed"
    assert outcome.assistant_content is None
    assert outcome.patches == ()
    assert secret not in repr(outcome)


@pytest.mark.asyncio
async def test_executor_cannot_forge_runtime_stop_control_flow_or_public_error_codes():
    runtime = _runtime_module()
    secret = "secret-executor-payload"
    call = _tool_call(runtime)
    provider = ToolCallingProvider(call)
    agent = _agent(
        runtime,
        provider,
        executor=InternalStopMimickingExecutor(secret),
    )

    outcome = await agent.run_turn(context=_context(), intent="检查 Executor 异常")

    assert outcome.status is runtime.AgentTurnStatus.FAILED
    assert outcome.error_code == "agent.tool_failed"
    assert outcome.assistant_content is None
    assert outcome.patches == ()
    assert secret not in repr(outcome)


@pytest.mark.parametrize("failing_port", ("clock", "context_state"))
@pytest.mark.asyncio
async def test_port_originated_cancelled_error_fails_closed_without_host_cancellation(
    failing_port: str,
):
    runtime = _runtime_module()
    context = _context()
    provider = ImmediateProvider()
    state = MutableContextState(runtime.AgentContextStamp.from_context(context))
    clock: object = MutableClock(context.created_at_utc)
    if failing_port == "clock":
        clock = CancelledClock()
    else:
        state.failure = asyncio.CancelledError()
    agent = _agent(runtime, provider, state=state, clock=clock)

    outcome = await agent.run_turn(context=context, intent="检查伪取消")

    assert outcome.status is runtime.AgentTurnStatus.FAILED
    assert outcome.error_code == "agent.context_stale"
    assert outcome.assistant_content is None
    assert outcome.patches == ()
    assert provider.requests == []


@pytest.mark.parametrize("limit_kind", ("provider", "total"))
@pytest.mark.asyncio
async def test_provider_and_total_limits_return_before_a_cancel_defying_port_drains(
    limit_kind: str,
):
    runtime = _runtime_module()
    provider = CancellationDefyingProvider(
        asyncio.Event(),
        asyncio.Event(),
        asyncio.Event(),
    )
    state = MutableContextState(runtime.AgentContextStamp.from_context(_context()))
    limits = (
        runtime.RuntimeLimits(
            max_provider_duration_ms=20,
            max_total_duration_ms=500,
        )
        if limit_kind == "provider"
        else runtime.RuntimeLimits(
            max_provider_duration_ms=500,
            max_total_duration_ms=20,
        )
    )
    agent = _agent(runtime, provider, state=state, limits=limits)

    outcome = await asyncio.wait_for(
        agent.run_turn(context=_context(), intent="硬时限"),
        1,
    )

    assert outcome.status is runtime.AgentTurnStatus.FAILED
    assert outcome.error_code == "agent.timeout"
    assert outcome.assistant_content is None
    assert outcome.patches == ()
    await asyncio.wait_for(provider.cancellation_seen.wait(), 1)
    busy = await agent.run_turn(context=_context(), intent="排空前")
    assert busy.error_code == "agent.busy"

    provider.release.set()
    recovered = await _run_after_drain(runtime, agent, state)
    assert recovered.status is runtime.AgentTurnStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_tool_limit_returns_before_a_cancel_defying_executor_drains():
    runtime = _runtime_module()
    provider = ToolCallingProvider(_tool_call(runtime))
    executor = CancellationDefyingExecutor(
        asyncio.Event(),
        asyncio.Event(),
        asyncio.Event(),
    )
    state = MutableContextState(runtime.AgentContextStamp.from_context(_context()))
    agent = _agent(
        runtime,
        provider,
        executor=executor,
        state=state,
        limits=runtime.RuntimeLimits(
            max_tool_duration_ms=20,
            max_total_duration_ms=500,
        ),
    )

    outcome = await asyncio.wait_for(
        agent.run_turn(context=_context(), intent="Tool 硬时限"),
        1,
    )

    assert outcome.status is runtime.AgentTurnStatus.FAILED
    assert outcome.error_code == "agent.timeout"
    assert outcome.assistant_content is None
    assert outcome.patches == ()
    await asyncio.wait_for(executor.cancellation_seen.wait(), 1)
    busy = await agent.run_turn(context=_context(), intent="排空前")
    assert busy.error_code == "agent.busy"

    executor.release.set()
    recovered = await _run_after_drain(runtime, agent, state)
    assert recovered.status is runtime.AgentTurnStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_host_cancellation_propagates_before_a_cancel_defying_port_drains():
    runtime = _runtime_module()
    provider = CancellationDefyingProvider(
        asyncio.Event(),
        asyncio.Event(),
        asyncio.Event(),
    )
    state = MutableContextState(runtime.AgentContextStamp.from_context(_context()))
    agent = _agent(runtime, provider, state=state)
    pending = asyncio.create_task(
        agent.run_turn(context=_context(), intent="宿主取消硬边界")
    )
    await asyncio.wait_for(provider.entered.wait(), 1)

    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(pending, 1)

    await asyncio.wait_for(provider.cancellation_seen.wait(), 1)
    busy = await agent.run_turn(context=_context(), intent="排空前")
    assert busy.error_code == "agent.busy"
    provider.release.set()
    recovered = await _run_after_drain(runtime, agent, state)
    assert recovered.status is runtime.AgentTurnStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_provider_failure_rechecks_current_context_before_terminal_output():
    runtime = _runtime_module()
    context = _context()
    provider = ReleasableFailingProvider(
        asyncio.Event(),
        asyncio.Event(),
        "provider-failure-secret",
    )
    state = MutableContextState(runtime.AgentContextStamp.from_context(context))
    agent = _agent(runtime, provider, context=context, state=state)
    pending = asyncio.create_task(
        agent.run_turn(context=context, intent="异常终态复核")
    )
    await asyncio.wait_for(provider.entered.wait(), 1)
    state.stamp = runtime.AgentContextStamp.from_context(
        replace(context, base_fingerprint="f" * 64)
    )
    provider.release.set()

    outcome = await asyncio.wait_for(pending, 1)

    assert outcome.error_code == "agent.context_stale"
    assert outcome.assistant_content is None
    assert outcome.patches == ()
    assert provider.secret not in repr(outcome)


@pytest.mark.asyncio
async def test_tool_failure_rechecks_current_context_before_terminal_output():
    runtime = _runtime_module()
    context = _context()
    provider = ToolCallingProvider(_tool_call(runtime))
    executor = ReleasableFailingExecutor(
        asyncio.Event(),
        asyncio.Event(),
        "tool-failure-secret",
    )
    state = MutableContextState(runtime.AgentContextStamp.from_context(context))
    agent = _agent(
        runtime,
        provider,
        executor=executor,
        context=context,
        state=state,
    )
    pending = asyncio.create_task(
        agent.run_turn(context=context, intent="Tool 异常终态复核")
    )
    await asyncio.wait_for(executor.entered.wait(), 1)
    state.stamp = runtime.AgentContextStamp.from_context(
        replace(context, base_fingerprint="f" * 64)
    )
    executor.release.set()

    outcome = await asyncio.wait_for(pending, 1)

    assert outcome.error_code == "agent.context_stale"
    assert outcome.assistant_content is None
    assert outcome.patches == ()
    assert executor.secret not in repr(outcome)


@pytest.mark.asyncio
async def test_drain_registration_survives_host_cancellation_interleaving():
    runtime = _runtime_module()
    provider = CancellationDefyingProvider(
        asyncio.Event(),
        asyncio.Event(),
        asyncio.Event(),
    )
    state = MutableContextState(runtime.AgentContextStamp.from_context(_context()))
    agent = _agent(runtime, provider, state=state)
    pending = asyncio.create_task(agent.run_turn(context=_context(), intent="取消交错"))
    await asyncio.wait_for(provider.entered.wait(), 1)

    assert (
        await agent.cancel(runtime.AgentContextStamp.from_context(_context())) is True
    )
    await asyncio.wait_for(provider.cancellation_seen.wait(), 1)
    await asyncio.sleep(0)
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending

    next_context = _next_context()
    state.stamp = runtime.AgentContextStamp.from_context(next_context)
    blocked = await agent.run_turn(context=next_context, intent="旧端口仍在排空")
    try:
        assert blocked.error_code == "agent.busy"
        assert provider.calls == 1
    finally:
        provider.release.set()
    recovered = await _run_after_drain(runtime, agent, state)
    assert recovered.status is runtime.AgentTurnStatus.SUCCEEDED


@pytest.mark.parametrize(
    ("port_kind", "exception_name", "expected_code"),
    (
        ("provider", "SystemExit", "agent.provider_failed"),
        ("executor", "KeyboardInterrupt", "agent.tool_failed"),
    ),
)
def test_port_base_exceptions_are_sanitized_inside_the_child_task_boundary(
    port_kind: str,
    exception_name: str,
    expected_code: str,
):
    secret = f"{port_kind}-base-exception-secret"
    probe = f"""
import asyncio
import runpy

namespace = runpy.run_path({str(Path(__file__))!r})
runtime = namespace["_runtime_module"]()

class ExplodingPort:
    async def complete(self, request):
        raise {exception_name}({secret!r})

    async def execute(self, call, context):
        raise {exception_name}({secret!r})

async def main():
    if {port_kind!r} == "provider":
        agent = namespace["_agent"](runtime, ExplodingPort())
    else:
        call = namespace["_tool_call"](runtime)
        provider = namespace["ToolCallingProvider"](call)
        agent = namespace["_agent"](
            runtime,
            provider,
            executor=ExplodingPort(),
        )
    outcome = await agent.run_turn(
        context=namespace["_context"](),
        intent="BaseException boundary",
    )
    print(outcome.error_code)

asyncio.run(main())
"""

    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.strip() == expected_code
    assert secret not in completed.stdout
    assert secret not in completed.stderr
