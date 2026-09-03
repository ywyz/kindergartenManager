"""模板中心上传安全、占位符和失败原子性的稳定 RED。"""

from importlib import import_module

import pytest

from _support import (
    actor,
    docx_with_external_relationship,
    docx_with_macro_member,
    docx_with_symlink_member,
    docx_with_text,
    docx_with_zipbomb,
    make_upload_center,
)


def _api():
    return import_module("app.service.template_center")


@pytest.mark.asyncio
async def test_same_content_deduplicates_blob_but_each_authorized_upload_gets_a_new_version():
    api = _api()
    center, effects = make_upload_center(api)
    content = docx_with_text("same bytes")

    first = await center.upload(
        actor(),
        document_type="daily_plan",
        filename="first.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=content,
    )
    second = await center.upload(
        actor(),
        document_type="daily_plan",
        filename="second.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=content,
    )

    assert first.content_sha256 == second.content_sha256
    assert first.template_version_id != second.template_version_id
    assert first.version == 1
    assert second.version == 2
    assert [call for call in effects["blobs"].calls if call[0] == "put"]
    assert len(effects["blobs"].blobs) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename",
    [
        "../escape.docx",
        "/tmp/absolute.docx",
        "nested/child.docx",
        r"nested\\child.docx",
        "template.docm",
        ".~lock.template.docx#",
    ],
)
async def test_upload_rejects_unsafe_or_non_docx_filenames_before_persistence(filename):
    api = _api()
    center, effects = make_upload_center(api)

    with pytest.raises(api.TemplateCenterError):
        await center.upload(
            actor(),
            document_type="daily_plan",
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content=docx_with_text("unsafe filename"),
        )

    assert effects["versions"].versions == []
    assert len(effects["audit"].events) == 1
    rejection = effects["audit"].events[0]
    assert rejection.action == "upload"
    assert rejection.outcome == "rejected"
    assert filename not in repr(rejection)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [
        b"not an OOXML package",
        docx_with_macro_member(),
        docx_with_external_relationship(),
        docx_with_symlink_member(),
        docx_with_zipbomb(),
    ],
    ids=["not-ooxml", "macro", "external-relationship", "symlink-member", "zipbomb"],
)
async def test_upload_rejects_malformed_or_active_content_before_version_commit(
    content,
):
    api = _api()
    center, effects = make_upload_center(api)

    with pytest.raises(api.TemplateCenterError):
        await center.upload(
            actor(),
            document_type="daily_plan",
            filename="candidate.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content=content,
        )

    assert effects["versions"].versions == []
    assert len(effects["audit"].events) == 1
    rejection = effects["audit"].events[0]
    assert rejection.action == "upload"
    assert rejection.outcome == "rejected"
    assert effects["versions"].transitions == []


@pytest.mark.asyncio
async def test_unknown_placeholder_is_rejected_without_leaking_placeholder_value():
    api = _api()
    center, effects = make_upload_center(api)
    value = "{{kg.daily_plan.not_declared}}"

    with pytest.raises(api.TemplateCenterError) as caught:
        await center.upload(
            actor(),
            document_type="daily_plan",
            filename="candidate.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content=docx_with_text(value),
        )

    assert value not in repr(caught.value)
    assert effects["versions"].versions == []
    assert len(effects["audit"].events) == 1
    rejection = effects["audit"].events[0]
    assert rejection.action == "upload"
    assert rejection.outcome == "rejected"
    assert value not in repr(rejection)


@pytest.mark.asyncio
async def test_audit_failure_does_not_publish_a_version_or_active_pointer():
    api = _api()
    center, effects = make_upload_center(api)
    effects["audit"].fail = True

    with pytest.raises(api.TemplateCenterError):
        await center.upload(
            actor(),
            document_type="daily_plan",
            filename="audit-failure.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content=docx_with_text("audit failure"),
        )

    assert effects["versions"].versions == []
    assert effects["versions"].transitions == []
    assert effects["audit"].events == []
    assert effects["transactions"].commit_attempts == 1
    assert effects["transactions"].commit_calls == 0
    assert effects["transactions"].units[-1].committed is False
