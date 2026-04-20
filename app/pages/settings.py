"""设置页面 - 学期时间、年级班级、区域/户外游戏内容、AI API 配置"""
from datetime import date
from nicegui import ui

from app.services.plan_service import (
    get_latest_semester, save_semester,
    get_ai_config, save_ai_config, get_decrypted_api_key,
    get_setting, set_setting,
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
            ui.label("🎮 区域游戏内容").classes("text-lg font-semibold mb-2")
            area_content = ui.textarea(
                "室内区域游戏内容（可多行描述各区域设置）",
                value=get_setting("area_content", ""),
                placeholder="例：\n美工区：颜料、画笔、彩纸\n建构区：积木、纸杯\n阅读区：绘本若干",
            ).classes("w-full").props("rows=5")

            outdoor_content = ui.textarea(
                "户外游戏内容（体育器材、场地等）",
                value=get_setting("outdoor_content", ""),
                placeholder="例：操场、跳绳、大型滑梯、沙池、平衡木",
            ).classes("w-full").props("rows=3")

            content_status = ui.label("").classes("text-sm")

            def on_save_content():
                set_setting("area_content", area_content.value)
                set_setting("outdoor_content", outdoor_content.value)
                content_status.set_text("✅ 游戏内容设置已保存")

            ui.button("保存游戏内容", on_click=on_save_content).classes("mt-2")

        # ---- AI API 配置 ----
        with ui.card().classes("w-full"):
            ui.label("🤖 AI API 配置").classes("text-lg font-semibold mb-2")
            ui.label(
                "配置与 OpenAI 兼容的 AI 接口。API Key 将加密存储在数据库中。"
            ).classes("text-sm text-gray-500 mb-2")

            ai_cfg = get_ai_config() or {}

            from app.config import AIConfig
            api_url_input = ui.input(
                "API 地址",
                value=ai_cfg.get("api_url", AIConfig.DEFAULT_URL),
                placeholder="https://api.openai.com/v1",
            ).classes("w-full")

            api_model_input = ui.input(
                "模型名称",
                value=ai_cfg.get("model_name", AIConfig.DEFAULT_MODEL),
                placeholder="gpt-4o",
            ).classes("w-full")

            # API Key 读取：解密显示（安全起见，实际生产中不显示原文）
            existing_key = get_decrypted_api_key(ai_cfg.get("id"))
            api_key_input = ui.input(
                "API Key",
                value=existing_key,
                password=True,
                password_toggle_button=True,
                placeholder="sk-...",
            ).classes("w-full")

            ai_status = ui.label("").classes("text-sm")
            ai_id_ref = {"id": ai_cfg.get("id")}

            def on_save_ai():
                url = api_url_input.value.strip()
                key = api_key_input.value.strip()
                model = api_model_input.value.strip()
                if not url or not key or not model:
                    ai_status.set_text("❌ 请填写完整的 API 配置")
                    return
                new_id = save_ai_config(url, key, model, ai_id_ref["id"])
                ai_id_ref["id"] = new_id
                ai_status.set_text("✅ AI 配置已保存")

            ui.button("保存 AI 配置", on_click=on_save_ai).classes("mt-2")

        # ---- AI 生成参数 ----
        with ui.card().classes("w-full"):
            ui.label("🎛️ AI 生成参数").classes("text-lg font-semibold mb-2")
            ui.label(
                "调节 AI 生成的创意度与多样性。温度越高内容越多样但可能不稳定，越低越保守。"
            ).classes("text-sm text-gray-500 mb-2")

            current_temp = float(get_setting("ai_temperature", "0.95"))
            current_top_p = float(get_setting("ai_top_p", "0.95"))
            current_freq_penalty = float(get_setting("ai_frequency_penalty", "0.3"))

            temp_slider = ui.slider(
                min=0.0, max=2.0, step=0.05, value=current_temp,
            ).classes("w-full").props('label-always')
            ui.label("").bind_text_from(temp_slider, "value", lambda v: f"温度 (temperature): {v:.2f}")

            top_p_slider = ui.slider(
                min=0.0, max=1.0, step=0.05, value=current_top_p,
            ).classes("w-full").props('label-always')
            ui.label("").bind_text_from(top_p_slider, "value", lambda v: f"Top P: {v:.2f}")

            freq_slider = ui.slider(
                min=0.0, max=2.0, step=0.05, value=current_freq_penalty,
            ).classes("w-full").props('label-always')
            ui.label("").bind_text_from(freq_slider, "value", lambda v: f"频率惩罚 (frequency_penalty): {v:.2f}")

            param_status = ui.label("").classes("text-sm")

            def on_save_params():
                set_setting("ai_temperature", str(temp_slider.value))
                set_setting("ai_top_p", str(top_p_slider.value))
                set_setting("ai_frequency_penalty", str(freq_slider.value))
                param_status.set_text("✅ AI 生成参数已保存")

            ui.button("保存生成参数", on_click=on_save_params).classes("mt-2")
