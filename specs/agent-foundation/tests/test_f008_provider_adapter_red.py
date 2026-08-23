"""F008 public RED tests for the OpenAI-compatible Agent Provider adapter."""

import asyncio
from datetime import date, datetime, timedelta, timezone
from importlib import import_module
import json
import re
from typing import Any
from uuid import UUID, uuid5

import httpx
import pytest

from app.service.agent.canonical import canonical_json
from app.service.agent.contracts import (
    DAILY_PLAN_SECTION_PATHS,
    FOUNDATION_ALLOWED_PERMISSIONS,
    AgentContext,
    DailyPlanProjection,
    DailyPlanScope,
    PlanSection,
    TrustedActor,
)
from app.service.agent.registry import build_foundation_registry


API_BASE_URL = "https://compatible.example/v1/"
API_KEY = "fictional-provider-secret-never-log"
MODEL_NAME = "fictional-agent-model"
OPERATION_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TURN_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
CONTEXT_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
PLAN_DATE = date(2026, 9, 7)
BASE_FINGERPRINT = "d" * 64
TENANT_ID = 1_234_567_890
USER_ID = 1_987_654_321
EXPECTED_WIRE_NAMES = {
    "daily_plan.read_current": "daily_plan__read_current",
    "daily_plan.read_context": "daily_plan__read_context",
    "calendar.read_evaluation": "calendar__read_evaluation",
    "settings.read_class_areas": "settings__read_class_areas",
    "daily_plan.draft_section_patch": "daily_plan__draft_section_patch",
    "daily_plan.draft_reflection_patch": "daily_plan__draft_reflection_patch",
}
WIRE_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")


def _adapter_module():
    return import_module("app.integration.ai_client.agent_provider")


def _context() -> AgentContext:
    sections = tuple(
        PlanSection(
            field_path=field_path,
            content="认识秋天" if field_path == "activity_goal" else "",
            truncated=False,
        )
        for field_path in DAILY_PLAN_SECTION_PATHS
    )
    created_at = datetime(2026, 9, 6, 9, 0, tzinfo=timezone.utc)
    return AgentContext(
        context_id=CONTEXT_ID,
        operation_id=OPERATION_ID,
        turn_id=TURN_ID,
        created_at_utc=created_at,
        expires_at_utc=created_at + timedelta(minutes=5),
        locale="zh-CN",
        actor=TrustedActor(tenant_id=TENANT_ID, user_id=USER_ID),
        active_scope=DailyPlanScope(daily_plan_id=7),
        facts=(
            DailyPlanProjection(
                plan_id=7,
                plan_date=PLAN_DATE,
                week_number=2,
                weekday_cn="周一",
                grade="大班",
                class_name="星星班",
                sections=sections,
                updated_at_utc=datetime(2026, 9, 6, 8, 30, tzinfo=timezone.utc),
                content_sha256="e" * 64,
            ),
        ),
        base_fingerprint=BASE_FINGERPRINT,
        allowed_permissions=FOUNDATION_ALLOWED_PERMISSIONS,
    )


def _request(
    runtime: Any,
    *,
    messages: tuple[object, ...] | None = None,
    response_limit: int = 321,
):
    context = _context()
    return runtime.ProviderTurnRequest(
        operation_id=context.operation_id,
        local_policy_version="agent-foundation-v1",
        context=context,
        messages=messages
        or (
            runtime.ProviderMessage(
                role=runtime.ProviderRole.USER,
                content="请概括当前计划",
            ),
        ),
        tools=build_foundation_registry().descriptors(),
        response_limit=response_limit,
    )


def _provider(module: Any, client: httpx.AsyncClient):
    return module.OpenAICompatibleAgentProvider(
        api_base_url=API_BASE_URL,
        api_key=API_KEY,
        model_name=MODEL_NAME,
        client=client,
    )


def _choice(
    *,
    content: object = "完成",
    finish_reason: object = "stop",
    tool_calls: object | None = None,
) -> dict[str, object]:
    message: dict[str, object] = {"role": "assistant", "content": content}
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    return {"index": 0, "message": message, "finish_reason": finish_reason}


def _response(
    *,
    content: object = "完成",
    finish_reason: object = "stop",
    tool_calls: object | None = None,
) -> dict[str, object]:
    return {
        "id": "provider-response-id",
        "object": "chat.completion",
        "choices": [
            _choice(
                content=content,
                finish_reason=finish_reason,
                tool_calls=tool_calls,
            )
        ],
    }


def _wire_call(
    *,
    raw_id: str,
    alias: str,
    arguments: str = "{}",
) -> dict[str, object]:
    return {
        "id": raw_id,
        "type": "function",
        "function": {"name": alias, "arguments": arguments},
    }


def _draft_arguments(tool_name: str) -> dict[str, object]:
    field_path = (
        "daily_reflection"
        if tool_name == "daily_plan.draft_reflection_patch"
        else "activity_goal"
    )
    return {
        "operation_id": str(OPERATION_ID),
        "turn_id": str(TURN_ID),
        "target": {
            "daily_plan_id": 7,
            "plan_date": PLAN_DATE.isoformat(),
        },
        "base_fingerprint": BASE_FINGERPRINT,
        "operations": [
            {
                "field_path": field_path,
                "before_value": "认识秋天" if field_path == "activity_goal" else "",
                "after_value": "探索秋天"
                if field_path == "activity_goal"
                else "继续观察",
            }
        ],
        "warnings": ["请教师复核"],
    }


def _arguments_for(tool_name: str) -> str:
    value = (
        _draft_arguments(tool_name) if tool_name.startswith("daily_plan.draft_") else {}
    )
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _expected_system_content() -> str:
    context = _context()
    value = {
        "policy_version": "agent-foundation-v1",
        "operation_id": context.operation_id,
        "turn_id": context.turn_id,
        "scope": context.active_scope,
        "facts": context.facts,
        "base_fingerprint": context.base_fingerprint,
    }
    return canonical_json(value)


def _assert_tool_parameters_are_closed(
    descriptor: object, parameters: dict[str, object]
) -> None:
    schema = descriptor.input_schema
    expected_fields = schema.required_fields | schema.optional_fields
    assert parameters["type"] == "object"
    assert parameters["additionalProperties"] is False
    assert set(parameters["required"]) == set(schema.required_fields)
    properties = parameters["properties"]
    assert isinstance(properties, dict)
    assert set(properties) == set(expected_fields)

    if not schema.operation_paths:
        assert properties == {}
        return

    target = properties["target"]
    assert target["type"] == "object"
    assert target["additionalProperties"] is False
    assert set(target["required"]) == {"daily_plan_id", "plan_date"}
    assert set(target["properties"]) == {"daily_plan_id", "plan_date"}

    operations = properties["operations"]
    assert operations["type"] == "array"
    assert operations["minItems"] == 1
    assert operations["maxItems"] == len(schema.operation_paths)
    item_schema = operations["items"]
    assert item_schema["type"] == "object"
    assert item_schema["additionalProperties"] is False
    assert set(item_schema["required"]) == {
        "field_path",
        "before_value",
        "after_value",
    }
    assert set(item_schema["properties"]) == {
        "field_path",
        "before_value",
        "after_value",
    }
    assert set(item_schema["properties"]["field_path"]["enum"]) == set(
        schema.operation_paths
    )

    warnings = properties["warnings"]
    assert warnings["type"] == "array"
    assert warnings["maxItems"] == 8
    assert warnings["items"]["type"] == "string"


def _assert_no_sensitive_text(
    *,
    values: tuple[str, ...],
    objects: tuple[object, ...],
    log_records: tuple[object, ...] = (),
) -> None:
    rendered = "\n".join(repr(item) + "\n" + str(item) for item in objects)
    rendered += "\n" + "\n".join(
        record.getMessage() for record in log_records if hasattr(record, "getMessage")
    )
    for value in values:
        assert value not in rendered


def test_wire_names_are_one_explicit_closed_bijection():
    module = _adapter_module()
    mapping = module.FOUNDATION_TOOL_WIRE_NAMES

    assert dict(mapping) == EXPECTED_WIRE_NAMES
    assert tuple(mapping) == tuple(EXPECTED_WIRE_NAMES)
    assert len(mapping) == len(set(mapping)) == len(set(mapping.values())) == 6
    assert all(WIRE_NAME_PATTERN.fullmatch(alias) for alias in mapping.values())
    inverse = {alias: name for name, alias in mapping.items()}
    assert all(inverse[mapping[name]] == name for name in mapping)
    with pytest.raises(TypeError):
        mapping["unexpected.tool"] = "unexpected_tool"


@pytest.mark.asyncio
async def test_request_is_one_exact_generic_chat_completions_post():
    module = _adapter_module()
    runtime = import_module("app.service.agent.runtime")
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json=_response(content="当前计划已读取。"),
            headers={"x-request-id": "fictional-request-id"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await _provider(module, client).complete(_request(runtime))

    assert len(captured) == 1
    outbound = captured[0]
    assert outbound.method == "POST"
    assert str(outbound.url) == "https://compatible.example/v1/chat/completions"
    assert outbound.headers["Authorization"] == f"Bearer {API_KEY}"
    body = json.loads(outbound.content)
    assert set(body) == {
        "model",
        "messages",
        "tools",
        "tool_choice",
        "max_tokens",
    }
    assert body["model"] == MODEL_NAME
    assert body["tool_choice"] == "auto"
    assert body["max_tokens"] == 321
    assert "store" not in body
    assert "parallel_tool_calls" not in body
    assert body["messages"] == [
        {"role": "system", "content": _expected_system_content()},
        {"role": "user", "content": "请概括当前计划"},
    ]

    descriptors = build_foundation_registry().descriptors()
    assert len(body["tools"]) == len(descriptors) == 6
    for descriptor, wire_tool in zip(descriptors, body["tools"], strict=True):
        assert wire_tool["type"] == "function"
        function = wire_tool["function"]
        assert function["name"] == EXPECTED_WIRE_NAMES[descriptor.name]
        assert "permission" not in function
        _assert_tool_parameters_are_closed(descriptor, function["parameters"])

    assert result.assistant_content == "当前计划已读取。"
    assert result.finish_reason is runtime.ProviderFinishReason.COMPLETED
    assert result.provider_request_id == "fictional-request-id"


@pytest.mark.asyncio
async def test_system_context_is_closed_and_omits_actor_identity_and_credentials():
    module = _adapter_module()
    runtime = import_module("app.service.agent.runtime")
    bodies: list[dict[str, object]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=_response())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = _provider(module, client)
        result = await provider.complete(_request(runtime))

    system = json.loads(bodies[0]["messages"][0]["content"])
    assert set(system) == {
        "policy_version",
        "operation_id",
        "turn_id",
        "scope",
        "facts",
        "base_fingerprint",
    }
    assert system["policy_version"] == "agent-foundation-v1"
    assert system["operation_id"] == str(OPERATION_ID)
    assert system["turn_id"] == str(TURN_ID)
    assert system["scope"] == {"daily_plan_id": 7, "plan_date": None}
    assert system["facts"] == json.loads(canonical_json(_context().facts))
    assert system["base_fingerprint"] == BASE_FINGERPRINT

    body_text = json.dumps(bodies[0], ensure_ascii=False, sort_keys=True)
    assert API_KEY not in body_text
    assert str(CONTEXT_ID) not in body_text
    assert str(TENANT_ID) not in body_text
    assert str(USER_ID) not in body_text
    assert "actor" not in body_text
    assert "tenant_id" not in body_text
    assert "user_id" not in body_text
    _assert_no_sensitive_text(
        values=(API_KEY, str(CONTEXT_ID), str(TENANT_ID), str(USER_ID)),
        objects=(provider, result),
    )


@pytest.mark.asyncio
async def test_all_six_wire_aliases_parse_to_descriptor_owned_permissions():
    module = _adapter_module()
    runtime = import_module("app.service.agent.runtime")
    raw_ids = tuple(f"opaque provider call / {index}" for index in range(6))
    tool_calls = [
        _wire_call(
            raw_id=raw_id,
            alias=EXPECTED_WIRE_NAMES[tool_name],
            arguments=_arguments_for(tool_name),
        )
        for raw_id, tool_name in zip(raw_ids, EXPECTED_WIRE_NAMES, strict=True)
    ]

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_response(
                content=None,
                finish_reason="tool_calls",
                tool_calls=tool_calls,
            ),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await _provider(module, client).complete(_request(runtime))

    descriptors = build_foundation_registry().descriptors()
    assert result.finish_reason is runtime.ProviderFinishReason.TOOL_CALLS
    assert tuple(call.tool_name for call in result.tool_calls) == tuple(
        descriptor.name for descriptor in descriptors
    )
    assert tuple(call.permission for call in result.tool_calls) == tuple(
        descriptor.permission for descriptor in descriptors
    )
    assert tuple(call.call_id for call in result.tool_calls) == tuple(
        uuid5(OPERATION_ID, raw_id) for raw_id in raw_ids
    )
    assert tuple(dict(call.arguments) for call in result.tool_calls) == tuple(
        json.loads(_arguments_for(descriptor.name)) for descriptor in descriptors
    )
    _assert_no_sensitive_text(values=raw_ids, objects=(result, *result.tool_calls))


@pytest.mark.asyncio
async def test_normalized_tool_id_is_self_consistent_in_the_next_wire_round():
    module = _adapter_module()
    runtime = import_module("app.service.agent.runtime")
    raw_id = "provider chose an arbitrary id / with spaces"
    normalized_id = uuid5(OPERATION_ID, raw_id)
    outbound_bodies: list[dict[str, object]] = []
    responses = [
        _response(
            content=None,
            finish_reason="tool_calls",
            tool_calls=[
                _wire_call(
                    raw_id=raw_id,
                    alias=EXPECTED_WIRE_NAMES["settings.read_class_areas"],
                )
            ],
        ),
        _response(content="区域信息已读取。"),
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        outbound_bodies.append(json.loads(request.content))
        return httpx.Response(200, json=responses.pop(0))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = _provider(module, client)
        first = await provider.complete(_request(runtime))
        call = first.tool_calls[0]
        execution = runtime.ToolExecutionResult(
            call_id=call.call_id,
            operation_id=call.operation_id,
            turn_id=call.turn_id,
            tool_name=call.tool_name,
            permission=call.permission,
            status=runtime.ToolExecutionStatus.OK,
            value={"grade": "大班", "class_name": "星星班"},
            error_code=None,
        )
        messages = (
            runtime.ProviderMessage(
                role=runtime.ProviderRole.USER,
                content="读取班级区域",
            ),
            runtime.ProviderMessage(
                role=runtime.ProviderRole.ASSISTANT,
                tool_calls=(call,),
            ),
            runtime.ProviderMessage(
                role=runtime.ProviderRole.TOOL,
                tool_results=(execution,),
            ),
        )
        second = await provider.complete(_request(runtime, messages=messages))

    assert call.call_id == normalized_id
    assert len(outbound_bodies) == 2
    wire_messages = outbound_bodies[1]["messages"]
    assistant = next(
        message for message in wire_messages if message["role"] == "assistant"
    )
    tool = next(message for message in wire_messages if message["role"] == "tool")
    assistant_id = assistant["tool_calls"][0]["id"]
    assert assistant_id == tool["tool_call_id"] == str(normalized_id)
    assert (
        assistant["tool_calls"][0]["function"]["name"]
        == (EXPECTED_WIRE_NAMES["settings.read_class_areas"])
    )
    assert raw_id not in json.dumps(outbound_bodies[1], ensure_ascii=False)
    assert second.assistant_content == "区域信息已读取。"


@pytest.mark.parametrize(
    ("finish_reason", "expected_reason"),
    [
        ("stop", "COMPLETED"),
        ("length", "LENGTH"),
        ("content_filter", "REFUSED"),
    ],
)
@pytest.mark.asyncio
async def test_text_finish_reasons_are_normalized(
    finish_reason: str,
    expected_reason: str,
):
    module = _adapter_module()
    runtime = import_module("app.service.agent.runtime")

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_response(content="有界文本", finish_reason=finish_reason),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await _provider(module, client).complete(_request(runtime))

    assert result.assistant_content == "有界文本"
    assert result.finish_reason is getattr(
        runtime.ProviderFinishReason, expected_reason
    )
    assert result.tool_calls == ()


def _invalid_cases() -> list[pytest.ParamSpec]:
    valid_choice = _choice()
    return [
        pytest.param(b"{not-json", {}, id="malformed-json"),
        pytest.param({}, {}, id="choices-missing"),
        pytest.param({"choices": {}}, {}, id="choices-not-list"),
        pytest.param({"choices": []}, {}, id="choices-empty"),
        pytest.param(
            {"choices": [valid_choice, valid_choice]},
            {},
            id="extra-choice",
        ),
        pytest.param(
            {"choices": [{"index": 0, "finish_reason": "stop"}]},
            {},
            id="message-missing",
        ),
        pytest.param(
            {"choices": [_choice(content=42)]},
            {},
            id="content-not-string",
        ),
        pytest.param(
            _response(finish_reason="new-provider-reason"),
            {},
            id="unknown-finish-reason",
        ),
        pytest.param(
            _response(
                content=None,
                finish_reason="tool_calls",
                tool_calls=[
                    _wire_call(
                        raw_id="bad-arguments-json",
                        alias="settings__read_class_areas",
                        arguments="{",
                    )
                ],
            ),
            {},
            id="tool-arguments-not-json",
        ),
        pytest.param(
            _response(
                content=None,
                finish_reason="tool_calls",
                tool_calls=[
                    _wire_call(
                        raw_id="arguments-not-object",
                        alias="settings__read_class_areas",
                        arguments="[]",
                    )
                ],
            ),
            {},
            id="tool-arguments-not-object",
        ),
        pytest.param(
            _response(
                content=None,
                finish_reason="tool_calls",
                tool_calls=[
                    _wire_call(
                        raw_id="arguments-schema-open",
                        alias="settings__read_class_areas",
                        arguments='{"unexpected":true}',
                    )
                ],
            ),
            {},
            id="tool-arguments-schema-open",
        ),
        pytest.param(
            _response(
                content=None,
                finish_reason="tool_calls",
                tool_calls=[
                    _wire_call(
                        raw_id="unknown-alias",
                        alias="unknown_tool_alias",
                    )
                ],
            ),
            {},
            id="unknown-wire-alias",
        ),
        pytest.param(
            _response(
                content=None,
                finish_reason="tool_calls",
                tool_calls=[
                    _wire_call(
                        raw_id="dotted-wire-name",
                        alias="settings.read_class_areas",
                    )
                ],
            ),
            {},
            id="canonical-dotted-name-on-wire",
        ),
        pytest.param(
            _response(),
            {"x-request-id": "x" * 129},
            id="request-id-too-long",
        ),
        pytest.param(
            _response(),
            {"x-request-id": ""},
            id="request-id-empty",
        ),
    ]


@pytest.mark.parametrize(("response_body", "headers"), _invalid_cases())
@pytest.mark.asyncio
async def test_malformed_provider_responses_fail_closed_and_sanitized(
    response_body: object,
    headers: dict[str, str],
    caplog: pytest.LogCaptureFixture,
):
    module = _adapter_module()
    runtime = import_module("app.service.agent.runtime")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if isinstance(response_body, bytes):
            return httpx.Response(200, content=response_body, headers=headers)
        return httpx.Response(200, json=response_body, headers=headers)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(module.AgentProviderAdapterError) as raised:
            await _provider(module, client).complete(_request(runtime))

    assert len(requests) == 1
    _assert_no_sensitive_text(
        values=(
            API_KEY,
            "not-json",
            "new-provider-reason",
            "bad-arguments-json",
            "arguments-not-object",
            "arguments-schema-open",
            "unknown_tool_alias",
            "settings.read_class_areas",
            "x" * 129,
        ),
        objects=(raised.value,),
        log_records=tuple(caplog.records),
    )


@pytest.mark.asyncio
async def test_http_400_is_sanitized_and_never_retried_with_a_degraded_payload(
    caplog: pytest.LogCaptureFixture,
):
    module = _adapter_module()
    runtime = import_module("app.service.agent.runtime")
    requests: list[httpx.Request] = []
    raw_detail = "provider echoed a confidential downstream error"

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            400,
            json={"error": {"message": f"{raw_detail}: {API_KEY}"}},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(module.AgentProviderAdapterError) as raised:
            await _provider(module, client).complete(_request(runtime))

    assert len(requests) == 1
    _assert_no_sensitive_text(
        values=(API_KEY, raw_detail),
        objects=(raised.value,),
        log_records=tuple(caplog.records),
    )


@pytest.mark.asyncio
async def test_host_cancellation_propagates_through_the_http_boundary():
    module = _adapter_module()
    runtime = import_module("app.service.agent.runtime")
    entered = asyncio.Event()
    handler_cancelled = asyncio.Event()

    async def handler(_request: httpx.Request) -> httpx.Response:
        entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            handler_cancelled.set()
            raise

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        task = asyncio.create_task(
            _provider(module, client).complete(_request(runtime))
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert handler_cancelled.is_set()
