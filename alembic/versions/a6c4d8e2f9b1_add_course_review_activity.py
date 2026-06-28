"""add course review activity

Revision ID: a6c4d8e2f9b1
Revises: d5e4f3a2b1c0
Create Date: 2026-06-28 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a6c4d8e2f9b1"
down_revision: Union[str, Sequence[str], None] = "d5e4f3a2b1c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_ENUM = (
    "ENUM('split','adapt','morning_exercise','morning_talk',"
    "'area_game','outdoor_game','daily_reflection','game_observation',"
    "'one_on_one_listening','homemade_teaching','course_review_activity')"
)
_OLD_ENUM = (
    "ENUM('split','adapt','morning_exercise','morning_talk',"
    "'area_game','outdoor_game','daily_reflection','game_observation',"
    "'one_on_one_listening','homemade_teaching')"
)


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    if not _has_table("course_review_activity"):
        op.create_table(
            "course_review_activity",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.BigInteger(), nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("grade", sa.String(length=16), nullable=False),
            sa.Column("class_name", sa.String(length=32), nullable=False),
            sa.Column("teacher_name", sa.String(length=64), nullable=False),
            sa.Column("activity_name", sa.String(length=128), nullable=False),
            sa.Column("child_count", sa.String(length=32), nullable=False),
            sa.Column("activity_time", sa.String(length=64), nullable=False),
            sa.Column("lesson_plan_original", sa.Text(), nullable=False),
            sa.Column("activity_goal", sa.Text(), nullable=False),
            sa.Column("activity_prep", sa.Text(), nullable=False),
            sa.Column("activity_process", sa.Text(), nullable=False),
            sa.Column("goal_adjusted", sa.Boolean(), nullable=False),
            sa.Column("goal_adjustment", sa.Text(), nullable=False),
            sa.Column("activity_goal_revised", sa.Text(), nullable=False),
            sa.Column("prep_adjusted", sa.Boolean(), nullable=False),
            sa.Column("prep_adjustment", sa.Text(), nullable=False),
            sa.Column("activity_prep_revised", sa.Text(), nullable=False),
            sa.Column("process_adjustment", sa.Text(), nullable=False),
            sa.Column("activity_process_revised", sa.Text(), nullable=False),
            sa.Column("review_reason", sa.Text(), nullable=False),
            sa.Column("revised_lesson_plan", sa.Text(), nullable=False),
            sa.Column("ai_raw_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_course_review_activity_tenant_user",
            "course_review_activity",
            ["tenant_id", "user_id"],
            unique=False,
        )

    if not _has_column("export_records", "course_review_activity_id"):
        with op.batch_alter_table("export_records") as batch_op:
            batch_op.add_column(
                sa.Column("course_review_activity_id", sa.BigInteger(), nullable=True)
            )

    if bind.dialect.name == "mysql":
        op.execute(
            f"ALTER TABLE prompt_template MODIFY COLUMN task_type {_NEW_ENUM} NOT NULL"
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name == "mysql":
        op.execute("DELETE FROM prompt_template WHERE task_type = 'course_review_activity'")
        op.execute(
            f"ALTER TABLE prompt_template MODIFY COLUMN task_type {_OLD_ENUM} NOT NULL"
        )

    if _has_column("export_records", "course_review_activity_id"):
        with op.batch_alter_table("export_records") as batch_op:
            batch_op.drop_column("course_review_activity_id")

    if _has_table("course_review_activity"):
        op.drop_index(
            "ix_course_review_activity_tenant_user",
            table_name="course_review_activity",
        )
        op.drop_table("course_review_activity")
