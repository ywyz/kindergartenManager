"""Tenant scoped shared-root persistence, called inside the identity transaction."""

import json
from datetime import UTC, date, datetime

from sqlalchemy import insert, select, update

from app.core.models.shared_weekly import TABLES
from app.core.models.source_mapping import TABLES as MAPPING_TABLES
from app.core.models.weekly_sources import TABLES as SOURCE_TABLES
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.authoring_contracts import (
    WeeklyAuthoringDraft,
    reference_for,
)
from app.service.shared_weekly.body_contracts import (
    SourceSnapshot,
    TargetPath,
    WeeklyCollaborationDraft,
    parse_body,
)
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
SOURCE = SOURCE_TABLES["shared_weekly_source"]
MAPPING_EVENT = MAPPING_TABLES["identity_mapping_event"]


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
        if type(draft) not in (
            WeeklyThemeDraft,
            WeeklyCollaborationDraft,
            WeeklyAuthoringDraft,
        ):
            raise IdentityRejected("input_invalid")
        if type(draft) is WeeklyAuthoringDraft and draft.archive:
            if root["current_version"] is None:
                raise IdentityRejected("source_unavailable")
            previous = (await self.load(root, assessment)).body
            prior_sources = (
                previous.all_sources
                if type(previous) is WeeklyAuthoringDraft
                else previous.sources
                if type(previous) is WeeklyCollaborationDraft
                else ()
            )
            allowed = {reference_for(source) for source in prior_sources}
            if any(reference_for(source) not in allowed for source in draft.archive):
                raise IdentityRejected("source_unavailable")
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
        version_id = result.inserted_primary_key[0]
        if (
            type(draft) in (WeeklyCollaborationDraft, WeeklyAuthoringDraft)
            and draft.sources
        ):
            for source in draft.sources:
                event = (
                    (
                        await self.session.execute(
                            select(MAPPING_EVENT).where(
                                MAPPING_EVENT.c.tenant_id == self.tenant_id,
                                MAPPING_EVENT.c.id == source.mapping_id,
                                MAPPING_EVENT.c.revision == source.mapping_revision,
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if (
                    event is None
                    or (
                        event["daily_plan_id"],
                        event["source_user_id"],
                        event["source_date"],
                    )
                    != (
                        source.source_id,
                        source.user_id,
                        source.day,
                    )
                    or (
                        event["class_instance_id"],
                        event["semester_id"],
                    )
                    != (
                        root["class_instance_id"],
                        root["semester_id"],
                    )
                    or source.revision < event["source_revision"]
                ):
                    raise IdentityRejected("source_unavailable")
            await self.session.execute(
                insert(SOURCE),
                [
                    {
                        "tenant_id": self.tenant_id,
                        "version_id": version_id,
                        "source_id": source.source_id,
                        "source_user_id": source.user_id,
                        "source_date": source.day,
                        "source_revision": source.revision,
                        "mapping_id": source.mapping_id,
                        "mapping_revision": source.mapping_revision,
                        "source_field": source.source_field,
                        "target_path": source.target.serialize(),
                        "imported_value": source.imported_value,
                        "imported_hash": source.imported_hash,
                        "adopted_hash": source.adopted_hash,
                        "provenance": source.provenance,
                    }
                    for source in draft.sources
                ],
            )
        stamp = PlanStamp(root["id"], version_id, number)
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
        body = parse_body(row["body_json"])
        if type(body) in (WeeklyCollaborationDraft, WeeklyAuthoringDraft):
            source_rows = tuple(
                (
                    await self.session.execute(
                        select(SOURCE)
                        .where(
                            SOURCE.c.tenant_id == self.tenant_id,
                            SOURCE.c.version_id == row["id"],
                        )
                        .order_by(SOURCE.c.id)
                    )
                ).mappings()
            )
            children = tuple(_source_from_row(item) for item in source_rows)
            # The body is part of the immutable payload and the child rows are
            # the database provenance record.  A mismatch means corruption or
            # an attempted forged source, so fail closed on load.
            if tuple(sorted(children, key=_source_key)) != tuple(
                sorted(body.sources, key=_source_key)
            ):
                raise IdentityRejected("content_invalid")
        elif await _has_source_children(
            self.session, SOURCE, self.tenant_id, row["id"]
        ):
            raise IdentityRejected("content_invalid")
        return LoadedWeek(
            EditStamp(self.stamp(root), assessment.stamp),
            body,
            parse_facts(row["facts_json"]),
        )


def _source_key(source: SourceSnapshot):
    return (
        source.target.day,
        source.target.field,
        source.source_id,
        source.user_id,
        source.day,
        source.revision,
        source.mapping_id,
        source.mapping_revision,
    )


def _source_from_row(row) -> SourceSnapshot:
    try:
        target_value = json.loads(row["target_path"])
        if type(target_value) is not dict or set(target_value) != {"day", "field"}:
            raise ValueError
        target = TargetPath(
            date.fromisoformat(target_value["day"]), target_value["field"]
        )
        return SourceSnapshot(
            source_id=row["source_id"],
            source_user_id=row["source_user_id"],
            source_date=row["source_date"],
            source_revision=row["source_revision"],
            mapping_id=row["mapping_id"],
            mapping_revision=row["mapping_revision"],
            source_field=row["source_field"],
            target_path=target,
            imported_value=row["imported_value"],
            imported_hash=row["imported_hash"],
            adopted_hash=row["adopted_hash"],
            provenance=row["provenance"],
        )
    except (IdentityRejected, KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise IdentityRejected("content_invalid") from None


async def _has_source_children(session, table, tenant_id, version_id) -> bool:
    return (
        await session.execute(
            select(table.c.id)
            .where(table.c.tenant_id == tenant_id, table.c.version_id == version_id)
            .limit(1)
        )
    ).first() is not None
