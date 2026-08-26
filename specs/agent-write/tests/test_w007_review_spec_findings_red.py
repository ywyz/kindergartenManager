"""Stable RED for fixed-SHA W007 Spec Review findings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import inspect
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.service.agent.composition import (
    AgentPatchSnapshot,
    DailyPlanAgentController,
)
from app.service.agent.confirmed_write import (
    ConfirmedDailyPlanWriteResult,
    ConfirmedWriteRejected,
    PendingPlanPatchConfirmation,
)
from app.service.agent.confirmation_flow import (
    PatchConfirmationSnapshot,
    PatchConfirmationStatus,
)
from app.service.agent.contracts import DailyPlanScope, TrustedActor
from app.service.agent.patch import PlanPatch
from app.service.agent.runtime import AgentTurnOutcome, AgentTurnStatus
from app.ui.components.date_panel import DateSelection
from app.ui.daily_plan_target import DailyPlanUiTarget

from conftest import (
    ACTOR_TENANT_ID,
    ACTOR_USER_ID,
    NOW,
    OPERATION_ID,
    PLAN_DATE,
    PLAN_ID,
    TURN_ID,
    build_patch,
    trusted_ui_session,
)


CONFIRMATION_ID = UUID("88888888-8888-4888-8888-888888888888")
SECOND_OPERATION_ID = UUID("99999999-9999-4999-8999-999999999999")


@dataclass(slots=True)
class _MultiPatchCoordinator:
    patches: tuple[PlanPatch, ...]

    async def execute(
        self,
        *,
        owner_id: UUID,
        actor: TrustedActor,
        scope: DailyPlanScope,
        intent: str,
        scope_reader: Callable[[], DailyPlanScope | None],
    ) -> AgentTurnOutcome:
        del owner_id, actor, intent
        assert scope_reader() == scope
        return AgentTurnOutcome(
            status=AgentTurnStatus.DRAFT_READY,
            assistant_content="同一轮生成两份独立草案。",
            patches=self.patches,
        )

    def invalidate(self, owner_id: UUID) -> None:
        del owner_id

    def plan_changed(self, actor: TrustedActor, scope: DailyPlanScope) -> None:
        del actor, scope

    async def cancel(self, owner_id: UUID) -> bool:
        del owner_id
        return True


@dataclass(slots=True)
class _RecordingWriter:
    issue_patch_ids: list[UUID] = field(default_factory=list)
    apply_confirmation_ids: list[UUID] = field(default_factory=list)
    reconcile_confirmation_ids: list[UUID] = field(default_factory=list)
    apply_error_code: str | None = None
    reconcile_error_code: str | None = None

    async def issue_confirmation(
        self,
        ui_session: object,
        patch: PlanPatch,
        *,
        expected_revision: int,
    ) -> PendingPlanPatchConfirmation:
        del ui_session
        self.issue_patch_ids.append(patch.patch_id)
        return PendingPlanPatchConfirmation(
            confirmation_id=CONFIRMATION_ID,
            expires_at_utc=NOW,
            daily_plan_id=patch.target.daily_plan_id,
            expected_revision=expected_revision,
            patch_id=patch.patch_id,
            patch_sha256=patch.canonical_sha256,
            field_paths=tuple(item.field_path for item in patch.operations),
        )

    async def apply(
        self,
        ui_session: object,
        confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult:
        del ui_session
        self.apply_confirmation_ids.append(confirmation_id)
        if self.apply_error_code is not None:
            raise ConfirmedWriteRejected(self.apply_error_code)
        return ConfirmedDailyPlanWriteResult(
            before_version_id=41,
            audit_id=42,
            before_revision=1,
            after_revision=2,
        )

    async def reconcile(
        self,
        ui_session: object,
        confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult:
        del ui_session
        self.reconcile_confirmation_ids.append(confirmation_id)
        if self.reconcile_error_code is not None:
            raise ConfirmedWriteRejected(self.reconcile_error_code)
        return ConfirmedDailyPlanWriteResult(
            before_version_id=41,
            audit_id=42,
            before_revision=1,
            after_revision=2,
        )


class _FakeElement:
    def __init__(
        self,
        fake_ui: _FakeUi,
        *,
        kind: str,
        text: str | None = None,
        on_click: Callable[..., object] | None = None,
    ) -> None:
        self._ui = fake_ui
        self.kind = kind
        self.text = text
        self.on_click = on_click
        self.parent = fake_ui._stack[-1] if fake_ui._stack else None
        self.children: list[_FakeElement] = []
        self.active = True
        self.enabled = True
        self.value = ""
        if self.parent is not None:
            self.parent.children.append(self)

    def __enter__(self) -> _FakeElement:
        self._ui._stack.append(self)
        return self

    def __exit__(self, *_args: object) -> None:
        assert self._ui._stack.pop() is self

    def classes(self, *_args: object, **_kwargs: object) -> _FakeElement:
        return self

    def props(self, *_args: object, **_kwargs: object) -> _FakeElement:
        return self

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def clear(self) -> None:
        def deactivate(element: _FakeElement) -> None:
            element.active = False
            for child in element.children:
                deactivate(child)

        for child in self.children:
            deactivate(child)
        self.children.clear()

    def is_within(self, ancestor: _FakeElement) -> bool:
        current = self.parent
        while current is not None:
            if current is ancestor:
                return True
            current = current.parent
        return False


class _FakeUi:
    def __init__(self) -> None:
        self._stack: list[_FakeElement] = []
        self.elements: list[_FakeElement] = []

    def _element(
        self,
        kind: str,
        text: str | None = None,
        *,
        on_click: Callable[..., object] | None = None,
    ) -> _FakeElement:
        element = _FakeElement(
            self,
            kind=kind,
            text=text,
            on_click=on_click,
        )
        self.elements.append(element)
        return element

    def card(self) -> _FakeElement:
        return self._element("card")

    def column(self) -> _FakeElement:
        return self._element("column")

    def row(self) -> _FakeElement:
        return self._element("row")

    def separator(self) -> _FakeElement:
        return self._element("separator")

    def label(self, text: str) -> _FakeElement:
        return self._element("label", text)

    def textarea(self, **_kwargs: object) -> _FakeElement:
        return self._element("textarea")

    def button(
        self,
        text: str,
        *,
        on_click: Callable[..., object] | None = None,
        **_kwargs: object,
    ) -> _FakeElement:
        return self._element("button", text, on_click=on_click)

    def latest_column(self) -> _FakeElement:
        return next(
            element
            for element in reversed(self.elements)
            if element.active and element.kind == "column"
        )

    def latest_button(
        self,
        text: str,
        *,
        within: _FakeElement,
    ) -> _FakeElement:
        return next(
            element
            for element in reversed(self.elements)
            if element.active
            and element.kind == "button"
            and element.text == text
            and element.is_within(within)
        )

    def active_label_texts(
        self,
        *,
        within: _FakeElement | None = None,
    ) -> tuple[str, ...]:
        return tuple(
            element.text
            for element in self.elements
            if element.active
            and element.kind == "label"
            and type(element.text) is str
            and (within is None or element.is_within(within))
        )

    def active_buttons(
        self,
        text: str,
        *,
        within: _FakeElement,
        enabled: bool | None = None,
    ) -> tuple[_FakeElement, ...]:
        return tuple(
            element
            for element in self.elements
            if element.active
            and element.kind == "button"
            and element.text == text
            and element.is_within(within)
            and (enabled is None or element.enabled is enabled)
        )


class _FakeClient:
    def on_disconnect(self, callback: Callable[..., object]) -> None:
        del callback

    def on_delete(self, callback: Callable[..., object]) -> None:
        del callback


class _NoopPatchActions:
    def render_patch_actions(self, patch: AgentPatchSnapshot) -> None:
        del patch

    def invalidate(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def close(self) -> None:
        return None


@dataclass(slots=True)
class _IdentityTerminalController:
    """Public confirmation-controller fake for malformed terminal identity."""

    patch_a: AgentPatchSnapshot
    patch_b: AgentPatchSnapshot
    terminal_patch_sha256: str | None
    issue_patch_ids: list[UUID] = field(default_factory=list)
    invalidated_patch_ids: list[UUID | None] = field(default_factory=list)
    _snapshot: PatchConfirmationSnapshot = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._snapshot = PatchConfirmationSnapshot(
            status=PatchConfirmationStatus.IDLE,
        )

    @property
    def snapshot(self) -> PatchConfirmationSnapshot:
        return self._snapshot

    async def issue(
        self,
        ui_session: object,
        patch_id: UUID,
        *,
        expected_plan_id: int,
        expected_revision: int,
    ) -> PatchConfirmationSnapshot:
        del ui_session
        assert expected_plan_id == PLAN_ID
        assert expected_revision == 1
        self.issue_patch_ids.append(patch_id)
        if patch_id == self.patch_a.patch_id:
            self._snapshot = PatchConfirmationSnapshot(
                status=PatchConfirmationStatus.FAILED,
                patch_id=self.patch_a.patch_id,
                patch_sha256=self.terminal_patch_sha256,
                daily_plan_id=PLAN_ID,
                expected_revision=1,
                error_code="write_failed",
            )
            return self._snapshot
        if patch_id == self.patch_b.patch_id:
            self._snapshot = PatchConfirmationSnapshot(
                status=PatchConfirmationStatus.PENDING,
                patch_id=self.patch_b.patch_id,
                patch_sha256=self.patch_b.patch_sha256,
                daily_plan_id=PLAN_ID,
                expected_revision=1,
                expires_at_utc=NOW,
                field_paths=tuple(
                    operation.field_path for operation in self.patch_b.operations
                ),
            )
            return self._snapshot
        raise AssertionError("unexpected patch issue")

    async def apply(self, ui_session: object) -> PatchConfirmationSnapshot:
        del ui_session
        raise AssertionError("this scenario never applies a confirmation")

    async def reconcile(self, ui_session: object) -> PatchConfirmationSnapshot:
        del ui_session
        raise AssertionError("this scenario never reconciles a confirmation")

    def invalidate(self) -> None:
        snapshot = self._snapshot
        self.invalidated_patch_ids.append(snapshot.patch_id)
        self._snapshot = PatchConfirmationSnapshot(
            status=PatchConfirmationStatus.STALE,
            patch_id=snapshot.patch_id,
            patch_sha256=snapshot.patch_sha256,
            daily_plan_id=snapshot.daily_plan_id,
            expected_revision=snapshot.expected_revision,
            error_code="target_mismatch",
        )

    async def disconnect(self) -> None:
        return None

    async def close(self) -> None:
        return None


def _agent_controller(*patches: PlanPatch) -> DailyPlanAgentController:
    return DailyPlanAgentController(
        coordinator=_MultiPatchCoordinator(tuple(patches)),  # type: ignore[arg-type]
        actor=TrustedActor(
            tenant_id=ACTOR_TENANT_ID,
            user_id=ACTOR_USER_ID,
        ),
    )


async def _press(button: _FakeElement) -> None:
    assert callable(button.on_click)
    result = button.on_click()
    assert inspect.isawaitable(result)
    await result


@pytest.mark.asyncio
async def test_second_patch_prepare_cannot_steal_pending_patch_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    confirmation_ui = __import__(
        "app.ui.components.agent_write_confirmation",
        fromlist=["DailyPlanPatchConfirmationPanel"],
    )
    flow_api = __import__(
        "app.service.agent.confirmation_flow",
        fromlist=["create_daily_plan_patch_confirmation_controller"],
    )
    patch_a = build_patch(
        operation_id=OPERATION_ID,
        turn_id=TURN_ID,
        after_goal="同一 turn 的草案 A",
    )
    patch_b = build_patch(
        operation_id=SECOND_OPERATION_ID,
        turn_id=TURN_ID,
        after_goal="同一 turn 的草案 B",
    )
    agent = _agent_controller(patch_a, patch_b)
    agent.scope_changed(PLAN_DATE)
    turn = await agent.run("同一 turn 生成 A/B 两份草案")
    patch_view_a, patch_view_b = turn.patches
    writer = _RecordingWriter()
    flow = flow_api.create_daily_plan_patch_confirmation_controller(
        agent_controller=agent,
        write_service=writer,
    )
    target = DailyPlanUiTarget(
        selection=DateSelection(generation=1, selected_date=PLAN_DATE),
        plan_id=PLAN_ID,
        revision=1,
        form_generation=0,
    )
    session = trusted_ui_session()
    applied: list[UUID | None] = []

    async def authorize() -> object:
        return session

    async def on_applied(snapshot: object, frozen_target: object) -> None:
        assert frozen_target == target
        applied.append(getattr(snapshot, "patch_id", None))

    fake_ui = _FakeUi()
    monkeypatch.setattr(confirmation_ui, "ui", fake_ui)
    panel = confirmation_ui.DailyPlanPatchConfirmationPanel(
        flow,
        authorize_confirmation=authorize,
        capture_target=lambda: target,
        is_current_target=lambda candidate: candidate == target,
        on_applied=on_applied,
    )

    panel.render_patch_actions(patch_view_a)
    view_a = fake_ui.latest_column()
    panel.render_patch_actions(patch_view_b)
    view_b = fake_ui.latest_column()
    await _press(fake_ui.latest_button("准备确认", within=view_a))
    apply_a = fake_ui.latest_button("确认采用", within=view_a)

    await _press(fake_ui.latest_button("准备确认", within=view_b))
    await _press(apply_a)

    assert writer.issue_patch_ids == [patch_a.patch_id]
    assert writer.apply_confirmation_ids == [CONFIRMATION_ID]
    assert applied == [patch_a.patch_id]
    assert flow.snapshot.patch_id == patch_a.patch_id
    assert flow.snapshot.status.value == "applied"


@pytest.mark.asyncio
async def test_reconcile_integrity_failure_keeps_every_patch_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    confirmation_ui = __import__(
        "app.ui.components.agent_write_confirmation",
        fromlist=["DailyPlanPatchConfirmationPanel"],
    )
    flow_api = __import__(
        "app.service.agent.confirmation_flow",
        fromlist=["create_daily_plan_patch_confirmation_controller"],
    )
    patch_a = build_patch(
        operation_id=OPERATION_ID,
        turn_id=TURN_ID,
        after_goal="对账完整性失败的草案 A",
    )
    patch_b = build_patch(
        operation_id=SECOND_OPERATION_ID,
        turn_id=TURN_ID,
        after_goal="必须继续阻断的草案 B",
    )
    agent = _agent_controller(patch_a, patch_b)
    agent.scope_changed(PLAN_DATE)
    turn = await agent.run("同一 turn 生成 A/B 两份草案")
    patch_view_a, patch_view_b = turn.patches
    writer = _RecordingWriter(
        apply_error_code="commit_outcome_unknown",
        reconcile_error_code="reconcile_integrity_failure",
    )
    flow = flow_api.create_daily_plan_patch_confirmation_controller(
        agent_controller=agent,
        write_service=writer,
    )
    target = DailyPlanUiTarget(
        selection=DateSelection(generation=1, selected_date=PLAN_DATE),
        plan_id=PLAN_ID,
        revision=1,
        form_generation=0,
    )
    session = trusted_ui_session()

    async def authorize() -> object:
        return session

    async def on_applied(_snapshot: object, _target: object) -> None:
        raise AssertionError("an integrity failure must never publish an apply")

    fake_ui = _FakeUi()
    monkeypatch.setattr(confirmation_ui, "ui", fake_ui)
    panel = confirmation_ui.DailyPlanPatchConfirmationPanel(
        flow,
        authorize_confirmation=authorize,
        capture_target=lambda: target,
        is_current_target=lambda candidate: candidate == target,
        on_applied=on_applied,
    )

    panel.render_patch_actions(patch_view_a)
    view_a = fake_ui.latest_column()
    panel.render_patch_actions(patch_view_b)
    view_b = fake_ui.latest_column()
    await _press(fake_ui.latest_button("准备确认", within=view_a))
    await _press(fake_ui.latest_button("确认采用", within=view_a))
    await _press(fake_ui.latest_button("人工对账", within=view_a))

    labels_a = fake_ui.active_label_texts(within=view_a)
    labels_b = fake_ui.active_label_texts(within=view_b)
    usable_prepare_b = fake_ui.active_buttons(
        "准备确认",
        within=view_b,
        enabled=True,
    )
    status_before_probe = flow.snapshot.status.value
    error_before_probe = flow.snapshot.error_code
    for button in usable_prepare_b:
        await _press(button)

    assert {
        "status_before_probe": status_before_probe,
        "error_before_probe": error_before_probe,
        "terminal_error_visible_on_a": any(
            "对账完整性检查失败" in label for label in labels_a
        ),
        "blocking_copy_visible_on_b": any(
            "人工核查" in label for label in labels_b
        ),
        "usable_prepare_count_on_b": len(usable_prepare_b),
        "issue_count_after_probe": len(writer.issue_patch_ids),
        "only_patch_a_issued": writer.issue_patch_ids == [patch_a.patch_id],
        "only_confirmation_reconciled": writer.reconcile_confirmation_ids
        == [CONFIRMATION_ID],
        "status_after_probe": flow.snapshot.status.value,
    } == {
        "status_before_probe": "failed",
        "error_before_probe": "reconcile_integrity_failure",
        "terminal_error_visible_on_a": True,
        "blocking_copy_visible_on_b": True,
        "usable_prepare_count_on_b": 0,
        "issue_count_after_probe": 1,
        "only_patch_a_issued": True,
        "only_confirmation_reconciled": True,
        "status_after_probe": "failed",
    }


@pytest.mark.asyncio
async def test_cancel_pending_patch_rerenders_all_current_patch_views(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    confirmation_ui = __import__(
        "app.ui.components.agent_write_confirmation",
        fromlist=["DailyPlanPatchConfirmationPanel"],
    )
    flow_api = __import__(
        "app.service.agent.confirmation_flow",
        fromlist=["create_daily_plan_patch_confirmation_controller"],
    )
    patch_a = build_patch(
        operation_id=OPERATION_ID,
        turn_id=TURN_ID,
        after_goal="待取消的草案 A",
    )
    patch_b = build_patch(
        operation_id=SECOND_OPERATION_ID,
        turn_id=TURN_ID,
        after_goal="取消后可独立确认的草案 B",
    )
    agent = _agent_controller(patch_a, patch_b)
    agent.scope_changed(PLAN_DATE)
    turn = await agent.run("同一 turn 生成 A/B 两份草案")
    patch_view_a, patch_view_b = turn.patches
    writer = _RecordingWriter()
    flow = flow_api.create_daily_plan_patch_confirmation_controller(
        agent_controller=agent,
        write_service=writer,
    )
    target = DailyPlanUiTarget(
        selection=DateSelection(generation=1, selected_date=PLAN_DATE),
        plan_id=PLAN_ID,
        revision=1,
        form_generation=0,
    )
    session = trusted_ui_session()

    async def authorize() -> object:
        return session

    async def on_applied(_snapshot: object, _target: object) -> None:
        raise AssertionError("this scenario only prepares confirmations")

    fake_ui = _FakeUi()
    monkeypatch.setattr(confirmation_ui, "ui", fake_ui)
    panel = confirmation_ui.DailyPlanPatchConfirmationPanel(
        flow,
        authorize_confirmation=authorize,
        capture_target=lambda: target,
        is_current_target=lambda candidate: candidate == target,
        on_applied=on_applied,
    )

    panel.render_patch_actions(patch_view_a)
    view_a = fake_ui.latest_column()
    panel.render_patch_actions(patch_view_b)
    view_b = fake_ui.latest_column()
    await _press(fake_ui.latest_button("准备确认", within=view_a))
    occupied_before_cancel = any(
        "另一份草案正在占用" in label
        for label in fake_ui.active_label_texts(within=view_b)
    )

    cancel_a = fake_ui.latest_button("取消确认", within=view_a)
    assert callable(cancel_a.on_click)
    assert cancel_a.on_click() is None

    labels_a_after_cancel = fake_ui.active_label_texts(within=view_a)
    labels_b_after_cancel = fake_ui.active_label_texts(within=view_b)
    usable_prepare_b = fake_ui.active_buttons(
        "准备确认",
        within=view_b,
        enabled=True,
    )
    stale_occupied_controls_b = fake_ui.active_buttons(
        "准备确认",
        within=view_b,
        enabled=False,
    )
    for button in usable_prepare_b:
        await _press(button)

    assert {
        "occupied_before_cancel": occupied_before_cancel,
        "cancelled_copy_visible_on_a": any(
            "已取消这一份草案的确认" in label
            for label in labels_a_after_cancel
        ),
        "occupied_copy_after_cancel": any(
            "另一份草案正在占用" in label for label in labels_b_after_cancel
        ),
        "usable_prepare_count_on_b": len(usable_prepare_b),
        "stale_occupied_control_count_on_b": len(stale_occupied_controls_b),
        "issue_count_after_b_prepare": len(writer.issue_patch_ids),
        "patches_issued_in_order": writer.issue_patch_ids
        == [patch_a.patch_id, patch_b.patch_id],
    } == {
        "occupied_before_cancel": True,
        "cancelled_copy_visible_on_a": True,
        "occupied_copy_after_cancel": False,
        "usable_prepare_count_on_b": 1,
        "stale_occupied_control_count_on_b": 0,
        "issue_count_after_b_prepare": 2,
        "patches_issued_in_order": True,
    }


@pytest.mark.asyncio
async def test_cancelled_patch_stays_closed_after_another_patch_is_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    confirmation_ui = __import__(
        "app.ui.components.agent_write_confirmation",
        fromlist=["DailyPlanPatchConfirmationPanel"],
    )
    flow_api = __import__(
        "app.service.agent.confirmation_flow",
        fromlist=["create_daily_plan_patch_confirmation_controller"],
    )
    patch_a = build_patch(
        operation_id=OPERATION_ID,
        turn_id=TURN_ID,
        after_goal="取消后必须保持关闭的草案 A",
    )
    patch_b = build_patch(
        operation_id=SECOND_OPERATION_ID,
        turn_id=TURN_ID,
        after_goal="随后准备并取消的草案 B",
    )
    agent = _agent_controller(patch_a, patch_b)
    agent.scope_changed(PLAN_DATE)
    turn = await agent.run("同一 generation 依次取消 A/B 两份草案")
    patch_view_a, patch_view_b = turn.patches
    writer = _RecordingWriter()
    flow = flow_api.create_daily_plan_patch_confirmation_controller(
        agent_controller=agent,
        write_service=writer,
    )
    target = DailyPlanUiTarget(
        selection=DateSelection(generation=1, selected_date=PLAN_DATE),
        plan_id=PLAN_ID,
        revision=1,
        form_generation=0,
    )
    session = trusted_ui_session()

    async def authorize() -> object:
        return session

    async def on_applied(_snapshot: object, _target: object) -> None:
        raise AssertionError("this scenario only prepares and cancels confirmations")

    fake_ui = _FakeUi()
    monkeypatch.setattr(confirmation_ui, "ui", fake_ui)
    panel = confirmation_ui.DailyPlanPatchConfirmationPanel(
        flow,
        authorize_confirmation=authorize,
        capture_target=lambda: target,
        is_current_target=lambda candidate: candidate == target,
        on_applied=on_applied,
    )

    panel.render_patch_actions(patch_view_a)
    view_a = fake_ui.latest_column()
    panel.render_patch_actions(patch_view_b)
    view_b = fake_ui.latest_column()
    await _press(fake_ui.latest_button("准备确认", within=view_a))
    cancel_a = fake_ui.latest_button("取消确认", within=view_a)
    assert callable(cancel_a.on_click)
    assert cancel_a.on_click() is None

    await _press(fake_ui.latest_button("准备确认", within=view_b))
    cancel_b = fake_ui.latest_button("取消确认", within=view_b)
    assert callable(cancel_b.on_click)
    assert cancel_b.on_click() is None

    labels_a_after_b_cancel = fake_ui.active_label_texts(within=view_a)
    usable_prepare_a = fake_ui.active_buttons(
        "准备确认",
        within=view_a,
        enabled=True,
    )
    for button in usable_prepare_a:
        await _press(button)

    assert {
        "known_closed_copy_visible_on_a": any(
            "已取消" in label or "已关闭" in label
            for label in labels_a_after_b_cancel
        ),
        "must_regenerate_copy_visible_on_a": any(
            "重新生成草案" in label for label in labels_a_after_b_cancel
        ),
        "usable_prepare_count_on_a": len(usable_prepare_a),
        "patches_issued_after_old_a_probe": writer.issue_patch_ids,
    } == {
        "known_closed_copy_visible_on_a": True,
        "must_regenerate_copy_visible_on_a": True,
        "usable_prepare_count_on_a": 0,
        "patches_issued_after_old_a_probe": [patch_a.patch_id, patch_b.patch_id],
    }


@pytest.mark.parametrize(
    "terminal_patch_sha256",
    [
        pytest.param(None, id="missing_hash"),
        pytest.param("0" * 64, id="wrong_hash"),
    ],
)
@pytest.mark.asyncio
async def test_identity_invalid_terminal_patch_stays_closed_after_next_owner(
    monkeypatch: pytest.MonkeyPatch,
    terminal_patch_sha256: str | None,
) -> None:
    confirmation_ui = __import__(
        "app.ui.components.agent_write_confirmation",
        fromlist=["DailyPlanPatchConfirmationPanel"],
    )
    patch_a = build_patch(
        operation_id=OPERATION_ID,
        turn_id=TURN_ID,
        after_goal="身份异常后必须保持关闭的草案 A",
    )
    patch_b = build_patch(
        operation_id=SECOND_OPERATION_ID,
        turn_id=TURN_ID,
        after_goal="随后成为 owner 并取消的草案 B",
    )
    agent = _agent_controller(patch_a, patch_b)
    agent.scope_changed(PLAN_DATE)
    turn = await agent.run("同一 generation 依次处理 A/B 两份草案")
    patch_view_a, patch_view_b = turn.patches
    controller = _IdentityTerminalController(
        patch_a=patch_view_a,
        patch_b=patch_view_b,
        terminal_patch_sha256=terminal_patch_sha256,
    )
    target = DailyPlanUiTarget(
        selection=DateSelection(generation=1, selected_date=PLAN_DATE),
        plan_id=PLAN_ID,
        revision=1,
        form_generation=0,
    )
    session = trusted_ui_session()

    async def authorize() -> object:
        return session

    async def on_applied(_snapshot: object, _target: object) -> None:
        raise AssertionError("this scenario never applies a confirmation")

    fake_ui = _FakeUi()
    monkeypatch.setattr(confirmation_ui, "ui", fake_ui)
    panel = confirmation_ui.DailyPlanPatchConfirmationPanel(
        controller,
        authorize_confirmation=authorize,
        capture_target=lambda: target,
        is_current_target=lambda candidate: candidate == target,
        on_applied=on_applied,
    )

    panel.render_patch_actions(patch_view_a)
    view_a = fake_ui.latest_column()
    panel.render_patch_actions(patch_view_b)
    view_b = fake_ui.latest_column()
    await _press(fake_ui.latest_button("准备确认", within=view_a))
    labels_a_after_identity_failure = fake_ui.active_label_texts(within=view_a)
    usable_prepare_a_after_failure = fake_ui.active_buttons(
        "准备确认",
        within=view_a,
        enabled=True,
    )

    await _press(fake_ui.latest_button("准备确认", within=view_b))
    b_became_owner = (
        controller.snapshot.status is PatchConfirmationStatus.PENDING
        and controller.snapshot.patch_id == patch_b.patch_id
        and controller.snapshot.patch_sha256 == patch_b.canonical_sha256
    )
    cancel_b = fake_ui.latest_button("取消确认", within=view_b)
    assert callable(cancel_b.on_click)
    assert cancel_b.on_click() is None

    labels_a_after_b_terminal = fake_ui.active_label_texts(within=view_a)
    labels_b_after_cancel = fake_ui.active_label_texts(within=view_b)
    usable_prepare_a_after_b_terminal = fake_ui.active_buttons(
        "准备确认",
        within=view_a,
        enabled=True,
    )
    for button in usable_prepare_a_after_b_terminal:
        await _press(button)

    assert {
        "identity_failure_visible_on_a": any(
            "草案身份校验失败" in label
            for label in labels_a_after_identity_failure
        ),
        "usable_prepare_count_on_a_after_failure": len(
            usable_prepare_a_after_failure
        ),
        "b_became_owner": b_became_owner,
        "b_cancelled_copy_visible": any(
            "已取消这一份草案" in label for label in labels_b_after_cancel
        ),
        "a_still_closed_after_b_terminal": any(
            "关闭" in label for label in labels_a_after_b_terminal
        ),
        "a_requires_regeneration": any(
            "重新生成草案" in label for label in labels_a_after_b_terminal
        ),
        "usable_prepare_count_on_a_after_b_terminal": len(
            usable_prepare_a_after_b_terminal
        ),
        "only_b_confirmation_invalidated": controller.invalidated_patch_ids
        == [patch_b.patch_id],
        "patches_issued_without_a_b_a": controller.issue_patch_ids,
    } == {
        "identity_failure_visible_on_a": True,
        "usable_prepare_count_on_a_after_failure": 0,
        "b_became_owner": True,
        "b_cancelled_copy_visible": True,
        "a_still_closed_after_b_terminal": True,
        "a_requires_regeneration": True,
        "usable_prepare_count_on_a_after_b_terminal": 0,
        "only_b_confirmation_invalidated": True,
        "patches_issued_without_a_b_a": [patch_a.patch_id, patch_b.patch_id],
    }


def test_agent_notice_distinguishes_read_only_from_explicit_local_adoption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft_ui = __import__(
        "app.ui.components.agent_draft",
        fromlist=["DailyPlanAgentPanel"],
    )

    def render_notice(patch_actions: object | None) -> tuple[str, ...]:
        fake_ui = _FakeUi()
        monkeypatch.setattr(draft_ui, "ui", fake_ui)
        monkeypatch.setattr(
            draft_ui,
            "context",
            SimpleNamespace(client=_FakeClient()),
        )
        draft_ui.DailyPlanAgentPanel(
            _agent_controller(),
            patch_actions=patch_actions,
        )
        return fake_ui.active_label_texts()

    read_only_labels = render_notice(None)
    adoption_labels = render_notice(_NoopPatchActions())
    absolute_read_only_notice = "仅生成建议，不会保存或修改当前计划。"

    assert absolute_read_only_notice in read_only_labels
    assert absolute_read_only_notice not in adoption_labels
    assert any(
        all(
            fragment in label
            for fragment in ("模型", "建议", "显式确认", "本地", "写入")
        )
        for label in adoption_labels
    )
