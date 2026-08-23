"""SQLAlchemy 异步会话的最外层 Unit of Work。"""
from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession


class AsyncSessionUnitOfWork:
    """在一个 use-case 结束时统一提交，任一步失败时统一回滚。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSessionUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc_type is not None:
            await self._session.rollback()
            return False

        try:
            await self._session.commit()
        except BaseException:
            await self._session.rollback()
            raise
        return False
