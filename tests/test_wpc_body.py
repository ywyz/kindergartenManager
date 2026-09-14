"""Closed weekly-collaboration.v2 body contract checks."""

import json
from dataclasses import replace
from datetime import date
from hashlib import sha256
from uuid import uuid4

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.models.academic_identity import TABLES as ID_TABLES
from app.core.models.daily_plan import DailyPlan
from app.core.models.source_mapping import TABLES as MAPPING_TABLES
from app.core.models.weekly_sources import TABLES as SOURCE_TABLES
from app.repository.daily_plan_repository import delete_daily_plan
from app.repository.source_mapping_repository import DAILY
from app.service.academic_identity.contracts import (
    ClassInput,
    IdentityRejected,
    IdentityStamp,
)
from app.service.shared_weekly.body_contracts import (
    CollaborationDay,
    SourceSnapshot,
    TargetPath,
    WeeklyCollaborationDraft,
    begin_edit,
    convert,
    import_value_hash,
    parse_body,
)
from app.service.shared_weekly.contracts import SharedWeekScope, TeachingWeekFacts
from app.service.shared_weekly.mapping_application import SourceMappingApplication
from app.service.shared_weekly.mapping_contracts import MappingTarget
from app.service.shared_weekly.people_contracts import People
from app.service.shared_weekly.root_application import SharedWeeklyApplication
from app.service.shared_weekly.root_contracts import WeeklyThemeDraft
from tests.test_wpc_identity import assignment
from tests.test_wpc_identity import world as _identity_world
from tests.test_wpc_shared_root import ready
from tests.test_wpc_sources import sources_ready

world = _identity_world

DATES = tuple(date(2026, 9, 7 + index) for index in range(5))


def _draft(*, source_value: str = "晨谈") -> WeeklyCollaborationDraft:
    days = tuple(
        CollaborationDay(day, source_value if index == 0 else "", "", "", "", "")
        for index, day in enumerate(DATES)
    )
    target = TargetPath(DATES[0], "morning_talk_topic")
    source = SourceSnapshot(
        source_id=9,
        user_id=3,
        day=DATES[0],
        revision=2,
        mapping_id=11,
        mapping_revision=1,
        source_field="morning_talk_topic",
        target=target,
        imported_value=source_value,
        imported_hash=import_value_hash(source_value),
        adopted_hash=import_value_hash(source_value),
        provenance="imported",
    )
    return WeeklyCollaborationDraft("春天", People(("甲", "乙"), "丙"), days, (source,))


def test_v2_canonical_round_trip_and_legacy_dispatch():
    draft = _draft()
    serialized = draft.serialize()
    assert parse_body(serialized) == draft
    legacy = WeeklyThemeDraft("旧主题").serialize()
    assert parse_body(legacy) == WeeklyThemeDraft("旧主题")


def test_v2_hashes_and_provenance_are_closed():
    with pytest.raises(IdentityRejected, match="content_invalid"):
        SourceSnapshot(
            1,
            3,
            DATES[0],
            1,
            1,
            1,
            "activity_name",
            TargetPath(DATES[0], "activity_name"),
            "source",
            "0" * 64,
            import_value_hash("source"),
            "imported",
        )
    with pytest.raises(IdentityRejected, match="content_invalid"):
        SourceSnapshot(
            1,
            3,
            DATES[0],
            1,
            1,
            1,
            "activity_name",
            TargetPath(DATES[1], "activity_name"),
            "source",
            import_value_hash("source"),
            import_value_hash("source"),
            "imported",
        )
    with pytest.raises(IdentityRejected, match="content_invalid"):
        SourceSnapshot(
            1,
            3,
            DATES[0],
            1,
            1,
            1,
            "activity_name",
            TargetPath(DATES[0], "activity_name"),
            "source",
            import_value_hash("source"),
            import_value_hash("edited"),
            "ai",
        )


def test_manual_update_keeps_source_baseline_and_hashes_current_value():
    original = _draft()
    target = TargetPath(DATES[0], "morning_talk_topic")
    changed = original.with_value(target, "手工")
    source = replace(
        original.sources[0],
        adopted_hash=import_value_hash("手工"),
        provenance="manual",
    )
    updated = replace(changed, sources=(source,))
    assert updated.value_at(target) == "手工"
    assert parse_body(updated.serialize()) == updated


def test_imported_snapshot_must_match_actual_day_value():
    body = _draft(source_value="实际")
    bad = replace(
        body.sources[0],
        imported_value="另一个源",
        imported_hash=import_value_hash("另一个源"),
    )
    with pytest.raises(IdentityRejected, match="content_invalid"):
        replace(body, sources=(bad,))


def test_convert_is_explicit_and_does_not_rewrite_legacy_bytes():
    facts = TeachingWeekFacts(
        tenant_id=11,
        scope=SharedWeekScope(1, 2, DATES[0]),
        semester_start=DATES[0],
        semester_end=DATES[-1],
        semester_revision=1,
        calendar_version="calendar.v1",
        calendar_fingerprint="calendar",
        rule_version="rules.v1",
        columns=DATES,
        teaching_days=DATES,
        fingerprint="facts",
    )
    legacy = WeeklyThemeDraft("主题").serialize()
    assert parse_body(legacy).serialize() == legacy
    converted = convert("主题", facts)
    assert type(converted) is WeeklyCollaborationDraft
    assert begin_edit(legacy, facts) == converted


async def test_source_audit_composite_fk_rejects_cross_root_version(world):
    _apps, scope_one, _member_one = await ready(world)
    factory, _tokens, sessions, identity_apps = world
    async with factory() as session:
        semester = (
            (
                await session.execute(
                    select(ID_TABLES["semester"]).where(
                        ID_TABLES["semester"].c.id == scope_one.semester_id
                    )
                )
            )
            .mappings()
            .one()
        )
    semester_stamp = IdentityStamp(semester["id"], semester["revision"])
    class_two = await identity_apps[2].create_class(
        sessions[2],
        ClassInput(semester["academic_year_id"], scope_one.semester_id, "五班", "中班"),
    )
    await identity_apps[2].grant(sessions[2], assignment(semester_stamp, class_two, 3))
    scope_two = SharedWeekScope(class_two.id, scope_one.semester_id, DATES[0])
    root_app = SharedWeeklyApplication(factory, lambda: world[1][3])
    first = await root_app.create(
        sessions[3], scope_one, WeeklyThemeDraft("root-one"), uuid4()
    )
    second = await root_app.create(
        sessions[3], scope_two, WeeklyThemeDraft("root-two"), uuid4()
    )
    loaded = await root_app.load(sessions[3], first.plan.plan_id)
    audit = SOURCE_TABLES["shared_weekly_source_audit"]
    values = {
        "tenant_id": 11,
        "actor_id": 3,
        "plan_id": first.plan.plan_id,
        "version_id": first.plan.current_version,
        "class_instance_id": scope_one.class_instance_id,
        "semester_id": scope_one.semester_id,
        "membership_revision": loaded.stamp.authorization.membership_revision,
        "assignments_json": "[[1,1]]",
        "operation_id": str(uuid4()),
        "session_hash": loaded.stamp.authorization.session_hash,
        "action": "source_read",
        "outcome": "success",
        "reason": "authorized",
    }
    async with factory() as session:
        await session.execute(insert(audit).values(**values))
        await session.commit()
    forged = dict(values)
    forged.update(
        version_id=second.plan.current_version,
        operation_id=str(uuid4()),
    )
    async with factory() as session:
        with pytest.raises(SQLAlchemyError):
            await session.execute(insert(audit).values(**forged))
        await session.rollback()


async def test_source_insert_binds_parent_scope_and_target_days(world):
    _source_app, loaded, source_ids, mapping, target, _member = await sources_ready(
        world, (3,)
    )
    factory, _tokens, sessions, identity_apps = world
    async with factory() as session:
        semester = (
            (
                await session.execute(
                    select(ID_TABLES["semester"]).where(
                        ID_TABLES["semester"].c.id == target.semester_id
                    )
                )
            )
            .mappings()
            .one()
        )
    semester_stamp = IdentityStamp(semester["id"], semester["revision"])
    class_two = await identity_apps[2].create_class(
        sessions[2],
        ClassInput(semester["academic_year_id"], target.semester_id, "六班", "中班"),
    )
    await identity_apps[2].grant(sessions[2], assignment(semester_stamp, class_two, 3))
    async with factory() as session:
        result = await session.execute(
            insert(DailyPlan.__table__).values(
                tenant_id=11,
                user_id=3,
                plan_date=DATES[2],
                week_number=2,
                weekday_cn="周三",
                grade="中班",
                class_name="跨班源",
                activity_name="班B活动",
                morning_talk_topic="班B晨谈",
                outdoor_activity="班B户外",
            )
        )
        class_two_source_id = result.inserted_primary_key[0]
        await session.commit()
    class_two_target = MappingTarget(
        class_two_source_id, class_two.id, target.semester_id
    )
    preview = await mapping.preview(sessions[2], class_two_target)
    await mapping.confirm(
        sessions[2], preview.candidate_id, confirmed=True, operation_id=uuid4()
    )
    source_rows = SOURCE_TABLES["shared_weekly_source"]
    # Build a real unpublished next version under class A's published root.
    from app.repository.shared_weekly_repository import ROOT, VERSION

    async with factory() as session:
        root_row = (
            (
                await session.execute(
                    select(ROOT).where(ROOT.c.id == loaded.stamp.plan.plan_id)
                )
            )
            .mappings()
            .one()
        )
        old_version = (
            (
                await session.execute(
                    select(VERSION).where(VERSION.c.id == root_row["current_version"])
                )
            )
            .mappings()
            .one()
        )
        pending_values = dict(old_version)
        pending_values.pop("id")
        pending_values.update(
            version=root_row["revision"] + 1,
            predecessor=root_row["current_version"],
            operation_id=str(uuid4()),
        )
        pending_id = (
            await session.execute(insert(VERSION).values(**pending_values))
        ).inserted_primary_key[0]
        events = (
            (
                await session.execute(
                    select(MAPPING_TABLES["identity_mapping_event"])
                    .where(MAPPING_TABLES["identity_mapping_event"].c.tenant_id == 11)
                    .order_by(MAPPING_TABLES["identity_mapping_event"].c.id)
                )
            )
            .mappings()
            .all()
        )
        event_a = next(e for e in events if e["daily_plan_id"] == source_ids[0])
        event_b = next(e for e in events if e["daily_plan_id"] == class_two_source_id)
        source_a_value = (
            await session.execute(
                select(DAILY.c.activity_name).where(DAILY.c.id == source_ids[0])
            )
        ).scalar_one()
        source_b_activity = (
            await session.execute(
                select(DAILY.c.activity_name).where(DAILY.c.id == class_two_source_id)
            )
        ).scalar_one()
        value_hash = lambda value: sha256(value.encode()).hexdigest()
        valid = {
            "tenant_id": 11,
            "version_id": pending_id,
            "source_id": event_a["daily_plan_id"],
            "source_user_id": event_a["source_user_id"],
            "source_date": event_a["source_date"],
            "source_revision": event_a["source_revision"],
            "mapping_id": event_a["id"],
            "mapping_revision": event_a["revision"],
            "source_field": "activity_name",
            "target_path": TargetPath(DATES[2], "activity_name").serialize(),
            "imported_value": source_a_value or "",
            "imported_hash": value_hash(source_a_value or ""),
            "adopted_hash": value_hash(source_a_value or ""),
            "provenance": "imported",
        }
        control = await session.begin_nested()
        await session.execute(insert(source_rows).values(**valid))
        await control.rollback()
        invalid_rows = (
            {
                **valid,
                "source_id": event_b["daily_plan_id"],
                "source_user_id": event_b["source_user_id"],
                "source_date": event_b["source_date"],
                "source_revision": event_b["source_revision"],
                "mapping_id": event_b["id"],
                "mapping_revision": event_b["revision"],
                "target_path": TargetPath(DATES[2], "activity_name").serialize(),
                "imported_value": source_b_activity or "",
                "imported_hash": value_hash(source_b_activity or ""),
                "adopted_hash": value_hash(source_b_activity or ""),
            },
            {
                **valid,
                "target_path": TargetPath(
                    date(2026, 9, 6), "activity_name"
                ).serialize(),
            },
            {
                **valid,
                "target_path": TargetPath(DATES[3], "outdoor_activity").serialize(),
            },
            {
                **valid,
                "target_path": json.dumps(
                    {"field": "activity_name", "day": DATES[4].isoformat()},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
            {
                **valid,
                "target_path": json.dumps(
                    {"day": DATES[2].isoformat()},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
            {
                **valid,
                "target_path": json.dumps(
                    {"day": DATES[2].isoformat(), "field": None},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
            {
                **valid,
                "source_field": "ACTIVITY_NAME",
                "target_path": json.dumps(
                    {"day": DATES[2].isoformat(), "field": "ACTIVITY_NAME"},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            },
            {
                **valid,
                "source_field": "outdoor_activity",
                "target_path": TargetPath(DATES[2], "outdoor_activity").serialize(),
                "provenance": "IMPORTED",
            },
        )
        rejected_rows = []
        for invalid in invalid_rows:
            rejected = False
            savepoint = await session.begin_nested()
            try:
                await session.execute(insert(source_rows).values(**invalid))
            except SQLAlchemyError:
                rejected = True
            finally:
                await savepoint.rollback()
            rejected_rows.append(rejected)
        assert rejected_rows == [True] * len(invalid_rows), (
            "source guard accepted an invalid parent scope/target path"
        )
        await session.rollback()


async def test_source_insert_rejects_deleted_source_without_predecessor_baseline(world):
    apps, scope, _member = await ready(world)
    factory, tokens, sessions, _identity_apps = world
    await apps[3].create(sessions[3], scope, WeeklyThemeDraft("empty"), uuid4())
    mapping = SourceMappingApplication(factory, lambda: tokens[2])
    async with factory() as session:
        result = await session.execute(
            insert(DailyPlan.__table__).values(
                tenant_id=11,
                user_id=3,
                plan_date=DATES[2],
                week_number=2,
                weekday_cn="周三",
                grade="中班",
                class_name="待删源",
                activity_name="已删源",
                morning_talk_topic="晨谈",
                outdoor_activity="户外",
            )
        )
        source_id = result.inserted_primary_key[0]
        await session.commit()
    target = MappingTarget(source_id, scope.class_instance_id, scope.semester_id)
    preview = await mapping.preview(world[2][2], target)
    await mapping.confirm(
        world[2][2], preview.candidate_id, confirmed=True, operation_id=uuid4()
    )
    async with factory() as session:
        await delete_daily_plan(session, 11, 3, plan_id=source_id, expected_revision=1)
        await session.commit()
    from app.repository.shared_weekly_repository import ROOT, VERSION

    async with factory() as session:
        root_row = (
            (await session.execute(select(ROOT).where(ROOT.c.tenant_id == 11)))
            .mappings()
            .one()
        )
        previous = (
            (
                await session.execute(
                    select(VERSION).where(VERSION.c.id == root_row["current_version"])
                )
            )
            .mappings()
            .one()
        )
        pending = dict(previous)
        pending.pop("id")
        pending.update(
            version=root_row["revision"] + 1,
            predecessor=root_row["current_version"],
            operation_id=str(uuid4()),
        )
        pending_id = (
            await session.execute(insert(VERSION).values(**pending))
        ).inserted_primary_key[0]
        event = (
            (
                await session.execute(
                    select(MAPPING_TABLES["identity_mapping_event"]).where(
                        MAPPING_TABLES["identity_mapping_event"].c.daily_plan_id
                        == source_id
                    )
                )
            )
            .mappings()
            .one()
        )
        row = {
            "tenant_id": 11,
            "version_id": pending_id,
            "source_id": source_id,
            "source_user_id": event["source_user_id"],
            "source_date": event["source_date"],
            "source_revision": event["source_revision"],
            "mapping_id": event["id"],
            "mapping_revision": event["revision"],
            "source_field": "activity_name",
            "target_path": TargetPath(DATES[2], "activity_name").serialize(),
            "imported_value": "已删源",
            "imported_hash": import_value_hash("已删源"),
            "adopted_hash": import_value_hash("已删源"),
            "provenance": "imported",
        }
        rejected = False
        savepoint = await session.begin_nested()
        try:
            await session.execute(
                insert(SOURCE_TABLES["shared_weekly_source"]).values(**row)
            )
        except SQLAlchemyError:
            rejected = True
        finally:
            await savepoint.rollback()
        assert rejected, "deleted source without predecessor baseline was accepted"
        await session.rollback()


async def test_source_insert_rejects_arbitrary_live_revision_and_field(world):
    apps, scope, _member = await ready(world)
    factory, tokens, sessions, _identity_apps = world
    await apps[3].create(sessions[3], scope, WeeklyThemeDraft("empty"), uuid4())
    mapping = SourceMappingApplication(factory, lambda: tokens[2])
    async with factory() as session:
        result = await session.execute(
            insert(DailyPlan.__table__).values(
                tenant_id=11,
                user_id=3,
                plan_date=DATES[2],
                week_number=2,
                weekday_cn="周三",
                grade="中班",
                class_name="活源",
                activity_name="真实源",
                morning_talk_topic="晨谈",
                outdoor_activity="户外",
            )
        )
        source_id = result.inserted_primary_key[0]
        await session.commit()
    target = MappingTarget(source_id, scope.class_instance_id, scope.semester_id)
    preview = await mapping.preview(world[2][2], target)
    await mapping.confirm(
        world[2][2], preview.candidate_id, confirmed=True, operation_id=uuid4()
    )
    from app.repository.shared_weekly_repository import ROOT, VERSION

    async with factory() as session:
        root_row = (
            (await session.execute(select(ROOT).where(ROOT.c.tenant_id == 11)))
            .mappings()
            .one()
        )
        previous = (
            (
                await session.execute(
                    select(VERSION).where(VERSION.c.id == root_row["current_version"])
                )
            )
            .mappings()
            .one()
        )
        pending = dict(previous)
        pending.pop("id")
        pending.update(
            version=root_row["revision"] + 1,
            predecessor=root_row["current_version"],
            operation_id=str(uuid4()),
        )
        pending_id = (
            await session.execute(insert(VERSION).values(**pending))
        ).inserted_primary_key[0]
        event = (
            (
                await session.execute(
                    select(MAPPING_TABLES["identity_mapping_event"]).where(
                        MAPPING_TABLES["identity_mapping_event"].c.daily_plan_id
                        == source_id
                    )
                )
            )
            .mappings()
            .one()
        )
        base = {
            "tenant_id": 11,
            "version_id": pending_id,
            "source_id": source_id,
            "source_user_id": event["source_user_id"],
            "source_date": event["source_date"],
            "source_revision": event["source_revision"],
            "mapping_id": event["id"],
            "mapping_revision": event["revision"],
            "source_field": "activity_name",
            "target_path": TargetPath(DATES[2], "activity_name").serialize(),
            "imported_value": "真实源",
            "imported_hash": import_value_hash("真实源"),
            "adopted_hash": import_value_hash("真实源"),
            "provenance": "imported",
        }
        invalid_rows = (
            {
                **base,
                "source_revision": event["source_revision"] + 1,
            },
            {
                **base,
                "imported_value": "伪造字段",
                "imported_hash": import_value_hash("伪造字段"),
                "adopted_hash": import_value_hash("伪造字段"),
            },
        )
        rejected_rows = []
        for row in invalid_rows:
            savepoint = await session.begin_nested()
            rejected = False
            try:
                await session.execute(
                    insert(SOURCE_TABLES["shared_weekly_source"]).values(**row)
                )
            except SQLAlchemyError:
                rejected = True
            finally:
                await savepoint.rollback()
            rejected_rows.append(rejected)
        assert rejected_rows == [True, True], (
            "live source revision/value forgery was accepted"
        )
        await session.rollback()
