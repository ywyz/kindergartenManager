"""设置页面 - 学期时间、年级班级、区域/户外游戏内容、AI API 配置"""
from datetime import date
from nicegui import ui

from app.services.plan_service import (
    get_latest_semester, save_semester,
    save_ai_config, get_all_ai_configs, delete_ai_config, get_decrypted_api_key,
    get_setting, set_setting, get_setting_list, set_setting_list,
)


GRADES = ["小班", "中班", "大班"]
CLASSES = ["1班", "2班", "3班", "4班"]


def settings_page():
    ui.page_title("系统设置 - 幼儿园每日活动计划")

    with ui.column().classes("w-full max-w-3xl mx-auto p-4 gap-4"):
        ui.label("⚙️ 系统设置").classes("text-2xl font-bold")

        # ---- 学期设置 ----
        with ui.card().classes("w-full"):
            ui.label("📅 学期设置").classes("text-lg font-semibold mb-2")

            semester = get_latest_semester() or {}

            semester_name_input = ui.input(
                "学期名称",
                value=semester.get("semester_name", "2025-2026学年第二学期"),
                placeholder="如：2025-2026学年第二学期",
            ).classes("w-full")

            with ui.row().classes("w-full gap-4"):
                start_input = ui.input(
                    "开学日期",
                    value=str(semester.get("start_date", "")) or "2026-02-17",
                    placeholder="YYYY-MM-DD",
                ).classes("flex-1")
                end_input = ui.input(
                    "结束日期",
                    value=str(semester.get("end_date", "")) or "2026-07-10",
                    placeholder="YYYY-MM-DD",
                ).classes("flex-1")

            with ui.row().classes("w-full gap-4"):
                grade_select = ui.select(
                    GRADES,
                    label="年级",
                    value=semester.get("grade", "小班"),
                ).classes("flex-1")
                class_select = ui.select(
                    CLASSES,
                    label="班级",
                    value=semester.get("class_name", "1班"),
                ).classes("flex-1")

            semester_status = ui.label("").classes("text-sm")
            semester_id_ref = {"id": semester.get("id")}

            def on_save_semester():
                try:
                    s_date = date.fromisoformat(start_input.value.strip())
                    e_date = date.fromisoformat(end_input.value.strip())
                    if s_date >= e_date:
                        semester_status.set_text("❌ 开学日期必须早于结束日期")
                        return
                    new_id = save_semester(
                        semester_name=semester_name_input.value.strip(),
                        start_date=s_date,
                        end_date=e_date,
                        grade=grade_select.value,
                        class_name=class_select.value,
                        semester_id=semester_id_ref["id"],
                    )
                    semester_id_ref["id"] = new_id
                    semester_status.set_text("✅ 学期设置已保存")
                except ValueError as e:
                    semester_status.set_text(f"❌ 日期格式错误：{e}")

            ui.button("保存学期设置", on_click=on_save_semester).classes("mt-2")

        # ---- 区域游戏内容 ----
        with ui.card().classes("w-full"):
            ui.label("🎮 游戏内容预设").classes("text-lg font-semibold mb-1")
            ui.label(
                "可配置多条预设内容供每日计划页面选择使用，每条为一个独立方案。"
            ).classes("text-sm text-gray-400 mb-3")

            # -------- 室内区域 --------
            ui.label("室内区域游戏内容").classes("text-sm font-semibold text-gray-600 mb-1")
            area_list: list[str] = get_setting_list("area_content_list")
            area_inputs: list = []
            area_container = ui.column().classes("w-full gap-2")

            def _sync_area():
                """将当前 textarea 值同步回 area_list"""
                for k, ta in enumerate(area_inputs):
                    if k < len(area_list):
                        area_list[k] = ta.value

            def _render_area_items():
                area_inputs.clear()
                area_container.clear()
                with area_container:
                    for i, item in enumerate(area_list):
                        with ui.row().classes("w-full items-start gap-2"):
                            ta = ui.textarea(
                                placeholder="例：美工区：颜料、画笔…",
                                value=item,
                            ).classes("flex-1").props("rows=2")
                            area_inputs.append(ta)
                            ui.button(
                                icon="delete",
                                on_click=lambda _, j=i: _del_area(j),
                            ).props("flat dense color=negative")

            def _del_area(idx: int):
                _sync_area()
                area_list.pop(idx)
                _render_area_items()

            def _add_area():
                _sync_area()
                area_list.append("")
                _render_area_items()

            _render_area_items()
            ui.button("➕ 添加室内区域方案", on_click=_add_area).classes("mt-1").props("flat dense")

            ui.separator().classes("my-3")

            # -------- 户外游戏 --------
            ui.label("户外游戏内容").classes("text-sm font-semibold text-gray-600 mb-1")
            outdoor_list: list[str] = get_setting_list("outdoor_content_list")
            outdoor_inputs: list = []
            outdoor_container = ui.column().classes("w-full gap-2")

            def _sync_outdoor():
                """将当前 textarea 值同步回 outdoor_list"""
                for k, ta in enumerate(outdoor_inputs):
                    if k < len(outdoor_list):
                        outdoor_list[k] = ta.value

            def _render_outdoor_items():
                outdoor_inputs.clear()
                outdoor_container.clear()
                with outdoor_container:
                    for i, item in enumerate(outdoor_list):
                        with ui.row().classes("w-full items-start gap-2"):
                            ta = ui.textarea(
                                placeholder="例：操场、跳绳、大型滑梯…",
                                value=item,
                            ).classes("flex-1").props("rows=2")
                            outdoor_inputs.append(ta)
                            ui.button(
                                icon="delete",
                                on_click=lambda _, j=i: _del_outdoor(j),
                            ).props("flat dense color=negative")

            def _del_outdoor(idx: int):
                _sync_outdoor()
                outdoor_list.pop(idx)
                _render_outdoor_items()

            def _add_outdoor():
                _sync_outdoor()
                outdoor_list.append("")
                _render_outdoor_items()

            _render_outdoor_items()
            ui.button("➕ 添加户外游戏方案", on_click=_add_outdoor).classes("mt-1").props("flat dense")

            ui.separator().classes("my-3")
            content_status = ui.label("").classes("text-sm")

            def on_save_content():
                _sync_area()
                _sync_outdoor()
                set_setting_list("area_content_list", area_list)
                set_setting_list("outdoor_content_list", outdoor_list)
                content_status.set_text("✅ 游戏内容预设已保存")

            ui.button("保存游戏内容预设", on_click=on_save_content).classes("mt-1")

        # ---- 教师与保育员信息 ----
        with ui.card().classes("w-full"):
            ui.label("👩‍🏫 教师与保育员信息").classes("text-lg font-semibold mb-2")
            ui.label(
                "此信息将在周计划导出时自动填入 Word 文档。"
            ).classes("text-sm text-gray-400 mb-3")

            teacher_input = ui.input(
                "班级教师姓名",
                value=get_setting("teacher_name", ""),
                placeholder="例：张老师",
            ).classes("w-full")
            carer_input = ui.input(
                "保育员姓名",
                value=get_setting("carer_name", ""),
                placeholder="例：李阿姨",
            ).classes("w-full mt-2")

            staff_status = ui.label("").classes("text-sm")

            def on_save_staff():
                set_setting("teacher_name", teacher_input.value.strip())
                set_setting("carer_name", carer_input.value.strip())
                staff_status.set_text("✅ 教师信息已保存")

            ui.button("保存教师信息", on_click=on_save_staff).classes("mt-2")

        # ---- AI API 配置（多条，负载均衡）----
        with ui.card().classes("w-full"):
            ui.label("🤖 AI API 配置").classes("text-lg font-semibold mb-1")
            ui.label(
                "支持配置多个 AI 端点，运行时按策略自动分发。API Key 加密存储。"
            ).classes("text-sm text-gray-400 mb-3")

            from app.config import AIConfig

            # 负载均衡策略选择
            with ui.row().classes("w-full items-center gap-3 mb-3"):
                ui.label("负载均衡策略：").classes("text-sm shrink-0")
                lb_mode_select = ui.select(
                    options={"random": "随机", "round_robin": "轮询", "weighted": "加权随机"},
                    value=get_setting("ai_lb_mode", "random"),
                    label="策略",
                ).classes("w-40")
                ui.label("（加权随机：权重越大被选中概率越高）").classes("text-xs text-gray-400")

            ai_cfgs: list[dict] = get_all_ai_configs()
            ai_cfg_inputs: list[dict] = []  # {"url", "key", "model", "weight"}
            ai_cfg_container = ui.column().classes("w-full gap-3")

            def _render_ai_cfg_list():
                ai_cfg_inputs.clear()
                ai_cfg_container.clear()
                with ai_cfg_container:
                    for i, cfg in enumerate(ai_cfgs):
                        existing_key = get_decrypted_api_key(cfg.get("id"))
                        with ui.card().classes("w-full bg-blue-50"):
                            with ui.row().classes("w-full items-center justify-between mb-1"):
                                ui.label(f"配置 {i + 1}").classes("text-sm font-semibold text-gray-600")
                                ui.button(
                                    icon="delete",
                                    on_click=lambda _, j=i: _del_ai_cfg(j),
                                ).props("flat dense color=negative")
                            url_inp = ui.input(
                                "API 地址", value=cfg.get("api_url", ""),
                                placeholder="https://api.openai.com/v1",
                            ).classes("w-full")
                            key_inp = ui.input(
                                "API Key", value=existing_key,
                                password=True, password_toggle_button=True,
                                placeholder="sk-...",
                            ).classes("w-full")
                            with ui.row().classes("w-full gap-3 items-start"):
                                model_inp = ui.input(
                                    "模型名称", value=cfg.get("model_name", ""),
                                    placeholder="gpt-4o",
                                ).classes("flex-1")
                                weight_inp = ui.number(
                                    "权重", value=cfg.get("weight", 1),
                                    min=1, max=100, step=1,
                                ).classes("w-24")
                            ai_cfg_inputs.append({
                                "url": url_inp, "key": key_inp,
                                "model": model_inp, "weight": weight_inp,
                            })

            def _del_ai_cfg(idx: int):
                cfg = ai_cfgs[idx]
                if cfg.get("id"):
                    delete_ai_config(cfg["id"])
                ai_cfgs.pop(idx)
                ai_cfg_inputs.clear()
                _render_ai_cfg_list()

            def _add_ai_cfg():
                ai_cfgs.append({"id": None, "api_url": AIConfig.DEFAULT_URL,
                                "model_name": AIConfig.DEFAULT_MODEL, "weight": 1})
                _render_ai_cfg_list()

            _render_ai_cfg_list()
            ui.button("➕ 添加 AI 配置", on_click=_add_ai_cfg).classes("mt-2").props("flat dense")

            ai_status = ui.label("").classes("text-sm mt-2")

            def on_save_ai():
                set_setting("ai_lb_mode", lb_mode_select.value or "random")
                for cfg, inps in zip(ai_cfgs, ai_cfg_inputs):
                    url = inps["url"].value.strip()
                    key = inps["key"].value.strip()
                    model = inps["model"].value.strip()
                    weight = int(inps["weight"].value or 1)
                    if not url or not key or not model:
                        ai_status.set_text("❌ 请填写每条配置的地址、Key 和模型名称")
                        return
                    new_id = save_ai_config(url, key, model, cfg.get("id"), weight)
                    cfg["id"] = new_id
                ai_status.set_text(f"✅ AI 配置已保存（共 {len(ai_cfgs)} 条，策略：{lb_mode_select.value}）")

            ui.button("保存 AI 配置", on_click=on_save_ai).classes("mt-2")
