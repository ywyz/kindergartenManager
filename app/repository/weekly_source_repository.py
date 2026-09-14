"""Narrow teaching projection, invoked only after exact-day authorization."""

from sqlalchemy import insert, select

from app.core.models.user import User
from app.repository.source_mapping_repository import (
    DAILY,
    MAPPING,
    SourceMappingRepository,
)
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.root_contracts import canonical
from app.service.shared_weekly.source_contracts import SourceCandidate

FIELDS = (
    "morning_talk_topic",
    "morning_talk_questions",
    "activity_name",
    "outdoor_activity",
    "indoor_area",
)


class WeeklySourceRepository(SourceMappingRepository):
    async def identities(self, scope):
        q = (
            select(MAPPING)
            .where(
                MAPPING.c.tenant_id == self.tenant_id,
                MAPPING.c.class_instance_id == scope.class_instance_id,
                MAPPING.c.semester_id == scope.semester_id,
                MAPPING.c.source_date
                >= scope.anchor_monday.__class__.fromordinal(
                    scope.anchor_monday.toordinal() - 1
                ),
                MAPPING.c.source_date
                <= scope.anchor_monday.__class__.fromordinal(
                    scope.anchor_monday.toordinal() + 5
                ),
            )
            .order_by(MAPPING.c.daily_plan_id)
        )
        return tuple((await self.session.execute(q)).mappings())

    async def project(self, mapping):
        q = (
            select(
                DAILY.c.id,
                DAILY.c.user_id,
                DAILY.c.plan_date,
                DAILY.c.revision,
                *(DAILY.c[n] for n in FIELDS),
            )
            .where(
                DAILY.c.tenant_id == self.tenant_id,
                DAILY.c.id == mapping["daily_plan_id"],
            )
            .with_for_update()
        )
        row = (await self.session.execute(q)).mappings().one_or_none()
        if row is None or (row["user_id"], row["plan_date"]) != (
            mapping["source_user_id"],
            mapping["source_date"],
        ):
            raise IdentityRejected("source_unavailable")
        # Username is an existing display field, never an authorization key.
        name = (
            await self.session.execute(
                select(User.display_name).where(
                    User.tenant_id == self.tenant_id, User.id == row["user_id"]
                )
            )
        ).scalar_one()
        return SourceCandidate(
            row["id"],
            row["user_id"],
            row["plan_date"],
            row["revision"],
            mapping["mapping_id"],
            mapping["revision"],
            name or "",
            *(row[n] or "" for n in FIELDS),
        )

    async def audit_sources(self, root, assessment, action, operation_id):
        from app.core.models.weekly_sources import TABLES

        table = TABLES["shared_weekly_source_audit"]
        auth = assessment.stamp
        await self.session.execute(
            insert(table).values(
                tenant_id=self.tenant_id,
                actor_id=auth.user_id,
                plan_id=root["id"],
                version_id=root["current_version"],
                class_instance_id=auth.scope.class_instance_id,
                semester_id=auth.scope.semester_id,
                membership_revision=auth.membership_revision,
                assignments_json=canonical(auth.assignments),
                operation_id=operation_id,
                session_hash=auth.session_hash,
                action=action,
                outcome="success",
                reason="authorized",
            )
        )
