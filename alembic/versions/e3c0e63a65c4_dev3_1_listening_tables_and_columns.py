"""dev3.1 listening tables and columns

Revision ID: e3c0e63a65c4
Revises: 4e2e0e079e56
Create Date: 2026-06-19 18:47:49.854050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = 'e3c0e63a65c4'
down_revision: Union[str, Sequence[str], None] = '4e2e0e079e56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_ENUM = (
    "ENUM('split','adapt','morning_exercise','morning_talk',"
    "'area_game','outdoor_game','daily_reflection','game_observation',"
    "'one_on_one_listening')"
)
_OLD_ENUM = (
    "ENUM('split','adapt','morning_exercise','morning_talk',"
    "'area_game','outdoor_game','daily_reflection','game_observation')"
)


def upgrade() -> None:
    """Upgrade schema."""
    # ── 1. 主表 listening_record ──────────────────────────────────────────
    op.create_table(
        'listening_record',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('obs_year', sa.Integer(), nullable=False),
        sa.Column('obs_month', sa.Integer(), nullable=False),
        sa.Column('child_name', sa.String(length=64), nullable=False),
        sa.Column('adult_count', sa.Integer(), nullable=True),
        sa.Column('child_age', sa.String(length=16), nullable=True),
        sa.Column('grade', sa.String(length=16), nullable=True),
        sa.Column('term', sa.String(length=16), nullable=True),
        sa.Column('class_name', sa.String(length=32), nullable=True),
        sa.Column('observer', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_listening_record_tenant_user', 'listening_record', ['tenant_id', 'user_id'], unique=False)

    # ── 2. 领域表 listening_domain ────────────────────────────────────────
    op.create_table(
        'listening_domain',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('record_id', sa.BigInteger(), nullable=False),
        sa.Column('domain', sa.String(length=8), nullable=False),
        sa.Column('obs_year', sa.Integer(), nullable=True),
        sa.Column('obs_month', sa.Integer(), nullable=True),
        sa.Column('date_1', sa.Date(), nullable=True),
        sa.Column('date_2', sa.Date(), nullable=True),
        sa.Column('date_3', sa.Date(), nullable=True),
        sa.Column('goals', sa.Text(), nullable=True),
        sa.Column('evaluation', sa.Text(), nullable=True),
        sa.Column('support_strategy', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_listening_domain_record', 'listening_domain', ['record_id'], unique=False)
    op.create_index('ix_listening_domain_tenant_user', 'listening_domain', ['tenant_id', 'user_id'], unique=False)

    # ── 3. 图片表 listening_image ─────────────────────────────────────────
    op.create_table(
        'listening_image',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('record_id', sa.BigInteger(), nullable=False),
        sa.Column('domain', sa.String(length=8), nullable=False),
        sa.Column('image_index', sa.Integer(), nullable=False),
        sa.Column('storage_backend', sa.String(length=16), nullable=False),
        sa.Column('blob_content', sa.LargeBinary().with_variant(mysql.LONGBLOB(), 'mysql'), nullable=True),
        sa.Column('object_key', sa.Text(), nullable=True),
        sa.Column('mime_type', sa.String(length=32), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('image_description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_listening_image_record', 'listening_image', ['record_id'], unique=False)
    op.create_index('ix_listening_image_tenant_user', 'listening_image', ['tenant_id', 'user_id'], unique=False)

    # ── 4. 指标结果表 listening_indicator_result ──────────────────────────
    op.create_table(
        'listening_indicator_result',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('record_id', sa.BigInteger(), nullable=False),
        sa.Column('domain', sa.String(length=8), nullable=False),
        sa.Column('catalog_id', sa.BigInteger(), nullable=False),
        sa.Column('stars', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_listening_indicator_record', 'listening_indicator_result', ['record_id'], unique=False)
    op.create_index('ix_listening_indicator_tenant_user', 'listening_indicator_result', ['tenant_id', 'user_id'], unique=False)

    # ── 5. 指标目录表 indicator_catalog ───────────────────────────────────
    op.create_table(
        'indicator_catalog',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('grade', sa.String(length=16), nullable=False),
        sa.Column('term', sa.String(length=16), nullable=False),
        sa.Column('domain', sa.String(length=8), nullable=False),
        sa.Column('level1_name', sa.String(length=64), nullable=False),
        sa.Column('level2_name', sa.String(length=512), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('standard_star1', sa.Text(), nullable=True),
        sa.Column('standard_star2', sa.Text(), nullable=True),
        sa.Column('standard_star3', sa.Text(), nullable=True),
        sa.Column('max_stars', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_indicator_catalog_lookup', 'indicator_catalog',
        ['tenant_id', 'grade', 'term', 'domain', 'sort_order'], unique=False,
    )

    # ── 6. export_records 增列 listening_record_id ────────────────────────
    op.add_column('export_records', sa.Column('listening_record_id', sa.BigInteger(), nullable=True))

    # ── 7. prompt_template.task_type 枚举扩展（仅 MySQL）──────────────────
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute(
            f"ALTER TABLE prompt_template MODIFY COLUMN task_type {_NEW_ENUM} NOT NULL"
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute("DELETE FROM prompt_template WHERE task_type = 'one_on_one_listening'")
        op.execute(
            f"ALTER TABLE prompt_template MODIFY COLUMN task_type {_OLD_ENUM} NOT NULL"
        )

    op.drop_column('export_records', 'listening_record_id')

    op.drop_index('ix_indicator_catalog_lookup', table_name='indicator_catalog')
    op.drop_table('indicator_catalog')

    op.drop_index('ix_listening_indicator_tenant_user', table_name='listening_indicator_result')
    op.drop_index('ix_listening_indicator_record', table_name='listening_indicator_result')
    op.drop_table('listening_indicator_result')

    op.drop_index('ix_listening_image_tenant_user', table_name='listening_image')
    op.drop_index('ix_listening_image_record', table_name='listening_image')
    op.drop_table('listening_image')

    op.drop_index('ix_listening_domain_tenant_user', table_name='listening_domain')
    op.drop_index('ix_listening_domain_record', table_name='listening_domain')
    op.drop_table('listening_domain')

    op.drop_index('ix_listening_record_tenant_user', table_name='listening_record')
    op.drop_table('listening_record')
