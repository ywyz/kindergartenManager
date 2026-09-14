"""Register weekly authoring tasks without rewriting existing prompt versions."""

import sqlalchemy as sa

from alembic import op

revision = "c264d8fa1037"
down_revision = "b153c7e9f026"
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
)
WEEKLY = (
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
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        enum = ",".join("'" + value + "'" for value in values)
        op.execute(
            "ALTER TABLE prompt_template MODIFY task_type ENUM(" + enum + ") NOT NULL"
        )
    # SQLite stores SQLAlchemy Enum as unconstrained VARCHAR; no row rewrite.


def upgrade():
    _alter(OLD + WEEKLY)


def downgrade():
    table = sa.table("prompt_template", sa.column("task_type"))
    if (
        op.get_bind()
        .execute(
            sa.select(table.c.task_type).where(table.c.task_type.in_(WEEKLY)).limit(1)
        )
        .first()
    ):
        raise RuntimeError("weekly_prompt_nonempty_downgrade_denied")
    _alter(OLD)
