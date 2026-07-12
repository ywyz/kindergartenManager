"""drop legacy tables from old version

Revision ID: 2ea4743f8fa7
Revises: a6c4d8e2f9b1
Create Date: 2026-07-11 12:38:10.469846

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '2ea4743f8fa7'
down_revision: Union[str, Sequence[str], None] = 'a6c4d8e2f9b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables_to_drop = ['daily_plans', 'weekly_plans', 'semester_settings', 'prompts', 'ai_call_logs', 'ai_config', 'app_settings']
    for table in tables_to_drop:
        if inspector.has_table(table):
            op.drop_table(table)


def downgrade() -> None:
    """Downgrade schema."""
    pass
