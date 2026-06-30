"""应用启动引导。

dev3.4 恢复登录系统后，不再自动创建默认管理员账号。
首次管理员应通过安装器初始化、CLI 或 `/setup-admin` 页面创建。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


async def ensure_default_user(session: AsyncSession) -> None:
    """兼容旧测试/调用点的空操作。"""
    return None


async def run_bootstrap() -> None:
    """应用启动时调用：登录模式下无需自动创建用户。"""
    logger.info("登录模式已启用，跳过默认管理员自动创建")
