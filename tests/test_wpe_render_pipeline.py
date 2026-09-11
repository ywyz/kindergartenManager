"""Actual saved application plus local renderer; synthetic qualification, not Word."""

from uuid import uuid4

from app.integration.ai_client import weekly_authoring_client as client
from app.integration.word_export.shared_weekly_word import (
    SharedWeeklyWordPort,
    _process,
)
from app.repository.shared_weekly_repository import VERSION
from app.repository.weekly_export_repository import AUDIT
from app.service.shared_weekly.authoring_application import SlotChange
from app.service.shared_weekly.export_application import SharedWeeklyExportApplication
from app.service.shared_weekly.layout_authority import LayoutAuthority
from app.service.shared_weekly.reduction_application import ReductionApplication
from tests.test_wpc_identity import world as _world
from tests.test_wpc_shared_root import rows
from tests.test_wpe_export_application import complete
from tests.test_wpe_word_authority import catalog

world = _world


async def actual_pipeline(world, monkeypatch, tmp_path):
    app, edit, _, _, _ = await complete(world, monkeypatch)
    version = (await _process("libreoffice", "--version")).decode().strip()
    authority = LayoutAuthority(catalog(tmp_path, version), local_only=True)
    await authority.activate(11, "synthetic", expected=None)
    exporting = SharedWeeklyExportApplication(app, SharedWeeklyWordPort(authority))
    reduction = ReductionApplication(app, exporting)
    app._reduction = reduction
    return app, edit, exporting, reduction


async def test_saved_actual_renderer_delivery_no_new_version(
    world, monkeypatch, tmp_path
):
    _, edit, exporting, _ = await actual_pipeline(world, monkeypatch, tmp_path)
    actor = world[2][3]
    before = await rows(world, VERSION)
    check = await exporting.check_saved(actor, edit.page_id, edit.page)
    assert check.fits, (check.pages, check.reason)
    document = await exporting.export_saved(actor, check.check_id)
    assert document.data.startswith(b"PK")
    assert await rows(world, VERSION) == before
    assert len(await rows(world, AUDIT)) == 1


async def test_actual_overflow_explicit_reduction_save_recheck(
    world, monkeypatch, tmp_path
):
    app, edit, exporting, reduction = await actual_pipeline(
        world, monkeypatch, tmp_path
    )
    actor = world[2][3]
    # Ordinary Chinese hand text exercises a real overflow and bounded shortening.
    paths = tuple(path for path in edit.body.paths[:33] if not path.endswith(".name"))
    edit = await app.update_slots(
        actor,
        edit.page_id,
        edit.page,
        tuple(
            SlotChange(path, "围绕主题进行观察，" * 10 + str(i))
            for i, path in enumerate(paths)
        ),
    )
    saved = await app.save_edit(actor, edit.page_id, edit.page, uuid4())
    edit = await app.begin_authoring(actor, saved.plan_id)
    before = await rows(world, VERSION)
    check = await exporting.check_saved(actor, edit.page_id, edit.page)
    assert not check.fits and check.reason == "layout_overflow"
    calls = []

    async def mock_reduction(prompt, payload, config):
        calls.append(payload)
        return {
            "values": {
                path: "围绕主题观察，" * 10 + str(i) for i, path in enumerate(paths)
            }
        }

    monkeypatch.setattr(client, "generate", mock_reduction)
    candidate = await reduction.propose(actor, check.check_id, edit.page_id, edit.page)
    assert {d.path for d in candidate.differences} == set(paths)
    assert {d.candidate_value for d in candidate.differences} == {
        "围绕主题观察，" * 10 + str(i) for i in range(len(paths))
    }
    assert await rows(world, VERSION) == before
    edit = await reduction.adopt(
        actor, candidate.candidate_id, edit.page, confirmed=True
    )
    assert await rows(world, VERSION) == before
    saved = await app.save_edit(actor, edit.page_id, edit.page, uuid4())
    edit = await app.begin_authoring(actor, saved.plan_id)
    check = await exporting.check_saved(actor, edit.page_id, edit.page)
    assert not check.fits and check.reason == "layout_overflow"
    assert await rows(world, AUDIT) == ()
    # Explicit teacher edits are the fallback; the exporter never edits or retries.
    edit = await app.update_slots(
        actor,
        edit.page_id,
        edit.page,
        tuple(SlotChange(path, "教师调整" + str(i)) for i, path in enumerate(paths)),
    )
    saved = await app.save_edit(actor, edit.page_id, edit.page, uuid4())
    edit = await app.begin_authoring(actor, saved.plan_id)
    check = await exporting.check_saved(actor, edit.page_id, edit.page)
    assert check.fits, (check.pages, check.reason)
    document = await exporting.export_saved(actor, check.check_id)
    assert document.data.startswith(b"PK") and len(calls) == 1
    assert len(await rows(world, VERSION)) == len(before) + 2
