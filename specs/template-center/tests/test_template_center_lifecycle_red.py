"""模板中心 active pointer、CAS、停用、回滚和审计的稳定 RED。"""

from importlib import import_module

import pytest

from _support import actor, docx_with_text, make_center


def _api():
    return import_module("app.service.template_center")


async def _upload_two_versions(center):
    first = await center.upload(
        actor(),
        document_type="daily_plan",
        filename="v1.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=docx_with_text("version one"),
    )
    second = await center.upload(
        actor(),
        document_type="daily_plan",
        filename="v2.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=docx_with_text("version two"),
    )
    return first, second


@pytest.mark.asyncio
async def test_activation_uses_exact_registry_revision_and_emits_a_traceable_transition():
    api = _api()
    center, effects = make_center(api)
    version, _other = await _upload_two_versions(center)

    receipt = await center.activate(
        actor(),
        document_type="daily_plan",
        version_id=version.template_version_id,
        expected_registry_revision=0,
        expected_active_version_id=None,
    )

    assert receipt.document_type == "daily_plan"
    assert receipt.active_version_id == version.template_version_id
    assert receipt.registry_revision == 1
    assert receipt.content_sha256 == version.content_sha256
    assert [getattr(event, "action", None) for event in effects["audit"].events] == [
        "upload",
        "upload",
        "activate",
    ]


@pytest.mark.asyncio
async def test_stale_activation_fails_without_changing_the_existing_active_pointer():
    api = _api()
    center, effects = make_center(api)
    first, second = await _upload_two_versions(center)
    session = actor()

    await center.activate(
        session,
        document_type="daily_plan",
        version_id=first.template_version_id,
        expected_registry_revision=0,
        expected_active_version_id=None,
    )

    with pytest.raises(api.TemplateCenterError):
        await center.activate(
            session,
            document_type="daily_plan",
            version_id=second.template_version_id,
            expected_registry_revision=0,
            expected_active_version_id=None,
        )

    binding = await center.resolve_active(session, document_type="daily_plan")
    assert binding.template_version_id == first.template_version_id
    assert binding.content_sha256 == first.content_sha256
    assert len(effects["versions"].transitions) == 1
    assert [getattr(event, "action", None) for event in effects["audit"].events].count(
        "activate"
    ) == 1
    assert effects["audit"].events[-1].outcome == "stale"


@pytest.mark.asyncio
async def test_deactivation_blocks_export_but_keeps_validated_version_reactivatable():
    api = _api()
    center, effects = make_center(api)
    version, _other = await _upload_two_versions(center)
    session = actor()

    await center.activate(
        session,
        document_type="daily_plan",
        version_id=version.template_version_id,
        expected_registry_revision=0,
        expected_active_version_id=None,
    )
    await center.deactivate(
        session,
        document_type="daily_plan",
        expected_registry_revision=1,
        expected_active_version_id=version.template_version_id,
    )

    with pytest.raises(api.TemplateCenterError):
        await center.resolve_active(session, document_type="daily_plan")

    assert len(effects["versions"].versions) == 2
    assert version.content_sha256 in effects["blobs"].blobs
    assert version.validation_status == "validated"

    reactivated = await center.activate(
        session,
        document_type="daily_plan",
        version_id=version.template_version_id,
        expected_registry_revision=2,
        expected_active_version_id=None,
    )
    assert reactivated.active_version_id == version.template_version_id
    assert reactivated.registry_revision == 3
    binding = await center.resolve_active(session, document_type="daily_plan")
    assert binding.template_version_id == version.template_version_id
    assert binding.content_sha256 == version.content_sha256
    assert len(effects["versions"].versions) == 2
    assert len(effects["versions"].transitions) == 3
    assert effects["audit"].events[-2].action == "deactivate"
    assert effects["audit"].events[-1].action == "activate"


@pytest.mark.asyncio
async def test_transition_and_audit_are_not_visible_when_staging_audit_fails():
    api = _api()
    center, effects = make_center(api)
    version, _other = await _upload_two_versions(center)
    session = actor()
    effects["audit"].fail = True

    with pytest.raises(api.TemplateCenterError):
        await center.activate(
            session,
            document_type="daily_plan",
            version_id=version.template_version_id,
            expected_registry_revision=0,
            expected_active_version_id=None,
        )

    snapshot = await effects["versions"].snapshot(7, "daily_plan")
    assert snapshot.active_version_id is None
    assert effects["versions"].transitions == []
    assert [event.action for event in effects["audit"].events] == ["upload", "upload"]
    assert effects["transactions"].commit_attempts == 3
    assert effects["transactions"].commit_calls == 2
    assert effects["transactions"].units[-1].committed is False


@pytest.mark.asyncio
async def test_rollback_moves_only_the_active_pointer_and_preserves_each_immutable_version():
    api = _api()
    center, effects = make_center(api)
    first, second = await _upload_two_versions(center)
    session = actor()

    await center.activate(
        session,
        document_type="daily_plan",
        version_id=first.template_version_id,
        expected_registry_revision=0,
        expected_active_version_id=None,
    )
    await center.activate(
        session,
        document_type="daily_plan",
        version_id=second.template_version_id,
        expected_registry_revision=1,
        expected_active_version_id=first.template_version_id,
    )
    receipt = await center.rollback(
        session,
        document_type="daily_plan",
        target_version_id=first.template_version_id,
        expected_registry_revision=2,
        expected_active_version_id=second.template_version_id,
    )

    assert receipt.active_version_id == first.template_version_id
    assert receipt.content_sha256 == first.content_sha256
    assert [version.version for version in effects["versions"].versions] == [1, 2]
    assert [version.content_sha256 for version in effects["versions"].versions] == [
        first.content_sha256,
        second.content_sha256,
    ]
    assert [getattr(event, "action", None) for event in effects["audit"].events][
        -1
    ] == ("rollback")


@pytest.mark.asyncio
async def test_cross_tenant_lifecycle_reference_is_rejected_before_transition_and_is_audited_safely():
    api = _api()
    center, effects = make_center(api)
    foreign = await center.upload(
        actor(tenant_id=99, user_id=3),
        document_type="daily_plan",
        filename="foreign.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=docx_with_text("foreign version"),
    )

    with pytest.raises(api.TemplateCenterError):
        await center.activate(
            actor(tenant_id=7, user_id=11),
            document_type="daily_plan",
            version_id=foreign.template_version_id,
            expected_registry_revision=0,
            expected_active_version_id=None,
        )

    assert effects["versions"].transitions == []
    assert [getattr(event, "action", None) for event in effects["audit"].events] == [
        "upload",
        "activate",
    ]
    assert effects["audit"].events[-1].outcome == "denied"
