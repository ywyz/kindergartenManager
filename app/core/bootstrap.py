"""认证模式启动钩子。

恢复可信 UI 登录后，应用不得再自动创建带固定密码的管理员。首次安装或旧单用户
升级必须显式运行 ``python -m app.jobs.bootstrap_admin --init``。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


async def ensure_default_user(session: AsyncSession) -> None:
    """保留旧调用点的无副作用兼容 seam。"""
    del session


async def run_bootstrap() -> None:
    """登录模式下不隐式创建或改写任何用户凭据。"""
    logger.info("可信 UI 登录已启用，跳过固定管理员自动创建")
