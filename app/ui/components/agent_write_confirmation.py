"""NiceGUI actions for one explicit, page-local Agent Patch confirmation.

This component is deliberately a thin adapter. It never receives a repository,
ORM object, raw ``PlanPatch``, confirmation identifier, or legacy save callback.
Every service operation receives a freshly authorized UI session and a target
captured synchronously at the user's click.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import secrets
from typing import Any, Protocol
from uuid import UUID

from nicegui import ui

from app.core.logging import get_logger
from app.service.agent.composition import AgentPatchSnapshot
from app.ui.auth_context import TrustedUiSession
from app.ui.daily_plan_target import DailyPlanUiTarget, UiSingleFlightSlot


logger = get_logger(__name__)

PATCH_CONFIRMATION_ACTION_LABELS = (
    "准备确认",
    "确认采用",
    "取消确认",
    "人工对账",
)
PATCH_CONFIRMATION_NOTICE = (
    "仅采用当前页面的这一份草案；不会自动采用、批量采用或跨页面采用。"
    "结果不明时请先人工对账；离开或重新生成后只能人工核查。"
)

_FIELD_LABELS = {
    "activity_goal": "活动目标",
    "activity_prep": "活动准备",
    "activity_key": "活动重点",
    "activity_difficult": "活动难点",
    "activity_process_original": "活动过程（原文）",
    "activity_process_adapted": "活动过程（改写后）",
    "morning_activity": "晨间活动",
    "morning_talk_topic": "晨间谈话主题",
    "morning_talk_questions": "晨间谈话问题",
    "indoor_area": "室内区域游戏",
    "outdoor_activity": "户外活动",
    "daily_reflection": "每日反思",
}

_ERROR_COPY = {
    "before_mismatch": "计划内容已变化，本次确认已关闭，请重新生成草案。",
    "commit_not_applied": "对账确认本次写入未生效，请重新生成草案。",
    "commit_outcome_unknown": (
        "提交结果暂不确定，禁止重复采用；请留在当前页面人工对账。"
        "离开或重新生成后只能人工核查。"
    ),
    "confirmation_actor_mismatch": "当前用户与确认主体不一致，本次确认已关闭。",
    "confirmation_consumed": "本次确认已经结束，不能再次采用。",
    "confirmation_consuming": "本次确认正在处理，不能重复提交。",
    "confirmation_expired": "本次确认已过期，请重新生成草案。",
    "confirmation_indeterminate": (
        "提交结果仍不确定，请保留当前页面人工对账；离开或重新生成后只能人工核查。"
    ),
    "confirmation_not_applied": "对账确认本次写入未生效，请重新生成草案。",
    "confirmation_not_found": "本次确认已失效，请重新生成草案。",
    "confirmation_session_mismatch": "登录会话已变化，本次确认已关闭。",
    "confirmation_store_full": "当前确认服务繁忙，本次确认已关闭。",
    "patch_not_current": "草案已不属于当前页面，请重新生成。",
    "reconcile_integrity_failure": "对账完整性检查失败，请停止操作并人工核查。",
    "revision_mismatch": "计划 revision 已变化，本次确认已关闭。",
    "target_mismatch": "确认目标与当前计划不一致，请重新生成草案。",
    "target_not_found": "目标计划已不存在，本次确认已关闭。",
    "ui_session_invalid": "登录会话已失效，本次确认已关闭。",
    "write_failed": "写入未完成，本次确认已关闭，请重新生成草案。",
    "write_unavailable": "写入服务暂不可用，本次确认已关闭。",
}

_INDETERMINATE_ERROR_COPY = {
    "commit_outcome_unknown": "提交结果暂不确定，禁止重复采用；请人工对账。",
    "confirmation_consuming": (
        "原提交仍可能处理中，禁止重复采用；请稍后再次人工对账。"
    ),
    "confirmation_indeterminate": (
        "对账后结果仍不确定，禁止重复采用；请稍后再次人工对账或人工核查。"
    ),
    "confirmation_not_found": (
        "对账材料缺失，提交结果仍不确定；禁止重复采用，只能人工核查。"
    ),
    "write_unavailable": (
        "人工对账暂不可用，提交结果仍不确定；禁止重复采用，请稍后再次人工对账。"
    ),
}

_STATUS_COPY = {
    "idle": "尚未准备确认。",
    "pending": "已冻结当前计划与这一份草案，请核对后确认采用。",
    "applied": "这一份草案已确认采用。",
    "stale": "页面、计划或草案已变化，本次确认已关闭。",
    "expired": "本次确认已过期，请重新生成草案。",
    "failed": "本次确认未完成，且不会自动重试。",
    "indeterminate": (
        "提交结果暂不确定，禁止再次采用；请留在当前页面人工对账。"
        "离开或重新生成后只能人工核查。"
    ),
    "not_applied": "对账确认本次写入未生效，请重新生成草案。",
    "closed": "页面或连接已关闭，本次确认不可再使用。",
    "issuing": "正在准备这一份草案的确认……",
    "applying": "正在采用这一份草案，请勿重复点击……",
    "reconciling": "正在只读对账，请勿重复点击……",
}

_KNOWN_TERMINAL_STATUSES = frozenset(
    {"applied", "stale", "expired", "failed", "not_applied"}
)


class PatchConfirmationSnapshotView(Protocol):
    """Safe scalar projection published by the application confirmation flow."""

    status: object
    patch_id: UUID | None
    patch_sha256: str | None
    daily_plan_id: int | None
    expected_revision: int | None
    expires_at_utc: datetime | None
    field_paths: tuple[str, ...]
    before_revision: int | None
    after_revision: int | None
    error_code: str | None


class PatchConfirmationController(Protocol):
    """Narrow application port used by the UI without exposing stored authority."""

    @property
    def snapshot(self) -> PatchConfirmationSnapshotView:
        """Return the latest safe, immutable projection."""

    async def issue(
        self,
        ui_session: TrustedUiSession,
        patch_id: UUID,
        *,
        expected_plan_id: int,
        expected_revision: int,
    ) -> PatchConfirmationSnapshotView:
        """Prepare one confirmation for the exact current page target."""

    async def apply(
        self,
        ui_session: TrustedUiSession,
    ) -> PatchConfirmationSnapshotView:
        """Apply the one already prepared confirmation."""

    async def reconcile(
        self,
        ui_session: TrustedUiSession,
    ) -> PatchConfirmationSnapshotView:
        """Explicitly inspect an indeterminate commit outcome."""

    def invalidate(self) -> None:
        """Synchronously revoke page-local authority and cancel late publication."""

    async def disconnect(self) -> None:
        """Close confirmation state for a disconnected client."""

    async def close(self) -> None:
        """Permanently close confirmation state for a deleted page."""


ConfirmationAuthorizer = Callable[[], Awaitable[TrustedUiSession | None]]
TargetCapture = Callable[[], DailyPlanUiTarget | None]
TargetPredicate = Callable[[DailyPlanUiTarget], bool]
AppliedCallback = Callable[
    [PatchConfirmationSnapshotView, DailyPlanUiTarget],
    Awaitable[None],
]


@dataclass(frozen=True, slots=True)
class _ConfirmationClick:
    generation: int
    patch: AgentPatchSnapshot
    target: DailyPlanUiTarget | None


@dataclass(slots=True)
class _PatchView:
    generation: int
    patch: AgentPatchSnapshot
    container: Any


@dataclass(frozen=True, slots=True)
class _TerminalPatchRecord:
    status: str
    error_code: str | None = None
    after_revision: int | None = None


class _Action(str, Enum):
    ISSUE = "issue"
    APPLY = "apply"
    RECONCILE = "reconcile"


class _PublishGuard(str, Enum):
    CURRENT = "current"
    SESSION_STALE = "session_stale"
    TARGET_STALE = "target_stale"
    APPLIED_TARGET_STALE = "applied_target_stale"
    INDETERMINATE_TARGET_STALE = "indeterminate_target_stale"


_ACTION_BUSY_COPY = {
    _Action.ISSUE: _STATUS_COPY["issuing"],
    _Action.APPLY: _STATUS_COPY["applying"],
    _Action.RECONCILE: _STATUS_COPY["reconciling"],
}

_ACTION_FAILURE_COPY = {
    _Action.ISSUE: "准备确认失败，本次确认已关闭。",
    _Action.APPLY: "确认采用失败，本次确认已关闭。",
    _Action.RECONCILE: "人工对账失败，本次确认已关闭。",
}


def _status_value(snapshot: PatchConfirmationSnapshotView) -> str:
    value = getattr(snapshot.status, "value", snapshot.status)
    return value if type(value) is str else "failed"


def _format_expiry(value: datetime | None) -> str | None:
    if type(value) is not datetime:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class DailyPlanPatchConfirmationPanel:
    """Render one-Patch confirmation controls inside the Agent Patch row."""

    def __init__(
        self,
        controller: PatchConfirmationController,
        *,
        authorize_confirmation: ConfirmationAuthorizer,
        capture_target: TargetCapture,
        is_current_target: TargetPredicate,
        on_applied: AppliedCallback,
    ) -> None:
        for callback in (
            authorize_confirmation,
            capture_target,
            is_current_target,
            on_applied,
        ):
            if not callable(callback):
                raise ValueError("patch_confirmation_callback_invalid")
        self._controller = controller
        self._authorize_confirmation = authorize_confirmation
        self._capture_target = capture_target
        self._is_current_target = is_current_target
        self._on_applied = on_applied
        self._operations = UiSingleFlightSlot[_ConfirmationClick]()
        self._generation = 0
        self._closed = False
        self._abandoned_indeterminate = False
        self._integrity_blocked = False
        self._issued_patch_id: UUID | None = None
        self._issued_patch_sha256: str | None = None
        self._issued_target: DailyPlanUiTarget | None = None
        self._views: list[_PatchView] = []
        self._terminal_patch_ledger: dict[
            tuple[UUID, str],
            _TerminalPatchRecord,
        ] = {}

    def render_patch_actions(self, patch: AgentPatchSnapshot) -> None:
        """Render explicit actions for exactly this displayed Patch row."""
        if type(patch) is not AgentPatchSnapshot:
            raise ValueError("agent_patch_snapshot_invalid")
        generation = self._generation
        self._views = [view for view in self._views if view.generation == generation]
        ui.separator().classes("my-1")
        ui.label(PATCH_CONFIRMATION_NOTICE).classes("text-xs text-orange-700")
        if self._abandoned_indeterminate:
            ui.label(
                "此前结果不明的页面内对账入口已放弃；本页只显示新建议，"
                "请刷新页面后再准备新的确认。"
            ).classes("text-xs font-medium text-red-700")
            return
        with ui.column().classes("w-full gap-1") as container:
            pass
        view = _PatchView(
            generation=generation,
            patch=patch,
            container=container,
        )
        self._views.append(view)
        self._render_view(view, self._controller.snapshot)

    def invalidate(self) -> None:
        """Synchronously close pending authority before any page mutation."""
        if self._closed:
            return
        self._latch_integrity_failure(self._controller.snapshot)
        if not self._integrity_blocked:
            self._controller.invalidate()
            self._abandoned_indeterminate = (
                _status_value(self._controller.snapshot) == "indeterminate"
            )
        self._terminal_patch_ledger.clear()
        self._generation += 1
        self._issued_patch_id = None
        self._issued_patch_sha256 = None
        self._issued_target = None
        self._views.clear()

    async def disconnect(self) -> None:
        """Close all connection-local controls and cancel their exact operation."""
        await self._shutdown(self._controller.disconnect)

    async def close(self) -> None:
        """Permanently close controls and cancel their exact operation."""
        await self._shutdown(self._controller.close)

    async def _shutdown(self, close_flow: Callable[[], Awaitable[None]]) -> None:
        if self._closed:
            return
        self._closed = True
        self._abandoned_indeterminate = True
        self._generation += 1
        self._issued_patch_id = None
        self._issued_patch_sha256 = None
        self._issued_target = None
        self._views.clear()
        self._terminal_patch_ledger.clear()
        await close_flow()

    def _capture_click(self, view: _PatchView) -> _ConfirmationClick:
        try:
            target = self._capture_target()
        except Exception as exc:
            logger.error(
                "patch_confirmation_target_capture_failed error_type=%s",
                type(exc).__name__,
            )
            target = None
        return _ConfirmationClick(
            generation=view.generation,
            patch=view.patch,
            target=target,
        )

    def _click_is_current(
        self,
        view: _PatchView,
        click: _ConfirmationClick,
        *,
        require_issued_target: bool,
    ) -> bool:
        target = click.target
        if (
            self._closed
            or self._integrity_blocked
            or view.generation != self._generation
            or click.generation != self._generation
            or type(target) is not DailyPlanUiTarget
        ):
            return False
        try:
            current = self._is_current_target(target)
        except Exception as exc:
            logger.error(
                "patch_confirmation_target_check_failed error_type=%s",
                type(exc).__name__,
            )
            return False
        if not current:
            return False
        if not require_issued_target:
            return True
        return bool(
            click.patch.patch_id == self._issued_patch_id
            and type(self._issued_patch_sha256) is str
            and secrets.compare_digest(
                click.patch.patch_sha256,
                self._issued_patch_sha256,
            )
            and target == self._issued_target
        )

    async def _authorize(self) -> TrustedUiSession | None:
        try:
            session = await self._authorize_confirmation()
        except Exception as exc:
            logger.error(
                "patch_confirmation_authorization_failed error_type=%s",
                type(exc).__name__,
            )
            return None
        return session if type(session) is TrustedUiSession else None

    async def _publish_guarded(
        self,
        view: _PatchView,
        click: _ConfirmationClick,
        first_session: TrustedUiSession,
        *,
        require_issued_target: bool,
    ) -> _PublishGuard:
        current_session = await self._authorize()
        if not (
            current_session is not None
            and current_session.session_id == first_session.session_id
            and current_session.tenant_id == first_session.tenant_id
            and current_session.user_id == first_session.user_id
        ):
            self._controller.invalidate()
            return _PublishGuard.SESSION_STALE
        if self._click_is_current(
            view,
            click,
            require_issued_target=require_issued_target,
        ):
            return _PublishGuard.CURRENT

        status = _status_value(self._controller.snapshot)
        self._controller.invalidate()
        if status == "applied":
            return _PublishGuard.APPLIED_TARGET_STALE
        if status == "indeterminate" or (
            _status_value(self._controller.snapshot) == "indeterminate"
        ):
            self._abandoned_indeterminate = True
            self._issued_patch_id = None
            self._issued_patch_sha256 = None
            self._issued_target = None
            return _PublishGuard.INDETERMINATE_TARGET_STALE
        return _PublishGuard.TARGET_STALE

    def _render_guard_rejection(
        self,
        view: _PatchView,
        guard: _PublishGuard,
        snapshot: PatchConfirmationSnapshotView,
    ) -> None:
        if view.generation != self._generation:
            return
        if guard is _PublishGuard.SESSION_STALE:
            if _status_value(snapshot) != "indeterminate":
                self._remember_patch_terminal(view.patch, "stale")
            view.container.clear()
            with view.container:
                ui.label("登录会话已变化，操作结果未在本页发布。").classes(
                    "text-xs font-medium text-red-700"
                )
                ui.label("禁止直接重试或重新采用；请重新登录后核查当前计划。").classes(
                    "text-xs text-gray-600"
                )
            return
        if guard is _PublishGuard.APPLIED_TARGET_STALE:
            view.container.clear()
            with view.container:
                ui.label("采用已经完成，但页面目标已变化；不要重复采用。").classes(
                    "text-xs font-medium text-red-700"
                )
                ui.label("请重新选择日期，从数据库载入当前计划。").classes(
                    "text-xs text-gray-600"
                )
            return
        if guard is _PublishGuard.INDETERMINATE_TARGET_STALE:
            self._render_abandoned_indeterminate(
                view,
                "提交结果不明且页面目标已变化；本页对账入口已放弃。",
            )
            return
        self._remember_patch_terminal(view.patch, "stale")
        view.container.clear()
        with view.container:
            ui.label("页面目标已变化，操作结果未在本页发布。").classes(
                "text-xs font-medium text-red-700"
            )
            ui.label("禁止直接重试或重新采用；请先从数据库重载并人工核查。").classes(
                "text-xs text-gray-600"
            )

    def _render_abandoned_indeterminate(
        self,
        view: _PatchView,
        message: str,
    ) -> None:
        if view.generation != self._generation:
            return
        view.container.clear()
        with view.container:
            ui.label(message).classes("text-xs font-medium text-red-700")
            ui.label("禁止重复采用，只能人工核查数据库与审计证据。").classes(
                "text-xs text-gray-600"
            )

    def _render_busy(self, view: _PatchView, message: str) -> None:
        if view.generation != self._generation:
            return
        view.container.clear()
        with view.container:
            ui.label(message).classes("text-xs text-blue-700")

    def _render_local_closed(self, view: _PatchView, message: str) -> None:
        if view.generation != self._generation:
            return
        view.container.clear()
        with view.container:
            ui.label(message).classes("text-xs text-red-600")
            ui.label("不会自动重试；如需采用，请重新生成草案。").classes(
                "text-xs text-gray-600"
            )

    @staticmethod
    def _patch_identity(patch: AgentPatchSnapshot) -> tuple[UUID, str]:
        return (patch.patch_id, patch.patch_sha256)

    @staticmethod
    def _snapshot_identity(
        snapshot: PatchConfirmationSnapshotView,
    ) -> tuple[UUID, str] | None:
        if (
            type(snapshot.patch_id) is not UUID
            or type(snapshot.patch_sha256) is not str
        ):
            return None
        return (snapshot.patch_id, snapshot.patch_sha256)

    def _remember_patch_terminal(
        self,
        patch: AgentPatchSnapshot,
        status: str,
        *,
        error_code: str | None = None,
        after_revision: int | None = None,
    ) -> None:
        """Close one exact Patch for the current Agent generation only."""
        if status == "indeterminate":
            return
        self._terminal_patch_ledger.setdefault(
            self._patch_identity(patch),
            _TerminalPatchRecord(
                status=status,
                error_code=error_code,
                after_revision=after_revision,
            ),
        )

    def _remember_known_terminal(
        self,
        snapshot: PatchConfirmationSnapshotView,
    ) -> None:
        status = _status_value(snapshot)
        if status not in _KNOWN_TERMINAL_STATUSES:
            return
        identity = self._snapshot_identity(snapshot)
        if identity is None:
            return
        self._terminal_patch_ledger.setdefault(
            identity,
            _TerminalPatchRecord(
                status=status,
                error_code=snapshot.error_code,
                after_revision=snapshot.after_revision,
            ),
        )

    def _remember_action_terminal(
        self,
        patch: AgentPatchSnapshot,
        snapshot: PatchConfirmationSnapshotView,
    ) -> None:
        """Close the clicked Patch when a terminal projection has bad identity."""
        status = _status_value(snapshot)
        if status not in _KNOWN_TERMINAL_STATUSES:
            return
        if self._snapshot_identity(snapshot) == self._patch_identity(patch):
            self._remember_known_terminal(snapshot)
            return
        self._remember_patch_terminal(
            patch,
            "failed",
            error_code="patch_not_current",
        )
        self._remember_known_terminal(snapshot)

    def _render_remembered_terminal(
        self,
        record: _TerminalPatchRecord,
    ) -> None:
        if record.status == "cancelled":
            ui.label("已取消这一份草案的确认；未执行写入。").classes(
                "text-xs text-red-600"
            )
        elif record.status == "applied":
            revision = (
                f" 当前 revision 为 {record.after_revision}。"
                if type(record.after_revision) is int
                else ""
            )
            ui.label(f"{_STATUS_COPY['applied']}{revision}").classes(
                "text-xs font-medium text-green-700"
            )
        else:
            message = _ERROR_COPY.get(
                record.error_code or "",
                _STATUS_COPY.get(record.status, _STATUS_COPY["failed"]),
            )
            css = (
                "text-orange-700"
                if record.status == "not_applied"
                else "text-red-600"
            )
            ui.label(message).classes(f"text-xs {css}")
        ui.label("这一份草案已关闭，不会自动重试或重复采用；请重新生成草案。").classes(
            "text-xs text-gray-600"
        )

    def _render_remembered_view(
        self,
        view: _PatchView,
        record: _TerminalPatchRecord,
    ) -> None:
        if view.generation != self._generation:
            return
        view.container.clear()
        with view.container:
            self._render_remembered_terminal(record)

    def _latch_integrity_failure(
        self,
        snapshot: PatchConfirmationSnapshotView,
    ) -> bool:
        """Keep a reconcile-integrity failure terminal for this page lifetime."""
        if snapshot.error_code == "reconcile_integrity_failure":
            self._integrity_blocked = True
            self._issued_patch_id = None
            self._issued_patch_sha256 = None
            self._issued_target = None
        return self._integrity_blocked

    def _render_integrity_blocked(
        self,
        view: _PatchView,
        snapshot: PatchConfirmationSnapshotView,
    ) -> None:
        if self._belongs_to_patch(snapshot, view.patch):
            self._render_target(snapshot)
        ui.label(_ERROR_COPY["reconcile_integrity_failure"]).classes(
            "text-xs font-medium text-red-700"
        )
        ui.label(
            "本页面的所有草案确认均已停止；请人工核查数据库与审计证据，"
            "刷新页面前不能准备或采用任何草案。"
        ).classes("text-xs text-gray-600")

    def _belongs_to_patch(
        self,
        snapshot: PatchConfirmationSnapshotView,
        patch: AgentPatchSnapshot,
    ) -> bool:
        if snapshot.patch_id != patch.patch_id:
            return False
        snapshot_hash = snapshot.patch_sha256
        return bool(
            type(snapshot_hash) is str
            and secrets.compare_digest(snapshot_hash, patch.patch_sha256)
        )

    @staticmethod
    def _patch_hash_mismatch(
        snapshot: PatchConfirmationSnapshotView,
        patch: AgentPatchSnapshot,
    ) -> bool:
        snapshot_hash = snapshot.patch_sha256
        return bool(
            snapshot.patch_id == patch.patch_id
            and (
                type(snapshot_hash) is not str
                or not secrets.compare_digest(snapshot_hash, patch.patch_sha256)
            )
        )

    def _render_target(self, snapshot: PatchConfirmationSnapshotView) -> None:
        if (
            type(snapshot.daily_plan_id) is int
            and type(snapshot.expected_revision) is int
        ):
            ui.label(
                f"目标计划：#{snapshot.daily_plan_id} · "
                f"预期 revision {snapshot.expected_revision}"
            ).classes("text-xs font-medium text-gray-700")
        if snapshot.field_paths:
            fields = "、".join(
                _FIELD_LABELS.get(path, path) for path in snapshot.field_paths
            )
            ui.label(f"本次字段：{fields}").classes("text-xs text-gray-600")
        expiry = _format_expiry(snapshot.expires_at_utc)
        if expiry is not None:
            ui.label(f"确认有效期至：{expiry}").classes("text-xs text-gray-600")

    def _render_prepare(self, view: _PatchView) -> None:
        ui.label(
            f"目标计划：#{view.patch.daily_plan_id} · 点击时将重新核对当前 revision"
        ).classes("text-xs text-gray-600")
        trigger = self._operations.bind(
            capture=lambda: self._capture_click(view),
            run=lambda owner, click: self._run_action(
                owner,
                view,
                click,
                _Action.ISSUE,
            ),
        )
        ui.button(
            PATCH_CONFIRMATION_ACTION_LABELS[0],
            icon="fact_check",
            on_click=trigger,
        ).props("outline dense").classes("text-blue-700")

    def _render_occupied(
        self,
        view: _PatchView,
        snapshot: PatchConfirmationSnapshotView,
    ) -> None:
        self._render_target(snapshot)
        ui.label(
            "另一份草案正在占用当前页面的确认；请先完成或取消该草案，"
            "不能准备这一份草案。"
        ).classes("text-xs font-medium text-orange-700")
        trigger = self._operations.bind(
            capture=lambda: self._capture_click(view),
            run=lambda owner, click: self._run_action(
                owner,
                view,
                click,
                _Action.ISSUE,
            ),
        )
        ui.button(
            PATCH_CONFIRMATION_ACTION_LABELS[0],
            icon="lock",
            on_click=trigger,
        ).props("outline dense").classes("text-gray-500").disable()

    def _render_pending(
        self,
        view: _PatchView,
        snapshot: PatchConfirmationSnapshotView,
    ) -> None:
        self._render_target(snapshot)
        ui.label(_STATUS_COPY["pending"]).classes("text-xs text-orange-700")
        apply_trigger = self._operations.bind(
            capture=lambda: self._capture_click(view),
            run=lambda owner, click: self._run_action(
                owner,
                view,
                click,
                _Action.APPLY,
            ),
        )
        with ui.row().classes("gap-2"):
            ui.button(
                PATCH_CONFIRMATION_ACTION_LABELS[1],
                icon="check_circle",
                on_click=apply_trigger,
            ).classes("bg-orange-600 text-white")
            ui.button(
                PATCH_CONFIRMATION_ACTION_LABELS[2],
                icon="cancel",
                on_click=lambda: self._cancel_confirmation(view),
            ).props("flat dense")

    def _render_indeterminate(
        self,
        view: _PatchView,
        snapshot: PatchConfirmationSnapshotView,
    ) -> None:
        self._render_target(snapshot)
        ui.label(
            _INDETERMINATE_ERROR_COPY.get(
                snapshot.error_code or "",
                _STATUS_COPY["indeterminate"],
            )
        ).classes("text-xs font-medium text-red-700")
        ui.label("离开或重新生成会销毁本页面内的人工对账入口。").classes(
            "text-xs text-orange-700"
        )
        trigger = self._operations.bind(
            capture=lambda: self._capture_click(view),
            run=lambda owner, click: self._run_action(
                owner,
                view,
                click,
                _Action.RECONCILE,
            ),
        )
        ui.button(
            PATCH_CONFIRMATION_ACTION_LABELS[3],
            icon="manage_search",
            on_click=trigger,
        ).props("outline dense").classes("text-red-700")

    def _render_terminal(
        self,
        snapshot: PatchConfirmationSnapshotView,
    ) -> None:
        status = _status_value(snapshot)
        self._render_target(snapshot)
        if status == "applied":
            revision = (
                f" 当前 revision 为 {snapshot.after_revision}。"
                if type(snapshot.after_revision) is int
                else ""
            )
            ui.label(f"{_STATUS_COPY[status]}{revision}").classes(
                "text-xs font-medium text-green-700"
            )
            return
        message = _ERROR_COPY.get(
            snapshot.error_code or "",
            _STATUS_COPY.get(status, _STATUS_COPY["failed"]),
        )
        css = "text-orange-700" if status == "not_applied" else "text-red-600"
        ui.label(message).classes(f"text-xs {css}")
        ui.label("此状态已关闭，不会自动重试；如需采用，请重新生成草案。").classes(
            "text-xs text-gray-600"
        )

    def _render_view(
        self,
        view: _PatchView,
        snapshot: PatchConfirmationSnapshotView,
    ) -> None:
        if view.generation != self._generation:
            return
        view.container.clear()
        with view.container:
            if self._closed:
                ui.label(_STATUS_COPY["closed"]).classes("text-xs text-red-600")
                return
            if self._latch_integrity_failure(snapshot):
                self._render_integrity_blocked(view, snapshot)
                return
            if self._patch_hash_mismatch(snapshot, view.patch):
                ui.label("草案身份校验失败，本页拒绝提供确认操作。").classes(
                    "text-xs text-red-600"
                )
                ui.label("不会自动重试；如需采用，请重新生成草案。").classes(
                    "text-xs text-gray-600"
                )
                return
            self._remember_known_terminal(snapshot)
            terminal = self._terminal_patch_ledger.get(
                self._patch_identity(view.patch)
            )
            if terminal is not None:
                if self._belongs_to_patch(snapshot, view.patch):
                    self._render_target(snapshot)
                self._render_remembered_terminal(terminal)
                return
            if not self._belongs_to_patch(snapshot, view.patch):
                if _status_value(snapshot) in {"pending", "indeterminate"}:
                    self._render_occupied(view, snapshot)
                    return
                self._render_prepare(view)
                return
            status = _status_value(snapshot)
            if status == "pending":
                self._render_pending(view, snapshot)
            elif status == "indeterminate":
                self._render_indeterminate(view, snapshot)
            elif status in {"issuing", "applying", "reconciling"}:
                ui.label(_STATUS_COPY[status]).classes("text-xs text-blue-700")
            elif status == "idle":
                self._render_prepare(view)
            else:
                self._render_terminal(snapshot)

    def _reject_stale_click(self, view: _PatchView) -> None:
        self._remember_known_terminal(self._controller.snapshot)
        self._controller.invalidate()
        self._remember_known_terminal(self._controller.snapshot)
        self._issued_patch_id = None
        self._issued_patch_sha256 = None
        self._issued_target = None
        if _status_value(self._controller.snapshot) == "indeterminate":
            self._abandoned_indeterminate = True
            self._render_abandoned_indeterminate(
                view,
                "提交结果仍不确定且页面目标或登录会话已变化；本页对账入口已放弃。",
            )
            return
        self._remember_patch_terminal(view.patch, "stale")
        self._render_local_closed(
            view,
            "页面目标或登录会话已变化，本次确认已关闭。",
        )

    def _issue_target_is_valid(self, click: _ConfirmationClick) -> bool:
        target = click.target
        return bool(
            type(target) is DailyPlanUiTarget
            and type(target.plan_id) is int
            and type(target.revision) is int
            and target.plan_id == click.patch.daily_plan_id
        )

    async def _invoke_action(
        self,
        action: _Action,
        session: TrustedUiSession,
        click: _ConfirmationClick,
    ) -> PatchConfirmationSnapshotView:
        target = click.target
        if action is _Action.ISSUE:
            assert type(target) is DailyPlanUiTarget
            assert type(target.plan_id) is int
            assert type(target.revision) is int
            return await self._controller.issue(
                session,
                click.patch.patch_id,
                expected_plan_id=target.plan_id,
                expected_revision=target.revision,
            )
        if action is _Action.APPLY:
            return await self._controller.apply(session)
        return await self._controller.reconcile(session)

    async def _run_action(
        self,
        _owner: object,
        view: _PatchView,
        click: _ConfirmationClick,
        action: _Action,
    ) -> None:
        if (
            self._closed
            or view.generation != self._generation
            or click.generation != self._generation
        ):
            return
        remembered = self._terminal_patch_ledger.get(
            self._patch_identity(click.patch)
        )
        if remembered is not None:
            self._render_remembered_view(view, remembered)
            return
        require_issued_target = action is not _Action.ISSUE
        current_snapshot = self._controller.snapshot
        if self._latch_integrity_failure(current_snapshot):
            self._render_all_views(current_snapshot)
            return
        if (
            action is _Action.ISSUE
            and _status_value(current_snapshot) in {"pending", "indeterminate"}
            and not self._belongs_to_patch(current_snapshot, click.patch)
        ):
            self._render_all_views(current_snapshot)
            return
        if not self._click_is_current(
            view,
            click,
            require_issued_target=require_issued_target,
        ) or (action is _Action.ISSUE and not self._issue_target_is_valid(click)):
            self._reject_stale_click(view)
            return

        self._render_busy(view, _ACTION_BUSY_COPY[action])
        current_session = await self._authorize()
        if current_session is None or not self._click_is_current(
            view,
            click,
            require_issued_target=require_issued_target,
        ):
            self._reject_stale_click(view)
            return
        try:
            snapshot = await self._invoke_action(action, current_session, click)
        except Exception as exc:
            logger.error(
                "patch_confirmation_%s_failed error_type=%s",
                action.value,
                type(exc).__name__,
            )
            self._remember_known_terminal(self._controller.snapshot)
            self._controller.invalidate()
            if _status_value(self._controller.snapshot) == "indeterminate":
                self._abandoned_indeterminate = True
                self._issued_patch_id = None
                self._issued_patch_sha256 = None
                self._issued_target = None
                self._render_abandoned_indeterminate(
                    view,
                    "操作异常且提交结果不确定；本页对账入口已放弃。",
                )
                return
            self._remember_patch_terminal(click.patch, "failed")
            self._render_local_closed(view, _ACTION_FAILURE_COPY[action])
            return
        if self._latch_integrity_failure(snapshot):
            self._render_all_views(snapshot)
            return
        self._remember_action_terminal(click.patch, snapshot)
        publish_guard = await self._publish_guarded(
            view,
            click,
            current_session,
            require_issued_target=require_issued_target,
        )
        if publish_guard is not _PublishGuard.CURRENT:
            self._render_guard_rejection(view, publish_guard, snapshot)
            return

        if action is _Action.ISSUE:
            if (
                _status_value(snapshot) == "pending"
                and self._belongs_to_patch(snapshot, click.patch)
            ):
                self._issued_patch_id = click.patch.patch_id
                self._issued_patch_sha256 = click.patch.patch_sha256
                self._issued_target = click.target
            else:
                self._issued_patch_id = None
                self._issued_patch_sha256 = None
                self._issued_target = None
        self._render_all_views(snapshot)
        if action is not _Action.ISSUE and _status_value(snapshot) == "applied":
            await self._publish_applied(view, snapshot, click.target)

    def _render_all_views(
        self,
        snapshot: PatchConfirmationSnapshotView,
    ) -> None:
        for current_view in tuple(self._views):
            self._render_view(current_view, snapshot)

    async def _publish_applied(
        self,
        view: _PatchView,
        snapshot: PatchConfirmationSnapshotView,
        target: DailyPlanUiTarget | None,
    ) -> None:
        if type(target) is not DailyPlanUiTarget or view.generation != self._generation:
            return
        try:
            await self._on_applied(snapshot, target)
        except Exception as exc:
            logger.error(
                "patch_confirmation_reload_failed error_type=%s",
                type(exc).__name__,
            )
            if view.generation != self._generation:
                return
            view.container.clear()
            with view.container:
                ui.label("采用已经完成，但页面重读失败；不要重复采用。").classes(
                    "text-xs font-medium text-red-700"
                )
                ui.label("请重新选择日期，从数据库载入当前计划。").classes(
                    "text-xs text-gray-600"
                )

    def _cancel_confirmation(self, view: _PatchView) -> None:
        if self._closed or view.generation != self._generation:
            return
        if self._integrity_blocked:
            self._render_all_views(self._controller.snapshot)
            return
        remembered = self._terminal_patch_ledger.get(
            self._patch_identity(view.patch)
        )
        if remembered is not None:
            self._render_remembered_view(view, remembered)
            return
        self._remember_known_terminal(self._controller.snapshot)
        self._controller.invalidate()
        if _status_value(self._controller.snapshot) == "indeterminate":
            self._render_all_views(self._controller.snapshot)
            return
        self._remember_patch_terminal(view.patch, "cancelled")
        current_views = tuple(
            current_view
            for current_view in self._views
            if current_view.generation == self._generation
        )
        self._generation += 1
        self._issued_patch_id = None
        self._issued_patch_sha256 = None
        self._issued_target = None
        self._views = [
            _PatchView(
                generation=self._generation,
                patch=current_view.patch,
                container=current_view.container,
            )
            for current_view in current_views
        ]
        self._render_all_views(self._controller.snapshot)
