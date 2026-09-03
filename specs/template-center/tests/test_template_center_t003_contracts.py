"""T003 GREEN gate for closed, side-effect-free template contracts."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from inspect import iscoroutinefunction
from uuid import uuid4

import pytest

import app.service.template_center as api


KNOWN = (
    "daily_plan",
    "game_observation",
    "one_on_one_listening",
    "homemade_teaching",
    "course_review_activity",
    "weekly_activity_plan",
    "monthly_theme_activity_plan",
)
ENABLED = KNOWN[:5]


def test_t003_registry_publishes_exact_known_enabled_and_reserved_sets():
    registry = api.build_initial_document_registry()
    assert registry.known_keys() == KNOWN
    assert tuple(item.key.value for item in registry.descriptors()) == ENABLED
    assert tuple(item.value for item in api.DocumentType) == KNOWN
    assert not hasattr(registry, "register")
    assert not hasattr(registry, "replace")


@pytest.mark.parametrize("key", KNOWN[5:])
def test_t003_reserved_document_types_are_known_but_fail_closed(key):
    registry = api.build_initial_document_registry()
    assert registry.is_enabled(key) is False
    with pytest.raises(api.TemplateCenterError) as caught:
        registry.resolve(key)
    assert caught.value.code.value == "document_type_reserved_until_gate"


def test_t003_unknown_types_and_aliases_are_rejected_with_stable_codes():
    registry = api.build_initial_document_registry()
    for key in ("daily-plan", "DAILY_PLAN", "unknown", True, None):
        with pytest.raises(api.TemplateCenterError) as caught:
            registry.resolve(key)
        assert caught.value.code is api.TemplateErrorCode.UNKNOWN_DOCUMENT_TYPE


def test_t003_descriptors_are_frozen_legacy_structural_manifests():
    descriptor = api.build_initial_document_registry().resolve("daily_plan")
    assert is_dataclass(descriptor)
    assert (
        descriptor.contract.structural_profile_id == "legacy_structural_v1.daily_plan"
    )
    assert descriptor.contract.tokens == ()
    assert descriptor.seed_relative_path == "templates/teacherplan.docx"
    assert len(descriptor.seed_sha256) == 64
    assert "weekly" not in tuple(
        item.key.value for item in api.INITIAL_DOCUMENT_DESCRIPTORS
    )
    with pytest.raises(FrozenInstanceError):
        descriptor.display_name = "changed"


def test_t003_version_reference_is_closed_frozen_and_content_addressed():
    sha = "a" * 64
    evidence = api.TemplateValidationEvidence(
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
        validator_version="validator.v1",
        validated_at_utc=datetime(2026, 9, 3, tzinfo=timezone.utc),
        validation_status=api.ValidationStatus.VALIDATED,
        token_occurrences=(),
    )
    version = api.TemplateVersionRef(
        template_version_id=uuid4(),
        tenant_id=7,
        document_type=api.DocumentType.DAILY_PLAN,
        version=1,
        content_sha256=sha,
        size_bytes=123,
        mime_type=api.DOCX_MIME_TYPE,
        extension=".docx",
        blob_ref=f"sha256/{sha}",
        contract_id="kg.template.daily_plan.legacy_structural",
        contract_version=1,
        validation_receipt_id=evidence.validation_receipt_id,
        validation_status=api.ValidationStatus.VALIDATED,
        validated_at_utc=datetime(2026, 9, 3, tzinfo=timezone.utc),
        validator_version="validator.v1",
        source=api.TemplateSource.UPLOAD,
        created_by_user_id=11,
        created_at_utc=datetime(2026, 9, 3, tzinfo=timezone.utc),
        validation_evidence=evidence,
    )
    assert {item.name for item in fields(version)} == {
        "template_version_id",
        "tenant_id",
        "document_type",
        "version",
        "content_sha256",
        "size_bytes",
        "mime_type",
        "extension",
        "blob_ref",
        "contract_id",
        "contract_version",
        "validation_receipt_id",
        "validation_status",
        "validated_at_utc",
        "validator_version",
        "source",
        "created_by_user_id",
        "created_at_utc",
        "validation_evidence",
    }
    assert not hasattr(version, "content")
    assert not hasattr(version, "absolute_path")
    assert not hasattr(version, "active")
    with pytest.raises(FrozenInstanceError):
        version.version = 2


@pytest.mark.parametrize("bad", (True, 0, -1, "7"))
def test_t003_version_reference_rejects_invalid_tenant_id(bad):
    sha = "b" * 64
    evidence = api.TemplateValidationEvidence(
        validation_receipt_id=uuid4(),
        content_sha256=sha,
        size_bytes=1,
        mime_type=api.DOCX_MIME_TYPE,
        extension=".docx",
        contract_id="contract.v1",
        contract_version=1,
        structural_profile_id="profile.v1",
        structural_profile_version=1,
        structure_summary_sha256="c" * 64,
        validator_version="validator.v1",
        validated_at_utc=datetime(2026, 9, 3, tzinfo=timezone.utc),
        validation_status=api.ValidationStatus.VALIDATED,
        token_occurrences=(),
    )
    with pytest.raises((TypeError, ValueError)):
        api.TemplateVersionRef(
            template_version_id=uuid4(),
            tenant_id=bad,
            document_type=api.DocumentType.DAILY_PLAN,
            version=1,
            content_sha256=sha,
            size_bytes=1,
            mime_type=api.DOCX_MIME_TYPE,
            extension=".docx",
            blob_ref=f"sha256/{sha}",
            contract_id="contract.v1",
            contract_version=1,
            validation_receipt_id=evidence.validation_receipt_id,
            validation_status=api.ValidationStatus.VALIDATED,
            validated_at_utc=datetime(2026, 9, 3, tzinfo=timezone.utc),
            validator_version="validator.v1",
            source=api.TemplateSource.UPLOAD,
            created_by_user_id=11,
            created_at_utc=datetime(2026, 9, 3, tzinfo=timezone.utc),
            validation_evidence=evidence,
        )


def test_t003_ports_expose_only_closed_entrypoints():
    expected = {
        api.TemplateBlobStorePort: {"put_if_absent", "read", "exists"},
        api.TemplateVersionStorePort: {"get_version", "snapshot"},
        api.TemplateUnitOfWork: {
            "allocate_version",
            "stage_version",
            "stage_transition",
            "stage_audit",
            "commit",
        },
        api.TemplateUnitOfWorkPort: {"begin"},
        api.TemplatePermissionPolicyPort: {"project", "authorize"},
        api.TemplateExportPort: {"resolve_active", "render", "parse"},
        api.TemplateClockPort: {"utcnow"},
        api.TemplateBackupPort: {
            "create_template_backup",
            "restore_template_backup",
        },
    }
    for port, methods in expected.items():
        public = {name for name in vars(port) if not name.startswith("_")}
        assert public == methods
        for name in methods:
            if port is not api.TemplateClockPort:
                assert iscoroutinefunction(getattr(port, name))


def test_t003_contract_surface_has_no_dynamic_discovery_or_future_jobs():
    assert not hasattr(api, "TemplateCandidateQualificationJob")
    assert not hasattr(api, "resolve_for_export")
    assert not hasattr(api, "get_template_path")


def test_t003_projection_uses_pathless_summary_and_enforces_document_type():
    summary = api.TemplateVersionSummary(
        template_version_id=uuid4(),
        tenant_id=7,
        document_type=api.DocumentType.DAILY_PLAN,
        version=1,
        content_sha256="c" * 64,
        contract_id="contract.v1",
        contract_version=1,
        validated_at_utc=datetime(2026, 9, 3, tzinfo=timezone.utc),
        created_at_utc=datetime(2026, 9, 3, tzinfo=timezone.utc),
    )
    assert not hasattr(summary, "blob_ref")
    assert "sha256/" not in repr(summary)
    with pytest.raises(ValueError):
        api.TemplatePermissionProjection(
            tenant_id=7,
            document_type=api.DocumentType.MONTHLY_THEME_ACTIVITY_PLAN,
            allowed_actions=(api.TemplateCapability.READ,),
            versions=(summary,),
            active_version=None,
        )


def test_t003_audit_event_has_complete_version_contract_and_revision_evidence():
    names = {item.name for item in fields(api.TemplateAuditEvent)}
    assert {
        "template_version_id",
        "content_sha256",
        "contract_id",
        "contract_version",
        "registry_revision",
    } <= names


def test_t003_audit_version_contract_and_revision_evidence_is_atomic():
    with pytest.raises(ValueError):
        api.TemplateAuditEvent(
            event_id=uuid4(),
            action=api.TemplateCapability.ACTIVATE,
            outcome=api.AuditOutcome.ACCEPTED,
            tenant_id=7,
            user_id=11,
            session_hash="e" * 64,
            document_type=api.DocumentType.DAILY_PLAN,
            template_version_id=uuid4(),
            content_sha256=None,
            contract_id="contract.v1",
            contract_version=None,
            registry_revision=None,
            occurred_at_utc=datetime(2026, 9, 3, tzinfo=timezone.utc),
        )


def test_t003_contracts_reject_nested_mutability_and_string_subclasses():
    class TextSubclass(str):
        pass

    with pytest.raises(ValueError):
        api.SyntheticPreviewCase(
            fixture_id="fixture.v1",
            provenance="synthetic",
            payload=(("mutable", {"value": []}),),
        )
    with pytest.raises(ValueError):
        api.TemplateTokenDescriptor(
            token_id="kg.daily_plan.title",
            value_kind=TextSubclass("text"),
            required=True,
            occurrence="single",
            allowed_parts=("word/document.xml",),
        )


def test_t003_contracts_require_canonical_utc_timezone():
    noncanonical_zero_offset = timezone(timedelta(0), "not-UTC")
    with pytest.raises(ValueError):
        api.BackupAttestation(
            schema_version=1,
            artifact_sha256="d" * 64,
            artifact_size=1,
            protected_image="repo/image@sha256:abc",
            created_at_utc=datetime(2026, 9, 3, tzinfo=noncanonical_zero_offset),
            status="verified",
        )


def test_t003_manifest_rejects_token_parts_outside_its_closed_part_set():
    token = api.TemplateTokenDescriptor(
        token_id="kg.daily_plan.title",
        value_kind="text",
        required=True,
        occurrence="single",
        allowed_parts=("word/header1.xml",),
    )
    with pytest.raises(ValueError):
        api.TemplateContractManifest(
            contract_id="contract.v1",
            contract_version=1,
            placeholder_contract_version=1,
            structural_profile_id="profile.v1",
            structural_profile_version=1,
            renderer_id="renderer.v1",
            parser_id="parser.v1",
            allowed_parts=("word/document.xml",),
            required_anchors=("anchor",),
            tokens=(token,),
        )
