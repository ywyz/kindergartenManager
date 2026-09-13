"""Shared authoring UI composition with request-local trusted token lookup."""

from dataclasses import dataclass

from app.integration.word_export.shared_weekly_word import SharedWeeklyWordPort
from app.service.shared_weekly.authoring_application import AuthoringApplication
from app.service.shared_weekly.collaboration_application import CollaborationApplication
from app.service.shared_weekly.export_application import SharedWeeklyExportApplication
from app.service.shared_weekly.mapping_application import SourceMappingApplication
from app.service.shared_weekly.page_application import WeeklyPageApplication
from app.service.shared_weekly.people_application import PeopleDefaultsApplication
from app.service.shared_weekly.reduction_application import ReductionApplication


@dataclass(frozen=True, slots=True)
class SharedWeeklyServices:
    weekly: CollaborationApplication
    mapping: SourceMappingApplication
    people: PeopleDefaultsApplication
    authoring: AuthoringApplication
    page: WeeklyPageApplication
    exporting: SharedWeeklyExportApplication
    reduction: ReductionApplication


_services: SharedWeeklyServices | None = None


def build_shared_weekly_production_application(
    *, word_port=None
) -> SharedWeeklyServices:
    from nicegui import app

    from app.core.database import AsyncSessionLocal

    token_source = lambda: app.storage.user.get("token")
    authoring = AuthoringApplication(AsyncSessionLocal, token_source)
    exporting = SharedWeeklyExportApplication(
        authoring, SharedWeeklyWordPort() if word_port is None else word_port
    )
    reduction = ReductionApplication(authoring, exporting)
    authoring._reduction = reduction
    return SharedWeeklyServices(
        CollaborationApplication(AsyncSessionLocal, token_source),
        SourceMappingApplication(AsyncSessionLocal, token_source),
        PeopleDefaultsApplication(AsyncSessionLocal, token_source),
        authoring,
        WeeklyPageApplication(AsyncSessionLocal, token_source),
        exporting,
        reduction,
    )


async def configure_shared_weekly_production(*, word_port=None) -> None:
    global _services
    # Publish only after the independently trusted operator configuration and
    # current dependencies pass. Explicit injection is for isolated composition.
    _services = None
    if word_port is None:
        from app.service.shared_weekly.layout_startup import load_operator_word_port

        word_port = await load_operator_word_port()
    _services = build_shared_weekly_production_application(word_port=word_port)


def get_shared_weekly_services() -> SharedWeeklyServices:
    if _services is None:
        raise RuntimeError("shared_weekly_not_configured")
    return _services
