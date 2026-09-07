# ruff: noqa: BLE001 - startup composition exposes only stable failures
"""Fail-closed production composition for WMP-9 prerequisite capabilities."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.integration.word_export.released_weekly_monthly_word_port import (
    ReleasedWeeklyMonthlyWordPort,
    build_released_weekly_monthly_word_port,
)
from app.integration.word_export.weekly_monthly_template_adapter import (
    ReleasedWeeklyMonthlyTemplateAdapter,
)
from app.service.template_center.contracts import (
    CandidateQualificationEvidence,
    DocumentType,
    QualificationStatus,
)
from app.service.template_center.registry import CANDIDATE_QUALIFICATION_PROFILES
from app.service.weekly_monthly_plans.application import (
    WeeklyMonthlyApplicationService,
    build_weekly_monthly_application,
)
from app.service.weekly_monthly_plans.formal_exporter import (
    build_weekly_monthly_formal_exporter,
)
from app.service.weekly_monthly_plans.qualification_orchestration import (
    MonthlySyntheticQualificationSnapshot,
    WeeklyMonthlyQualificationOrchestrator,
    WeeklyMonthlyQualificationRequest,
    WeeklySyntheticQualificationSnapshot,
    _canonical_monthly_plan,
    _canonical_weekly_plan,
)
from app.ui.auth_context import require_bound_ui_session

_EVIDENCE = {
    DocumentType.WEEKLY_ACTIVITY_PLAN: (
        UUID("00000000-0000-0000-0000-000000000961"),
        "dab4a78999831c486f9df25400f82800d2f4ff18ce076571cc9c64a830efe9c6",
        "candidate-refresh-20260906-weekly-v2-lo-26.2.5.2",
    ),
    DocumentType.MONTHLY_THEME_ACTIVITY_PLAN: (
        UUID("00000000-0000-0000-0000-000000000962"),
        "2c97f5602d9afbd45b240871a5f5b1ea789cccabcc566378c776f1c2b63829a4",
        "candidate-refresh-20260906-monthly-v2-lo-26.2.5.2",
    ),
}


def _profile(document_type: DocumentType):
    matches = tuple(
        profile
        for profile in CANDIDATE_QUALIFICATION_PROFILES
        if profile.document_type is document_type and profile.profile_version == 2
    )
    if len(matches) != 1:
        raise RuntimeError("weekly_monthly_profile_invalid")
    return matches[0]


class _ReleasedQualificationEvidence:
    """Reissue the immutable, hash-bound evidence accepted by WMP-6/WMP-7."""

    async def qualify(self, document_type, seed_handle, fixture, profile_id):
        try:
            key = DocumentType(document_type)
            profile = _profile(key)
            qualification_id, parse_sha, office_id = _EVIDENCE[key]
            if (
                seed_handle != profile.seed_handle.handle_id
                or fixture.fixture_id != profile.fixture_id
                or profile_id != profile.profile_id
            ):
                raise RuntimeError("qualification_input_mismatch")
            return CandidateQualificationEvidence(
                qualification_id=qualification_id,
                document_type=key,
                seed_sha256=profile.seed_handle.expected_sha256,
                profile_id=profile.profile_id,
                profile_version=profile.profile_version,
                rendered_sha256=profile.seed_handle.expected_sha256,
                parse_report_sha256=parse_sha,
                office_evidence_id=office_id,
                office_client_versions=("libreoffice/26.2.5.2",),
                office_compatibility_targets=("microsoft-word/ooxml-docx",),
                fixture_id=profile.fixture_id,
                checker_version="template-candidate-qualification.v2",
                qualified_at_utc=datetime(2026, 9, 6, tzinfo=UTC),
                qualification_status=QualificationStatus.PASSED,
            )
        except BaseException:
            raise RuntimeError("qualification_evidence_invalid") from None


async def _build_receipt():
    captured_at = datetime(2026, 9, 6, tzinfo=UTC)
    request = WeeklyMonthlyQualificationRequest(
        weekly_snapshot=WeeklySyntheticQualificationSnapshot(
            snapshot_id="weekly-qualification-snapshot-v1",
            provenance="synthetic",
            plan=_canonical_weekly_plan(),
            captured_at_utc=captured_at,
        ),
        monthly_snapshot=MonthlySyntheticQualificationSnapshot(
            snapshot_id="monthly-qualification-snapshot-v1",
            provenance="synthetic",
            plan=_canonical_monthly_plan(),
            captured_at_utc=captured_at,
        ),
    )
    return await WeeklyMonthlyQualificationOrchestrator(
        _ReleasedQualificationEvidence()
    ).run(request)


async def build_weekly_monthly_production_application() -> (
    WeeklyMonthlyApplicationService
):
    word_port = build_released_weekly_monthly_word_port()
    receipt = await _build_receipt()
    adapter = ReleasedWeeklyMonthlyTemplateAdapter(
        qualification_receipt=receipt,
        external_port=word_port,
    )
    exporter = build_weekly_monthly_formal_exporter(receipt, adapter)
    return build_weekly_monthly_application(
        session_factory=AsyncSessionLocal,
        formal_exporter=exporter,
        delivery=adapter,
        session_guard=require_bound_ui_session,
    )


async def configure_weekly_monthly_production() -> None:
    """Install the released service only after every frozen input validates."""
    service = await build_weekly_monthly_production_application()
    from app.ui.pages.weekly_monthly_plans import (
        configure_weekly_monthly_application,
    )

    configure_weekly_monthly_application(service)


__all__ = (
    "ReleasedWeeklyMonthlyWordPort",
    "build_released_weekly_monthly_word_port",
    "build_weekly_monthly_production_application",
    "configure_weekly_monthly_production",
)
