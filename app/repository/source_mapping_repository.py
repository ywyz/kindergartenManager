"""Tenant-bound identity projections and ordered mapping locks."""

from datetime import UTC, datetime

from sqlalchemy import insert, select, update

from app.core.models.academic_identity import TABLES as IDENTITIES
from app.core.models.daily_plan import DailyPlan
from app.core.models.source_mapping import TABLES
from app.core.models.user import User
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.mapping_contracts import MappingStamp

EVENT = TABLES["identity_mapping_event"]
MAPPING = TABLES["daily_plan_identity"]
DAILY = DailyPlan.__table__


class SourceMappingRepository:
    def __init__(self, session, tenant_id):
        self.session, self.tenant_id = session, tenant_id

    async def source_identity(self, source_id, lock=False):
        names = ("id", "user_id", "plan_date", "revision", "grade", "class_name")
        q = select(*(DAILY.c[n] for n in names)).where(
            DAILY.c.tenant_id == self.tenant_id, DAILY.c.id == source_id
        )
        if lock:
            q = q.with_for_update()
        row = (await self.session.execute(q)).mappings().one_or_none()
        if row is None:
            raise IdentityRejected("source_unavailable")
        return row

    async def mapping(self, source_id):
        return (
            (
                await self.session.execute(
                    select(MAPPING).where(
                        MAPPING.c.tenant_id == self.tenant_id,
                        MAPPING.c.daily_plan_id == source_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

    async def lock_scopes(self, identity, scopes):
        for cls, sem in sorted(set(scopes)):
            await identity.require(
                "class_semester", lock=True, class_instance_id=cls, semester_id=sem
            )
        a = IDENTITIES["teacher_class_assignment"]
        # Lock the complete bounded guard membership set in ID order before any root/source lock.
        from sqlalchemy import and_, or_

        q = (
            select(a)
            .where(
                a.c.tenant_id == self.tenant_id,
                or_(
                    *(
                        and_(a.c.class_instance_id == c, a.c.semester_id == s)
                        for c, s in scopes
                    )
                ),
            )
            .order_by(a.c.id)
            .with_for_update()
        )
        return tuple((await self.session.execute(q)).mappings())

    async def require_day_member(self, identity, user_id, cls, sem, day, assignments):
        user = (
            await self.session.execute(
                select(User).where(User.tenant_id == self.tenant_id, User.id == user_id)
            )
        ).scalar_one_or_none()
        semester = await identity.require("semester", id=sem)
        now = datetime.now(UTC).replace(tzinfo=None)
        active = tuple(
            a
            for a in assignments
            if a["user_id"] == user_id
            and a["class_instance_id"] == cls
            and a["semester_id"] == sem
            and a["revoked_at"] is None
            and a["valid_from"] <= now < a["valid_until"]
        )
        if (
            user is None
            or not user.is_active
            or user.role.value not in ("teacher", "teaching_admin")
            or any(
                not semester["start_date"]
                <= a["scope_start_date"]
                <= a["scope_end_date"]
                <= semester["end_date"]
                for a in active
            )
        ):
            raise IdentityRejected("source_unavailable")
        matches = tuple(
            (a["id"], a["revision"])
            for a in active
            if a["scope_start_date"] <= day <= a["scope_end_date"]
        )
        if not matches or not semester["start_date"] <= day <= semester["end_date"]:
            raise IdentityRejected("source_unavailable")
        identity.authorization_deadlines.append(
            min(a["valid_until"] for a in active if (a["id"], a["revision"]) in matches)
        )
        return (user.auth_epoch, matches)

    async def operation(self, operation_id):
        return (
            (
                await self.session.execute(
                    select(EVENT).where(
                        EVENT.c.tenant_id == self.tenant_id,
                        EVENT.c.operation_id == operation_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

    async def save(
        self, target, source, previous, actor, session_hash, binding_hash, operation_id
    ):
        if await self.operation(operation_id):
            raise IdentityRejected("operation_replayed")
        revision = previous["revision"] + 1 if previous else 1
        result = await self.session.execute(
            insert(EVENT).values(
                tenant_id=self.tenant_id,
                daily_plan_id=source["id"],
                source_user_id=source["user_id"],
                source_date=source["plan_date"],
                source_revision=source["revision"],
                class_instance_id=target.class_instance_id,
                semester_id=target.semester_id,
                revision=revision,
                previous_id=previous["mapping_id"] if previous else None,
                actor_id=actor.user_id,
                session_hash=session_hash,
                binding_hash=binding_hash,
                operation_id=operation_id,
            )
        )
        event_id = result.inserted_primary_key[0]
        values = {
            "source_user_id": source["user_id"],
            "source_date": source["plan_date"],
            "class_instance_id": target.class_instance_id,
            "semester_id": target.semester_id,
            "mapping_id": event_id,
            "revision": revision,
        }
        if previous:
            result = await self.session.execute(
                update(MAPPING)
                .where(
                    MAPPING.c.tenant_id == self.tenant_id,
                    MAPPING.c.daily_plan_id == source["id"],
                    MAPPING.c.mapping_id == previous["mapping_id"],
                    MAPPING.c.revision == previous["revision"],
                )
                .values(**values)
            )
            if result.rowcount != 1:
                raise IdentityRejected("mapping_conflict")
        else:
            await self.session.execute(
                insert(MAPPING).values(
                    tenant_id=self.tenant_id, daily_plan_id=source["id"], **values
                )
            )
        return MappingStamp(event_id, revision)
