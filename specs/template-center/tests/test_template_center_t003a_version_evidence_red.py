"""T003A atomic allocation and immutable validation-evidence contract RED."""

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from importlib import import_module
from inspect import signature
from uuid import uuid4

import pytest

from _support import MemoryAuditSink, MemoryTransactionPort, MemoryVersionStore


NOW = datetime(2026, 9, 3, tzinfo=timezone.utc)


def _api():
    return import_module("app.service.template_center")


def _evidence(api, *, sha: str = "a" * 64):
    return api.TemplateValidationEvidence(
        validation_receipt_id=uuid4(),
        content_sha256=sha,
        size_bytes=123,
        mime_type=api.DOCX_MIME_TYPE,
        extension=".docx",
        contract_id="kg.template.daily_plan.legacy_structural",
        contract_version=1,
        structural_profile_id="legacy_structural_v1.daily_plan",
        structural_profile_version=1,
        structure_summary_sha256="b" * 64,
        validator_version="template-upload-validator.v1",
        validated_at_utc=NOW,
        validation_status=api.ValidationStatus.VALIDATED,
        token_occurrences=(),
    )


def _version(api, evidence, allocation, *, content_sha256: str | None = None):
    return api.TemplateVersionRef(
        template_version_id=allocation.template_version_id,
        tenant_id=allocation.tenant_id,
        document_type=allocation.document_type,
        version=allocation.version,
        content_sha256=content_sha256 or evidence.content_sha256,
        size_bytes=evidence.size_bytes,
        mime_type=evidence.mime_type,
        extension=evidence.extension,
        blob_ref=f"sha256/{evidence.content_sha256}",
        contract_id=evidence.contract_id,
        contract_version=evidence.contract_version,
        validation_receipt_id=evidence.validation_receipt_id,
        validation_status=evidence.validation_status,
        validated_at_utc=evidence.validated_at_utc,
        validator_version=evidence.validator_version,
        source=api.TemplateSource.UPLOAD,
        created_by_user_id=11,
        created_at_utc=NOW,
        validation_evidence=evidence,
    )


def test_validation_evidence_is_closed_frozen_and_content_bound():
    api = _api()
    evidence = _evidence(api)

    assert {item.name for item in fields(evidence)} == {
        "validation_receipt_id",
        "content_sha256",
        "size_bytes",
        "mime_type",
        "extension",
        "contract_id",
        "contract_version",
        "structural_profile_id",
        "structural_profile_version",
        "structure_summary_sha256",
        "validator_version",
        "validated_at_utc",
        "validation_status",
        "token_occurrences",
    }
    assert not hasattr(evidence, "content")
    assert not hasattr(evidence, "path")
    with pytest.raises(FrozenInstanceError):
        evidence.validator_version = "changed"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("content_sha256", "A" * 64),
        ("size_bytes", True),
        ("structural_profile_id", ""),
        ("structural_profile_version", 0),
        ("structure_summary_sha256", "not-a-sha"),
        ("validator_version", ""),
        ("validated_at_utc", datetime(2026, 9, 3)),
    ],
)
def test_validation_evidence_rejects_invalid_fields(field, value):
    api = _api()
    values = {
        item.name: getattr(_evidence(api), item.name) for item in fields(_evidence(api))
    }
    values[field] = value
    with pytest.raises((TypeError, ValueError)):
        api.TemplateValidationEvidence(**values)


def test_version_is_fixed_to_the_exact_validation_evidence():
    api = _api()
    evidence = _evidence(api)
    allocation = api.VersionAllocation(
        template_version_id=uuid4(),
        tenant_id=7,
        document_type=api.DocumentType.DAILY_PLAN,
        version=1,
    )
    version = _version(api, evidence, allocation)

    assert version.validation_evidence is evidence
    assert version.validation_evidence.structural_profile_id == (
        "legacy_structural_v1.daily_plan"
    )
    assert version.validation_evidence.structure_summary_sha256 == "b" * 64

    mismatched = _evidence(api, sha="c" * 64)
    with pytest.raises((TypeError, ValueError)):
        _version(api, mismatched, allocation, content_sha256="a" * 64)


def test_validation_evidence_is_derived_from_the_exact_t004_receipt():
    api = _api()
    receipt = api.TemplateValidationReceipt(
        content_sha256="d" * 64,
        size_bytes=321,
        mime_type=api.DOCX_MIME_TYPE,
        extension=".docx",
        contract_id="kg.template.daily_plan.legacy_structural",
        contract_version=2,
        structural_profile_id="legacy_structural_v2.daily_plan",
        structural_profile_version=2,
        structure_summary_sha256="e" * 64,
        token_occurrences=(),
        validator_version="template-upload-validator.v2",
    )
    receipt_id = uuid4()

    evidence = api.TemplateValidationEvidence.from_receipt(
        receipt_id,
        receipt,
        validated_at_utc=NOW,
    )

    assert evidence.validation_receipt_id == receipt_id
    assert evidence.content_sha256 == receipt.content_sha256
    assert evidence.size_bytes == receipt.size_bytes
    assert evidence.contract_id == receipt.contract_id
    assert evidence.contract_version == receipt.contract_version
    assert evidence.structural_profile_id == receipt.structural_profile_id
    assert evidence.structural_profile_version == receipt.structural_profile_version
    assert evidence.structure_summary_sha256 == receipt.structure_summary_sha256
    assert evidence.token_occurrences == receipt.token_occurrences
    assert evidence.validator_version == receipt.validator_version


def test_version_allocation_is_closed_frozen_and_strictly_scoped():
    api = _api()
    allocation = api.VersionAllocation(
        template_version_id=uuid4(),
        tenant_id=7,
        document_type=api.DocumentType.DAILY_PLAN,
        version=1,
    )
    assert {item.name for item in fields(allocation)} == {
        "template_version_id",
        "tenant_id",
        "document_type",
        "version",
    }
    with pytest.raises(FrozenInstanceError):
        allocation.version = 2
    with pytest.raises((TypeError, ValueError)):
        api.VersionAllocation(
            template_version_id=uuid4(),
            tenant_id=True,
            document_type=api.DocumentType.DAILY_PLAN,
            version=1,
        )


def test_unit_of_work_exposes_only_a_narrow_bound_allocation_method():
    api = _api()
    parameters = tuple(signature(api.TemplateUnitOfWork.allocate_version).parameters)
    assert parameters == ("self",)


@pytest.mark.asyncio
async def test_interleaved_reservations_are_unique_monotonic_and_scope_local():
    api = _api()
    store = MemoryVersionStore()
    transactions = MemoryTransactionPort(store, MemoryAuditSink())
    daily_a = await transactions.begin(7, api.DocumentType.DAILY_PLAN)
    daily_b = await transactions.begin(7, api.DocumentType.DAILY_PLAN)
    other_tenant = await transactions.begin(8, api.DocumentType.DAILY_PLAN)
    other_type = await transactions.begin(7, api.DocumentType.GAME_OBSERVATION)

    first = await daily_a.allocate_version()
    second = await daily_b.allocate_version()
    tenant_first = await other_tenant.allocate_version()
    type_first = await other_type.allocate_version()

    assert (first.version, second.version) == (1, 2)
    assert first.template_version_id != second.template_version_id
    assert tenant_first.version == 1
    assert type_first.version == 1
    assert first.tenant_id == second.tenant_id == 7
    assert first.document_type is api.DocumentType.DAILY_PLAN


@pytest.mark.asyncio
async def test_abandoned_reservation_is_never_reused():
    api = _api()
    store = MemoryVersionStore()
    transactions = MemoryTransactionPort(store, MemoryAuditSink())
    abandoned = await transactions.begin(7, api.DocumentType.DAILY_PLAN)
    later = await transactions.begin(7, api.DocumentType.DAILY_PLAN)

    assert (await abandoned.allocate_version()).version == 1
    assert (await later.allocate_version()).version == 2
    assert store.versions == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("document_type", "error_code"),
    [
        ("weekly_activity_plan", "document_type_reserved_until_gate"),
        ("monthly_theme_activity_plan", "document_type_reserved_until_gate"),
        ("unknown_type", "unknown_document_type"),
    ],
)
async def test_allocation_rejects_reserved_and_unknown_document_types(
    document_type, error_code
):
    api = _api()
    transactions = MemoryTransactionPort(MemoryVersionStore(), MemoryAuditSink())

    with pytest.raises(api.TemplateCenterError) as caught:
        await transactions.begin(7, document_type)

    assert caught.value.code.value == error_code
    assert transactions.version_sequences == {}


@pytest.mark.asyncio
async def test_allocation_can_only_be_consumed_once_by_its_own_unit_of_work():
    api = _api()
    store = MemoryVersionStore()
    transactions = MemoryTransactionPort(store, MemoryAuditSink())
    owner = await transactions.begin(7, api.DocumentType.DAILY_PLAN)
    stranger = await transactions.begin(7, api.DocumentType.DAILY_PLAN)
    allocation = await owner.allocate_version()
    version = _version(api, _evidence(api), allocation)

    with pytest.raises((api.TemplateCenterError, ValueError)):
        await stranger.stage_version(allocation, version)
    await owner.stage_version(allocation, version)
    with pytest.raises((api.TemplateCenterError, ValueError)):
        await owner.stage_version(allocation, version)

    assert stranger.staged_versions == []
    assert owner.staged_versions == [version]


@pytest.mark.asyncio
async def test_forged_or_mismatched_allocation_cannot_stage_a_version():
    api = _api()
    store = MemoryVersionStore()
    transactions = MemoryTransactionPort(store, MemoryAuditSink())
    unit = await transactions.begin(7, api.DocumentType.DAILY_PLAN)
    allocation = await unit.allocate_version()
    forged = api.VersionAllocation(
        template_version_id=allocation.template_version_id,
        tenant_id=allocation.tenant_id,
        document_type=allocation.document_type,
        version=allocation.version,
    )
    version = _version(api, _evidence(api), allocation)

    with pytest.raises((api.TemplateCenterError, ValueError)):
        await unit.stage_version(forged, version)
    other_allocation = api.VersionAllocation(
        template_version_id=uuid4(),
        tenant_id=7,
        document_type=api.DocumentType.DAILY_PLAN,
        version=99,
    )
    wrong_version = _version(api, _evidence(api), other_allocation)
    with pytest.raises((api.TemplateCenterError, ValueError)):
        await unit.stage_version(allocation, wrong_version)

    assert unit.staged_versions == []


@pytest.mark.asyncio
async def test_failed_commit_does_not_publish_or_reuse_the_allocation():
    api = _api()
    store = MemoryVersionStore()
    audit = MemoryAuditSink()
    transactions = MemoryTransactionPort(store, audit)
    failed = await transactions.begin(7, api.DocumentType.DAILY_PLAN)
    allocation = await failed.allocate_version()
    version = _version(api, _evidence(api), allocation)
    await failed.stage_version(allocation, version)
    audit.fail = True

    with pytest.raises(RuntimeError):
        await failed.commit()

    audit.fail = False
    later = await transactions.begin(7, api.DocumentType.DAILY_PLAN)
    assert (await later.allocate_version()).version == 2
    assert store.versions == []
