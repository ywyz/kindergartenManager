"""add personal development record table

Revision ID: 3a8d9b2c1e0f
Revises: 2ea4743f8fa7
Create Date: 2026-07-11 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '3a8d9b2c1e0f'
down_revision: Union[str, Sequence[str], None] = '2ea4743f8fa7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'personal_development_record',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('semester_id', sa.BigInteger(), nullable=False),
        sa.Column('child_name', sa.String(length=64), nullable=False),
        sa.Column('gender', sa.String(length=8), nullable=True),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('enrollment_date', sa.Date(), nullable=True),
        sa.Column('height', sa.Float(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('chest_circumference', sa.Float(), nullable=True),
        sa.Column('hemoglobin', sa.Float(), nullable=True),
        sa.Column('vision_left', sa.Float(), nullable=True),
        sa.Column('vision_right', sa.Float(), nullable=True),
        sa.Column('grade', sa.String(length=16), nullable=True),
        sa.Column('class_name', sa.String(length=32), nullable=True),
        sa.Column('observer', sa.String(length=64), nullable=True),
        sa.Column('development_status', sa.Text(), nullable=True),
        sa.Column('measures_taken', sa.Text(), nullable=True),
        sa.Column('home_contact', sa.Text(), nullable=True),
        sa.Column('outstanding_performance', sa.Text(), nullable=True),
        sa.Column('progress', sa.Text(), nullable=True),
        sa.Column('teacher_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'child_name', 'semester_id', name='uq_personal_child_semester'),
    )
    op.create_index('ix_personal_development_tenant_user', 'personal_development_record', ['tenant_id', 'user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_personal_development_tenant_user', table_name='personal_development_record')
    op.drop_table('personal_development_record')