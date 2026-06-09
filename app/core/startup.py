"""应用启动模块：自动执行 Alembic 数据库迁移。

支持三种运行模式：
- 开发模式（python -m app.main）：直接运行，alembic.ini 在项目根目录
- PyInstaller 打包模式：alembic.ini 和 alembic/ 目录随二进制打包进 _MEIPASS
- Docker 模式：与开发模式相同
"""
import logging
import os
import sys

logger = logging.getLogger("app.startup")


def _get_alembic_ini_path() -> str:
    if getattr(sys, "frozen", False):
        # PyInstaller 打包模式：资源在 _MEIPASS 目录
        return os.path.join(sys._MEIPASS, "alembic.ini")
    return "alembic.ini"


def _get_alembic_script_location() -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "alembic")
    return "alembic"


def _build_sync_url(database_url: str | None) -> str:
    """将异步驱动 URL 转换为 Alembic 所需的同步驱动 URL。"""
    if database_url is None:
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            return f"sqlite:///{exe_dir}/kindergarten.db"
        return "sqlite:///./kindergarten.db"
    if "+aiosqlite" in database_url:
        return database_url.replace("+aiosqlite", "")
    if "+aiomysql" in database_url:
        return database_url.replace("+aiomysql", "+pymysql")
    return database_url


def run_startup_migrations() -> None:
    """在应用启动时自动执行 alembic upgrade head。

    迁移失败时记录错误日志但不阻断启动，允许应用以降级模式运行（
    例如数据库暂时不可达时仍能加载页面并展示友好提示）。
    """
    try:
        from alembic import command
        from alembic.config import Config

        from app.core.config import settings

        ini_path = _get_alembic_ini_path()
        script_location = _get_alembic_script_location()
        sync_url = _build_sync_url(settings.DATABASE_URL)

        alembic_cfg = Config(ini_path)
        alembic_cfg.set_main_option("script_location", script_location)
        # configparser 插值规则：% 须转义为 %%，否则 URL 中的 %40 等编码字符会引发 ValueError
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url.replace("%", "%%"))

        logger.info("正在执行数据库迁移...", extra={"db_url": sync_url.split("@")[-1] if "@" in sync_url else sync_url})
        command.upgrade(alembic_cfg, "head")
        logger.info("数据库迁移完成")
    except Exception:
        logger.exception("数据库迁移失败，应用将继续启动（数据库功能可能不可用）")
