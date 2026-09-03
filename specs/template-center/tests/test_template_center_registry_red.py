"""模板中心 registry、版本引用和权限投影的稳定 RED。"""

from importlib import import_module
from uuid import uuid4

import pytest

from _support import (
    INITIAL_TYPES,
    KNOWN_TYPES,
    RESERVED_TYPES,
    actor,
    docx_with_text,
    make_center,
)


def _api():
    # 延迟导入：正式 seam 缺失时仍必须 collection clean。
    return import_module("app.service.template_center")


def test_initial_registry_is_closed_and_defers_week_month_types():
    api = _api()
    registry = api.build_initial_document_registry()

    assert tuple(registry.known_keys()) == KNOWN_TYPES
    descriptors = registry.descriptors()
    assert tuple(descriptor.key for descriptor in descriptors) == INITIAL_TYPES

    for reserved in RESERVED_TYPES:
        assert registry.is_enabled(reserved) is False
        with pytest.raises(api.TemplateCenterError):
            registry.resolve(reserved)


@pytest.mark.asyncio
async def test_phase1_reserved_types_are_rejected_by_projection_upload_activation_and_export_resolution():
    api = _api()
    center, effects = make_center(api)
    session = actor()

    for reserved in RESERVED_TYPES:
        with pytest.raises(api.TemplateCenterError):
            await center.project(session, document_type=reserved)
        with pytest.raises(api.TemplateCenterError):
            await center.upload(
                session,
                document_type=reserved,
                filename="reserved.docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                content=docx_with_text("reserved type"),
            )
        with pytest.raises(api.TemplateCenterError):
            await center.activate(
                session,
                document_type=reserved,
                version_id=uuid4(),
                expected_registry_revision=0,
                expected_active_version_id=None,
            )
        with pytest.raises(api.TemplateCenterError):
            await center.resolve_active(session, document_type=reserved)

    assert effects["blobs"].calls == []
    assert effects["versions"].versions == []
    assert effects["versions"].transitions == []


@pytest.mark.asyncio
async def test_uploaded_version_is_immutable_and_returns_only_content_addressed_evidence():
    api = _api()
    center, _effects = make_center(api)

    version = await center.upload(
        actor(),
        document_type="daily_plan",
        filename="daily-plan.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=docx_with_text("synthetic registry fixture"),
    )

    assert version.document_type == "daily_plan"
    assert version.version == 1
    assert version.validation_receipt_id
    assert version.validation_status == "validated"
    assert len(version.content_sha256) == 64
    assert version.blob_ref == f"sha256/{version.content_sha256}"
    assert not hasattr(version, "content")
    assert not hasattr(version, "absolute_path")
    with pytest.raises((AttributeError, TypeError)):
        version.version = 99
    with pytest.raises((AttributeError, TypeError)):
        version.validation_status = "invalid"


@pytest.mark.asyncio
async def test_permission_projection_is_tenant_scoped_and_contains_no_storage_or_secret_data():
    api = _api()
    center, _effects = make_center(api)
    session = actor(tenant_id=23, user_id=41, role="teacher")

    projection = await center.project(session, document_type="daily_plan")

    assert projection.tenant_id == 23
    assert projection.document_type == "daily_plan"
    assert isinstance(projection.allowed_actions, tuple)
    rendered = repr(projection)
    assert "sha256/" not in rendered
    assert "absolute" not in rendered.lower()
    assert "password" not in rendered.lower()
    assert "api_key" not in rendered.lower()


@pytest.mark.asyncio
async def test_policy_default_deny_happens_before_blob_or_version_side_effects_and_is_audited_safely():
    api = _api()
    from _support import AllowPolicy

    center, effects = make_center(api, policy=AllowPolicy(allowed={"read"}))

    with pytest.raises(api.TemplateCenterError):
        await center.upload(
            actor(role="teacher"),
            document_type="daily_plan",
            filename="daily-plan.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content=docx_with_text("denied"),
        )

    assert effects["blobs"].calls == []
    assert effects["versions"].versions == []
    assert len(effects["audit"].events) == 1
    denial = effects["audit"].events[0]
    assert denial.action == "upload"
    assert denial.outcome == "denied"


@pytest.mark.asyncio
async def test_export_resolution_is_tenant_scoped_and_does_not_call_renderer():
    api = _api()
    center, effects = make_center(api)

    foreign = await center.upload(
        actor(tenant_id=99, user_id=3),
        document_type="daily_plan",
        filename="foreign.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=docx_with_text("foreign"),
    )

    with pytest.raises(api.TemplateCenterError):
        await center.resolve_active(actor(tenant_id=7), document_type="daily_plan")

    assert effects["exports"].render_calls == []
    assert effects["exports"].resolve_calls == [(7, "daily_plan")]
    assert foreign.tenant_id == 99
