"""WP-D closed body and migrated repository evidence (synthetic inputs)."""

import json
from datetime import date, timedelta

from app.service.shared_weekly.body_contracts import (
    CollaborationDay,
    WeeklyCollaborationDraft,
    parse_body,
)
from app.service.shared_weekly.people_contracts import People
from app.service.shared_weekly.root_contracts import canonical

PATHS = tuple(
    [
        f"games.{group}.{field}"
        for group in ("collective.0", "collective.1", "autonomous")
        for field in ("name", "goals.0", "goals.1", "goals.2")
    ]
    + [
        f"area.{field}"
        for field in (
            "name",
            "goals.0",
            "goals.1",
            "goals.2",
            "materials",
            "guidance.0",
            "guidance.1",
            "guidance.2",
        )
    ]
    + [f"{group}.{i}" for group in ("focus", "environment") for i in range(3)]
    + [f"habits.{i}.{field}" for i in range(3) for field in ("name", "content")]
    + ["home"]
)


def base():
    return WeeklyCollaborationDraft(
        "《春天》",
        People(("老师",), "保育员"),
        tuple(
            CollaborationDay(date(2026, 9, 7) + timedelta(days=i), "", "", "", "", "")
            for i in range(5)
        ),
        (),
    )


def v3_payload():
    data = json.loads(base().serialize())
    data.update(
        schema="weekly-authoring.v3",
        budget_version="weekly-authoring-budget.v1",
        archive=[],
        calendar=None,
        outdoor_title="体能大循环",
        area_title="1.户外游戏 2.区域游戏 3.专用室",
        slots={
            path: {"value": "", "provenance": "manual", "references": []}
            for path in PATHS
        },
    )
    data["slots"].update(
        {
            f"days.{day.day.isoformat()}.{field}": {
                "value": "",
                "provenance": "manual",
                "references": [],
            }
            for day in base().days
            for field in ("morning_talk_topic", "morning_talk_questions")
        }
    )
    return data


def test_structured_empty_week_preserves_fixed_slots_and_legacy_body():
    old = base().serialize()
    body = parse_body(canonical(v3_payload()))
    assert body.base.serialize() == old
    assert body.serialize() == canonical(v3_payload())
    assert body.value_at("area.materials") == ""
    assert len(body.slots) == 43
    assert parse_body(old).serialize() == old


from dataclasses import replace
from uuid import uuid4

import pytest

from app.repository.shared_weekly_repository import VERSION
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.authoring_contracts import (
    AuthoringSlot,
    SourceReference,
    WeeklyAuthoringDraft,
    reference_for,
)
from app.service.shared_weekly.body_contracts import (
    SourceSnapshot,
    TargetPath,
    import_value_hash,
)
from app.service.shared_weekly.contracts import SharedAction
from app.service.shared_weekly.root_contracts import WeeklyThemeDraft
from tests.test_wpc_identity import world as _world
from tests.test_wpc_shared_root import ready, rows

world = _world


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(extra=True),
        lambda d: d["slots"].pop("focus.0"),
        lambda d: d["slots"].update({"focus.3": d["slots"]["focus.0"]}),
        lambda d: d["slots"]["home"].update(value=True),
        lambda d: d["slots"]["home"].update(value="x" * 401),
        lambda d: d["slots"]["games.autonomous.name"].update(value="x" * 65),
        lambda d: d["slots"]["focus.0"].update(value="x" * 161),
        lambda d: d["slots"]["focus.0"].update(value="\0"),
        lambda d: d["slots"]["focus.0"].update(provenance="provider"),
        lambda d: d["slots"]["focus.0"].update(provenance="imported", value="unbacked"),
        lambda d: d["slots"]["focus.0"].update(
            references=[
                {
                    "target": {"day": "2026-09-07", "field": "outdoor_activity"},
                    "snapshot_hash": "a" * 64,
                }
            ]
        ),
        lambda d: d.update(outdoor_title="other"),
        lambda d: d.update(area_title="other"),
        lambda d: d["slots"]["days.2026-09-07.morning_talk_topic"].update(
            value="unmirrored"
        ),
    ],
)
def test_reject_closed_schema_and_limits(mutation):
    data = v3_payload()
    mutation(data)
    with pytest.raises(IdentityRejected, match="content_invalid"):
        parse_body(canonical(data))


def test_fixed_empty_draft_complete_validation_and_no_silent_truncation():
    draft = WeeklyAuthoringDraft.from_collaboration(base())
    with pytest.raises(IdentityRejected, match="content_invalid"):
        draft.validate_complete()
    changed = draft.with_slot("home", AuthoringSlot(" 文本\n"))
    assert changed.value_at("home") == " 文本\n"
    changed.validate_complete(("home",))
    with pytest.raises(IdentityRejected):
        changed.with_slot("focus.0", AuthoringSlot("\ud800"))
    with pytest.raises(IdentityRejected):
        changed.with_slot("focus.0", AuthoringSlot("repeat")).with_slot(
            "focus.1", AuthoringSlot("repeat")
        )
    assert draft.value_at("home") == ""


def sourced_base():
    target = TargetPath(date(2026, 9, 7), "outdoor_activity")
    value = "游戏名称：追球；目标：练习平衡"
    source = SourceSnapshot(
        1,
        3,
        target.day,
        1,
        1,
        1,
        target.field,
        target,
        value,
        import_value_hash(value),
        import_value_hash(value),
    )
    return replace(base().with_value(target, value), sources=(source,))


def test_reference_is_exact_import_baseline_and_survives_manual_day_edit():
    original = sourced_base()
    ref = reference_for(original.sources[0])
    draft = WeeklyAuthoringDraft.from_collaboration(original).with_slot(
        "games.collective.0.name", AuthoringSlot("追球", "imported", (ref,))
    )
    edited = draft.with_value(ref.target, "手工保留旧来源")
    assert edited.slot_at("games.collective.0.name").references == (ref,)
    assert parse_body(edited.serialize()) == edited
    with pytest.raises(IdentityRejected):
        draft.with_slot(
            "games.collective.0.name", AuthoringSlot("凭空名称", "imported", (ref,))
        )
    with pytest.raises(IdentityRejected):
        draft.with_slot(
            "games.collective.0.name",
            AuthoringSlot("追球", "imported", (SourceReference(ref.target, "a" * 64),)),
        )
    with pytest.raises(IdentityRejected):
        AuthoringSlot("追球", "imported", (ref, ref))


def test_duplicate_json_and_aggregate_body_rejected():
    payload = canonical(v3_payload())
    with pytest.raises(IdentityRejected):
        parse_body(
            payload.replace(
                '"schema":"weekly-authoring.v3"',
                '"schema":"weekly-authoring.v3","schema":"weekly-authoring.v3"',
            )
        )
    with pytest.raises(IdentityRejected):
        WeeklyAuthoringDraft.parse(" " * 1_048_577)


async def test_migrated_repository_v3_roundtrip_preserves_v1_history(world):
    apps, scope, _ = await ready(world)
    actor = world[2][3]
    created = await apps[3].create(actor, scope, WeeklyThemeDraft("原稿"), uuid4())
    before = (await rows(world, VERSION))[0]
    loaded = await apps[3].load(actor, created.plan.plan_id)
    draft = WeeklyAuthoringDraft.from_collaboration(base()).with_slot(
        "home", AuthoringSlot("一起观察春天")
    )
    async with apps[3]._identity.transaction(actor, commit_unknown=True) as (
        identity,
        current_actor,
    ):
        repo, root, assessment = await apps[3]._locked(
            identity,
            current_actor,
            created.plan.plan_id,
            SharedAction.EDIT,
            loaded.stamp.authorization,
        )
        saved = await repo.publish(root, assessment, draft, str(uuid4()))
    current = await apps[3].load(actor, created.plan.plan_id)
    assert current.stamp.plan == saved
    assert current.body == draft
    assert (await rows(world, VERSION))[0] == before


def test_explicit_conversion_keeps_missing_imported_morning_as_empty_draft():
    original = base()
    target = TargetPath(original.days[0].day, "morning_talk_topic")
    source = SourceSnapshot(
        1,
        3,
        target.day,
        1,
        1,
        1,
        target.field,
        target,
        "",
        import_value_hash(""),
        import_value_hash(""),
    )
    original = replace(original, sources=(source,))
    draft = WeeklyAuthoringDraft.from_collaboration(original)
    assert draft.base == original
    assert draft.value_at(f"days.{target.day.isoformat()}.morning_talk_topic") == ""
    assert parse_body(draft.serialize()) == draft


def test_atomic_slot_replacement_permits_swap_but_rejects_duplicate_paths():
    draft = WeeklyAuthoringDraft.from_collaboration(base()).with_slots(
        (("focus.0", AuthoringSlot("甲")), ("focus.1", AuthoringSlot("乙")))
    )
    swapped = draft.with_slots(
        (("focus.0", AuthoringSlot("乙")), ("focus.1", AuthoringSlot("甲")))
    )
    assert (swapped.value_at("focus.0"), swapped.value_at("focus.1")) == ("乙", "甲")
    with pytest.raises(IdentityRejected):
        draft.with_slots(
            (("focus.0", AuthoringSlot("甲")), ("focus.0", AuthoringSlot("乙")))
        )


def test_v3_calendar_identity_roundtrip_is_frozen():
    data = v3_payload()
    data["calendar"] = {
        "rule_version": "wpd.v1",
        "label_fingerprint": "b" * 64,
        "columns": [
            {"day": day.day.isoformat(), "teaching": True, "label": ""}
            for day in base().days
        ],
    }
    draft = parse_body(canonical(data))
    assert draft.calendar.rule_version == "wpd.v1"
    assert draft.with_slot("home", AuthoringSlot("手填")).calendar == draft.calendar
    assert draft.serialize() == canonical(data)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(extra=True),
        lambda d: d.update(label_fingerprint="invalid"),
        lambda d: d["columns"][0].update(teaching=1),
        lambda d: d["columns"][0].update(label="放假"),
        lambda d: d["columns"][0].update(day="2026-09-08"),
        lambda d: d["columns"].pop(),
    ],
)
def test_calendar_schema_and_masks_fail_closed(mutation):
    data = v3_payload()
    calendar = {
        "rule_version": "wpd.v1",
        "label_fingerprint": "b" * 64,
        "columns": [
            {"day": day.day.isoformat(), "teaching": True, "label": ""}
            for day in base().days
        ],
    }
    mutation(calendar)
    data["calendar"] = calendar
    with pytest.raises(IdentityRejected):
        parse_body(canonical(data))


def test_v3_budget_version_is_serialized_and_unknown_version_rejected():
    draft = WeeklyAuthoringDraft.from_collaboration(base())
    data = json.loads(draft.serialize())
    assert data.get("budget_version") == "weekly-authoring-budget.v1"
    assert parse_body(canonical(data)) == draft
    data["budget_version"] = "weekly-authoring-budget.future"
    with pytest.raises(IdentityRejected):
        parse_body(canonical(data))


@pytest.mark.parametrize(
    "paths",
    [
        ("games.collective.0.name", "games.collective.1.name"),
        ("games.collective.0.name", "games.autonomous.name"),
        ("habits.0.name", "habits.2.name"),
    ],
)
def test_duplicate_named_games_and_habits_cannot_count_as_distinct_items(paths):
    draft = WeeklyAuthoringDraft.from_collaboration(base())
    with pytest.raises(IdentityRejected, match="content_invalid"):
        draft.with_slots(tuple((path, AuthoringSlot("重复名称")) for path in paths))


def archived_draft():
    old = sourced_base()
    ref = reference_for(old.sources[0])
    draft = WeeklyAuthoringDraft.from_collaboration(old).with_slot(
        "games.collective.0.name", AuthoringSlot("追球", "imported", (ref,))
    )
    new_value = "游戏名称：跳圈；目标：练习跨越"
    new_source = replace(
        old.sources[0],
        revision=2,
        imported_value=new_value,
        imported_hash=import_value_hash(new_value),
        adopted_hash=import_value_hash(new_value),
    )
    new_base = replace(old.with_value(ref.target, new_value), sources=(new_source,))
    return replace(draft, base=new_base, archive=(old.sources[0],))


def test_archived_baseline_preserves_imported_structure_after_reimport():
    draft = archived_draft()
    assert draft.value_at("games.collective.0.name") == "追球"
    assert draft.slot_at("games.collective.0.name").provenance == "imported"
    assert len(draft.all_sources) == 2
    assert parse_body(draft.serialize()) == draft


def test_replacing_last_archived_reference_trims_unused_archive():
    draft = archived_draft()
    changed = draft.with_slot("games.collective.0.name", AuthoringSlot("新手工名称"))
    assert changed.archive == ()
    assert changed.value_at("games.collective.0.name") == "新手工名称"


async def test_repository_rejects_archive_not_in_previous_immutable_body(world):
    apps, scope, _ = await ready(world)
    actor = world[2][3]
    created = await apps[3].create(actor, scope, WeeklyThemeDraft("原稿"), uuid4())
    before = await rows(world, VERSION)
    loaded = await apps[3].load(actor, created.plan.plan_id)
    with pytest.raises(IdentityRejected, match="source_unavailable"):
        async with apps[3]._identity.transaction(actor, commit_unknown=True) as (
            identity,
            current_actor,
        ):
            repo, root, assessment = await apps[3]._locked(
                identity,
                current_actor,
                created.plan.plan_id,
                SharedAction.EDIT,
                loaded.stamp.authorization,
            )
            await repo.publish(root, assessment, archived_draft(), str(uuid4()))
    assert await rows(world, VERSION) == before


@pytest.mark.parametrize("count,accepted", [(128, True), (129, False)])
def test_archive_limit_counts_referenced_full_snapshots(count, accepted):
    original = sourced_base().sources[0]
    archive = tuple(replace(original, revision=i + 1) for i in range(count))
    draft = WeeklyAuthoringDraft.from_collaboration(base())
    slots = list(draft.slots)
    # Five independently selected fields can reference 128 historical snapshots
    # while every slot remains below its separate 30-reference cap.
    for offset in range(0, count, 30):
        index = offset // 30
        slots[index] = AuthoringSlot(
            "",
            "manual",
            tuple(reference_for(source) for source in archive[offset : offset + 30]),
        )
    if accepted:
        result = replace(draft, slots=tuple(slots), archive=archive)
        assert len(result.archive) == 128
        assert parse_body(result.serialize()) == result
    else:
        with pytest.raises(IdentityRejected, match="content_invalid"):
            replace(draft, slots=tuple(slots), archive=archive)
