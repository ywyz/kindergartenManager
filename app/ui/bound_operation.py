"""同步冻结点击输入，并把异步 UI 副作用绑定到同一可信会话。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar

from app.core.logging import get_logger
from app.ui.auth_context import TrustedUiSession, require_bound_ui_session


logger = get_logger(__name__)

PayloadT = TypeVar("PayloadT")
ResultT = TypeVar("ResultT")

UiSessionAuthorizer = Callable[
    [TrustedUiSession],
    Awaitable[TrustedUiSession | None],
]


class UiOperationPhase(str, Enum):
    """允许页面同步处理的两个受保护写回阶段。"""

    STARTED = "started"
    FINISHED = "finished"


class UiOperationStatus(str, Enum):
    """终态只暴露成功或关闭失败，不暴露异常正文。"""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class UiOperationOutcome(Generic[ResultT]):
    """异步 effect 的脱敏终态；业务值不进入 repr。"""

    status: UiOperationStatus
    value: ResultT | None = field(default=None, repr=False)
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class UiOperationEvent(Generic[ResultT]):
    """presenter 只会在同一会话与代次仍有效时收到的事件。"""

    phase: UiOperationPhase
    outcome: UiOperationOutcome[ResultT] | None = None


@dataclass(frozen=True, slots=True, repr=False)
class _Ticket(Generic[PayloadT]):
    generation: int
    payload: PayloadT


class BoundUiOperationScope:
    """页面内短命的会话、代次与 single-flight 操作编排。"""

    def __init__(
        self,
        opened_session: TrustedUiSession,
        *,
        authorize: UiSessionAuthorizer = require_bound_ui_session,
    ) -> None:
        if type(opened_session) is not TrustedUiSession:
            raise TypeError("opened_session must be a TrustedUiSession")
        self._opened_session = opened_session
        self._authorize = authorize
        self._generation = 0
        self._busy_slots: set[str] = set()

    def invalidate(self, *_event_args: object) -> None:
        """同步使所有迟到结果失效；不取消、不重试也不写 UI。"""
        self._generation += 1

    def bind(
        self,
        *,
        slot: str,
        capture: Callable[[], PayloadT],
        effect: Callable[
            [TrustedUiSession, PayloadT],
            Awaitable[ResultT],
        ],
        present: Callable[[UiOperationEvent[ResultT]], None],
        is_current: Callable[[PayloadT], bool] | None = None,
    ) -> Callable[..., Coroutine[Any, Any, None] | None]:
        """返回普通同步 handler；调用当下先 capture，再返回异步执行体。"""
        if type(slot) is not str or not slot:
            raise ValueError("slot must be a non-empty string")
        current_check = is_current or (lambda _payload: True)

        def trigger(*_event_args: object) -> Coroutine[Any, Any, None] | None:
            if slot in self._busy_slots:
                return None
            try:
                payload = deepcopy(capture())
            except Exception as exc:
                logger.error(
                    "bound_ui_capture_failed error_type=%s",
                    type(exc).__name__,
                )
                return None
            self._generation += 1
            ticket = _Ticket(
                generation=self._generation,
                payload=payload,
            )
            self._busy_slots.add(slot)
            return self._run(
                slot=slot,
                ticket=ticket,
                effect=effect,
                present=present,
                is_current=current_check,
            )

        return trigger

    def _ticket_is_current(
        self,
        ticket: _Ticket[PayloadT],
        is_current: Callable[[PayloadT], bool],
    ) -> bool:
        if ticket.generation != self._generation:
            return False
        try:
            return bool(is_current(ticket.payload))
        except Exception as exc:
            logger.error(
                "bound_ui_target_validation_failed error_type=%s",
                type(exc).__name__,
            )
            return False

    @staticmethod
    def _same_live_session(
        expected: TrustedUiSession,
        current: TrustedUiSession | None,
    ) -> bool:
        return bool(
            current is not None
            and current.session_id == expected.session_id
            and current.tenant_id == expected.tenant_id
            and current.user_id == expected.user_id
            and datetime.now(timezone.utc) < current.expires_at_utc
        )

    async def _authorize_ticket(
        self,
        ticket: _Ticket[PayloadT],
        is_current: Callable[[PayloadT], bool],
    ) -> TrustedUiSession | None:
        if not self._ticket_is_current(ticket, is_current):
            return None
        try:
            current = await self._authorize(self._opened_session)
        except Exception as exc:
            logger.error(
                "bound_ui_authorization_failed error_type=%s",
                type(exc).__name__,
            )
            return None
        if not self._ticket_is_current(ticket, is_current):
            return None
        if not self._same_live_session(self._opened_session, current):
            return None
        return current

    async def _run(
        self,
        *,
        slot: str,
        ticket: _Ticket[PayloadT],
        effect: Callable[
            [TrustedUiSession, PayloadT],
            Awaitable[ResultT],
        ],
        present: Callable[[UiOperationEvent[ResultT]], None],
        is_current: Callable[[PayloadT], bool],
    ) -> None:
        try:
            current = await self._authorize_ticket(ticket, is_current)
            if current is None:
                return

            present(UiOperationEvent(phase=UiOperationPhase.STARTED))
            try:
                value = await effect(current, ticket.payload)
            except Exception as exc:
                logger.error(
                    "bound_ui_effect_failed error_type=%s",
                    type(exc).__name__,
                )
                if await self._authorize_ticket(ticket, is_current) is None:
                    return
                present(
                    UiOperationEvent(
                        phase=UiOperationPhase.FINISHED,
                        outcome=UiOperationOutcome(
                            status=UiOperationStatus.FAILED,
                            error_code="operation.failed",
                        ),
                    )
                )
                return

            if await self._authorize_ticket(ticket, is_current) is None:
                return
            present(
                UiOperationEvent(
                    phase=UiOperationPhase.FINISHED,
                    outcome=UiOperationOutcome(
                        status=UiOperationStatus.SUCCEEDED,
                        value=value,
                    ),
                )
            )
        finally:
            self._busy_slots.discard(slot)
