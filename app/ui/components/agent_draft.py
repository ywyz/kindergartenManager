"""READ/DRAFT daily-plan Agent panel with optional explicit Patch actions.

The panel renders detached suggestions and owns no write implementation. A
page-local adapter may add one-Patch actions through the narrow
``AgentPatchActions`` interface; the panel never receives a repository, session,
legacy save callback, or Provider WRITE capability.
"""

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Protocol

from nicegui import context, ui

from app.service.agent.composition import (
    AgentPanelSnapshot,
    AgentPanelStatus,
    AgentPatchSnapshot,
    DailyPlanAgentController,
)


AGENT_ACTION_LABELS = ("运行", "取消", "丢弃建议")
AGENT_FIXED_NOTICE = "仅生成建议，不会保存或修改当前计划。"
AGENT_CONFIRMATION_NOTICE = (
    "模型只生成建议；仅在你显式确认采用后，本地应用才会写入当前计划。"
)

_STATUS_COPY = {
    AgentPanelStatus.IDLE: "等待运行",
    AgentPanelStatus.RUNNING: "正在生成建议……",
    AgentPanelStatus.SUCCEEDED: "建议已生成",
    AgentPanelStatus.DRAFT_READY: "草案建议已生成，请人工核对",
    AgentPanelStatus.FAILED: "本次运行未完成",
    AgentPanelStatus.CANCELLED: "本次运行已取消",
}

_ERROR_COPY = {
    "agent.busy": "已有 Agent 操作正在运行，请稍后重试。",
    "agent.cancelled": "本次运行已取消。",
    "agent.configuration_failed": "AI 配置暂不可用，请检查设置后重试。",
    "agent.configuration_missing": "尚未配置可用的文本模型，请前往设置。",
    "agent.context_stale": "日期或页面状态已变化，本次结果已丢弃。",
    "agent.page_closed": "页面已关闭，本次结果未显示。",
    "agent.plan_not_found": "所选日期尚无已保存计划，无法建立只读上下文。",
    "agent.scope_required": "请先选择日期。",
    "agent.timeout": "模型响应超时，请稍后重试。",
    "agent.tool_failed": "只读工具执行失败，本次结果未采用。",
    "agent.tool_not_allowed": "模型请求了未授权工具，本次结果已拒绝。",
    "agent.tool_schema_invalid": "模型工具参数不符合关闭契约，本次结果已拒绝。",
}


class AgentPatchActions(Protocol):
    """Optional page-local actions rendered beside one detached Patch view.

    The Agent panel owns only this narrow rendering/lifecycle port. The port is
    responsible for authorizing any confirmation operation and may not turn the
    Foundation registry itself into a WRITE surface.
    """

    def render_patch_actions(self, patch: AgentPatchSnapshot) -> None:
        """Render explicit actions for this one immutable Patch snapshot."""

    def invalidate(self) -> None:
        """Synchronously revoke any pending action before page state changes."""

    async def disconnect(self) -> None:
        """Discard connection-local confirmation state."""

    async def close(self) -> None:
        """Permanently close page-local confirmation state."""


class DailyPlanAgentPanel:
    """NiceGUI rendering facade around one page-local Agent controller."""

    def __init__(
        self,
        controller: DailyPlanAgentController,
        *,
        authorize_operation: Callable[[], Awaitable[bool]] | None = None,
        patch_actions: AgentPatchActions | None = None,
    ) -> None:
        if type(controller) is not DailyPlanAgentController:
            raise ValueError("agent_controller_invalid")
        self._controller = controller
        self._authorize_operation = authorize_operation
        self._patch_actions = patch_actions
        self._closed = False

        with ui.card().classes("w-full"):
            ui.label("每日计划 Agent（建议模式）").classes(
                "text-base font-bold text-blue-700"
            )
            notice = (
                AGENT_FIXED_NOTICE
                if patch_actions is None
                else AGENT_CONFIRMATION_NOTICE
            )
            ui.label(notice).classes("text-sm text-orange-700")
            self._scope_label = ui.label("尚未选择日期").classes(
                "text-sm text-gray-500"
            )
            self._intent = (
                ui.textarea(
                    label="希望 Agent 协助什么？",
                    placeholder="例如：结合当前计划，提出更清晰的活动目标建议",
                )
                .classes("w-full")
                .props("rows=3 autogrow")
            )
            with ui.row().classes("gap-2"):
                self._run_button = ui.button(
                    AGENT_ACTION_LABELS[0],
                    icon="smart_toy",
                    on_click=self._run,
                ).classes("bg-blue-600 text-white")
                self._cancel_button = ui.button(
                    AGENT_ACTION_LABELS[1],
                    icon="stop_circle",
                    on_click=self._cancel,
                ).props("outline")
                self._discard_button = ui.button(
                    AGENT_ACTION_LABELS[2],
                    icon="delete_sweep",
                    on_click=self._discard,
                ).props("flat")
            self._status_label = ui.label("").classes("text-sm text-gray-600")
            self._result_container = ui.column().classes("w-full gap-2")

        client = context.client
        client.on_disconnect(self.disconnect)
        client.on_delete(self.close)
        self._render(controller.snapshot)

    def scope_changed(self, selected_date: date | None) -> None:
        """Synchronously invalidate old work before date-side awaits begin."""
        if self._closed:
            return
        patch_actions = getattr(self, "_patch_actions", None)
        if patch_actions is not None:
            patch_actions.invalidate()
        snapshot = self._controller.scope_changed(selected_date)
        self._render(snapshot)

    def plan_changed(self, changed_date: date) -> None:
        """Invalidate suggestions based on an authoritative plan before mutation."""
        if self._closed:
            return
        patch_actions = getattr(self, "_patch_actions", None)
        if patch_actions is not None:
            patch_actions.invalidate()
        snapshot = self._controller.plan_changed(changed_date)
        self._render(snapshot)

    async def disconnect(self) -> None:
        """Cancel connection-local work while keeping the controller reusable."""
        if self._closed:
            return
        patch_actions = getattr(self, "_patch_actions", None)
        if patch_actions is not None:
            await patch_actions.disconnect()
        snapshot = await self._controller.disconnect()
        self._render(snapshot)

    async def close(self) -> None:
        """Release page-local state and cancel its exact in-flight operation."""
        if self._closed:
            return
        self._closed = True
        patch_actions = getattr(self, "_patch_actions", None)
        if patch_actions is not None:
            await patch_actions.close()
        await self._controller.close()

    async def _run(self) -> None:
        if self._closed:
            return
        operation_snapshot = self._controller.snapshot
        intent = str(self._intent.value or "").strip()
        if (
            self._authorize_operation is not None
            and not await self._authorize_operation()
        ):
            return
        if self._controller.snapshot is not operation_snapshot:
            return
        if not intent:
            self._status_label.text = "请输入本次协助意图。"
            self._status_label.classes(
                remove="text-gray-600 text-green-700",
                add="text-orange-700",
            )
            return
        patch_actions = getattr(self, "_patch_actions", None)
        if patch_actions is not None:
            patch_actions.invalidate()
        self._render_running()
        snapshot = await self._controller.run(intent)
        if (
            self._authorize_operation is not None
            and not await self._authorize_operation()
        ):
            self._controller.discard()
            return
        if not self._closed:
            self._render(snapshot)

    async def _cancel(self) -> None:
        if self._closed:
            return
        requested = await self._controller.cancel()
        if requested and not self._closed:
            self._status_label.text = "正在取消……"

    def _discard(self) -> None:
        if self._closed:
            return
        patch_actions = getattr(self, "_patch_actions", None)
        if patch_actions is not None:
            patch_actions.invalidate()
        self._intent.value = ""
        self._render(self._controller.discard())

    def _render_running(self) -> None:
        self._run_button.disable()
        self._discard_button.disable()
        self._cancel_button.enable()
        self._status_label.classes(
            remove="text-red-600 text-orange-700 text-green-700",
            add="text-gray-600",
        )
        self._status_label.text = _STATUS_COPY[AgentPanelStatus.RUNNING]
        self._result_container.clear()

    def _render(self, snapshot: AgentPanelSnapshot) -> None:
        selected_date = snapshot.selected_date
        self._scope_label.text = (
            f"当前日期：{selected_date.isoformat()}"
            if selected_date is not None
            else "尚未选择日期"
        )
        self._run_button.enable()
        self._discard_button.enable()
        if snapshot.status is AgentPanelStatus.RUNNING:
            self._render_running()
            return
        self._cancel_button.disable()

        self._status_label.classes(
            remove="text-red-600 text-orange-700 text-green-700 text-gray-600"
        )
        if snapshot.status in {
            AgentPanelStatus.SUCCEEDED,
            AgentPanelStatus.DRAFT_READY,
        }:
            self._status_label.classes(add="text-green-700")
        elif snapshot.status is AgentPanelStatus.FAILED:
            self._status_label.classes(add="text-red-600")
        elif snapshot.status is AgentPanelStatus.CANCELLED:
            self._status_label.classes(add="text-orange-700")
        else:
            self._status_label.classes(add="text-gray-600")

        self._status_label.text = _STATUS_COPY[snapshot.status]
        self._result_container.clear()
        with self._result_container:
            if snapshot.error_code is not None:
                ui.label(
                    _ERROR_COPY.get(
                        snapshot.error_code,
                        "本次运行失败，未显示或保存任何建议。",
                    )
                ).classes("text-sm text-red-600")
            if snapshot.assistant_content:
                with ui.card().classes("w-full bg-blue-50"):
                    ui.label("模型建议").classes("text-sm font-semibold")
                    ui.label(snapshot.assistant_content).classes(
                        "text-sm whitespace-pre-wrap"
                    )
            for patch in snapshot.patches:
                with ui.card().classes("w-full bg-amber-50"):
                    ui.label(
                        f"草案：{patch.tool_name} · {patch.plan_date.isoformat()}"
                    ).classes("text-sm font-semibold")
                    for operation in patch.operations:
                        ui.label(operation.field_path).classes(
                            "text-xs font-medium text-gray-700"
                        )
                        ui.label(f"原值：{operation.before_display}").classes(
                            "text-xs whitespace-pre-wrap text-gray-600"
                        )
                        ui.label(f"建议：{operation.after_display}").classes(
                            "text-xs whitespace-pre-wrap text-blue-800"
                        )
                    for warning in patch.warnings:
                        ui.label(f"复核提示：{warning}").classes(
                            "text-xs text-orange-700"
                        )
                    patch_actions = getattr(self, "_patch_actions", None)
                    if patch_actions is not None:
                        patch_actions.render_patch_actions(patch)


def render_daily_plan_agent_panel(
    controller: DailyPlanAgentController,
    *,
    authorize_operation: Callable[[], Awaitable[bool]] | None = None,
    patch_actions: AgentPatchActions | None = None,
) -> DailyPlanAgentPanel:
    """Render and return the non-writing daily-plan Agent panel."""
    return DailyPlanAgentPanel(
        controller,
        authorize_operation=authorize_operation,
        patch_actions=patch_actions,
    )
