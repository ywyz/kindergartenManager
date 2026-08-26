"""add append-only agent write evidence

Revision ID: e5f7a9c2d4b6
Revises: c1a8e4f6b2d9
Create Date: 2026-08-26 16:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = "e5f7a9c2d4b6"
down_revision: Union[str, Sequence[str], None] = "c1a8e4f6b2d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_EVIDENCE_TABLES = (
    "daily_plan_operation_version",
    "agent_write_audit",
)


def _create_immutability_triggers(table_name: str) -> None:
    dialect_name = op.get_bind().dialect.name
    if dialect_name == "sqlite":
        for action in ("UPDATE", "DELETE"):
            trigger_name = f"trg_{table_name}_no_{action.casefold()}"
            op.execute(
                f"""
                CREATE TRIGGER {trigger_name}
                BEFORE {action} ON {table_name}
                FOR EACH ROW
                BEGIN
                    SELECT RAISE(ABORT, '{table_name} is append-only');
                END
                """
            )
        return
    if dialect_name == "mysql":
        for action in ("UPDATE", "DELETE"):
            trigger_name = f"trg_{table_name}_no_{action.casefold()}"
            op.execute(
                f"""
                CREATE TRIGGER {trigger_name}
                BEFORE {action} ON {table_name}
                FOR EACH ROW
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = '{table_name} is append-only'
                """
            )
        return
    raise RuntimeError("unsupported database dialect for agent write evidence")


def upgrade() -> None:
    """Create the two append-only evidence tables and database guards."""
    op.create_table(
        "daily_plan_operation_version",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("daily_plan_id", sa.BigInteger(), nullable=False),
        sa.Column("confirmation_id", sa.String(length=36), nullable=False),
        sa.Column("patch_id", sa.String(length=36), nullable=False),
        sa.Column("patch_sha256", sa.String(length=64), nullable=False),
        sa.Column("operation_id", sa.String(length=36), nullable=False),
        sa.Column("turn_id", sa.String(length=36), nullable=False),
        sa.Column("before_revision", sa.Integer(), nullable=False),
        sa.Column("field_paths_json", sa.Text(), nullable=False),
        sa.Column(
            "snapshot_json",
            sa.Text().with_variant(mysql.LONGTEXT(), "mysql"),
            nullable=False,
        ),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "before_revision >= 1",
            name="ck_daily_plan_operation_version_revision_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "agent_write_audit",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("confirmation_id", sa.String(length=36), nullable=False),
        sa.Column("nonce_sha256", sa.String(length=64), nullable=False),
        sa.Column("session_sha256", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("daily_plan_id", sa.BigInteger(), nullable=False),
        sa.Column("patch_id", sa.String(length=36), nullable=False),
        sa.Column("patch_sha256", sa.String(length=64), nullable=False),
        sa.Column("operation_id", sa.String(length=36), nullable=False),
        sa.Column("turn_id", sa.String(length=36), nullable=False),
        sa.Column("field_paths_json", sa.Text(), nullable=False),
        sa.Column("before_version_id", sa.BigInteger(), nullable=False),
        sa.Column("before_revision", sa.Integer(), nullable=False),
        sa.Column("after_revision", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "before_revision >= 1",
            name="ck_agent_write_audit_before_revision_positive",
        ),
        sa.CheckConstraint(
            "after_revision = before_revision + 1",
            name="ck_agent_write_audit_revision_step",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "confirmation_id",
            name="uq_agent_write_audit_confirmation_id",
        ),
        sa.UniqueConstraint(
            "nonce_sha256",
            name="uq_agent_write_audit_nonce_sha256",
        ),
    )

    for table_name in _EVIDENCE_TABLES:
        _create_immutability_triggers(table_name)


def downgrade() -> None:
    """Remove append-only guards before dropping their evidence tables."""
    for table_name in reversed(_EVIDENCE_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_delete")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_update")
        op.drop_table(table_name)
