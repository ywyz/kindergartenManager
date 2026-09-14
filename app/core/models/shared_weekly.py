"""Minimal shared theme drafts; canonical body/facts are immutable version bytes."""

import sqlalchemy as sa

from app.core.database import Base


def _tables(metadata):
    def idcol():
        return sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        )

    def num(name, nullable=False):
        return sa.Column(name, sa.BigInteger(), nullable=nullable)

    def fk(local, remote):
        return sa.ForeignKeyConstraint(local, remote, ondelete="RESTRICT")

    def created():
        return sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        )

    def table(name, *cols):
        return sa.Table(name, metadata, *cols, mysql_engine="InnoDB")

    root = table(
        "shared_weekly_plan",
        idcol(),
        num("tenant_id"),
        num("class_instance_id"),
        num("semester_id"),
        sa.Column("anchor_monday", sa.Date(), nullable=False),
        sa.Column("contract", sa.String(32), nullable=False),
        num("created_by"),
        num("current_version", True),
        num("revision"),
        created(),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.CheckConstraint("contract = 'shared_weekly_v1'", name="ck_sw_contract"),
        sa.CheckConstraint("revision >= 0", name="ck_sw_revision"),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "id", "class_instance_id"),
        sa.UniqueConstraint(
            "tenant_id", "class_instance_id", "semester_id", "anchor_monday"
        ),
        fk(
            ["tenant_id", "class_instance_id", "semester_id"],
            [
                "class_semester.tenant_id",
                "class_semester.class_instance_id",
                "class_semester.semester_id",
            ],
        ),
        fk(["tenant_id", "created_by"], ["user.tenant_id", "user.id"]),
    )
    version = table(
        "shared_weekly_version",
        idcol(),
        num("tenant_id"),
        num("plan_id"),
        num("version"),
        num("predecessor", True),
        num("editor_id"),
        num("assignment_id"),
        num("assignment_revision"),
        num("membership_revision"),
        sa.Column("assignments_json", sa.Text(), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False, unique=True),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column("body_json", sa.Text(), nullable=False),
        sa.Column("facts_json", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        created(),
        sa.CheckConstraint(
            "version >= 1 AND assignment_revision >= 1 AND membership_revision >= 1",
            name="ck_swv_positive",
        ),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "plan_id", "id"),
        sa.UniqueConstraint("tenant_id", "plan_id", "version"),
        fk(
            ["tenant_id", "plan_id"],
            ["shared_weekly_plan.tenant_id", "shared_weekly_plan.id"],
        ),
        fk(
            ["tenant_id", "plan_id", "predecessor"],
            [
                "shared_weekly_version.tenant_id",
                "shared_weekly_version.plan_id",
                "shared_weekly_version.id",
            ],
        ),
        fk(["tenant_id", "editor_id"], ["user.tenant_id", "user.id"]),
        fk(
            ["tenant_id", "assignment_id"],
            ["teacher_class_assignment.tenant_id", "teacher_class_assignment.id"],
        ),
    )
    dates = table(
        "shared_weekly_date",
        num("tenant_id"),
        num("plan_id"),
        num("class_instance_id"),
        sa.Column("day_date", sa.Date(), nullable=False),
        created(),
        sa.PrimaryKeyConstraint("tenant_id", "class_instance_id", "day_date"),
        sa.UniqueConstraint("tenant_id", "plan_id", "day_date"),
        fk(
            ["tenant_id", "plan_id", "class_instance_id"],
            [
                "shared_weekly_plan.tenant_id",
                "shared_weekly_plan.id",
                "shared_weekly_plan.class_instance_id",
            ],
        ),
    )
    audit = table(
        "shared_weekly_audit",
        idcol(),
        num("tenant_id"),
        num("actor_id"),
        num("class_instance_id"),
        num("semester_id"),
        num("plan_id"),
        num("version_id"),
        num("revision"),
        num("membership_revision"),
        sa.Column("assignments_json", sa.Text(), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False, unique=True),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(16), nullable=False),
        created(),
        sa.CheckConstraint("action IN ('create','save','read')", name="ck_swa_action"),
        sa.CheckConstraint(
            "outcome IN ('created','saved','existing','unchanged','loaded')",
            name="ck_swa_outcome",
        ),
        sa.CheckConstraint("reason = 'authorized'", name="ck_swa_reason"),
    )
    return root, version, dates, audit


TABLES = {t.name: t for t in _tables(Base.metadata)}
