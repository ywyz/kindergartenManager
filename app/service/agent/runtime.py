"""Application-owned provider port and bounded serial Agent runtime."""

import asyncio
from collections.abc import Awaitable, Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Protocol, cast, runtime_checkable
from uuid import UUID

from app.core.logging import get_logger
from app.service.agent.contracts import (
    AgentContext,
    DailyPlanScope,
    MAX_TOOL_ID,
    Permission,
    SHA256_HEX_PATTERN,
    ToolDescriptor,
    TrustedActor,
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

logger = get_logger(__name__)


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


def _log_provider_rejection(
    stage: str,
    *,
    finish_reason: ProviderFinishReason | None = None,
) -> None:
    try:
        logger.warning(
            "Agent Runtime 拒绝 Provider 结果",
            extra={
                "agent_provider_stage": stage,
                "finish_reason": (
                    finish_reason.value if finish_reason is not None else None
                ),
            },
        )
    except Exception:
        pass


class AgentTurnStatus(str, Enum):
    """Public terminal states for one bounded runtime operation."""

    SUCCEEDED = "succeeded"
    DRAFT_READY = "draft_ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class AgentContextStamp:
    """Closed copy of the live actor, scope, and operation binding."""

    context_id: UUID
    operation_id: UUID
    turn_id: UUID
    actor: TrustedActor
    active_scope: DailyPlanScope
    base_fingerprint: str

    def __post_init__(self) -> None:
        if not _valid_context_stamp_fields(self):
            raise ValueError("agent_context_stamp_invalid")

    @classmethod
    def from_context(cls, context: AgentContext) -> "AgentContextStamp":
        """Copy a fully validated context without retaining its nested objects."""
        if not validate_agent_context(context):
            raise ValueError("agent_context_stamp_invalid")
        scope = context.active_scope
        return cls(
            context_id=context.context_id,
            operation_id=context.operation_id,
            turn_id=context.turn_id,
            actor=TrustedActor(
                tenant_id=context.actor.tenant_id,
                user_id=context.actor.user_id,
            ),
            active_scope=DailyPlanScope(
                daily_plan_id=scope.daily_plan_id,
                plan_date=scope.plan_date,
            ),
            base_fingerprint=context.base_fingerprint,
        )


def _valid_stamp_scope(scope: DailyPlanScope) -> bool:
    if scope.daily_plan_id is not None:
        return (
            scope.plan_date is None
            and type(scope.daily_plan_id) is int
            and 0 < scope.daily_plan_id <= MAX_TOOL_ID
        )
    return type(scope.plan_date) is date


def _valid_context_stamp_fields(value: AgentContextStamp) -> bool:
    """Validate the complete closed stamp shape from one shared predicate."""
    try:
        return (
            type(value.context_id) is UUID
            and type(value.operation_id) is UUID
            and type(value.turn_id) is UUID
            and type(value.actor) is TrustedActor
            and type(value.actor.tenant_id) is int
            and 0 < value.actor.tenant_id <= MAX_TOOL_ID
            and type(value.actor.user_id) is int
            and 0 < value.actor.user_id <= MAX_TOOL_ID
            and type(value.active_scope) is DailyPlanScope
            and _valid_stamp_scope(value.active_scope)
            and type(value.base_fingerprint) is str
            and SHA256_HEX_PATTERN.fullmatch(value.base_fingerprint) is not None
        )
    except (AttributeError, TypeError):
        return False


def _valid_context_stamp(value: object) -> bool:
    return type(value) is AgentContextStamp and _valid_context_stamp_fields(value)


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
    max_provider_duration_ms: int = 30_000
    max_tool_duration_ms: int = 10_000
    max_total_duration_ms: int = 60_000

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value <= 0
            for value in (
                self.max_intent_chars,
                self.max_response_chars,
                self.max_tool_result_chars,
                self.max_tool_calls,
                self.max_messages,
                self.max_provider_duration_ms,
                self.max_tool_duration_ms,
                self.max_total_duration_ms,
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


@runtime_checkable
class AgentCurrentContextPort(Protocol):
    """Return the application's current immutable context binding."""

    def current_stamp(self) -> AgentContextStamp | None:
        """Return the current stamp, or ``None`` when the binding is unavailable."""
        ...


class _OperationStopped(Exception):
    """Runtime stop signal; port-raised instances are normalized at the boundary."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class _PortFailure(Exception):
    """Sanitized marker for every exception originating inside a port call."""


def _failure(code: str) -> AgentTurnOutcome:
    return AgentTurnOutcome(status=AgentTurnStatus.FAILED, error_code=code)


def _stopped_outcome(code: str) -> AgentTurnOutcome:
    if code == "agent.cancelled":
        return AgentTurnOutcome(
            status=AgentTurnStatus.CANCELLED,
            error_code="agent.cancelled",
        )
    return _failure(code)


def _host_task_is_cancelling() -> bool:
    task = asyncio.current_task()
    return task is not None and bool(task.cancelling())


class AgentRuntime:
    """Run one local provider operation at a time within fixed ceilings."""

    def __init__(
        self,
        *,
        provider: AgentProviderPort,
        executor: AgentToolExecutorPort,
        registry: AgentToolRegistry,
        context_state: AgentCurrentContextPort,
        limits: RuntimeLimits | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._provider = provider
        self._executor = executor
        self._registry = registry
        self._limits = limits or RuntimeLimits()
        self._context_state = context_state
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._state_lock = asyncio.Lock()
        self._active_operation_id: UUID | None = None
        self._active_stamp: AgentContextStamp | None = None
        self._active_io_task: asyncio.Task[object] | None = None
        self._active_io_cancel_sent = False
        self._active_stop_event: asyncio.Event | None = None
        self._active_drain_task: asyncio.Task[None] | None = None
        self._active_run_released = True
        self._active_stop_code: str | None = None

    async def run_turn(self, *, context: AgentContext, intent: str) -> AgentTurnOutcome:
        """Run a bounded serial turn; never expose provider exception details."""
        if not validate_agent_context(context) or type(intent) is not str:
            return _failure("agent.tool_schema_invalid")
        normalized_intent = intent.strip()
        if not normalized_intent:
            return _failure("agent.tool_schema_invalid")
        if len(normalized_intent) > self._limits.max_intent_chars:
            return _failure("agent.limit_exceeded")
        try:
            stamp = AgentContextStamp.from_context(context)
        except ValueError:
            return _failure("agent.tool_schema_invalid")

        async with self._state_lock:
            if self._active_operation_id is not None:
                return _failure("agent.busy")
            self._active_operation_id = context.operation_id
            self._active_stamp = stamp
            self._active_stop_event = asyncio.Event()
            self._active_drain_task = None
            self._active_run_released = False
            self._active_stop_code = None

        deadline = (
            asyncio.get_running_loop().time()
            + self._limits.max_total_duration_ms / 1000
        )
        final_stop_code: str | None = None
        try:
            initial_error = self._gate_error(
                context=context,
                expected_stamp=stamp,
                deadline=deadline,
            )
            if initial_error is not None:
                outcome = _stopped_outcome(initial_error)
            else:
                try:
                    outcome = await self._run_active(
                        context=context,
                        intent=normalized_intent,
                        expected_stamp=stamp,
                        deadline=deadline,
                    )
                except _OperationStopped as stopped:
                    outcome = _stopped_outcome(stopped.code)
        finally:
            async with self._state_lock:
                if self._active_stamp == stamp:
                    final_stop_code = self._active_stop_code
                    self._active_run_released = True
                    if self._active_drain_task is None:
                        self._clear_active_locked()
        if final_stop_code is not None:
            return _stopped_outcome(final_stop_code)
        return outcome

    async def cancel(self, stamp: AgentContextStamp) -> bool:
        """Cancel only the active operation with the exact complete binding."""
        if not _valid_context_stamp(stamp):
            return False
        async with self._state_lock:
            if self._active_stamp != stamp or self._active_stop_code is not None:
                return False
            self._active_stop_code = "agent.cancelled"
            if self._active_stop_event is not None:
                self._active_stop_event.set()
            active_task = self._active_io_task
            if active_task is not None and not active_task.done():
                self._request_port_cancel(active_task)
            return True

    async def _run_active(
        self,
        *,
        context: AgentContext,
        intent: str,
        expected_stamp: AgentContextStamp,
        deadline: float,
    ) -> AgentTurnOutcome:
        messages = (ProviderMessage(role=ProviderRole.USER, content=intent),)
        total_tool_calls = 0
        call_ids: set[UUID] = set()
        patches: list[PlanPatch] = []

        while True:
            gate_error = self._gate_error(
                context=context,
                expected_stamp=expected_stamp,
                deadline=deadline,
            )
            if gate_error is not None:
                return _stopped_outcome(gate_error)
            request = ProviderTurnRequest(
                operation_id=context.operation_id,
                local_policy_version=LOCAL_POLICY_VERSION,
                context=context,
                messages=messages,
                tools=self._registry.descriptors(),
                response_limit=self._limits.max_response_chars,
            )
            try:
                result = await self._await_port(
                    lambda: self._provider.complete(request),
                    expected_stamp=expected_stamp,
                    deadline=deadline,
                    max_duration_ms=self._limits.max_provider_duration_ms,
                )
            except _OperationStopped:
                raise
            except _PortFailure:
                gate_error = self._gate_error(
                    context=context,
                    expected_stamp=expected_stamp,
                    deadline=deadline,
                )
                if gate_error is not None:
                    return _stopped_outcome(gate_error)
                _log_provider_rejection("provider_port_failure")
                return _failure("agent.provider_failed")
            gate_error = self._gate_error(
                context=context,
                expected_stamp=expected_stamp,
                deadline=deadline,
            )
            if gate_error is not None:
                return _stopped_outcome(gate_error)
            if type(result) is not ProviderTurnResult:
                _log_provider_rejection("result_type")
                return _failure("agent.provider_failed")
            if (
                result.assistant_content is not None
                and len(result.assistant_content) > self._limits.max_response_chars
            ):
                return _failure("agent.response_too_large")

            if not result.tool_calls:
                if result.finish_reason is not ProviderFinishReason.COMPLETED:
                    _log_provider_rejection(
                        "text_finish_reason",
                        finish_reason=result.finish_reason,
                    )
                    return _failure("agent.provider_failed")
                gate_error = self._gate_error(
                    context=context,
                    expected_stamp=expected_stamp,
                    deadline=deadline,
                )
                if gate_error is not None:
                    return _stopped_outcome(gate_error)
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
                _log_provider_rejection(
                    "tool_finish_reason",
                    finish_reason=result.finish_reason,
                )
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
                    execution = await self._await_port(
                        lambda: self._executor.execute(call, context),
                        expected_stamp=expected_stamp,
                        deadline=deadline,
                        max_duration_ms=min(
                            self._limits.max_tool_duration_ms,
                            descriptor.timeout_ms,
                        ),
                    )
                except _OperationStopped:
                    raise
                except _PortFailure:
                    gate_error = self._gate_error(
                        context=context,
                        expected_stamp=expected_stamp,
                        deadline=deadline,
                    )
                    if gate_error is not None:
                        return _stopped_outcome(gate_error)
                    return _failure("agent.tool_failed")
                gate_error = self._gate_error(
                    context=context,
                    expected_stamp=expected_stamp,
                    deadline=deadline,
                )
                if gate_error is not None:
                    return _stopped_outcome(gate_error)
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

    async def _await_port(
        self,
        invoke: Callable[[], object],
        *,
        expected_stamp: AgentContextStamp,
        deadline: float,
        max_duration_ms: int,
    ) -> object:
        """Return at the hard boundary while draining a defiant port in background."""
        if self._active_stop_code is not None:
            raise _OperationStopped(self._active_stop_code)
        task = asyncio.create_task(self._invoke_port(invoke))
        self._active_io_task = task
        self._active_io_cancel_sent = False
        loop = asyncio.get_running_loop()
        timeout_seconds = min(max_duration_ms / 1000, max(0.0, deadline - loop.time()))
        stop_event = self._active_stop_event
        if stop_event is None:
            self._request_port_cancel(task)
            self._detach_port_task(task=task, expected_stamp=expected_stamp)
            raise _OperationStopped("agent.cancelled")
        stop_waiter = asyncio.create_task(stop_event.wait())
        try:
            done, _ = await asyncio.wait(
                (task, stop_waiter),
                timeout=timeout_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
        except asyncio.CancelledError:
            stop_waiter.cancel()
            stop_waiter.add_done_callback(self._discard_task_result)
            self._request_port_cancel(task)
            self._detach_port_task(task=task, expected_stamp=expected_stamp)
            raise

        stop_waiter.cancel()
        stop_waiter.add_done_callback(self._discard_task_result)
        if self._active_stop_code is not None or stop_waiter in done:
            code = self._active_stop_code or "agent.cancelled"
            await self._cancel_or_drain_port(
                task=task,
                expected_stamp=expected_stamp,
            )
            raise _OperationStopped(code)
        if task not in done:
            self._active_stop_code = "agent.timeout"
            stop_event.set()
            await self._cancel_or_drain_port(
                task=task,
                expected_stamp=expected_stamp,
            )
            raise _OperationStopped("agent.timeout")

        if self._active_io_task is task:
            self._active_io_task = None
            self._active_io_cancel_sent = False
        try:
            return task.result()
        except BaseException:
            raise _PortFailure from None

    @staticmethod
    async def _invoke_port(invoke: Callable[[], object]) -> object:
        """Contain every port BaseException before it crosses a child Task."""
        try:
            awaitable = invoke()
            if not hasattr(awaitable, "__await__"):
                raise _PortFailure
            return await cast(Awaitable[object], awaitable)
        except asyncio.CancelledError:
            raise
        except BaseException:
            raise _PortFailure from None

    async def _cancel_or_drain_port(
        self,
        *,
        task: asyncio.Task[object],
        expected_stamp: AgentContextStamp,
    ) -> None:
        """Deliver cancellation once, then detach if the port suppresses it."""
        self._request_port_cancel(task)
        try:
            await asyncio.sleep(0)
        finally:
            self._detach_port_task(task=task, expected_stamp=expected_stamp)

    def _request_port_cancel(self, task: asyncio.Task[object]) -> None:
        if (
            self._active_io_task is task
            and not self._active_io_cancel_sent
            and not task.done()
        ):
            self._active_io_cancel_sent = True
            task.cancel()

    def _detach_port_task(
        self,
        *,
        task: asyncio.Task[object],
        expected_stamp: AgentContextStamp,
    ) -> None:
        if task.done():
            self._discard_task_result(task)
            if self._active_io_task is task:
                self._active_io_task = None
                self._active_io_cancel_sent = False
            return
        if self._active_drain_task is None:
            self._active_drain_task = asyncio.create_task(
                self._drain_port_task(task=task, expected_stamp=expected_stamp)
            )

    async def _drain_port_task(
        self,
        *,
        task: asyncio.Task[object],
        expected_stamp: AgentContextStamp,
    ) -> None:
        """Consume every late value/exception and release busy only after drain."""
        try:
            await task
        except BaseException:
            pass
        current_drain = asyncio.current_task()
        async with self._state_lock:
            if self._active_stamp != expected_stamp:
                return
            if self._active_io_task is task:
                self._active_io_task = None
                self._active_io_cancel_sent = False
            if self._active_drain_task is current_drain:
                self._active_drain_task = None
            if self._active_run_released:
                self._clear_active_locked()

    @staticmethod
    def _discard_task_result(task: asyncio.Future[Any]) -> None:
        if not task.done():
            return
        try:
            task.result()
        except BaseException:
            pass

    def _clear_active_locked(self) -> None:
        self._active_operation_id = None
        self._active_stamp = None
        self._active_io_task = None
        self._active_io_cancel_sent = False
        self._active_stop_event = None
        self._active_drain_task = None
        self._active_run_released = True
        self._active_stop_code = None

    def _gate_error(
        self,
        *,
        context: AgentContext,
        expected_stamp: AgentContextStamp,
        deadline: float,
    ) -> str | None:
        if self._active_stop_code is not None:
            return self._active_stop_code
        if asyncio.get_running_loop().time() >= deadline:
            self._active_stop_code = "agent.timeout"
            return self._active_stop_code
        if not validate_agent_context(context):
            return "agent.context_stale"
        try:
            context_stamp = AgentContextStamp.from_context(context)
            now = self._clock()
        except asyncio.CancelledError:
            if _host_task_is_cancelling():
                raise
            return "agent.context_stale"
        except Exception:
            return "agent.context_stale"
        if (
            context_stamp != expected_stamp
            or type(now) is not datetime
            or now.tzinfo is not timezone.utc
            or not context.created_at_utc <= now < context.expires_at_utc
        ):
            return "agent.context_stale"
        try:
            current_stamp = self._context_state.current_stamp()
        except asyncio.CancelledError:
            if _host_task_is_cancelling():
                raise
            return "agent.context_stale"
        except Exception:
            return "agent.context_stale"
        if not _valid_context_stamp(current_stamp) or current_stamp != expected_stamp:
            return "agent.context_stale"
        return None

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
