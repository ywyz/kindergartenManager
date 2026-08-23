"""F005 public RED tests for the closed, canonical ``PlanPatch`` seam."""

from dataclasses import fields, replace
from datetime import date, datetime, timedelta, timezone
from importlib import import_module
import re
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.daily_plan import DailyPlan
from app.service.agent.contracts import (
    FOUNDATION_ALLOWED_PERMISSIONS,
    AgentContext,
    DailyPlanProjection,
    DailyPlanScope,
    PlanSection,
    TrustedActor,
)


PLAN_SECTION_PATHS = (
    "activity_goal",
    "activity_prep",
    "activity_key",
    "activity_difficult",
    "activity_process_original",
    "activity_process_adapted",
    "morning_activity",
    "indoor_area",
    "outdoor_activity",
    "morning_talk_topic",
    "morning_talk_questions",
    "daily_reflection",
)
OPERATION_ID = UUID("11111111-1111-4111-8111-111111111111")
TURN_ID = UUID("22222222-2222-4222-8222-222222222222")
PLAN_DATE = date(2026, 9, 7)
BASE_FINGERPRINT = "a" * 64


def _patch_module():
    return import_module("app.service.agent.patch")


def _context(*, plan_id: int = 7, truncated_path: str | None = None) -> AgentContext:
    content_by_path = {
        "activity_goal": "认识秋天",
        "activity_prep": "",
        "daily_reflection": "孩子们主动观察了落叶",
    }
    sections = tuple(
        PlanSection(
            field_path=field_path,
            content=content_by_path.get(field_path, ""),
            truncated=field_path == truncated_path,
        )
        for field_path in PLAN_SECTION_PATHS
    )
    projection = DailyPlanProjection(
        plan_id=plan_id,
        plan_date=PLAN_DATE,
        week_number=2,
        weekday_cn="周一",
        grade="大班",
        class_name="星星班",
        sections=sections,
        updated_at_utc=datetime(2026, 9, 6, 8, 30, tzinfo=timezone.utc),
        content_sha256="b" * 64,
    )
    created_at = datetime(2026, 9, 6, 9, 0, tzinfo=timezone.utc)
    return AgentContext(
        context_id=UUID("33333333-3333-4333-8333-333333333333"),
        operation_id=OPERATION_ID,
        turn_id=TURN_ID,
        created_at_utc=created_at,
        expires_at_utc=created_at + timedelta(minutes=5),
        locale="zh-CN",
        actor=TrustedActor(tenant_id=1, user_id=10),
        active_scope=DailyPlanScope(daily_plan_id=plan_id),
        facts=(projection,),
        base_fingerprint=BASE_FINGERPRINT,
        allowed_permissions=FOUNDATION_ALLOWED_PERMISSIONS,
    )


def _proposal(*, plan_id: int = 7):
    patch = _patch_module()
    return patch.DraftPatchProposal(
        operation_id=OPERATION_ID,
        turn_id=TURN_ID,
        tool_name="daily_plan.draft_section_patch",
        target=patch.PlanPatchTarget(daily_plan_id=plan_id, plan_date=PLAN_DATE),
        base_fingerprint=BASE_FINGERPRINT,
        operations=(
            patch.DraftPatchOperation(
                field_path="activity_prep",
                before_value="",
                after_value="准备落叶",
            ),
            patch.DraftPatchOperation(
                field_path="activity_goal",
                before_value="认识秋天",
                after_value="探索秋天",
            ),
        ),
        warnings=("请教师复核",),
    )


def _assert_rejected(code: str, context: AgentContext, proposal: object) -> None:
    patch = _patch_module()
    with pytest.raises(patch.PlanPatchRejected) as error:
        patch.build_plan_patch(context=context, proposal=proposal)
    assert error.value.code == code
    assert str(error.value) == code


def test_patch_paths_and_input_shape_are_closed_and_prefix_free():
    patch = _patch_module()

    assert patch.ALLOWED_PLAN_PATCH_PATHS == PLAN_SECTION_PATHS
    assert {field.name for field in fields(patch.DraftPatchOperation)} == {
        "field_path",
        "before_value",
        "after_value",
    }
    assert all(
        not left.startswith(f"{right}.")
        for left in patch.ALLOWED_PLAN_PATCH_PATHS
        for right in patch.ALLOWED_PLAN_PATCH_PATHS
        if left != right
    )
    with pytest.raises(TypeError):
        patch.DraftPatchOperation(
            op="replace",
            path="/activity_goal",
            value="通用 JSON Patch 不得进入",
        )


def test_patch_binds_context_and_has_stable_canonical_sha256():
    patch = _patch_module()
    context = _context()
    first = patch.build_plan_patch(context=context, proposal=_proposal())
    reordered = replace(
        _proposal(),
        operations=tuple(reversed(_proposal().operations)),
    )
    second = patch.build_plan_patch(context=context, proposal=reordered)

    assert first.schema_version == 1
    assert first.operation_id == OPERATION_ID
    assert first.turn_id == TURN_ID
    assert first.tool_name == "daily_plan.draft_section_patch"
    assert first.target == patch.PlanPatchTarget(daily_plan_id=7, plan_date=PLAN_DATE)
    assert first.base_fingerprint == BASE_FINGERPRINT
    assert tuple(operation.field_path for operation in first.operations) == (
        "activity_goal",
        "activity_prep",
    )
    assert first.operations[0].before_sha256 == (
        "2ed65a43ace2dbd28de93e2c687e26443514d2878a43e5e3e0831413ce3c9eb7"
    )
    assert first.operations[1].before_sha256 == (
        "12ae32cb1ec02d01eda3581b127c1fee3b0dc53572ed6baf239721a03d82e126"
    )
    assert first.canonical_sha256 == (
        "89f04dacd8f420610b55b72fc66701db0dbb61d4141b89cb0f15383eb9792188"
    )
    assert re.fullmatch(r"[0-9a-f]{64}", first.canonical_sha256)
    assert second.canonical_sha256 == first.canonical_sha256
    assert second.patch_id != first.patch_id
    assert "认识秋天" not in repr(first)
    assert "探索秋天" not in repr(first)


@pytest.mark.parametrize(
    ("change", "code"),
    (
        (
            {"operation_id": UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")},
            "operation_mismatch",
        ),
        ({"turn_id": UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")}, "turn_mismatch"),
        (
            {
                "target": lambda patch: patch.PlanPatchTarget(
                    daily_plan_id=8,
                    plan_date=PLAN_DATE,
                )
            },
            "target_mismatch",
        ),
        ({"base_fingerprint": "c" * 64}, "fingerprint_mismatch"),
    ),
)
def test_patch_rejects_incomplete_context_binding(change: dict, code: str):
    patch = _patch_module()
    normalized = {
        key: value(patch) if callable(value) else value for key, value in change.items()
    }
    _assert_rejected(code, _context(), replace(_proposal(), **normalized))


def test_patch_rejects_duplicate_overlap_and_tool_path_expansion():
    context = _context()
    operation = _proposal().operations[1]

    _assert_rejected(
        "duplicate_field_path",
        context,
        replace(_proposal(), operations=(operation, operation)),
    )
    _assert_rejected(
        "overlapping_field_path",
        context,
        replace(
            _proposal(),
            operations=(
                operation,
                replace(operation, field_path="activity_goal.detail"),
            ),
        ),
    )
    _assert_rejected(
        "field_path_not_allowed",
        context,
        replace(
            _proposal(),
            operations=(replace(operation, field_path="/activity_goal"),),
        ),
    )
    _assert_rejected(
        "field_path_not_allowed_for_tool",
        context,
        replace(
            _proposal(),
            tool_name="daily_plan.draft_reflection_patch",
            operations=(operation,),
        ),
    )


@pytest.mark.parametrize(
    ("operation", "context", "code"),
    (
        ({"before_value": 1}, None, "before_value_invalid"),
        ({"after_value": 1}, None, "after_value_invalid"),
        ({"before_value": "前" * 4097}, None, "before_value_too_large"),
        ({"after_value": "后" * 4097}, None, "after_value_too_large"),
        ({"before_value": "伪造旧值"}, None, "before_value_mismatch"),
        ({}, "activity_goal", "before_value_unavailable"),
    ),
)
def test_before_and_after_are_validated_independently(
    operation: dict,
    context: str | None,
    code: str,
):
    proposal = _proposal()
    changed_operation = replace(proposal.operations[1], **operation)
    _assert_rejected(
        code,
        _context(truncated_path=context),
        replace(proposal, operations=(changed_operation,)),
    )


async def _seed_plan(session: AsyncSession) -> DailyPlan:
    plan = DailyPlan(
        tenant_id=1,
        user_id=10,
        plan_date=PLAN_DATE,
        week_number=2,
        weekday_cn="周一",
        grade="大班",
        class_name="星星班",
        activity_goal="认识秋天",
        activity_prep="",
        daily_reflection="孩子们主动观察了落叶",
        updated_at=datetime(2026, 9, 6, 8, 30, tzinfo=timezone.utc),
    )
    session.add(plan)
    await session.commit()
    return plan


def _ui_body() -> dict[str, str]:
    return {
        "activity_goal": "认识秋天",
        "activity_prep": "",
        "daily_reflection": "孩子们主动观察了落叶",
    }


@pytest.mark.asyncio
async def test_successful_patch_construction_changes_neither_database_nor_ui_body(
    async_session: AsyncSession,
):
    patch = _patch_module()
    plan = await _seed_plan(async_session)
    ui_body = _ui_body()
    before_ui = dict(ui_body)
    before_database = (plan.activity_goal, plan.activity_prep, plan.updated_at)

    result = patch.build_plan_patch(
        context=_context(plan_id=plan.id),
        proposal=_proposal(plan_id=plan.id),
    )

    await async_session.refresh(plan)
    assert result.operations[0].after_value == "探索秋天"
    assert ui_body == before_ui
    assert (plan.activity_goal, plan.activity_prep, plan.updated_at) == before_database
    assert not async_session.new
    assert not async_session.dirty
    assert not async_session.deleted


@pytest.mark.asyncio
async def test_rejected_patch_changes_neither_database_nor_ui_body(
    async_session: AsyncSession,
):
    plan = await _seed_plan(async_session)
    ui_body = _ui_body()
    before_ui = dict(ui_body)
    before_database = (plan.activity_goal, plan.activity_prep, plan.updated_at)
    invalid = replace(
        _proposal(plan_id=plan.id),
        base_fingerprint="c" * 64,
    )

    _assert_rejected("fingerprint_mismatch", _context(plan_id=plan.id), invalid)

    await async_session.refresh(plan)
    assert ui_body == before_ui
    assert (plan.activity_goal, plan.activity_prep, plan.updated_at) == before_database
    assert not async_session.new
    assert not async_session.dirty
    assert not async_session.deleted
