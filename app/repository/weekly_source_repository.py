"""Narrow teaching projection, invoked only after exact-day authorization."""

from sqlalchemy import insert, select

from app.core.models.user import User
from app.repository.source_mapping_repository import (
    DAILY,
    EVENT,
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


PROJECTION_FIELDS = (*FIELDS, "morning_activity")


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

    async def owned_identities(self, scope, user_id):
        """Unmapped personal rows stay personal; no identity mapping is written.

        A legacy label is usable only when it names one canonical class in this
        semester. Existing mappings, including mappings to another class, win.
        """
        from app.core.models.academic_identity import TABLES

        classes, semesters = TABLES["class_instance"], TABLES["class_semester"]
        eligible = (
            select(classes.c.id, classes.c.display_name, classes.c.grade)
            .join(
                semesters,
                (semesters.c.tenant_id == classes.c.tenant_id)
                & (semesters.c.class_instance_id == classes.c.id),
            )
            .where(
                classes.c.tenant_id == self.tenant_id,
                semesters.c.semester_id == scope.semester_id,
            )
        )
        rows = (await self.session.execute(eligible)).mappings().all()
        target = next((r for r in rows if r["id"] == scope.class_instance_id), None)
        if (
            target is None
            or sum(
                (r["display_name"], r["grade"])
                == (target["display_name"], target["grade"])
                for r in rows
            )
            != 1
        ):
            return ()
        from datetime import timedelta

        query = (
            select(DAILY.c.id, DAILY.c.plan_date, DAILY.c.revision)
            .where(
                DAILY.c.tenant_id == self.tenant_id,
                DAILY.c.user_id == user_id,
                DAILY.c.class_name == target["display_name"],
                DAILY.c.grade == target["grade"],
                DAILY.c.plan_date >= scope.anchor_monday - timedelta(days=1),
                DAILY.c.plan_date <= scope.anchor_monday + timedelta(days=5),
                ~select(MAPPING.c.daily_plan_id)
                .where(
                    MAPPING.c.tenant_id == self.tenant_id,
                    MAPPING.c.daily_plan_id == DAILY.c.id,
                )
                .exists(),
            )
            .order_by(DAILY.c.id)
        )
        events = (
            (
                await self.session.execute(
                    select(EVENT)
                    .where(
                        EVENT.c.tenant_id == self.tenant_id,
                        EVENT.c.source_user_id == user_id,
                        EVENT.c.class_instance_id == scope.class_instance_id,
                        EVENT.c.semester_id == scope.semester_id,
                    )
                    .order_by(EVENT.c.id)
                )
            )
            .mappings()
            .all()
        )
        latest = {e["daily_plan_id"]: e for e in events}
        return tuple(
            {
                "tenant_id": self.tenant_id,
                "daily_plan_id": r.id,
                "source_user_id": user_id,
                "source_date": r.plan_date,
                "class_instance_id": scope.class_instance_id,
                "semester_id": scope.semester_id,
                "mapping_id": latest[r.id]["id"] if r.id in latest else r.id,
                "revision": latest[r.id]["revision"] if r.id in latest else r.revision,
                "owned_class_name": target["display_name"],
                "owned_grade": target["grade"],
            }
            for r in (await self.session.execute(query))
        )

    async def project(self, mapping):
        q = (
            select(
                DAILY.c.id,
                DAILY.c.user_id,
                DAILY.c.plan_date,
                DAILY.c.revision,
                *(DAILY.c[n] for n in PROJECTION_FIELDS),
            )
            .where(
                DAILY.c.tenant_id == self.tenant_id,
                DAILY.c.id == mapping["daily_plan_id"],
            )
            .with_for_update()
        )
        if "owned_class_name" in mapping:
            q = q.where(
                DAILY.c.class_name == mapping["owned_class_name"],
                DAILY.c.grade == mapping["owned_grade"],
                DAILY.c.user_id == mapping["source_user_id"],
                ~select(MAPPING.c.daily_plan_id)
                .where(
                    MAPPING.c.tenant_id == self.tenant_id,
                    MAPPING.c.daily_plan_id == DAILY.c.id,
                )
                .exists(),
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
            *(row[n] or "" for n in PROJECTION_FIELDS),
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
