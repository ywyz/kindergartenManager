"""expand prompt_task_type enum — replace generate with 5 activity subtypes

Revision ID: e2a3f1b8c9d0
Revises: bcd07e51527d
Create Date: 2026-05-17 20:30:00.000000

变更说明：
将 task_type 列的 Enum 从 ('split', 'adapt', 'generate') 扩展为：
('split', 'adapt', 'morning_exercise', 'morning_talk', 'area_game', 'outdoor_game', 'daily_reflection')

'generate' 从未写入生产数据，故直接替换。SQLite 测试库由 ORM model 创建，无需额外处理。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2a3f1b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'bcd07e51527d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_ENUM = (
    "ENUM('split', 'adapt', 'morning_exercise', 'morning_talk', "
    "'area_game', 'outdoor_game', 'daily_reflection')"
)
_OLD_ENUM = "ENUM('split', 'adapt', 'generate')"


def upgrade() -> None:
    """升级：将 generate 替换为 5 个一日活动子类型。"""
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        # 先删除使用旧 Enum 值的行（开发阶段无生产数据）
        op.execute(
            "DELETE FROM prompt_template WHERE task_type = 'generate'"
        )
        op.execute(
            f"ALTER TABLE prompt_template MODIFY COLUMN task_type {_NEW_ENUM} NOT NULL"
        )
    # SQLite：由测试 fixture 通过 create_all 根据最新 ORM 创建，无需迁移


def downgrade() -> None:
    """降级：恢复为 generate 单值。"""
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        # 先删除新 Enum 值的行
        op.execute(
            "DELETE FROM prompt_template WHERE task_type IN "
            "('morning_exercise', 'morning_talk', 'area_game', 'outdoor_game', 'daily_reflection')"
        )
        op.execute(
            f"ALTER TABLE prompt_template MODIFY COLUMN task_type {_OLD_ENUM} NOT NULL"
        )
