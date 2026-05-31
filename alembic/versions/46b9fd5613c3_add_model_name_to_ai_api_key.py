"""add_model_name_to_ai_api_key

Revision ID: 46b9fd5613c3
Revises: 1a0d0e46f700
Create Date: 2026-05-17 15:30:50.597578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46b9fd5613c3'
down_revision: Union[str, Sequence[str], None] = '1a0d0e46f700'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    列 model_name 可能已存在（来自另一台机器的未提交迁移）。
    若不存在则新增；若已存在则修改为 NOT NULL + server_default。
    """
    # 回填已有 NULL 值（另一台机器添加列时未设置默认值）
    op.execute(
        "UPDATE ai_api_key SET model_name = 'gpt-4o-mini' WHERE model_name IS NULL"
    )

    # 将列修改为 NOT NULL，并设置 server_default
    op.alter_column(
        "ai_api_key",
        "model_name",
        existing_type=sa.String(128),
        nullable=False,
        server_default="gpt-4o-mini",
    )


def downgrade() -> None:
    """Downgrade schema: 恢复为可空、无默认值。"""
    op.alter_column(
        "ai_api_key",
        "model_name",
        existing_type=sa.String(128),
        nullable=True,
        server_default=None,
    )
