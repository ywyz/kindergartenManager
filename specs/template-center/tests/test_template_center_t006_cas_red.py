"""Independent T006 RED for scoped, atomic active-pointer lifecycle."""

from __future__ import annotations

import asyncio
from importlib import import_module
from uuid import uuid4

import pytest

from _support import actor, docx_with_text, make_lifecycle_center


def _api():
    return import_module("app.service.template_center")


async def _upload(center, *, tenant_id: int = 7, label: str = "candidate"):
    return await center.upload(
        actor(tenant_id=tenant_id),
        document_type="daily_plan",
        filename=f"{label}.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=docx_with_text(label),
    )


def test_empty_registry_state_is_an_explicit_revision_zero_value() -> None:
    api = _api()

    state = api.TemplateRegistryState(
        tenant_id=7,
        document_type=api.DocumentType.DAILY_PLAN,
        registry_revision=0,
        active_version_id=None,
        active_content_sha256=None,
        last_transition_event_id=None,
    )

    assert state.registry_revision == 0
    assert state.last_transition_event_id is None


@pytest.mark.asyncio
async def test_expected_active_mismatch_is_stale_and_preserves_pointer() -> None:
    api = _api()
    center, effects = make_lifecycle_center(api)
    version = await _upload(center)
    session = actor()
    await center.activate(
        session,
        document_type="daily_plan",
        version_id=version.template_version_id,
        expected_registry_revision=0,
        expected_active_version_id=None,
    )

    with pytest.raises(api.TemplateCenterError) as caught:
        await center.deactivate(
            session,
            document_type="daily_plan",
            expected_registry_revision=1,
            expected_active_version_id=uuid4(),
        )

    assert caught.value.code is api.TemplateErrorCode.REGISTRY_STALE
    snapshot = await effects["versions"].snapshot(7, "daily_plan")
    assert snapshot.active_version_id == version.template_version_id
    assert len(effects["versions"].transitions) == 1
    assert effects["audit"].events[-1].action is api.TemplateCapability.DEACTIVATE
    assert effects["audit"].events[-1].outcome is api.AuditOutcome.STALE


@pytest.mark.asyncio
async def test_same_cas_concurrent_activations_have_exactly_one_winner() -> None:
    api = _api()
    center, effects = make_lifecycle_center(api)
    first = await _upload(center, label="first")
    second = await _upload(center, label="second")
    session = actor()

    results = await asyncio.gather(
        center.activate(
            session,
            document_type="daily_plan",
            version_id=first.template_version_id,
            expected_registry_revision=0,
            expected_active_version_id=None,
        ),
        center.activate(
            session,
            document_type="daily_plan",
            version_id=second.template_version_id,
            expected_registry_revision=0,
            expected_active_version_id=None,
        ),
        return_exceptions=True,
    )

    receipts = [result for result in results if type(result) is api.TransitionReceipt]
    failures = [result for result in results if type(result) is api.TemplateCenterError]
    assert len(receipts) == 1
    assert len(failures) == 1
    assert failures[0].code is api.TemplateErrorCode.REGISTRY_STALE
    assert len(effects["versions"].transitions) == 1
    assert effects["audit"].events[-2].outcome is api.AuditOutcome.ACCEPTED
    assert effects["audit"].events[-1].outcome is api.AuditOutcome.STALE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", ("fail_stage_transition", "fail_stage_audit", "fail_commit")
)
async def test_lifecycle_failure_is_atomic_over_existing_pointer(failure: str) -> None:
    api = _api()
    center, effects = make_lifecycle_center(api)
    first = await _upload(center, label="first")
    second = await _upload(center, label="second")
    session = actor()
    await center.activate(
        session,
        document_type="daily_plan",
        version_id=first.template_version_id,
        expected_registry_revision=0,
        expected_active_version_id=None,
    )
    transactions = effects["transactions"]
    setattr(transactions, failure, True)
    before_versions = tuple(effects["versions"].versions)
    before_transitions = tuple(effects["versions"].transitions)
    before_audits = tuple(effects["audit"].events)

    with pytest.raises(api.TemplateCenterError) as caught:
        await center.activate(
            session,
            document_type="daily_plan",
            version_id=second.template_version_id,
            expected_registry_revision=1,
            expected_active_version_id=first.template_version_id,
        )

    assert caught.value.code is api.TemplateErrorCode.STORAGE_FAILED
    snapshot = await effects["versions"].snapshot(7, "daily_plan")
    assert snapshot.active_version_id == first.template_version_id
    assert tuple(effects["versions"].versions) == before_versions
    assert tuple(effects["versions"].transitions) == before_transitions
    assert tuple(effects["audit"].events) == before_audits


@pytest.mark.asyncio
async def test_active_pointer_and_revision_are_tenant_scoped() -> None:
    api = _api()
    center, effects = make_lifecycle_center(api)
    tenant_seven = await _upload(center, tenant_id=7, label="tenant-seven")
    tenant_nine = await _upload(center, tenant_id=9, label="tenant-nine")

    await center.activate(
        actor(tenant_id=7),
        document_type="daily_plan",
        version_id=tenant_seven.template_version_id,
        expected_registry_revision=0,
        expected_active_version_id=None,
    )
    await center.activate(
        actor(tenant_id=9),
        document_type="daily_plan",
        version_id=tenant_nine.template_version_id,
        expected_registry_revision=0,
        expected_active_version_id=None,
    )

    seven = await effects["versions"].snapshot(7, "daily_plan")
    nine = await effects["versions"].snapshot(9, "daily_plan")
    assert (seven.registry_revision, seven.active_version_id) == (
        1,
        tenant_seven.template_version_id,
    )
    assert (nine.registry_revision, nine.active_version_id) == (
        1,
        tenant_nine.template_version_id,
    )


@pytest.mark.asyncio
async def test_accepted_transition_audit_is_complete_and_redacted() -> None:
    api = _api()
    center, effects = make_lifecycle_center(api)
    version = await _upload(center)
    session = actor()

    await center.activate(
        session,
        document_type="daily_plan",
        version_id=version.template_version_id,
        expected_registry_revision=0,
        expected_active_version_id=None,
    )

    event = effects["audit"].events[-1]
    assert event.action is api.TemplateCapability.ACTIVATE
    assert event.outcome is api.AuditOutcome.ACCEPTED
    assert event.tenant_id == session.tenant_id
    assert event.user_id == session.user_id
    assert event.session_hash != str(session.session_id)
    assert event.template_version_id == version.template_version_id
    assert event.content_sha256 == version.content_sha256
    assert event.contract_id == version.contract_id
    assert event.contract_version == version.contract_version
    assert event.registry_revision == 1
    assert event.occurred_at_utc.tzinfo is not None
    assert event.schema_version == 1
    assert not hasattr(event, "blob_ref")
    assert not hasattr(event, "content")
