"""drop_invite_code_table — 删除邀请码表（邀请码功能已移除）

注册流程改为：首个注册用户自动成为 sys_admin，后续用户等待管理员审核。

Revision ID: 4e2e0e079e56
Revises: 6553de463329
Create Date: 2026-06-13 17:17:39.054874

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e2e0e079e56'
down_revision: Union[str, Sequence[str], None] = '6553de463329'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """删除 invite_code 表（邀请码功能已移除）。"""
    op.drop_table("invite_code")


def downgrade() -> None:
    """重建 invite_code 表（回滚用）。"""
    op.create_table(
        "invite_code",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("note", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_invite_code_tenant_id", "invite_code", ["tenant_id"])
