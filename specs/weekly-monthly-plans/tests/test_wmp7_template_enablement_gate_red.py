"""WMP-7/T011-E template type enablement stable RED.

The gate consumes only the closed WMP-6 receipt and delegates to the frozen
template-center export port.  Its business surface is active opaque bindings;
it does not publish registry objects or implement the WMP-8 exporter.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from uuid import UUID, uuid4

import pytest

MODULE_NAME = "app.service.weekly_monthly_plans.template_enablement"
WEEKLY_SHA256 = "f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b"
MONTHLY_SHA256 = "f2e5dbe2a468dd15c55cdd6b70c5e15fe63048a3708b151732e208703b0d11f4"
WEEKLY = "weekly_activity_plan"
MONTHLY = "monthly_theme_activity_plan"


def _api():
    return import_module(MODULE_NAME)


def _orchestration():
    return import_module("app.service.weekly_monthly_plans.qualification_orchestration")


def _template_center():
    return import_module("app.service.template_center")


class _CurrentQualificationJob:
    async def qualify(self, document_type, seed_handle, fixture, profile_id):
        tc = _template_center()
        profiles = {
            profile.document_type.value: profile
            for profile in tc.CANDIDATE_QUALIFICATION_PROFILES
            if profile.profile_version == 2
        }
        profile = profiles[document_type]
        assert seed_handle == profile.seed_handle.handle_id
        assert profile_id == profile.profile_id
        return tc.CandidateQualificationEvidence(
            qualification_id=uuid4(),
            document_type=profile.document_type,
            seed_sha256=profile.seed_handle.expected_sha256,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            rendered_sha256=profile.seed_handle.expected_sha256,
            parse_report_sha256=(
                "dab4a78999831c486f9df25400f82800d2f4ff18ce076571cc9c64a830efe9c6"
                if document_type.startswith("weekly")
                else "2c97f5602d9afbd45b240871a5f5b1ea789cccabcc566378c776f1c2b63829a4"
            ),
            office_evidence_id=(
                "candidate-refresh-20260906-weekly-v2-lo-26.2.5.2"
                if document_type.startswith("weekly")
                else "candidate-refresh-20260906-monthly-v2-lo-26.2.5.2"
            ),
            office_client_versions=("libreoffice/26.2.5.2",),
            office_compatibility_targets=("microsoft-word/ooxml-docx",),
            fixture_id=fixture.fixture_id,
            checker_version="template-candidate-qualification.v2",
            qualified_at_utc=datetime(2026, 9, 6, tzinfo=UTC),
            qualification_status=tc.QualificationStatus.PASSED,
        )


class _ActiveExportPort:
    def __init__(self, overrides=None):
        self.overrides = overrides or {}
        self.calls = []

    async def resolve_active(self, tenant_id, document_type):
        tc = _template_center()
        self.calls.append((tenant_id, document_type))
        profile = next(
            item
            for item in tc.CANDIDATE_QUALIFICATION_PROFILES
            if item.document_type is document_type and item.profile_version == 2
        )
        values = {
            "document_type": document_type,
            "content_sha256": profile.seed_handle.expected_sha256,
            "contract_id": profile.contract.contract_id,
            "contract_version": profile.contract.contract_version,
            "tenant_id": tenant_id,
            "template_version_id": UUID(
                "00000000-0000-0000-0000-000000000101"
                if document_type.value == WEEKLY
                else "00000000-0000-0000-0000-000000000102"
            ),
            "version": 7,
        }
        values.update(self.overrides)
        return tc.TemplateExportBinding(**values)


async def _receipt():
    q = _orchestration()
    return await q.WeeklyMonthlyQualificationOrchestrator(
        _CurrentQualificationJob()
    ).run(
        q.WeeklyMonthlyQualificationRequest(
            weekly_snapshot=q.WeeklySyntheticQualificationSnapshot(
                snapshot_id="weekly-qualification-snapshot-v1",
                provenance="synthetic",
                plan=q._canonical_weekly_plan(),
                captured_at_utc=datetime(2026, 9, 6, tzinfo=UTC),
            ),
            monthly_snapshot=q.MonthlySyntheticQualificationSnapshot(
                snapshot_id="monthly-qualification-snapshot-v1",
                provenance="synthetic",
                plan=q._canonical_monthly_plan(),
                captured_at_utc=datetime(2026, 9, 6, tzinfo=UTC),
            ),
        )
    )


@pytest.mark.asyncio
async def test_wmp7_enables_exactly_the_two_reserved_document_types():
    gate = _api()
    port = _ActiveExportPort()
    active_gate = gate.build_weekly_monthly_active_binding_gate(await _receipt(), port)

    weekly = await active_gate.resolve_active(17, WEEKLY)
    monthly = await active_gate.resolve_active(17, MONTHLY)
    assert (
        weekly.kind
        is monthly.kind
        is _template_center().TemplateExportBindingKind.ACTIVE
    )
    assert [item[1].value for item in port.calls] == [WEEKLY, MONTHLY]
    with pytest.raises(gate.TemplateTypeEnablementError):
        await active_gate.resolve_active(17, "daily_plan")
    assert len(port.calls) == 2


@pytest.mark.asyncio
async def test_wmp7_descriptors_pin_current_candidate_hash_profile_and_contract():
    gate = _api()
    active_gate = gate.build_weekly_monthly_active_binding_gate(
        await _receipt(), _ActiveExportPort()
    )

    weekly = await active_gate.resolve_active(17, WEEKLY)
    monthly = await active_gate.resolve_active(17, MONTHLY)
    assert (weekly.content_sha256, monthly.content_sha256) == (
        WEEKLY_SHA256,
        MONTHLY_SHA256,
    )
    assert weekly.contract_id == "kg.template.weekly_activity_plan.candidate"
    assert monthly.contract_id == "kg.template.monthly_theme_activity_plan.candidate"
    assert weekly.contract_version == monthly.contract_version == 2

    mismatched = gate.build_weekly_monthly_active_binding_gate(
        await _receipt(), _ActiveExportPort({"content_sha256": "0" * 64})
    )
    with pytest.raises(gate.TemplateTypeEnablementError) as caught:
        await mismatched.resolve_active(17, WEEKLY)
    assert caught.value.code is gate.TemplateTypeEnablementErrorCode.BINDING_INVALID


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [None, object(), "receipt"])
async def test_wmp7_missing_or_wrong_receipt_fails_closed(bad):
    gate = _api()
    with pytest.raises(gate.TemplateTypeEnablementError) as caught:
        gate.build_weekly_monthly_active_binding_gate(bad, _ActiveExportPort())
    assert caught.value.code is gate.TemplateTypeEnablementErrorCode.RECEIPT_INVALID


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field",
    [
        "batch_sha256",
        "weekly_snapshot_sha256",
        "monthly_snapshot_sha256",
        "weekly_mapping_sha256",
        "monthly_mapping_sha256",
    ],
)
async def test_wmp7_tampered_receipt_hashes_fail_closed(field):
    gate = _api()
    receipt = await _receipt()
    object.__setattr__(receipt, field, "0" * 64)
    with pytest.raises(gate.TemplateTypeEnablementError) as caught:
        gate.build_weekly_monthly_active_binding_gate(receipt, _ActiveExportPort())
    assert caught.value.code is gate.TemplateTypeEnablementErrorCode.RECEIPT_INVALID


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("side", "field", "value"),
    [
        ("weekly", "seed_sha256", "0" * 64),
        ("monthly", "seed_sha256", "0" * 64),
        ("weekly", "profile_id", "weekly_activity_plan-profile-v1"),
        ("monthly", "profile_version", 1),
        ("weekly", "fixture_id", "stale-fixture-v0"),
        ("monthly", "checker_version", "template-candidate-qualification.v1"),
        ("weekly", "office_client_versions", ("libreoffice/24.1.9.2",)),
        ("monthly", "office_compatibility_targets", ("docx",)),
    ],
)
async def test_wmp7_stale_mismatched_or_cross_version_evidence_fails_closed(
    side, field, value
):
    gate = _api()
    receipt = await _receipt()
    evidence_name = f"{side}_evidence"
    object.__setattr__(
        receipt,
        evidence_name,
        replace(getattr(receipt, evidence_name), **{field: value}),
    )
    with pytest.raises(gate.TemplateTypeEnablementError) as caught:
        gate.build_weekly_monthly_active_binding_gate(receipt, _ActiveExportPort())
    assert caught.value.code is gate.TemplateTypeEnablementErrorCode.EVIDENCE_STALE


@pytest.mark.asyncio
async def test_wmp7_rejects_cross_document_evidence_even_if_public_hash_is_resealed():
    gate = _api()
    receipt = await _receipt()
    object.__setattr__(receipt, "weekly_evidence", receipt.monthly_evidence)
    with pytest.raises(gate.TemplateTypeEnablementError):
        gate.build_weekly_monthly_active_binding_gate(receipt, _ActiveExportPort())


def test_wmp7_module_is_internal_and_does_not_expand_business_package_surface():
    gate = _api()
    package = import_module("app.service.weekly_monthly_plans")
    assert hasattr(gate, "build_weekly_monthly_active_binding_gate")
    assert not hasattr(package, "build_weekly_monthly_enabled_registry")
    assert not hasattr(package, "build_weekly_monthly_active_binding_gate")
    assert not hasattr(package, "WeeklyMonthlyEnabledRegistry")
    assert not any(
        hasattr(gate, name)
        for name in (
            "upload",
            "activate",
            "rollback",
            "render",
            "parse",
            "export",
            "download",
            "resolve_version",
            "requested_version",
            "fallback",
            "discover",
        )
    )


@pytest.mark.asyncio
async def test_wmp7_registry_does_not_expose_receipt_evidence_or_provider_objects():
    gate = _api()
    active_gate = gate.build_weekly_monthly_active_binding_gate(
        await _receipt(), _ActiveExportPort()
    )
    rendered = repr(active_gate)
    for forbidden in (
        "qualification_id",
        "office_evidence_id",
        "rendered_sha256",
        "parse_report_sha256",
        "provider",
        "bucket",
        "url",
        "blob",
    ):
        assert forbidden not in rendered.lower()
    assert not hasattr(active_gate, "qualification_receipt")
    assert not hasattr(active_gate, "evidence")
    assert not hasattr(active_gate, "resolve")
    assert not hasattr(active_gate, "_document_registry")
    binding = await active_gate.resolve_active(17, WEEKLY)
    assert not hasattr(binding, "seed_relative_path")
    assert not hasattr(binding, "blob")


def test_wmp7_module_has_no_storage_database_ui_network_or_dynamic_dependencies():
    gate = _api()
    path = Path(gate.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = {
        node.module
        for node in ast.walk(tree)
        if type(node) is ast.ImportFrom and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if type(node) is ast.Import
        for alias in node.names
    }
    assert imports <= {
        "__future__",
        "enum",
        "app.service.template_center.contracts",
        "app.service.template_center.registry",
        "app.service.weekly_monthly_plans.qualification_orchestration",
    }
    source = path.read_text(encoding="utf-8").lower()
    for forbidden in (
        "sqlalchemy",
        "repository",
        "alembic",
        "http",
        "requests",
        "aiohttp",
        "pathlib",
        "open(",
        "import_module",
    ):
        assert forbidden not in source


def test_wmp7_does_not_publish_wmp8_wmp9_or_agent_capabilities():
    gate = _api()
    assert gate.ENABLEMENT_CONTRACT_VERSION == "weekly-monthly-template-enablement.v1"
    assert not any(
        name in vars(gate)
        for name in (
            "WeeklyMonthlyExporter",
            "FormalExporter",
            "ExportResult",
            "ApprovalWorkflow",
            "AgentTool",
            "TemplateCrud",
        )
    )
