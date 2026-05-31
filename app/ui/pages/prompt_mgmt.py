"""提示词管理页面（路由：/prompts）。

支持以下任务类型的提示词版本管理，每种类型独立维护版本历史：
- split：教案拆分
- adapt：年龄适配
- morning_exercise：晨间活动
- morning_talk：晨间谈话
- area_game：区域游戏
- outdoor_game：户外游戏
- daily_reflection：一日活动反思

功能：
- 查看并编辑当前激活提示词
- 保存为新版本（自动递增版本号，旧版本设为 inactive）
- 查看历史版本列表，支持一键回滚
"""

from nicegui import app, ui

from app.auth.jwt import decode_access_token
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AiCallError, AiParseError, ConfigError
from app.core.logging import get_logger
from app.integration.ai_client.adapt_client import DEFAULT_ADAPT_PROMPT, adapt_activity_process
from app.integration.ai_client.base import call_ai_text
from app.integration.ai_client.generate_client import (
    DEFAULT_AREA_GAME_PROMPT,
    DEFAULT_DAILY_REFLECTION_PROMPT,
    DEFAULT_MORNING_EXERCISE_PROMPT,
    DEFAULT_MORNING_TALK_PROMPT,
    DEFAULT_OUTDOOR_GAME_PROMPT,
)
from app.integration.ai_client.lesson_plan_client import DEFAULT_SPLIT_PROMPT, split_lesson_plan
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key
from app.repository.prompt_repository import (
    get_active_prompt,
    list_versions,
    rollback_to_version,
    save_new_version,
)

logger = get_logger(__name__)

# 每种任务类型的展示名称与内置默认提示词
_TASK_CONFIG = {
    "split": {
        "label": "教案拆分提示词",
        "placeholder": DEFAULT_SPLIT_PROMPT,
    },
    "adapt": {
        "label": "年龄适配提示词",
        "placeholder": DEFAULT_ADAPT_PROMPT,
    },
    "morning_exercise": {
        "label": "晨间活动提示词",
        "placeholder": DEFAULT_MORNING_EXERCISE_PROMPT,
    },
    "morning_talk": {
        "label": "晨间谈话提示词",
        "placeholder": DEFAULT_MORNING_TALK_PROMPT,
    },
    "area_game": {
        "label": "区域游戏提示词",
        "placeholder": DEFAULT_AREA_GAME_PROMPT,
    },
    "outdoor_game": {
        "label": "户外游戏提示词",
        "placeholder": DEFAULT_OUTDOOR_GAME_PROMPT,
    },
    "daily_reflection": {
        "label": "一日活动反思提示词",
        "placeholder": DEFAULT_DAILY_REFLECTION_PROMPT,
    },
}

# 每种任务类型的输出格式要求（展示在编辑器上方）
_TASK_SCHEMA: dict[str, str] = {
    "split": (
        "输出 JSON，必须包含以下 5 个字段（key 名称不可修改）：\n"
        '{"activity_goal": "...", "activity_prep": "...", '
        '"activity_key": "...", "activity_difficult": "...", "activity_process": "..."}'
    ),
    "adapt": (
        "输出 JSON，必须包含以下字段（key 名称不可修改）：\n"
        '{"adapted_process": "改写后的活动过程"}\n'
        "⚠ key 必须是 adapted_process，不可使用 activity_process 等其他名称！"
    ),
    "morning_exercise": "输出纯文本（非 JSON），按提示词中定义的格式生成晨间活动方案",
    "morning_talk": "输出纯文本（非 JSON），按提示词中定义的格式生成晨间谈话方案",
    "area_game": "输出纯文本（非 JSON），按提示词中定义的格式生成区域游戏方案",
    "outdoor_game": "输出纯文本（非 JSON），按提示词中定义的格式生成户外游戏方案",
    "daily_reflection": "输出纯文本（非 JSON），按提示词中定义的格式生成一日活动反思",
}

# 测试区输入框提示文字
_TEST_PLACEHOLDER: dict[str, str] = {
    "split": "粘贴完整教案文本（含活动目标、准备、过程等）进行测试……",
    "adapt": "粘贴活动过程原文进行测试……",
    "morning_exercise": "输入背景信息进行测试（如：中班，今日教案主题是春天的植物……）",
    "morning_talk": "输入活动背景进行测试（如：中班，今日活动主题是春天的花朵……）",
    "area_game": "输入背景信息进行测试（如：中班，可用室内区域：美工区、建构区……）",
    "outdoor_game": "输入背景信息进行测试（如：中班，可用户外区域：操场、沙池……）",
    "daily_reflection": "输入当日活动概述进行测试（如：中班，今日开展了春天主题活动……）",
}


def _get_current_user() -> dict | None:
    """从 storage 中解码当前用户信息，未登录返回 None。"""
    token = app.storage.user.get("token")
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None


@ui.page("/prompts")
async def prompt_mgmt_page() -> None:
    user = _get_current_user()
    if not user:
        ui.navigate.to("/")
        return

    tenant_id: int = user["tenant_id"]
    user_id: int = int(user["sub"])

    # ── 顶部导航 ─────────────────────────────────────────────────────────────
    with ui.header().classes("bg-blue-700 text-white items-center px-4"):
        ui.label("幼儿园教学管理系统").classes("text-lg font-bold flex-1")
        ui.button(
            "返回主页",
            on_click=lambda: ui.navigate.to("/home"),
        ).classes("text-white")
        ui.button(
            "退出登录",
            on_click=lambda: (app.storage.user.clear(), ui.navigate.to("/")),
        ).classes("text-white ml-2")

    with ui.column().classes("w-full max-w-3xl mx-auto p-6 gap-6"):
        ui.label("提示词管理").classes("text-xl font-bold text-blue-700")
        ui.label(
            "为每种 AI 任务配置自定义提示词版本。保存新版本后，下一次 AI 调用将自动使用最新激活版本。"
        ).classes("text-sm text-gray-500")

        # ── Tabs ──────────────────────────────────────────────────────────────
        with ui.tabs().classes("w-full") as tabs:
            tab_split = ui.tab("教案拆分")
            tab_adapt = ui.tab("年龄适配")
            tab_morning_exercise = ui.tab("晨间活动")
            tab_morning_talk = ui.tab("晨间谈话")
            tab_area_game = ui.tab("区域游戏")
            tab_outdoor_game = ui.tab("户外游戏")
            tab_daily_reflection = ui.tab("一日反思")

        with ui.tab_panels(tabs, value=tab_split).classes("w-full"):
            with ui.tab_panel(tab_split):
                await _build_task_panel(tenant_id, user_id, "split")
            with ui.tab_panel(tab_adapt):
                await _build_task_panel(tenant_id, user_id, "adapt")
            with ui.tab_panel(tab_morning_exercise):
                await _build_task_panel(tenant_id, user_id, "morning_exercise")
            with ui.tab_panel(tab_morning_talk):
                await _build_task_panel(tenant_id, user_id, "morning_talk")
            with ui.tab_panel(tab_area_game):
                await _build_task_panel(tenant_id, user_id, "area_game")
            with ui.tab_panel(tab_outdoor_game):
                await _build_task_panel(tenant_id, user_id, "outdoor_game")
            with ui.tab_panel(tab_daily_reflection):
                await _build_task_panel(tenant_id, user_id, "daily_reflection")


async def _build_task_panel(tenant_id: int, user_id: int, task_type: str) -> None:
    """构建单个任务类型的提示词编辑区块（含历史版本列表）。"""
    config = _TASK_CONFIG[task_type]
    label = config["label"]
    placeholder = config["placeholder"]

    # 从数据库读取当前激活版本
    async with AsyncSessionLocal() as session:
        active = await get_active_prompt(session, tenant_id, user_id, task_type)
        versions = await list_versions(session, tenant_id, user_id, task_type)

    initial_content = active.content if active else ""

    with ui.card().classes("w-full"):
        ui.label(label).classes("text-base font-semibold text-blue-700 mb-1")

        if active:
            ui.badge(f"当前激活：v{active.version}", color="green").classes("mb-2")
        else:
            ui.badge("使用内置默认（尚未保存自定义版本）", color="gray").classes("mb-2")

        content_area = ui.textarea(
            placeholder=placeholder,
            value=initial_content,
        ).classes("w-full font-mono text-sm").props("rows=12 outlined")

        msg_label = ui.label("").classes("text-sm mt-1")

        async def save_version() -> None:
            new_content = content_area.value.strip()
            if not new_content:
                msg_label.set_text("⚠ 内容不能为空")
                msg_label.classes(replace="text-sm mt-1 text-orange-600")
                return

            try:
                async with AsyncSessionLocal() as session:
                    new_prompt = await save_new_version(
                        session, tenant_id, user_id, task_type, new_content
                    )
                logger.info(
                    "保存提示词新版本",
                    extra={
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "task_type": task_type,
                        "version": new_prompt.version,
                    },
                )
                msg_label.set_text(f"✓ 已保存为 v{new_prompt.version}，刷新页面可查看历史")
                msg_label.classes(replace="text-sm mt-1 text-green-600")
                # 刷新历史列表
                history_container.clear()
                async with AsyncSessionLocal() as session:
                    updated_versions = await list_versions(
                        session, tenant_id, user_id, task_type
                    )
                _render_history(history_container, updated_versions, tenant_id, user_id, task_type, content_area, msg_label)
            except Exception as e:
                logger.error("保存提示词失败", extra={"error": str(e)})
                msg_label.set_text(f"✗ 保存失败：{e}")
                msg_label.classes(replace="text-sm mt-1 text-red-600")

        ui.button("保存为新版本", on_click=save_version).classes(
            "bg-blue-600 text-white mt-2"
        )

    # ── 格式要求说明 ──────────────────────────────────────────────────────────
    schema_desc = _TASK_SCHEMA.get(task_type, "")
    if schema_desc:
        with ui.card().classes("w-full bg-amber-50 border border-amber-200 mt-2"):
            ui.label("⚠ 提示词输出格式要求").classes(
                "text-xs font-semibold text-amber-700 mb-1"
            )
            ui.label(schema_desc).classes(
                "text-xs text-gray-700 font-mono whitespace-pre-wrap"
            )

    # ── 在线测试 ──────────────────────────────────────────────────────────────
    with ui.expansion("🧪 测试提示词效果", icon="science").classes("w-full mt-2"):
        with ui.column().classes("w-full gap-3 p-1"):

            test_input = ui.textarea(
                label="测试输入",
                placeholder=_TEST_PLACEHOLDER.get(task_type, "请输入测试内容……"),
            ).classes("w-full").props("rows=6 outlined")

            # 年龄适配额外选项
            test_grade_select = None
            if task_type == "adapt":
                test_grade_select = ui.select(
                    ["小班", "中班", "大班"],
                    value="中班",
                    label="测试年龄段",
                ).props("outlined dense")

            test_msg = ui.label("").classes("text-sm")

            # 输出区域（split 显示 5 个字段，其余显示原始文本）
            if task_type == "split":
                test_goal_out = ui.textarea(label="活动目标").classes("w-full").props(
                    "rows=3 outlined readonly"
                )
                test_prep_out = ui.textarea(label="活动准备").classes("w-full").props(
                    "rows=2 outlined readonly"
                )
                test_key_out = ui.textarea(label="活动重点").classes("w-full").props(
                    "rows=2 outlined readonly"
                )
                test_diff_out = ui.textarea(label="活动难点").classes("w-full").props(
                    "rows=2 outlined readonly"
                )
                test_proc_out = ui.textarea(label="活动过程").classes("w-full").props(
                    "rows=5 outlined readonly"
                )
            else:
                test_result_out = ui.textarea(label="AI 返回结果").classes(
                    "w-full"
                ).props("rows=7 outlined readonly")

            async def do_test() -> None:
                if not content_area.value.strip():
                    test_msg.classes(replace="text-sm text-orange-500")
                    test_msg.set_text("⚠ 请先在上方输入提示词内容")
                    return
                if not test_input.value.strip():
                    test_msg.classes(replace="text-sm text-orange-500")
                    test_msg.set_text("⚠ 请输入测试文本")
                    return

                test_btn.props("loading")
                test_msg.classes(replace="text-sm text-gray-500")
                test_msg.set_text("AI 测试中，请稍候……")

                try:
                    async with AsyncSessionLocal() as session:
                        ai_key = await get_active_ai_key(session, tenant_id, user_id)
                    if ai_key is None:
                        test_msg.classes(replace="text-sm text-orange-500")
                        test_msg.set_text("⚠ 未配置 AI Key，请到【设置】页面配置")
                        return

                    api_key_plain = get_decrypted_key(ai_key)
                    base_url = ai_key.api_base_url
                    model = ai_key.model_name
                    current_prompt = content_area.value.strip()

                    if task_type == "split":
                        result = await split_lesson_plan(
                            raw_text=test_input.value,
                            api_base_url=base_url,
                            api_key=api_key_plain,
                            model_name=model,
                            system_prompt=current_prompt,
                        )
                        test_goal_out.value = result.get("activity_goal", "")
                        test_prep_out.value = result.get("activity_prep", "")
                        test_key_out.value = result.get("activity_key", "")
                        test_diff_out.value = result.get("activity_difficult", "")
                        test_proc_out.value = result.get("activity_process", "")

                    elif task_type == "adapt":
                        grade = test_grade_select.value if test_grade_select else "中班"
                        adapted = await adapt_activity_process(
                            original=test_input.value,
                            grade=grade,
                            api_base_url=base_url,
                            api_key=api_key_plain,
                            model_name=model,
                            system_prompt=current_prompt,
                        )
                        test_result_out.value = adapted

                    else:
                        # 生成类任务：直接用 call_ai_text，以 test_input 为用户消息
                        text = await call_ai_text(
                            messages=[
                                {"role": "system", "content": current_prompt},
                                {"role": "user", "content": test_input.value},
                            ],
                            api_base_url=base_url,
                            api_key=api_key_plain,
                            model_name=model,
                        )
                        test_result_out.value = text

                    test_msg.classes(replace="text-sm text-green-600")
                    test_msg.set_text("✅ 测试完成")

                except AiParseError as e:
                    test_msg.classes(replace="text-sm text-red-500")
                    test_msg.set_text(f"❌ 解析失败：{e.message}")
                except AiCallError as e:
                    test_msg.classes(replace="text-sm text-red-500")
                    test_msg.set_text(f"❌ AI调用失败：{e.message}")
                except ConfigError as e:
                    test_msg.classes(replace="text-sm text-orange-500")
                    test_msg.set_text(f"⚠ {e.message}")
                except Exception as e:
                    test_msg.classes(replace="text-sm text-red-500")
                    test_msg.set_text(f"❌ {type(e).__name__}: {e}")
                finally:
                    test_btn.props(remove="loading")

            test_btn = ui.button("测试当前提示词", on_click=do_test).classes(
                "bg-amber-600 text-white"
            )

    # ── 历史版本列表 ──────────────────────────────────────────────────────────
    history_container = ui.column().classes("w-full gap-2 mt-2")
    _render_history(history_container, versions, tenant_id, user_id, task_type, content_area, msg_label)


def _render_history(
    container: ui.column,
    versions: list,
    tenant_id: int,
    user_id: int,
    task_type: str,
    content_area: ui.textarea,
    msg_label: ui.label,
) -> None:
    """渲染历史版本列表到指定容器。"""
    if not versions:
        return

    with container:
        ui.label("历史版本").classes("text-sm font-semibold text-gray-600 mt-2")
        for v in versions:
            created_str = v.created_at.strftime("%Y-%m-%d %H:%M") if v.created_at else "—"
            with ui.row().classes("items-center gap-2 bg-gray-50 rounded p-2 w-full"):
                if v.is_active:
                    ui.badge(f"v{v.version} ✓ 激活", color="green")
                else:
                    ui.badge(f"v{v.version}", color="gray")
                ui.label(created_str).classes("text-xs text-gray-500 flex-1")

                if not v.is_active:
                    # 捕获当前循环变量
                    _ver = v.version

                    async def rollback(_ver=_ver) -> None:
                        try:
                            async with AsyncSessionLocal() as session:
                                rolled = await rollback_to_version(
                                    session, tenant_id, user_id, task_type, _ver
                                )
                            content_area.value = rolled.content
                            msg_label.set_text(f"✓ 已回滚到 v{_ver}，刷新页面可看完整历史")
                            msg_label.classes(replace="text-sm mt-1 text-blue-600")
                            # 刷新容器
                            container.clear()
                            async with AsyncSessionLocal() as session:
                                updated = await list_versions(
                                    session, tenant_id, user_id, task_type
                                )
                            _render_history(container, updated, tenant_id, user_id, task_type, content_area, msg_label)
                        except Exception as e:
                            msg_label.set_text(f"✗ 回滚失败：{e}")
                            msg_label.classes(replace="text-sm mt-1 text-red-600")

                    ui.button("回滚", on_click=rollback).classes(
                        "text-xs bg-gray-200 text-gray-700"
                    ).props("size=sm")
