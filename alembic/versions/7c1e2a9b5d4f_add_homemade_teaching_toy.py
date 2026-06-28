"""add homemade teaching toy table

Revision ID: 7c1e2a9b5d4f
Revises: 2f7a9c1d4e8b
Create Date: 2026-06-28 13:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c1e2a9b5d4f"
down_revision: Union[str, Sequence[str], None] = "2f7a9c1d4e8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """Upgrade schema."""
    if _has_table("homemade_teaching_toy"):
        return

    op.create_table(
        "homemade_teaching_toy",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("grade", sa.String(length=16), nullable=False),
        sa.Column("class_name", sa.String(length=32), nullable=False),
        sa.Column("teacher_name", sa.String(length=64), nullable=False),
        sa.Column("toy_name", sa.String(length=128), nullable=False),
        sa.Column("materials", sa.Text(), nullable=False),
        sa.Column("play_methods", sa.Text(), nullable=False),
        sa.Column("ai_raw_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_homemade_teaching_tenant_user",
        "homemade_teaching_toy",
        ["tenant_id", "user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    if _has_table("homemade_teaching_toy"):
        op.drop_index("ix_homemade_teaching_tenant_user", table_name="homemade_teaching_toy")
        op.drop_table("homemade_teaching_toy")
