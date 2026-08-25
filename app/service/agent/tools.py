"""Closed local executors for the six Agent Foundation tools."""

import asyncio
from collections.abc import Callable
from typing import AsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from app.service.agent.contracts import (
    FOUNDATION_TOOL_NAMES,
    AgentContext,
    ToolDescriptor,
    validate_agent_context,
)
from app.service.agent.patch import PlanPatchRejected, build_plan_patch_from_arguments
from app.service.agent.read_service import AgentReadService, HolidayLookup
from app.service.agent.registry import AgentToolRegistry, AgentToolRejected
from app.service.agent.runtime import (
    ProviderToolCall,
    ToolExecutionResult,
    ToolExecutionStatus,
)


SessionFactory = Callable[[], AsyncContextManager[AsyncSession]]
_READ_TOOL_NAMES = frozenset(
    {
        "daily_plan.read_current",
        "daily_plan.read_context",
        "calendar.read_evaluation",
        "settings.read_class_areas",
    }
)
_DRAFT_TOOL_NAMES = frozenset(
    {
        "daily_plan.draft_section_patch",
        "daily_plan.draft_reflection_patch",
    }
)


class FoundationToolExecutor:
    """Execute the exact Foundation registry without exposing persistence seams."""

    def __init__(
        self,
        session_factory: SessionFactory,
        registry: AgentToolRegistry,
        holiday_lookup: HolidayLookup | None = None,
    ) -> None:
        if (
            not callable(session_factory)
            or type(registry) is not AgentToolRegistry
            or tuple(item.name for item in registry.descriptors())
            != FOUNDATION_TOOL_NAMES
            or holiday_lookup is not None
            and not callable(holiday_lookup)
        ):
            raise ValueError("foundation_tool_executor_invalid")
        self._session_factory = session_factory
        self._registry = registry
        self._holiday_lookup = holiday_lookup

    async def execute(
        self,
        call: ProviderToolCall,
        context: AgentContext,
    ) -> ToolExecutionResult:
        """Execute one already-resolved call and return only a sanitized envelope."""
        binding_error = self._binding_error(call, context)
        if binding_error is not None:
            return self._result(
                call,
                status=ToolExecutionStatus.REJECTED,
                error_code=binding_error,
            )

        try:
            descriptor = self._registry.resolve(call.tool_name, call.permission)
        except AgentToolRejected:
            return self._result(
                call,
                status=ToolExecutionStatus.REJECTED,
                error_code="agent.tool_not_allowed",
            )
        if not descriptor.input_schema.accepts(call.arguments):
            return self._result(
                call,
                status=ToolExecutionStatus.REJECTED,
                error_code="agent.tool_schema_invalid",
            )

        if call.tool_name in _DRAFT_TOOL_NAMES:
            return self._execute_draft(call, context)
        if call.tool_name not in _READ_TOOL_NAMES:
            return self._result(
                call,
                status=ToolExecutionStatus.REJECTED,
                error_code="agent.tool_not_allowed",
            )
        return await self._execute_read(call, context, descriptor)

    @staticmethod
    def _binding_error(
        call: ProviderToolCall,
        context: AgentContext,
    ) -> str | None:
        if type(call) is not ProviderToolCall or not validate_agent_context(context):
            return "agent.tool_schema_invalid"
        if call.permission not in context.allowed_permissions:
            return "agent.tool_not_allowed"
        if call.operation_id != context.operation_id or call.turn_id != context.turn_id:
            return "agent.tool_schema_invalid"
        return None

    async def _execute_read(
        self,
        call: ProviderToolCall,
        context: AgentContext,
        descriptor: ToolDescriptor,
    ) -> ToolExecutionResult:
        try:
            async with self._session_factory() as session:
                reader = (
                    AgentReadService(session, context.actor)
                    if self._holiday_lookup is None
                    else AgentReadService(
                        session,
                        context.actor,
                        holiday_lookup=self._holiday_lookup,
                    )
                )
                value = await self._read_value(reader, call.tool_name, context)
        except asyncio.CancelledError:
            raise
        except Exception:
            return self._result(
                call,
                status=ToolExecutionStatus.FAILED,
                error_code="agent.tool_failed",
            )

        if value is None or not descriptor.output_schema.accepts(value):
            return self._result(
                call,
                status=ToolExecutionStatus.FAILED,
                error_code="agent.tool_failed",
            )
        return self._result(call, status=ToolExecutionStatus.OK, value=value)

    @staticmethod
    async def _read_value(
        reader: AgentReadService,
        tool_name: str,
        context: AgentContext,
    ) -> object:
        if tool_name == "daily_plan.read_current":
            return await reader.read_current(context.active_scope)
        if tool_name == "daily_plan.read_context":
            return await reader.read_context(context.active_scope)
        if tool_name == "settings.read_class_areas":
            return await reader.read_class_areas()

        target_date = context.active_scope.plan_date
        if target_date is None:
            plan_context = await reader.read_context(context.active_scope)
            if plan_context is None:
                return None
            target_date = plan_context.plan_date
        return await reader.read_calendar(target_date)

    def _execute_draft(
        self,
        call: ProviderToolCall,
        context: AgentContext,
    ) -> ToolExecutionResult:
        try:
            patch = build_plan_patch_from_arguments(
                context=context,
                tool_name=call.tool_name,
                arguments=call.arguments,
            )
        except PlanPatchRejected:
            return self._result(
                call,
                status=ToolExecutionStatus.REJECTED,
                error_code="agent.tool_schema_invalid",
            )
        except Exception:
            return self._result(
                call,
                status=ToolExecutionStatus.FAILED,
                error_code="agent.tool_failed",
            )
        return self._result(call, status=ToolExecutionStatus.OK, value=patch)

    @staticmethod
    def _result(
        call: ProviderToolCall,
        *,
        status: ToolExecutionStatus,
        value: object = None,
        error_code: str | None = None,
    ) -> ToolExecutionResult:
        return ToolExecutionResult(
            call_id=call.call_id,
            operation_id=call.operation_id,
            turn_id=call.turn_id,
            tool_name=call.tool_name,
            permission=call.permission,
            status=status,
            value=value,
            error_code=error_code,
        )
