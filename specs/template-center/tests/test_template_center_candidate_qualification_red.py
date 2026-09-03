"""T011 周/月候选模板资格门的稳定 RED。

候选资格是受控 seed/fixture 的内部校验 job，不是 TemplateCenter 的正式 Preview 或 CRUD。
"""

from importlib import import_module

import pytest

from _support import (
    MemoryControlledSeedStore,
    MemoryExportPort,
    MemoryOfficeQualificationPort,
    MemoryQualificationEvidenceStore,
    RESERVED_TYPES,
    docx_with_external_relationship,
    docx_with_macro_member,
    docx_with_structure_profile_mismatch,
    OFFICE_CLIENT_VERSIONS,
)


def _api():
    return import_module("app.service.template_center")


def _job(api, *, seeds=None, office=None):
    seeds = seeds or MemoryControlledSeedStore()
    export = MemoryExportPort()
    office = office or MemoryOfficeQualificationPort()
    evidence = MemoryQualificationEvidenceStore()
    job = api.TemplateCandidateQualificationJob(
        controlled_seed_store=seeds,
        export_port=export,
        office_qualification_port=office,
        qualification_evidence_store=evidence,
    )
    return job, {
        "seeds": seeds,
        "export": export,
        "office": office,
        "evidence": evidence,
    }


def _fixture(api, *, provenance="synthetic"):
    return api.SyntheticQualificationFixture(
        fixture_id="weekly-monthly-fixture-v1",
        provenance=provenance,
        values={"title": "仅用于候选资格的合成值"},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("document_type", "seed_handle"),
    [
        ("weekly_activity_plan", "controlled-weekplan-seed-v1"),
        ("monthly_theme_activity_plan", "controlled-monthplan-seed-v1"),
    ],
)
async def test_reserved_candidate_qualification_uses_controlled_seed_and_same_opaque_export_port(
    document_type, seed_handle
):
    api = _api()
    job, effects = _job(api)

    evidence = await job.qualify(
        document_type=document_type,
        seed_handle=seed_handle,
        fixture=_fixture(api),
        profile_id=f"{document_type}-profile-v1",
    )

    assert evidence.document_type == document_type
    assert evidence.qualification_status == "passed"
    assert len(evidence.seed_sha256) == 64
    assert evidence.profile_id == f"{document_type}-profile-v1"
    assert len(evidence.rendered_sha256) == 64
    assert len(evidence.parse_report_sha256) == 64
    assert evidence.profile_version == 1
    assert evidence.office_evidence_id == "office-qualification-v1"
    assert evidence.office_client_versions
    assert evidence.fixture_id == "weekly-monthly-fixture-v1"
    assert not hasattr(evidence, "rendered_bytes")
    assert not hasattr(evidence, "seed_bytes")
    assert not hasattr(evidence, "absolute_path")
    assert not hasattr(evidence, "active_version_id")
    assert not hasattr(evidence, "template_version_id")
    assert effects["seeds"].read_calls == [(seed_handle, document_type)]
    assert len(effects["export"].render_calls) == 1
    assert len(effects["export"].parse_calls) == 1
    assert effects["export"].resolve_calls == []
    assert len(effects["office"].calls) == 1
    assert effects["evidence"].items == [evidence]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_id", "seed_content"),
    [
        ("macro", docx_with_macro_member()),
        ("external-rel", docx_with_external_relationship()),
        ("bad-zip", b"registered candidate but not a ZIP package"),
        ("structure-profile-mismatch", docx_with_structure_profile_mismatch()),
    ],
    ids=["macro", "external-rel", "bad-zip", "structure-profile-mismatch"],
)
async def test_registered_candidate_seed_reuses_security_validator_and_fails_before_render_or_office(
    case_id, seed_content
):
    """A registered handle is not a trust bypass: security/profile failures stop the pipeline."""
    api = _api()
    seed_handle = f"controlled-weekplan-{case_id}-v1"
    seeds = MemoryControlledSeedStore()
    seeds.register_controlled_seed(seed_handle, seed_content)
    job, effects = _job(api, seeds=seeds)

    with pytest.raises(api.TemplateCenterError):
        await job.qualify(
            document_type="weekly_activity_plan",
            seed_handle=seed_handle,
            fixture=_fixture(api),
            profile_id="weekly_activity_plan-profile-v1",
        )

    # This is deliberately distinct from preflight rejection: the controlled seed
    # was read, but the shared byte/ZIP/XML/profile validator stopped the pipeline.
    assert effects["seeds"].read_calls == [(seed_handle, "weekly_activity_plan")]
    assert effects["export"].render_calls == []
    assert effects["export"].parse_calls == []
    assert effects["office"].calls == []
    assert not any(
        getattr(item, "qualification_status", None) == "passed"
        for item in effects["evidence"].items
    )
    assert effects["export"].resolve_calls == []
    assert (
        api.build_initial_document_registry().is_enabled("weekly_activity_plan")
        is False
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_id", "status", "evidence_id", "client_versions"),
    [
        ("office-failed", "failed", "office-failure-v1", OFFICE_CLIENT_VERSIONS),
        ("missing-word", "passed", "office-without-word-v1", ("libreoffice/24.2.7.2",)),
        (
            "missing-libreoffice",
            "passed",
            "office-without-libreoffice-v1",
            ("word/16.0.17328.20124",),
        ),
        ("missing-evidence-id", "passed", None, OFFICE_CLIENT_VERSIONS),
        (
            "missing-exact-client-version",
            "passed",
            "office-unversioned-v1",
            ("word", "libreoffice"),
        ),
    ],
    ids=[
        "office-failed",
        "missing-word",
        "missing-libreoffice",
        "missing-evidence-id",
        "missing-exact-client-version",
    ],
)
async def test_incomplete_office_qualification_fails_after_render_without_passed_evidence_or_enablement(
    case_id, status, evidence_id, client_versions
):
    """Office evidence is an independent required gate, not a best-effort annotation."""
    api = _api()
    office = MemoryOfficeQualificationPort(
        status=status,
        evidence_id=evidence_id,
        client_versions=client_versions,
    )
    job, effects = _job(api, office=office)

    with pytest.raises(api.TemplateCenterError):
        await job.qualify(
            document_type="weekly_activity_plan",
            seed_handle="controlled-weekplan-seed-v1",
            fixture=_fixture(api),
            profile_id="weekly_activity_plan-profile-v1",
        )

    # The seed passed the common security/profile stage, so render/parse and the
    # Office call are observable; the incomplete Office result must still fail closed.
    assert effects["seeds"].read_calls == [
        ("controlled-weekplan-seed-v1", "weekly_activity_plan")
    ]
    assert len(effects["export"].render_calls) == 1
    assert len(effects["export"].parse_calls) == 1
    assert len(effects["office"].calls) == 1
    assert not any(
        getattr(item, "qualification_status", None) == "passed"
        for item in effects["evidence"].items
    )
    assert effects["export"].resolve_calls == []
    assert (
        api.build_initial_document_registry().is_enabled("weekly_activity_plan")
        is False
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("document_type", "seed_handle", "provenance"),
    [
        ("weekly_activity_plan", "../templates/weekplan.docx", "synthetic"),
        ("monthly_theme_activity_plan", "controlled-monthplan-seed-v1", "business"),
        ("daily_plan", "controlled-weekplan-seed-v1", "synthetic"),
        ("unknown_type", "controlled-weekplan-seed-v1", "synthetic"),
    ],
)
async def test_candidate_qualification_rejects_uncontrolled_or_non_reserved_inputs_without_side_effects(
    document_type, seed_handle, provenance
):
    api = _api()
    job, effects = _job(api)

    with pytest.raises(api.TemplateCenterError) as caught:
        await job.qualify(
            document_type=document_type,
            seed_handle=seed_handle,
            fixture=_fixture(api, provenance=provenance),
            profile_id="candidate-profile-v1",
        )

    assert seed_handle not in repr(caught.value)
    assert effects["seeds"].read_calls == []
    assert effects["export"].render_calls == []
    assert effects["export"].parse_calls == []
    assert effects["export"].resolve_calls == []
    assert effects["office"].calls == []
    assert effects["evidence"].items == []


@pytest.mark.asyncio
async def test_qualification_is_not_formal_preview_or_enablement_and_exposes_no_public_crud():
    api = _api()
    job, effects = _job(api)

    evidence = await job.qualify(
        document_type=RESERVED_TYPES[0],
        seed_handle="controlled-weekplan-seed-v1",
        fixture=_fixture(api),
        profile_id="weekly_activity_plan-profile-v1",
    )
    registry = api.build_initial_document_registry()

    assert evidence.qualification_status == "passed"
    assert registry.is_enabled(RESERVED_TYPES[0]) is False
    assert tuple(descriptor.key for descriptor in registry.descriptors()) == (
        "daily_plan",
        "game_observation",
        "one_on_one_listening",
        "homemade_teaching",
        "course_review_activity",
    )
    for forbidden in (
        "project",
        "upload",
        "preview",
        "resolve_active",
        "activate",
        "deactivate",
        "rollback",
        "download",
        "formal_download",
        "read_business",
        "write_business",
        "create_version",
    ):
        assert not hasattr(job, forbidden)
    assert not hasattr(evidence, "rendered_bytes")
    assert not hasattr(evidence, "content")
    assert not hasattr(evidence, "active_version_id")
    assert effects["export"].resolve_calls == []
