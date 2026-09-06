"""Stable RED for the first read-only WMP-7 review findings."""

from __future__ import annotations

import ast
from dataclasses import replace
from importlib import import_module
from pathlib import Path

import pytest
from test_wmp7_template_enablement_gate_red import _ActiveExportPort, _receipt


def _gate():
    return import_module("app.service.weekly_monthly_plans.template_enablement")


def _orchestration():
    return import_module("app.service.weekly_monthly_plans.qualification_orchestration")


@pytest.mark.asyncio
async def test_review_business_surface_is_active_binding_only_not_registry_descriptor():
    gate = _gate()
    assert hasattr(gate, "build_weekly_monthly_active_binding_gate")
    assert not hasattr(gate, "build_weekly_monthly_enabled_registry")


@pytest.mark.asyncio
async def test_review_production_registry_enables_only_current_weekly_monthly_pair():
    gate = _gate()
    tc = import_module("app.service.template_center")
    receipt = await _receipt()

    enabled = gate._build_wmp7_document_registry(receipt)
    assert enabled.known_keys() == tc.GLOBAL_KNOWN_DOCUMENT_TYPES
    assert tuple(item.key.value for item in enabled.descriptors()) == (
        tc.GLOBAL_KNOWN_DOCUMENT_TYPES
    )
    assert all(enabled.is_enabled(item) for item in tc.GLOBAL_KNOWN_DOCUMENT_TYPES)
    assert enabled.resolve("weekly_activity_plan").seed_sha256 == (
        "f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b"
    )
    assert enabled.resolve("monthly_theme_activity_plan").seed_sha256 == (
        "f2e5dbe2a468dd15c55cdd6b70c5e15fe63048a3708b151732e208703b0d11f4"
    )
    initial = tc.build_initial_document_registry()
    assert not initial.is_enabled("weekly_activity_plan")
    assert not initial.is_enabled("monthly_theme_activity_plan")


@pytest.mark.asyncio
async def test_review_wmp7_descriptors_do_not_declare_future_template_capabilities():
    gate = _gate()
    tc = import_module("app.service.template_center")
    enabled = gate._build_wmp7_document_registry(await _receipt())

    for document_type in ("weekly_activity_plan", "monthly_theme_activity_plan"):
        assert enabled.resolve(document_type).capabilities == (
            tc.TemplateCapability.READ,
        )


@pytest.mark.asyncio
async def test_review_forged_resealed_receipt_with_arbitrary_snapshots_is_rejected():
    gate = _gate()
    q = _orchestration()
    original = await _receipt()
    forged = object.__new__(q.WeeklyMonthlyQualificationReceipt)
    weekly_snapshot = "a" * 64
    monthly_snapshot = "b" * 64
    weekly_mapping = q._mapping_hash("weekly_activity_plan")
    monthly_mapping = q._mapping_hash("monthly_theme_activity_plan")
    batch = q._hash(
        {
            "contract_version": q.QUALIFICATION_ORCHESTRATION_CONTRACT_VERSION,
            "weekly": {
                "snapshot_sha256": weekly_snapshot,
                "mapping_sha256": weekly_mapping,
                "evidence": original.weekly_evidence,
            },
            "monthly": {
                "snapshot_sha256": monthly_snapshot,
                "mapping_sha256": monthly_mapping,
                "evidence": original.monthly_evidence,
            },
        }
    )
    for name, value in (
        ("batch_sha256", batch),
        ("weekly_snapshot_sha256", weekly_snapshot),
        ("monthly_snapshot_sha256", monthly_snapshot),
        ("weekly_mapping_sha256", weekly_mapping),
        ("monthly_mapping_sha256", monthly_mapping),
        ("weekly_evidence", original.weekly_evidence),
        ("monthly_evidence", original.monthly_evidence),
    ):
        object.__setattr__(forged, name, value)

    with pytest.raises(gate.TemplateTypeEnablementError) as caught:
        gate.build_weekly_monthly_active_binding_gate(forged, _ActiveExportPort())
    assert caught.value.code is gate.TemplateTypeEnablementErrorCode.RECEIPT_INVALID


def test_review_gate_uses_no_mutable_or_identity_based_issuer_authority():
    gate = _gate()
    q = _orchestration()
    for module in (gate, q):
        source = Path(module.__file__).read_text(encoding="utf-8").lower()
        assert "weakset" not in source
        assert "weakref" not in source
        assert "_issued_receipts" not in source
        assert "id(receipt)" not in source


@pytest.mark.asyncio
async def test_review_external_receipt_shapes_are_rejected_without_deserialization():
    gate = _gate()
    original = await _receipt()
    payload = {name: getattr(original, name) for name in original.__dataclass_fields__}
    for external in (payload, tuple(payload.values())):
        with pytest.raises(gate.TemplateTypeEnablementError) as caught:
            gate.build_weekly_monthly_active_binding_gate(external, _ActiveExportPort())
        assert caught.value.code is gate.TemplateTypeEnablementErrorCode.RECEIPT_INVALID


@pytest.mark.asyncio
async def test_review_current_profile_contract_drift_expires_evidence(monkeypatch):
    gate = _gate()
    receipt = await _receipt()
    weekly = next(
        item
        for item in gate.CANDIDATE_QUALIFICATION_PROFILES
        if item.profile_id == "weekly_activity_plan-profile-v2"
    )
    changed_contract = replace(
        weekly.contract,
        renderer_id="kg.renderer.weekly_activity_plan.changed.v99",
    )
    changed = replace(weekly, contract=changed_contract)
    monkeypatch.setattr(
        gate,
        "CANDIDATE_QUALIFICATION_PROFILES",
        tuple(
            changed if item is weekly else item
            for item in gate.CANDIDATE_QUALIFICATION_PROFILES
        ),
    )

    with pytest.raises(gate.TemplateTypeEnablementError) as caught:
        gate.build_weekly_monthly_active_binding_gate(receipt, _ActiveExportPort())
    assert caught.value.code is gate.TemplateTypeEnablementErrorCode.EVIDENCE_STALE


@pytest.mark.asyncio
async def test_review_post_construction_contract_drift_expires_gate(monkeypatch):
    gate = _gate()
    active_gate = gate.build_weekly_monthly_active_binding_gate(
        await _receipt(), _ActiveExportPort()
    )
    weekly = next(
        item
        for item in gate.CANDIDATE_QUALIFICATION_PROFILES
        if item.profile_id == "weekly_activity_plan-profile-v2"
    )
    changed = replace(
        weekly,
        contract=replace(
            weekly.contract,
            renderer_id="kg.renderer.weekly_activity_plan.changed.v99",
        ),
    )
    monkeypatch.setattr(
        gate,
        "CANDIDATE_QUALIFICATION_PROFILES",
        tuple(
            changed if item is weekly else item
            for item in gate.CANDIDATE_QUALIFICATION_PROFILES
        ),
    )

    with pytest.raises(gate.TemplateTypeEnablementError) as caught:
        await active_gate.resolve_active(17, "weekly_activity_plan")
    assert caught.value.code is gate.TemplateTypeEnablementErrorCode.EVIDENCE_STALE


def test_review_malformed_same_type_receipt_is_sanitized():
    gate = _gate()
    q = _orchestration()
    malformed = object.__new__(q.WeeklyMonthlyQualificationReceipt)
    with pytest.raises(gate.TemplateTypeEnablementError) as caught:
        gate.build_weekly_monthly_active_binding_gate(malformed, _ActiveExportPort())
    assert caught.value.code is gate.TemplateTypeEnablementErrorCode.RECEIPT_INVALID
    assert caught.value.__cause__ is None


def test_review_gate_does_not_import_private_wmp6_hashing_helpers():
    gate = _gate()
    path = Path(gate.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if type(node) is ast.ImportFrom
        and node.module
        == "app.service.weekly_monthly_plans.qualification_orchestration"
        for alias in node.names
    }
    assert "_hash" not in imported
    assert "_mapping_hash" not in imported
    assert "_verify_qualification_receipt" in imported
