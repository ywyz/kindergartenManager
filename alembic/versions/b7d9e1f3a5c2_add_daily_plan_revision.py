"""add daily plan revision

Revision ID: b7d9e1f3a5c2
Revises: a6c4d8e2f9b1
Create Date: 2026-08-25 13:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7d9e1f3a5c2"
down_revision: Union[str, Sequence[str], None] = "a6c4d8e2f9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add an explicit, positive revision and backfill existing plans to 1."""
    with op.batch_alter_table("daily_plan") as batch_op:
        batch_op.add_column(
            sa.Column(
                "revision",
                sa.Integer(),
                server_default=sa.text("1"),
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "ck_daily_plan_revision_positive",
            "revision >= 1",
        )

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute(
            """
            CREATE TRIGGER trg_daily_plan_revision_initial
            BEFORE INSERT ON daily_plan
            FOR EACH ROW
            WHEN NEW.revision != 1
            BEGIN
                SELECT RAISE(ABORT, 'daily_plan revision must start at one');
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_daily_plan_revision_step
            BEFORE UPDATE ON daily_plan
            FOR EACH ROW
            WHEN NEW.revision != OLD.revision + 1
              OR NOT (
                  NEW.week_number IS NOT OLD.week_number
                  OR NEW.weekday_cn IS NOT OLD.weekday_cn
                  OR NEW.grade IS NOT OLD.grade
                  OR NEW.class_name IS NOT OLD.class_name
                  OR NEW.activity_goal IS NOT OLD.activity_goal
                  OR NEW.activity_prep IS NOT OLD.activity_prep
                  OR NEW.activity_key IS NOT OLD.activity_key
                  OR NEW.activity_difficult IS NOT OLD.activity_difficult
                  OR NEW.activity_process_original IS NOT OLD.activity_process_original
                  OR NEW.activity_process_adapted IS NOT OLD.activity_process_adapted
                  OR NEW.morning_activity IS NOT OLD.morning_activity
                  OR NEW.indoor_area IS NOT OLD.indoor_area
                  OR NEW.outdoor_activity IS NOT OLD.outdoor_activity
                  OR NEW.morning_talk_topic IS NOT OLD.morning_talk_topic
                  OR NEW.morning_talk_questions IS NOT OLD.morning_talk_questions
                  OR NEW.daily_reflection IS NOT OLD.daily_reflection
              )
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'daily_plan update must change content and increment revision by one'
                );
            END
            """
        )
    elif bind.dialect.name == "mysql":
        op.execute(
            """
            CREATE TRIGGER trg_daily_plan_revision_initial
            BEFORE INSERT ON daily_plan
            FOR EACH ROW
            BEGIN
                IF NEW.revision <> 1 THEN
                    SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'daily_plan revision must start at one';
                END IF;
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_daily_plan_revision_step
            BEFORE UPDATE ON daily_plan
            FOR EACH ROW
            BEGIN
                IF NEW.revision <> OLD.revision + 1
                   OR NOT (
                       NOT (NEW.week_number <=> OLD.week_number)
                       OR NOT (CAST(NEW.weekday_cn AS BINARY) <=> CAST(OLD.weekday_cn AS BINARY))
                       OR NOT (CAST(NEW.grade AS BINARY) <=> CAST(OLD.grade AS BINARY))
                       OR NOT (CAST(NEW.class_name AS BINARY) <=> CAST(OLD.class_name AS BINARY))
                       OR NOT (CAST(NEW.activity_goal AS BINARY) <=> CAST(OLD.activity_goal AS BINARY))
                       OR NOT (CAST(NEW.activity_prep AS BINARY) <=> CAST(OLD.activity_prep AS BINARY))
                       OR NOT (CAST(NEW.activity_key AS BINARY) <=> CAST(OLD.activity_key AS BINARY))
                       OR NOT (CAST(NEW.activity_difficult AS BINARY) <=> CAST(OLD.activity_difficult AS BINARY))
                       OR NOT (CAST(NEW.activity_process_original AS BINARY) <=> CAST(OLD.activity_process_original AS BINARY))
                       OR NOT (CAST(NEW.activity_process_adapted AS BINARY) <=> CAST(OLD.activity_process_adapted AS BINARY))
                       OR NOT (CAST(NEW.morning_activity AS BINARY) <=> CAST(OLD.morning_activity AS BINARY))
                       OR NOT (CAST(NEW.indoor_area AS BINARY) <=> CAST(OLD.indoor_area AS BINARY))
                       OR NOT (CAST(NEW.outdoor_activity AS BINARY) <=> CAST(OLD.outdoor_activity AS BINARY))
                       OR NOT (CAST(NEW.morning_talk_topic AS BINARY) <=> CAST(OLD.morning_talk_topic AS BINARY))
                       OR NOT (CAST(NEW.morning_talk_questions AS BINARY) <=> CAST(OLD.morning_talk_questions AS BINARY))
                       OR NOT (CAST(NEW.daily_reflection AS BINARY) <=> CAST(OLD.daily_reflection AS BINARY))
                   ) THEN
                    SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'daily_plan update must change content and increment revision by one';
                END IF;
            END
            """
        )


def downgrade() -> None:
    """Remove the daily-plan revision contract."""
    op.execute("DROP TRIGGER IF EXISTS trg_daily_plan_revision_step")
    op.execute("DROP TRIGGER IF EXISTS trg_daily_plan_revision_initial")
    with op.batch_alter_table("daily_plan") as batch_op:
        batch_op.drop_constraint(
            "ck_daily_plan_revision_positive",
            type_="check",
        )
        batch_op.drop_column("revision")
