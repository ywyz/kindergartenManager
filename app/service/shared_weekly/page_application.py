"""Small authenticated page projections using the existing shared authorization."""

from dataclasses import dataclass
from datetime import date

from app.repository.weekly_page_repository import WeeklyPageRepository
from app.service.shared_weekly.contracts import SharedAction
from app.service.shared_weekly.root_application import SharedWeeklyApplication


@dataclass(frozen=True, slots=True)
class WeekChoice:
    class_id: int
    semester_id: int
    class_name: str
    start: date
    end: date


class WeeklyPageApplication(SharedWeeklyApplication):
    async def choices(self, expected) -> tuple[WeekChoice, ...]:
        async with self._identity.transaction(expected) as (identity, actor):
            rows = await WeeklyPageRepository(
                identity.session, actor.tenant_id
            ).choices(actor.user_id)
            return tuple(
                WeekChoice(
                    r["class_instance_id"],
                    r["semester_id"],
                    r["display_name"],
                    r["start_date"],
                    r["end_date"],
                )
                for r in rows
            )

    async def last_editor(self, expected, plan_id: int) -> str:
        async with self._identity.transaction(expected) as (identity, actor):
            _, root, _ = await self._locked(identity, actor, plan_id, SharedAction.READ)
            return await WeeklyPageRepository(identity.session, actor.tenant_id).editor(
                root["current_version"]
            )
