"""Tenant scoped shared-root persistence, called inside the identity transaction."""

from datetime import UTC, datetime

from sqlalchemy import insert, select, update

from app.core.models.shared_weekly import TABLES
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.contracts import SharedWeekScope
from app.service.shared_weekly.root_contracts import (
    EditStamp,
    LoadedWeek,
    PlanStamp,
    WeeklyThemeDraft,
    canonical,
    facts_json,
    parse_facts,
    payload_hash,
)

ROOT, VERSION, DATE, AUDIT = (
    TABLES["shared_weekly_" + x] for x in ("plan", "version", "date", "audit")
)


class SharedWeeklyRepository:
    def __init__(self, session, tenant_id):
        self.session = session
        self.tenant_id = tenant_id

    def query(self, table):
        return select(table).where(table.c.tenant_id == self.tenant_id)

    async def root(self, plan_id, *, lock=False):
        query = self.query(ROOT).where(ROOT.c.id == plan_id)
        if lock:
            query = query.with_for_update()
        row = (await self.session.execute(query)).mappings().one_or_none()
        if row is None or row["contract"] != "shared_weekly_v1":
            raise IdentityRejected("scope_denied")
        return row

    @staticmethod
    def scope(row):
        return SharedWeekScope(
            row["class_instance_id"], row["semester_id"], row["anchor_monday"]
        )

    @staticmethod
    def stamp(row):
        return PlanStamp(row["id"], row["current_version"], row["revision"])

    async def by_scope(self, scope):
        return (
            (
                await self.session.execute(
                    self.query(ROOT)
                    .where(
                        ROOT.c.class_instance_id == scope.class_instance_id,
                        ROOT.c.semester_id == scope.semester_id,
                        ROOT.c.anchor_monday == scope.anchor_monday,
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )

    async def operation(self, op):
        return (
            (
                await self.session.execute(
                    self.query(AUDIT).where(AUDIT.c.operation_id == op)
                )
            )
            .mappings()
            .one_or_none()
        )

    async def require_new_operation(self, op):
        if await self.operation(op) is not None:
            raise IdentityRejected("operation_replayed")

    async def check_dates(self, root, facts):
        dates = tuple(
            (
                await self.session.execute(
                    select(DATE.c.day_date)
                    .where(
                        DATE.c.tenant_id == self.tenant_id, DATE.c.plan_id == root["id"]
                    )
                    .order_by(DATE.c.day_date)
                )
            ).scalars()
        )
        if dates != facts.columns:
            raise IdentityRejected("calendar_stale")

    async def audit(self, stamp, assessment, op, action, outcome):
        auth = assessment.stamp
        await self.session.execute(
            insert(AUDIT).values(
                tenant_id=self.tenant_id,
                actor_id=auth.user_id,
                class_instance_id=auth.scope.class_instance_id,
                semester_id=auth.scope.semester_id,
                plan_id=stamp.plan_id,
                version_id=stamp.current_version,
                revision=stamp.revision,
                membership_revision=auth.membership_revision,
                assignments_json=canonical(auth.assignments),
                operation_id=op,
                session_hash=auth.session_hash,
                action=action,
                outcome=outcome,
                reason="authorized",
            )
        )

    async def create(self, assessment, draft, op):
        facts, auth = assessment.facts, assessment.stamp
        # Guard locks serialize same-scope creation; unique constraints also protect direct DML.
        occupied = (
            await self.session.execute(
                self.query(DATE).where(
                    DATE.c.class_instance_id == auth.scope.class_instance_id,
                    DATE.c.day_date.in_(facts.columns),
                )
            )
        ).first()
        if occupied:
            raise IdentityRejected("semester_week_conflict")
        result = await self.session.execute(
            insert(ROOT).values(
                tenant_id=self.tenant_id,
                class_instance_id=auth.scope.class_instance_id,
                semester_id=auth.scope.semester_id,
                anchor_monday=auth.scope.anchor_monday,
                contract="shared_weekly_v1",
                created_by=auth.user_id,
                revision=0,
            )
        )
        plan_id = result.inserted_primary_key[0]
        await self.session.execute(
            insert(DATE),
            [
                {
                    "tenant_id": self.tenant_id,
                    "plan_id": plan_id,
                    "class_instance_id": auth.scope.class_instance_id,
                    "day_date": day,
                }
                for day in facts.columns
            ],
        )
        root = await self.root(plan_id)
        return await self.publish(root, assessment, draft, op)

    async def publish(self, root, assessment, draft, op):
        auth = assessment.stamp
        body, facts = draft.serialize(), facts_json(assessment.facts)
        number = root["revision"] + 1
        result = await self.session.execute(
            insert(VERSION).values(
                tenant_id=self.tenant_id,
                plan_id=root["id"],
                version=number,
                predecessor=root["current_version"],
                editor_id=auth.user_id,
                assignment_id=auth.assignments[0][0],
                assignment_revision=auth.assignments[0][1],
                membership_revision=auth.membership_revision,
                assignments_json=canonical(auth.assignments),
                operation_id=op,
                session_hash=auth.session_hash,
                body_json=body,
                facts_json=facts,
                payload_sha256=payload_hash(body, facts),
            )
        )
        stamp = PlanStamp(root["id"], result.inserted_primary_key[0], number)
        await self.audit(
            stamp,
            assessment,
            op,
            "create" if number == 1 else "save",
            "created" if number == 1 else "saved",
        )
        result = await self.session.execute(
            update(ROOT)
            .where(
                ROOT.c.tenant_id == self.tenant_id,
                ROOT.c.id == root["id"],
                ROOT.c.revision == root["revision"],
                ROOT.c.current_version.is_(None)
                if root["current_version"] is None
                else ROOT.c.current_version == root["current_version"],
            )
            .values(
                current_version=stamp.current_version,
                revision=number,
                updated_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        if result.rowcount != 1:
            raise IdentityRejected("plan_conflict")
        return stamp

    async def load(self, root, assessment):
        row = (
            (
                await self.session.execute(
                    self.query(VERSION).where(
                        VERSION.c.plan_id == root["id"],
                        VERSION.c.id == root["current_version"],
                        VERSION.c.version == root["revision"],
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if (
            row is None
            or payload_hash(row["body_json"], row["facts_json"])
            != row["payload_sha256"]
        ):
            raise IdentityRejected("content_invalid")
        return LoadedWeek(
            EditStamp(self.stamp(root), assessment.stamp),
            WeeklyThemeDraft.parse(row["body_json"]),
            parse_facts(row["facts_json"]),
        )
