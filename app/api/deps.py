"""对外 REST API 的 FastAPI 依赖。"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """提供独立的异步数据库会话（只读查询，无需提交）。

    测试可通过 ``app.dependency_overrides[get_db]`` 注入内存库会话。
    """
    async with AsyncSessionLocal() as session:
        yield session
