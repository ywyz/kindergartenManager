"""系统管理员初始化脚本。

用法：
    BOOTSTRAP_ADMIN_ENABLED=true \
    BOOTSTRAP_ADMIN_PASSWORD='<strong-password>' \
    .venv/bin/python -m app.jobs.bootstrap_admin
"""
import asyncio
from sqlalchemy.engine import make_url

from app.auth.password import hash_password
from app.core.audit import log_audit
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.models.user import UserRole
from app.repository.user_repository import create_user, get_user_by_username


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

    db_host = make_url(database_url).host
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


async def _main() -> None:
    message = await bootstrap_admin(
        enabled=settings.BOOTSTRAP_ADMIN_ENABLED,
        tenant_id=settings.BOOTSTRAP_ADMIN_TENANT_ID,
        username=settings.BOOTSTRAP_ADMIN_USERNAME,
        password=settings.BOOTSTRAP_ADMIN_PASSWORD,
        allow_remote=settings.BOOTSTRAP_ADMIN_ALLOW_REMOTE,
        database_url=settings.DATABASE_URL,
    )
    print(message)


if __name__ == "__main__":
    asyncio.run(_main())
