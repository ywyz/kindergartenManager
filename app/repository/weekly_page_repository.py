"""Tenant-filtered display choices; grants remain the shared policy's responsibility."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.core.models.academic_identity import TABLES
from app.core.models.user import User
from app.repository.shared_weekly_repository import VERSION


class WeeklyPageRepository:
    def __init__(self, session, tenant_id):
        self.session, self.tenant_id = session, tenant_id

    async def choices(self, user_id):
        assignment = TABLES["teacher_class_assignment"]
        classroom, semester = TABLES["class_instance"], TABLES["semester"]
        now = datetime.now(UTC).replace(tzinfo=None)
        query = (
            select(
                assignment.c.class_instance_id,
                assignment.c.semester_id,
                classroom.c.display_name,
                semester.c.start_date,
                semester.c.end_date,
            )
            .join(
                classroom,
                (classroom.c.tenant_id == assignment.c.tenant_id)
                & (classroom.c.id == assignment.c.class_instance_id),
            )
            .join(
                semester,
                (semester.c.tenant_id == assignment.c.tenant_id)
                & (semester.c.id == assignment.c.semester_id),
            )
            .where(
                assignment.c.tenant_id == self.tenant_id,
                assignment.c.user_id == user_id,
                assignment.c.revoked_at.is_(None),
                assignment.c.valid_from <= now,
                assignment.c.valid_until > now,
            )
            .distinct()
        )
        return tuple((await self.session.execute(query)).mappings())

    async def editor(self, version_id):
        query = (
            select(User.display_name, User.username)
            .join(
                VERSION,
                (VERSION.c.tenant_id == User.tenant_id)
                & (VERSION.c.editor_id == User.id),
            )
            .where(VERSION.c.tenant_id == self.tenant_id, VERSION.c.id == version_id)
        )
        row = (await self.session.execute(query)).one()
        return row.display_name or row.username
