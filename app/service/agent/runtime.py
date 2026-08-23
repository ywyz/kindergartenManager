"""Application-owned provider port and bounded serial Agent runtime."""

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from types import MappingProxyType
from typing import Protocol, runtime_checkable
from uuid import UUID

from app.service.agent.contracts import (
    AgentContext,
    Permission,
    ToolDescriptor,
    validate_agent_context,
)
from app.service.agent.canonical import canonical_json
from app.service.agent.patch import (
    PlanPatch,
    PlanPatchRejected,
    build_plan_patch_from_arguments,
    plan_patch_matches_expected,
)
from app.service.agent.registry import AgentToolRegistry, AgentToolRejected

LOCAL_POLICY_VERSION = "agent-foundation-v1"
MAX_PROVIDER_REQUEST_ID_LENGTH = 128
MAX_TOOL_ERROR_CODE_LENGTH = 128


class ProviderRole(str, Enum):
    """Closed application message roles understood by provider adapters."""

    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ProviderFinishReason(str, Enum):
    """Closed provider completion reasons used by the Foundation runtime."""

    COMPLETED = "completed"
    TOOL_CALLS = "tool_calls"
    LENGTH = "length"
    REFUSED = "refused"


class ToolExecutionStatus(str, Enum):
    """Closed local tool-execution outcomes."""

    OK = "ok"
    REJECTED = "rejected"
    FAILED = "failed"


class AgentTurnStatus(str, Enum):
    """Public terminal states for one bounded runtime operation."""

    SUCCEEDED = "succeeded"
    DRAFT_READY = "draft_ready"
    FAILED = "failed"


def _freeze_json(value: object) -> object:
    """Copy provider-owned JSON-like values into immutable local structures."""
    if value is None or type(value) in {str, int, float, bool}:
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("provider_arguments_invalid")
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    raise ValueError("provider_arguments_invalid")


@dataclass(frozen=True, slots=True)
class _InvalidToolPayload:
    """Immutable marker replacing unsupported executor-owned values."""


_INVALID_TOOL_PAYLOAD = _InvalidToolPayload()


def _freeze_tool_value(value: object) -> object:
    """Deep-copy allowed payload containers without retaining executor objects."""
    if is_dataclass(value):
        return _freeze_dataclass_value(value)
    if value is None or type(value) in {str, int, float, bool}:
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            return _INVALID_TOOL_PAYLOAD
        return MappingProxyType(
            {key: _freeze_tool_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_tool_value(item) for item in value)
    return _INVALID_TOOL_PAYLOAD


def _freeze_dataclass_value(value: object) -> object:
    """Copy a frozen dataclass while marking mutable or unsupported fields invalid."""
    if isinstance(value, type):
        return _INVALID_TOOL_PAYLOAD
    parameters = getattr(type(value), "__dataclass_params__", None)
    if parameters is None or not parameters.frozen:
        return _INVALID_TOOL_PAYLOAD
    copied = {
        item.name: _freeze_dataclass_field(getattr(value, item.name))
        for item in fields(value)
    }
    try:
        return type(value)(**copied)
    except (TypeError, ValueError):
        return _INVALID_TOOL_PAYLOAD


def _freeze_dataclass_field(value: object) -> object:
    if value is None or type(value) in {str, int, float, bool, date, datetime, UUID}:
        return value
    if isinstance(value, Enum):
        return value
    if type(value) is tuple:
        return tuple(_freeze_dataclass_field(item) for item in value)
    if type(value) is frozenset:
        return frozenset(_freeze_dataclass_field(item) for item in value)
    if is_dataclass(value):
        return _freeze_dataclass_value(value)
    return _INVALID_TOOL_PAYLOAD


@dataclass(frozen=True, slots=True)
class ProviderToolCall:
    """One provider-requested call, fully bound to the operation and turn."""

    call_id: UUID
    operation_id: UUID
    turn_id: UUID
    tool_name: str
    permission: Permission
    arguments: Mapping[str, object] = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.call_id) is not UUID
            or type(self.operation_id) is not UUID
            or type(self.turn_id) is not UUID
            or type(self.tool_name) is not str
            or not self.tool_name
            or not isinstance(self.permission, Permission)
            or not isinstance(self.arguments, Mapping)
        ):
            raise ValueError("provider_tool_call_invalid")
        frozen_arguments = _freeze_json(self.arguments)
        if not isinstance(frozen_arguments, Mapping):
            raise ValueError("provider_tool_call_invalid")
        object.__setattr__(self, "arguments", frozen_arguments)


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    """One immutable local result returned to the runtime."""

    call_id: UUID
    operation_id: UUID
    turn_id: UUID
    tool_name: str
    permission: Permission
    status: ToolExecutionStatus
    value: object = field(repr=False)
    error_code: str | None

    def __post_init__(self) -> None:
        if (
            type(self.call_id) is not UUID
            or type(self.operation_id) is not UUID
            or type(self.turn_id) is not UUID
            or type(self.tool_name) is not str
            or not self.tool_name
            or not isinstance(self.permission, Permission)
            or not isinstance(self.status, ToolExecutionStatus)
            or (self.error_code is not None and type(self.error_code) is not str)
        ):
            raise ValueError("tool_execution_result_invalid")
        object.__setattr__(self, "value", _freeze_tool_value(self.value))


@dataclass(frozen=True, slots=True)
class ProviderMessage:
    """Application-owned provider message with sensitive payloads hidden in repr."""

    role: ProviderRole
    content: str | None = field(default=None, repr=False)
    tool_calls: tuple[ProviderToolCall, ...] = field(default=(), repr=False)
    tool_results: tuple[ToolExecutionResult, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.role, ProviderRole):
            raise ValueError("provider_message_invalid")
        if self.content is not None and type(self.content) is not str:
            raise ValueError("provider_message_invalid")
        if type(self.tool_calls) is not tuple or not all(
            type(call) is ProviderToolCall for call in self.tool_calls
        ):
            raise ValueError("provider_message_invalid")
        if type(self.tool_results) is not tuple or not all(
            type(result) is ToolExecutionResult for result in self.tool_results
        ):
            raise ValueError("provider_message_invalid")


@dataclass(frozen=True, slots=True)
class ProviderTurnRequest:
    """Frozen application request passed to a provider adapter."""

    operation_id: UUID
    local_policy_version: str
    context: AgentContext
    messages: tuple[ProviderMessage, ...]
    tools: tuple[ToolDescriptor, ...]
    response_limit: int

    def __post_init__(self) -> None:
        if (
            type(self.operation_id) is not UUID
            or not validate_agent_context(self.context)
            or self.operation_id != self.context.operation_id
            or type(self.local_policy_version) is not str
            or not self.local_policy_version
            or type(self.messages) is not tuple
            or not self.messages
            or not all(type(message) is ProviderMessage for message in self.messages)
            or type(self.tools) is not tuple
            or not all(type(tool) is ToolDescriptor for tool in self.tools)
            or type(self.response_limit) is not int
            or self.response_limit <= 0
        ):
            raise ValueError("provider_request_invalid")


@dataclass(frozen=True, slots=True)
class ProviderTurnResult:
    """Normalized result returned by a provider adapter."""

    assistant_content: str | None = field(default=None, repr=False)
    tool_calls: tuple[ProviderToolCall, ...] = field(default=(), repr=False)
    finish_reason: ProviderFinishReason = ProviderFinishReason.COMPLETED
    provider_request_id: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if (
            self.assistant_content is not None
            and type(self.assistant_content) is not str
        ):
            raise ValueError("provider_result_invalid")
        if type(self.tool_calls) is not tuple or not all(
            type(call) is ProviderToolCall for call in self.tool_calls
        ):
            raise ValueError("provider_result_invalid")
        if not isinstance(self.finish_reason, ProviderFinishReason):
            raise ValueError("provider_result_invalid")
        if (
            self.provider_request_id is not None
            and type(self.provider_request_id) is not str
        ):
            raise ValueError("provider_result_invalid")
        if (
            self.provider_request_id is not None
            and len(self.provider_request_id) > MAX_PROVIDER_REQUEST_ID_LENGTH
        ):
            raise ValueError("provider_request_id_too_large")


@dataclass(frozen=True, slots=True)
class RuntimeLimits:
    """Local ceilings that bound a serial provider/tool loop."""

    max_intent_chars: int = 2_000
    max_response_chars: int = 4_096
    max_tool_result_chars: int = 16_384
    max_tool_calls: int = 6
    max_messages: int = 12

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value <= 0
            for value in (
                self.max_intent_chars,
                self.max_response_chars,
                self.max_tool_result_chars,
                self.max_tool_calls,
                self.max_messages,
            )
        ):
            raise ValueError("runtime_limits_invalid")


@dataclass(frozen=True, slots=True)
class AgentTurnOutcome:
    """Sanitized terminal output from one runtime operation."""

    status: AgentTurnStatus
    assistant_content: str | None = field(default=None, repr=False)
    patches: tuple[PlanPatch, ...] = field(default=(), repr=False)
    error_code: str | None = None


@runtime_checkable
class AgentProviderPort(Protocol):
    """Provider-neutral async completion port owned by the application layer."""

    async def complete(self, request: ProviderTurnRequest) -> ProviderTurnResult:
        """Return one normalized provider turn."""
        ...


@runtime_checkable
class AgentToolExecutorPort(Protocol):
    """Narrow executor port; concrete tool wiring remains outside the runtime."""

    async def execute(
        self, call: ProviderToolCall, context: AgentContext
    ) -> ToolExecutionResult:
        """Execute one already-resolved READ or DRAFT call."""
        ...


def _failure(code: str) -> AgentTurnOutcome:
    return AgentTurnOutcome(status=AgentTurnStatus.FAILED, error_code=code)


class AgentRuntime:
    """Run one local provider operation at a time within fixed ceilings."""

    def __init__(
        self,
        *,
        provider: AgentProviderPort,
        executor: AgentToolExecutorPort,
        registry: AgentToolRegistry,
        limits: RuntimeLimits | None = None,
    ) -> None:
        self._provider = provider
        self._executor = executor
        self._registry = registry
        self._limits = limits or RuntimeLimits()
        self._state_lock = asyncio.Lock()
        self._active_operation_id: UUID | None = None

    async def run_turn(self, *, context: AgentContext, intent: str) -> AgentTurnOutcome:
        """Run a bounded serial turn; never expose provider exception details."""
        if not validate_agent_context(context) or type(intent) is not str:
            return _failure("agent.tool_schema_invalid")
        normalized_intent = intent.strip()
        if not normalized_intent:
            return _failure("agent.tool_schema_invalid")
        if len(normalized_intent) > self._limits.max_intent_chars:
            return _failure("agent.limit_exceeded")

        async with self._state_lock:
            if self._active_operation_id is not None:
                return _failure("agent.busy")
            self._active_operation_id = context.operation_id

        try:
            return await self._run_active(context=context, intent=normalized_intent)
        finally:
            async with self._state_lock:
                if self._active_operation_id == context.operation_id:
                    self._active_operation_id = None

    async def _run_active(
        self, *, context: AgentContext, intent: str
    ) -> AgentTurnOutcome:
        messages = (ProviderMessage(role=ProviderRole.USER, content=intent),)
        total_tool_calls = 0
        call_ids: set[UUID] = set()
        patches: list[PlanPatch] = []

        while True:
            request = ProviderTurnRequest(
                operation_id=context.operation_id,
                local_policy_version=LOCAL_POLICY_VERSION,
                context=context,
                messages=messages,
                tools=self._registry.descriptors(),
                response_limit=self._limits.max_response_chars,
            )
            try:
                result = await self._provider.complete(request)
            except Exception:
                return _failure("agent.provider_failed")
            if type(result) is not ProviderTurnResult:
                return _failure("agent.provider_failed")
            if (
                result.assistant_content is not None
                and len(result.assistant_content) > self._limits.max_response_chars
            ):
                return _failure("agent.response_too_large")

            if not result.tool_calls:
                if result.finish_reason is not ProviderFinishReason.COMPLETED:
                    return _failure("agent.provider_failed")
                status = (
                    AgentTurnStatus.DRAFT_READY
                    if patches
                    else AgentTurnStatus.SUCCEEDED
                )
                return AgentTurnOutcome(
                    status=status,
                    assistant_content=result.assistant_content,
                    patches=tuple(patches),
                )

            if result.finish_reason is not ProviderFinishReason.TOOL_CALLS:
                return _failure("agent.provider_failed")
            total_tool_calls += len(result.tool_calls)
            if total_tool_calls > self._limits.max_tool_calls:
                return _failure("agent.limit_exceeded")
            if len(messages) + 2 > self._limits.max_messages:
                return _failure("agent.limit_exceeded")

            resolved_calls: list[
                tuple[ProviderToolCall, ToolDescriptor, PlanPatch | None]
            ] = []
            for call in result.tool_calls:
                error, descriptor, expected_patch = self._validate_call(
                    call=call,
                    context=context,
                    seen_call_ids=call_ids,
                )
                if error is not None:
                    return _failure(error)
                if descriptor is None:
                    return _failure("agent.tool_schema_invalid")
                call_ids.add(call.call_id)
                resolved_calls.append((call, descriptor, expected_patch))

            results: list[ToolExecutionResult] = []
            for call, descriptor, expected_patch in resolved_calls:
                try:
                    execution = await self._executor.execute(call, context)
                except Exception:
                    return _failure("agent.tool_failed")
                error = self._validate_execution(
                    call=call,
                    context=context,
                    descriptor=descriptor,
                    execution=execution,
                    expected_patch=expected_patch,
                )
                if error is not None:
                    return _failure(error)
                results.append(execution)
                if call.permission is Permission.DRAFT:
                    patches.append(execution.value)

            messages += (
                ProviderMessage(
                    role=ProviderRole.ASSISTANT,
                    content=result.assistant_content,
                    tool_calls=tuple(call for call, _, _ in resolved_calls),
                ),
                ProviderMessage(
                    role=ProviderRole.TOOL,
                    tool_results=tuple(results),
                ),
            )

    def _validate_call(
        self,
        *,
        call: ProviderToolCall,
        context: AgentContext,
        seen_call_ids: set[UUID],
    ) -> tuple[str | None, ToolDescriptor | None, PlanPatch | None]:
        if call.operation_id != context.operation_id or call.turn_id != context.turn_id:
            return "agent.tool_schema_invalid", None, None
        if call.call_id in seen_call_ids:
            return "agent.tool_schema_invalid", None, None
        if call.permission not in context.allowed_permissions:
            return "agent.tool_not_allowed", None, None
        try:
            descriptor = self._registry.resolve(call.tool_name, call.permission)
        except AgentToolRejected:
            return "agent.tool_not_allowed", None, None
        if not descriptor.input_schema.accepts(call.arguments):
            return "agent.tool_schema_invalid", None, None
        expected_patch = None
        if call.permission is Permission.DRAFT:
            try:
                expected_patch = build_plan_patch_from_arguments(
                    context=context,
                    tool_name=call.tool_name,
                    arguments=call.arguments,
                )
            except PlanPatchRejected:
                return "agent.tool_schema_invalid", None, None
        return None, descriptor, expected_patch

    def _validate_execution(
        self,
        *,
        call: ProviderToolCall,
        context: AgentContext,
        descriptor: ToolDescriptor,
        execution: object,
        expected_patch: PlanPatch | None,
    ) -> str | None:
        if type(execution) is not ToolExecutionResult:
            return "agent.tool_schema_invalid"
        if (
            execution.call_id != call.call_id
            or execution.operation_id != context.operation_id
            or execution.turn_id != context.turn_id
            or execution.tool_name != call.tool_name
            or execution.permission is not call.permission
        ):
            return "agent.tool_schema_invalid"
        if (
            execution.error_code is not None
            and len(execution.error_code) > MAX_TOOL_ERROR_CODE_LENGTH
        ):
            return "agent.tool_schema_invalid"
        if (
            execution.status is ToolExecutionStatus.OK
            and execution.error_code is not None
        ):
            return "agent.tool_schema_invalid"
        if execution.status is not ToolExecutionStatus.OK:
            return "agent.tool_failed"
        if expected_patch is None:
            if not descriptor.output_schema.accepts(execution.value):
                return "agent.tool_schema_invalid"
        elif not plan_patch_matches_expected(
            actual=execution.value, expected=expected_patch
        ):
            return "agent.tool_schema_invalid"
        try:
            serialized = canonical_json(execution.value)
        except (TypeError, ValueError):
            return "agent.tool_schema_invalid"
        if len(serialized) > self._limits.max_tool_result_chars:
            return "agent.limit_exceeded"
        return None
