"""AI 接口配置页面（路由 /setup）。

简化后的单页面：仅配置 AI 文本模型接口信息（Base URL、API Key、模型名称）。
系统默认使用 SQLite，数据库配置已移至 /settings 页面。
"""

import httpx
from nicegui import ui

from app.core.database import AsyncSessionLocal
from app.core.user_context import get_current_user
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key, save_ai_key


def _mask_api_key(plain: str) -> str:
    """将明文 API Key 脱敏。"""
    if len(plain) >= 8:
        return "sk-****" + plain[-4:]
    return "sk-****"


@ui.page("/setup")
async def setup_page() -> None:
    """AI 接口配置页面。"""
    user = get_current_user()
    tenant_id: int = user["tenant_id"]
    user_id: int = int(user["sub"])

    # 读取已有 AI 配置
    existing_url = ""
    existing_model = ""
    existing_key_display = ""
    async with AsyncSessionLocal() as session:
        ai_key = await get_active_ai_key(session, tenant_id, user_id, key_type="text")
        if ai_key:
            existing_url = ai_key.api_base_url or ""
            existing_model = ai_key.model_name or ""
            try:
                plain_key = get_decrypted_key(ai_key)
                existing_key_display = _mask_api_key(plain_key)
            except Exception:
                existing_key_display = "sk-****（解密失败）"

    with ui.column().classes("w-full max-w-lg mx-auto px-4 py-8 gap-4"):
        ui.label("🤖 AI 接口配置").classes("text-2xl font-bold text-blue-700")
        ui.label(
            "配置 AI 接口后可使用教案拆分、年龄适配等 AI 功能。"
        ).classes("text-sm text-gray-500 mb-2")

        with ui.card().classes("w-full"):
            api_url_in = ui.input(
                label="API Base URL",
                placeholder="https://api.openai.com/v1",
                value=existing_url,
            ).classes("w-full")

            api_key_in = ui.input(
                label="API Key",
                placeholder=existing_key_display or "sk-...",
                password=True,
                password_toggle_button=True,
            ).classes("w-full")
            if existing_key_display:
                ui.label(f"当前：{existing_key_display}").classes(
                    "text-xs text-gray-400 -mt-1"
                )

            model_in = ui.input(
                label="模型名称",
                value=existing_model or "gpt-4o-mini",
                placeholder="如：gpt-4o-mini、deepseek-chat",
            ).classes("w-full")

            status_label = ui.label("").classes("text-sm mt-2")

            async def _test_connection() -> None:
                """测试 AI 接口连通性。"""
                url = api_url_in.value.strip().rstrip("/")
                key = api_key_in.value.strip()
                if not url:
                    status_label.set_text("❌ 请填写 API Base URL")
                    status_label.classes(replace="text-red-600 text-sm mt-2")
                    return
                if not key:
                    status_label.set_text("❌ 请填写 API Key")
                    status_label.classes(replace="text-red-600 text-sm mt-2")
                    return

                status_label.set_text("⏳ 正在测试连接...")
                status_label.classes(replace="text-gray-500 text-sm mt-2")
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        resp = await client.get(
                            f"{url}/models",
                            headers={"Authorization": f"Bearer {key}"},
                        )
                    if resp.status_code == 200:
                        status_label.set_text("✅ 连接成功")
                        status_label.classes(replace="text-green-600 text-sm mt-2")
                    else:
                        status_label.set_text(
                            f"⚠️ 接口返回 {resp.status_code}，请检查配置"
                        )
                        status_label.classes(replace="text-amber-600 text-sm mt-2")
                except Exception as exc:
                    status_label.set_text(f"❌ 连接失败：{exc}")
                    status_label.classes(replace="text-red-600 text-sm mt-2")

            async def _save_config() -> None:
                """保存 AI 配置。"""
                url = api_url_in.value.strip()
                key = api_key_in.value.strip()
                model = model_in.value.strip() or "gpt-4o-mini"

                if not url:
                    status_label.set_text("❌ API Base URL 不能为空")
                    status_label.classes(replace="text-red-600 text-sm mt-2")
                    return
                if not key and not existing_key_display:
                    status_label.set_text("❌ API Key 不能为空")
                    status_label.classes(replace="text-red-600 text-sm mt-2")
                    return

                try:
                    async with AsyncSessionLocal() as session:
                        # 如果用户未修改 key（留空），复用已有 key
                        if not key and existing_key_display:
                            ai_existing = await get_active_ai_key(
                                session, tenant_id, user_id, key_type="text"
                            )
                            if ai_existing:
                                plain_key = get_decrypted_key(ai_existing)
                            else:
                                status_label.set_text("❌ 无法获取已有 Key，请重新输入")
                                status_label.classes(
                                    replace="text-red-600 text-sm mt-2"
                                )
                                return
                        else:
                            plain_key = key

                        await save_ai_key(
                            session,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            api_base_url=url,
                            plain_api_key=plain_key,
                            model_name=model,
                            key_type="text",
                        )
                    status_label.set_text("✅ 配置已保存！")
                    status_label.classes(replace="text-green-600 text-sm mt-2")
                except Exception as exc:
                    status_label.set_text(f"❌ 保存失败：{exc}")
                    status_label.classes(replace="text-red-600 text-sm mt-2")

            with ui.row().classes("mt-3 gap-2 flex-wrap"):
                ui.button("测试连接", on_click=_test_connection).props("flat")
                ui.button("保存配置", on_click=_save_config, icon="save").classes(
                    "bg-blue-600 text-white"
                )

        with ui.row().classes("mt-4 justify-center"):
            ui.link("← 返回主页", "/home").classes("text-blue-600 text-sm")
            ui.label("·").classes("text-gray-300")
            ui.link("前往完整设置 →", "/settings").classes("text-blue-600 text-sm")

