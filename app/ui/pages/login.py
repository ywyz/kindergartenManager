"""可信 UI 会话登录页（路由：/login）。"""

from nicegui import app, ui

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AuthError
from app.core.logging import get_logger
from app.repository.user_repository import has_active_sys_admin
from app.service.auth_service import login
from app.ui.auth_context import TrustedUiSession, resolve_current_ui_session

logger = get_logger(__name__)


async def _load_login_page_state(
    token: str | None,
) -> tuple[TrustedUiSession | None, bool, bool]:
    """返回 current/admin-ready/database-available；DB 失败时清除旧 token。"""
    try:
        async with AsyncSessionLocal() as session:
            current = await resolve_current_ui_session(session, token)
            admin_ready = await has_active_sys_admin(
                session,
                tenant_id=settings.BOOTSTRAP_ADMIN_TENANT_ID,
            )
    except Exception as exc:
        logger.error(
            "login_page_session_validation_failed error_type=%s",
            type(exc).__name__,
        )
        if app.storage.user.get("token") == token:
            app.storage.user.clear()
        return None, False, False
    return current, admin_ready, True


@ui.page("/login")
async def login_page() -> None:
    token = app.storage.user.get("token")
    current, admin_ready, database_available = await _load_login_page_state(token)
    if current is not None:
        ui.navigate.to("/home")
        return
    if token and app.storage.user.get("token") == token:
        app.storage.user.clear()

    with ui.column().classes("w-full max-w-md mx-auto mt-16 p-8 gap-4"):
        ui.label("幼儿园教学管理系统").classes(
            "text-2xl font-bold text-blue-700 text-center"
        )
        ui.label("请登录后继续").classes("text-sm text-gray-500 text-center")
        if not database_available:
            ui.label("数据库暂不可用，登录已失败关闭，请稍后重试。").classes(
                "text-red-600 text-sm text-center"
            )
        elif not admin_ready:
            ui.label(
                "尚无可用管理员；请在应用主机上显式运行管理员初始化命令。"
            ).classes("text-orange-600 text-sm text-center")

        error_label = ui.label("").classes("text-red-600 text-sm hidden")
        username_input = ui.input(label="用户名").classes("w-full")
        password_input = ui.input(
            label="密码",
            password=True,
            password_toggle_button=True,
        ).classes("w-full")
        login_button = ui.button("登录", icon="login").classes(
            "w-full bg-blue-600 text-white"
        )
        login_generation = 0
        active_generation: int | None = None

        def login_attempt_is_current(generation: int, token: object) -> bool:
            return (
                active_generation == generation
                and app.storage.user.get("token") == token
            )

        async def do_login(
            username: str,
            password: str,
            generation: int,
            expected_token: object,
        ) -> None:
            nonlocal active_generation
            owned_token = expected_token
            loading_started = False
            try:
                if not login_attempt_is_current(generation, owned_token):
                    return
                error_label.classes(add="hidden")
                if not username or not password:
                    error_label.set_text("请输入用户名和密码")
                    error_label.classes(remove="hidden")
                    return

                login_button.props("loading=true")
                loading_started = True
                async with AsyncSessionLocal() as session:
                    token_value = await login(
                        session,
                        tenant_id=settings.BOOTSTRAP_ADMIN_TENANT_ID,
                        username=username,
                        password=password,
                    )
                if not login_attempt_is_current(generation, owned_token):
                    return
                app.storage.user.clear()
                app.storage.user["token"] = token_value
                owned_token = token_value
                ui.navigate.to("/home")
            except AuthError:
                if not login_attempt_is_current(generation, owned_token):
                    return
                error_label.set_text(
                    "用户名或密码错误、账号不可用；旧单用户安装请先运行管理员初始化命令重设密码"
                )
                error_label.classes(remove="hidden")
            except Exception as exc:
                if not login_attempt_is_current(generation, owned_token):
                    return
                logger.warning(
                    "UI 登录失败",
                    extra={"error_type": type(exc).__name__},
                )
                error_label.set_text("登录失败，请稍后重试")
                error_label.classes(remove="hidden")
            finally:
                if active_generation == generation:
                    if loading_started and app.storage.user.get("token") == owned_token:
                        login_button.props(remove="loading")
                    active_generation = None

        def trigger_login() -> object | None:
            nonlocal active_generation, login_generation
            if active_generation is not None:
                return None
            username = str(username_input.value or "").strip()
            password = str(password_input.value or "")
            expected_token = app.storage.user.get("token")
            login_generation += 1
            active_generation = login_generation
            return do_login(
                username,
                password,
                login_generation,
                expected_token,
            )

        login_button.on("click", trigger_login)
        password_input.on("keydown.enter", trigger_login)
