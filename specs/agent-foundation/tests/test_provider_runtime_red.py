"""F006 public RED tests for the provider port and bounded serial runtime."""

import ast
import asyncio
from dataclasses import FrozenInstanceError, dataclass, field, fields, replace
from datetime import date, datetime, timedelta, timezone
from importlib import import_module
import inspect
from typing import Any
from uuid import UUID

import pytest

from app.service.agent.contracts import (
    FOUNDATION_ALLOWED_PERMISSIONS,
    AgentContext,
    DailyPlanProjection,
    DailyPlanScope,
    Permission,
    PlanSection,
    TrustedActor,
)


OPERATION_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TURN_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
PLAN_DATE = date(2026, 9, 7)
BASE_FINGERPRINT = "d" * 64
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


def _runtime_module():
    return import_module("app.service.agent.runtime")


def _context() -> AgentContext:
    sections = tuple(
        PlanSection(
            field_path=field_path,
            content="认识秋天" if field_path == "activity_goal" else "",
            truncated=False,
        )
        for field_path in PLAN_SECTION_PATHS
    )
    projection = DailyPlanProjection(
        plan_id=7,
        plan_date=PLAN_DATE,
        week_number=2,
        weekday_cn="周一",
        grade="大班",
        class_name="星星班",
        sections=sections,
        updated_at_utc=datetime(2026, 9, 6, 8, 30, tzinfo=timezone.utc),
        content_sha256="e" * 64,
    )
    created_at = datetime(2026, 9, 6, 9, 0, tzinfo=timezone.utc)
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
        base_fingerprint=BASE_FINGERPRINT,
        allowed_permissions=FOUNDATION_ALLOWED_PERMISSIONS,
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


def _tool_call(
    runtime: Any,
    *,
    call_id: int,
    tool_name: str = "settings.read_class_areas",
    permission: Permission = Permission.READ,
    arguments: dict[str, object] | None = None,
    operation_id: UUID = OPERATION_ID,
    turn_id: UUID = TURN_ID,
):
    return runtime.ProviderToolCall(
        call_id=UUID(int=call_id),
        operation_id=operation_id,
        turn_id=turn_id,
        tool_name=tool_name,
        permission=permission,
        arguments={} if arguments is None else arguments,
    )


def _draft_arguments() -> dict[str, object]:
    return {
        "operation_id": str(OPERATION_ID),
        "turn_id": str(TURN_ID),
        "target": {"daily_plan_id": 7, "plan_date": PLAN_DATE.isoformat()},
        "base_fingerprint": BASE_FINGERPRINT,
        "operations": [
            {
                "field_path": "activity_goal",
                "before_value": "认识秋天",
                "after_value": "探索秋天",
            }
        ],
        "warnings": ["请教师复核"],
    }


def _plan_patch(context: AgentContext):
    patch = import_module("app.service.agent.patch")
    proposal = patch.DraftPatchProposal(
        operation_id=context.operation_id,
        turn_id=context.turn_id,
        tool_name="daily_plan.draft_section_patch",
        target=patch.PlanPatchTarget(daily_plan_id=7, plan_date=PLAN_DATE),
        base_fingerprint=context.base_fingerprint,
        operations=(
            patch.DraftPatchOperation(
                field_path="activity_goal",
                before_value="认识秋天",
                after_value="探索秋天",
            ),
        ),
        warnings=("请教师复核",),
    )
    return patch.build_plan_patch(context=context, proposal=proposal)


@dataclass
class ScriptedProvider:
    responses: list[object]
    requests: list[object] = field(default_factory=list)

    async def complete(self, request: object) -> object:
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


@dataclass
class ScriptedExecutor:
    draft_patch: object | None = None
    calls: list[object] = field(default_factory=list)
    active: int = 0
    max_active: int = 0
    corrupt_binding: bool = False

    async def execute(self, call: object, context: AgentContext) -> object:
        runtime = _runtime_module()
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.calls.append(call)
        await asyncio.sleep(0)
        self.active -= 1
        value = (
            self.draft_patch if call.permission is Permission.DRAFT else {"ok": True}
        )
        return runtime.ToolExecutionResult(
            call_id=UUID(int=999) if self.corrupt_binding else call.call_id,
            operation_id=context.operation_id,
            turn_id=context.turn_id,
            tool_name=call.tool_name,
            permission=call.permission,
            status=runtime.ToolExecutionStatus.OK,
            value=value,
            error_code=None,
        )


def _agent_runtime(
    runtime: Any,
    provider: object,
    executor: object | None = None,
    *,
    limits: object | None = None,
):
    registry = import_module("app.service.agent.registry").build_foundation_registry()
    return runtime.AgentRuntime(
        provider=provider,
        executor=executor or ScriptedExecutor(),
        registry=registry,
        limits=limits or runtime.RuntimeLimits(),
    )


def test_provider_contracts_are_frozen_application_owned_and_closed():
    runtime = _runtime_module()
    registry = import_module("app.service.agent.registry").build_foundation_registry()
    context = _context()
    message = runtime.ProviderMessage(
        role=runtime.ProviderRole.USER, content="查看计划"
    )
    request = runtime.ProviderTurnRequest(
        operation_id=context.operation_id,
        local_policy_version="agent-foundation-v1",
        context=context,
        messages=(message,),
        tools=registry.descriptors(),
        response_limit=4096,
    )

    assert {item.name for item in fields(request)} == {
        "operation_id",
        "local_policy_version",
        "context",
        "messages",
        "tools",
        "response_limit",
    }
    assert isinstance(ScriptedProvider([]), runtime.AgentProviderPort)
    assert all(
        tool.input_schema.additional_properties is False for tool in request.tools
    )
    draft_schema = request.tools[4].input_schema
    assert draft_schema.required_fields == frozenset(
        {"operation_id", "turn_id", "target", "base_fingerprint", "operations"}
    )
    assert draft_schema.optional_fields == frozenset({"warnings"})
    assert "查看计划" not in repr(message)
    with pytest.raises(FrozenInstanceError):
        request.response_limit = 1


def test_provider_and_runtime_modules_do_not_leak_sdk_ui_or_persistence_types():
    runtime = _runtime_module()
    tree = ast.parse(inspect.getsource(runtime))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert not any(
        module == "httpx"
        or module.startswith("openai")
        or module == "nicegui"
        or module.startswith("app.ui")
        or module.startswith("app.core.database")
        or module.startswith("app.repository")
        for module in imported_modules
    )


@pytest.mark.asyncio
async def test_runtime_returns_bounded_plain_text_without_calling_tools():
    runtime = _runtime_module()
    provider = ScriptedProvider([_provider_result(runtime, content="当前计划已读取。")])
    executor = ScriptedExecutor()
    agent = _agent_runtime(runtime, provider, executor)

    outcome = await agent.run_turn(context=_context(), intent="请概括当前计划")

    assert outcome.status is runtime.AgentTurnStatus.SUCCEEDED
    assert outcome.assistant_content == "当前计划已读取。"
    assert outcome.patches == ()
    assert outcome.error_code is None
    assert executor.calls == []
    request = provider.requests[0]
    assert request.context is _context() or request.context == _context()
    assert request.operation_id == OPERATION_ID
    assert request.local_policy_version == "agent-foundation-v1"
    assert tuple(message.role for message in request.messages) == (
        runtime.ProviderRole.USER,
    )
    assert tuple(tool.name for tool in request.tools) == (
        "daily_plan.read_current",
        "daily_plan.read_context",
        "calendar.read_evaluation",
        "settings.read_class_areas",
        "daily_plan.draft_section_patch",
        "daily_plan.draft_reflection_patch",
    )


@pytest.mark.asyncio
async def test_runtime_executes_provider_tool_calls_serially_in_stable_order():
    runtime = _runtime_module()
    calls = (
        _tool_call(runtime, call_id=1),
        _tool_call(runtime, call_id=2, tool_name="daily_plan.read_current"),
    )
    provider = ScriptedProvider(
        [
            _provider_result(runtime, tool_calls=calls, finish_reason="tool_calls"),
            _provider_result(runtime, content="读取完成。"),
        ]
    )
    executor = ScriptedExecutor()
    agent = _agent_runtime(runtime, provider, executor)

    outcome = await agent.run_turn(context=_context(), intent="读取上下文")

    assert outcome.status is runtime.AgentTurnStatus.SUCCEEDED
    assert tuple(call.call_id for call in executor.calls) == (UUID(int=1), UUID(int=2))
    assert executor.max_active == 1
    assert tuple(message.role for message in provider.requests[1].messages) == (
        runtime.ProviderRole.USER,
        runtime.ProviderRole.ASSISTANT,
        runtime.ProviderRole.TOOL,
    )


@pytest.mark.asyncio
async def test_runtime_returns_only_a_f005_bound_plan_patch_from_draft_result():
    runtime = _runtime_module()
    context = _context()
    call = _tool_call(
        runtime,
        call_id=3,
        tool_name="daily_plan.draft_section_patch",
        permission=Permission.DRAFT,
        arguments=_draft_arguments(),
    )
    provider = ScriptedProvider(
        [
            _provider_result(runtime, tool_calls=(call,), finish_reason="tool_calls"),
            _provider_result(runtime, content="草案已生成。"),
        ]
    )
    patch = _plan_patch(context)
    agent = _agent_runtime(runtime, provider, ScriptedExecutor(draft_patch=patch))

    outcome = await agent.run_turn(context=context, intent="调整活动目标")

    assert outcome.status is runtime.AgentTurnStatus.DRAFT_READY
    assert outcome.patches == (patch,)
    assert outcome.patches[0].operation_id == context.operation_id
    assert outcome.patches[0].turn_id == context.turn_id
    assert outcome.patches[0].base_fingerprint == context.base_fingerprint


@dataclass
class BlockingProvider:
    entered: asyncio.Event
    release: asyncio.Event

    async def complete(self, _request: object) -> object:
        runtime = _runtime_module()
        self.entered.set()
        await self.release.wait()
        return _provider_result(runtime, content="完成")


@pytest.mark.asyncio
async def test_runtime_rejects_a_second_concurrent_operation_as_busy():
    runtime = _runtime_module()
    entered = asyncio.Event()
    release = asyncio.Event()
    agent = _agent_runtime(runtime, BlockingProvider(entered, release))

    first = asyncio.create_task(agent.run_turn(context=_context(), intent="第一个请求"))
    await entered.wait()
    second = await agent.run_turn(context=_context(), intent="第二个请求")
    release.set()
    first_outcome = await first

    assert second.status is runtime.AgentTurnStatus.FAILED
    assert second.error_code == "agent.busy"
    assert first_outcome.status is runtime.AgentTurnStatus.SUCCEEDED


@pytest.mark.parametrize(
    ("call_change", "expected_code"),
    (
        ({"tool_name": "daily_plan.delete"}, "agent.tool_not_allowed"),
        ({"permission": Permission.WRITE}, "agent.tool_not_allowed"),
        ({"permission": Permission.DRAFT}, "agent.tool_not_allowed"),
        ({"arguments": {"unexpected": True}}, "agent.tool_schema_invalid"),
        (
            {"operation_id": UUID("11111111-1111-4111-8111-111111111111")},
            "agent.tool_schema_invalid",
        ),
        (
            {"turn_id": UUID("22222222-2222-4222-8222-222222222222")},
            "agent.tool_schema_invalid",
        ),
    ),
)
@pytest.mark.asyncio
async def test_runtime_rejects_untrusted_tool_call_expansion(
    call_change: dict[str, object],
    expected_code: str,
):
    runtime = _runtime_module()
    call = replace(_tool_call(runtime, call_id=4), **call_change)
    provider = ScriptedProvider(
        [_provider_result(runtime, tool_calls=(call,), finish_reason="tool_calls")]
    )
    agent = _agent_runtime(runtime, provider)

    outcome = await agent.run_turn(context=_context(), intent="尝试扩大工具")

    assert outcome.status is runtime.AgentTurnStatus.FAILED
    assert outcome.error_code == expected_code


@pytest.mark.asyncio
async def test_runtime_enforces_tool_call_and_message_window_limits():
    runtime = _runtime_module()
    two_calls = (
        _tool_call(runtime, call_id=5),
        _tool_call(runtime, call_id=6),
    )
    tool_limited = _agent_runtime(
        runtime,
        ScriptedProvider(
            [
                _provider_result(
                    runtime, tool_calls=two_calls, finish_reason="tool_calls"
                )
            ]
        ),
        limits=runtime.RuntimeLimits(max_tool_calls=1),
    )
    message_limited = _agent_runtime(
        runtime,
        ScriptedProvider(
            [
                _provider_result(
                    runtime,
                    tool_calls=(_tool_call(runtime, call_id=7),),
                    finish_reason="tool_calls",
                )
            ]
        ),
        limits=runtime.RuntimeLimits(max_messages=2),
    )

    tool_outcome = await tool_limited.run_turn(context=_context(), intent="多次调用")
    message_outcome = await message_limited.run_turn(
        context=_context(), intent="扩大消息窗口"
    )

    assert tool_outcome.error_code == "agent.limit_exceeded"
    assert message_outcome.error_code == "agent.limit_exceeded"


@pytest.mark.asyncio
async def test_runtime_rejects_oversized_or_structurally_invalid_provider_results():
    runtime = _runtime_module()
    oversized = _agent_runtime(
        runtime,
        ScriptedProvider([_provider_result(runtime, content="字" * 11)]),
        limits=runtime.RuntimeLimits(max_response_chars=10),
    )
    invalid = _agent_runtime(runtime, ScriptedProvider([{"content": "伪造"}]))

    oversized_outcome = await oversized.run_turn(context=_context(), intent="检查长度")
    invalid_outcome = await invalid.run_turn(context=_context(), intent="检查结构")

    assert oversized_outcome.error_code == "agent.response_too_large"
    assert invalid_outcome.error_code == "agent.provider_failed"


@pytest.mark.asyncio
async def test_runtime_sanitizes_provider_failure_and_rejects_misbound_tool_result():
    runtime = _runtime_module()
    provider_failure = _agent_runtime(
        runtime,
        ScriptedProvider([RuntimeError("secret-provider-payload")]),
    )
    call = _tool_call(runtime, call_id=8)
    result_failure = _agent_runtime(
        runtime,
        ScriptedProvider(
            [_provider_result(runtime, tool_calls=(call,), finish_reason="tool_calls")]
        ),
        ScriptedExecutor(corrupt_binding=True),
    )

    provider_outcome = await provider_failure.run_turn(
        context=_context(), intent="触发失败"
    )
    result_outcome = await result_failure.run_turn(
        context=_context(), intent="触发绑定失败"
    )

    assert provider_outcome.error_code == "agent.provider_failed"
    assert "secret-provider-payload" not in repr(provider_outcome)
    assert result_outcome.error_code == "agent.tool_schema_invalid"
