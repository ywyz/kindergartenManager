"""Versioned, immutable phase-1 document and contract registries."""

from app.service.template_center.contracts import (
    CandidateQualificationProfile,
    ControlledSeedHandle,
    DocumentType,
    DocumentTypeDescriptor,
    TemplateCapability,
    TemplateCenterError,
    TemplateContractManifest,
    TemplateErrorCode,
)

GLOBAL_KNOWN_DOCUMENT_TYPES = tuple(item.value for item in DocumentType)
PHASE1_ENABLED_DOCUMENT_TYPES = GLOBAL_KNOWN_DOCUMENT_TYPES[:5]
PHASE1_RESERVED_DOCUMENT_TYPES = GLOBAL_KNOWN_DOCUMENT_TYPES[5:]

_CANDIDATE_PROFILE_ROWS = (
    (
        DocumentType.WEEKLY_ACTIVITY_PLAN,
        "controlled-weekplan-seed-v2",
        "weekly_activity_plan-profile-v2",
        2,
        "157abf313206d94a90337807e490e0ea0ad8b72cf0d3eb6d7ef0ed6a6aa93f14",
        "tables:word/document.xml:3x9x7",
    ),
    (
        DocumentType.MONTHLY_THEME_ACTIVITY_PLAN,
        "controlled-monthplan-seed-v2",
        "monthly_theme_activity_plan-profile-v2",
        2,
        "de806aed3289f0a5f0019318aec63380f681dae3113383d47d03b363337b69d5",
        "tables:word/document.xml:1x8x4",
    ),
)

_WEEKLY_CANDIDATE_PARTS = (
    "word/document.xml",
    "word/footnotes.xml",
    "word/endnotes.xml",
    "word/theme/theme1.xml",
    "word/settings.xml",
    "word/numbering.xml",
    "word/styles.xml",
    "word/webSettings.xml",
    "word/fontTable.xml",
)
_MONTHLY_CANDIDATE_PARTS = (
    "word/document.xml",
    "word/theme/theme1.xml",
    "word/settings.xml",
    "word/numbering.xml",
    "word/styles.xml",
    "word/fontTable.xml",
)

_CAPABILITIES = tuple(TemplateCapability)
_SEEDS = (
    (
        "daily_plan",
        "每日活动计划",
        "teacherplan.docx",
        "9ed9702c8ba1d632b6d0eeeb18fc3bd310d75d661f43c862fd41f11e4a961828",
    ),
    (
        "game_observation",
        "游戏观察记录",
        "ObservationRecord.docx",
        "73bed753a2b15cb6ee1bcd92dbf958303c72e1baa26fd1a0dc981378eddd577f",
    ),
    (
        "one_on_one_listening",
        "一对一倾听记录",
        "OneOnOneListeningSmallSecond.docx",
        "65664e55aec919c280299fc322bb85723e33e3fad4ee8931b021e4cf817e57fd",
    ),
    (
        "homemade_teaching",
        "自制教玩具",
        "homemadeteaching.docx",
        "e5bd321f9de23ef1ba5498492e98c55217d40aa4bf70cbe4df5801009027933d",
    ),
    (
        "course_review_activity",
        "课程审议活动",
        "coursereviewactivity.docx",
        "b2194e10621320a5929917c634679ab47f2c0777a857bb9d3bbc986cd81d3e97",
    ),
)


def _manifest(key: str) -> TemplateContractManifest:
    return TemplateContractManifest(
        contract_id=f"kg.template.{key}.legacy_structural",
        contract_version=1,
        placeholder_contract_version=1,
        structural_profile_id=f"legacy_structural_v1.{key}",
        structural_profile_version=1,
        renderer_id=f"kg.renderer.{key}.v1",
        parser_id=f"kg.parser.{key}.v1",
        allowed_parts=("word/document.xml",),
        required_anchors=(f"legacy:{key}:root",),
    )


def _candidate_profile(
    document_type: DocumentType,
    handle_id: str,
    profile_id: str,
    profile_version: int,
    seed_sha256: str,
    table_anchor: str,
) -> CandidateQualificationProfile:
    allowed_parts = (
        _WEEKLY_CANDIDATE_PARTS
        if document_type is DocumentType.WEEKLY_ACTIVITY_PLAN
        else _MONTHLY_CANDIDATE_PARTS
    )
    contract = TemplateContractManifest(
        contract_id=f"kg.template.{document_type.value}.candidate",
        contract_version=profile_version,
        placeholder_contract_version=1,
        structural_profile_id=profile_id,
        structural_profile_version=profile_version,
        renderer_id=f"kg.renderer.{document_type.value}.candidate.v1",
        parser_id=f"kg.parser.{document_type.value}.candidate.v1",
        allowed_parts=allowed_parts,
        required_anchors=(table_anchor,),
    )
    return CandidateQualificationProfile(
        document_type=document_type,
        seed_handle=ControlledSeedHandle(
            handle_id=handle_id,
            document_type=document_type,
            expected_sha256=seed_sha256,
        ),
        profile_id=profile_id,
        profile_version=profile_version,
        fixture_id="weekly-monthly-fixture-v1",
        contract=contract,
    )


CANDIDATE_QUALIFICATION_PROFILES = tuple(
    _candidate_profile(*row) for row in _CANDIDATE_PROFILE_ROWS
)


def candidate_profile(
    document_type: object, seed_handle: object, profile_id: object
) -> CandidateQualificationProfile:
    """Resolve the two closed released candidate profiles only."""
    if not (
        type(document_type) is str
        and type(seed_handle) is str
        and type(profile_id) is str
    ):
        raise TemplateCenterError(TemplateErrorCode.INPUT_INVALID)
    for profile in CANDIDATE_QUALIFICATION_PROFILES:
        if (
            document_type == profile.document_type.value
            and seed_handle == profile.seed_handle.handle_id
            and profile_id == profile.profile_id
        ):
            return profile
    raise TemplateCenterError(TemplateErrorCode.INPUT_INVALID)


INITIAL_DOCUMENT_DESCRIPTORS = tuple(
    DocumentTypeDescriptor(
        key=DocumentType(key),
        display_name=display_name,
        contract=_manifest(key),
        export_port_id="template_export_port.v1",
        seed_relative_path=f"templates/{filename}",
        seed_sha256=seed_sha256,
        capabilities=_CAPABILITIES,
    )
    for key, display_name, filename, seed_sha256 in _SEEDS
)


class InitialDocumentRegistry:
    """Closed phase-1 registry; it has no mutation or dynamic registration seam."""

    __slots__ = ()

    def known_keys(self) -> tuple[str, ...]:
        return GLOBAL_KNOWN_DOCUMENT_TYPES

    def descriptors(self) -> tuple[DocumentTypeDescriptor, ...]:
        return INITIAL_DOCUMENT_DESCRIPTORS

    def is_enabled(self, document_type: str | DocumentType) -> bool:
        key = (
            document_type.value
            if type(document_type) is DocumentType
            else document_type
        )
        return type(key) is str and key in PHASE1_ENABLED_DOCUMENT_TYPES

    def resolve(self, document_type: str | DocumentType) -> DocumentTypeDescriptor:
        key = (
            document_type.value
            if type(document_type) is DocumentType
            else document_type
        )
        if type(key) is not str or key not in GLOBAL_KNOWN_DOCUMENT_TYPES:
            raise TemplateCenterError(TemplateErrorCode.UNKNOWN_DOCUMENT_TYPE)
        for descriptor in INITIAL_DOCUMENT_DESCRIPTORS:
            if descriptor.key.value == key:
                return descriptor
        raise TemplateCenterError(TemplateErrorCode.DOCUMENT_TYPE_RESERVED_UNTIL_GATE)


class InitialContractRegistry:
    """Closed lookup for the five enabled legacy structural manifests."""

    __slots__ = ()

    def descriptors(self) -> tuple[TemplateContractManifest, ...]:
        return tuple(item.contract for item in INITIAL_DOCUMENT_DESCRIPTORS)

    def resolve(self, document_type: str | DocumentType) -> TemplateContractManifest:
        return InitialDocumentRegistry().resolve(document_type).contract


def build_initial_document_registry() -> InitialDocumentRegistry:
    return InitialDocumentRegistry()


def build_initial_contract_registry() -> InitialContractRegistry:
    return InitialContractRegistry()
