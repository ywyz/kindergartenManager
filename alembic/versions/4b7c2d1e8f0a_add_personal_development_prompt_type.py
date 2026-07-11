"""add personal_development to prompt_task_type enum

Revision ID: 4b7c2d1e8f0a
Revises: 3a8d9b2c1e0f
Create Date: 2026-07-11 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '4b7c2d1e8f0a'
down_revision: Union[str, Sequence[str], None] = '3a8d9b2c1e0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('prompt_template', schema=None) as batch_op:
        batch_op.alter_column(
            'task_type',
            type_=sa.Enum(
                "split",
                "adapt",
                "morning_exercise",
                "morning_talk",
                "area_game",
                "outdoor_game",
                "daily_reflection",
                "game_observation",
                "one_on_one_listening",
                "homemade_teaching",
                "course_review_activity",
                "personal_development",
                name="prompt_task_type",
            ),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('prompt_template', schema=None) as batch_op:
        batch_op.alter_column(
            'task_type',
            type_=sa.Enum(
                "split",
                "adapt",
                "morning_exercise",
                "morning_talk",
                "area_game",
                "outdoor_game",
                "daily_reflection",
                "game_observation",
                "one_on_one_listening",
                "homemade_teaching",
                "course_review_activity",
                name="prompt_task_type",
            ),
            nullable=False,
        )