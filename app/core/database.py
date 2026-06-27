from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.paths import app_data_dir


def _resolve_database_url() -> str:
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    # 未配置 DATABASE_URL：降级使用内嵌 SQLite（写入用户可写数据目录）
    db_path = app_data_dir() / "kindergarten.db"
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


def _build_engine():
    url = _resolve_database_url()
    if url.startswith("sqlite"):
        return create_async_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_async_engine(
        url,
        pool_pre_ping=False,   # 关闭：避免每次取连接前额外发 SELECT 1（对远程 DB 影响显著）
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,     # 30 分钟回收连接，防止服务端主动断开后复用报错
    )


engine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
