"""add_observation_id_to_export_record

Revision ID: 6553de463329
Revises: ff6b88b2ee1e
Create Date: 2026-06-10 20:07:57.917062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6553de463329'
down_revision: Union[str, Sequence[str], None] = 'ff6b88b2ee1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "export_records",
        sa.Column("observation_id", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("export_records", "observation_id")
