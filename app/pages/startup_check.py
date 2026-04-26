"""系统启动自检页 — 检查 DB / AI 配置 / Word 模板三项关键依赖"""
import asyncio

from nicegui import run, ui

from app.config import AppConfig
from app.db import execute_one
from app.services.ai_service import get_ai_service


# ---------------------------------------------------------------------------
# 各项检测逻辑（同步，供 run.io_bound 调用）
# ---------------------------------------------------------------------------

def _sync_check_db() -> tuple[bool, str]:
    """测试数据库连通性"""
    try:
        execute_one("SELECT 1")
        return True, ""
    except Exception as e:
        return False, str(e)


def _sync_check_ai() -> tuple[bool, str]:
    """检查 AI 配置是否可获取（不发实际请求）"""
    try:
        ai = get_ai_service()
        if ai is None:
            return False, "未配置 AI Key，请前往「系统设置」填写"
        return True, f"模型：{ai.model}"
    except Exception as e:
        return False, str(e)


def _sync_check_template() -> tuple[bool, str]:
    """检查 Word 模板文件是否存在"""
    path = AppConfig.WORD_TEMPLATE
    if path.exists():
        return True, str(path)
    return False, f"文件不存在：{path}"


# ---------------------------------------------------------------------------
# UI 辅助
# ---------------------------------------------------------------------------

_CHECK_ITEMS = [
    ("database",         "数据库连接",    _sync_check_db),
    ("smart_toy",        "AI 配置",       _sync_check_ai),
    ("description",      "Word 模板文件", _sync_check_template),
]


def _render_result_card(container, icon: str, name: str, ok: bool, detail: str):
    """在指定容器中渲染单项检测结果卡片"""
    with container:
        with ui.card().classes("w-full mb-3"):
            with ui.row().classes("items-center gap-3 p-1"):
                ui.icon(icon, size="28px").classes(
                    "text-blue-500"
                )
                ui.label(name).classes("text-base font-semibold flex-1")
                if ok:
                    ui.badge("✅ 正常", color="positive")
                else:
                    ui.badge("❌ 异常", color="negative")
            if detail:
                ui.label(detail).classes(
                    "text-sm text-green-700 px-2 pb-1"
                    if ok
                    else "text-sm text-red-600 px-2 pb-1"
                )


# ---------------------------------------------------------------------------
# 页面函数
# ---------------------------------------------------------------------------

def startup_check_page():
    """系统自检页面"""

    ui.label("🔍 系统自检").classes("text-2xl font-bold mb-4")
    ui.label(
        "检查数据库、AI 配置、Word 模板三项关键依赖是否就绪。"
    ).classes("text-sm text-gray-500 mb-6")

    status_label = ui.label("⏳ 正在检测，请稍候…").classes("text-sm text-gray-400 mb-2")
    results_container = ui.column().classes("w-full")
    check_btn: ui.button = None  # type: ignore  # forward declaration

    async def run_checks():
        status_label.set_text("⏳ 正在检测，请稍候…")
        results_container.clear()
        if check_btn is not None:
            check_btn.disable()

        # DB 和 AI 并发检测；模板为同步文件判断一起并发
        db_result, ai_result, tpl_result = await asyncio.gather(
            run.io_bound(_sync_check_db),
            run.io_bound(_sync_check_ai),
            run.io_bound(_sync_check_template),
        )

        results = [db_result, ai_result, tpl_result]
        for (icon, name, _fn), (ok, detail) in zip(_CHECK_ITEMS, results):
            _render_result_card(results_container, icon, name, ok, detail)

        all_ok = all(ok for ok, _ in results)
        if all_ok:
            status_label.set_text("✅ 所有检测项正常，系统就绪")
        else:
            failed = sum(1 for ok, _ in results if not ok)
            status_label.set_text(f"⚠️ {failed} 项异常，请根据提示修复")

        if check_btn is not None:
            check_btn.enable()

    check_btn = ui.button(
        "🔄 重新检测",
        on_click=run_checks,
    ).classes("mt-4")

    # 页面加载后自动执行一次检测
    ui.timer(0.1, run_checks, once=True)
