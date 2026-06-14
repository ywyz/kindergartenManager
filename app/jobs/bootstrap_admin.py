"""系统管理员初始化脚本。

模式：
  --init           创建 sys_admin 账号（默认模式）
  --reset-password 重置 sys_admin 账号密码（需提供旧密码验证）

用法（环境变量方式）：
    BOOTSTRAP_ADMIN_ENABLED=true \
    BOOTSTRAP_ADMIN_PASSWORD='<strong-password>' \
    .venv/bin/python -m app.jobs.bootstrap_admin --init

用法（交互式，任一参数均可省略环境变量）：
    .venv/bin/python -m app.jobs.bootstrap_admin --init
    .venv/bin/python -m app.jobs.bootstrap_admin --reset-password
"""
import argparse
import asyncio
import getpass

from sqlalchemy.engine import make_url

from app.auth.password import hash_password, verify_password
from app.core.audit import log_audit
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.models.user import UserRole
from app.core.startup import run_startup_migrations
from app.repository.user_repository import create_user, get_user_by_username, update_password


async def bootstrap_admin(
    *,
    enabled: bool,
    tenant_id: int,
    username: str,
    password: str,
    allow_remote: bool,
    database_url: str,
) -> str:
    """初始化系统管理员账号，返回执行结果说明。"""
    if not enabled:
        return "skip: BOOTSTRAP_ADMIN_ENABLED=false"

    # 空串表示内嵌 SQLite，视为本地数据库
    db_host = make_url(database_url).host if database_url else None
    local_hosts = {None, "localhost", "127.0.0.1", "::1"}
    if (db_host not in local_hosts) and (not allow_remote):
        return "error: remote database blocked, set BOOTSTRAP_ADMIN_ALLOW_REMOTE=true to continue"

    normalized_username = username.strip()
    if not normalized_username:
        return "error: BOOTSTRAP_ADMIN_USERNAME 不能为空"
    if len(password) < 8:
        return "error: BOOTSTRAP_ADMIN_PASSWORD 至少 8 位"

    async with AsyncSessionLocal() as session:
        existing = await get_user_by_username(
            session,
            tenant_id=tenant_id,
            username=normalized_username,
        )
        if existing is not None:
            return f"skip: sys_admin already exists ({normalized_username})"

        user = await create_user(
            session,
            tenant_id=tenant_id,
            username=normalized_username,
            hashed_password=hash_password(password),
            role=UserRole.sys_admin,
        )

    log_audit(
        "bootstrap_admin",
        tenant_id=tenant_id,
        user_id=user.id,
        username=normalized_username,
    )
    return f"ok: created sys_admin {normalized_username} (id={user.id})"


async def reset_admin_password(
    *,
    tenant_id: int,
    username: str,
    old_password: str,
    new_password: str,
    allow_remote: bool,
    database_url: str,
) -> str:
    """重置 sys_admin 密码（需旧密码验证），返回执行结果说明。"""
    db_host = make_url(database_url).host if database_url else None
    local_hosts = {None, "localhost", "127.0.0.1", "::1"}
    if (db_host not in local_hosts) and (not allow_remote):
        return "error: remote database blocked, set BOOTSTRAP_ADMIN_ALLOW_REMOTE=true to continue"

    if len(new_password) < 8:
        return "error: 新密码至少 8 位"

    normalized_username = username.strip()
    async with AsyncSessionLocal() as session:
        user = await get_user_by_username(
            session, tenant_id=tenant_id, username=normalized_username
        )
        if user is None or user.role != UserRole.sys_admin:
            return f"error: 用户 {normalized_username!r} 不存在或非 sys_admin"
        if not verify_password(old_password, user.hashed_password):
            return "error: 旧密码错误"
        await update_password(
            session,
            tenant_id=tenant_id,
            user_id=user.id,
            new_hashed_password=hash_password(new_password),
        )

    log_audit(
        "bootstrap_reset_password",
        tenant_id=tenant_id,
        user_id=user.id,
        username=normalized_username,
    )
    return f"ok: password reset for sys_admin {normalized_username}"


def _prompt_str(prompt_text: str, default: str = "") -> str:
    """带默认值的交互式字符串提示。"""
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt_text}{suffix}: ").strip()
    return value or default


def _prompt_password(prompt_text: str) -> str:
    """安全密码提示（不回显）。"""
    return getpass.getpass(f"{prompt_text}: ")


async def _run_init() -> None:
    """--init 模式：创建 sys_admin 账号。"""
    print("\n[Step 1/3] 执行数据库迁移...")
    try:
        run_startup_migrations()
        print("[Step 1/3] ✅ 迁移完成")
    except Exception as exc:
        print(f"[Step 1/3] ⚠️  迁移失败（{exc}），继续尝试...")

    print("\n[Step 2/3] 配置管理员账号...")

    enabled = settings.BOOTSTRAP_ADMIN_ENABLED
    if not enabled:
        resp = input("BOOTSTRAP_ADMIN_ENABLED 未设置为 true，是否继续？[y/N] ").strip().lower()
        if resp != "y":
            print("已取消。")
            return
        enabled = True

    tenant_id = settings.BOOTSTRAP_ADMIN_TENANT_ID
    username = settings.BOOTSTRAP_ADMIN_USERNAME or _prompt_str("管理员用户名", "sysadmin")
    password = settings.BOOTSTRAP_ADMIN_PASSWORD or _prompt_password("管理员密码（至少8位）")
    allow_remote = settings.BOOTSTRAP_ADMIN_ALLOW_REMOTE

    print("\n[Step 3/3] 创建管理员账号...")
    message = await bootstrap_admin(
        enabled=enabled,
        tenant_id=tenant_id,
        username=username,
        password=password,
        allow_remote=allow_remote,
        database_url=settings.DATABASE_URL,
    )
    print(f"[Step 3/3] {message}")


async def _run_reset() -> None:
    """--reset-password 模式：重置 sys_admin 密码。"""
    print("\n[Step 1/2] 验证身份...")

    tenant_id = settings.BOOTSTRAP_ADMIN_TENANT_ID
    username = _prompt_str("管理员用户名")
    old_password = _prompt_password("旧密码")
    new_password = _prompt_password("新密码（至少8位）")
    new_password_confirm = _prompt_password("确认新密码")

    if new_password != new_password_confirm:
        print("❌ 两次密码不一致，已取消。")
        return

    print("\n[Step 2/2] 重置密码...")
    message = await reset_admin_password(
        tenant_id=tenant_id,
        username=username,
        old_password=old_password,
        new_password=new_password,
        allow_remote=settings.BOOTSTRAP_ADMIN_ALLOW_REMOTE,
        database_url=settings.DATABASE_URL,
    )
    print(f"[Step 2/2] {message}")


async def _main() -> None:
    parser = argparse.ArgumentParser(description="系统管理员初始化脚本")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--init", action="store_true", help="创建系统管理员账号（默认）")
    group.add_argument("--reset-password", action="store_true", help="重置系统管理员密码")
    args = parser.parse_args()

    if args.reset_password:
        await _run_reset()
    else:
        await _run_init()


if __name__ == "__main__":
    asyncio.run(_main())
