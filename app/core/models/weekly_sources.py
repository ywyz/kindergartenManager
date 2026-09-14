"""Schema for immutable shared-weekly source snapshots and source audits."""

import sqlalchemy as sa

from app.core.database import Base


def _tables(metadata):
    def id_col():
        return sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        )

    def n(name, nullable=False):
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

    source = table(
        "shared_weekly_source",
        id_col(),
        n("tenant_id"),
        n("version_id"),
        n("source_id"),
        n("source_user_id"),
        sa.Column("source_date", sa.Date(), nullable=False),
        n("source_revision"),
        n("mapping_id"),
        n("mapping_revision"),
        sa.Column("source_field", sa.String(32), nullable=False),
        sa.Column("target_path", sa.String(64), nullable=False),
        sa.Column("imported_value", sa.Text(), nullable=False),
        sa.Column("imported_hash", sa.String(64), nullable=False),
        sa.Column("adopted_hash", sa.String(64), nullable=False),
        sa.Column("provenance", sa.String(16), nullable=False),
        created(),
        fk(
            ["tenant_id", "version_id"],
            ["shared_weekly_version.tenant_id", "shared_weekly_version.id"],
        ),
        fk(
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
    )

    source_audit = table(
        "shared_weekly_source_audit",
        id_col(),
        n("tenant_id"),
        n("actor_id"),
        n("plan_id"),
        n("version_id"),
        n("class_instance_id"),
        n("semester_id"),
        n("membership_revision"),
        sa.Column("assignments_json", sa.Text(), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False, unique=True),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(16), nullable=False),
        created(),
        fk(["tenant_id", "actor_id"], ["user.tenant_id", "user.id"]),
        fk(
            ["tenant_id", "plan_id"],
            ["shared_weekly_plan.tenant_id", "shared_weekly_plan.id"],
        ),
        fk(
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
    )

    return source, source_audit


TABLES = {t.name: t for t in _tables(Base.metadata)}
