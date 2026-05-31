"""公共测试 fixture。

提供基于 SQLite 内存库的异步 session，用于仓库层集成测试，
与真实 MySQL 连接完全隔离。
"""
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.models  # noqa: F401 — 确保所有 model 注册到 Base.metadata
from app.core.database import Base


@pytest_asyncio.fixture
async def async_session() -> AsyncSession:
    """每个测试函数获得独立的 SQLite 内存库 + 全新表结构。"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
