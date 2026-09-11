"""Production collaboration composition with request-local trusted token lookup.

Services retain only bounded temporary confirmation state. No new public API or
complete authoring UI is installed by this WP-C composition.
"""

from dataclasses import dataclass

from app.service.shared_weekly.collaboration_application import CollaborationApplication
from app.service.shared_weekly.mapping_application import SourceMappingApplication
from app.service.shared_weekly.people_application import PeopleDefaultsApplication


@dataclass(frozen=True, slots=True)
class SharedWeeklyServices:
    weekly: CollaborationApplication
    mapping: SourceMappingApplication
    people: PeopleDefaultsApplication


_services: SharedWeeklyServices | None = None


def build_shared_weekly_production_application() -> SharedWeeklyServices:
    from nicegui import app

    from app.core.database import AsyncSessionLocal

    token_source = lambda: app.storage.user.get("token")
    return SharedWeeklyServices(
        CollaborationApplication(AsyncSessionLocal, token_source),
        SourceMappingApplication(AsyncSessionLocal, token_source),
        PeopleDefaultsApplication(AsyncSessionLocal, token_source),
    )


def configure_shared_weekly_production() -> None:
    global _services
    _services = build_shared_weekly_production_application()


def get_shared_weekly_services() -> SharedWeeklyServices:
    if _services is None:
        raise RuntimeError("shared_weekly_not_configured")
    return _services
