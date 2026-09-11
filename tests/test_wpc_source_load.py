"""Source-child/body consistency checks through the real shared-week load seam."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import insert, select, update

from app.repository.shared_weekly_repository import AUDIT, ROOT, SOURCE, VERSION
from app.repository.source_mapping_repository import DAILY, EVENT
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.body_contracts import (
    CollaborationDay,
    SourceSnapshot,
    TargetPath,
    WeeklyCollaborationDraft,
    import_value_hash,
)
from app.service.shared_weekly.mapping_contracts import MappingTarget
from app.service.shared_weekly.people_contracts import People
from app.service.shared_weekly.root_contracts import WeeklyThemeDraft, payload_hash
from tests.test_wpc_identity import world as _identity_world
from tests.test_wpc_mapping import setup

world = _identity_world
WEEK = tuple(date(2026, 9, day) for day in range(7, 12))


async def _legal_sources(world):
    mapping, target, roots, scope, _member = await setup(world)
    preview = await mapping.preview(world[2][2], target)
    await mapping.confirm(
        world[2][2], preview.candidate_id, confirmed=True, operation_id=uuid4()
    )

    async with world[0]() as session:
        result = await session.execute(
            insert(DAILY).values(
                tenant_id=11,
                user_id=3,
                plan_date=date(2026, 9, 9),
                week_number=2,
                weekday_cn="周三",
                grade="中班",
                class_name="任意别名",
                activity_name="活动B",
                morning_talk_topic="晨谈B",
                daily_reflection="PRIVATE",
            )
        )
        second_id = result.inserted_primary_key[0]
        await session.commit()
    second_target = MappingTarget(
        second_id, target.class_instance_id, target.semester_id
    )
    preview = await mapping.preview(world[2][2], second_target)
    await mapping.confirm(
        world[2][2], preview.candidate_id, confirmed=True, operation_id=uuid4()
    )

    async with world[0]() as session:
        events = (
            (
                await session.execute(
                    select(EVENT)
                    .where(EVENT.c.daily_plan_id.in_((target.daily_plan_id, second_id)))
                    .order_by(EVENT.c.daily_plan_id, EVENT.c.revision)
                )
            )
            .mappings()
            .all()
        )
    by_source = {row["daily_plan_id"]: row for row in events}
    values = {target.daily_plan_id: "活动", second_id: "活动B"}
    snapshots = {}
    for source_id, event in by_source.items():
        value = values[source_id]
        snapshots[source_id] = SourceSnapshot(
            source_id=source_id,
            user_id=event["source_user_id"],
            day=event["source_date"],
            revision=event["source_revision"],
            mapping_id=event["id"],
            mapping_revision=event["revision"],
            source_field="activity_name",
            target=TargetPath(event["source_date"], "activity_name"),
            imported_value=value,
            imported_hash=import_value_hash(value),
            adopted_hash=import_value_hash(value),
            provenance="imported",
        )
    days = tuple(
        CollaborationDay(
            day=item,
            morning_talk_topic="",
            morning_talk_questions="",
            activity_name="活动" if item == date(2026, 9, 9) else "",
            outdoor_activity="",
            indoor_area="",
        )
        for item in WEEK
    )
    return roots, scope, target.daily_plan_id, second_id, snapshots, days


def _source_row(snapshot, version_id):
    return {
        "tenant_id": 11,
        "version_id": version_id,
        "source_id": snapshot.source_id,
        "source_user_id": snapshot.user_id,
        "source_date": snapshot.day,
        "source_revision": snapshot.revision,
        "mapping_id": snapshot.mapping_id,
        "mapping_revision": snapshot.mapping_revision,
        "source_field": snapshot.source_field,
        "target_path": snapshot.target.serialize(),
        "imported_value": snapshot.imported_value,
        "imported_hash": snapshot.imported_hash,
        "adopted_hash": snapshot.adopted_hash,
        "provenance": snapshot.provenance,
    }


async def _publish_native_next_version(world, plan_id, body, children):
    """Publish a trigger-valid next version using only direct Core DML."""

    async with world[0]() as session:
        root = (
            (await session.execute(select(ROOT).where(ROOT.c.id == plan_id)))
            .mappings()
            .one()
        )
        old_version = (
            (
                await session.execute(
                    select(VERSION).where(VERSION.c.id == root["current_version"])
                )
            )
            .mappings()
            .one()
        )
        old_audit = (
            (
                await session.execute(
                    select(AUDIT)
                    .where(AUDIT.c.version_id == old_version["id"])
                    .order_by(AUDIT.c.id)
                )
            )
            .mappings()
            .first()
        )
        assert old_audit is not None

        body_json = body.serialize()
        operation_id = str(uuid4())
        version_values = dict(old_version)
        version_values.pop("id")
        version_values.update(
            version=root["revision"] + 1,
            predecessor=root["current_version"],
            operation_id=operation_id,
            body_json=body_json,
            payload_sha256=payload_hash(body_json, old_version["facts_json"]),
        )
        version_id = (
            await session.execute(insert(VERSION).values(**version_values))
        ).inserted_primary_key[0]
        for snapshot in children:
            await session.execute(
                insert(SOURCE).values(**_source_row(snapshot, version_id))
            )

        audit_values = dict(old_audit)
        audit_values.pop("id")
        audit_values.update(
            version_id=version_id,
            revision=root["revision"] + 1,
            operation_id=operation_id,
            action="save",
            outcome="saved",
        )
        await session.execute(insert(AUDIT).values(**audit_values))
        result = await session.execute(
            update(ROOT)
            .where(ROOT.c.id == plan_id, ROOT.c.revision == root["revision"])
            .values(current_version=version_id, revision=root["revision"] + 1)
        )
        assert result.rowcount == 1
        await session.commit()


@pytest.mark.parametrize(
    "case",
    [
        "v2_body_missing_children",
        "v2_empty_body_with_child",
        "v2_body_with_different_child",
        "v1_body_with_child",
    ],
)
async def test_load_rejects_source_body_children_mismatch(world, case):
    roots, scope, source_a_id, source_b_id, snapshots, days = await _legal_sources(
        world
    )
    created = await roots[3].create(
        world[2][3], scope, WeeklyThemeDraft("base"), uuid4()
    )
    source_a = snapshots[source_a_id]
    source_b = snapshots[source_b_id]
    v2_a = WeeklyCollaborationDraft("v2", People(), days, (source_a,))
    v2_empty = WeeklyCollaborationDraft("v2", People(), days, ())
    if case == "v2_body_missing_children":
        body, children = v2_a, ()
    elif case == "v2_empty_body_with_child":
        body, children = v2_empty, (source_a,)
    elif case == "v2_body_with_different_child":
        body, children = v2_a, (source_b,)
    else:
        body, children = WeeklyThemeDraft("legacy"), (source_a,)

    await _publish_native_next_version(world, created.plan.plan_id, body, children)
    with pytest.raises(IdentityRejected, match="content_invalid"):
        await roots[3].load(world[2][3], created.plan.plan_id)
