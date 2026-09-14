"""WP-B application snapshots only; Provider and patch paths stay closed."""

import hashlib
import json

import pytest
from conftest import PLAN_ID, MutableClock, build_patch, trusted_ui_session
from sqlalchemy import select

from app.core.models.agent_write_evidence import DailyPlanOperationVersion
from app.core.models.daily_plan import DailyPlan
from app.service.agent import confirmed_write as api
from app.service.agent.canonical import canonical_json


async def test_new_snapshot_includes_name_and_pending_name_edit_stales(
    migrated_write_database,
):
    db = migrated_write_database
    service = api.ConfirmedDailyPlanWriteService(
        session_factory=db.session_factory, clock=MutableClock()
    )
    actor = trusted_ui_session()
    pending = await service.issue_confirmation(
        actor, build_patch(), expected_revision=1
    )
    async with db.session_factory() as s:
        plan = await s.get(DailyPlan, PLAN_ID)
        plan.activity_name = "秋叶拼画"
        await s.commit()
    with pytest.raises(api.ConfirmedWriteRejected, match="revision_mismatch"):
        await service.apply(actor, pending.confirmation_id)
    pending = await service.issue_confirmation(
        actor, build_patch(), expected_revision=2
    )
    result = await service.apply(actor, pending.confirmation_id)
    async with db.session_factory() as s:
        v = await s.get(DailyPlanOperationVersion, result.before_version_id)
        body = json.loads(v.snapshot_json)
        assert body["snapshot_schema_version"] == 2
        assert body["activity_name"] == "秋叶拼画"
    assert await service.reconcile(actor, pending.confirmation_id) == result


async def test_v1_immutable_evidence_still_reconciles(
    migrated_write_database, monkeypatch
):
    db = migrated_write_database
    service = api.ConfirmedDailyPlanWriteService(
        session_factory=db.session_factory, clock=MutableClock()
    )
    original = api._daily_plan_snapshot

    def historical_v1(plan):
        body = json.loads(original(plan)[0])
        body.pop("snapshot_schema_version", None)
        body.pop("activity_name", None)
        data = canonical_json(body)
        return data, hashlib.sha256(data.encode()).hexdigest()

    # Emulate the historical writer at its serialization boundary, before immutable INSERT.
    with monkeypatch.context() as m:
        m.setattr(api, "_daily_plan_snapshot", historical_v1)
        actor = trusted_ui_session()
        pending = await service.issue_confirmation(
            actor, build_patch(), expected_revision=1
        )
        result = await service.apply(actor, pending.confirmation_id)
    async with db.session_factory() as s:
        before = (await s.scalars(select(DailyPlanOperationVersion))).one()
        evidence = (before.snapshot_json, before.snapshot_sha256)
    assert await service.reconcile(actor, pending.confirmation_id) == result
    async with db.session_factory() as s:
        after = (await s.scalars(select(DailyPlanOperationVersion))).one()
        assert (after.snapshot_json, after.snapshot_sha256) == evidence


@pytest.mark.parametrize("schema", [1, 3, True, "2"])
async def test_reconcile_rejects_unknown_snapshot_version(
    migrated_write_database, monkeypatch, schema
):
    db = migrated_write_database
    service = api.ConfirmedDailyPlanWriteService(
        session_factory=db.session_factory, clock=MutableClock()
    )
    original = api._daily_plan_snapshot

    def invalid_snapshot(plan):
        body = json.loads(original(plan)[0])
        body["snapshot_schema_version"] = schema
        data = canonical_json(body)
        return data, hashlib.sha256(data.encode()).hexdigest()

    with monkeypatch.context() as m:
        m.setattr(api, "_daily_plan_snapshot", invalid_snapshot)
        actor = trusted_ui_session()
        pending = await service.issue_confirmation(
            actor, build_patch(), expected_revision=1
        )
        await service.apply(actor, pending.confirmation_id)
    with pytest.raises(api.ConfirmedWriteRejected, match="reconcile_integrity_failure"):
        await service.reconcile(actor, pending.confirmation_id)


def test_name_is_not_a_provider_or_patch_path():
    from app.service.agent.contracts import Permission
    from app.service.agent.patch import ALLOWED_PLAN_PATCH_PATHS
    from app.service.agent.registry import build_foundation_registry

    assert frozenset(ALLOWED_PLAN_PATCH_PATHS) == frozenset(
        {
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
        }
    )
    descriptors = build_foundation_registry().descriptors()
    assert sum(d.permission is Permission.READ for d in descriptors) == 4
    assert sum(d.permission is Permission.DRAFT for d in descriptors) == 2
    for d in descriptors:
        assert "activity_name" not in d.input_schema.operation_paths
