"""Catalog integrity and binding linearization; synthetic evidence only."""

import asyncio
import json
from hashlib import sha256

import pytest

from app.integration.word_export.shared_weekly_word import (
    SEED_SHA256,
    SharedWeeklyWordPort,
)
from app.service.shared_weekly.layout_authority import (
    LayoutAuthority,
    LayoutAuthorityRejected,
)
from app.service.shared_weekly.layout_contracts import PROFILE


def catalog(tmp_path, renderer_version="synthetic-test"):
    from app.integration.word_export import (
        released_weekly_monthly_word_port as released,
    )
    from app.service.template_center.contracts import DocumentType

    profile = released._profile(DocumentType.WEEKLY_ACTIVITY_PLAN)
    released_binding = {
        "template_version_id": str(
            released._RELEASED[DocumentType.WEEKLY_ACTIVITY_PLAN][1]
        ),
        "version": released._ACTIVE_VERSION,
        "content_sha256": SEED_SHA256,
        "contract_id": profile.contract.contract_id,
        "contract_version": profile.contract.contract_version,
    }
    client = {"product": "Synthetic test client", "version": "1"}
    renderer = {"product": "LibreOffice", "version": renderer_version}
    fixtures = []
    for columns in (5, 6):
        artifacts = {}
        for kind in ("docx", "pdf", "page-1.png"):
            raw = f"synthetic-{columns}-{kind}".encode()
            name = f"{columns}-{kind}"
            (tmp_path / name).write_bytes(raw)
            artifacts[kind] = {"file": name, "sha256": sha256(raw).hexdigest()}
        observation = {
            "schema": "weekly-layout-native-observation.v1",
            "role": "local-synthetic",
            "client": client,
            "renderer": renderer,
            "columns": columns,
            "body_sha256": "a" * 64,
            "template_sha256": SEED_SHA256,
            "profile": PROFILE,
            "pages": 1,
            "page_observations": ["all_text_visible_no_clipping_no_overflow"],
            "font": "SimSun",
            "font_pt": 12,
            "line_pt": 20,
            "fixed_counts": [2, 1, 3, 1, 3, 3, 3, 3, 3, 1],
            "docx_sha256": artifacts["docx"]["sha256"],
            "pdf_sha256": artifacts["pdf"]["sha256"],
            "png_sha256": artifacts["page-1.png"]["sha256"],
        }
        raw = json.dumps(observation).encode()
        name = f"{columns}-native-report.json"
        (tmp_path / name).write_bytes(raw)
        digest = sha256(raw).hexdigest()
        artifacts["native-report.json"] = {"file": name, "sha256": digest}
        fixtures.append(
            {
                "columns": columns,
                "body_sha256": "a" * 64,
                "artifacts": artifacts,
                "observation": digest,
            }
        )
    raw = json.dumps(
        {
            "schema": "weekly-layout-qualification.v1",
            "profile": PROFILE,
            "template_sha256": SEED_SHA256,
            "renderer": renderer,
            "client": client,
            "role": "local-synthetic",
            "fixtures": fixtures,
            "released_binding": released_binding,
        }
    ).encode()
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(raw)
    return {"synthetic": (manifest, sha256(raw).hexdigest())}


async def test_production_rejects_synthetic_qualification(tmp_path):
    authority = LayoutAuthority(catalog(tmp_path))
    with pytest.raises(LayoutAuthorityRejected, match="qualification_invalid"):
        await authority.activate(1, "synthetic", expected=None)


async def test_guard_serializes_activation_and_revalidates_current(tmp_path):
    authority = LayoutAuthority(catalog(tmp_path), local_only=True)
    first = await authority.activate(1, "synthetic", expected=None)
    async with authority.binding_guard(first):
        task = asyncio.create_task(authority.activate(1, "synthetic", expected=first))
        await asyncio.sleep(0)
        assert not task.done()
    second = await task
    assert first != second
    with pytest.raises(LayoutAuthorityRejected, match="template_changed"):
        async with authority.binding_guard(first):
            pytest.fail("stale binding delivered")
    assert await authority.resolve_binding(1) == second


async def test_evidence_tamper_revokes_current_binding(tmp_path):
    authority = LayoutAuthority(catalog(tmp_path), local_only=True)
    binding = await authority.activate(1, "synthetic", expected=None)
    (tmp_path / "5-page-1.png").write_bytes(b"tampered")
    with pytest.raises(LayoutAuthorityRejected, match="qualification_invalid"):
        async with authority.binding_guard(binding):
            pytest.fail("corrupt evidence delivered")


async def test_formal_port_rejects_renderer_drift(tmp_path):
    authority = LayoutAuthority(catalog(tmp_path), local_only=True)
    binding = await authority.activate(1, "synthetic", expected=None)
    with pytest.raises(ValueError, match="renderer_changed"):
        await SharedWeeklyWordPort(authority).render_check(binding, None, None)


async def test_formal_algorithm_with_local_qualification_actual_renderer(tmp_path):
    from app.integration.word_export.shared_weekly_word import _process
    from app.service.shared_weekly.layout_contracts import WeekDisplay
    from tests.test_wpe_word_layout import complete_body

    version = (await _process("libreoffice", "--version")).decode().strip()
    authority = LayoutAuthority(catalog(tmp_path, version), local_only=True)
    binding = await authority.activate(1, "synthetic", expected=None)
    port = SharedWeeklyWordPort(authority)
    body = complete_body()
    result = await port.render_check(
        binding, body, WeekDisplay("小一班", "第一学期", 3)
    )
    assert result.binding == binding
    assert result.payload_hash == sha256(body.serialize().encode()).hexdigest()
    assert result.fits and result.pages == 1 and result.data
    assert binding.active_version.startswith("local-synthetic:")


async def test_current_released_active_version_change_invalidates_qualification(
    tmp_path, monkeypatch
):
    from app.integration.word_export import (
        released_weekly_monthly_word_port as released,
    )

    authority = LayoutAuthority(catalog(tmp_path), local_only=True)
    binding = await authority.activate(1, "synthetic", expected=None)
    monkeypatch.setattr(released, "_ACTIVE_VERSION", released._ACTIVE_VERSION + 1)
    with pytest.raises(LayoutAuthorityRejected, match="template_changed"):
        await authority.resolve_binding(binding.tenant_id)
