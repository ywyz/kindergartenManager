"""add teacher_name to class_config

Revision ID: 2f7a9c1d4e8b
Revises: 9ec29bdc3822
Create Date: 2026-06-28 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f7a9c1d4e8b"
down_revision: Union[str, Sequence[str], None] = "9ec29bdc3822"
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
    if not _has_column("class_config", "teacher_name"):
        with op.batch_alter_table("class_config") as batch_op:
            batch_op.add_column(sa.Column("teacher_name", sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    if _has_column("class_config", "teacher_name"):
        with op.batch_alter_table("class_config") as batch_op:
            batch_op.drop_column("teacher_name")
