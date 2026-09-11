"""Explicit daily source mappings and immutable events."""

import sqlalchemy as sa

from alembic import op

revision = "9e31a6c8d204"
down_revision = "8d20f3b5c721"
branch_labels = None
depends_on = None


def _tables(metadata):
    def num(n):
        return sa.Column(n, sa.BigInteger(), nullable=False)

    def ident():
        return sa.Column(
            "id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True
        )

    def target():
        return sa.ForeignKeyConstraint(
            ["tenant_id", "class_instance_id", "semester_id"],
            [
                "class_semester.tenant_id",
                "class_semester.class_instance_id",
                "class_semester.semester_id",
            ],
            ondelete="RESTRICT",
        )

    event = sa.Table(
        "identity_mapping_event",
        metadata,
        ident(),
        num("tenant_id"),
        num("daily_plan_id"),
        num("source_user_id"),
        sa.Column("source_date", sa.Date(), nullable=False),
        num("source_revision"),
        num("class_instance_id"),
        num("semester_id"),
        num("revision"),
        sa.Column("previous_id", sa.BigInteger()),
        num("actor_id"),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column("binding_hash", sa.String(64), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "daily_plan_id", "revision"),
        target(),
        sa.CheckConstraint(
            "revision >= 1 AND source_revision >= 1", name="ck_mapping_event_revision"
        ),
        mysql_engine="InnoDB",
    )
    pointer = sa.Table(
        "daily_plan_identity",
        metadata,
        num("tenant_id"),
        num("daily_plan_id"),
        num("source_user_id"),
        sa.Column("source_date", sa.Date(), nullable=False),
        num("class_instance_id"),
        num("semester_id"),
        num("mapping_id"),
        num("revision"),
        sa.PrimaryKeyConstraint("tenant_id", "daily_plan_id"),
        target(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "daily_plan_id", "source_user_id"],
            ["daily_plan.tenant_id", "daily_plan.id", "daily_plan.user_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "mapping_id"],
            ["identity_mapping_event.tenant_id", "identity_mapping_event.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_daily_identity_revision"),
        mysql_engine="InnoDB",
    )
    return event, pointer


def upgrade():
    bind = op.get_bind()
    op.create_index(
        "uq_daily_identity_parent",
        "daily_plan",
        ["tenant_id", "id", "user_id"],
        unique=True,
    )
    metadata = sa.MetaData()
    for name in ("daily_plan", "class_semester"):
        sa.Table(name, metadata, autoload_with=bind)
    event, pointer = _tables(metadata)
    event.create(bind)
    pointer.create(bind)
    event_invalid = """NOT EXISTS (SELECT 1 FROM daily_plan d WHERE d.tenant_id=NEW.tenant_id AND d.id=NEW.daily_plan_id AND d.user_id=NEW.source_user_id AND d.plan_date=NEW.source_date AND d.revision=NEW.source_revision)
        OR (NEW.revision=1 AND (NEW.previous_id IS NOT NULL OR EXISTS (SELECT 1 FROM daily_plan_identity p WHERE p.tenant_id=NEW.tenant_id AND p.daily_plan_id=NEW.daily_plan_id)))
        OR (NEW.revision>1 AND NOT EXISTS (SELECT 1 FROM daily_plan_identity p WHERE p.tenant_id=NEW.tenant_id AND p.daily_plan_id=NEW.daily_plan_id AND p.mapping_id=NEW.previous_id AND p.revision=NEW.revision-1))"""
    if bind.dialect.name == "sqlite":
        op.execute(
            f"CREATE TRIGGER mapping_event_insert BEFORE INSERT ON identity_mapping_event WHEN {event_invalid} BEGIN SELECT RAISE(ABORT, 'mapping_conflict'); END"
        )
    else:
        op.execute(
            f"CREATE TRIGGER mapping_event_insert BEFORE INSERT ON identity_mapping_event FOR EACH ROW BEGIN IF {event_invalid} THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='mapping_conflict'; END IF; END"
        )
    for action in ("UPDATE", "DELETE"):
        name = "mapping_event_no_" + action.lower()
        if bind.dialect.name == "sqlite":
            op.execute(
                f"CREATE TRIGGER {name} BEFORE {action} ON identity_mapping_event BEGIN SELECT RAISE(ABORT, 'immutable_mapping'); END"
            )
        else:
            op.execute(
                f"CREATE TRIGGER {name} BEFORE {action} ON identity_mapping_event FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='immutable_mapping'"
            )
    condition = "NOT EXISTS (SELECT 1 FROM identity_mapping_event e WHERE e.tenant_id=NEW.tenant_id AND e.id=NEW.mapping_id AND e.daily_plan_id=NEW.daily_plan_id AND e.source_user_id=NEW.source_user_id AND e.source_date=NEW.source_date AND e.class_instance_id=NEW.class_instance_id AND e.semester_id=NEW.semester_id AND e.revision=NEW.revision)"
    for action in ("INSERT", "UPDATE"):
        name = "mapping_pointer_" + action.lower()
        extra = (
            " OR NEW.revision != OLD.revision+1 OR NEW.tenant_id != OLD.tenant_id OR NEW.daily_plan_id != OLD.daily_plan_id"
            if action == "UPDATE"
            else " OR NEW.revision != 1"
        )
        if bind.dialect.name == "sqlite":
            op.execute(
                f"CREATE TRIGGER {name} BEFORE {action} ON daily_plan_identity WHEN {condition}{extra} BEGIN SELECT RAISE(ABORT, 'mapping_conflict'); END"
            )
        else:
            op.execute(
                f"CREATE TRIGGER {name} BEFORE {action} ON daily_plan_identity FOR EACH ROW BEGIN IF {condition}{extra} THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='mapping_conflict'; END IF; END"
            )


def downgrade():
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM identity_mapping_event LIMIT 1")).first():
        raise RuntimeError("nonempty_mapping_downgrade_refused")
    op.drop_table("daily_plan_identity")
    op.drop_table("identity_mapping_event")
    op.drop_index("uq_daily_identity_parent", table_name="daily_plan")
