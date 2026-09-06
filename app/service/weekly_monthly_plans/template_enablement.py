"""Closed WMP-7 enablement gate for the qualified weekly/monthly pair."""

from enum import Enum

from app.service.template_center.contracts import (
    CandidateQualificationEvidence,
    DocumentType,
    DocumentTypeDescriptor,
    QualificationStatus,
    TemplateCapability,
    TemplateExportBinding,
    TemplateExportBindingKind,
)
from app.service.template_center.registry import (
    CANDIDATE_QUALIFICATION_PROFILES,
    GLOBAL_KNOWN_DOCUMENT_TYPES,
    INITIAL_DOCUMENT_DESCRIPTORS,
)
from app.service.weekly_monthly_plans.qualification_orchestration import (
    WeeklyMonthlyQualificationReceipt,
    _verify_qualification_receipt,
)

ENABLEMENT_CONTRACT_VERSION = "weekly-monthly-template-enablement.v1"

_WEEKLY = DocumentType.WEEKLY_ACTIVITY_PLAN
_MONTHLY = DocumentType.MONTHLY_THEME_ACTIVITY_PLAN
_ENABLED = (_WEEKLY, _MONTHLY)
_SNAPSHOT_SHA256 = {
    _WEEKLY: "d4631280016cff193b3e78b7ee9e4e50d06db7361466a51509526aedcd6fa2dd",
    _MONTHLY: "bc0843bf4d896de995c2ebfba5bb2f4a23150755ad7b26d8b78d1bde846489c9",
}
_EVIDENCE = {
    _WEEKLY: (
        "dab4a78999831c486f9df25400f82800d2f4ff18ce076571cc9c64a830efe9c6",
        "candidate-refresh-20260906-weekly-v2-lo-26.2.5.2",
    ),
    _MONTHLY: (
        "2c97f5602d9afbd45b240871a5f5b1ea789cccabcc566378c776f1c2b63829a4",
        "candidate-refresh-20260906-monthly-v2-lo-26.2.5.2",
    ),
}
_PROFILE_SIGNATURES = {
    _WEEKLY: (
        "controlled-weekplan-seed-v2",
        "f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b",
        "weekly_activity_plan-profile-v2",
        2,
        "weekly-monthly-fixture-v1",
        "kg.template.weekly_activity_plan.candidate",
        2,
        1,
        "weekly_activity_plan-profile-v2",
        2,
        "kg.renderer.weekly_activity_plan.candidate.v1",
        "kg.parser.weekly_activity_plan.candidate.v1",
        (
            "word/document.xml",
            "word/footnotes.xml",
            "word/endnotes.xml",
            "word/theme/theme1.xml",
            "word/settings.xml",
            "word/numbering.xml",
            "word/styles.xml",
            "word/webSettings.xml",
            "word/fontTable.xml",
        ),
        ("tables:word/document.xml:2x9x7",),
        (),
    ),
    _MONTHLY: (
        "controlled-monthplan-seed-v2",
        "f2e5dbe2a468dd15c55cdd6b70c5e15fe63048a3708b151732e208703b0d11f4",
        "monthly_theme_activity_plan-profile-v2",
        2,
        "weekly-monthly-fixture-v1",
        "kg.template.monthly_theme_activity_plan.candidate",
        2,
        1,
        "monthly_theme_activity_plan-profile-v2",
        2,
        "kg.renderer.monthly_theme_activity_plan.candidate.v1",
        "kg.parser.monthly_theme_activity_plan.candidate.v1",
        (
            "word/document.xml",
            "word/theme/theme1.xml",
            "word/settings.xml",
            "word/numbering.xml",
            "word/styles.xml",
            "word/fontTable.xml",
        ),
        ("tables:word/document.xml:1x8x4",),
        (),
    ),
}


class TemplateTypeEnablementErrorCode(str, Enum):
    RECEIPT_INVALID = "receipt_invalid"
    EVIDENCE_STALE = "evidence_stale"
    INPUT_INVALID = "input_invalid"
    BINDING_INVALID = "binding_invalid"


class TemplateTypeEnablementError(Exception):
    """A stable body-free WMP-7 rejection."""

    def __init__(self, code: TemplateTypeEnablementErrorCode) -> None:
        if type(code) is not TemplateTypeEnablementErrorCode:
            raise TypeError("template_type_enablement_error_code_invalid")
        self.code = code
        super().__init__(code.value)


def _profile_signature(profile: object) -> tuple[object, ...] | None:
    try:
        contract = profile.contract
        return (
            profile.seed_handle.handle_id,
            profile.seed_handle.expected_sha256,
            profile.profile_id,
            profile.profile_version,
            profile.fixture_id,
            contract.contract_id,
            contract.contract_version,
            contract.placeholder_contract_version,
            contract.structural_profile_id,
            contract.structural_profile_version,
            contract.renderer_id,
            contract.parser_id,
            contract.allowed_parts,
            contract.required_anchors,
            contract.tokens,
        )
    except AttributeError:
        return None


def _current_profiles() -> dict[DocumentType, object]:
    matches = {
        document_type: tuple(
            profile
            for profile in CANDIDATE_QUALIFICATION_PROFILES
            if profile.document_type is document_type
            and _profile_signature(profile) == _PROFILE_SIGNATURES[document_type]
        )
        for document_type in _ENABLED
    }
    if any(len(items) != 1 for items in matches.values()):
        raise TemplateTypeEnablementError(
            TemplateTypeEnablementErrorCode.EVIDENCE_STALE
        )
    return {key: items[0] for key, items in matches.items()}


def _evidence_matches(
    evidence: object, document_type: DocumentType, profile: object
) -> bool:
    if type(evidence) is not CandidateQualificationEvidence:
        return False
    parse_sha256, office_id = _EVIDENCE[document_type]
    return (
        evidence.document_type is document_type
        and evidence.seed_sha256 == profile.seed_handle.expected_sha256
        and evidence.profile_id == profile.profile_id
        and evidence.profile_version == profile.profile_version
        and evidence.rendered_sha256 == profile.seed_handle.expected_sha256
        and evidence.parse_report_sha256 == parse_sha256
        and evidence.office_evidence_id == office_id
        and evidence.office_client_versions == ("libreoffice/26.2.5.2",)
        and evidence.office_compatibility_targets == ("microsoft-word/ooxml-docx",)
        and evidence.fixture_id == profile.fixture_id
        and evidence.checker_version == "template-candidate-qualification.v2"
        and evidence.qualified_at_utc.isoformat() == "2026-09-06T00:00:00+00:00"
        and evidence.qualification_status is QualificationStatus.PASSED
    )


def _validate_receipt(
    receipt: object,
) -> tuple[object, object]:
    if type(receipt) is not WeeklyMonthlyQualificationReceipt:
        raise TemplateTypeEnablementError(
            TemplateTypeEnablementErrorCode.RECEIPT_INVALID
        )
    try:
        if (
            receipt.weekly_snapshot_sha256 != _SNAPSHOT_SHA256[_WEEKLY]
            or receipt.monthly_snapshot_sha256 != _SNAPSHOT_SHA256[_MONTHLY]
        ):
            raise TemplateTypeEnablementError(
                TemplateTypeEnablementErrorCode.RECEIPT_INVALID
            )
        profiles = _current_profiles()
        if not _evidence_matches(receipt.weekly_evidence, _WEEKLY, profiles[_WEEKLY]):
            raise TemplateTypeEnablementError(
                TemplateTypeEnablementErrorCode.EVIDENCE_STALE
            )
        if not _evidence_matches(
            receipt.monthly_evidence, _MONTHLY, profiles[_MONTHLY]
        ):
            raise TemplateTypeEnablementError(
                TemplateTypeEnablementErrorCode.EVIDENCE_STALE
            )
        if not _verify_qualification_receipt(receipt):
            raise TemplateTypeEnablementError(
                TemplateTypeEnablementErrorCode.RECEIPT_INVALID
            )
        return profiles[_WEEKLY], profiles[_MONTHLY]
    except TemplateTypeEnablementError:
        raise
    except (AttributeError, TypeError, ValueError):
        raise TemplateTypeEnablementError(
            TemplateTypeEnablementErrorCode.RECEIPT_INVALID
        ) from None


def _candidate_descriptor(profile: object, display_name: str) -> DocumentTypeDescriptor:
    return DocumentTypeDescriptor(
        key=profile.document_type,
        display_name=display_name,
        contract=profile.contract,
        export_port_id="template_export_port.v1",
        seed_relative_path=(
            "templates/weekplan.docx"
            if profile.document_type is _WEEKLY
            else "templates/monthplan.docx"
        ),
        seed_sha256=profile.seed_handle.expected_sha256,
        capabilities=(TemplateCapability.READ,),
    )


class _Wmp7DocumentRegistry:
    __slots__ = ("__descriptors",)

    def __init__(self, weekly_profile: object, monthly_profile: object) -> None:
        self.__descriptors = INITIAL_DOCUMENT_DESCRIPTORS + (
            _candidate_descriptor(weekly_profile, "每周活动计划"),
            _candidate_descriptor(monthly_profile, "月主题活动计划"),
        )

    def known_keys(self) -> tuple[str, ...]:
        return GLOBAL_KNOWN_DOCUMENT_TYPES

    def descriptors(self) -> tuple[DocumentTypeDescriptor, ...]:
        return self.__descriptors

    def is_enabled(self, document_type: object) -> bool:
        key = (
            document_type.value
            if type(document_type) is DocumentType
            else document_type
        )
        return type(key) is str and key in GLOBAL_KNOWN_DOCUMENT_TYPES

    def resolve(self, document_type: object) -> DocumentTypeDescriptor:
        key = (
            document_type.value
            if type(document_type) is DocumentType
            else document_type
        )
        for descriptor in self.__descriptors:
            if descriptor.key.value == key:
                return descriptor
        raise TemplateTypeEnablementError(TemplateTypeEnablementErrorCode.INPUT_INVALID)


def _build_wmp7_document_registry(receipt: object) -> _Wmp7DocumentRegistry:
    weekly_profile, monthly_profile = _validate_receipt(receipt)
    return _Wmp7DocumentRegistry(weekly_profile, monthly_profile)


class _WeeklyMonthlyActiveBindingGate:
    __slots__ = ("__active_port",)

    def __init__(self, active_port: object) -> None:
        self.__active_port = active_port

    async def resolve_active(
        self, tenant_id: object, document_type: object
    ) -> TemplateExportBinding:
        if type(tenant_id) is not int or tenant_id <= 0:
            raise TemplateTypeEnablementError(
                TemplateTypeEnablementErrorCode.INPUT_INVALID
            )
        try:
            key = (
                document_type
                if type(document_type) is DocumentType
                else DocumentType(document_type)
            )
        except (TypeError, ValueError):
            raise TemplateTypeEnablementError(
                TemplateTypeEnablementErrorCode.INPUT_INVALID
            ) from None
        if key not in _ENABLED:
            raise TemplateTypeEnablementError(
                TemplateTypeEnablementErrorCode.INPUT_INVALID
            )

        profile = _current_profiles()[key]
        try:
            binding = await self.__active_port.resolve_active(tenant_id, key)
        except Exception:  # noqa: BLE001 - sanitize the closed port boundary
            raise TemplateTypeEnablementError(
                TemplateTypeEnablementErrorCode.BINDING_INVALID
            ) from None
        if not (
            type(binding) is TemplateExportBinding
            and binding.kind is TemplateExportBindingKind.ACTIVE
            and binding.tenant_id == tenant_id
            and binding.document_type is key
            and binding.content_sha256 == profile.seed_handle.expected_sha256
            and binding.contract_id == profile.contract.contract_id
            and binding.contract_version == profile.contract.contract_version
        ):
            raise TemplateTypeEnablementError(
                TemplateTypeEnablementErrorCode.BINDING_INVALID
            )
        return binding


def build_weekly_monthly_active_binding_gate(
    receipt: object, active_port: object
) -> _WeeklyMonthlyActiveBindingGate:
    _build_wmp7_document_registry(receipt)
    if not callable(getattr(active_port, "resolve_active", None)):
        raise TemplateTypeEnablementError(TemplateTypeEnablementErrorCode.INPUT_INVALID)
    return _WeeklyMonthlyActiveBindingGate(active_port)


__all__ = (
    "ENABLEMENT_CONTRACT_VERSION",
    "TemplateTypeEnablementError",
    "TemplateTypeEnablementErrorCode",
    "build_weekly_monthly_active_binding_gate",
)
