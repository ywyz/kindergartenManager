"""Stable RED for the first fixed-SHA W007 Spec Review findings."""

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
    PendingPlanPatchConfirmation,
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
        del ui_session, confirmation_id
        raise AssertionError("reconcile must not run in this scenario")


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
        return None

    def disable(self) -> None:
        return None

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

    def active_label_texts(self) -> tuple[str, ...]:
        return tuple(
            element.text
            for element in self.elements
            if element.active
            and element.kind == "label"
            and type(element.text) is str
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
