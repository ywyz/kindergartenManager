"""Add the WMP-9 production-prerequisite aggregate and authorization tables.

Revision ID: 3c9f4b2a7d1e
Revises: 2b7f3d5e9c8a
Create Date: 2026-09-07 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "3c9f4b2a7d1e"
down_revision: str | Sequence[str] | None = "2b7f3d5e9c8a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
_LONG_TEXT = sa.Text().with_variant(mysql.LONGTEXT(), "mysql")
_PLAN_KINDS = "'weekly_activity_plan', 'monthly_theme_activity_plan'"
_STATUSES = "'draft', 'submitted', 'returned', 'approved', 'archived'"
_GRANT_ACTIONS = "'read', 'review', 'export', 'archive'"
_ITEM_CATEGORIES = (
    "'theme_goals', 'life_habits', 'play_activities', "
    "'environment_creation', 'home_school_cooperation', 'other', 'activity_contents'"
)


def _byte_length(column: str, maximum: int) -> str:
    """Return a SQLite/MySQL equivalent UTF-8 byte-length expression."""
    if op.get_bind().dialect.name == "mysql":
        return f"OCTET_LENGTH(COALESCE({column}, '')) <= {maximum}"
    return f"length(CAST(COALESCE({column}, '') AS BLOB)) <= {maximum}"


def _sha256_check(column: str) -> str:
    """Return a strict lowercase hexadecimal SHA-256 predicate per dialect."""

    if op.get_bind().dialect.name == "mysql":
        # Match type ``c`` avoids a case-insensitive connection collation
        # accepting A-F without mixing the binary and utf8mb4 character sets.
        return (
            f"CHAR_LENGTH({column}) = 64 AND "
            f"REGEXP_LIKE({column}, '^[0-9a-f]{{64}}$', 'c')"
        )
    if op.get_bind().dialect.name == "sqlite":
        return f"length({column}) = 64 AND {column} NOT GLOB '*[^0-9a-f]*'"
    raise RuntimeError("unsupported database dialect for WMP-9 digest checks")


def _create_trigger(table_name: str, action: str, condition: str | None = None) -> None:
    dialect_name = op.get_bind().dialect.name
    trigger_name = f"trg_{table_name}_no_{action.casefold()}"
    if dialect_name == "sqlite":
        when_clause = f"\n                WHEN NOT ({condition})" if condition else ""
        op.execute(
            f"""
            CREATE TRIGGER {trigger_name}
            BEFORE {action} ON {table_name}
            FOR EACH ROW{when_clause}
            BEGIN
                SELECT RAISE(ABORT, '{table_name} mutation is protected');
            END
            """
        )
        return
    if dialect_name == "mysql":
        if condition is None:
            op.execute(
                f"""
                CREATE TRIGGER {trigger_name}
                BEFORE {action} ON {table_name}
                FOR EACH ROW
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = '{table_name} mutation is protected'
                """
            )
        else:
            op.execute(
                f"""
                CREATE TRIGGER {trigger_name}
                BEFORE {action} ON {table_name}
                FOR EACH ROW
                BEGIN
                    IF NOT ({condition}) THEN
                        SIGNAL SQLSTATE '45000'
                        SET MESSAGE_TEXT = '{table_name} mutation is protected';
                    END IF;
                END
                """
            )
        return
    raise RuntimeError("unsupported database dialect for WMP-9 triggers")


def _drop_triggers(table_name: str) -> None:
    dialect_name = op.get_bind().dialect.name
    if dialect_name not in {"sqlite", "mysql"}:
        raise RuntimeError("unsupported database dialect for WMP-9 triggers")
    for action in ("UPDATE", "DELETE"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_{action.casefold()}")


def upgrade() -> None:
    byte_checks = [
        _byte_length("grade", 256),
        _byte_length("class_name", 256),
        _byte_length("teacher_names_json", 256),
        _byte_length("caregiver_name", 256),
        _byte_length("theme_name", 1024),
        _byte_length("canonical_payload_json", 1_048_576),
        _byte_length("weekly_focus", 32_768),
        _byte_length("environment_creation", 32_768),
        _byte_length("life_habits", 32_768),
        _byte_length("home_school_cooperation", 32_768),
        _byte_length("previous_month_analysis", 32_768),
        _byte_length("monthly_focus", 32_768),
    ]
    day_byte_checks = [
        _byte_length("morning_talk", 16_384),
        _byte_length("collective_activity", 16_384),
        _byte_length("area_game", 16_384),
        _byte_length("outdoor_game", 16_384),
    ]
    item_byte_checks = [_byte_length("content", 16_384)]

    op.create_table(
        "weekly_monthly_plan",
        sa.Column("id", _ID, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("teacher_id", sa.BigInteger(), nullable=False),
        sa.Column("class_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_kind", sa.String(length=64), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=True),
        sa.Column(
            "revision", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "tenant_id >= 1 AND owner_user_id >= 1 AND teacher_id >= 1 AND class_id >= 1",
            name="ck_wmp_root_positive_identity",
        ),
        sa.CheckConstraint(
            "teacher_id = owner_user_id", name="ck_wmp_root_teacher_is_owner"
        ),
        sa.CheckConstraint(
            "current_version IS NULL OR current_version >= 1",
            name="ck_wmp_root_current_version_positive",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_wmp_root_revision_positive"),
        sa.CheckConstraint(
            "(deleted_at IS NULL AND deleted_by IS NULL) OR "
            "(deleted_at IS NOT NULL AND deleted_by IS NOT NULL AND current_version IS NULL)",
            name="ck_wmp_root_tombstone_complete",
        ),
        sa.CheckConstraint(
            f"plan_kind IN ({_PLAN_KINDS})", name="ck_wmp_root_plan_kind"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_wmp_root_tenant_id"),
    )
    op.create_index(
        "ix_wmp_root_tenant_owner",
        "weekly_monthly_plan",
        ["tenant_id", "owner_user_id"],
    )
    op.create_index(
        "ix_wmp_root_tenant_current",
        "weekly_monthly_plan",
        ["tenant_id", "current_version"],
    )
    op.create_index(
        "ix_wmp_root_tenant_teacher_class",
        "weekly_monthly_plan",
        ["tenant_id", "teacher_id", "class_id"],
    )

    op.create_table(
        "weekly_monthly_plan_version",
        sa.Column("id", _ID, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "plan_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("plan_kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=True),
        sa.Column("week_end", sa.Date(), nullable=True),
        sa.Column("week_number", sa.Integer(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("month", sa.Integer(), nullable=True),
        sa.Column("month_start", sa.Date(), nullable=True),
        sa.Column("month_end", sa.Date(), nullable=True),
        sa.Column("grade", sa.String(length=256), nullable=False),
        sa.Column("class_name", sa.String(length=256), nullable=False),
        sa.Column("teacher_names_json", _LONG_TEXT, nullable=False),
        sa.Column("caregiver_name", sa.String(length=256), nullable=True),
        sa.Column("theme_name", _LONG_TEXT, nullable=False),
        sa.Column("weekly_focus", _LONG_TEXT, nullable=True),
        sa.Column("environment_creation", _LONG_TEXT, nullable=True),
        sa.Column("life_habits", _LONG_TEXT, nullable=True),
        sa.Column("home_school_cooperation", _LONG_TEXT, nullable=True),
        sa.Column("previous_month_analysis", _LONG_TEXT, nullable=True),
        sa.Column("monthly_focus", _LONG_TEXT, nullable=True),
        sa.Column("source_daily_plan_ids_json", _LONG_TEXT, nullable=False),
        sa.Column("source_weekly_plan_ids_json", _LONG_TEXT, nullable=False),
        sa.Column("canonical_payload_json", _LONG_TEXT, nullable=False),
        sa.Column("canonical_payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("predecessor_version", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "tenant_id >= 1 AND plan_id >= 1 AND version >= 1 AND created_by >= 1",
            name="ck_wmp_version_positive_identity",
        ),
        sa.CheckConstraint(
            f"plan_kind IN ({_PLAN_KINDS})", name="ck_wmp_version_plan_kind"
        ),
        sa.CheckConstraint(f"status IN ({_STATUSES})", name="ck_wmp_version_status"),
        sa.CheckConstraint(
            "predecessor_version IS NULL OR predecessor_version >= 1",
            name="ck_wmp_version_predecessor_positive",
        ),
        sa.CheckConstraint(
            _sha256_check("canonical_payload_sha256"),
            name="ck_wmp_version_payload_sha256_hex",
        ),
        *[
            sa.CheckConstraint(expression, name=f"ck_wmp_version_bytes_{index}")
            for index, expression in enumerate(byte_checks)
        ],
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "plan_id", "version", name="uq_wmp_version_tenant_plan_version"
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_wmp_version_tenant_id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "plan_id"],
            ["weekly_monthly_plan.tenant_id", "weekly_monthly_plan.id"],
            ondelete="RESTRICT",
            name="fk_wmp_version_tenant_plan",
        ),
    )
    op.create_index(
        "ix_wmp_version_tenant_plan_status",
        "weekly_monthly_plan_version",
        ["tenant_id", "plan_id", "status"],
    )
    op.create_index(
        "ix_wmp_version_tenant_kind_week",
        "weekly_monthly_plan_version",
        ["tenant_id", "plan_kind", "week_start"],
    )
    op.create_index(
        "ix_wmp_version_tenant_kind_month",
        "weekly_monthly_plan_version",
        ["tenant_id", "plan_kind", "year", "month"],
    )

    op.create_table(
        "weekly_activity_plan_day",
        sa.Column("id", _ID, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "version_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column("day_index", sa.Integer(), nullable=False),
        sa.Column("day_date", sa.Date(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("weekday_cn", sa.String(length=16), nullable=False),
        sa.Column("morning_talk", _LONG_TEXT, nullable=False),
        sa.Column("collective_activity", _LONG_TEXT, nullable=False),
        sa.Column("area_game", _LONG_TEXT, nullable=False),
        sa.Column("outdoor_game", _LONG_TEXT, nullable=False),
        sa.CheckConstraint(
            "tenant_id >= 1 AND version_id >= 1 AND day_index BETWEEN 0 AND 4 AND weekday BETWEEN 0 AND 4",
            name="ck_wmp_day_identity_order",
        ),
        *[
            sa.CheckConstraint(expression, name=f"ck_wmp_day_bytes_{index}")
            for index, expression in enumerate(day_byte_checks)
        ],
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", "day_index", name="uq_wmp_day_version_index"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "version_id"],
            [
                "weekly_monthly_plan_version.tenant_id",
                "weekly_monthly_plan_version.id",
            ],
            ondelete="CASCADE",
            name="fk_wmp_day_tenant_version",
        ),
    )
    op.create_index(
        "ix_wmp_day_tenant_version",
        "weekly_activity_plan_day",
        ["tenant_id", "version_id"],
    )

    op.create_table(
        "monthly_theme_activity_item",
        sa.Column("id", _ID, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "version_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("content", _LONG_TEXT, nullable=False),
        sa.CheckConstraint(
            "tenant_id >= 1 AND version_id >= 1 AND item_index >= 0",
            name="ck_wmp_month_item_identity_order",
        ),
        sa.CheckConstraint(
            f"category IN ({_ITEM_CATEGORIES})", name="ck_wmp_month_item_category"
        ),
        *[
            sa.CheckConstraint(expression, name=f"ck_wmp_month_item_bytes_{index}")
            for index, expression in enumerate(item_byte_checks)
        ],
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "version_id", "category", "item_index", name="uq_wmp_month_item_order"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "version_id"],
            [
                "weekly_monthly_plan_version.tenant_id",
                "weekly_monthly_plan_version.id",
            ],
            ondelete="CASCADE",
            name="fk_wmp_month_item_tenant_version",
        ),
    )
    op.create_index(
        "ix_wmp_month_item_tenant_version",
        "monthly_theme_activity_item",
        ["tenant_id", "version_id"],
    )

    op.create_table(
        "weekly_monthly_scope_grant",
        sa.Column("id", _ID, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("grantee_user_id", sa.BigInteger(), nullable=False),
        sa.Column("teacher_user_id", sa.BigInteger(), nullable=False),
        sa.Column("class_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "tenant_id >= 1 AND grantee_user_id >= 1 AND teacher_user_id >= 1 AND class_id >= 1",
            name="ck_wmp_grant_positive_identity",
        ),
        sa.CheckConstraint(f"action IN ({_GRANT_ACTIONS})", name="ck_wmp_grant_action"),
        sa.CheckConstraint("revision >= 1", name="ck_wmp_grant_revision_positive"),
        sa.CheckConstraint(
            "(is_active = 1 AND revoked_at IS NULL) OR "
            "(is_active = 0 AND revoked_at IS NOT NULL)",
            name="ck_wmp_grant_active_revocation_xor",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "grantee_user_id",
            "teacher_user_id",
            "class_id",
            "action",
            name="uq_wmp_grant_exact_scope_action",
        ),
    )
    op.create_index(
        "ix_wmp_grant_lookup",
        "weekly_monthly_scope_grant",
        ["tenant_id", "grantee_user_id", "teacher_user_id", "class_id", "action"],
    )

    op.create_table(
        "weekly_monthly_audit_event",
        sa.Column("id", _ID, autoincrement=True, nullable=False),
        sa.Column("operation_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("teacher_id", sa.BigInteger(), nullable=False),
        sa.Column("class_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_kind", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("status_before", sa.String(length=16), nullable=True),
        sa.Column("status_after", sa.String(length=16), nullable=True),
        sa.Column("grant_revision", sa.Integer(), nullable=True),
        sa.Column("session_sha256", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "tenant_id >= 1 AND actor_id >= 1 AND owner_user_id >= 1 AND teacher_id >= 1 "
            "AND class_id >= 1 AND plan_id >= 1 AND plan_version >= 1",
            name="ck_wmp_audit_positive_identity",
        ),
        sa.CheckConstraint(
            f"plan_kind IN ({_PLAN_KINDS})", name="ck_wmp_audit_plan_kind"
        ),
        sa.CheckConstraint(
            "action IN ('read', 'review', 'export', 'archive', 'submit', 'delete')",
            name="ck_wmp_audit_action",
        ),
        sa.CheckConstraint(
            "outcome IN ('success', 'denied')", name="ck_wmp_audit_outcome"
        ),
        sa.CheckConstraint(
            "status_before IS NULL OR status_before IN "
            "('draft', 'submitted', 'returned', 'approved', 'archived')",
            name="ck_wmp_audit_status_before",
        ),
        sa.CheckConstraint(
            "status_after IS NULL OR status_after IN "
            "('draft', 'submitted', 'returned', 'approved', 'archived')",
            name="ck_wmp_audit_status_after",
        ),
        sa.CheckConstraint(
            _sha256_check("session_sha256"),
            name="ck_wmp_audit_session_sha256_hex",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("operation_id", name="uq_wmp_audit_operation_id"),
    )
    op.create_index(
        "ix_wmp_audit_tenant_created",
        "weekly_monthly_audit_event",
        ["tenant_id", "created_at"],
    )

    # Versions and body rows are immutable except for the one repository-owned
    # current-DRAFT purge.  The audit stream remains unconditionally
    # append-only.
    _create_trigger("weekly_monthly_plan_version", "UPDATE")
    _create_trigger(
        "weekly_monthly_plan_version",
        "DELETE",
        "OLD.status = 'draft' AND EXISTS ("
        "SELECT 1 FROM weekly_monthly_plan p "
        "WHERE p.tenant_id = OLD.tenant_id AND p.id = OLD.plan_id "
        "AND p.current_version IS NULL AND p.deleted_at IS NOT NULL "
        "AND p.deleted_by IS NOT NULL)",
    )
    for table_name in ("weekly_activity_plan_day", "monthly_theme_activity_item"):
        _create_trigger(table_name, "UPDATE")
        _create_trigger(
            table_name,
            "DELETE",
            "EXISTS ("
            "SELECT 1 FROM weekly_monthly_plan_version v "
            "JOIN weekly_monthly_plan p ON p.tenant_id = v.tenant_id "
            "AND p.id = v.plan_id "
            "WHERE v.tenant_id = OLD.tenant_id AND v.id = OLD.version_id "
            "AND v.status = 'draft' AND p.current_version IS NULL "
            "AND p.deleted_at IS NOT NULL AND p.deleted_by IS NOT NULL)",
        )
    _create_trigger("weekly_monthly_audit_event", "UPDATE")
    _create_trigger("weekly_monthly_audit_event", "DELETE")


def downgrade() -> None:
    for table_name in (
        "weekly_monthly_audit_event",
        "monthly_theme_activity_item",
        "weekly_activity_plan_day",
        "weekly_monthly_plan_version",
    ):
        _drop_triggers(table_name)
    op.drop_table("weekly_monthly_audit_event")
    op.drop_table("weekly_monthly_scope_grant")
    op.drop_table("monthly_theme_activity_item")
    op.drop_table("weekly_activity_plan_day")
    op.drop_table("weekly_monthly_plan_version")
    op.drop_table("weekly_monthly_plan")
