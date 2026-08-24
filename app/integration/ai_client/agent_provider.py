"""Closed OpenAI-compatible adapter for the daily-plan Agent runtime."""

from __future__ import annotations

from collections.abc import Mapping
import json
from types import MappingProxyType
from uuid import UUID, uuid5

import httpx

from app.service.agent.canonical import canonical_json
from app.service.agent.contracts import (
    FOUNDATION_TOOL_DESCRIPTORS,
    MAX_TOOL_ID,
    MAX_TOOL_TEXT_LENGTH,
    MAX_TOOL_WARNING_LENGTH,
    MAX_TOOL_WARNINGS,
    ClosedToolInputSchema,
    ToolDescriptor,
)
from app.service.agent.runtime import (
    MAX_PROVIDER_REQUEST_ID_LENGTH,
    AgentProviderPort,
    ProviderFinishReason,
    ProviderRole,
    ProviderToolCall,
    ProviderTurnRequest,
    ProviderTurnResult,
    ToolExecutionResult,
)


FOUNDATION_TOOL_WIRE_NAMES: Mapping[str, str] = MappingProxyType(
    {
        "daily_plan.read_current": "daily_plan__read_current",
        "daily_plan.read_context": "daily_plan__read_context",
        "calendar.read_evaluation": "calendar__read_evaluation",
        "settings.read_class_areas": "settings__read_class_areas",
        "daily_plan.draft_section_patch": "daily_plan__draft_section_patch",
        "daily_plan.draft_reflection_patch": ("daily_plan__draft_reflection_patch"),
    }
)

_WIRE_TO_TOOL_NAME = MappingProxyType(
    {wire_name: name for name, wire_name in FOUNDATION_TOOL_WIRE_NAMES.items()}
)
_FINISH_REASONS = MappingProxyType(
    {
        "stop": ProviderFinishReason.COMPLETED,
        "tool_calls": ProviderFinishReason.TOOL_CALLS,
        "length": ProviderFinishReason.LENGTH,
        "content_filter": ProviderFinishReason.REFUSED,
    }
)
_MAX_WIRE_TOOL_CALL_ID_LENGTH = 128
_MAX_WIRE_ARGUMENTS_LENGTH = 64 * 1024
_ERROR_CODE = "agent.provider_adapter_failed"


class AgentProviderAdapterError(RuntimeError):
    """Sanitized failure at the concrete Provider boundary."""

    def __init__(self) -> None:
        super().__init__(_ERROR_CODE)


class _InvalidWire(Exception):
    """Private marker whose instances never cross the adapter boundary."""


class OpenAICompatibleAgentProvider(AgentProviderPort):
    """Translate closed application DTOs to one Chat Completions request."""

    __slots__ = ("_api_base_url", "_api_key", "_client", "_model_name")

    def __init__(
        self,
        *,
        api_base_url: str,
        api_key: str,
        model_name: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if (
            type(api_base_url) is not str
            or not api_base_url.strip()
            or type(api_key) is not str
            or not api_key
            or type(model_name) is not str
            or not model_name.strip()
            or (client is not None and not isinstance(client, httpx.AsyncClient))
        ):
            raise AgentProviderAdapterError
        self._api_base_url = api_base_url.rstrip("/")
        self._api_key = api_key
        self._model_name = model_name
        self._client = client

    def __repr__(self) -> str:
        return "OpenAICompatibleAgentProvider()"

    async def complete(self, request: ProviderTurnRequest) -> ProviderTurnResult:
        """Send exactly one request and return only a normalized application DTO."""
        payload: dict[str, object] | None = None
        try:
            payload = _build_payload(request=request, model_name=self._model_name)
        except Exception:
            pass
        if payload is None:
            raise AgentProviderAdapterError

        response: httpx.Response | None = None
        request_failed = False
        try:
            response = await self._post_once(payload)
        except Exception:
            request_failed = True
        if request_failed or response is None or not response.is_success:
            raise AgentProviderAdapterError

        body: object | None = None
        json_failed = False
        try:
            body = response.json()
        except Exception:
            json_failed = True
        if json_failed:
            raise AgentProviderAdapterError

        result: ProviderTurnResult | None = None
        parse_failed = False
        try:
            result = _parse_response(
                body=body,
                response=response,
                request=request,
            )
        except Exception:
            parse_failed = True
        if parse_failed or result is None:
            raise AgentProviderAdapterError
        return result

    async def _post_once(self, payload: dict[str, object]) -> httpx.Response:
        endpoint = f"{self._api_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._client is not None:
            return await self._client.post(endpoint, headers=headers, json=payload)
        async with httpx.AsyncClient() as client:
            return await client.post(endpoint, headers=headers, json=payload)


def _build_payload(
    *,
    request: ProviderTurnRequest,
    model_name: str,
) -> dict[str, object]:
    if type(request) is not ProviderTurnRequest:
        raise _InvalidWire
    if request.tools != FOUNDATION_TOOL_DESCRIPTORS:
        raise _InvalidWire
    system_content = canonical_json(
        {
            "policy_version": request.local_policy_version,
            "operation_id": request.operation_id,
            "turn_id": request.context.turn_id,
            "scope": request.context.active_scope,
            "facts": request.context.facts,
            "base_fingerprint": request.context.base_fingerprint,
        }
    )
    messages = [
        {
            "role": "system",
            "content": system_content,
        },
        *_serialize_messages(request),
    ]
    tools = [_serialize_tool(descriptor) for descriptor in request.tools]
    return {
        "model": model_name,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "max_completion_tokens": request.response_limit,
    }


def _serialize_messages(request: ProviderTurnRequest) -> list[dict[str, object]]:
    wire_messages: list[dict[str, object]] = []
    pending_calls: dict[UUID, ProviderToolCall] = {}
    for message in request.messages:
        if message.role is ProviderRole.USER:
            if (
                pending_calls
                or type(message.content) is not str
                or message.tool_calls
                or message.tool_results
            ):
                raise _InvalidWire
            wire_messages.append({"role": "user", "content": message.content})
            continue
        if message.role is ProviderRole.ASSISTANT:
            if pending_calls or message.tool_results or not message.tool_calls:
                raise _InvalidWire
            tool_calls = [
                _serialize_assistant_call(call, request) for call in message.tool_calls
            ]
            pending_calls = {call.call_id: call for call in message.tool_calls}
            if len(pending_calls) != len(message.tool_calls):
                raise _InvalidWire
            wire_messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": tool_calls,
                }
            )
            continue
        if message.role is ProviderRole.TOOL:
            if message.content is not None or message.tool_calls or not pending_calls:
                raise _InvalidWire
            results = {result.call_id: result for result in message.tool_results}
            if set(results) != set(pending_calls) or len(results) != len(
                message.tool_results
            ):
                raise _InvalidWire
            for call_id in pending_calls:
                result = results[call_id]
                _validate_tool_result(result, pending_calls[call_id], request)
                wire_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(call_id),
                        "content": canonical_json(
                            {
                                "status": result.status,
                                "value": result.value,
                                "error_code": result.error_code,
                            }
                        ),
                    }
                )
            pending_calls = {}
            continue
        raise _InvalidWire
    if pending_calls:
        raise _InvalidWire
    return wire_messages


def _serialize_assistant_call(
    call: ProviderToolCall,
    request: ProviderTurnRequest,
) -> dict[str, object]:
    descriptor = _descriptor_for_call(call, request)
    if not descriptor.input_schema.accepts(call.arguments):
        raise _InvalidWire
    return {
        "id": str(call.call_id),
        "type": "function",
        "function": {
            "name": FOUNDATION_TOOL_WIRE_NAMES[call.tool_name],
            "arguments": canonical_json(call.arguments),
        },
    }


def _validate_tool_result(
    result: ToolExecutionResult,
    call: ProviderToolCall,
    request: ProviderTurnRequest,
) -> None:
    if (
        type(result) is not ToolExecutionResult
        or result.call_id != call.call_id
        or result.operation_id != request.operation_id
        or result.turn_id != request.context.turn_id
        or result.tool_name != call.tool_name
        or result.permission is not call.permission
    ):
        raise _InvalidWire


def _descriptor_for_call(
    call: ProviderToolCall,
    request: ProviderTurnRequest,
) -> ToolDescriptor:
    if (
        type(call) is not ProviderToolCall
        or call.operation_id != request.operation_id
        or call.turn_id != request.context.turn_id
    ):
        raise _InvalidWire
    descriptors = {descriptor.name: descriptor for descriptor in request.tools}
    descriptor = descriptors.get(call.tool_name)
    if descriptor is None or call.permission is not descriptor.permission:
        raise _InvalidWire
    return descriptor


def _serialize_tool(descriptor: ToolDescriptor) -> dict[str, object]:
    return {
        "type": "function",
        "function": {
            "name": FOUNDATION_TOOL_WIRE_NAMES[descriptor.name],
            "parameters": _input_json_schema(descriptor.input_schema),
        },
    }


def _input_json_schema(schema: ClosedToolInputSchema) -> dict[str, object]:
    properties: dict[str, object] = {}
    if schema.operation_paths:
        properties = {
            "operation_id": {"type": "string", "format": "uuid"},
            "turn_id": {"type": "string", "format": "uuid"},
            "target": {
                "type": "object",
                "properties": {
                    "daily_plan_id": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_TOOL_ID,
                    },
                    "plan_date": {"type": "string", "format": "date"},
                },
                "required": ["daily_plan_id", "plan_date"],
                "additionalProperties": False,
            },
            "base_fingerprint": {
                "type": "string",
                "pattern": "^[0-9a-f]{64}$",
            },
            "operations": {
                "type": "array",
                "minItems": 1,
                "maxItems": len(schema.operation_paths),
                "items": {
                    "type": "object",
                    "properties": {
                        "field_path": {
                            "type": "string",
                            "enum": sorted(schema.operation_paths),
                        },
                        "before_value": {
                            "type": "string",
                            "maxLength": MAX_TOOL_TEXT_LENGTH,
                        },
                        "after_value": {
                            "type": "string",
                            "maxLength": MAX_TOOL_TEXT_LENGTH,
                        },
                    },
                    "required": ["field_path", "before_value", "after_value"],
                    "additionalProperties": False,
                },
            },
            "warnings": {
                "type": "array",
                "maxItems": MAX_TOOL_WARNINGS,
                "items": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": MAX_TOOL_WARNING_LENGTH,
                },
            },
        }
    return {
        "type": "object",
        "properties": properties,
        "required": sorted(schema.required_fields),
        "additionalProperties": False,
    }


def _parse_response(
    *,
    body: object,
    response: httpx.Response,
    request: ProviderTurnRequest,
) -> ProviderTurnResult:
    if not isinstance(body, Mapping):
        raise _InvalidWire
    choices = body.get("choices")
    if type(choices) is not list or len(choices) != 1:
        raise _InvalidWire
    choice = choices[0]
    if not isinstance(choice, Mapping) or not {
        "index",
        "message",
        "finish_reason",
    }.issubset(choice):
        raise _InvalidWire
    if type(choice["index"]) is not int or choice["index"] != 0:
        raise _InvalidWire
    finish_reason = _FINISH_REASONS.get(choice["finish_reason"])
    if finish_reason is None:
        raise _InvalidWire
    message = choice["message"]
    if not isinstance(message, Mapping) or message.get("role") != "assistant":
        raise _InvalidWire
    if message.get("refusal") is not None or message.get("function_call") is not None:
        raise _InvalidWire

    if finish_reason is ProviderFinishReason.TOOL_CALLS:
        content, tool_calls = _parse_tool_message(message, request)
    else:
        if "content" not in message or message.get("tool_calls") is not None:
            raise _InvalidWire
        content = message["content"]
        if type(content) is not str or len(content) > request.response_limit:
            raise _InvalidWire
        tool_calls = ()

    request_id = _parse_request_id(response)
    return ProviderTurnResult(
        assistant_content=content,
        tool_calls=tool_calls,
        finish_reason=finish_reason,
        provider_request_id=request_id,
    )


def _parse_tool_message(
    message: Mapping[object, object],
    request: ProviderTurnRequest,
) -> tuple[str | None, tuple[ProviderToolCall, ...]]:
    if "tool_calls" not in message:
        raise _InvalidWire
    content = message.get("content")
    if content is not None and (
        type(content) is not str or len(content) > request.response_limit
    ):
        raise _InvalidWire
    wire_calls = message["tool_calls"]
    if (
        type(wire_calls) is not list
        or not wire_calls
        or len(wire_calls) > len(request.tools)
    ):
        raise _InvalidWire
    descriptors = {descriptor.name: descriptor for descriptor in request.tools}
    calls = tuple(
        _parse_tool_call(value, descriptors=descriptors, request=request)
        for value in wire_calls
    )
    if len({call.call_id for call in calls}) != len(calls):
        raise _InvalidWire
    return content, calls


def _parse_tool_call(
    value: object,
    *,
    descriptors: Mapping[str, ToolDescriptor],
    request: ProviderTurnRequest,
) -> ProviderToolCall:
    if not isinstance(value, Mapping) or set(value) != {"id", "type", "function"}:
        raise _InvalidWire
    raw_id = value["id"]
    if (
        type(raw_id) is not str
        or not raw_id
        or len(raw_id) > _MAX_WIRE_TOOL_CALL_ID_LENGTH
        or value["type"] != "function"
    ):
        raise _InvalidWire
    function = value["function"]
    if not isinstance(function, Mapping) or set(function) != {"name", "arguments"}:
        raise _InvalidWire
    alias = function["name"]
    arguments_json = function["arguments"]
    if (
        type(alias) is not str
        or alias not in _WIRE_TO_TOOL_NAME
        or type(arguments_json) is not str
        or len(arguments_json) > _MAX_WIRE_ARGUMENTS_LENGTH
    ):
        raise _InvalidWire
    tool_name = _WIRE_TO_TOOL_NAME[alias]
    descriptor = descriptors.get(tool_name)
    if descriptor is None:
        raise _InvalidWire
    arguments: object | None = None
    try:
        arguments = json.loads(arguments_json)
    except (json.JSONDecodeError, RecursionError):
        pass
    if not isinstance(arguments, Mapping) or not descriptor.input_schema.accepts(
        arguments
    ):
        raise _InvalidWire
    return ProviderToolCall(
        call_id=uuid5(request.operation_id, raw_id),
        operation_id=request.operation_id,
        turn_id=request.context.turn_id,
        tool_name=descriptor.name,
        permission=descriptor.permission,
        arguments=arguments,
    )


def _parse_request_id(response: httpx.Response) -> str | None:
    value = response.headers.get("x-request-id")
    if value is None:
        return None
    if (
        not value
        or len(value) > MAX_PROVIDER_REQUEST_ID_LENGTH
        or not value.isascii()
        or any(not 0x21 <= ord(character) <= 0x7E for character in value)
    ):
        raise _InvalidWire
    return value
