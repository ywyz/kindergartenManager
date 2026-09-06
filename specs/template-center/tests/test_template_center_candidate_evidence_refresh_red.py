"""Stable RED for append-only qualification of the sanitized candidate bytes."""

from hashlib import sha256
from importlib import import_module
from pathlib import Path

import pytest


WEEKLY_V2_SHA256 = "f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b"
MONTHLY_V2_SHA256 = "f2e5dbe2a468dd15c55cdd6b70c5e15fe63048a3708b151732e208703b0d11f4"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _api():
    return import_module("app.service.template_center")


def _candidate_profile(document_type, seed_handle, profile_id):
    registry = import_module("app.service.template_center.registry")
    return registry.candidate_profile(document_type, seed_handle, profile_id)


def _profile_rows(api):
    return tuple(
        (
            profile.document_type.value,
            profile.seed_handle.handle_id,
            profile.seed_handle.expected_sha256,
            profile.profile_id,
            profile.profile_version,
            profile.contract.contract_version,
            profile.contract.structural_profile_version,
            profile.fixture_id,
            profile.contract.renderer_id,
            profile.contract.parser_id,
            profile.contract.required_anchors,
        )
        for profile in api.CANDIDATE_QUALIFICATION_PROFILES
    )


def test_candidate_profiles_append_v2_without_rebinding_historical_v1():
    api = _api()

    assert _profile_rows(api) == (
        (
            "weekly_activity_plan",
            "controlled-weekplan-seed-v1",
            "226c8208659bb6334533499b417aaf5f7ccad1e82d3a7cd6b8955d91a2b6417a",
            "weekly_activity_plan-profile-v1",
            1,
            1,
            1,
            "weekly-monthly-fixture-v1",
            "kg.renderer.weekly_activity_plan.candidate.v1",
            "kg.parser.weekly_activity_plan.candidate.v1",
            ("tables:word/document.xml:2x9x7",),
        ),
        (
            "monthly_theme_activity_plan",
            "controlled-monthplan-seed-v1",
            "787f1a9be8aaebd27cf87c25747a3f8e70e584ac5bfd1c068ffedc2df54a4ac6",
            "monthly_theme_activity_plan-profile-v1",
            1,
            1,
            1,
            "weekly-monthly-fixture-v1",
            "kg.renderer.monthly_theme_activity_plan.candidate.v1",
            "kg.parser.monthly_theme_activity_plan.candidate.v1",
            ("tables:word/document.xml:1x8x4",),
        ),
        (
            "weekly_activity_plan",
            "controlled-weekplan-seed-v2",
            WEEKLY_V2_SHA256,
            "weekly_activity_plan-profile-v2",
            2,
            2,
            2,
            "weekly-monthly-fixture-v1",
            "kg.renderer.weekly_activity_plan.candidate.v1",
            "kg.parser.weekly_activity_plan.candidate.v1",
            ("tables:word/document.xml:2x9x7",),
        ),
        (
            "monthly_theme_activity_plan",
            "controlled-monthplan-seed-v2",
            MONTHLY_V2_SHA256,
            "monthly_theme_activity_plan-profile-v2",
            2,
            2,
            2,
            "weekly-monthly-fixture-v1",
            "kg.renderer.monthly_theme_activity_plan.candidate.v1",
            "kg.parser.monthly_theme_activity_plan.candidate.v1",
            ("tables:word/document.xml:1x8x4",),
        ),
    )


@pytest.mark.parametrize(
    ("document_type", "seed_handle", "profile_id"),
    [
        (
            "weekly_activity_plan",
            "controlled-weekplan-seed-v1",
            "weekly_activity_plan-profile-v2",
        ),
        (
            "weekly_activity_plan",
            "controlled-weekplan-seed-v2",
            "weekly_activity_plan-profile-v1",
        ),
        (
            "monthly_theme_activity_plan",
            "controlled-monthplan-seed-v1",
            "monthly_theme_activity_plan-profile-v2",
        ),
        (
            "monthly_theme_activity_plan",
            "controlled-monthplan-seed-v2",
            "monthly_theme_activity_plan-profile-v1",
        ),
    ],
    ids=["weekly-v1-v2", "weekly-v2-v1", "monthly-v1-v2", "monthly-v2-v1"],
)
def test_candidate_profile_resolver_rejects_cross_version_combinations(
    document_type, seed_handle, profile_id
):
    api = _api()

    with pytest.raises(api.TemplateCenterError) as caught:
        _candidate_profile(document_type, seed_handle, profile_id)

    assert caught.value.code is api.TemplateErrorCode.INPUT_INVALID


@pytest.mark.parametrize(
    ("document_type", "seed_handle", "profile_id", "filename", "expected_sha256"),
    [
        (
            "weekly_activity_plan",
            "controlled-weekplan-seed-v2",
            "weekly_activity_plan-profile-v2",
            "weekplan.docx",
            WEEKLY_V2_SHA256,
        ),
        (
            "monthly_theme_activity_plan",
            "controlled-monthplan-seed-v2",
            "monthly_theme_activity_plan-profile-v2",
            "monthplan.docx",
            MONTHLY_V2_SHA256,
        ),
    ],
    ids=["weekly-v2", "monthly-v2"],
)
def test_current_candidate_bytes_match_v2_profile_and_unique_validator(
    document_type, seed_handle, profile_id, filename, expected_sha256
):
    api = _api()
    content = (_REPOSITORY_ROOT / "templates" / filename).read_bytes()
    profile = _candidate_profile(document_type, seed_handle, profile_id)

    assert sha256(content).hexdigest() == expected_sha256
    receipt = api.validate_upload(
        content,
        filename,
        api.DOCX_MIME_TYPE,
        profile.contract,
    )
    assert receipt.content_sha256 == expected_sha256
    assert receipt.structural_profile_id == profile_id
    assert receipt.structural_profile_version == profile.profile_version == 2


def test_reserved_types_remain_disabled_after_v2_profiles_are_registered():
    api = _api()
    registry = api.build_initial_document_registry()

    assert api.PHASE1_RESERVED_DOCUMENT_TYPES == (
        "weekly_activity_plan",
        "monthly_theme_activity_plan",
    )
    assert registry.is_enabled("weekly_activity_plan") is False
    assert registry.is_enabled("monthly_theme_activity_plan") is False
