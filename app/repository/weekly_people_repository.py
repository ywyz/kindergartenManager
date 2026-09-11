"""Tenant-bound persistence for weekly people defaults and its ledger."""

import json
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from app.core.models.weekly_people import TABLES
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.people_contracts import (
    People,
    PeopleDefaults,
    PeopleOperationStamp,
)

DEFAULTS = TABLES["weekly_person_defaults"]
AUDIT = TABLES["weekly_person_defaults_audit"]


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _people_json(people: People) -> str:
    return people.serialize()


def _people_hash(people: People) -> str:
    return sha256(_people_json(people).encode("utf-8")).hexdigest()


def _row_people(row) -> People:
    try:
        teachers = json.loads(row["teacher_names_json"])
        # The column stores the teacher list separately from the caregiver so
        # the row remains aligned with the migration proposal.  Parse through
        # the closed DTO before returning any value to the caller.
        if type(teachers) is not list:
            raise ValueError
        return People(tuple(teachers), row["caregiver_name"])
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        raise IdentityRejected("content_invalid") from None


class WeeklyPeopleRepository:
    """Repository used only inside an ``IdentityApplication`` transaction."""

    def __init__(self, session, tenant_id: int):
        self.session = session
        self.tenant_id = tenant_id

    def _query(self):
        return select(DEFAULTS).where(DEFAULTS.c.tenant_id == self.tenant_id)

    async def get(self, user_id: int, class_instance_id: int, *, lock=False):
        query = self._query().where(
            DEFAULTS.c.user_id == user_id,
            DEFAULTS.c.class_instance_id == class_instance_id,
        )
        if lock:
            query = query.with_for_update()
        row = (await self.session.execute(query)).mappings().one_or_none()
        if row is None:
            return None
        revision = row["revision"]
        if type(revision) is not int or revision < 1:
            raise IdentityRejected("content_invalid")
        return PeopleDefaults(revision, _row_people(row))

    async def operation(self, operation_id: str):
        return (
            (
                await self.session.execute(
                    select(AUDIT).where(
                        AUDIT.c.tenant_id == self.tenant_id,
                        AUDIT.c.operation_id == operation_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

    async def require_new_operation(self, operation_id: str) -> None:
        if await self.operation(operation_id) is not None:
            raise IdentityRejected("operation_replayed")

    async def _audit(
        self,
        *,
        actor_id: int,
        class_instance_id: int,
        revision: int,
        people_hash: str,
        operation_id: str,
        session_hash: str,
        outcome: str,
    ) -> None:
        await self.session.execute(
            insert(AUDIT).values(
                tenant_id=self.tenant_id,
                actor_id=actor_id,
                class_instance_id=class_instance_id,
                revision=revision,
                people_hash=people_hash,
                operation_id=operation_id,
                session_hash=session_hash,
                action="save",
                outcome=outcome,
                reason="authorized",
            )
        )

    async def save(
        self,
        *,
        user_id: int,
        class_instance_id: int,
        expected_revision: int,
        people: People,
        operation_id: str,
        session_hash: str,
    ) -> PeopleDefaults:
        """Apply one explicit CAS and record its operation in the same tx."""

        await self.require_new_operation(operation_id)
        current = await self.get(user_id, class_instance_id, lock=True)
        if expected_revision == 0:
            if current is not None:
                raise IdentityRejected("defaults_conflict")
            revision = 1
            try:
                await self.session.execute(
                    insert(DEFAULTS).values(
                        tenant_id=self.tenant_id,
                        user_id=user_id,
                        class_instance_id=class_instance_id,
                        teacher_names_json=json.dumps(
                            list(people.teachers),
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        caregiver_name=people.caregiver,
                        revision=revision,
                        created_at=utcnow(),
                        updated_at=utcnow(),
                    )
                )
            except IntegrityError:
                raise IdentityRejected("defaults_conflict") from None
            result = PeopleDefaults(revision, people)
            await self._audit(
                actor_id=user_id,
                class_instance_id=class_instance_id,
                revision=revision,
                people_hash=_people_hash(people),
                operation_id=operation_id,
                session_hash=session_hash,
                outcome="created",
            )
            return result

        if current is None or current.revision != expected_revision:
            raise IdentityRejected("defaults_conflict")

        if current.people == people:
            revision = current.revision
            outcome = "unchanged"
        else:
            revision = current.revision + 1
            result = await self.session.execute(
                update(DEFAULTS)
                .where(
                    DEFAULTS.c.tenant_id == self.tenant_id,
                    DEFAULTS.c.user_id == user_id,
                    DEFAULTS.c.class_instance_id == class_instance_id,
                    DEFAULTS.c.revision == expected_revision,
                )
                .values(
                    teacher_names_json=json.dumps(
                        list(people.teachers),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    caregiver_name=people.caregiver,
                    revision=revision,
                    updated_at=utcnow(),
                )
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                raise IdentityRejected("defaults_conflict")
            outcome = "updated"

        await self._audit(
            actor_id=user_id,
            class_instance_id=class_instance_id,
            revision=revision,
            people_hash=_people_hash(
                people if outcome == "updated" else current.people
            ),
            operation_id=operation_id,
            session_hash=session_hash,
            outcome=outcome,
        )
        return PeopleDefaults(
            revision, people if outcome == "updated" else current.people
        )

    async def reconcile(
        self,
        *,
        actor_id: int,
        class_instance_id: int,
        operation_id: str,
        session_hash: str,
    ) -> PeopleOperationStamp | None:
        """Return the immutable audit result; never read current defaults/retry."""

        row = await self.operation(operation_id)
        if row is None:
            return None
        if (
            row["actor_id"],
            row["class_instance_id"],
            row["session_hash"],
        ) != (actor_id, class_instance_id, session_hash):
            raise IdentityRejected("scope_denied")
        try:
            return PeopleOperationStamp(
                row["revision"], row["people_hash"], row["outcome"]
            )
        except KeyError:
            raise IdentityRejected("content_invalid") from None


def session_hash(session_id) -> str:
    return sha256(str(session_id).encode()).hexdigest()


__all__ = ["AUDIT", "DEFAULTS", "WeeklyPeopleRepository"]
