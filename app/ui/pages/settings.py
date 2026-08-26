"""配置页面（路由：/settings）。

包含配置区块：
1. 学期配置：学期名称、开始日期、结束日期
2. 班级配置：年级、班级名称、区域内容、户外内容
3. AI 文本模型 / 视觉模型
4. 数据库配置（SQLite / MySQL）
5. 端口配置
"""

from datetime import date

from nicegui import ui

from app.core.config import settings as app_settings
from app.core.database import AsyncSessionLocal
from app.core.env_writer import read_dot_env, write_dot_env
from app.core.exceptions import CryptoError
from app.repository.ai_key_repository import (
    get_active_ai_key,
    get_decrypted_key,
    save_ai_key,
)
from app.repository.class_repository import get_class_config, upsert_class_config
from app.repository.semester_repository import (
    get_active_semester,
    upsert_active_semester,
)
from app.service.settings_service import verify_saved_ai_connection
from app.ui.auth_context import (
    TrustedUiSession,
    require_bound_ui_session,
    require_current_ui_session,
)
from app.ui.components.app_shell import render_shell
from app.ui.helpers import mask_api_key as _mask_api_key

_GRADES = ["小班", "中班", "大班"]


@ui.page("/settings")
async def settings_page() -> None:
    ui_session = await require_current_ui_session()
    if ui_session is None:
        return

    tenant_id = ui_session.tenant_id
    user_id = ui_session.user_id

    await render_shell(ui_session.as_user_dict(), active="settings")

    async def require_live_session() -> TrustedUiSession | None:
        return await require_bound_ui_session(ui_session)

    with ui.column().classes("w-full max-w-2xl mx-auto p-6 gap-6"):
        # ══════════════════════════════════════════════════════════════════════
        # 区块一：学期配置
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            ui.label("学期配置").classes("text-lg font-bold text-blue-700 mb-2")

            semester_name_input = ui.input(
                label="学期名称",
                placeholder="如：2025-2026学年第一学期",
            ).classes("w-full")

            with ui.row().classes("w-full gap-4"):
                start_date_input = ui.input(
                    label="开始日期",
                    placeholder="YYYY-MM-DD",
                ).classes("flex-1")
                with start_date_input:
                    with ui.menu().props("no-parent-event") as start_menu:
                        with ui.date().bind_value(start_date_input):
                            with ui.row().classes("justify-end"):
                                ui.button("确定", on_click=start_menu.close).props(
                                    "flat"
                                )
                    ui.button(icon="event", on_click=start_menu.open).props(
                        "flat round"
                    )

                end_date_input = ui.input(
                    label="结束日期",
                    placeholder="YYYY-MM-DD",
                ).classes("flex-1")
                with end_date_input:
                    with ui.menu().props("no-parent-event") as end_menu:
                        with ui.date().bind_value(end_date_input):
                            with ui.row().classes("justify-end"):
                                ui.button("确定", on_click=end_menu.close).props("flat")
                    ui.button(icon="event", on_click=end_menu.open).props("flat round")

            semester_msg = ui.label("").classes("text-sm mt-1")

            async def save_semester() -> None:
                current = await require_live_session()
                if current is None:
                    return
                semester_msg.classes(remove="text-green-600 text-red-500")
                name = semester_name_input.value.strip()
                start_str = start_date_input.value.strip()
                end_str = end_date_input.value.strip()

                if not name:
                    semester_msg.text = "请输入学期名称"
                    semester_msg.classes(add="text-red-500")
                    return
                if not start_str or not end_str:
                    semester_msg.text = "请选择开始和结束日期"
                    semester_msg.classes(add="text-red-500")
                    return

                try:
                    start_date = date.fromisoformat(start_str)
                    end_date = date.fromisoformat(end_str)
                except ValueError:
                    semester_msg.text = "日期格式错误，请使用 YYYY-MM-DD"
                    semester_msg.classes(add="text-red-500")
                    return

                if start_date >= end_date:
                    semester_msg.text = "结束日期必须晚于开始日期"
                    semester_msg.classes(add="text-red-500")
                    return

                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        await upsert_active_semester(
                            session,
                            current.tenant_id,
                            current.user_id,
                            name,
                            start_date,
                            end_date,
                        )

                semester_msg.text = "学期配置已保存"
                semester_msg.classes(add="text-green-600")

            ui.button("保存学期配置", on_click=save_semester).classes(
                "mt-3 bg-blue-600 text-white"
            )

        # ══════════════════════════════════════════════════════════════════════
        # 区块二：班级配置
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            ui.label("班级配置").classes("text-lg font-bold text-blue-700 mb-2")

            with ui.row().classes("w-full gap-4"):
                grade_select = ui.select(
                    options=_GRADES,
                    label="年级",
                    value=_GRADES[0],
                ).classes("flex-1")

                class_name_input = ui.input(
                    label="班级名称",
                    placeholder="如：阳光班",
                ).classes("flex-1")

            teacher_name_input = ui.input(
                label="教师姓名",
                placeholder="如：张老师",
            ).classes("w-full mt-2")

            indoor_areas_input = ui.textarea(
                label="区域内容",
                placeholder="描述班级室内区域活动内容……",
            ).classes("w-full mt-2")

            outdoor_content_input = ui.textarea(
                label="户外内容",
                placeholder="描述户外游戏活动内容……",
            ).classes("w-full mt-2")

            class_msg = ui.label("").classes("text-sm mt-1")

            async def save_class() -> None:
                current = await require_live_session()
                if current is None:
                    return
                class_msg.classes(remove="text-green-600 text-red-500")
                c_name = class_name_input.value.strip()
                grade = grade_select.value

                if not c_name:
                    class_msg.text = "请输入班级名称"
                    class_msg.classes(add="text-red-500")
                    return

                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        await upsert_class_config(
                            session,
                            current.tenant_id,
                            current.user_id,
                            grade=grade,
                            class_name=c_name,
                            teacher_name=teacher_name_input.value.strip() or None,
                            indoor_areas=indoor_areas_input.value.strip() or None,
                            outdoor_content=outdoor_content_input.value.strip() or None,
                        )

                class_msg.text = "班级配置已保存"
                class_msg.classes(add="text-green-600")

            ui.button("保存班级配置", on_click=save_class).classes(
                "mt-3 bg-blue-600 text-white"
            )

        # ══════════════════════════════════════════════════════════════════════
        # 区块三：AI 接口配置 — 文本模型
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            ui.label("AI 接口配置 — 文本模型").classes(
                "text-lg font-bold text-blue-700 mb-2"
            )
            ui.label(
                "用于教案拆分、年龄适配、一日活动生成等文本任务。API Key 保存后以脱敏形式显示。"
            ).classes("text-xs text-gray-500 mb-3")

            ai_url_input = ui.input(
                label="API 地址",
                placeholder="如：https://api.openai.com/v1",
            ).classes("w-full")

            ai_model_input = ui.input(
                label="模型名称",
                placeholder="如：gpt-4o-mini / deepseek-chat / qwen-plus",
            ).classes("w-full mt-2")

            ai_key_input = ui.input(
                label="API Key",
                placeholder="输入 API Key（保存后脱敏显示）",
                password=True,
                password_toggle_button=True,
            ).classes("w-full mt-2")

            ai_msg = ui.label("").classes("text-sm mt-1")

            # 记录当前展示给用户的脱敏值，用于判断是否修改过
            _current_masked: list[str] = [""]

            async def save_ai_key_handler() -> None:
                current = await require_live_session()
                if current is None:
                    return
                ai_msg.classes(remove="text-green-600 text-red-500")
                url = ai_url_input.value.strip()
                model = ai_model_input.value.strip()
                key_val = ai_key_input.value.strip()

                if not url:
                    ai_msg.text = "请输入 API 地址"
                    ai_msg.classes(add="text-red-500")
                    return

                if not model:
                    ai_msg.text = "请输入模型名称"
                    ai_msg.classes(add="text-red-500")
                    return

                # 判断用户是否修改了 Key
                key_changed = key_val and key_val != _current_masked[0]

                if key_changed:
                    # 用户输入了新 Key
                    plain_key = key_val
                elif not key_val:
                    # Key 字段为空：尝试复用数据库中已有的 Key
                    async with AsyncSessionLocal() as session:
                        existing = await get_active_ai_key(
                            session,
                            current.tenant_id,
                            current.user_id,
                        )
                    if existing is None:
                        ai_msg.text = "请输入 API Key"
                        ai_msg.classes(add="text-red-500")
                        return
                    try:
                        plain_key = get_decrypted_key(existing)
                    except CryptoError:
                        ai_msg.text = "已有 Key 解密失败，请重新输入"
                        ai_msg.classes(add="text-red-500")
                        return
                else:
                    # 用户未修改 Key（值等于脱敏字符串）：复用已有 Key
                    async with AsyncSessionLocal() as session:
                        existing = await get_active_ai_key(
                            session,
                            current.tenant_id,
                            current.user_id,
                        )
                    if existing is None:
                        ai_msg.text = "请输入 API Key"
                        ai_msg.classes(add="text-red-500")
                        return
                    try:
                        plain_key = get_decrypted_key(existing)
                    except CryptoError:
                        ai_msg.text = "已有 Key 解密失败，请重新输入"
                        ai_msg.classes(add="text-red-500")
                        return

                current = await require_live_session()
                if current is None:
                    return
                async with AsyncSessionLocal() as session:
                    await save_ai_key(
                        session,
                        current.tenant_id,
                        current.user_id,
                        url,
                        plain_key,
                        model,
                        key_type="text",
                    )

                masked = _mask_api_key(plain_key)
                _current_masked[0] = masked
                ai_key_input.value = masked
                ai_msg.text = "AI 接口配置已保存"
                ai_msg.classes(add="text-green-600")

            async def verify_connection() -> None:
                current = await require_live_session()
                if current is None:
                    return
                ai_msg.classes(remove="text-green-600 text-red-500 text-blue-600")
                ai_msg.text = "连接测试中……"

                async with AsyncSessionLocal() as session:
                    result = await verify_saved_ai_connection(
                        session,
                        tenant_id=current.tenant_id,
                        user_id=current.user_id,
                        key_type="text",
                    )
                if await require_live_session() is None:
                    return

                if result.code == "not_configured":
                    ai_msg.text = "请先保存 AI 接口配置"
                    ai_msg.classes(add="text-red-500")
                    return
                if result.code == "key_decryption_failed":
                    ai_msg.text = "Key 解密失败，请重新保存"
                    ai_msg.classes(add="text-red-500")
                    return
                if result.code == "ok":
                    ai_msg.text = "✓ 连接成功"
                    ai_msg.classes(add="text-green-600")
                elif result.code == "http_error":
                    ai_msg.text = f"连接失败（HTTP {result.http_status}）"
                    ai_msg.classes(add="text-red-500")
                elif result.code == "timeout":
                    ai_msg.text = "连接失败（请求超时）"
                    ai_msg.classes(add="text-red-500")
                else:
                    ai_msg.text = "连接失败（网络请求异常）"
                    ai_msg.classes(add="text-red-500")

            with ui.row().classes("mt-3 gap-3"):
                ui.button("保存", on_click=save_ai_key_handler).classes(
                    "bg-blue-600 text-white"
                )
                ui.button("验证连接", on_click=verify_connection).classes(
                    "bg-gray-100 text-gray-700"
                )

        # ══════════════════════════════════════════════════════════════════════
        # 区块四：AI 接口配置 — 视觉模型
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            ui.label("AI 接口配置 — 视觉模型").classes(
                "text-lg font-bold text-green-700 mb-2"
            )
            ui.label(
                "用于游戏观察图片分析（key_type=vision），与文本模型独立配置。"
            ).classes("text-xs text-gray-500 mb-3")

            vision_url_input = ui.input(
                label="视觉模型 API 地址",
                placeholder="如：https://api.openai.com/v1",
            ).classes("w-full")

            vision_model_input = ui.input(
                label="视觉模型名称",
                placeholder="如：gpt-4o / qwen-vl-plus",
            ).classes("w-full mt-2")

            vision_key_input = ui.input(
                label="视觉模型 API Key",
                placeholder="输入 API Key（保存后脱敏显示）",
                password=True,
                password_toggle_button=True,
            ).classes("w-full mt-2")

            vision_msg = ui.label("").classes("text-sm mt-1")
            _vision_masked: list[str] = [""]

            async def save_vision_key_handler() -> None:
                current = await require_live_session()
                if current is None:
                    return
                vision_msg.classes(remove="text-green-600 text-red-500")
                url = vision_url_input.value.strip()
                model = vision_model_input.value.strip()
                key_val = vision_key_input.value.strip()

                if not url:
                    vision_msg.text = "请输入视觉模型 API 地址"
                    vision_msg.classes(add="text-red-500")
                    return
                if not model:
                    vision_msg.text = "请输入视觉模型名称"
                    vision_msg.classes(add="text-red-500")
                    return

                key_changed = key_val and key_val != _vision_masked[0]
                if key_changed:
                    plain_key = key_val
                else:
                    async with AsyncSessionLocal() as session:
                        existing = await get_active_ai_key(
                            session,
                            current.tenant_id,
                            current.user_id,
                            key_type="vision",
                        )
                    if existing is None:
                        if not key_val:
                            vision_msg.text = "请输入视觉模型 API Key"
                            vision_msg.classes(add="text-red-500")
                            return
                        plain_key = key_val
                    else:
                        try:
                            plain_key = get_decrypted_key(existing)
                        except CryptoError:
                            vision_msg.text = "已有 Key 解密失败，请重新输入"
                            vision_msg.classes(add="text-red-500")
                            return

                current = await require_live_session()
                if current is None:
                    return
                async with AsyncSessionLocal() as session:
                    await save_ai_key(
                        session,
                        current.tenant_id,
                        current.user_id,
                        url,
                        plain_key,
                        model,
                        key_type="vision",
                    )

                masked = _mask_api_key(plain_key)
                _vision_masked[0] = masked
                vision_key_input.value = masked
                vision_msg.text = "视觉模型配置已保存"
                vision_msg.classes(add="text-green-600")

            async def verify_vision_connection() -> None:
                current = await require_live_session()
                if current is None:
                    return
                vision_msg.classes(remove="text-green-600 text-red-500")
                vision_msg.text = "连接测试中……"

                async with AsyncSessionLocal() as session:
                    result = await verify_saved_ai_connection(
                        session,
                        tenant_id=current.tenant_id,
                        user_id=current.user_id,
                        key_type="vision",
                    )
                if await require_live_session() is None:
                    return

                if result.code == "not_configured":
                    vision_msg.text = "请先保存视觉模型配置"
                    vision_msg.classes(add="text-red-500")
                    return
                if result.code == "key_decryption_failed":
                    vision_msg.text = "Key 解密失败，请重新保存"
                    vision_msg.classes(add="text-red-500")
                    return
                if result.code == "ok":
                    vision_msg.text = "✓ 视觉模型连接成功"
                    vision_msg.classes(add="text-green-600")
                elif result.code == "http_error":
                    vision_msg.text = f"连接失败（HTTP {result.http_status}）"
                    vision_msg.classes(add="text-red-500")
                elif result.code == "timeout":
                    vision_msg.text = "连接失败（请求超时）"
                    vision_msg.classes(add="text-red-500")
                else:
                    vision_msg.text = "连接失败（网络请求异常）"
                    vision_msg.classes(add="text-red-500")

            with ui.row().classes("mt-3 gap-3"):
                ui.button("保存视觉模型", on_click=save_vision_key_handler).classes(
                    "bg-green-600 text-white"
                )
                ui.button("验证连接", on_click=verify_vision_connection).classes(
                    "bg-gray-100 text-gray-700"
                )

    # ── 加载已有配置并回填 ──────────────────────────────────────────────────────
    async with AsyncSessionLocal() as session:
        semester = await get_active_semester(session, tenant_id, user_id)
        class_cfg = await get_class_config(session, tenant_id, user_id)
        ai_key_record = await get_active_ai_key(
            session, tenant_id, user_id, key_type="text"
        )
        ai_vision_record = await get_active_ai_key(
            session, tenant_id, user_id, key_type="vision"
        )

    if await require_live_session() is None:
        return

    if semester:
        semester_name_input.value = semester.semester_name
        start_date_input.value = semester.start_date.isoformat()
        end_date_input.value = semester.end_date.isoformat()

    if class_cfg:
        grade_select.value = class_cfg.grade
        class_name_input.value = class_cfg.class_name
        teacher_name_input.value = class_cfg.teacher_name or ""
        indoor_areas_input.value = class_cfg.indoor_areas or ""
        outdoor_content_input.value = class_cfg.outdoor_content or ""

    if ai_key_record:
        ai_url_input.value = ai_key_record.api_base_url
        ai_model_input.value = ai_key_record.model_name
        try:
            plain = get_decrypted_key(ai_key_record)
            masked = _mask_api_key(plain)
            _current_masked[0] = masked
            ai_key_input.value = masked
        except CryptoError:
            ai_key_input.value = ""
            ai_msg.text = "Key 解密失败，请重新配置"
            ai_msg.classes(add="text-red-500")

    if ai_vision_record:
        vision_url_input.value = ai_vision_record.api_base_url
        vision_model_input.value = ai_vision_record.model_name
        try:
            plain_v = get_decrypted_key(ai_vision_record)
            masked_v = _mask_api_key(plain_v)
            _vision_masked[0] = masked_v
            vision_key_input.value = masked_v
        except CryptoError:
            vision_key_input.value = ""
            vision_msg.text = "视觉模型 Key 解密失败，请重新配置"
            vision_msg.classes(add="text-red-500")

        # ══════════════════════════════════════════════════════════════════════
        # 区块五：数据库配置
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            ui.label("数据库配置").classes("text-lg font-bold text-blue-700 mb-2")
            ui.label(
                "默认使用 SQLite（无需额外配置）。切换到 MySQL 需填写连接信息。"
            ).classes("text-sm text-gray-500 mb-2")

            current_env = read_dot_env()
            current_db_url = current_env.get("DATABASE_URL", "")
            is_mysql = current_db_url.startswith("mysql")

            # 解析已有 MySQL URL 的各字段
            _parsed_host = ""
            _parsed_port = "3306"
            _parsed_user = ""
            _parsed_password = ""
            _parsed_dbname = ""
            if is_mysql and "://" in current_db_url:
                try:
                    from urllib.parse import urlparse

                    parsed = urlparse(current_db_url.replace("mysql+aiomysql", "mysql"))
                    _parsed_host = parsed.hostname or ""
                    _parsed_port = str(parsed.port or 3306)
                    _parsed_user = parsed.username or ""
                    _parsed_password = parsed.password or ""
                    _parsed_dbname = parsed.path.lstrip("/") if parsed.path else ""
                except Exception:
                    pass

            db_mode_radio = ui.radio(
                {"sqlite": "📦 SQLite（内嵌，推荐）", "mysql": "🗄️ MySQL（外部数据库）"},
                value="mysql" if is_mysql else "sqlite",
            ).classes("mb-2")

            # MySQL 独立字段容器
            mysql_fields = ui.column().classes("w-full gap-2")
            mysql_fields.bind_visibility_from(
                db_mode_radio, "value", backward=lambda v: v == "mysql"
            )
            with mysql_fields:
                db_host_input = ui.input(
                    label="服务器地址", value=_parsed_host, placeholder="localhost"
                ).classes("w-full")
                db_port_input = ui.input(
                    label="端口", value=_parsed_port, placeholder="3306"
                ).classes("w-full")
                db_user_input = ui.input(
                    label="用户名", value=_parsed_user, placeholder="root"
                ).classes("w-full")
                db_pass_input = ui.input(
                    label="密码",
                    value=_parsed_password,
                    password=True,
                    password_toggle_button=True,
                ).classes("w-full")
                db_name_input = ui.input(
                    label="数据库名", value=_parsed_dbname, placeholder="kindergarten"
                ).classes("w-full")

            ui.label("⚠️ 切换数据库后原有数据不会自动迁移，请提前备份。").classes(
                "text-xs text-amber-600 mt-1"
            )

            db_status = ui.label("").classes("text-sm mt-2")

            async def _save_db_config() -> None:
                if await require_live_session() is None:
                    return
                db_status.set_text("")
                if db_mode_radio.value == "sqlite":
                    new_url = ""
                else:
                    host = db_host_input.value.strip()
                    port = db_port_input.value.strip() or "3306"
                    user_val = db_user_input.value.strip()
                    pwd_val = db_pass_input.value
                    dbname = db_name_input.value.strip()

                    if not host or not user_val or not dbname:
                        db_status.set_text("❌ 服务器地址、用户名和数据库名为必填项")
                        db_status.classes(replace="text-red-600 text-sm mt-2")
                        return

                    new_url = (
                        f"mysql+aiomysql://{user_val}:{pwd_val}@{host}:{port}/{dbname}"
                    )

                try:
                    write_dot_env({"DATABASE_URL": new_url})
                    db_status.set_text("✅ 数据库配置已保存，需重启应用生效")
                    db_status.classes(replace="text-green-600 text-sm mt-2")
                except RuntimeError as exc:
                    db_status.set_text(f"❌ 保存失败：{exc}")
                    db_status.classes(replace="text-red-600 text-sm mt-2")

            ui.button("保存数据库配置", on_click=_save_db_config).classes(
                "mt-2 bg-blue-600 text-white"
            )

        # ══════════════════════════════════════════════════════════════════════
        # 区块六：端口配置
        # ══════════════════════════════════════════════════════════════════════
        with ui.card().classes("w-full"):
            ui.label("应用端口").classes("text-lg font-bold text-blue-700 mb-2")

            current_port = int(current_env.get("PORT", str(app_settings.PORT)))
            port_input = ui.number(
                label="监听端口",
                value=current_port,
                min=1024,
                max=65535,
                format="%d",
            ).classes("w-full")

            port_status = ui.label("").classes("text-sm mt-2")

            async def _save_port() -> None:
                if await require_live_session() is None:
                    return
                port_status.set_text("")
                try:
                    new_port = int(port_input.value or app_settings.PORT)
                except (ValueError, TypeError):
                    port_status.set_text("❌ 端口号格式错误")
                    port_status.classes(replace="text-red-600 text-sm mt-2")
                    return

                if new_port < 1024 or new_port > 65535:
                    port_status.set_text("❌ 端口范围 1024~65535")
                    port_status.classes(replace="text-red-600 text-sm mt-2")
                    return

                try:
                    write_dot_env({"PORT": str(new_port)})
                    port_status.set_text("✅ 端口配置已保存，需重启应用生效")
                    port_status.classes(replace="text-green-600 text-sm mt-2")
                except RuntimeError as exc:
                    port_status.set_text(f"❌ 保存失败：{exc}")
                    port_status.classes(replace="text-red-600 text-sm mt-2")

            ui.button("保存端口配置", on_click=_save_port).classes(
                "mt-2 bg-blue-600 text-white"
            )
