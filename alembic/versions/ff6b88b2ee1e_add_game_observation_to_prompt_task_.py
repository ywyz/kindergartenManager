"""add_game_observation_to_prompt_task_type_enum

Revision ID: ff6b88b2ee1e
Revises: 54c20d37a461
Create Date: 2026-06-09 22:51:40.436937

变更说明：
将 prompt_template.task_type 枚举从 7 个值扩展为 8 个值，增加 'game_observation'。
MySQL 不支持通过 autogenerate 检测 Enum 变更，须手动 ALTER TABLE。
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'ff6b88b2ee1e'
down_revision: Union[str, Sequence[str], None] = '54c20d37a461'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_ENUM = (
    "ENUM('split','adapt','morning_exercise','morning_talk',"
    "'area_game','outdoor_game','daily_reflection','game_observation')"
)
_OLD_ENUM = (
    "ENUM('split','adapt','morning_exercise','morning_talk',"
    "'area_game','outdoor_game','daily_reflection')"
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute(
            f"ALTER TABLE prompt_template MODIFY COLUMN task_type {_NEW_ENUM} NOT NULL"
        )
    # SQLite：ORM create_all 已含新值，无需额外处理


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        # 先删除新类型数据，避免降级时约束报错
        op.execute("DELETE FROM prompt_template WHERE task_type = 'game_observation'")
        op.execute(
            f"ALTER TABLE prompt_template MODIFY COLUMN task_type {_OLD_ENUM} NOT NULL"
        )
