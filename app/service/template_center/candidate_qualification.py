"""Controlled synthetic candidate qualification for the two reserved plan types."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from uuid import uuid4

from app.service.template_center.contracts import (
    CandidateQualificationEvidence,
    ExportParseReport,
    OfficeQualificationResult,
    QualificationStatus,
    RenderedTemplate,
    SyntheticQualificationFixture,
    TemplateCenterError,
    TemplateErrorCode,
    TemplateExportBinding,
)
from app.service.template_center.registry import candidate_profile
from app.service.template_center.validator import validate_upload


CANDIDATE_CHECKER_VERSION = "template-candidate-qualification.v1"
_WORD_VERSION = re.compile(r"word/16\.0\.[0-9]{5}\.[0-9]{5}")
_LIBREOFFICE_VERSION = re.compile(
    r"libreoffice/(?P<major>[0-9]+)\.(?P<minor>[0-9]+)\.(?P<patch>[0-9]+)(?:\.(?P<build>[0-9]+))?"
)


def _parse_report_sha256(report: ExportParseReport) -> str:
    payload = {
        "binding_id": str(report.binding.candidate_binding_id),
        "external_relationships": report.has_external_relationships,
        "macros": report.has_macros,
        "structure_summary_sha256": report.structure_summary_sha256,
        "unresolved_token_ids": report.unresolved_token_ids,
        "valid": report.valid,
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _office_result_is_complete(result: OfficeQualificationResult) -> bool:
    if (
        result.status != "passed"
        or type(result.evidence_id) is not str
        or not result.evidence_id.strip()
        or len(result.client_versions) != 2
        or len(set(result.client_versions)) != 2
    ):
        return False
    word = [item for item in result.client_versions if _WORD_VERSION.fullmatch(item)]
    libreoffice = []
    for item in result.client_versions:
        match = _LIBREOFFICE_VERSION.fullmatch(item)
        if match and (int(match["major"]), int(match["minor"])) >= (24, 2):
            libreoffice.append(item)
    return len(word) == 1 and len(libreoffice) == 1


class TemplateCandidateQualificationJob:
    """One-method internal job; it cannot access active state or business data."""

    __slots__ = (
        "_controlled_seed_store",
        "_export_port",
        "_office_qualification_port",
        "_qualification_evidence_store",
    )

    def __init__(
        self,
        controlled_seed_store: object,
        export_port: object,
        office_qualification_port: object,
        qualification_evidence_store: object,
    ) -> None:
        self._controlled_seed_store = controlled_seed_store
        self._export_port = export_port
        self._office_qualification_port = office_qualification_port
        self._qualification_evidence_store = qualification_evidence_store

    async def qualify(
        self,
        document_type: str,
        seed_handle: str,
        fixture: SyntheticQualificationFixture,
        profile_id: str,
    ) -> CandidateQualificationEvidence:
        if (
            type(document_type) is not str
            or type(seed_handle) is not str
            or type(profile_id) is not str
            or type(fixture) is not SyntheticQualificationFixture
            or fixture.provenance != "synthetic"
        ):
            raise TemplateCenterError(TemplateErrorCode.INPUT_INVALID)
        profile = candidate_profile(document_type, seed_handle, profile_id)
        if fixture.fixture_id != profile.fixture_id:
            raise TemplateCenterError(TemplateErrorCode.INPUT_INVALID)

        try:
            seed_bytes = await self._controlled_seed_store.read_controlled_seed(
                profile.seed_handle, profile.document_type
            )
        except Exception as error:
            raise TemplateCenterError(TemplateErrorCode.STORAGE_FAILED) from error

        validation = validate_upload(
            content=seed_bytes,
            filename="controlled-candidate.docx",
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            contract=profile.contract,
        )
        if validation.content_sha256 != profile.seed_handle.expected_sha256:
            raise TemplateCenterError(TemplateErrorCode.VALIDATION_FAILED)
        binding = TemplateExportBinding.candidate(
            document_type=profile.document_type,
            content_sha256=validation.content_sha256,
            contract_id=validation.contract_id,
            contract_version=validation.contract_version,
            candidate_binding_id=uuid4(),
            profile_id=profile_id,
            profile_version=profile.profile_version,
        )

        try:
            rendered = await self._export_port.render(binding, fixture.values)
            if (
                type(rendered) is not RenderedTemplate
                or rendered.binding is not binding
                or sha256(rendered.rendered_bytes).hexdigest()
                != rendered.rendered_sha256
            ):
                raise ValueError("rendered_result_invalid")
            rendered_validation = validate_upload(
                content=rendered.rendered_bytes,
                filename="rendered-candidate.docx",
                content_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
                contract=profile.contract,
            )
            report = await self._export_port.parse(binding, rendered.rendered_bytes)
            if (
                type(report) is not ExportParseReport
                or report.binding is not binding
                or not report.valid
                or report.structure_summary_sha256
                != rendered_validation.structure_summary_sha256
                or report.unresolved_token_ids
                or report.has_macros
                or report.has_external_relationships
            ):
                raise ValueError("parse_report_invalid")
            office = await self._office_qualification_port.qualify(
                binding, report, profile_id
            )
            if type(
                office
            ) is not OfficeQualificationResult or not _office_result_is_complete(
                office
            ):
                raise ValueError("office_result_invalid")
        except Exception as error:
            raise TemplateCenterError(TemplateErrorCode.EXPORT_FAILED) from error

        evidence = CandidateQualificationEvidence(
            qualification_id=uuid4(),
            document_type=profile.document_type,
            seed_sha256=validation.content_sha256,
            profile_id=profile_id,
            profile_version=profile.profile_version,
            rendered_sha256=rendered.rendered_sha256,
            parse_report_sha256=_parse_report_sha256(report),
            office_evidence_id=office.evidence_id,
            office_client_versions=office.client_versions,
            fixture_id=fixture.fixture_id,
            checker_version=CANDIDATE_CHECKER_VERSION,
            qualified_at_utc=datetime.now(timezone.utc),
            qualification_status=QualificationStatus.PASSED,
        )
        try:
            stored = await self._qualification_evidence_store.append(evidence)
        except Exception as error:
            raise TemplateCenterError(TemplateErrorCode.STORAGE_FAILED) from error
        if stored is not evidence:
            raise TemplateCenterError(TemplateErrorCode.STORAGE_FAILED)
        return evidence
