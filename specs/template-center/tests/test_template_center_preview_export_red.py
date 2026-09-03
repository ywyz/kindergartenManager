"""模板中心合成预览和导出解析端口的稳定 RED。"""

from importlib import import_module

import pytest

from _support import actor, docx_with_text, make_center


def _api():
    return import_module("app.service.template_center")


async def _active_center(api):
    center, effects = make_center(api)
    version = await center.upload(
        actor(),
        document_type="daily_plan",
        filename="preview.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=docx_with_text("preview fixture"),
    )
    await center.activate(
        actor(),
        document_type="daily_plan",
        version_id=version.template_version_id,
        expected_registry_revision=0,
        expected_active_version_id=None,
    )
    return center, effects, version


@pytest.mark.asyncio
async def test_preview_requires_explicit_synthetic_provenance_and_returns_version_evidence():
    api = _api()
    center, effects, version = await _active_center(api)
    case = api.SyntheticPreviewCase(
        provenance="synthetic",
        values={"title": "仅用于测试的合成值"},
    )

    receipt = await center.preview(
        actor(),
        document_type="daily_plan",
        version_id=version.template_version_id,
        synthetic_case=case,
    )

    assert receipt.template_version_id == version.template_version_id
    assert receipt.content_sha256 == version.content_sha256
    assert receipt.persisted is False
    assert receipt.rendered_bytes
    assert receipt.parse_report.valid is True
    assert len(effects["versions"].versions) == 1
    assert len(effects["versions"].transitions) == 1
    assert len(effects["exports"].render_calls) == 1
    assert len(effects["exports"].parse_calls) == 1


@pytest.mark.asyncio
async def test_preview_rejects_business_provenance_before_renderer_and_without_persisting_content():
    api = _api()
    center, effects, version = await _active_center(api)
    case = api.SyntheticPreviewCase(
        provenance="business",
        values={"child_name": "不得进入模板预览测试"},
    )

    with pytest.raises(api.TemplateCenterError) as caught:
        await center.preview(
            actor(),
            document_type="daily_plan",
            version_id=version.template_version_id,
            synthetic_case=case,
        )

    assert "不得进入模板预览测试" not in repr(caught.value)
    assert effects["exports"].render_calls == []
    assert len(effects["versions"].versions) == 1
    assert len(effects["versions"].transitions) == 1


@pytest.mark.asyncio
async def test_active_resolution_binds_exact_version_and_hash_without_exposing_blob_bytes_or_path():
    api = _api()
    center, effects, version = await _active_center(api)

    binding = await center.resolve_active(actor(), document_type="daily_plan")

    assert binding.template_version_id == version.template_version_id
    assert binding.version == version.version
    assert binding.content_sha256 == version.content_sha256
    assert binding.contract_id == version.contract_id
    assert not hasattr(binding, "content")
    assert not hasattr(binding, "absolute_path")
    assert effects["exports"].resolve_calls == [(7, "daily_plan")]


@pytest.mark.asyncio
async def test_no_active_version_fails_closed_and_never_falls_back_to_a_scratch_export():
    api = _api()
    center, effects = make_center(api)
    await center.upload(
        actor(),
        document_type="daily_plan",
        filename="not-active.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=docx_with_text("not active"),
    )

    with pytest.raises(api.TemplateCenterError):
        await center.resolve_active(actor(), document_type="daily_plan")

    assert effects["exports"].render_calls == []
    assert effects["exports"].parse_calls == []
    assert effects["exports"].resolve_calls == [(7, "daily_plan")]
