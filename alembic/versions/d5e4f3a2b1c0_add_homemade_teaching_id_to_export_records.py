"""add homemade teaching id to export records

Revision ID: d5e4f3a2b1c0
Revises: c8b6d4e2a931
Create Date: 2026-06-28 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d5e4f3a2b1c0"
down_revision: Union[str, Sequence[str], None] = "c8b6d4e2a931"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    if not _has_column("export_records", "homemade_teaching_id"):
        with op.batch_alter_table("export_records") as batch_op:
            batch_op.add_column(sa.Column("homemade_teaching_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    if _has_column("export_records", "homemade_teaching_id"):
        with op.batch_alter_table("export_records") as batch_op:
            batch_op.drop_column("homemade_teaching_id")
