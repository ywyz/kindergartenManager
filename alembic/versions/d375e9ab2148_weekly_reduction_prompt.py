"""Register bounded reduction prompt without rewriting old prompt versions."""

import sqlalchemy as sa

from alembic import op

revision = "d375e9ab2148"
down_revision = "d375e9012abc"
branch_labels = None
depends_on = None

OLD = (
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
    "weekly_morning_talk",
    "weekly_games",
    "weekly_area",
    "weekly_materials",
    "weekly_focus",
    "weekly_environment",
    "weekly_habits",
    "weekly_home",
)


def _alter(values):
    if op.get_bind().dialect.name == "mysql":
        enum = ",".join("'" + value + "'" for value in values)
        op.execute(
            "ALTER TABLE prompt_template MODIFY task_type ENUM(" + enum + ") NOT NULL"
        )


def upgrade():
    _alter(OLD + ("weekly_reduction",))


def downgrade():
    table = sa.table("prompt_template", sa.column("task_type"))
    if (
        op.get_bind()
        .execute(
            sa.select(table.c.task_type)
            .where(table.c.task_type == "weekly_reduction")
            .limit(1)
        )
        .first()
    ):
        raise RuntimeError("weekly_reduction_prompt_nonempty_downgrade_denied")
    _alter(OLD)
