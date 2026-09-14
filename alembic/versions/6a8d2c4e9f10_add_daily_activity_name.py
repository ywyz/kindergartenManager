"""Add nullable daily activity name and include it in the revision contract.

Revision ID: 6a8d2c4e9f10
Revises: 3c9f4b2a7d1e
"""

import sqlalchemy as sa

from alembic import op

revision = "6a8d2c4e9f10"
down_revision = "3c9f4b2a7d1e"
branch_labels = None
depends_on = None

# Frozen migration-local list: future application fields must not change this DDL.
_OLD_FIELDS = (
    "week_number",
    "weekday_cn",
    "grade",
    "class_name",
    "activity_goal",
    "activity_prep",
    "activity_key",
    "activity_difficult",
    "activity_process_original",
    "activity_process_adapted",
    "morning_activity",
    "indoor_area",
    "outdoor_activity",
    "morning_talk_topic",
    "morning_talk_questions",
    "daily_reflection",
)


def _revision_trigger(*, include_name: bool) -> None:
    fields = _OLD_FIELDS + (("activity_name",) if include_name else ())
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        changes = " OR ".join(f"NEW.{f} IS NOT OLD.{f}" for f in fields)
        op.execute(f"""CREATE TRIGGER trg_daily_plan_revision_step
            BEFORE UPDATE ON daily_plan FOR EACH ROW
            WHEN NEW.revision != OLD.revision + 1 OR NOT ({changes})
            BEGIN SELECT RAISE(ABORT,
              'daily_plan update must change content and increment revision by one'); END""")
    elif dialect == "mysql":
        changes = " OR ".join(
            f"NOT (NEW.{f} <=> OLD.{f})"
            if f == "week_number"
            else f"NOT (CAST(NEW.{f} AS BINARY) <=> CAST(OLD.{f} AS BINARY))"
            for f in fields
        )
        op.execute(f"""CREATE TRIGGER trg_daily_plan_revision_step
            BEFORE UPDATE ON daily_plan FOR EACH ROW BEGIN
            IF NEW.revision <> OLD.revision + 1 OR NOT ({changes}) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT =
              'daily_plan update must change content and increment revision by one';
            END IF; END""")
    else:
        raise RuntimeError("unsupported daily_plan migration dialect")


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect not in {"sqlite", "mysql"}:
        raise RuntimeError("unsupported daily_plan migration dialect")
    # Native ADD preserves existing constraints, indexes and immutable evidence.
    op.add_column("daily_plan", sa.Column("activity_name", sa.Text(), nullable=True))
    op.execute("DROP TRIGGER IF EXISTS trg_daily_plan_revision_step")
    _revision_trigger(include_name=True)
    for action in ("INSERT", "UPDATE"):
        name = f"trg_daily_plan_activity_name_{action.lower()}"
        if dialect == "sqlite":
            op.execute(f"""CREATE TRIGGER {name} BEFORE {action} ON daily_plan
                FOR EACH ROW WHEN NEW.activity_name IS NOT NULL AND
                (typeof(NEW.activity_name) != 'text' OR length(CAST(NEW.activity_name AS BLOB)) > 256)
                BEGIN SELECT RAISE(ABORT, 'daily_plan activity_name invalid'); END""")
        else:
            op.execute(f"""CREATE TRIGGER {name} BEFORE {action} ON daily_plan
                FOR EACH ROW BEGIN
                IF NEW.activity_name IS NOT NULL AND OCTET_LENGTH(NEW.activity_name) > 256 THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'daily_plan activity_name invalid';
                END IF; END""")


def downgrade() -> None:
    bind = op.get_bind()
    length = (
        "length(CAST(activity_name AS BLOB))"
        if bind.dialect.name == "sqlite"
        else "OCTET_LENGTH(activity_name)"
    )
    if bind.execute(
        sa.text(
            f"SELECT 1 FROM daily_plan WHERE activity_name IS NOT NULL AND {length} > 0 LIMIT 1"
        )
    ).first():
        raise RuntimeError("activity_name data prevents downgrade")
    # Check before any DDL; never erase names to make rollback pass.
    for trigger in (
        "trg_daily_plan_activity_name_insert",
        "trg_daily_plan_activity_name_update",
        "trg_daily_plan_revision_step",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger}")
    # Supported SQLite has native DROP COLUMN, preserving unrelated constraints/triggers.
    op.drop_column("daily_plan", "activity_name")
    _revision_trigger(include_name=False)
