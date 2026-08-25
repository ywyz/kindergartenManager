"""F004 integration fixtures for the Agent Foundation public service seam."""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.models  # noqa: F401 - register every ORM model with Base.metadata
from app.core.database import Base


@pytest_asyncio.fixture
async def async_session() -> AsyncSession:
    """Give each Foundation integration test an isolated in-memory database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()
