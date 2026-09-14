# ruff: noqa: BLE001 - UI failures are sanitized and retain the current editor
"""Teacher weekly authoring page. All buttons use session-bound applications."""

from datetime import date, datetime, timedelta
from uuid import uuid4

from nicegui import ui

from app.service.shared_weekly.authoring_application import SlotChange
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
    "activity_name": "集体活动名称（缺失请手填）",
}

# These fields remain in the persisted collaboration schema for historical
# plans.  They are deliberately carried through a save without exposing them
# as teacher-facing weekly-plan inputs.  Outdoor/area source material is
# projected into the final structured slots by the authoring application.
_HIDDEN_DAY_FIELDS = (
    "morning_talk_questions",
    "outdoor_activity",
    "indoor_area",
)


LAYOUT_MESSAGES = {
    "ok": "实际单页检测通过",
    "fits": "实际单页检测通过",
    "font_missing": "缺少周计划中文字体字体，无法检查或导出；请联系管理员配置字体。",
    "renderer_missing": "缺少排版渲染器，无法检查或导出；请联系管理员配置。",
    "renderer_unavailable": "受控排版渲染器不可用，无法检查或导出。",
    "renderer_changed": "渲染器版本已变化，需要重新完成资格验证。",
    "renderer_failed": "实际排版渲染失败，未交付文件，请稍后重新检查。",
    "qualification_required": "当前正式模板尚未完成五/六列与 Word 排版资格，暂不能检查或导出。",
    "qualification_invalid": "正式模板资格材料无效，暂不能检查或导出，请联系管理员。",
    "template_changed": "正式模板或激活版本已变化，请重新确认模板资格。",
    "template_stale": "模板版本已变化，请重新检查保存版本。",
    "layout_overflow": "文档超过一页或发生裁切/溢出，未交付文件；请调整内容并保存后再次导出。",
    "layout_geometry_invalid": "实际页面几何或裁切检查失败，不交付文件。",
    "layout_invalid": "实际排版检查结果无效，不交付文件。",
    "roundtrip_failed": "模板填充回读不一致，不交付文件。",
    "schema_invalid": "正文结构不符合周计划固定栏目要求，请检查后保存。",
    "required_fields_missing": "必需内容或人员尚未填写完整；草稿仍可保存，补齐后才能导出。",
    "candidate_cancelled": "操作已失效，正文保持。",
    "candidate_busy": "已有操作正在进行，请稍候。",
    "ai_timeout": "AI 生成超时，正文保持；请稍后重试。",
    "ai_unavailable": "AI 服务暂不可用，正文保持；请稍后重试。",
    "ai_invalid": "AI 返回内容无法使用，正文保持；请稍后重试。",
    "config_invalid": "当前 AI 配置不可用，请检查设置。",
    "prompt_stale": "提示词已变化，请重新生成缺失内容。",
    "source_unavailable": "本人每日计划来源已变化或不可用，正文保持。",
}


# One-click generation walks all managed weekly prompts in dependency
# order; a task whose retained content is already complete is skipped.
ALL_WEEKLY_TASKS = (
    "weekly_morning_talk",
    "weekly_games",
    "weekly_area",
    "weekly_materials",
    "weekly_focus",
    "weekly_environment",
    "weekly_habits",
    "weekly_home",
)


ACTION_MESSAGES = {
    "required_theme": "请先填写主题名称。",
    "required_activity_name": "集体活动名称缺失，请手填后再生成晨谈。",
    "required_area_name": "请先确认重点区域名称。",
    "source_selection_required": "游戏或区域结构无法自动确定，请先在对应内容格填写名称。",
    "check_required": "当前内容尚未满足导出条件，请补齐必填栏目。",
    "commit_unknown": "保存结果未知，请只读对账，勿重试提交。",
    "save_required": "请先保存当前修改。",
    "unsaved_changes": "存在未保存修改，请先保存后切换计划。",
    "plan_conflict": "同班教师已保存新版本，请保留当前内容并重新打开计划比较。",
    "calendar_unavailable": "教学日历不可用。",
    "source_unavailable": "来源已变化或不可用，正文保持。",
    "page_stale": "候选或页面已过期，正文保持。",
    "games_format_invalid": "游戏整格格式无法识别，正文保持；请保留游戏名称和三行目标标签。",
    "area_format_invalid": "区域游戏整格格式无法识别，正文保持；请保留区域、目标、材料和指导标签。",
    "habits_format_invalid": "生活习惯整格格式无法识别，正文保持；请保留三组习惯名称和具体内容标签。",
    "morning_topic_required": "晨谈只能填写主题或简要陈述，不能填写问题或问答过程。",
    **LAYOUT_MESSAGES,
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


def _default_week_range(choice, today: date | None = None) -> tuple[date, date]:
    """Choose the current in-semester teaching week for the date controls."""
    today = datetime.now().astimezone().date() if today is None else today
    if today < choice.start or today > choice.end:
        today = choice.start
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    start = max(monday, choice.start)
    end = min(friday, choice.end)
    # A semester can begin/end mid-week.  Both values must still identify the
    # same canonical week for CalendarApplication.resolve_week.
    if start > end or (start - timedelta(days=start.weekday())) != (
        end - timedelta(days=end.weekday())
    ):
        return today, today
    return start, end


def _format_labeled_cell(labels: tuple[str, ...], values: tuple[str, ...]) -> str:
    return "\n".join(f"{label}：{value}" for label, value in zip(labels, values))


def _parse_labeled_cell(
    value: object, labels: tuple[str, ...]
) -> tuple[str, ...] | None:
    """Parse a complete content cell while retaining multiline section text."""
    if type(value) is not str:
        return None
    # A label at the beginning of a line is the delimiter.  Reject repeated
    # delimiters so a teacher's multiline content is never silently split into
    # a different field; the existing cell remains available for correction.
    if value.count(labels[0] + "：") != 1 or any(
        value.count("\n" + label + "：") != 1 for label in labels[1:]
    ):
        return None
    cursor = 0
    result = []
    for index, label in enumerate(labels):
        marker = label + "："
        if not value.startswith(marker, cursor):
            return None
        cursor += len(marker)
        if index + 1 < len(labels):
            next_marker = "\n" + labels[index + 1] + "："
            boundary = value.find(next_marker, cursor)
            if boundary < 0:
                return None
            result.append(value[cursor:boundary])
            cursor = boundary + 1
        else:
            result.append(value[cursor:])
    return tuple(result)


_GAME_LABELS = ("游戏名称", "目标1", "目标2", "目标3")
_AREA_LABELS = (
    "重点指导区域",
    "目标1",
    "目标2",
    "目标3",
    "材料",
    "指导1",
    "指导2",
    "指导3",
)
_HABIT_LABELS = tuple(
    label for index in range(1, 4) for label in (f"习惯{index}名称", f"习惯{index}内容")
)


def _format_game_cell(body, prefix: str) -> str:
    return _format_labeled_cell(
        _GAME_LABELS,
        tuple(
            body.value_at(prefix + suffix)
            for suffix in (".name", ".goals.0", ".goals.1", ".goals.2")
        ),
    )


def _parse_game_cell(value: object) -> tuple[str, ...] | None:
    return _parse_labeled_cell(value, _GAME_LABELS)


def _format_area_cell(body) -> str:
    return _format_labeled_cell(
        _AREA_LABELS,
        tuple(
            body.value_at(path)
            for path in (
                "area.name",
                "area.goals.0",
                "area.goals.1",
                "area.goals.2",
                "area.materials",
                "area.guidance.0",
                "area.guidance.1",
                "area.guidance.2",
            )
        ),
    )


def _parse_area_cell(value: object) -> tuple[str, ...] | None:
    return _parse_labeled_cell(value, _AREA_LABELS)


def _format_habits_cell(body) -> str:
    return _format_labeled_cell(
        _HABIT_LABELS,
        tuple(
            body.value_at(f"habits.{index}.{field}")
            for index in range(3)
            for field in ("name", "content")
        ),
    )


def _parse_habits_cell(value: object) -> tuple[str, ...] | None:
    return _parse_labeled_cell(value, _HABIT_LABELS)


class WeeklyEditor:
    """Actual page callback state, with no implicit adoption or persistence."""

    def __init__(self, services, expected):
        self.services, self.expected = services, expected
        self.edit = None
        self.dirty = False
        self.ui_revision = 0
        self.unknown = None
        self.check = None
        self.source_changes = ()
        self.conflicts = ()
        self.proposal = None
        self._generation_owner = None

    def presentation_stamp(self):
        return self.ui_revision, self.dirty, self.edit, self.unknown

    def require_same_presentation(self, stamp):
        if self.presentation_stamp() != stamp:
            raise ValueError("page_stale")

    @property
    def generation_busy(self) -> bool:
        return self._generation_owner is not None

    def begin_generation(self):
        if self.generation_busy or self.proposal is not None:
            raise ValueError("candidate_busy")
        owner = object()
        self._generation_owner = owner
        return owner

    def end_generation(self, owner) -> None:
        if self._generation_owner is owner:
            self._generation_owner = None

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
        had_saved_sources = bool(fresh.body.sources)
        navigation = self.presentation_stamp()
        # Source reads happen only after a page ticket has been acquired.  The
        # service fills empty fields from this teacher's own daily records and
        # returns a new page stamp when the in-memory body changes; nothing is
        # persisted by opening the week.
        filled = await author.autofill_owned(
            self.expected, self.edit.page_id, self.edit.page
        )
        self.require_same_presentation(navigation)
        self.dirty = filled.body != self.edit.body
        self.edit = filled
        self.check = None
        self.conflicts = author.owned_conflicts(self.expected, self.edit.page_id)
        # A saved plan can retain source snapshots from a previous authoring
        # session.  Show only changed/unavailable references inline; there is
        # no persistent "check sources" teacher action.
        self.source_changes = ()
        if had_saved_sources:
            source_check_presentation = self.presentation_stamp()
            try:
                checks = await author.check_authoring_sources(
                    self.expected, result.plan.plan_id
                )
            except Exception as exc:
                if str(exc) != "content_invalid":
                    raise
                checks = ()
            self.require_same_presentation(source_check_presentation)
            self.source_changes = tuple(x for x in checks if x.status != "unchanged")
        return self.edit

    async def resolve_conflicts(self, source_ids, flush=None):
        """Apply an explicit choice only for days with real source conflicts."""
        await self.live()
        if not source_ids:
            raise ValueError("source_selection_required")
        if flush is not None:
            await flush()
        before = self.edit.body
        result = await self.services.authoring.autofill_owned(
            self.expected,
            self.edit.page_id,
            self.edit.page,
            source_ids=tuple(source_ids),
        )
        await self.live()
        self.edit = result
        self.dirty = self.dirty or result.body != before
        self.check = None
        self.conflicts = self.services.authoring.owned_conflicts(
            self.expected, self.edit.page_id
        )
        self.ui_revision += 1
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

    def _replace_navigation(self, presentation, fresh):
        try:
            self.require_same_presentation(presentation)
            if self.edit is not None:
                self.services.authoring.discard_edit(self.expected, self.edit.page_id)
        except Exception:
            self.services.authoring.discard_edit(self.expected, fresh.page_id)
            raise
        self.edit, self.dirty, self.check = fresh, False, None
        self.source_changes = ()
        self.conflicts = ()
        self.proposal = None

    async def generate(self, task, *, owner=None):
        await self.live()
        owns_generation = owner is None
        if owns_generation:
            owner = self.begin_generation()
        elif self._generation_owner is not owner:
            raise ValueError("candidate_busy")
        stamp = self.presentation_stamp()
        edit = self.edit
        try:
            result = await self.services.authoring.generate_missing(
                self.expected, edit.page_id, edit.page, task
            )
            try:
                await self.live()
                self.require_same_presentation(stamp)
            except Exception:
                self.services.authoring.cancel_generated(
                    self.expected, result.candidate_id
                )
                raise
            self.proposal = result
            return result
        finally:
            if owns_generation:
                self.end_generation(owner)

    async def adopt(self):
        await self.live()
        stamp = self.presentation_stamp()
        result = await self.services.authoring.adopt_generated(
            self.expected, self.proposal.candidate_id, self.edit.page, confirmed=True
        )
        self.require_same_presentation(stamp)
        self.edit = result
        self.dirty, self.check, self.proposal = True, None, None

    async def reject(self):
        await self.live()
        if self.proposal is not None:
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
        if self.dirty or self.unknown:
            raise ValueError("save_required")
        # Layout qualification is an export prerequisite, but remains an
        # internal step so teachers do not have to manage a separate check
        # button or stale check ticket.
        await self.check_saved()
        if self.check is None or not self.check.fits:
            raise ValueError(self.check.reason if self.check else "check_required")
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
    ui.label("同班教师共享 · 选择班级和教学周后自动补填本人每日计划；修改后请保存。")
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
    default_start, default_end = _default_week_range(choices[0])

    def choice_changed(_event=None):
        choice = choices[int(choice_input.value)]
        start, end = _default_week_range(choice)
        start_input.value = start.isoformat()
        end_input.value = end.isoformat()

    choice_input = ui.select(
        {i: f"{c.class_name} · {c.start}—{c.end}" for i, c in enumerate(choices)},
        value=0,
        label="授权班级与学期",
        on_change=choice_changed,
    ).classes("w-full")
    with ui.row():
        start_input = ui.input("起始日期", value=default_start.isoformat()).props(
            "type=date"
        )
        end_input = ui.input("结束日期", value=default_end.isoformat()).props(
            "type=date"
        )
    host = ui.column().classes("w-full")
    fields, slot_fields = {}, {}
    game_fields, area_field, habits_field = {}, {}, None
    header_fields = {}

    async def guard(action):
        try:
            await action()
        except Exception as exc:
            notice.text = ACTION_MESSAGES.get(
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
                day.day,
                fields[(day.day, "morning_talk_topic")].value,
                day.morning_talk_questions,
                fields[(day.day, "activity_name")].value,
                day.outdoor_activity,
                day.indoor_area,
            )
            for day in editor.edit.body.days
        )
        values = {path: widget.value for path, widget in slot_fields.items()}
        for prefix, widget in game_fields.items():
            parsed = _parse_game_cell(widget.value)
            if parsed is None:
                raise ValueError("games_format_invalid")
            for suffix, value in zip(
                (".name", ".goals.0", ".goals.1", ".goals.2"), parsed
            ):
                values[prefix + suffix] = value
        parsed_area = _parse_area_cell(area_field.value)
        if parsed_area is None:
            raise ValueError("area_format_invalid")
        for path, value in zip(
            (
                "area.name",
                "area.goals.0",
                "area.goals.1",
                "area.goals.2",
                "area.materials",
                "area.guidance.0",
                "area.guidance.1",
                "area.guidance.2",
            ),
            parsed_area,
        ):
            values[path] = value
        parsed_habits = _parse_habits_cell(habits_field.value)
        if parsed_habits is None:
            raise ValueError("habits_format_invalid")
        for index, (name, content) in enumerate(
            zip(parsed_habits[::2], parsed_habits[1::2])
        ):
            values[f"habits.{index}.name"] = name
            values[f"habits.{index}.content"] = content
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
            values,
        )

    generation_button = None

    async def fill_sequence(remaining):
        """One click completes every missing weekly task without per-task review.

        The click itself authorizes applying missing-only candidates: each
        task is generated then adopted immediately, in memory only. Adoption
        never touches saved or manually filled cells, and nothing is saved.
        Any user edit or navigation invalidates the presentation stamp, the
        remaining tasks stop, and late results are discarded before adoption.
        """
        await editor.live()
        if editor.generation_busy or editor.proposal is not None:
            raise ValueError("candidate_busy")
        owner = editor.begin_generation()
        if generation_button is not None:
            generation_button.props("loading")
        filled = 0
        missing_requirements = []
        try:
            await flush()
            stamp = editor.presentation_stamp()
            while remaining:
                task, remaining = remaining[0], remaining[1:]
                try:
                    editor.require_same_presentation(stamp)
                    notice.text = "正在补全：" + WEEKLY_LABELS[task] + "……"
                    await editor.generate(task, owner=owner)
                    editor.require_same_presentation(stamp)
                    await editor.adopt()
                    stamp = editor.presentation_stamp()
                    await render()
                    editor.require_same_presentation(stamp)
                    filled += 1
                except Exception as exc:
                    if str(exc) in (
                        "no_missing_content",
                        "required_activity_name",
                        "required_area_name",
                    ):
                        try:
                            editor.require_same_presentation(stamp)
                        except ValueError as stale:
                            exc = stale
                        else:
                            if str(exc) != "no_missing_content":
                                missing_requirements.append(ACTION_MESSAGES[str(exc)])
                            continue
                    remaining_incomplete = (
                        "已补全的栏目已保留，其余栏目未完成；请核对后稍后重试或手填。"
                    )
                    if str(exc) in (
                        "page_stale",
                        "candidate_cancelled",
                        "session_invalid",
                    ):
                        notice.text = (
                            "检测到您的修改或页面跳转，本次补全已停止，正文保持；"
                            + remaining_incomplete
                        )
                    else:
                        notice.text = (
                            ACTION_MESSAGES.get(
                                str(exc),
                                "操作被拒绝或已失效，当前正文保留。",
                            )
                            + "\n"
                            + remaining_incomplete
                        )
                    if editor.proposal is not None:
                        editor.services.authoring.cancel_generated(
                            editor.expected, editor.proposal.candidate_id
                        )
                        editor.proposal = None
                    return
            notice.text = (
                "已补全可生成内容；请核对并保存。"
                if filled
                else "没有可生成的缺失内容。"
            ) + (
                "仍需填写：" + "；".join(missing_requirements)
                if missing_requirements
                else ""
            )
        finally:
            if editor._generation_owner is owner:
                editor.end_generation(owner)
                if generation_button is not None:
                    generation_button.props(remove="loading")

    async def fill_missing_all():
        await fill_sequence(tuple(ALL_WEEKLY_TASKS))

    async def render():
        nonlocal area_field, habits_field
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
        game_fields.clear()
        area_field = None
        habits_field = None

        def slot_widget(path, label=None):
            widget = (
                ui.textarea(
                    label or slot_label(path),
                    value=editor.edit.body.slot_at(path).value,
                    on_change=mark_dirty,
                )
                .classes("w-full")
                .props("autogrow")
            )
            slot_fields[path] = widget
            return widget

        async def conflict_picker():
            if not editor.conflicts:
                return
            with ui.card().classes("w-full gap-3 border border-orange-300"):
                ui.label("发现同一天有多份本人每日计划，请选择后自动补填").classes(
                    "text-lg font-semibold text-orange-800"
                )
                selectors = []
                for day, candidates in editor.conflicts:
                    ui.label(f"{day} 的本人每日计划")
                    options = {
                        source.source_id: (
                            f"{source.teacher_display} · "
                            f"{source.activity_name or '活动名称待手填'} · "
                            f"{source.morning_talk_topic or '晨谈待填写'}"
                        )
                        for source in candidates
                    }
                    selectors.append(
                        ui.select(options, label="选择一份来源").classes("w-full")
                    )

                async def apply_choices():
                    selected = tuple(
                        widget.value for widget in selectors if widget.value is not None
                    )
                    if len(selected) != len(selectors):
                        raise ValueError("source_selection_required")
                    await editor.resolve_conflicts(selected, flush=flush)
                    await render()

                ui.button("应用选择并自动补填", on_click=lambda: guard(apply_choices))

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
            if editor.source_changes:
                ui.label(
                    "来源提示：已保存的本人每日计划来源发生变化或暂不可用；当前正文已保留。"
                ).classes("text-orange-800 whitespace-pre-wrap")
            await conflict_picker()

            with ui.card().classes("w-full gap-3"):
                ui.label(OUTDOOR_TITLE).classes("text-lg font-semibold")
                for prefix, heading in (
                    ("games.collective.0", "集体游戏 1"),
                    ("games.collective.1", "集体游戏 2"),
                    ("games.autonomous", "自主游戏"),
                ):
                    with ui.card().classes("w-full gap-2 border"):
                        ui.label(heading).classes("font-semibold")
                        game_fields[prefix] = (
                            ui.textarea(
                                heading,
                                value=_format_game_cell(editor.edit.body, prefix),
                                on_change=mark_dirty,
                            )
                            .classes("w-full")
                            .props("autogrow")
                        )

            with ui.card().classes("w-full gap-3"):
                ui.label("区域游戏").classes("text-lg font-semibold")
                ui.label(AREA_TITLE).classes("text-sm text-gray-600")
                area_field = (
                    ui.textarea(
                        "区域游戏完整内容",
                        value=_format_area_cell(editor.edit.body),
                        on_change=mark_dirty,
                    )
                    .classes("w-full")
                    .props("autogrow")
                )

            for section, heading in (
                ("focus", "本周重点"),
                ("environment", "环境创设"),
            ):
                with ui.card().classes("w-full gap-3"):
                    ui.label(heading).classes("text-lg font-semibold")
                    for i in range(3):
                        slot_widget(f"{section}.{i}", f"{heading} {i + 1}")

            with ui.card().classes("w-full gap-3"):
                ui.label("生活习惯").classes("text-lg font-semibold")
                ui.label(
                    "整格包含卫生、午餐、午睡等习惯的名称和具体内容，请保留标签。"
                ).classes("text-sm text-gray-600")
                habits_field = (
                    ui.textarea(
                        "生活习惯完整内容",
                        value=_format_habits_cell(editor.edit.body),
                        on_change=mark_dirty,
                    )
                    .classes("w-full")
                    .props("autogrow")
                )

            with ui.card().classes("w-full gap-3"):
                ui.label("家园共育").classes("text-lg font-semibold")
                slot_widget("home", "家园共育")
            with ui.card().classes("w-full gap-3"):
                ui.label("AI 补全、保存与导出").classes("text-lg font-semibold")
                await action_buttons()
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

    async def action_buttons():
        nonlocal generation_button

        async def save():
            await flush()
            await editor.save()
            await render()
            notice.text = "已保存。"

        async def export():
            download = await editor.export()
            ui.download(download.data, filename=download.filename)
            notice.text = "已完成排版检查并导出 Word。"

        with ui.row().classes("w-full flex-wrap items-start gap-2"):
            generation_button = ui.button(
                "AI 补全缺失内容", on_click=lambda: guard(fill_missing_all)
            )
            ui.button("保存", on_click=lambda: guard(save))
            ui.button("导出 Word", on_click=lambda: guard(export))
        if editor.generation_busy:
            generation_button.props("loading")

    async def open_week():
        await editor.open(
            choices[choice_input.value],
            date.fromisoformat(start_input.value),
            date.fromisoformat(end_input.value),
        )
        await render()

    ui.button("打开 / 新建本周共享计划", on_click=lambda: guard(open_week))
