"""Database tables for per-user, per-class weekly people defaults.

The defaults row is mutable through the application CAS.  Its operation
ledger is append-only and contains no names or other teaching body content.
"""

import sqlalchemy as sa

from app.core.database import Base


def _tables(metadata):
    def ident():
        return sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        )

    def number(name, *, nullable=False):
        return sa.Column(name, sa.BigInteger(), nullable=nullable)

    def created():
        return sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        )

    def updated():
        return sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        )

    def table(name, *columns):
        return sa.Table(name, metadata, *columns, mysql_engine="InnoDB")

    defaults = table(
        "weekly_person_defaults",
        number("tenant_id"),
        number("user_id"),
        number("class_instance_id"),
        sa.Column("teacher_names_json", sa.Text(), nullable=False),
        sa.Column("caregiver_name", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        created(),
        updated(),
        sa.PrimaryKeyConstraint("tenant_id", "user_id", "class_instance_id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["user.tenant_id", "user.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "class_instance_id"],
            ["class_instance.tenant_id", "class_instance.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_weekly_people_revision"),
        sa.Index(
            "ix_weekly_person_defaults_tenant_class",
            "tenant_id",
            "class_instance_id",
        ),
    )

    audit = table(
        "weekly_person_defaults_audit",
        ident(),
        number("tenant_id"),
        number("actor_id"),
        number("class_instance_id"),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("people_hash", sa.String(64), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(16), nullable=False),
        created(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "actor_id"],
            ["user.tenant_id", "user.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "class_instance_id"],
            ["class_instance.tenant_id", "class_instance.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("tenant_id", "operation_id"),
        sa.CheckConstraint("revision >= 1", name="ck_weekly_people_audit_revision"),
        sa.CheckConstraint(
            "length(people_hash) = 64", name="ck_weekly_people_audit_hash"
        ),
        sa.CheckConstraint("action = 'save'", name="ck_weekly_people_audit_action"),
        sa.CheckConstraint(
            "outcome IN ('created','updated','unchanged')",
            name="ck_weekly_people_audit_outcome",
        ),
        sa.CheckConstraint(
            "reason = 'authorized'", name="ck_weekly_people_audit_reason"
        ),
    )
    return defaults, audit


TABLES = {table.name: table for table in _tables(Base.metadata)}

__all__ = ["TABLES"]
