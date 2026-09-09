"""Execute actual page handlers with widget doubles and real persistence.

This is headless handler evidence, not browser or Office acceptance.
"""

import ast
import os
from contextlib import asynccontextmanager
from datetime import date
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from docx import Document

from app.api.schemas import DailyPlanOut
from app.integration.word_export.exporter import export_daily_plan
from app.repository.daily_plan_repository import get_daily_plan_by_date, save_daily_plan
from app.service.lesson_plan_service import LessonPlanResult
from app.ui.daily_plan_target import UiGenerationGuard


class Widget:
    value = ""
    text = ""

    def classes(self, *args, **kwargs):
        return self

    def props(self, *args, **kwargs):
        return self


def handlers(session):
    path = Path(os.getenv("WPB_UI_SOURCE", "app/ui/pages/daily_plan.py"))
    tree = ast.parse(path.read_text())
    names = {"_capture_save", "_clear_plan_body", "_load_draft", "_do_split"}
    nodes = [
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names
    ]
    module = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__", names=[ast.alias(name="annotations")], level=0
            ),
            *nodes,
        ],
        type_ignores=[],
    )
    scope = {}
    for name in [
        "name_input",
        "goal_area",
        "prep_area",
        "key_area",
        "difficult_area",
        "adapted_area",
        "original_area",
        "morning_activity_area",
        "morning_talk_area",
        "area_game_area",
        "outdoor_activity_area",
        "daily_reflection_area",
        "split_msg",
        "split_btn",
    ]:
        scope[name] = Widget()
    day = date(2026, 9, 7)
    selection = SimpleNamespace(selected_date=day)
    scope.update(
        state={
            "selected_date": day,
            "week_number": 2,
            "weekday_cn": "周一",
            "grade": "中班",
            "class_name": "合成班",
            "loaded_plan_id": None,
            "loaded_revision": None,
        },
        selection_state={"current": selection},
        tenant_id=11,
        user_id=7,
        form_generation=UiGenerationGuard(),
        get_daily_plan_by_date=get_daily_plan_by_date,
        _require_live_session=AsyncMock(return_value=object()),
        split_operations=SimpleNamespace(owns=lambda _: True),
    )

    @asynccontextmanager
    async def factory():
        yield session

    scope["AsyncSessionLocal"] = factory
    scope["_capture_plan_target"] = lambda: SimpleNamespace(
        selected_date=day,
        plan_id=scope["state"]["loaded_plan_id"],
        revision=scope["state"]["loaded_revision"],
    )
    scope["_is_current_plan_target"] = lambda target: target is scope["target"]
    scope["target"] = scope["_capture_plan_target"]()
    scope["process_lesson_plan"] = AsyncMock(
        return_value=LessonPlanResult(
            "目标", "准备", "重点", "难点", "原过程", "改过程", activity_name="秋叶拼画"
        )
    )
    # Compile only trusted local production handlers; no user/AI text is executed.
    exec(compile(ast.fix_missing_locations(module), str(path), "exec"), scope)  # noqa: S102
    return scope, selection


async def test_split_hand_edit_frozen_save_reload_api_word(async_session):
    s, selection = handlers(async_session)
    await s["_do_split"](object(), (s["target"], "活动名称：秋叶拼画", "中班"))
    assert s["name_input"].value == "秋叶拼画"
    s["name_input"].value = "叶子拓印"
    _, payload = s["_capture_save"]()
    s["name_input"].value = "后来未保存的输入"
    assert payload["activity_name"] == "叶子拓印"
    plan = await save_daily_plan(async_session, 11, 7, **payload)
    await async_session.commit()
    s["_clear_plan_body"]()
    assert s["name_input"].value == ""
    await s["_load_draft"](selection.selected_date, selection)
    assert s["name_input"].value == "叶子拓印"
    assert DailyPlanOut.from_model(plan).activity_name == "叶子拓印"
    assert (
        Document(BytesIO(export_daily_plan(plan, []))).tables[0].rows[6].cells[-1].text
        == "活动主题：叶子拓印"
    )


async def test_missing_name_split_prompts_hand_entry_and_stale_page_rejected(
    async_session,
):
    s, _ = handlers(async_session)
    s["process_lesson_plan"].return_value = LessonPlanResult(
        "目标", "", "", "", "过程", "过程"
    )
    await s["_do_split"](object(), (s["target"], "只有过程", "中班"))
    assert s["name_input"].value == ""
    assert "手动填写" in s["split_msg"].text
    s["name_input"].value = "教师原输入"
    await s["_do_split"](object(), (object(), "旧页面文本", "中班"))
    assert s["name_input"].value == "教师原输入"
    assert s["process_lesson_plan"].await_count == 1
