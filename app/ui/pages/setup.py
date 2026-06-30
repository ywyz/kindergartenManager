"""个人 AI 接口配置页面（路由 /setup）。"""

import httpx
from nicegui import ui

from app.core.database import AsyncSessionLocal
from app.core.exceptions import CryptoError
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key, save_ai_key
from app.ui.auth_context import get_current_user_or_redirect
from app.ui.components.app_shell import render_shell
from app.ui.error_messages import format_user_error


def _mask_api_key(plain: str) -> str:
    """将明文 API Key 脱敏。"""
    if len(plain) >= 8:
        return "sk-****" + plain[-4:]
    return "sk-****"


async def _get_plain_key_for_save(
    *,
    tenant_id: int,
    user_id: int,
    key_type: str,
    typed_key: str,
    current_masked: str,
) -> str | None:
    """根据输入框内容解析要保存/验证的明文 Key。"""
    if typed_key and typed_key != current_masked:
        return typed_key
    async with AsyncSessionLocal() as session:
        existing = await get_active_ai_key(session, tenant_id, user_id, key_type=key_type)
    if existing is None:
        return None
    return get_decrypted_key(existing)


@ui.page("/setup")
async def setup_page() -> None:
    """当前登录用户的文本模型与视觉模型配置。"""
    user = await get_current_user_or_redirect()
    if not user:
        return
    tenant_id: int = user["tenant_id"]
    user_id: int = int(user["sub"])

    await render_shell(user, active="setup")

    async with AsyncSessionLocal() as session:
        text_record = await get_active_ai_key(session, tenant_id, user_id, key_type="text")
        vision_record = await get_active_ai_key(session, tenant_id, user_id, key_type="vision")

    def _existing(record) -> tuple[str, str, str]:
        if record is None:
            return "", "", ""
        try:
            return record.api_base_url or "", record.model_name or "", _mask_api_key(get_decrypted_key(record))
        except CryptoError:
            return record.api_base_url or "", record.model_name or "", ""

    text_url, text_model, text_mask = _existing(text_record)
    vision_url, vision_model, vision_mask = _existing(vision_record)

    with ui.column().classes("w-full max-w-2xl mx-auto px-4 py-8 gap-4"):
        ui.label("个人 AI 接口配置").classes("text-2xl font-bold text-blue-700")
        ui.label("文本模型和视觉模型按当前登录用户独立保存。").classes(
            "text-sm text-gray-500"
        )

        def render_key_card(
            *,
            key_type: str,
            title: str,
            description: str,
            existing_url: str,
            existing_model: str,
            existing_mask: str,
            default_model: str,
            button_class: str,
        ) -> None:
            current_masked: list[str] = [existing_mask]
            with ui.card().classes("w-full"):
                ui.label(title).classes("text-lg font-bold text-blue-700 mb-1")
                ui.label(description).classes("text-xs text-gray-500 mb-3")
                api_url_in = ui.input(
                    label="API Base URL",
                    placeholder="https://api.openai.com/v1",
                    value=existing_url,
                ).classes("w-full")
                model_in = ui.input(
                    label="模型名称",
                    value=existing_model or default_model,
                    placeholder=default_model,
                ).classes("w-full")
                key_in = ui.input(
                    label="API Key",
                    value=existing_mask,
                    placeholder="sk-...",
                    password=True,
                    password_toggle_button=True,
                ).classes("w-full")
                status_label = ui.label("").classes("text-sm mt-1")

                async def _save_config() -> None:
                    status_label.set_text("")
                    url = api_url_in.value.strip()
                    model = model_in.value.strip()
                    typed_key = key_in.value.strip()
                    if not url:
                        status_label.set_text("请输入 API Base URL")
                        status_label.classes(replace="text-red-600 text-sm mt-1")
                        return
                    if not model:
                        status_label.set_text("请输入模型名称")
                        status_label.classes(replace="text-red-600 text-sm mt-1")
                        return
                    try:
                        plain_key = await _get_plain_key_for_save(
                            tenant_id=tenant_id,
                            user_id=user_id,
                            key_type=key_type,
                            typed_key=typed_key,
                            current_masked=current_masked[0],
                        )
                    except CryptoError as exc:
                        status_label.set_text(format_user_error(exc))
                        status_label.classes(replace="text-red-600 text-sm mt-1")
                        return
                    if not plain_key:
                        status_label.set_text("请输入 API Key")
                        status_label.classes(replace="text-red-600 text-sm mt-1")
                        return

                    async with AsyncSessionLocal() as session:
                        await save_ai_key(
                            session,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            api_base_url=url,
                            plain_api_key=plain_key,
                            model_name=model,
                            key_type=key_type,
                        )
                    current_masked[0] = _mask_api_key(plain_key)
                    key_in.value = current_masked[0]
                    status_label.set_text("配置已保存")
                    status_label.classes(replace="text-green-600 text-sm mt-1")

                async def _test_connection() -> None:
                    status_label.set_text("连接测试中...")
                    status_label.classes(replace="text-gray-500 text-sm mt-1")
                    url = api_url_in.value.strip().rstrip("/")
                    try:
                        plain_key = await _get_plain_key_for_save(
                            tenant_id=tenant_id,
                            user_id=user_id,
                            key_type=key_type,
                            typed_key=key_in.value.strip(),
                            current_masked=current_masked[0],
                        )
                    except CryptoError as exc:
                        status_label.set_text(format_user_error(exc))
                        status_label.classes(replace="text-red-600 text-sm mt-1")
                        return
                    if not url or not plain_key:
                        status_label.set_text("请先填写并保存完整配置")
                        status_label.classes(replace="text-red-600 text-sm mt-1")
                        return
                    try:
                        async with httpx.AsyncClient(timeout=10) as client:
                            resp = await client.get(
                                f"{url}/models",
                                headers={"Authorization": f"Bearer {plain_key}"},
                            )
                        if resp.is_success:
                            status_label.set_text("连接成功")
                            status_label.classes(replace="text-green-600 text-sm mt-1")
                        else:
                            status_label.set_text(f"接口返回 HTTP {resp.status_code}，请检查 Key、地址和模型")
                            status_label.classes(replace="text-red-600 text-sm mt-1")
                    except httpx.TimeoutException:
                        status_label.set_text("连接超时，请检查网络和 API 地址")
                        status_label.classes(replace="text-red-600 text-sm mt-1")
                    except Exception as exc:
                        status_label.set_text(f"连接失败：{type(exc).__name__}")
                        status_label.classes(replace="text-red-600 text-sm mt-1")

                with ui.row().classes("mt-3 gap-2 flex-wrap"):
                    ui.button("测试连接", on_click=_test_connection).props("flat")
                    ui.button("保存配置", on_click=_save_config, icon="save").classes(button_class)

        render_key_card(
            key_type="text",
            title="文本模型",
            description="用于教案拆分、年龄适配、提示词测试和文本生成。",
            existing_url=text_url,
            existing_model=text_model,
            existing_mask=text_mask,
            default_model="gpt-4o-mini",
            button_class="bg-blue-600 text-white",
        )
        render_key_card(
            key_type="vision",
            title="视觉模型",
            description="用于游戏观察、一对一倾听等图片理解任务。",
            existing_url=vision_url,
            existing_model=vision_model,
            existing_mask=vision_mask,
            default_model="gpt-4o",
            button_class="bg-green-600 text-white",
        )
