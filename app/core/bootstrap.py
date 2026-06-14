"""应用启动引导：确保默认用户存在。

单用户模式下，系统启动时自动在 user 表中创建默认管理员账号。
如果已存在则跳过（幂等）。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.core.models.user import User, UserRole

logger = get_logger(__name__)

_DEFAULT_TENANT_ID = 1
_DEFAULT_USERNAME = "admin"
_DEFAULT_DISPLAY_NAME = "管理员"


async def ensure_default_user(session: AsyncSession) -> None:
    """确保默认用户存在，不存在则创建。已存在则跳过。"""
    stmt = select(User).where(
        User.tenant_id == _DEFAULT_TENANT_ID,
        User.username == _DEFAULT_USERNAME,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return

    from app.auth.password import hash_password

    user = User(
        tenant_id=_DEFAULT_TENANT_ID,
        username=_DEFAULT_USERNAME,
        hashed_password=hash_password("not-used-single-user-mode"),
        role=UserRole.sys_admin,
        is_active=True,
        display_name=_DEFAULT_DISPLAY_NAME,
    )
    session.add(user)
    await session.commit()
    logger.info("已创建默认管理员用户", extra={"username": _DEFAULT_USERNAME})


async def run_bootstrap() -> None:
    """应用启动时调用：确保默认用户已就绪。"""
    try:
        async with AsyncSessionLocal() as session:
            await ensure_default_user(session)
    except Exception as exc:
        logger.warning(
            "默认用户引导失败（首次启动时数据库可能尚未就绪）",
            extra={"error": str(exc)},
        )
