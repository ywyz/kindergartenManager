"""Alembic 配置工具；迁移只允许由显式迁移任务调用。

支持三种运行模式：
- 开发模式（python -m app.main）：直接运行，alembic.ini 在项目根目录
- PyInstaller 打包模式：alembic.ini 和 alembic/ 目录随二进制打包进 _MEIPASS
- Docker 模式：与开发模式相同
"""

import hashlib
import logging
import os
import sys

from app.core.paths import app_data_dir

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


def build_sync_url(database_url: str | None) -> str:
    """将异步驱动 URL 转换为 Alembic 所需的同步驱动 URL。

    迁移（alembic/env.py）与应用运行时（app/core/database.py）必须经由本函数解析到
    同一个 SQLite 文件，否则打包模式下会出现“迁移建表在 A 库、应用读 B 库”导致
    no such table。空 URL 时统一落到 ``app_data_dir()/kindergarten.db``。
    """
    if not database_url:
        db_path = app_data_dir() / "kindergarten.db"
        return f"sqlite:///{db_path.as_posix()}"
    if "+aiosqlite" in database_url:
        return database_url.replace("+aiosqlite", "")
    if "+aiomysql" in database_url:
        return database_url.replace("+aiomysql", "+pymysql")
    return database_url


def database_identity_sha256(database_url: str | None) -> str:
    """Return the canonical credential-free identity for a database target."""
    from sqlalchemy.engine import URL, make_url

    url = make_url(build_sync_url(database_url))
    if url.get_backend_name() == "sqlite" and url.database:
        database = os.path.abspath(url.database)
        normalized_url = URL.create(drivername=url.drivername, database=database)
    else:
        normalized_url = URL.create(
            drivername=url.drivername,
            host=url.host.casefold().rstrip(".") if url.host else None,
            port=url.port,
            database=url.database,
        )
    normalized = normalized_url.render_as_string(hide_password=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def configured_database_identity_sha256() -> str:
    """Return the canonical identity for the configured database target."""
    from app.core.config import settings

    return database_identity_sha256(settings.DATABASE_URL)


def read_configured_database_revision() -> str:
    """Read the actual configured database's current Alembic revision."""
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    from app.core.config import settings

    engine = create_engine(build_sync_url(settings.DATABASE_URL))
    try:
        with engine.connect() as connection:
            revision = MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()
    return revision or "base"


def get_migration_head() -> str:
    """Return the sole Alembic head shipped with this code/image."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(_get_alembic_ini_path())
    config.set_main_option("script_location", _get_alembic_script_location())
    heads = ScriptDirectory.from_config(config).get_heads()
    if len(heads) != 1:
        raise RuntimeError("Expected exactly one Alembic head")
    return heads[0]


def run_migrations(*, log_failure_detail: bool = True) -> None:
    """为显式迁移任务执行 alembic upgrade head。

    桌面、开发与服务器模式统一 fail-closed：迁移失败时重新抛出，防止应用在未知
    或过期 schema 上继续接受业务操作。默认记录异常；已经提供脱敏错误边界的调用方
    可关闭详细日志，避免 CLI 输出连接串或 SQL 参数。
    """
    try:
        from alembic import command
        from alembic.config import Config

        from app.core.config import settings

        ini_path = _get_alembic_ini_path()
        script_location = _get_alembic_script_location()
        sync_url = build_sync_url(settings.DATABASE_URL)

        alembic_cfg = Config(ini_path)
        alembic_cfg.set_main_option("script_location", script_location)
        # configparser 插值规则：% 须转义为 %%，否则 URL 中的 %40 等编码字符会引发 ValueError
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url.replace("%", "%%"))

        logger.info(
            "正在执行数据库迁移...",
            extra={"db_url": sync_url.split("@")[-1] if "@" in sync_url else sync_url},
        )
        command.upgrade(alembic_cfg, "head")
        logger.info("数据库迁移完成")
    except Exception:
        if log_failure_detail:
            logger.exception("数据库迁移失败，显式迁移任务已中止")
        raise
