"""Add immutable content-free shared export authorization audit; retain old rows."""

import sqlalchemy as sa

from alembic import op

revision = "d375e9012abc"
down_revision = "c264d8fa1037"
branch_labels = None
depends_on = None
NAME = "shared_weekly_export_audit"


def upgrade():
    op.create_table(
        NAME,
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        *[
            sa.Column(
                name,
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                nullable=False,
            )
            for name in (
                "tenant_id",
                "actor_id",
                "class_instance_id",
                "semester_id",
                "plan_id",
                "version_id",
                "revision",
                "membership_revision",
            )
        ],
        sa.Column("assignments_json", sa.Text(), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False, unique=True),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("template_sha256", sa.String(64), nullable=False),
        sa.Column("binding_version", sa.String(128), nullable=False),
        sa.Column("body_sha256", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["user.tenant_id", "user.id"]
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "plan_id", "version_id"],
            [
                "shared_weekly_version.tenant_id",
                "shared_weekly_version.plan_id",
                "shared_weekly_version.id",
            ],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "plan_id", "class_instance_id"],
            [
                "shared_weekly_plan.tenant_id",
                "shared_weekly_plan.id",
                "shared_weekly_plan.class_instance_id",
            ],
        ),
        sa.CheckConstraint(
            "action = 'export' AND outcome = 'authorized' AND reason = 'authorized'",
            name="ck_swea_action",
        ),
        sa.CheckConstraint(
            "revision > 0 AND membership_revision > 0", name="ck_swea_revisions"
        ),
        sa.CheckConstraint(
            "length(session_hash) = 64 AND length(template_sha256) = 64 AND length(body_sha256) = 64 AND length(binding_version) > 0",
            name="ck_swea_hashes",
        ),
        mysql_engine="InnoDB",
    )
    for action in ("UPDATE", "DELETE"):
        name = f"{NAME}_{action.lower()}_deny"
        if op.get_bind().dialect.name == "sqlite":
            op.execute(
                f"CREATE TRIGGER {name} BEFORE {action} ON {NAME} BEGIN SELECT RAISE(ABORT, 'shared_immutable'); END"
            )
        else:
            op.execute(
                f"CREATE TRIGGER {name} BEFORE {action} ON {NAME} FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='shared_immutable'"
            )


def downgrade():
    table = sa.table(NAME, sa.column("id"))
    if op.get_bind().execute(sa.select(table.c.id).limit(1)).first():
        raise RuntimeError("shared_export_audit_nonempty_downgrade_denied")
    op.drop_table(NAME)
