"""Explicit daily identity pointer and retained immutable mapping events."""

import sqlalchemy as sa

from app.core.database import Base


def _tables(metadata):
    def num(n):
        return sa.Column(n, sa.BigInteger(), nullable=False)

    def ident():
        return sa.Column(
            "id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True
        )

    def target():
        return sa.ForeignKeyConstraint(
            ["tenant_id", "class_instance_id", "semester_id"],
            [
                "class_semester.tenant_id",
                "class_semester.class_instance_id",
                "class_semester.semester_id",
            ],
            ondelete="RESTRICT",
        )

    event = sa.Table(
        "identity_mapping_event",
        metadata,
        ident(),
        num("tenant_id"),
        num("daily_plan_id"),
        num("source_user_id"),
        sa.Column("source_date", sa.Date(), nullable=False),
        num("source_revision"),
        num("class_instance_id"),
        num("semester_id"),
        num("revision"),
        sa.Column("previous_id", sa.BigInteger()),
        num("actor_id"),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column("binding_hash", sa.String(64), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "daily_plan_id", "revision"),
        target(),
        sa.CheckConstraint(
            "revision >= 1 AND source_revision >= 1", name="ck_mapping_event_revision"
        ),
        mysql_engine="InnoDB",
    )
    pointer = sa.Table(
        "daily_plan_identity",
        metadata,
        num("tenant_id"),
        num("daily_plan_id"),
        num("source_user_id"),
        sa.Column("source_date", sa.Date(), nullable=False),
        num("class_instance_id"),
        num("semester_id"),
        num("mapping_id"),
        num("revision"),
        sa.PrimaryKeyConstraint("tenant_id", "daily_plan_id"),
        target(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "daily_plan_id", "source_user_id"],
            ["daily_plan.tenant_id", "daily_plan.id", "daily_plan.user_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "mapping_id"],
            ["identity_mapping_event.tenant_id", "identity_mapping_event.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_daily_identity_revision"),
        mysql_engine="InnoDB",
    )
    return event, pointer


TABLES = {t.name: t for t in _tables(Base.metadata)}
