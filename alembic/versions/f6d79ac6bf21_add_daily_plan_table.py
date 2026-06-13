"""add daily_plan table

Revision ID: f6d79ac6bf21
Revises: 46b9fd5613c3
Create Date: 2026-05-17 15:55:01.424684

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'f6d79ac6bf21'
down_revision: Union[str, Sequence[str], None] = '46b9fd5613c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'daily_plan' not in inspector.get_table_names():
        # 全新数据库（如 SQLite 首次安装）：daily_plan 从未由 Alembic 创建，直接建表
        op.create_table(
            'daily_plan',
            sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
            sa.Column('tenant_id', sa.BigInteger(), nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('plan_date', sa.Date(), nullable=False),
            sa.Column('week_number', sa.Integer(), nullable=False),
            sa.Column('weekday_cn', sa.String(length=4), nullable=False),
            sa.Column('grade', sa.String(length=16), nullable=False),
            sa.Column('class_name', sa.String(length=32), nullable=False),
            sa.Column('activity_goal', sa.Text(), nullable=True),
            sa.Column('activity_prep', sa.Text(), nullable=True),
            sa.Column('activity_key', sa.Text(), nullable=True),
            sa.Column('activity_difficult', sa.Text(), nullable=True),
            sa.Column('activity_process_original', sa.Text(), nullable=True),
            sa.Column('activity_process_adapted', sa.Text(), nullable=True),
            sa.Column('morning_activity', sa.Text(), nullable=True),
            sa.Column('indoor_area', sa.Text(), nullable=True),
            sa.Column('outdoor_activity', sa.Text(), nullable=True),
            sa.Column('morning_talk_topic', sa.Text(), nullable=True),
            sa.Column('morning_talk_questions', sa.Text(), nullable=True),
            sa.Column('daily_reflection', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_daily_plan_tenant_id', 'daily_plan', ['tenant_id'], unique=False)
        op.create_index('ix_daily_plan_user_id', 'daily_plan', ['user_id'], unique=False)
    else:
        # 已有数据（MySQL 等）：表由历史 MySQL 脚本创建，此处只做调整
        op.alter_column('daily_plan', 'week_number',
                   existing_type=mysql.INTEGER(),
                   nullable=False)
        op.alter_column('daily_plan', 'weekday_cn',
                   existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=4),
                   nullable=False)
        op.alter_column('daily_plan', 'grade',
                   existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=16),
                   nullable=False)
        op.alter_column('daily_plan', 'class_name',
                   existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=32),
                   nullable=False)
        op.drop_index(op.f('ix_daily_plan_tenant_user'), table_name='daily_plan')
        op.drop_index(op.f('uq_daily_plan_tenant_user_date'), table_name='daily_plan')
        op.create_index(op.f('ix_daily_plan_tenant_id'), 'daily_plan', ['tenant_id'], unique=False)
        op.create_index(op.f('ix_daily_plan_user_id'), 'daily_plan', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.drop_index(op.f('ix_daily_plan_user_id'), table_name='daily_plan')
        op.drop_index(op.f('ix_daily_plan_tenant_id'), table_name='daily_plan')
        op.create_index(op.f('uq_daily_plan_tenant_user_date'), 'daily_plan', ['tenant_id', 'user_id', 'plan_date'], unique=True)
        op.create_index(op.f('ix_daily_plan_tenant_user'), 'daily_plan', ['tenant_id', 'user_id'], unique=False)
        op.alter_column('daily_plan', 'class_name',
                   existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=32),
                   nullable=True)
        op.alter_column('daily_plan', 'grade',
                   existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=16),
                   nullable=True)
        op.alter_column('daily_plan', 'weekday_cn',
                   existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=4),
                   nullable=True)
        op.alter_column('daily_plan', 'week_number',
                   existing_type=mysql.INTEGER(),
                   nullable=True)
    else:
        op.drop_table('daily_plan')

