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

from app.auth.legacy import (
    reject_legacy_single_user_password,
    uses_legacy_single_user_password,
)
from app.auth.password import hash_password, verify_password
from app.core.audit import log_audit
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.models.user import UserRole
from app.core.startup import run_startup_migrations
from app.repository.user_repository import (
    create_user,
    get_user_by_username,
    list_users_by_tenant,
    update_password,
)


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
    try:
        reject_legacy_single_user_password(password)
    except ValueError:
        return "error: BOOTSTRAP_ADMIN_PASSWORD 不得使用旧单用户模式保留值"

    async with AsyncSessionLocal() as session:
        existing = await get_user_by_username(
            session,
            tenant_id=tenant_id,
            username=normalized_username,
        )
        legacy_admins = [
            candidate
            for candidate in await list_users_by_tenant(session, tenant_id=tenant_id)
            if candidate.role is UserRole.sys_admin
            and uses_legacy_single_user_password(candidate.hashed_password)
        ]
        if len(legacy_admins) > 1:
            return "error: multiple legacy sys_admin accounts require manual recovery"
        if len(legacy_admins) == 1:
            legacy_admin = legacy_admins[0]
            await update_password(
                session,
                tenant_id=tenant_id,
                user_id=legacy_admin.id,
                new_hashed_password=hash_password(password),
                is_active=True,
            )
            log_audit(
                "bootstrap_recover_single_user_admin",
                tenant_id=tenant_id,
                user_id=legacy_admin.id,
                username=legacy_admin.username,
            )
            return (
                "ok: recovered legacy sys_admin "
                f"{legacy_admin.username} (id={legacy_admin.id})"
            )
        if existing is not None:
            if existing.role is UserRole.sys_admin:
                return f"skip: sys_admin already exists ({normalized_username})"
            return (
                f"error: username already belongs to non-admin ({normalized_username})"
            )

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
    try:
        reject_legacy_single_user_password(new_password)
    except ValueError:
        return "error: 新密码不得使用旧单用户模式保留值"

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


async def _run_init() -> int:
    """--init 模式：创建 sys_admin 账号。"""
    print("\n[Step 1/3] 执行数据库迁移...")
    try:
        run_startup_migrations(log_failure_detail=False)
        print("[Step 1/3] ✅ 迁移完成")
    except Exception:
        # 数据库异常可能携带连接串或 SQL 参数，不跨 CLI 边界输出正文。
        print("[Step 1/3] ❌ 迁移失败，已停止管理员初始化")
        return 1

    print("\n[Step 2/3] 配置管理员账号...")

    enabled = settings.BOOTSTRAP_ADMIN_ENABLED
    if not enabled:
        resp = (
            input("BOOTSTRAP_ADMIN_ENABLED 未设置为 true，是否继续？[y/N] ")
            .strip()
            .lower()
        )
        if resp != "y":
            print("已取消。")
            return 2
        enabled = True

    tenant_id = settings.BOOTSTRAP_ADMIN_TENANT_ID
    username = settings.BOOTSTRAP_ADMIN_USERNAME or _prompt_str(
        "管理员用户名", "sysadmin"
    )
    password = settings.BOOTSTRAP_ADMIN_PASSWORD or _prompt_password(
        "管理员密码（至少8位）"
    )
    allow_remote = settings.BOOTSTRAP_ADMIN_ALLOW_REMOTE

    print("\n[Step 3/3] 创建管理员账号...")
    try:
        message = await bootstrap_admin(
            enabled=enabled,
            tenant_id=tenant_id,
            username=username,
            password=password,
            allow_remote=allow_remote,
            database_url=settings.DATABASE_URL,
        )
    except Exception:
        # SQLAlchemy 异常参数可能包含密码哈希；只输出固定失败文案。
        print("[Step 3/3] ❌ 创建失败：请检查数据库迁移与连接状态")
        return 1
    # 同 _run_reset：bootstrap_admin 接收明文密码参数，避免将其返回值直接内插
    # 日志，改为按状态前缀输出固定文案，规避 CodeQL 明文记录密码的误报。
    if message.startswith("ok"):
        print("[Step 3/3] ✅ 系统管理员账号已创建完成")
        return 0
    elif message.startswith("skip"):
        print("[Step 3/3] ⏭️  系统管理员账号已存在或未启用，已跳过")
        return 0
    else:
        print("[Step 3/3] ❌ 创建失败：请检查环境变量配置与数据库连接")
        return 1


async def _run_reset() -> int:
    """--reset-password 模式：重置 sys_admin 密码。"""
    print("\n[Step 1/2] 验证身份...")

    tenant_id = settings.BOOTSTRAP_ADMIN_TENANT_ID
    username = _prompt_str("管理员用户名")
    old_password = _prompt_password("旧密码")
    new_password = _prompt_password("新密码（至少8位）")
    new_password_confirm = _prompt_password("确认新密码")

    if new_password != new_password_confirm:
        print("❌ 两次密码不一致，已取消。")
        return 2

    print("\n[Step 2/2] 重置密码...")
    try:
        message = await reset_admin_password(
            tenant_id=tenant_id,
            username=username,
            old_password=old_password,
            new_password=new_password,
            allow_remote=settings.BOOTSTRAP_ADMIN_ALLOW_REMOTE,
            database_url=settings.DATABASE_URL,
        )
    except Exception:
        # 数据库异常可能携带连接串、哈希或 SQL 参数，只输出固定失败文案。
        print("[Step 2/2] ❌ 重置失败：请检查数据库迁移与连接状态")
        return 1
    # 不要把 reset_admin_password 的返回值直接写入控制台/日志：该函数接收明文
    # 密码参数，CodeQL(py/clear-text-logging) 会对异步函数做“参数→返回值”的保守
    # 污点传播，将返回值误判为可能含密码。改为按状态前缀输出固定文案（返回值本身
    # 仅含用户名等非敏感信息，绝不含密码）。
    if message.startswith("ok"):
        print("[Step 2/2] ✅ 密码已重置完成")
        return 0
    else:
        print(
            "[Step 2/2] ❌ 重置失败：请确认用户名存在且为系统管理员、"
            "旧密码正确、新密码不少于 8 位、且数据库可访问。"
        )
        return 1


async def _main() -> int:
    parser = argparse.ArgumentParser(description="系统管理员初始化脚本")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--init", action="store_true", help="创建系统管理员账号（默认）")
    group.add_argument(
        "--reset-password", action="store_true", help="重置系统管理员密码"
    )
    args = parser.parse_args()

    if args.reset_password:
        return await _run_reset()
    return await _run_init()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
