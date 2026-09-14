"""Tenant-scoped, content-free delivery authorization audit (never a file record)."""

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    insert,
    select,
)

from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.root_contracts import canonical

AUDIT = Table(
    "shared_weekly_export_audit",
    MetaData(),
    Column("id", Integer, primary_key=True),
    Column("tenant_id", Integer),
    Column("actor_id", Integer),
    Column("class_instance_id", Integer),
    Column("semester_id", Integer),
    Column("plan_id", Integer),
    Column("version_id", Integer),
    Column("revision", Integer),
    Column("membership_revision", Integer),
    Column("assignments_json", Text),
    Column("operation_id", String(36)),
    Column("session_hash", String(64)),
    Column("action", String(16)),
    Column("outcome", String(16)),
    Column("reason", String(32)),
    Column("template_sha256", String(64)),
    Column("binding_version", String(128)),
    Column("body_sha256", String(64)),
    Column("created_at", DateTime),
)


class WeeklyExportRepository:
    def __init__(self, session, tenant_id):
        self.session = session
        self.tenant_id = tenant_id

    async def operation(self, operation_id):
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

    async def authorize_delivery(
        self, target, assessment, operation_id, binding, body_hash
    ):
        if await self.operation(operation_id) is not None:
            raise IdentityRejected("operation_replayed")
        stamp = assessment.stamp
        await self.session.execute(
            insert(AUDIT).values(
                tenant_id=self.tenant_id,
                actor_id=stamp.user_id,
                class_instance_id=stamp.scope.class_instance_id,
                semester_id=stamp.scope.semester_id,
                plan_id=target.plan_id,
                version_id=target.current_version,
                revision=target.revision,
                membership_revision=stamp.membership_revision,
                assignments_json=canonical(stamp.assignments),
                operation_id=operation_id,
                session_hash=stamp.session_hash,
                action="export",
                outcome="authorized",
                reason="authorized",
                template_sha256=binding.template_sha256,
                binding_version=binding.active_version,
                body_sha256=body_hash,
            )
        )
