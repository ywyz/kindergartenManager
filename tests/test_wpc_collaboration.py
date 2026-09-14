"""Real mapping -> daily selection -> adoption -> CAS -> reload -> reimport."""

from dataclasses import replace
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from app.repository.shared_weekly_repository import VERSION
from app.repository.source_mapping_repository import DAILY
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.collaboration_application import CollaborationApplication
from app.service.shared_weekly.editor_contracts import ManualWeekEdit
from app.service.shared_weekly.people_application import PeopleDefaultsApplication
from app.service.shared_weekly.people_contracts import People
from tests.test_wpc_identity import world as _identity_world

world = _identity_world
from tests.test_wpc_shared_root import rows
from tests.test_wpc_sources import sources_ready


async def ready_editor(world):
    _, loaded, ids, mapping, target, member = await sources_ready(world, (3, 4))
    app = CollaborationApplication(world[0], lambda: world[1][3])
    edit = await app.begin_edit(world[2][3], loaded.stamp.plan.plan_id)
    return app, edit, ids, mapping, target, member


async def propose(world, app, edit, source_id):
    listed = await app.list_sources(world[2][3], edit.target)
    selected = await app.select_sources(world[2][3], listed.list_id, (source_id,))
    return await app.propose_import(
        world[2][3], edit.page_id, edit.page, selected.selection_id
    )


async def adopt(world, app, edit, source_id):
    candidate = await propose(world, app, edit, source_id)
    return await app.adopt_candidate(
        world[2][3], candidate.candidate_id, edit.page, confirmed=True
    )


async def test_full_import_manual_check_cancel_reimport_history(world):
    app, edit, ids, _, _, _ = await ready_editor(world)
    source_before = await rows(world, DAILY)
    versions_before = await rows(world, VERSION)
    candidate = await propose(world, app, edit, ids[-1])
    assert len(candidate.differences) == 5
    assert await rows(world, VERSION) == versions_before
    edit = await app.adopt_candidate(
        world[2][3], candidate.candidate_id, edit.page, confirmed=True
    )
    assert len(edit.body.sources) == 5
    assert await rows(world, VERSION) == versions_before
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    assert await rows(world, DAILY) == source_before
    original_versions = await rows(world, VERSION)
    edit = await app.begin_edit(world[2][3], saved.plan_id)
    days = tuple(
        replace(d, morning_talk_topic="手工保留") if d.day == date(2026, 9, 9) else d
        for d in edit.body.days
    )
    edit = await app.update_edit(
        world[2][3],
        edit.page_id,
        edit.page,
        ManualWeekEdit(edit.body.theme, edit.body.people, days),
    )
    async with world[0]() as s:
        await s.execute(
            update(DAILY)
            .where(DAILY.c.id == ids[-1])
            .values(morning_talk_topic="新源", revision=DAILY.c.revision + 1)
        )
        await s.commit()
    # Retaining old sources is not a request to import again.
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    before = await rows(world, VERSION)
    checks = await app.check_sources(world[2][3], saved.plan_id)
    assert {s.status for s in checks} == {"changed"}
    assert await rows(world, VERSION) == before
    edit = await app.begin_edit(world[2][3], saved.plan_id)
    candidate = await propose(world, app, edit, ids[-1])
    difference = next(
        d for d in candidate.differences if d.target_path.field == "morning_talk_topic"
    )
    assert (
        difference.current_value,
        difference.imported_value,
        difference.source_value,
    ) == ("手工保留", "source", "新源")
    app.cancel_candidate(world[2][3], candidate.candidate_id)
    assert await rows(world, VERSION) == before
    edit = await adopt(world, app, edit, ids[-1])
    new = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    loaded = await app.load(world[2][3], new.plan_id)
    assert (
        next(
            d for d in loaded.body.days if d.day == date(2026, 9, 9)
        ).morning_talk_topic
        == "新源"
    )
    assert (await rows(world, VERSION))[: len(original_versions)] == original_versions
    assert {s.status for s in await app.check_sources(world[2][3], new.plan_id)} == {
        "unchanged"
    }


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "mapping",
        "revoke",
        "session",
        "cancel",
        "expire",
        "edit",
        "other_save",
    ],
)
async def test_candidate_drift_zero_adoption_or_save(world, change):
    app, edit, ids, mapping, target, member = await ready_editor(world)
    candidate = await propose(world, app, edit, ids[0])
    if change == "source":
        async with world[0]() as s:
            await s.execute(
                update(DAILY)
                .where(DAILY.c.id == ids[0])
                .values(activity_name="new", revision=DAILY.c.revision + 1)
            )
            await s.commit()
    elif change == "mapping":
        p = await mapping.preview(world[2][2], target)
        await mapping.confirm(
            world[2][2], p.candidate_id, confirmed=True, operation_id=uuid4()
        )
    elif change == "revoke":
        await world[3][2].revoke(world[2][2], member.id, 1)
    elif change == "session":
        from app.core.models.user import User

        async with world[0]() as s:
            await s.execute(update(User).where(User.id == 3).values(auth_epoch=2))
            await s.commit()
    elif change == "cancel":
        app.cancel_candidate(world[2][3], candidate.candidate_id)
    elif change == "expire":
        app._imports._items[candidate.candidate_id] = replace(
            app._imports._items[candidate.candidate_id], expires=0
        )
    elif change == "edit":
        await app.update_edit(
            world[2][3],
            edit.page_id,
            edit.page,
            ManualWeekEdit("手改", edit.body.people, edit.body.days),
        )
    elif change == "other_save":
        other = CollaborationApplication(world[0], lambda: world[1][4])
        other_edit = await other.begin_edit(world[2][4], edit.target.plan.plan_id)
        other_edit = await other.update_edit(
            world[2][4],
            other_edit.page_id,
            other_edit.page,
            ManualWeekEdit("other", other_edit.body.people, other_edit.body.days),
        )
        await other.save_edit(world[2][4], other_edit.page_id, other_edit.page, uuid4())
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected):
        await app.adopt_candidate(
            world[2][3], candidate.candidate_id, edit.page, confirmed=True
        )
    assert await rows(world, VERSION) == before


@pytest.mark.parametrize("change", ["source", "mapping", "revoke"])
async def test_save_revalidates_new_import(world, change):
    app, edit, ids, mapping, target, member = await ready_editor(world)
    edit = await adopt(world, app, edit, ids[0])
    if change == "source":
        async with world[0]() as s:
            await s.execute(
                update(DAILY)
                .where(DAILY.c.id == ids[0])
                .values(activity_name="new", revision=DAILY.c.revision + 1)
            )
            await s.commit()
    elif change == "mapping":
        p = await mapping.preview(world[2][2], target)
        await mapping.confirm(
            world[2][2], p.candidate_id, confirmed=True, operation_id=uuid4()
        )
    else:
        await world[3][2].revoke(world[2][2], member.id, 1)
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected):
        await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    assert await rows(world, VERSION) == before


async def test_shared_people_defaults_initialization_and_history(world):
    app, edit, _, _, _, _ = await ready_editor(world)
    scope = edit.target.authorization.scope
    defaults = PeopleDefaultsApplication(world[0], lambda: world[1][3])
    await defaults.save_defaults(
        world[2][3], scope, 0, People(("甲", "乙"), "丙"), uuid4()
    )
    existing = await app.create_week(world[2][3], scope, "do not replace", uuid4())
    assert not existing.created
    assert (await app.load(world[2][3], existing.plan.plan_id)).body.theme == "theme"
    # A second class provides a fresh authorized root without calendar assumptions.
    from app.service.academic_identity.contracts import (
        ClassInput,
        IdentityStamp,
    )
    from tests.test_wpc_identity import assignment

    async with world[0]() as s:
        from app.core.models.academic_identity import TABLES

        year = (
            await s.execute(
                select(TABLES["class_instance"].c.academic_year_id).where(
                    TABLES["class_instance"].c.id == scope.class_instance_id
                )
            )
        ).scalar_one()
    cls = await world[3][2].create_class(
        world[2][2], ClassInput(year, scope.semester_id, "新班", "中班")
    )
    for uid in (3, 4):
        await world[3][2].grant(
            world[2][2], assignment(IdentityStamp(scope.semester_id, 1), cls, uid)
        )
    new_scope = replace(scope, class_instance_id=cls.id)
    await defaults.save_defaults(
        world[2][3], new_scope, 0, People(("甲", "乙"), "丙"), uuid4()
    )
    first = await app.create_week(world[2][3], new_scope, "new", uuid4())
    old_versions = await rows(world, VERSION)
    other = CollaborationApplication(world[0], lambda: world[1][4])
    assert (await other.load(world[2][4], first.plan.plan_id)).body.people == People(
        ("甲", "乙"), "丙"
    )
    await defaults.save_defaults(
        world[2][3], new_scope, 1, People(("更新",), ""), uuid4()
    )
    assert not (
        await other.create_week(world[2][4], new_scope, "other", uuid4())
    ).created
    assert (await other.load(world[2][4], first.plan.plan_id)).body.people == People(
        ("甲", "乙"), "丙"
    )
    assert await rows(world, VERSION) == old_versions
    shared = await other.begin_edit(world[2][4], first.plan.plan_id)
    shared = await other.update_edit(
        world[2][4],
        shared.page_id,
        shared.page,
        ManualWeekEdit(shared.body.theme, People(("明确编辑",), ""), shared.body.days),
    )
    saved = await other.save_edit(world[2][4], shared.page_id, shared.page, uuid4())
    assert (await other.load(world[2][4], saved.plan_id)).body.people == People(
        ("明确编辑",), ""
    )
    assert (await rows(world, VERSION))[: len(old_versions)] == old_versions


@pytest.mark.parametrize("change", ["deleted", "source_revoked", "source_disabled"])
async def test_unavailable_keeps_shared_snapshot_and_allows_manual_save(world, change):
    app, edit, ids, _, _, _ = await ready_editor(world)
    edit = await adopt(world, app, edit, ids[-1])
    stamp = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    old = await rows(world, VERSION)
    if change == "deleted":
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from app.core.database import _build_engine
        from app.repository.daily_plan_repository import delete_daily_plan

        engine = _build_engine()
        async with async_sessionmaker(engine)() as s:
            await delete_daily_plan(s, 11, 4, plan_id=ids[-1], expected_revision=1)
            await s.commit()
        await engine.dispose()
    elif change == "source_disabled":
        from app.core.models.user import User

        async with world[0]() as s:
            await s.execute(update(User).where(User.id == 4).values(is_active=False))
            await s.commit()
    else:
        from app.core.models.academic_identity import TABLES

        async with world[0]() as s:
            aid = (
                await s.execute(
                    select(TABLES["teacher_class_assignment"].c.id).where(
                        TABLES["teacher_class_assignment"].c.user_id == 4
                    )
                )
            ).scalar_one()
        await world[3][2].revoke(world[2][2], aid, 1)
    assert {s.status for s in await app.check_sources(world[2][3], stamp.plan_id)} == {
        "unavailable"
    }
    assert await rows(world, VERSION) == old
    edit = await app.begin_edit(world[2][3], stamp.plan_id)
    edit = await app.update_edit(
        world[2][3],
        edit.page_id,
        edit.page,
        ManualWeekEdit("manual after unavailable", edit.body.people, edit.body.days),
    )
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    assert (
        await app.load(world[2][3], saved.plan_id)
    ).body.sources == edit.body.sources
    assert (await rows(world, VERSION))[: len(old)] == old


async def test_production_composition_uses_shared_authoring_services(
    world, monkeypatch
):
    from app.core import database
    from app.service.shared_weekly.production_composition import (
        build_shared_weekly_production_application,
    )

    monkeypatch.setattr(database, "AsyncSessionLocal", world[0])
    services = build_shared_weekly_production_application()
    assert type(services.weekly) is CollaborationApplication
    assert type(services.people) is PeopleDefaultsApplication
    assert services.weekly._identity._factory is world[0]
    # Trusted token source is installed by composition; page actor/role flags are not inputs.
    import inspect

    assert set(inspect.signature(services.weekly.create_week).parameters) == {
        "expected",
        "scope",
        "theme",
        "operation_id",
    }


async def test_legacy_theme_save_cannot_discard_collaboration_snapshots(world):
    from app.service.shared_weekly.root_contracts import WeeklyThemeDraft

    app, edit, ids, _, _, _ = await ready_editor(world)
    edit = await adopt(world, app, edit, ids[0])
    stamp = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    loaded = await app.load(world[2][3], stamp.plan_id)
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected, match="content_invalid"):
        await app.save(
            world[2][3], loaded.stamp, WeeklyThemeDraft("legacy overwrite"), uuid4()
        )
    assert await rows(world, VERSION) == before
