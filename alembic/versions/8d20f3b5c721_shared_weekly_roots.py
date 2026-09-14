"""Shared weekly roots, immutable theme versions, date occupancy and audit.

Revision ID: 8d20f3b5c721
Revises: 7c91e2a4b610
"""

import sqlalchemy as sa

from alembic import op

revision = "8d20f3b5c721"
down_revision = "7c91e2a4b610"
branch_labels = None
depends_on = None


def _tables(metadata):
    def idcol():
        return sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        )

    def num(name, nullable=False):
        return sa.Column(name, sa.BigInteger(), nullable=nullable)

    def fk(local, remote):
        return sa.ForeignKeyConstraint(local, remote, ondelete="RESTRICT")

    def created():
        return sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        )

    def table(name, *cols):
        return sa.Table(name, metadata, *cols, mysql_engine="InnoDB")

    root = table(
        "shared_weekly_plan",
        idcol(),
        num("tenant_id"),
        num("class_instance_id"),
        num("semester_id"),
        sa.Column("anchor_monday", sa.Date(), nullable=False),
        sa.Column("contract", sa.String(32), nullable=False),
        num("created_by"),
        num("current_version", True),
        num("revision"),
        created(),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.CheckConstraint("contract = 'shared_weekly_v1'", name="ck_sw_contract"),
        sa.CheckConstraint("revision >= 0", name="ck_sw_revision"),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "id", "class_instance_id"),
        sa.UniqueConstraint(
            "tenant_id", "class_instance_id", "semester_id", "anchor_monday"
        ),
        fk(
            ["tenant_id", "class_instance_id", "semester_id"],
            [
                "class_semester.tenant_id",
                "class_semester.class_instance_id",
                "class_semester.semester_id",
            ],
        ),
        fk(["tenant_id", "created_by"], ["user.tenant_id", "user.id"]),
    )
    version = table(
        "shared_weekly_version",
        idcol(),
        num("tenant_id"),
        num("plan_id"),
        num("version"),
        num("predecessor", True),
        num("editor_id"),
        num("assignment_id"),
        num("assignment_revision"),
        num("membership_revision"),
        sa.Column("assignments_json", sa.Text(), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False, unique=True),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column("body_json", sa.Text(), nullable=False),
        sa.Column("facts_json", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        created(),
        sa.CheckConstraint(
            "version >= 1 AND assignment_revision >= 1 AND membership_revision >= 1",
            name="ck_swv_positive",
        ),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "plan_id", "id"),
        sa.UniqueConstraint("tenant_id", "plan_id", "version"),
        fk(
            ["tenant_id", "plan_id"],
            ["shared_weekly_plan.tenant_id", "shared_weekly_plan.id"],
        ),
        fk(
            ["tenant_id", "plan_id", "predecessor"],
            [
                "shared_weekly_version.tenant_id",
                "shared_weekly_version.plan_id",
                "shared_weekly_version.id",
            ],
        ),
        fk(["tenant_id", "editor_id"], ["user.tenant_id", "user.id"]),
        fk(
            ["tenant_id", "assignment_id"],
            ["teacher_class_assignment.tenant_id", "teacher_class_assignment.id"],
        ),
    )
    dates = table(
        "shared_weekly_date",
        num("tenant_id"),
        num("plan_id"),
        num("class_instance_id"),
        sa.Column("day_date", sa.Date(), nullable=False),
        created(),
        sa.PrimaryKeyConstraint("tenant_id", "class_instance_id", "day_date"),
        sa.UniqueConstraint("tenant_id", "plan_id", "day_date"),
        fk(
            ["tenant_id", "plan_id", "class_instance_id"],
            [
                "shared_weekly_plan.tenant_id",
                "shared_weekly_plan.id",
                "shared_weekly_plan.class_instance_id",
            ],
        ),
    )
    audit = table(
        "shared_weekly_audit",
        idcol(),
        num("tenant_id"),
        num("actor_id"),
        num("class_instance_id"),
        num("semester_id"),
        num("plan_id"),
        num("version_id"),
        num("revision"),
        num("membership_revision"),
        sa.Column("assignments_json", sa.Text(), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False, unique=True),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(16), nullable=False),
        created(),
        sa.CheckConstraint("action IN ('create','save','read')", name="ck_swa_action"),
        sa.CheckConstraint(
            "outcome IN ('created','saved','existing','unchanged','loaded')",
            name="ck_swa_outcome",
        ),
        sa.CheckConstraint("reason = 'authorized'", name="ck_swa_reason"),
    )
    return root, version, dates, audit


def upgrade():
    bind = op.get_bind()
    metadata = sa.MetaData()
    for name in ("user", "class_semester", "teacher_class_assignment"):
        sa.Table(name, metadata, autoload_with=bind)
    tables = _tables(metadata)
    for table in tables:
        table.create(bind)
    dialect = bind.dialect.name
    for name in ("shared_weekly_version", "shared_weekly_date", "shared_weekly_audit"):
        for action in ("UPDATE", "DELETE"):
            trigger = f"{name}_{action.lower()}_deny"
            if dialect == "sqlite":
                op.execute(
                    f"CREATE TRIGGER {trigger} BEFORE {action} ON {name} BEGIN SELECT RAISE(ABORT, 'shared_immutable'); END"
                )
            else:
                op.execute(
                    f"CREATE TRIGGER {trigger} BEFORE {action} ON {name} FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='shared_immutable'"
                )
    if dialect == "sqlite":
        op.execute("""CREATE TRIGGER shared_root_insert_guard BEFORE INSERT ON shared_weekly_plan BEGIN
          SELECT CASE WHEN NEW.revision != 0 OR NEW.current_version IS NOT NULL
          OR strftime('%w',NEW.anchor_monday) != '1'
          THEN RAISE(ABORT,'shared_publish_invalid') END; END""")
        op.execute("""CREATE TRIGGER shared_date_insert_guard BEFORE INSERT ON shared_weekly_date BEGIN
          SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM shared_weekly_plan p WHERE p.id=NEW.plan_id
            AND p.tenant_id=NEW.tenant_id AND p.class_instance_id=NEW.class_instance_id AND p.revision=0)
          THEN RAISE(ABORT,'shared_immutable') END; END""")
        op.execute(
            "CREATE TRIGGER shared_root_delete_deny BEFORE DELETE ON shared_weekly_plan BEGIN SELECT RAISE(ABORT, 'shared_immutable'); END"
        )
        op.execute("""CREATE TRIGGER shared_root_publish BEFORE UPDATE ON shared_weekly_plan BEGIN
          SELECT CASE WHEN NEW.id != OLD.id OR NEW.tenant_id != OLD.tenant_id
          OR NEW.class_instance_id != OLD.class_instance_id OR NEW.semester_id != OLD.semester_id
          OR NEW.anchor_monday != OLD.anchor_monday OR NEW.contract != OLD.contract
          OR NEW.created_by != OLD.created_by OR NEW.created_at != OLD.created_at
          OR NEW.revision != OLD.revision + 1
          OR NOT EXISTS (SELECT 1 FROM shared_weekly_version v JOIN shared_weekly_audit a
            ON a.operation_id=v.operation_id AND a.tenant_id=v.tenant_id AND a.version_id=v.id AND a.plan_id=v.plan_id
            AND a.actor_id=v.editor_id AND a.session_hash=v.session_hash
            AND a.class_instance_id=NEW.class_instance_id AND a.semester_id=NEW.semester_id
            AND a.revision=NEW.revision AND a.membership_revision=v.membership_revision
            AND a.assignments_json=v.assignments_json
            AND ((NEW.revision=1 AND a.action='create' AND a.outcome='created')
              OR (NEW.revision>1 AND a.action='save' AND a.outcome='saved'))
            WHERE v.tenant_id=NEW.tenant_id AND v.plan_id=NEW.id AND v.id=NEW.current_version
            AND v.version=NEW.revision AND v.predecessor IS OLD.current_version)
          OR (SELECT COUNT(*) FROM shared_weekly_date d WHERE d.tenant_id=NEW.tenant_id AND d.plan_id=NEW.id) NOT IN (5,6)
          THEN RAISE(ABORT,'shared_publish_invalid') END; END""")
    else:
        op.execute("""CREATE TRIGGER shared_root_insert_guard BEFORE INSERT ON shared_weekly_plan FOR EACH ROW BEGIN
          IF NEW.revision <> 0 OR NEW.current_version IS NOT NULL OR WEEKDAY(NEW.anchor_monday) <> 0
          THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='shared_publish_invalid'; END IF; END""")
        op.execute("""CREATE TRIGGER shared_date_insert_guard BEFORE INSERT ON shared_weekly_date FOR EACH ROW BEGIN
          IF NOT EXISTS (SELECT 1 FROM shared_weekly_plan p WHERE p.id=NEW.plan_id
            AND p.tenant_id=NEW.tenant_id AND p.class_instance_id=NEW.class_instance_id AND p.revision=0)
          THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='shared_immutable'; END IF; END""")
        op.execute(
            "CREATE TRIGGER shared_root_delete_deny BEFORE DELETE ON shared_weekly_plan FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='shared_immutable'"
        )
        op.execute("""CREATE TRIGGER shared_root_publish BEFORE UPDATE ON shared_weekly_plan FOR EACH ROW BEGIN
          IF NEW.id <> OLD.id OR NEW.tenant_id <> OLD.tenant_id
          OR NEW.class_instance_id <> OLD.class_instance_id OR NEW.semester_id <> OLD.semester_id
          OR NEW.anchor_monday <> OLD.anchor_monday OR NEW.contract <> OLD.contract
          OR NEW.created_by <> OLD.created_by OR NEW.created_at <> OLD.created_at
          OR NEW.revision <> OLD.revision + 1
          OR NOT EXISTS (SELECT 1 FROM shared_weekly_version v JOIN shared_weekly_audit a
            ON a.operation_id=v.operation_id AND a.tenant_id=v.tenant_id AND a.version_id=v.id AND a.plan_id=v.plan_id
            AND a.actor_id=v.editor_id AND a.session_hash=v.session_hash
            AND a.class_instance_id=NEW.class_instance_id AND a.semester_id=NEW.semester_id
            AND a.revision=NEW.revision AND a.membership_revision=v.membership_revision
            AND a.assignments_json=v.assignments_json
            AND ((NEW.revision=1 AND a.action='create' AND a.outcome='created')
              OR (NEW.revision>1 AND a.action='save' AND a.outcome='saved'))
            WHERE v.tenant_id=NEW.tenant_id AND v.plan_id=NEW.id AND v.id=NEW.current_version
            AND v.version=NEW.revision AND (v.predecessor <=> OLD.current_version))
          OR (SELECT COUNT(*) FROM shared_weekly_date d WHERE d.tenant_id=NEW.tenant_id AND d.plan_id=NEW.id) NOT IN (5,6)
          THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='shared_publish_invalid'; END IF; END""")


def downgrade():
    bind = op.get_bind()
    names = (
        "shared_weekly_audit",
        "shared_weekly_date",
        "shared_weekly_version",
        "shared_weekly_plan",
    )
    for name in names:
        if bind.execute(sa.text(f"SELECT COUNT(*) FROM {name}")).scalar_one():
            raise RuntimeError("shared_nonempty_downgrade_denied")
    op.execute("DROP TRIGGER shared_root_insert_guard")
    op.execute("DROP TRIGGER shared_date_insert_guard")
    op.execute("DROP TRIGGER shared_root_publish")
    op.execute("DROP TRIGGER shared_root_delete_deny")
    for name in names:
        if name != "shared_weekly_plan":
            for action in ("update", "delete"):
                op.execute(f"DROP TRIGGER {name}_{action}_deny")
        op.drop_table(name)
