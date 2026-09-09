"""Tenant-filtered identity persistence; called only inside the application lock scope."""

from dataclasses import asdict
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.academic_identity import TABLES
from app.core.models.user import User
from app.service.academic_identity.contracts import (
    AcademicYearInput,
    AssignmentInput,
    ClassInput,
    ClassSemesterInput,
    IdentityRejected,
    IdentityStamp,
    SemesterInput,
)


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class IdentityRepository:
    def __init__(self, session: AsyncSession, tenant_id: int) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def row(
        self, name: str, *, lock: bool = False, **identity: Any
    ) -> RowMapping | None:
        table = TABLES[name]
        stmt = select(table).where(table.c.tenant_id == self.tenant_id)
        for key, value in identity.items():
            stmt = stmt.where(table.c[key] == value)
        if lock:
            stmt = stmt.with_for_update()
        return (await self.session.execute(stmt)).mappings().one_or_none()

    async def require(self, name: str, **identity: Any) -> RowMapping:
        row = await self.row(name, **identity)
        if row is None:
            raise IdentityRejected("scope_denied")
        return row

    async def add(self, name: str, **values: Any) -> IdentityStamp:
        result = await self.session.execute(
            insert(TABLES[name]).values(tenant_id=self.tenant_id, **values)
        )
        return IdentityStamp(result.inserted_primary_key[0], 1)

    async def audit(
        self, actor_id: int, target_id: int, action: str, session_hash: str
    ) -> None:
        await self.add(
            "identity_audit",
            actor_id=actor_id,
            target_id=target_id,
            action="identity_manage",
            operation_kind=action,
            outcome="success",
            reason="authorized",
            operation_id=str(uuid4()),
            session_hash=session_hash,
        )

    async def manager(self, user_id: int) -> None:
        row = await self.row("tenant_identity_manager", user_id=user_id)
        if row is None or not row["is_active"]:
            raise IdentityRejected("identity_manager_required")

    async def lock_configuration(self) -> None:
        # The guard is provisioned by the controlled qualification job.
        await self.require("tenant_identity_guard", lock=True)

    async def reject_overlap(self, name: str, start: date, end: date) -> None:
        table = TABLES[name]
        hit = (
            await self.session.execute(
                select(table.c.id)
                .where(
                    table.c.tenant_id == self.tenant_id,
                    table.c.start_date <= end,
                    table.c.end_date >= start,
                )
                .with_for_update()
            )
        ).first()
        if hit:
            raise IdentityRejected("period_overlap")

    async def create_year(self, command: AcademicYearInput) -> IdentityStamp:
        await self.reject_overlap("academic_year", command.start_date, command.end_date)
        return await self.add("academic_year", **asdict(command))

    async def create_semester(self, command: SemesterInput) -> IdentityStamp:
        year = await self.require("academic_year", id=command.academic_year_id)
        if (
            not year["start_date"]
            <= command.start_date
            <= command.end_date
            <= year["end_date"]
        ):
            raise IdentityRejected("period_invalid")
        await self.reject_overlap("semester", command.start_date, command.end_date)
        return await self.add("semester", **asdict(command))

    async def create_class(self, command: ClassInput) -> IdentityStamp:
        await self.require(
            "semester",
            id=command.semester_id,
            academic_year_id=command.academic_year_id,
        )
        result = await self.add(
            "class_instance",
            academic_year_id=command.academic_year_id,
            display_name=command.display_name,
            grade=command.grade,
        )
        await self.add(
            "class_semester",
            class_instance_id=result.id,
            semester_id=command.semester_id,
            academic_year_id=command.academic_year_id,
        )
        return result

    async def bind_class(self, command: ClassSemesterInput) -> IdentityStamp:
        cls = await self.require("class_instance", id=command.class_instance_id)
        await self.require(
            "semester", id=command.semester_id, academic_year_id=cls["academic_year_id"]
        )
        await self.add(
            "class_semester",
            class_instance_id=cls["id"],
            semester_id=command.semester_id,
            academic_year_id=cls["academic_year_id"],
        )
        return IdentityStamp(cls["id"], cls["revision"])

    async def grant(self, command: AssignmentInput) -> IdentityStamp:
        await self.require(
            "class_semester",
            lock=True,
            class_instance_id=command.class_instance_id,
            semester_id=command.semester_id,
        )
        semester = await self.require("semester", id=command.semester_id)
        if (
            not semester["start_date"]
            <= command.scope_start_date
            <= command.scope_end_date
            <= semester["end_date"]
        ):
            raise IdentityRejected("period_invalid")
        user = (
            await self.session.execute(
                select(User).where(
                    User.tenant_id == self.tenant_id, User.id == command.user_id
                )
            )
        ).scalar_one_or_none()
        if (
            user is None
            or not user.is_active
            or user.role.value not in ("teacher", "teaching_admin")
        ):
            raise IdentityRejected("scope_denied")
        table = TABLES["teacher_class_assignment"]
        overlap = (
            await self.session.execute(
                select(table.c.id)
                .where(
                    table.c.tenant_id == self.tenant_id,
                    table.c.user_id == command.user_id,
                    table.c.class_instance_id == command.class_instance_id,
                    table.c.semester_id == command.semester_id,
                    table.c.revoked_at.is_(None),
                    table.c.scope_start_date <= command.scope_end_date,
                    table.c.scope_end_date >= command.scope_start_date,
                )
                .order_by(table.c.id)
                .with_for_update()
            )
        ).first()
        if overlap:
            raise IdentityRejected("assignment_overlap")
        values = asdict(command)
        values["valid_from"] = command.valid_from.replace(tzinfo=None)
        values["valid_until"] = command.valid_until.replace(tzinfo=None)
        result = await self.add("teacher_class_assignment", **values)
        await self.bump_membership(command.class_instance_id, command.semester_id)
        return result

    async def bump_membership(self, class_id: int, semester_id: int) -> None:
        table = TABLES["class_semester"]
        await self.session.execute(
            update(table)
            .where(
                table.c.tenant_id == self.tenant_id,
                table.c.class_instance_id == class_id,
                table.c.semester_id == semester_id,
            )
            .values(
                membership_revision=table.c.membership_revision + 1,
                revision=table.c.revision + 1,
                updated_at=utcnow(),
            )
        )

    async def revoke(self, assignment_id: int, expected_revision: int) -> IdentityStamp:
        before = await self.require("teacher_class_assignment", id=assignment_id)
        await self.require(
            "class_semester",
            lock=True,
            class_instance_id=before["class_instance_id"],
            semester_id=before["semester_id"],
        )
        row = await self.require(
            "teacher_class_assignment", lock=True, id=assignment_id
        )
        table = TABLES["teacher_class_assignment"]
        result = await self.session.execute(
            update(table)
            .where(
                table.c.tenant_id == self.tenant_id,
                table.c.id == assignment_id,
                table.c.revision == expected_revision,
                table.c.revoked_at.is_(None),
            )
            .values(
                revoked_at=utcnow(), revision=table.c.revision + 1, updated_at=utcnow()
            )
        )
        if result.rowcount != 1:
            raise IdentityRejected("membership_stale")
        await self.bump_membership(row["class_instance_id"], row["semester_id"])
        return IdentityStamp(assignment_id, expected_revision + 1)
