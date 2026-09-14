# ruff: noqa: BLE001 - UI callback sanitizes application failures
"""Protected weekly/monthly plan page and export callbacks."""

from __future__ import annotations

from uuid import uuid4

from nicegui import ui

from app.service.weekly_monthly_plans.application import (
    FormalExportDownload,
    WeeklyMonthlyApplicationService,
)
from app.service.weekly_monthly_plans.contracts import (
    MonthlyThemeActivityPlan,
    PlanKind,
    ReviewStatus,
    WeeklyActivityPlan,
)
from app.service.weekly_monthly_plans.read_service import PlanAggregateSnapshot
from app.ui.auth_context import require_bound_ui_session, require_current_ui_session
from app.ui.pages import (
    shared_weekly_plan,  # noqa: F401 - register teacher authoring route
)

# The process composition root may install the released WMP-8 application
# service.  Until it does, this page remains fail-closed and never fabricates
# a preview or a legacy export.
_application_service: WeeklyMonthlyApplicationService | None = None


def configure_weekly_monthly_application(
    service: WeeklyMonthlyApplicationService,
) -> None:
    """Install the already-composed production application service."""
    global _application_service
    if type(service) is not WeeklyMonthlyApplicationService:
        raise TypeError("service must be WeeklyMonthlyApplicationService")
    _application_service = service


async def export_plan(
    service: WeeklyMonthlyApplicationService,
    ui_session,
    *,
    plan_id: int,
    document_type: str,
) -> FormalExportDownload:
    """Single callback seam used by the protected page and integration tests."""
    return await service.export_plan(
        ui_session,
        plan_id=plan_id,
        document_type=document_type,
    )


def format_plan_details(snapshot: PlanAggregateSnapshot) -> str:
    """Format one detached authorized snapshot without repository metadata."""
    if type(snapshot) is not PlanAggregateSnapshot:
        raise TypeError("snapshot must be a PlanAggregateSnapshot")
    plan = snapshot.aggregate
    header = (
        f"状态：{plan.status.value}\n版本：{plan.version}\n"
        f"班级：{plan.scope.class_name}\n主题：{plan.theme_name}"
    )
    if type(plan) is WeeklyActivityPlan:
        days = "\n".join(
            f"{day.weekday_cn} {day.day_date:%Y-%m-%d}\n"
            f"晨谈：{day.morning_talk}\n集体活动：{day.collective_activity}\n"
            f"户外游戏：{day.outdoor_game}\n区域游戏：{day.area_game}"
            for day in plan.days
        )
        return (
            f"{header}\n{days}\n本周重点：{plan.weekly_focus}\n"
            f"环境创设：{plan.environment_creation}\n生活习惯：{plan.life_habits}\n"
            f"家园共育：{plan.home_school_cooperation}"
        )
    if type(plan) is MonthlyThemeActivityPlan:
        sections = (
            ("主题目标(theme_goals)", plan.theme_goals),
            ("生活习惯(life_habits)", plan.life_habits),
            ("游戏活动(play_activities)", plan.play_activities),
            ("环境创设(environment_creation)", plan.environment_creation),
            ("家园共育(home_school_cooperation)", plan.home_school_cooperation),
            ("其它(other)", plan.other),
            ("活动内容(activity_contents)", plan.activity_contents),
        )
        ordered = "\n".join(f"{name}：{'；'.join(values)}" for name, values in sections)
        return (
            f"{header}\n上月分析：{plan.previous_month_analysis}\n"
            f"本月重点：{plan.monthly_focus}\n{ordered}"
        )
    raise TypeError("unsupported plan snapshot")


@ui.page("/weekly-monthly-plans")
async def weekly_monthly_plans_page() -> None:
    """Render a small protected entry point; callbacks rebind the captured session."""
    ui_session = await require_current_ui_session()
    if ui_session is None:
        return

    async def _require_live_session():
        return await require_bound_ui_session(ui_session)

    if await _require_live_session() is None:
        return

    ui.label("周/月计划").classes("text-2xl font-bold")
    ui.link("填写 / 生成 / 保存 / 导出本周共享计划", "/weekly-plan").classes("text-lg")
    ui.label("请选择一个已授权的周计划或月计划进行查看与导出。").classes(
        "text-sm text-gray-600"
    )

    if _application_service is None:
        ui.label("周/月计划功能尚未完成生产配置").classes("text-sm text-red-700")
        return
    try:
        available = await _application_service.list_plans(ui_session)
    except Exception:
        ui.label("授权计划列表读取失败").classes("text-sm text-red-700")
        return
    if not available:
        ui.label("当前没有可读取的周/月计划").classes("text-sm text-gray-600")
        return
    available_by_id = {item.aggregate.plan_id: item for item in available}

    plan_id_input = ui.select(
        {
            plan_id: (
                f"{snapshot.plan_kind.value} · {snapshot.aggregate.scope.class_name} "
                f"· v{snapshot.aggregate.version}"
            )
            for plan_id, snapshot in available_by_id.items()
        },
        value=next(iter(available_by_id)),
        label="已授权计划",
    ).classes("w-full")
    kind_select = ui.select(
        {
            "weekly_activity_plan": "周活动计划",
            "monthly_theme_activity_plan": "月主题活动计划",
        },
        value=PlanKind.WEEKLY_ACTIVITY.value,
        label="文档类型",
    ).classes("w-full")
    output = ui.label("").classes("text-sm")
    version_input = ui.number(label="当前版本", min=1, precision=0, value=1)
    revision_input = ui.number(label="当前修订号", min=1, precision=0, value=1)
    target_select = ui.select(
        {
            ReviewStatus.SUBMITTED.value: "提交",
            ReviewStatus.RETURNED.value: "退回",
            ReviewStatus.APPROVED.value: "批准",
            ReviewStatus.ARCHIVED.value: "归档",
        },
        value=ReviewStatus.SUBMITTED.value,
        label="目标状态",
    )
    delete_confirmation = None

    def _identities() -> tuple[int, int, int] | None:
        values = (plan_id_input.value, version_input.value, revision_input.value)
        if any(type(value) not in {int, float} or int(value) <= 0 for value in values):
            return None
        return tuple(int(value) for value in values)

    async def _read() -> None:
        if await _require_live_session() is None:
            return
        identities = _identities()
        if identities is None:
            output.text = "计划 ID 无效"
            return
        if _application_service is None:
            output.text = "读取功能尚未完成生产配置"
            return
        try:
            snapshot = await _application_service.read_plan(
                ui_session,
                plan_id=identities[0],
            )
        except Exception:
            output.text = "读取被拒绝或已失效"
            return
        output.text = format_plan_details(snapshot)

    async def _export() -> None:
        if await _require_live_session() is None:
            return
        identities = _identities()
        if identities is None:
            output.text = "计划 ID 无效"
            return
        if _application_service is None:
            output.text = "导出功能尚未完成生产配置"
            return
        try:
            download = await export_plan(
                _application_service,
                ui_session,
                plan_id=identities[0],
                document_type=str(kind_select.value),
            )
        except Exception:
            output.text = "导出被拒绝或已失效"
            return
        ui.download(download.content_bytes, filename=download.filename)
        output.text = "导出请求已完成"

    async def _transition() -> None:
        identities = _identities()
        if await _require_live_session() is None or identities is None:
            output.text = "计划标识无效"
            return
        if _application_service is None:
            output.text = "审核功能尚未完成生产配置"
            return
        try:
            result = await _application_service.transition_plan(
                ui_session,
                plan_id=identities[0],
                expected_version=identities[1],
                expected_revision=identities[2],
                target_status=ReviewStatus(str(target_select.value)),
                operation_id=f"ui-transition-{uuid4()}",
            )
        except Exception:
            output.text = "状态变更被拒绝或已失效"
            return
        output.text = f"状态已更新为 {result.status.value}，版本 {result.version}"

    async def _confirm_delete() -> None:
        nonlocal delete_confirmation
        identities = _identities()
        if await _require_live_session() is None or identities is None:
            output.text = "计划标识无效"
            return
        if _application_service is None:
            output.text = "删除功能尚未完成生产配置"
            return
        try:
            delete_confirmation = await _application_service.issue_delete_confirmation(
                ui_session,
                plan_id=identities[0],
                expected_version=identities[1],
                expected_revision=identities[2],
            )
        except Exception:
            output.text = "删除确认被拒绝或已失效"
            return
        output.text = "删除确认已生成，请再次点击确认删除"

    async def _delete() -> None:
        nonlocal delete_confirmation
        identities = _identities()
        if await _require_live_session() is None or identities is None:
            output.text = "计划标识无效"
            return
        if _application_service is None or delete_confirmation is None:
            output.text = "缺少有效删除确认"
            return
        try:
            await _application_service.delete_draft(
                ui_session,
                plan_id=identities[0],
                expected_version=identities[1],
                expected_revision=identities[2],
                confirmation=delete_confirmation,
                operation_id=f"ui-delete-{uuid4()}",
            )
        except Exception:
            output.text = "删除被拒绝或已失效"
            return
        delete_confirmation = None
        output.text = "草稿已删除"

    ui.button("读取", on_click=_read)
    ui.button("导出 DOCX", on_click=_export)
    ui.button("提交/审核/归档", on_click=_transition)
    ui.button("申请删除确认", on_click=_confirm_delete)
    ui.button("确认删除草稿", on_click=_delete)


__all__ = (
    "configure_weekly_monthly_application",
    "export_plan",
    "format_plan_details",
    "weekly_monthly_plans_page",
)
