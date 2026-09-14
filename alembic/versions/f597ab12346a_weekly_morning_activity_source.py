"""Include the daily morning-activity source with unchanged identity guards."""

from pathlib import Path

import sqlalchemy as sa

from alembic import op, util

revision = "f597ab12346a"
down_revision = "e486fa012359"
branch_labels = None
depends_on = None

_OLD = "source_field IN ('morning_talk_topic','morning_talk_questions','activity_name','outdoor_activity','indoor_area')"
_NEW = _OLD[:-1] + ",'morning_activity')"


def _constraint(sql):
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        # Batch recreation must preserve every existing immutable-source guard.
        triggers = connection.execute(
            sa.text(
                "SELECT name, sql FROM sqlite_master WHERE type='trigger' AND sql IS NOT NULL"
            )
        ).all()
        for name, _ in triggers:
            op.execute(sa.text('DROP TRIGGER "' + name.replace('"', '""') + '"'))
        with op.batch_alter_table("shared_weekly_source", recreate="always") as batch:
            batch.drop_constraint("ck_sws_source_field", type_="check")
            batch.create_check_constraint("ck_sws_source_field", sql)
        for _, definition in triggers:
            op.execute(sa.text(definition))
    else:
        op.drop_constraint("ck_sws_source_field", "shared_weekly_source", type_="check")
        op.create_check_constraint("ck_sws_source_field", "shared_weekly_source", sql)


def _condition(sql):
    sql = sql.replace("'indoor_area')", "'indoor_area','morning_activity')")
    sql = sql.replace(
        "_utf8mb4'indoor_area'\n", "_utf8mb4'indoor_area', _utf8mb4'morning_activity'\n"
    )
    sql = sql.replace(
        "WHEN 'indoor_area' THEN COALESCE(d.indoor_area, '')",
        "WHEN 'indoor_area' THEN COALESCE(d.indoor_area, '')\n                         WHEN 'morning_activity' THEN COALESCE(d.morning_activity, '')",
    )
    return sql


def upgrade():
    prior = util.load_python_file(
        str(Path(__file__).parent), "e486fa012359_owned_weekly_snapshots.py"
    )
    _constraint(_NEW)
    prior._install(
        _condition(prior.SQLITE_SOURCE),
        _condition(prior.MYSQL_SOURCE),
        prior.EVENT_GUARD,
    )


def downgrade():
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM shared_weekly_source WHERE source_field='morning_activity' LIMIT 1"
            )
        )
        .first()
    ):
        raise RuntimeError("morning_activity_downgrade_requires_verified_restore")
    prior = util.load_python_file(
        str(Path(__file__).parent), "e486fa012359_owned_weekly_snapshots.py"
    )
    _constraint(_OLD)
    prior._install(prior.SQLITE_SOURCE, prior.MYSQL_SOURCE, prior.EVENT_GUARD)
