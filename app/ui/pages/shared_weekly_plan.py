# ruff: noqa: BLE001 - UI failures are sanitized and retain the current editor
"""Teacher weekly authoring page. All buttons use session-bound applications."""

from datetime import date
from uuid import uuid4

from nicegui import ui

from app.service.shared_weekly.authoring_application import SlotChange, StructureChoice
from app.service.shared_weekly.authoring_contracts import (
    AREA_TITLE,
    OUTDOOR_TITLE,
    SLOT_PATHS,
)
from app.service.shared_weekly.body_contracts import CollaborationDay, TargetPath
from app.service.shared_weekly.editor_contracts import ManualWeekEdit
from app.service.shared_weekly.people_contracts import People
from app.service.shared_weekly.production_composition import get_shared_weekly_services
from app.service.shared_weekly.prompt_contracts import WEEKLY_LABELS
from app.ui.auth_context import require_bound_ui_session, require_current_ui_session
from app.ui.components.app_shell import render_shell

DAY_LABELS = {
    "morning_talk_topic": "晨谈主题",
    "morning_talk_questions": "晨谈问题",
    "activity_name": "集体活动名称（缺失请手填）",
    "outdoor_activity": "户外来源原文",
    "indoor_area": "区域来源原文",
}


LAYOUT_MESSAGES = {
    "ok": "实际单页检测通过",
    "fits": "实际单页检测通过",
    "font_missing": "缺少宋体字体，无法检查或导出；请联系管理员配置字体。",
    "renderer_missing": "缺少排版渲染器，无法检查或导出；请联系管理员配置。",
    "renderer_unavailable": "受控排版渲染器不可用，无法检查或导出。",
    "renderer_changed": "渲染器版本已变化，需要重新完成资格验证。",
    "renderer_failed": "实际排版渲染失败，未交付文件，请稍后重新检查。",
    "qualification_required": "当前正式模板尚未完成五/六列与 Word 排版资格，暂不能检查或导出。",
    "qualification_invalid": "正式模板资格材料无效，暂不能检查或导出，请联系管理员。",
    "template_changed": "正式模板或激活版本已变化，请重新确认模板资格。",
    "template_stale": "模板版本已变化，请重新检查保存版本。",
    "layout_overflow": "文档超过一页或发生裁切/溢出，不交付文件；请比较缩减候选或手动调整后保存重检。",
    "layout_geometry_invalid": "实际页面几何或裁切检查失败，不交付文件。",
    "layout_invalid": "实际排版检查结果无效，不交付文件。",
    "roundtrip_failed": "模板填充回读不一致，不交付文件。",
    "schema_invalid": "正文结构不符合周计划固定栏目要求，请检查后保存。",
    "required_fields_missing": "必需内容或人员尚未填写完整；草稿仍可保存，补齐后才能导出。",
    "reduction_manual_required": "当前正文没有可安全应用的缩减规则，请手动调整、保存后重新检查。",
    "reduction_limit": "本轮已用完两次缩减候选，请保留正文并手动调整后重新检查。",
    "reduction_facts_changed": "缩减候选未满足事实保护规则，已拒绝，正文保持。",
    "reduction_check_required": "请先检查保存版本；仅实际超页结果可生成缩减候选。",
    "candidate_cancelled": "操作已取消，正文保持，未交付文件。",
}


def slot_label(path: str | TargetPath) -> str:
    if type(path) is TargetPath:
        return f"{path.day} · {DAY_LABELS[path.field]}"
    if path.startswith("days."):
        _, day, field = path.split(".", 2)
        return f"{day} · {DAY_LABELS[field]}"
    labels = {
        "games": "整周游戏",
        "collective": "集体游戏",
        "autonomous": "自主游戏",
        "name": "名称",
        "goals": "目标",
        "area": "重点区域",
        "materials": "材料",
        "guidance": "指导",
        "focus": "本周重点",
        "environment": "环境创设",
        "habits": "生活习惯",
        "content": "内容",
        "home": "家园共育",
    }
    return " / ".join(
        str(int(p) + 1) if p.isdigit() else labels.get(p, p) for p in path.split(".")
    )


class WeeklyEditor:
    """Actual page callback state, with no implicit adoption or persistence."""

    def __init__(self, services, expected):
        self.services, self.expected = services, expected
        self.edit = None
        self.dirty = False
        self.ui_revision = 0
        self.unknown = None
        self.check = None
        self.proposal = None
        self.proposal_kind = None

    def presentation_stamp(self):
        return self.ui_revision, self.dirty, self.edit, self.unknown

    def require_same_presentation(self, stamp):
        if self.presentation_stamp() != stamp:
            raise ValueError("page_stale")

    async def live(self):
        presentation = self.presentation_stamp()
        if await require_bound_ui_session(self.expected) is None:
            raise ValueError("session_invalid")
        self.require_same_presentation(presentation)

    async def open(self, choice, start, end, theme=""):
        presentation = self.presentation_stamp()
        await self.live()
        if self.dirty or self.unknown:
            raise ValueError("unsaved_changes")
        author = self.services.authoring
        display = await author.calendar.resolve_week(
            self.expected, choice.class_id, choice.semester_id, start, end
        )
        self.require_same_presentation(presentation)
        op = uuid4()
        try:
            result = await author.create_week(self.expected, display.scope, theme, op)
        except Exception as exc:
            if str(exc) == "commit_unknown":
                self.unknown = (display.scope, op)
            raise
        self.require_same_presentation(presentation)
        fresh = await author.begin_authoring(self.expected, result.plan.plan_id)
        self._replace_navigation(presentation, fresh)
        return self.edit

    async def manual(self, values, slots):
        await self.live()
        revision = self.ui_revision
        edit = self.edit
        if self.unknown:
            raise ValueError("commit_unknown")
        if values != ManualWeekEdit(edit.body.theme, edit.body.people, edit.body.days):
            self.edit = await self.services.authoring.update_edit(
                self.expected, edit.page_id, edit.page, values
            )
            self.dirty = True
        changes = tuple(
            SlotChange(path, value)
            for path, value in slots.items()
            if self.edit.body.slot_at(path).value != value
        )
        if changes:
            self.edit = await self.services.authoring.update_slots(
                self.expected, self.edit.page_id, self.edit.page, changes
            )
            self.dirty = True
        if self.dirty:
            self.check = None
        if self.ui_revision != revision:
            raise ValueError("page_stale")
        return self.edit

    async def save(self):
        await self.live()
        if self.unknown:
            raise ValueError("commit_unknown")
        revision = self.ui_revision
        edit, op = self.edit, uuid4()
        try:
            stamp = await self.services.authoring.save_edit(
                self.expected, edit.page_id, edit.page, op
            )
        except Exception as exc:
            if str(exc) == "commit_unknown":
                self.unknown = (edit.target.authorization.scope, op)
            raise
        self.dirty = False
        self.check = None
        self.edit = await self.services.authoring.begin_authoring(
            self.expected, stamp.plan_id
        )
        if self.ui_revision != revision:
            self.dirty = True
            raise ValueError("page_stale")
        return self.edit

    async def reconcile(self):
        await self.live()
        if self.unknown is None:
            raise ValueError("no_unknown_operation")
        scope, operation = self.unknown
        return await self.services.authoring.reconcile(self.expected, scope, operation)

    async def reload(self):
        presentation = self.presentation_stamp()
        await self.live()
        if self.unknown:
            raise ValueError("commit_unknown")
        fresh = await self.services.authoring.begin_authoring(
            self.expected, self.edit.target.plan.plan_id
        )
        self._replace_navigation(presentation, fresh)

    def _replace_navigation(self, presentation, fresh):
        try:
            self.require_same_presentation(presentation)
            if self.edit is not None:
                self.services.authoring.discard_edit(self.expected, self.edit.page_id)
        except Exception:
            self.services.authoring.discard_edit(self.expected, fresh.page_id)
            raise
        self.edit, self.dirty, self.check = fresh, False, None
        self.proposal = None

    async def generate(self, task, paths=()):
        await self.live()
        stamp = self.presentation_stamp()
        edit = self.edit
        if paths:
            result = await self.services.authoring.regenerate(
                self.expected, edit.page_id, edit.page, task, tuple(paths)
            )
        else:
            result = await self.services.authoring.generate_missing(
                self.expected, edit.page_id, edit.page, task
            )
        await self.live()
        try:
            self.require_same_presentation(stamp)
        except ValueError:
            self.services.authoring.cancel_generated(self.expected, result.candidate_id)
            raise
        self.proposal, self.proposal_kind = result, "generated"
        return result

    async def adopt(self):
        await self.live()
        revision = self.ui_revision
        target = (
            self.services.reduction
            if self.proposal_kind == "reduction"
            else self.services.authoring
        )
        method = (
            target.adopt
            if self.proposal_kind == "reduction"
            else target.adopt_candidate
            if self.proposal_kind == "import"
            else target.adopt_generated
        )
        self.edit = await method(
            self.expected, self.proposal.candidate_id, self.edit.page, confirmed=True
        )
        self.dirty, self.check, self.proposal = True, None, None
        if self.ui_revision != revision:
            raise ValueError("page_stale")

    async def reject(self):
        await self.live()
        if self.proposal is not None:
            if self.proposal_kind == "reduction":
                self.services.reduction.cancel(
                    self.expected, self.proposal.candidate_id
                )
            elif self.proposal_kind == "import":
                self.services.authoring.cancel_candidate(
                    self.expected, self.proposal.candidate_id
                )
            else:
                self.services.authoring.cancel_generated(
                    self.expected, self.proposal.candidate_id
                )
            self.proposal = None

    async def check_saved(self):
        await self.live()
        if self.dirty or self.unknown:
            raise ValueError("save_required")
        stamp = self.presentation_stamp()
        page_id = self.edit.page_id
        result = await self.services.exporting.check_saved(
            self.expected, page_id, self.edit.page
        )
        await self.live()
        try:
            self.require_same_presentation(stamp)
        except ValueError:
            self.services.exporting.cancel_check(self.expected, page_id)
            raise
        self.check = result
        return result

    async def export(self):
        await self.live()
        if self.dirty or self.unknown or self.check is None or not self.check.fits:
            raise ValueError("check_required")
        stamp = self.presentation_stamp()
        download = await self.services.exporting.export_saved(
            self.expected, self.check.check_id
        )
        await self.live()
        self.require_same_presentation(stamp)
        return download


@ui.page("/weekly-plan")
async def shared_weekly_plan_page():
    expected = await require_current_ui_session()
    if expected is None:
        return
    await render_shell(expected.as_user_dict(), active="weekly-plan")
    with ui.column().classes("w-full max-w-5xl mx-auto p-4 gap-4"):
        await _weekly_content(expected)


async def _weekly_content(expected):
    ui.label("幼儿园每周工作计划表").classes("text-2xl font-bold")
    ui.label("同班教师共享 · 修改后请保存；下载前检测保存版本的实际单页排版。")
    try:
        services = get_shared_weekly_services()
        choices = await services.page.choices(expected)
    except Exception:
        ui.label("班级授权或周计划配置不可用")
        return
    if not choices:
        ui.label("当前没有有效的班级学期授权")
        return
    editor = WeeklyEditor(services, expected)
    notice = ui.label("").classes("text-orange-800 whitespace-pre-wrap")
    choice_input = ui.select(
        {i: f"{c.class_name} · {c.start}—{c.end}" for i, c in enumerate(choices)},
        value=0,
        label="授权班级与学期",
    ).classes("w-full")
    with ui.row():
        start_input = ui.input("起始日期", value=choices[0].start.isoformat()).props(
            "type=date"
        )
        end_input = ui.input("结束日期", value=choices[0].start.isoformat()).props(
            "type=date"
        )
    host = ui.column().classes("w-full")
    fields, slot_fields = {}, {}
    header_fields = {}

    async def guard(action):
        try:
            await action()
        except Exception as exc:
            reasons = {
                "required_theme": "请先填写主题名称。",
                "required_activity_name": "集体活动名称缺失，请手填后再生成晨谈。",
                "required_area_name": "请先确认重点区域名称。",
                "source_selection_required": "请先选择每日来源中的游戏或区域结构。",
                "check_required": "请先检测已保存版本，检测通过后才能导出。",
                "commit_unknown": "保存结果未知，请只读对账，勿重试提交。",
                "save_required": "请先保存当前修改。",
                "unsaved_changes": "存在未保存修改，请保存或明确放弃后重载。",
                "plan_conflict": "同班教师已保存新版本，请保留当前内容并重载比较。",
                "calendar_unavailable": "教学日历不可用。",
                "source_unavailable": "来源已变化或不可用，正文保持。",
                "page_stale": "候选或页面已过期，正文保持。",
            }
            reasons.update(LAYOUT_MESSAGES)
            notice.text = reasons.get(
                str(exc),
                "操作被拒绝或已失效，当前正文保留。请检查授权、来源、必填项与当前版本。",
            )

    def mark_dirty(_=None):
        editor.ui_revision += 1
        editor.dirty = True
        editor.check = None
        notice.text = "存在未保存修改"

    async def flush():
        days = tuple(
            CollaborationDay(
                day.day, *(fields[(day.day, key)].value for key in DAY_LABELS)
            )
            for day in editor.edit.body.days
        )
        await editor.manual(
            ManualWeekEdit(
                header_fields["theme"].value,
                People(
                    tuple(
                        x.strip()
                        for x in header_fields["teachers"].value.splitlines()
                        if x.strip()
                    ),
                    header_fields["caregiver"].value,
                ),
                days,
            ),
            {p: w.value for p, w in slot_fields.items()},
        )

    async def proposal_dialog():
        proposal = editor.proposal
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-4xl"):
            ui.label("逐项比较；采用只改当前页面，仍需保存")
            for difference in proposal.differences:
                ui.label(
                    slot_label(
                        getattr(
                            difference,
                            "path",
                            getattr(difference, "target_path", ""),
                        )
                    )
                )
                ui.label("当前：" + difference.current_value).classes(
                    "whitespace-pre-wrap"
                )
                if hasattr(difference, "imported_value"):
                    ui.label(
                        "上次导入：" + (difference.imported_value or "（无）")
                    ).classes("whitespace-pre-wrap")
                ui.label(
                    "候选："
                    + getattr(
                        difference,
                        "candidate_value",
                        getattr(difference, "source_value", ""),
                    )
                ).classes("whitespace-pre-wrap")

            async def adopt():
                await flush()
                await editor.adopt()
                dialog.close()
                await render()

            async def reject():
                await editor.reject()
                dialog.close()

            ui.button("明确采用", on_click=lambda: guard(adopt))
            ui.button("拒绝，保留原文", on_click=lambda: guard(reject))
        dialog.props("persistent").open()

    async def render():
        presentation = editor.presentation_stamp()
        title, theme, display, people = await services.authoring.header(
            expected, editor.edit.page_id, editor.edit.page
        )
        last = await services.page.last_editor(
            expected, editor.edit.target.plan.plan_id
        )
        editor.require_same_presentation(presentation)
        host.clear()
        fields.clear()
        slot_fields.clear()
        with host:
            ui.label(
                f"{display.class_name} · {display.semester_display} · 第{display.week_number}周 · {theme}"
            )
            ui.label(
                f"同班共享 · 最后编辑者：{last} · "
                + ("未保存修改" if editor.dirty else "已载入保存版本")
            )
            with ui.card().classes("w-full gap-3"):
                ui.label("主题与共享人员").classes("text-lg font-semibold")
                header_fields["theme"] = ui.input(
                    "主题名称", value=editor.edit.body.theme, on_change=mark_dirty
                ).classes("w-full")
                header_fields["teachers"] = ui.textarea(
                    "教师姓名（每行一位）",
                    value="\n".join(people.teachers),
                    on_change=mark_dirty,
                ).classes("w-full")
                header_fields["caregiver"] = ui.input(
                    "保育员姓名", value=people.caregiver, on_change=mark_dirty
                )

                async def defaults():
                    await flush()
                    current = await services.people.read_defaults(
                        expected, display.scope
                    )
                    await services.people.save_defaults(
                        expected,
                        display.scope,
                        current.revision if current else 0,
                        editor.edit.body.people,
                        uuid4(),
                    )
                    notice.text = "人员设置已保存，仅用于下次新建。"

                ui.button("明确保存人员默认设置", on_click=lambda: guard(defaults))
            with ui.row().classes("w-full flex-nowrap overflow-x-auto"):
                for day, mask in zip(editor.edit.body.days, display.columns):
                    with ui.column().classes("min-w-48 flex-1"):
                        ui.label(
                            f"{day.day:%Y-%m-%d} 周{'一二三四五六日'[day.day.weekday()]}"
                        )
                        for key, label in DAY_LABELS.items():
                            widget = (
                                ui.textarea(
                                    label, value=getattr(day, key), on_change=mark_dirty
                                )
                                .classes("w-full")
                                .props("autogrow")
                            )
                            if not mask.teaching:
                                widget.disable()
                            fields[(day.day, key)] = widget
            for section, heading in (
                ("games", OUTDOOR_TITLE),
                ("area", AREA_TITLE),
                ("focus", "本周重点"),
                ("environment", "环境创设"),
                ("habits", "生活习惯"),
                ("home", "家园共育"),
            ):
                with ui.card().classes("w-full gap-3"):
                    ui.label(heading).classes("text-lg font-semibold")
                    for path in SLOT_PATHS:
                        if path.split(".")[0] != section:
                            continue
                        slot_fields[path] = (
                            ui.textarea(
                                slot_label(path),
                                value=editor.edit.body.slot_at(path).value,
                                on_change=mark_dirty,
                            )
                            .classes("w-full")
                            .props("autogrow")
                        )
            with ui.card().classes("w-full gap-3"):
                ui.label("来源、生成与保存导出").classes("text-lg font-semibold")
                await action_buttons(display)
            with ui.expansion("A4 比例阅读预览（不代表 Word 页数）").classes("w-full"):  # noqa: SIM117
                with (
                    ui.column()
                    .classes("w-full border p-4")
                    .style(
                        "max-width:210mm; min-height:297mm; font-family:SimSun,serif"
                    )
                ):
                    ui.label(title)
                    ui.label(f"{display.class_name} {theme} 第{display.week_number}周")
                    ui.label("、".join(people.teachers) + " / " + people.caregiver)
                    with ui.row().classes("w-full flex-nowrap gap-0"):
                        for day in editor.edit.body.days:
                            with ui.column().classes("flex-1 min-w-0 border p-1"):
                                ui.label(f"{day.day:%m/%d}")
                                ui.label(day.morning_talk_topic).classes(
                                    "whitespace-pre-wrap break-words"
                                )
                                ui.label(day.morning_talk_questions).classes(
                                    "whitespace-pre-wrap break-words"
                                )
                                ui.label(day.activity_name).classes(
                                    "whitespace-pre-wrap break-words"
                                )
                    for section, heading in (
                        ("games", OUTDOOR_TITLE),
                        ("area", AREA_TITLE),
                        ("focus", "本周重点"),
                        ("environment", "环境创设"),
                        ("habits", "生活习惯"),
                        ("home", "家园共育"),
                    ):
                        with ui.column().classes("w-full border p-2 gap-1"):
                            ui.label(heading).classes("font-semibold")
                            for path in SLOT_PATHS:
                                if path.split(".")[0] == section:
                                    ui.label(
                                        slot_label(path)
                                        + "："
                                        + editor.edit.body.slot_at(path).value
                                    ).classes("whitespace-pre-wrap break-words")

    async def action_buttons(display):
        async def source_check():
            await editor.live()
            await flush()
            result = await services.authoring.check_authoring_sources(
                expected, editor.edit.target.plan.plan_id
            )
            statuses = {
                "unchanged": "未变化",
                "changed": "已变化，请比较后重新导入",
                "unavailable": "已不可用",
            }
            notice.text = "来源检查：" + (
                "；".join(
                    f"{x.reference.target.day} {DAY_LABELS.get(x.reference.target.field, x.reference.target.field)}：{statuses[x.status]}"
                    for x in result
                )
                or "没有已保存的来源"
            )

        async def sources():
            await editor.live()
            await flush()
            listed = await services.authoring.list_sources(expected, editor.edit.target)
            with ui.dialog() as dialog, ui.card().classes("w-full max-w-3xl"):
                selectors = []
                for day in listed.days:
                    ui.label(f"{day.day} {day.message or '请显式选择来源'}")
                    options = {
                        s.source_id: f"{s.teacher_display} · {s.activity_name or '活动名称待手填'} · {s.morning_talk_topic}"
                        for s in day.candidates
                    }
                    selectors.append(
                        ui.select(options, label="每日来源（可留空）").classes("w-full")
                    )
                    for source in day.candidates:
                        ui.label(
                            f"{source.teacher_display}：{source.morning_talk_questions}\n{source.outdoor_activity}\n{source.indoor_area}"
                        ).classes("whitespace-pre-wrap")

                async def propose():
                    await editor.live()
                    selected = await services.authoring.select_sources(
                        expected,
                        listed.list_id,
                        tuple(w.value for w in selectors if w.value is not None),
                    )
                    editor.proposal = await services.authoring.propose_import(
                        expected,
                        editor.edit.page_id,
                        editor.edit.page,
                        selected.selection_id,
                    )
                    editor.proposal_kind = "import"
                    dialog.close()
                    await proposal_dialog()

                ui.button("比较导入差异", on_click=lambda: guard(propose))
                ui.button("取消", on_click=dialog.close)
            dialog.open()

        async def structure():
            await editor.live()
            await flush()
            listed = await services.authoring.list_structure(
                expected, editor.edit.page_id, editor.edit.page
            )
            with ui.dialog() as dialog, ui.card():
                widgets = []
                for group in (
                    "games.collective.0",
                    "games.collective.1",
                    "games.autonomous",
                    "area",
                ):
                    widgets.append(
                        (
                            group,
                            ui.select(
                                {
                                    o.option_id: f"{o.reference.target.day} · {o.name} · "
                                    + "；".join(
                                        slot_label(k) + "：" + v for k, v in o.values
                                    )
                                    for o in listed.options
                                    if o.kind
                                    == (
                                        "area"
                                        if group == "area"
                                        else "autonomous"
                                        if group == "games.autonomous"
                                        else "collective"
                                    )
                                },
                                label=slot_label(group),
                            ),
                        )
                    )

                async def propose():
                    await editor.live()
                    editor.proposal = await services.authoring.propose_structure(
                        expected,
                        listed.list_id,
                        editor.edit.page,
                        tuple(
                            StructureChoice(w.value, group)
                            for group, w in widgets
                            if w.value is not None
                        ),
                    )
                    editor.proposal_kind = "generated"
                    dialog.close()
                    await proposal_dialog()

                ui.button("比较选定结构", on_click=lambda: guard(propose))
                ui.button("取消", on_click=dialog.close)
            dialog.open()

        ui.button("检查来源变化", on_click=lambda: guard(source_check))
        ui.button("选择每日来源 / 处理重复备课", on_click=lambda: guard(sources))
        ui.button("选择游戏与区域结构", on_click=lambda: guard(structure))
        task = ui.select(
            {k: v for k, v in WEEKLY_LABELS.items() if k != "weekly_reduction"},
            value="weekly_focus",
            label="生成栏目",
        )
        paths = ui.select(
            {p: slot_label(p) for p in SLOT_PATHS}
            | {
                f"days.{d.day}.{field}": f"{d.day} {DAY_LABELS[field]}"
                for d in editor.edit.body.days
                if d.day in display.facts.teaching_days
                for field in ("morning_talk_topic", "morning_talk_questions")
            },
            multiple=True,
            label="重新生成的字段（仅同一栏目）",
        ).classes("w-full")

        async def generate(selected=False):
            await editor.live()
            if selected and not paths.value:
                notice.text = "请先选择需要重新生成的字段。"
                return
            await flush()
            await editor.generate(
                task.value, tuple(paths.value or ()) if selected else ()
            )
            await proposal_dialog()

        async def cancel_generation():
            await editor.live()
            services.authoring.cancel_generation(expected, editor.edit.page_id)
            services.reduction.cancel_generation(expected, editor.edit.page_id)
            services.exporting.cancel_check(expected, editor.edit.page_id)
            editor.check = None
            notice.text = "已取消生成，正文保持。"

        ui.button("生成缺失内容", on_click=lambda: guard(generate))
        ui.button("重新生成选定字段", on_click=lambda: guard(lambda: generate(True)))
        ui.button("取消生成", on_click=lambda: guard(cancel_generation))

        async def save():
            await flush()
            await editor.save()
            await render()
            notice.text = "草稿已保存。"

        async def reload():
            with ui.dialog() as dialog, ui.card():
                ui.label("重载会放弃当前未保存修改，是否继续？")

                async def confirmed():
                    await editor.reload()
                    dialog.close()
                    await render()

                ui.button("明确放弃并重载", on_click=lambda: guard(confirmed))
                ui.button("保留", on_click=dialog.close)
            dialog.open()

        async def reconcile():
            result = await editor.reconcile()
            notice.text = "只读对账：" + (
                "已找到原操作保存记录；请重新进入页面读取。"
                if result
                else "未找到原操作记录；未重试、未写入。"
            )

        async def check():
            result = await editor.check_saved()
            notice.text = f"单页检测：{LAYOUT_MESSAGES.get(result.reason, '实际排版检查未通过，不交付文件。')}；页数：{result.pages}"

        async def export():
            download = await editor.export()
            ui.download(download.data, filename=download.filename)

        async def reduce():
            await editor.live()
            if editor.dirty or editor.check is None:
                raise ValueError("save_required")
            stamp = editor.presentation_stamp()
            proposal = await services.reduction.propose(
                expected, editor.check.check_id, editor.edit.page_id, editor.edit.page
            )
            await editor.live()
            try:
                editor.require_same_presentation(stamp)
            except ValueError:
                services.reduction.cancel(expected, proposal.candidate_id)
                raise
            editor.proposal = proposal
            editor.proposal_kind = "reduction"
            await proposal_dialog()

        ui.button("保存草稿", on_click=lambda: guard(save))
        ui.button("重载保存版本", on_click=lambda: guard(reload))
        ui.button("保存结果未知：只读对账", on_click=lambda: guard(reconcile))
        ui.button("检测保存版本的单页排版", on_click=lambda: guard(check))
        ui.button("生成篇幅缩减候选（最多两轮）", on_click=lambda: guard(reduce))
        ui.button("导出已检查的 DOCX", on_click=lambda: guard(export))

    async def open_week():
        await editor.open(
            choices[choice_input.value],
            date.fromisoformat(start_input.value),
            date.fromisoformat(end_input.value),
        )
        await render()

    ui.button("打开 / 新建本周共享计划", on_click=lambda: guard(open_week))
