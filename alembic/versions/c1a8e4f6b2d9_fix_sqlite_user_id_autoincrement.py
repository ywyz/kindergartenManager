"""fix SQLite user id autoincrement

Revision ID: c1a8e4f6b2d9
Revises: b7d9e1f3a5c2
Create Date: 2026-08-26 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1a8e4f6b2d9"
down_revision: Union[str, Sequence[str], None] = "b7d9e1f3a5c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Use SQLite's exact INTEGER PRIMARY KEY spelling for generated user IDs."""
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        # MySQL already has the intended BIGINT AUTO_INCREMENT definition.
        return
    if bind.dialect.name != "sqlite":
        raise RuntimeError("unsupported database dialect for user id migration")

    with op.batch_alter_table("user", recreate="always") as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
            autoincrement=True,
        )


def downgrade() -> None:
    """Restore the historical SQLite BIGINT primary-key definition."""
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        return
    if bind.dialect.name != "sqlite":
        raise RuntimeError("unsupported database dialect for user id migration")

    with op.batch_alter_table("user", recreate="always") as batch_op:
        batch_op.alter_column(
            "id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
            autoincrement=True,
        )
