"""add homemade teaching prompt task

Revision ID: c8b6d4e2a931
Revises: 7c1e2a9b5d4f
Create Date: 2026-06-28 13:50:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c8b6d4e2a931"
down_revision: Union[str, Sequence[str], None] = "7c1e2a9b5d4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_ENUM = (
    "ENUM('split','adapt','morning_exercise','morning_talk',"
    "'area_game','outdoor_game','daily_reflection','game_observation',"
    "'one_on_one_listening','homemade_teaching')"
)
_OLD_ENUM = (
    "ENUM('split','adapt','morning_exercise','morning_talk',"
    "'area_game','outdoor_game','daily_reflection','game_observation',"
    "'one_on_one_listening')"
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute(
            f"ALTER TABLE prompt_template MODIFY COLUMN task_type {_NEW_ENUM} NOT NULL"
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute("DELETE FROM prompt_template WHERE task_type = 'homemade_teaching'")
        op.execute(
            f"ALTER TABLE prompt_template MODIFY COLUMN task_type {_OLD_ENUM} NOT NULL"
        )
