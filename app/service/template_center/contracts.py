"""Closed, side-effect-free contracts for template-center slice T003."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Protocol
from uuid import UUID


DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
MAX_TEMPLATE_BYTES = 16 * 1024 * 1024
_SHA256 = re.compile(r"[0-9a-f]{64}")


class DocumentType(str, Enum):
    DAILY_PLAN = "daily_plan"
    GAME_OBSERVATION = "game_observation"
    ONE_ON_ONE_LISTENING = "one_on_one_listening"
    HOMEMADE_TEACHING = "homemade_teaching"
    COURSE_REVIEW_ACTIVITY = "course_review_activity"
    WEEKLY_ACTIVITY_PLAN = "weekly_activity_plan"
    MONTHLY_THEME_ACTIVITY_PLAN = "monthly_theme_activity_plan"


class TemplateCapability(str, Enum):
    LIST = "list"
    READ = "read"
    UPLOAD = "upload"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    ROLLBACK = "rollback"
    PREVIEW = "preview"
    BACKUP = "backup"
    RESTORE = "restore"
    RENDER = "render"
    PARSE = "parse"


class TemplateErrorCode(str, Enum):
    UNKNOWN_DOCUMENT_TYPE = "unknown_document_type"
    DOCUMENT_TYPE_RESERVED_UNTIL_GATE = "document_type_reserved_until_gate"
    CONTRACT_INVALID = "contract_invalid"
    INPUT_INVALID = "input_invalid"
    PERMISSION_DENIED = "permission_denied"
    TENANT_MISMATCH = "tenant_mismatch"
    VERSION_NOT_FOUND = "version_not_found"
    TEMPLATE_NOT_ACTIVE = "template_not_active"
    VALIDATION_FAILED = "validation_failed"
    REGISTRY_STALE = "registry_stale"
    STORAGE_FAILED = "storage_failed"
    EXPORT_FAILED = "export_failed"
    BACKUP_FAILED = "backup_failed"


class TemplateCenterError(ValueError):
    """A sanitized rejection carrying only a stable public error code."""

    def __init__(self, code: TemplateErrorCode) -> None:
        if type(code) is not TemplateErrorCode:
            raise TypeError("template_error_code_invalid")
        self.code = code
        super().__init__(code.value)


class TemplateSource(str, Enum):
    REPOSITORY_SEED = "repository_seed"
    UPLOAD = "upload"
    RESTORE = "restore"


class ValidationStatus(str, Enum):
    VALIDATED = "validated"


class AuditOutcome(str, Enum):
    ACCEPTED = "accepted"
    DENIED = "denied"
    REJECTED = "rejected"
    STALE = "stale"
    FAILED = "failed"


def _positive_int(value: object, code: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(code)


def _nonempty_text(value: object, code: str) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError(code)


def _sha256(value: object, code: str) -> None:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(code)


def _utc(value: object, code: str) -> None:
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError(code)


def _deeply_immutable(value: object) -> bool:
    if value is None or type(value) in {bool, int, float, str, bytes, UUID, datetime}:
        return type(value) is not datetime or value.tzinfo is timezone.utc
    return type(value) is tuple and all(_deeply_immutable(item) for item in value)


def _document_type(value: object, code: str) -> None:
    if type(value) is not DocumentType:
        raise ValueError(code)


@dataclass(frozen=True, slots=True)
class TemplateTokenDescriptor:
    token_id: str
    value_kind: str
    required: bool
    occurrence: str
    allowed_parts: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.token_id) is not str
            or re.fullmatch(r"kg\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_.]*", self.token_id)
            is None
            or type(self.value_kind) is not str
            or self.value_kind not in {"text", "rich_text", "image"}
            or type(self.required) is not bool
            or type(self.occurrence) is not str
            or self.occurrence not in {"single", "repeatable"}
            or type(self.allowed_parts) is not tuple
            or not self.allowed_parts
            or not all(type(part) is str and part for part in self.allowed_parts)
        ):
            raise ValueError("template_token_descriptor_invalid")


@dataclass(frozen=True, slots=True)
class TemplateContractManifest:
    contract_id: str
    contract_version: int
    placeholder_contract_version: int
    structural_profile_id: str
    structural_profile_version: int
    renderer_id: str
    parser_id: str
    allowed_parts: tuple[str, ...]
    required_anchors: tuple[str, ...]
    tokens: tuple[TemplateTokenDescriptor, ...] = ()

    def __post_init__(self) -> None:
        for value in (
            self.contract_id,
            self.structural_profile_id,
            self.renderer_id,
            self.parser_id,
        ):
            _nonempty_text(value, "template_contract_manifest_invalid")
        for value in (
            self.contract_version,
            self.placeholder_contract_version,
            self.structural_profile_version,
        ):
            _positive_int(value, "template_contract_manifest_invalid")
        if (
            type(self.allowed_parts) is not tuple
            or not self.allowed_parts
            or not all(type(part) is str and part for part in self.allowed_parts)
            or type(self.required_anchors) is not tuple
            or not self.required_anchors
            or not all(
                type(anchor) is str and anchor for anchor in self.required_anchors
            )
            or type(self.tokens) is not tuple
            or not all(type(token) is TemplateTokenDescriptor for token in self.tokens)
            or len({token.token_id for token in self.tokens}) != len(self.tokens)
            or any(
                not set(token.allowed_parts).issubset(self.allowed_parts)
                for token in self.tokens
            )
        ):
            raise ValueError("template_contract_manifest_invalid")


@dataclass(frozen=True, slots=True)
class TemplateTokenOccurrence:
    """Sanitized token metadata emitted by the pure upload validator."""

    token_id: str
    value_kind: str
    part_name: str
    location: str

    def __post_init__(self) -> None:
        if (
            type(self.token_id) is not str
            or re.fullmatch(r"kg\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_.]*", self.token_id)
            is None
            or type(self.value_kind) is not str
            or self.value_kind not in {"text", "rich_text", "image"}
            or type(self.part_name) is not str
            or not self.part_name
            or type(self.location) is not str
            or re.fullmatch(r"paragraph:[0-9]+", self.location) is None
        ):
            raise ValueError("template_token_occurrence_invalid")


@dataclass(frozen=True, slots=True)
class TemplateValidationReceipt:
    """Content-bound, pathless result of side-effect-free T004 validation."""

    content_sha256: str
    size_bytes: int
    mime_type: str
    extension: str
    contract_id: str
    contract_version: int
    structural_profile_id: str
    structural_profile_version: int
    structure_summary_sha256: str
    token_occurrences: tuple[TemplateTokenOccurrence, ...]
    validator_version: str

    def __post_init__(self) -> None:
        _sha256(self.content_sha256, "template_validation_receipt_invalid")
        _positive_int(self.size_bytes, "template_validation_receipt_invalid")
        if self.size_bytes > MAX_TEMPLATE_BYTES:
            raise ValueError("template_validation_receipt_invalid")
        if self.mime_type != DOCX_MIME_TYPE or self.extension != ".docx":
            raise ValueError("template_validation_receipt_invalid")
        _nonempty_text(self.contract_id, "template_validation_receipt_invalid")
        _positive_int(self.contract_version, "template_validation_receipt_invalid")
        _nonempty_text(
            self.structural_profile_id, "template_validation_receipt_invalid"
        )
        _positive_int(
            self.structural_profile_version, "template_validation_receipt_invalid"
        )
        _sha256(self.structure_summary_sha256, "template_validation_receipt_invalid")
        if type(self.token_occurrences) is not tuple or not all(
            type(item) is TemplateTokenOccurrence for item in self.token_occurrences
        ):
            raise ValueError("template_validation_receipt_invalid")
        _nonempty_text(self.validator_version, "template_validation_receipt_invalid")


@dataclass(frozen=True, slots=True)
class TemplateValidationEvidence:
    """Persistable, content-bound evidence derived from one T004 receipt."""

    validation_receipt_id: UUID
    content_sha256: str
    size_bytes: int
    mime_type: str
    extension: str
    contract_id: str
    contract_version: int
    structural_profile_id: str
    structural_profile_version: int
    structure_summary_sha256: str
    validator_version: str
    validated_at_utc: datetime
    validation_status: ValidationStatus
    token_occurrences: tuple[TemplateTokenOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.validation_receipt_id) is not UUID:
            raise ValueError("template_validation_evidence_invalid")
        _sha256(self.content_sha256, "template_validation_evidence_invalid")
        _positive_int(self.size_bytes, "template_validation_evidence_invalid")
        if (
            self.size_bytes > MAX_TEMPLATE_BYTES
            or self.mime_type != DOCX_MIME_TYPE
            or self.extension != ".docx"
        ):
            raise ValueError("template_validation_evidence_invalid")
        _nonempty_text(self.contract_id, "template_validation_evidence_invalid")
        _positive_int(self.contract_version, "template_validation_evidence_invalid")
        _nonempty_text(
            self.structural_profile_id, "template_validation_evidence_invalid"
        )
        _positive_int(
            self.structural_profile_version, "template_validation_evidence_invalid"
        )
        _sha256(self.structure_summary_sha256, "template_validation_evidence_invalid")
        _nonempty_text(self.validator_version, "template_validation_evidence_invalid")
        _utc(self.validated_at_utc, "template_validation_evidence_invalid")
        if (
            type(self.validation_status) is not ValidationStatus
            or self.validation_status is not ValidationStatus.VALIDATED
            or type(self.token_occurrences) is not tuple
            or not all(
                type(item) is TemplateTokenOccurrence for item in self.token_occurrences
            )
        ):
            raise ValueError("template_validation_evidence_invalid")

    @classmethod
    def from_receipt(
        cls,
        validation_receipt_id: UUID,
        receipt: TemplateValidationReceipt,
        *,
        validated_at_utc: datetime,
    ) -> "TemplateValidationEvidence":
        if type(receipt) is not TemplateValidationReceipt:
            raise ValueError("template_validation_evidence_invalid")
        return cls(
            validation_receipt_id=validation_receipt_id,
            content_sha256=receipt.content_sha256,
            size_bytes=receipt.size_bytes,
            mime_type=receipt.mime_type,
            extension=receipt.extension,
            contract_id=receipt.contract_id,
            contract_version=receipt.contract_version,
            structural_profile_id=receipt.structural_profile_id,
            structural_profile_version=receipt.structural_profile_version,
            structure_summary_sha256=receipt.structure_summary_sha256,
            validator_version=receipt.validator_version,
            validated_at_utc=validated_at_utc,
            validation_status=ValidationStatus.VALIDATED,
            token_occurrences=receipt.token_occurrences,
        )


@dataclass(frozen=True, slots=True)
class DocumentTypeDescriptor:
    key: DocumentType
    display_name: str
    contract: TemplateContractManifest
    export_port_id: str
    seed_relative_path: str
    seed_sha256: str
    capabilities: tuple[TemplateCapability, ...]

    def __post_init__(self) -> None:
        _document_type(self.key, "document_type_descriptor_invalid")
        _nonempty_text(self.display_name, "document_type_descriptor_invalid")
        if type(self.contract) is not TemplateContractManifest:
            raise ValueError("document_type_descriptor_invalid")
        _nonempty_text(self.export_port_id, "document_type_descriptor_invalid")
        if (
            type(self.seed_relative_path) is not str
            or not self.seed_relative_path.startswith("templates/")
            or self.seed_relative_path.startswith("/")
            or ".." in self.seed_relative_path.split("/")
        ):
            raise ValueError("document_type_descriptor_invalid")
        _sha256(self.seed_sha256, "document_type_descriptor_invalid")
        if (
            type(self.capabilities) is not tuple
            or not self.capabilities
            or not all(type(item) is TemplateCapability for item in self.capabilities)
            or len(set(self.capabilities)) != len(self.capabilities)
        ):
            raise ValueError("document_type_descriptor_invalid")


@dataclass(frozen=True, slots=True)
class BlobRef:
    value: str
    content_sha256: str

    def __post_init__(self) -> None:
        _sha256(self.content_sha256, "blob_ref_invalid")
        if self.value != f"sha256/{self.content_sha256}":
            raise ValueError("blob_ref_invalid")


@dataclass(frozen=True, slots=True)
class VersionAllocation:
    """Opaque reservation from one tenant/type-bound unit of work."""

    template_version_id: UUID
    tenant_id: int
    document_type: DocumentType
    version: int

    def __post_init__(self) -> None:
        if type(self.template_version_id) is not UUID:
            raise ValueError("version_allocation_invalid")
        _positive_int(self.tenant_id, "version_allocation_invalid")
        _document_type(self.document_type, "version_allocation_invalid")
        _positive_int(self.version, "version_allocation_invalid")


@dataclass(frozen=True, slots=True)
class TemplateVersionRef:
    template_version_id: UUID
    tenant_id: int
    document_type: DocumentType
    version: int
    content_sha256: str
    size_bytes: int
    mime_type: str
    extension: str
    blob_ref: str
    contract_id: str
    contract_version: int
    validation_receipt_id: UUID
    validation_status: ValidationStatus
    validated_at_utc: datetime
    validator_version: str
    source: TemplateSource
    created_by_user_id: int | None
    created_at_utc: datetime
    validation_evidence: TemplateValidationEvidence

    def __post_init__(self) -> None:
        if type(self.template_version_id) is not UUID:
            raise ValueError("template_version_ref_invalid")
        _positive_int(self.tenant_id, "template_version_ref_invalid")
        _document_type(self.document_type, "template_version_ref_invalid")
        _positive_int(self.version, "template_version_ref_invalid")
        _sha256(self.content_sha256, "template_version_ref_invalid")
        _positive_int(self.size_bytes, "template_version_ref_invalid")
        if self.size_bytes > MAX_TEMPLATE_BYTES:
            raise ValueError("template_version_ref_invalid")
        if (
            self.mime_type != DOCX_MIME_TYPE
            or self.extension != ".docx"
            or self.blob_ref != f"sha256/{self.content_sha256}"
        ):
            raise ValueError("template_version_ref_invalid")
        _nonempty_text(self.contract_id, "template_version_ref_invalid")
        _positive_int(self.contract_version, "template_version_ref_invalid")
        if (
            type(self.validation_receipt_id) is not UUID
            or type(self.validation_status) is not ValidationStatus
            or self.validation_status is not ValidationStatus.VALIDATED
        ):
            raise ValueError("template_version_ref_invalid")
        _utc(self.validated_at_utc, "template_version_ref_invalid")
        _nonempty_text(self.validator_version, "template_version_ref_invalid")
        if type(self.source) is not TemplateSource:
            raise ValueError("template_version_ref_invalid")
        if self.source is TemplateSource.REPOSITORY_SEED:
            if self.created_by_user_id is not None:
                raise ValueError("template_version_ref_invalid")
        else:
            _positive_int(self.created_by_user_id, "template_version_ref_invalid")
        _utc(self.created_at_utc, "template_version_ref_invalid")
        if type(self.validation_evidence) is not TemplateValidationEvidence:
            raise ValueError("template_version_ref_invalid")
        evidence = self.validation_evidence
        if (
            evidence.validation_receipt_id != self.validation_receipt_id
            or evidence.content_sha256 != self.content_sha256
            or evidence.size_bytes != self.size_bytes
            or evidence.mime_type != self.mime_type
            or evidence.extension != self.extension
            or evidence.contract_id != self.contract_id
            or evidence.contract_version != self.contract_version
            or evidence.validation_status is not self.validation_status
            or evidence.validated_at_utc != self.validated_at_utc
            or evidence.validator_version != self.validator_version
        ):
            raise ValueError("template_version_ref_invalid")


@dataclass(frozen=True, slots=True)
class TemplateRegistryState:
    tenant_id: int
    document_type: DocumentType
    registry_revision: int
    active_version_id: UUID | None
    active_content_sha256: str | None
    last_transition_event_id: UUID

    def __post_init__(self) -> None:
        _positive_int(self.tenant_id, "template_registry_state_invalid")
        _document_type(self.document_type, "template_registry_state_invalid")
        _positive_int(self.registry_revision, "template_registry_state_invalid")
        if type(self.last_transition_event_id) is not UUID:
            raise ValueError("template_registry_state_invalid")
        if (self.active_version_id is None) != (self.active_content_sha256 is None):
            raise ValueError("template_registry_state_invalid")
        if self.active_version_id is not None:
            if type(self.active_version_id) is not UUID:
                raise ValueError("template_registry_state_invalid")
            _sha256(self.active_content_sha256, "template_registry_state_invalid")


@dataclass(frozen=True, slots=True)
class TemplateVersionSummary:
    """Pathless immutable version metadata safe for permission projections."""

    template_version_id: UUID
    tenant_id: int
    document_type: DocumentType
    version: int
    content_sha256: str
    contract_id: str
    contract_version: int
    validated_at_utc: datetime
    created_at_utc: datetime

    def __post_init__(self) -> None:
        if type(self.template_version_id) is not UUID:
            raise ValueError("template_version_summary_invalid")
        _positive_int(self.tenant_id, "template_version_summary_invalid")
        _document_type(self.document_type, "template_version_summary_invalid")
        _positive_int(self.version, "template_version_summary_invalid")
        _sha256(self.content_sha256, "template_version_summary_invalid")
        _nonempty_text(self.contract_id, "template_version_summary_invalid")
        _positive_int(self.contract_version, "template_version_summary_invalid")
        _utc(self.validated_at_utc, "template_version_summary_invalid")
        _utc(self.created_at_utc, "template_version_summary_invalid")


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    allowed: bool
    policy_version: str
    reason_code: str

    def __post_init__(self) -> None:
        if type(self.allowed) is not bool:
            raise ValueError("permission_decision_invalid")
        _nonempty_text(self.policy_version, "permission_decision_invalid")
        _nonempty_text(self.reason_code, "permission_decision_invalid")


@dataclass(frozen=True, slots=True)
class TemplatePermissionProjection:
    tenant_id: int
    document_type: DocumentType | None
    allowed_actions: tuple[TemplateCapability, ...]
    versions: tuple[TemplateVersionSummary, ...]
    active_version: TemplateVersionSummary | None

    def __post_init__(self) -> None:
        _positive_int(self.tenant_id, "template_permission_projection_invalid")
        if self.document_type is not None:
            _document_type(self.document_type, "template_permission_projection_invalid")
        if (
            type(self.allowed_actions) is not tuple
            or not all(
                type(item) is TemplateCapability for item in self.allowed_actions
            )
            or len(set(self.allowed_actions)) != len(self.allowed_actions)
            or type(self.versions) is not tuple
            or not all(type(item) is TemplateVersionSummary for item in self.versions)
            or any(
                item.tenant_id != self.tenant_id
                or (
                    self.document_type is not None
                    and item.document_type is not self.document_type
                )
                for item in self.versions
            )
            or (
                self.active_version is not None
                and (
                    type(self.active_version) is not TemplateVersionSummary
                    or self.active_version.tenant_id != self.tenant_id
                    or (
                        self.document_type is not None
                        and self.active_version.document_type is not self.document_type
                    )
                )
            )
        ):
            raise ValueError("template_permission_projection_invalid")


@dataclass(frozen=True, slots=True)
class TemplateTransitionEvent:
    event_id: UUID
    tenant_id: int
    document_type: DocumentType
    registry_revision: int
    active_version_id: UUID | None
    active_content_sha256: str | None
    occurred_at_utc: datetime

    def __post_init__(self) -> None:
        if type(self.event_id) is not UUID:
            raise ValueError("template_transition_event_invalid")
        _positive_int(self.tenant_id, "template_transition_event_invalid")
        _document_type(self.document_type, "template_transition_event_invalid")
        _positive_int(self.registry_revision, "template_transition_event_invalid")
        if (self.active_version_id is None) != (self.active_content_sha256 is None):
            raise ValueError("template_transition_event_invalid")
        if self.active_version_id is not None:
            if type(self.active_version_id) is not UUID:
                raise ValueError("template_transition_event_invalid")
            _sha256(self.active_content_sha256, "template_transition_event_invalid")
        _utc(self.occurred_at_utc, "template_transition_event_invalid")


@dataclass(frozen=True, slots=True)
class TransitionReceipt:
    document_type: DocumentType
    active_version_id: UUID | None
    registry_revision: int
    content_sha256: str | None

    def __post_init__(self) -> None:
        _document_type(self.document_type, "transition_receipt_invalid")
        _positive_int(self.registry_revision, "transition_receipt_invalid")
        if (self.active_version_id is None) != (self.content_sha256 is None):
            raise ValueError("transition_receipt_invalid")
        if self.active_version_id is not None:
            if type(self.active_version_id) is not UUID:
                raise ValueError("transition_receipt_invalid")
            _sha256(self.content_sha256, "transition_receipt_invalid")


@dataclass(frozen=True, slots=True)
class TemplateAuditEvent:
    event_id: UUID
    action: TemplateCapability
    outcome: AuditOutcome
    tenant_id: int
    user_id: int
    session_hash: str
    document_type: DocumentType
    template_version_id: UUID | None
    content_sha256: str | None
    contract_id: str | None
    contract_version: int | None
    registry_revision: int | None
    occurred_at_utc: datetime
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            type(self.event_id) is not UUID
            or type(self.action) is not TemplateCapability
            or type(self.outcome) is not AuditOutcome
        ):
            raise ValueError("template_audit_event_invalid")
        _positive_int(self.tenant_id, "template_audit_event_invalid")
        _positive_int(self.user_id, "template_audit_event_invalid")
        _sha256(self.session_hash, "template_audit_event_invalid")
        _document_type(self.document_type, "template_audit_event_invalid")
        evidence = (
            self.template_version_id,
            self.content_sha256,
            self.contract_id,
            self.contract_version,
            self.registry_revision,
        )
        if not (
            all(item is None for item in evidence)
            or all(item is not None for item in evidence)
        ):
            raise ValueError("template_audit_event_invalid")
        if (
            self.template_version_id is not None
            and type(self.template_version_id) is not UUID
        ):
            raise ValueError("template_audit_event_invalid")
        if self.content_sha256 is not None:
            _sha256(self.content_sha256, "template_audit_event_invalid")
        if self.contract_id is not None:
            _nonempty_text(self.contract_id, "template_audit_event_invalid")
        if self.contract_version is not None:
            _positive_int(self.contract_version, "template_audit_event_invalid")
        if self.registry_revision is not None:
            _positive_int(self.registry_revision, "template_audit_event_invalid")
        _utc(self.occurred_at_utc, "template_audit_event_invalid")
        _positive_int(self.schema_version, "template_audit_event_invalid")


@dataclass(frozen=True, slots=True)
class CommitReceipt:
    committed: bool

    def __post_init__(self) -> None:
        if self.committed is not True:
            raise ValueError("commit_receipt_invalid")


@dataclass(frozen=True, slots=True)
class TemplateExportBinding:
    tenant_id: int
    document_type: DocumentType
    template_version_id: UUID
    version: int
    content_sha256: str
    contract_id: str
    contract_version: int

    def __post_init__(self) -> None:
        _positive_int(self.tenant_id, "template_export_binding_invalid")
        _document_type(self.document_type, "template_export_binding_invalid")
        if type(self.template_version_id) is not UUID:
            raise ValueError("template_export_binding_invalid")
        _positive_int(self.version, "template_export_binding_invalid")
        _sha256(self.content_sha256, "template_export_binding_invalid")
        _nonempty_text(self.contract_id, "template_export_binding_invalid")
        _positive_int(self.contract_version, "template_export_binding_invalid")


@dataclass(frozen=True, slots=True)
class RenderedTemplate:
    binding: TemplateExportBinding
    rendered_bytes: bytes
    rendered_sha256: str

    def __post_init__(self) -> None:
        if (
            type(self.binding) is not TemplateExportBinding
            or type(self.rendered_bytes) is not bytes
        ):
            raise ValueError("rendered_template_invalid")
        _sha256(self.rendered_sha256, "rendered_template_invalid")


@dataclass(frozen=True, slots=True)
class ExportParseReport:
    binding: TemplateExportBinding
    valid: bool
    structure_summary_sha256: str
    unresolved_token_ids: tuple[str, ...]
    has_macros: bool
    has_external_relationships: bool

    def __post_init__(self) -> None:
        if (
            type(self.binding) is not TemplateExportBinding
            or type(self.valid) is not bool
            or type(self.unresolved_token_ids) is not tuple
            or not all(type(item) is str and item for item in self.unresolved_token_ids)
            or type(self.has_macros) is not bool
            or type(self.has_external_relationships) is not bool
        ):
            raise ValueError("export_parse_report_invalid")
        _sha256(self.structure_summary_sha256, "export_parse_report_invalid")


@dataclass(frozen=True, slots=True)
class SyntheticPreviewCase:
    fixture_id: str
    provenance: str
    payload: tuple[tuple[str, object], ...]

    def __post_init__(self) -> None:
        if (
            type(self.fixture_id) is not str
            or not self.fixture_id
            or self.provenance != "synthetic"
            or type(self.payload) is not tuple
            or not all(
                type(item) is tuple
                and len(item) == 2
                and type(item[0]) is str
                and bool(item[0])
                and _deeply_immutable(item[1])
                for item in self.payload
            )
        ):
            raise ValueError("synthetic_preview_case_invalid")


@dataclass(frozen=True, slots=True)
class TemplatePreviewReceipt:
    template_version_id: UUID
    content_sha256: str
    rendered_bytes: bytes
    parse_report: ExportParseReport
    persisted: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.template_version_id) is not UUID
            or type(self.rendered_bytes) is not bytes
            or type(self.parse_report) is not ExportParseReport
            or self.persisted is not False
        ):
            raise ValueError("template_preview_receipt_invalid")
        _sha256(self.content_sha256, "template_preview_receipt_invalid")


@dataclass(frozen=True, slots=True)
class BackupAttestation:
    schema_version: int
    artifact_sha256: str
    artifact_size: int
    protected_image: str
    created_at_utc: datetime
    status: str

    def __post_init__(self) -> None:
        _positive_int(self.schema_version, "backup_attestation_invalid")
        _sha256(self.artifact_sha256, "backup_attestation_invalid")
        _positive_int(self.artifact_size, "backup_attestation_invalid")
        _nonempty_text(self.protected_image, "backup_attestation_invalid")
        _utc(self.created_at_utc, "backup_attestation_invalid")
        if self.status != "verified":
            raise ValueError("backup_attestation_invalid")


@dataclass(frozen=True, slots=True)
class RestoreReceipt:
    expected_tenant_id: int
    committed: bool

    def __post_init__(self) -> None:
        _positive_int(self.expected_tenant_id, "restore_receipt_invalid")
        if self.committed is not True:
            raise ValueError("restore_receipt_invalid")


class TemplateBlobStorePort(Protocol):
    async def put_if_absent(self, content_sha256: str, content: bytes) -> BlobRef: ...
    async def read(self, blob_ref: BlobRef, expected_sha256: str) -> bytes: ...
    async def exists(self, blob_ref: BlobRef, expected_sha256: str) -> bool: ...


class TemplateVersionStorePort(Protocol):
    async def get_version(
        self, tenant_id: int, version_id: UUID
    ) -> TemplateVersionRef | None: ...
    async def snapshot(
        self, tenant_id: int, document_type: DocumentType
    ) -> TemplateRegistryState: ...


class TemplateUnitOfWork(Protocol):
    async def allocate_version(self) -> VersionAllocation: ...
    async def stage_version(
        self,
        allocation: VersionAllocation,
        version_ref: TemplateVersionRef,
    ) -> None: ...
    async def stage_transition(
        self, transition_event: TemplateTransitionEvent
    ) -> None: ...
    async def stage_audit(self, audit_event: TemplateAuditEvent) -> None: ...
    async def commit(self) -> CommitReceipt: ...


class TemplateUnitOfWorkPort(Protocol):
    async def begin(
        self, tenant_id: int, document_type: DocumentType
    ) -> TemplateUnitOfWork: ...


class TemplatePermissionPolicyPort(Protocol):
    async def project(
        self, current_trusted_session: object, document_type: DocumentType | None = None
    ) -> TemplatePermissionProjection: ...

    async def authorize(
        self,
        current_trusted_session: object,
        action: TemplateCapability,
        document_type: DocumentType,
        tenant_id: int,
    ) -> PermissionDecision: ...


class TemplateExportPort(Protocol):
    async def resolve_active(
        self, tenant_id: int, document_type: DocumentType
    ) -> TemplateExportBinding: ...
    async def render(
        self, binding: TemplateExportBinding, payload: object
    ) -> RenderedTemplate: ...
    async def parse(
        self, binding: TemplateExportBinding, rendered_bytes: bytes
    ) -> ExportParseReport: ...


class TemplateClockPort(Protocol):
    def utcnow(self) -> datetime: ...


class TemplateBackupPort(Protocol):
    async def create_template_backup(
        self,
        snapshot: object,
        destination_handle: object,
        *,
        protected_image: str,
        now: datetime,
    ) -> BackupAttestation: ...

    async def restore_template_backup(
        self,
        artifact_handle: object,
        target_handle: object,
        *,
        expected_tenant_id: int,
    ) -> RestoreReceipt: ...
