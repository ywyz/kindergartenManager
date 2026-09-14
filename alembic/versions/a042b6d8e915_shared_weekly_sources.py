"""Immutable source snapshots and source-read/check audits for shared weeks."""

import sqlalchemy as sa

from alembic import op

revision = "a042b6d8e915"
down_revision = "9e31a6c8d204"
branch_labels = None
depends_on = None


def _id_column():
    return sa.Column(
        "id",
        sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
        primary_key=True,
        autoincrement=True,
    )


def _number(name: str):
    return sa.Column(name, sa.BigInteger(), nullable=False)


def _created():
    return sa.Column(
        "created_at",
        sa.DateTime(),
        nullable=False,
        server_default=sa.func.current_timestamp(),
    )


def _fk(local, remote):
    return sa.ForeignKeyConstraint(local, remote, ondelete="RESTRICT")


def _tables(metadata):
    source = sa.Table(
        "shared_weekly_source",
        metadata,
        _id_column(),
        _number("tenant_id"),
        _number("version_id"),
        _number("source_id"),
        _number("source_user_id"),
        sa.Column("source_date", sa.Date(), nullable=False),
        _number("source_revision"),
        _number("mapping_id"),
        _number("mapping_revision"),
        sa.Column("source_field", sa.String(32), nullable=False),
        sa.Column("target_path", sa.String(64), nullable=False),
        sa.Column("imported_value", sa.Text(), nullable=False),
        sa.Column("imported_hash", sa.String(64), nullable=False),
        sa.Column("adopted_hash", sa.String(64), nullable=False),
        sa.Column("provenance", sa.String(16), nullable=False),
        _created(),
        _fk(
            ["tenant_id", "version_id"],
            ["shared_weekly_version.tenant_id", "shared_weekly_version.id"],
        ),
        _fk(
            ["tenant_id", "mapping_id"],
            ["identity_mapping_event.tenant_id", "identity_mapping_event.id"],
        ),
        sa.UniqueConstraint(
            "tenant_id", "version_id", "target_path", name="uq_sws_target"
        ),
        sa.CheckConstraint(
            "source_id > 0 AND source_user_id > 0 AND source_revision > 0",
            name="ck_sws_source_identity",
        ),
        sa.CheckConstraint(
            "mapping_id > 0 AND mapping_revision > 0", name="ck_sws_mapping"
        ),
        sa.CheckConstraint(
            "source_field IN ('morning_talk_topic','morning_talk_questions','activity_name','outdoor_activity','indoor_area')",
            name="ck_sws_source_field",
        ),
        sa.CheckConstraint(
            "target_path <> '' AND length(target_path) <= 64",
            name="ck_sws_target_path",
        ),
        sa.CheckConstraint(
            "length(imported_hash) = 64 AND length(adopted_hash) = 64",
            name="ck_sws_hash_length",
        ),
        sa.CheckConstraint(
            "provenance IN ('imported','manual')", name="ck_sws_provenance"
        ),
        mysql_engine="InnoDB",
    )

    audit = sa.Table(
        "shared_weekly_source_audit",
        metadata,
        _id_column(),
        _number("tenant_id"),
        _number("actor_id"),
        _number("plan_id"),
        _number("version_id"),
        _number("class_instance_id"),
        _number("semester_id"),
        _number("membership_revision"),
        sa.Column("assignments_json", sa.Text(), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False, unique=True),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(16), nullable=False),
        _created(),
        _fk(["tenant_id", "actor_id"], ["user.tenant_id", "user.id"]),
        _fk(
            ["tenant_id", "plan_id"],
            ["shared_weekly_plan.tenant_id", "shared_weekly_plan.id"],
        ),
        _fk(
            ["tenant_id", "plan_id", "version_id"],
            [
                "shared_weekly_version.tenant_id",
                "shared_weekly_version.plan_id",
                "shared_weekly_version.id",
            ],
        ),
        sa.CheckConstraint(
            "action IN ('source_read','source_check')", name="ck_swsa_action"
        ),
        sa.CheckConstraint("outcome = 'success'", name="ck_swsa_outcome"),
        sa.CheckConstraint("reason = 'authorized'", name="ck_swsa_reason"),
        mysql_engine="InnoDB",
    )
    return source, audit


def _create_immutable_trigger(bind, table: str, action: str, message: str) -> None:
    name = f"{table}_{action.lower()}_deny"
    if bind.dialect.name == "sqlite":
        op.execute(
            f"CREATE TRIGGER {name} BEFORE {action} ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{message}'); END"
        )
    else:
        op.execute(
            f"CREATE TRIGGER {name} BEFORE {action} ON {table} FOR EACH ROW "
            f"SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='{message}'"
        )


def upgrade():
    bind = op.get_bind()
    metadata = sa.MetaData()
    for name in (
        "user",
        "identity_mapping_event",
        "shared_weekly_plan",
        "shared_weekly_version",
    ):
        sa.Table(name, metadata, autoload_with=bind)
    source, audit = _tables(metadata)
    source.create(bind)
    audit.create(bind)

    for table in ("shared_weekly_source", "shared_weekly_source_audit"):
        _create_immutable_trigger(bind, table, "UPDATE", "shared_immutable")
        _create_immutable_trigger(bind, table, "DELETE", "shared_immutable")

    # A source row may be appended only while its new version is the next
    # unpublished version.  Once the root pointer moves, the same insert is
    # rejected.  This leaves source rows atomic with the version publication.
    if bind.dialect.name == "sqlite":
        condition = """NOT EXISTS (
            SELECT 1
              FROM shared_weekly_version v
              JOIN shared_weekly_plan p
                ON p.tenant_id = v.tenant_id AND p.id = v.plan_id
             WHERE v.tenant_id = NEW.tenant_id
               AND v.id = NEW.version_id
               AND ((p.revision = 0 AND p.current_version IS NULL
                     AND v.version = 1 AND v.predecessor IS NULL)
                 OR (v.version = p.revision + 1
                     AND v.predecessor IS p.current_version))
        ) OR NOT EXISTS (
            SELECT 1
              FROM identity_mapping_event e
              JOIN shared_weekly_version v
                ON v.tenant_id = e.tenant_id AND v.id = NEW.version_id
              JOIN shared_weekly_plan p
                ON p.tenant_id = v.tenant_id AND p.id = v.plan_id
             WHERE e.tenant_id = NEW.tenant_id
               AND e.id = NEW.mapping_id
               AND e.revision = NEW.mapping_revision
               AND e.daily_plan_id = NEW.source_id
               AND e.source_user_id = NEW.source_user_id
               AND e.source_date = NEW.source_date
               AND e.class_instance_id = p.class_instance_id
               AND e.semester_id = p.semester_id
               AND NEW.source_revision >= e.source_revision
        ) OR NOT (
            NEW.source_field IN ('morning_talk_topic','morning_talk_questions',
                                 'activity_name','outdoor_activity','indoor_area')
            AND NEW.provenance IN ('imported','manual')
            AND NEW.target_path = '{"day":"' || NEW.source_date
                || '","field":"' || NEW.source_field || '"}'
            AND EXISTS (
                SELECT 1
                  FROM shared_weekly_date d
                  JOIN shared_weekly_version v
                    ON v.tenant_id = d.tenant_id AND v.plan_id = d.plan_id
                 WHERE v.tenant_id = NEW.tenant_id
                   AND v.id = NEW.version_id
                   AND d.day_date = NEW.source_date
            )
        ) OR NOT (
            EXISTS (
                SELECT 1
                  FROM shared_weekly_version v
                  JOIN shared_weekly_source prior_source
                    ON prior_source.tenant_id = v.tenant_id
                   AND prior_source.version_id = v.predecessor
                   AND prior_source.target_path = NEW.target_path
                   AND prior_source.source_id = NEW.source_id
                   AND prior_source.source_user_id = NEW.source_user_id
                   AND prior_source.source_date = NEW.source_date
                   AND prior_source.source_revision = NEW.source_revision
                   AND prior_source.mapping_id = NEW.mapping_id
                   AND prior_source.mapping_revision = NEW.mapping_revision
                   AND prior_source.source_field = NEW.source_field
                   AND prior_source.imported_value = NEW.imported_value
                   AND prior_source.imported_hash = NEW.imported_hash
                 WHERE v.tenant_id = NEW.tenant_id
                   AND v.id = NEW.version_id
            )
            OR EXISTS (
                SELECT 1
                  FROM daily_plan d
                  JOIN daily_plan_identity m
                    ON m.tenant_id = NEW.tenant_id
                   AND m.daily_plan_id = NEW.source_id
                 WHERE d.tenant_id = NEW.tenant_id
                   AND d.id = NEW.source_id
                   AND d.user_id = NEW.source_user_id
                   AND d.plan_date = NEW.source_date
                   AND d.revision = NEW.source_revision
                   AND m.source_user_id = NEW.source_user_id
                   AND m.source_date = NEW.source_date
                   AND m.mapping_id = NEW.mapping_id
                   AND m.revision = NEW.mapping_revision
                   AND CASE NEW.source_field
                         WHEN 'morning_talk_topic' THEN COALESCE(d.morning_talk_topic, '')
                         WHEN 'morning_talk_questions' THEN COALESCE(d.morning_talk_questions, '')
                         WHEN 'activity_name' THEN COALESCE(d.activity_name, '')
                         WHEN 'outdoor_activity' THEN COALESCE(d.outdoor_activity, '')
                         WHEN 'indoor_area' THEN COALESCE(d.indoor_area, '')
                       END = NEW.imported_value
            )
        )"""
        op.execute(
            "CREATE TRIGGER shared_weekly_source_insert_guard "
            "BEFORE INSERT ON shared_weekly_source "
            f"WHEN {condition} BEGIN SELECT RAISE(ABORT, 'shared_source_publish_invalid'); END"
        )
    else:
        condition = """NOT EXISTS (
            SELECT 1
              FROM shared_weekly_version v
              JOIN shared_weekly_plan p
                ON p.tenant_id = v.tenant_id AND p.id = v.plan_id
             WHERE v.tenant_id = NEW.tenant_id
               AND v.id = NEW.version_id
               AND ((p.revision = 0 AND p.current_version IS NULL
                     AND v.version = 1 AND v.predecessor IS NULL)
                 OR (v.version = p.revision + 1
                     AND v.predecessor <=> p.current_version))
        ) OR NOT EXISTS (
            SELECT 1
              FROM identity_mapping_event e
              JOIN shared_weekly_version v
                ON v.tenant_id = e.tenant_id AND v.id = NEW.version_id
              JOIN shared_weekly_plan p
                ON p.tenant_id = v.tenant_id AND p.id = v.plan_id
             WHERE e.tenant_id = NEW.tenant_id
               AND e.id = NEW.mapping_id
               AND e.revision = NEW.mapping_revision
               AND e.daily_plan_id = NEW.source_id
               AND e.source_user_id = NEW.source_user_id
               AND e.source_date = NEW.source_date
               AND e.class_instance_id = p.class_instance_id
               AND e.semester_id = p.semester_id
               AND NEW.source_revision >= e.source_revision
        ) OR NOT (
            BINARY NEW.source_field IN (
                _utf8mb4'morning_talk_topic', _utf8mb4'morning_talk_questions',
                _utf8mb4'activity_name', _utf8mb4'outdoor_activity', _utf8mb4'indoor_area'
            )
            AND BINARY NEW.provenance IN (_utf8mb4'imported', _utf8mb4'manual')
            AND BINARY NEW.target_path = BINARY CONCAT(
                '{"day":"', DATE_FORMAT(NEW.source_date, '%Y-%m-%d'),
                '","field":"', NEW.source_field, '"}'
            )
            AND EXISTS (
                SELECT 1
                  FROM shared_weekly_date d
                  JOIN shared_weekly_version v
                    ON v.tenant_id = d.tenant_id AND v.plan_id = d.plan_id
                 WHERE v.tenant_id = NEW.tenant_id
                   AND v.id = NEW.version_id
                   AND d.day_date = NEW.source_date
            )
        ) OR NOT (
            EXISTS (
                SELECT 1
                  FROM shared_weekly_version v
                  JOIN shared_weekly_source prior_source
                    ON prior_source.tenant_id = v.tenant_id
                   AND prior_source.version_id = v.predecessor
                   AND BINARY prior_source.target_path = BINARY NEW.target_path
                   AND prior_source.source_id = NEW.source_id
                   AND prior_source.source_user_id = NEW.source_user_id
                   AND prior_source.source_date = NEW.source_date
                   AND prior_source.source_revision = NEW.source_revision
                   AND prior_source.mapping_id = NEW.mapping_id
                   AND prior_source.mapping_revision = NEW.mapping_revision
                   AND BINARY prior_source.source_field = BINARY NEW.source_field
                   AND BINARY prior_source.imported_value = BINARY NEW.imported_value
                   AND BINARY prior_source.imported_hash = BINARY NEW.imported_hash
                 WHERE v.tenant_id = NEW.tenant_id
                   AND v.id = NEW.version_id
            )
            OR EXISTS (
                SELECT 1
                  FROM daily_plan d
                  JOIN daily_plan_identity m
                    ON m.tenant_id = NEW.tenant_id
                   AND m.daily_plan_id = NEW.source_id
                 WHERE d.tenant_id = NEW.tenant_id
                   AND d.id = NEW.source_id
                   AND d.user_id = NEW.source_user_id
                   AND d.plan_date = NEW.source_date
                   AND d.revision = NEW.source_revision
                   AND m.source_user_id = NEW.source_user_id
                   AND m.source_date = NEW.source_date
                   AND m.mapping_id = NEW.mapping_id
                   AND m.revision = NEW.mapping_revision
                   AND BINARY (CASE NEW.source_field
                         WHEN 'morning_talk_topic' THEN COALESCE(d.morning_talk_topic, '')
                         WHEN 'morning_talk_questions' THEN COALESCE(d.morning_talk_questions, '')
                         WHEN 'activity_name' THEN COALESCE(d.activity_name, '')
                         WHEN 'outdoor_activity' THEN COALESCE(d.outdoor_activity, '')
                         WHEN 'indoor_area' THEN COALESCE(d.indoor_area, '')
                       END) = BINARY NEW.imported_value
            )
        )"""
        op.execute(
            "CREATE TRIGGER shared_weekly_source_insert_guard "
            "BEFORE INSERT ON shared_weekly_source FOR EACH ROW BEGIN "
            f"IF {condition} THEN SIGNAL SQLSTATE '45000' "
            "SET MESSAGE_TEXT='shared_source_publish_invalid'; END IF; END"
        )


def downgrade():
    bind = op.get_bind()
    for table in ("shared_weekly_source", "shared_weekly_source_audit"):
        if bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError("shared_weekly_source_nonempty_downgrade_denied")

    op.execute("DROP TRIGGER shared_weekly_source_insert_guard")
    for table in ("shared_weekly_source", "shared_weekly_source_audit"):
        for action in ("update", "delete"):
            op.execute(f"DROP TRIGGER {table}_{action}_deny")
    op.drop_table("shared_weekly_source_audit")
    op.drop_table("shared_weekly_source")
