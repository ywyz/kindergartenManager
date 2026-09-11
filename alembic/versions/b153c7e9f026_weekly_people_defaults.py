"""Persist explicit class-scoped people defaults and their operation ledger.

Revision ID: b153c7e9f026
Revises: a042b6d8e915
"""

import sqlalchemy as sa

from alembic import op

revision = "b153c7e9f026"
down_revision = "a042b6d8e915"
branch_labels = None
depends_on = None


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

    defaults = sa.Table(
        "weekly_person_defaults",
        metadata,
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
        mysql_engine="InnoDB",
    )
    audit = sa.Table(
        "weekly_person_defaults_audit",
        metadata,
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
        mysql_engine="InnoDB",
    )
    return defaults, audit


def upgrade():
    bind = op.get_bind()
    metadata = sa.MetaData()
    for name in ("user", "class_instance"):
        sa.Table(name, metadata, autoload_with=bind)
    defaults, audit = _tables(metadata)
    defaults.create(bind)
    audit.create(bind)

    for action in ("UPDATE", "DELETE"):
        name = f"weekly_people_audit_no_{action.lower()}"
        if bind.dialect.name == "sqlite":
            op.execute(
                f"CREATE TRIGGER {name} BEFORE {action} ON weekly_person_defaults_audit "
                "BEGIN SELECT RAISE(ABORT, 'weekly_people_audit_immutable'); END"
            )
        else:
            op.execute(
                f"CREATE TRIGGER {name} BEFORE {action} ON weekly_person_defaults_audit "
                "FOR EACH ROW SIGNAL SQLSTATE '45000' "
                "SET MESSAGE_TEXT='weekly_people_audit_immutable'"
            )


def downgrade():
    bind = op.get_bind()
    for name in ("weekly_person_defaults_audit", "weekly_person_defaults"):
        if bind.execute(sa.text(f"SELECT 1 FROM {name} LIMIT 1")).first():
            raise RuntimeError("weekly_people_nonempty_downgrade_denied")
    op.execute("DROP TRIGGER weekly_people_audit_no_update")
    op.execute("DROP TRIGGER weekly_people_audit_no_delete")
    op.drop_table("weekly_person_defaults_audit")
    op.drop_table("weekly_person_defaults")
