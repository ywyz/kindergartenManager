"""Persistent weekly/monthly plan aggregates for the WMP-9 prerequisite gate.

The WMP service contracts remain persistence-free.  These models are the
production storage boundary: a plan is a stable root pointing at immutable
versions, while the ordered weekly/monthly body rows are immutable children.
The audit table intentionally has no foreign keys to the plan body so a
confirmed DRAFT deletion can retain content-free evidence.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import (
    DDL,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_ID = BigInteger().with_variant(Integer, "sqlite")
_LONG_TEXT = Text().with_variant(mysql.LONGTEXT(), "mysql")

_PLAN_KINDS = ("weekly_activity_plan", "monthly_theme_activity_plan")
_STATUSES = ("draft", "submitted", "returned", "approved", "archived")
_GRANT_ACTIONS = ("read", "review", "export", "archive")
_ITEM_CATEGORIES = (
    "theme_goals",
    "life_habits",
    "play_activities",
    "environment_creation",
    "home_school_cooperation",
    "other",
    "activity_contents",
)


def _in_check(column: str, values: tuple[str, ...], name: str) -> CheckConstraint:
    quoted = ", ".join(f"'{value}'" for value in values)
    return CheckConstraint(f"{column} IN ({quoted})", name=name)


def _dialect_checks(
    sqlite_expression: str, mysql_expression: str, name: str
) -> tuple[CheckConstraint, CheckConstraint]:
    """Keep metadata-created test schemas valid on both supported dialects."""
    return (
        CheckConstraint(sqlite_expression, name=name).ddl_if(dialect="sqlite"),
        CheckConstraint(mysql_expression, name=f"{name}_mysql").ddl_if(dialect="mysql"),
    )


class WeeklyMonthlyPlan(Base):
    """Stable aggregate identity and its current-version CAS pointer."""

    __tablename__ = "weekly_monthly_plan"
    __table_args__ = (
        CheckConstraint(
            "tenant_id >= 1 AND owner_user_id >= 1 AND teacher_id >= 1 AND class_id >= 1",
            name="ck_wmp_root_positive_identity",
        ),
        CheckConstraint(
            "teacher_id = owner_user_id",
            name="ck_wmp_root_teacher_is_owner",
        ),
        CheckConstraint(
            "current_version IS NULL OR current_version >= 1",
            name="ck_wmp_root_current_version_positive",
        ),
        CheckConstraint("revision >= 1", name="ck_wmp_root_revision_positive"),
        CheckConstraint(
            "(deleted_at IS NULL AND deleted_by IS NULL) OR "
            "(deleted_at IS NOT NULL AND deleted_by IS NOT NULL AND current_version IS NULL)",
            name="ck_wmp_root_tombstone_complete",
        ),
        _in_check("plan_kind", _PLAN_KINDS, "ck_wmp_root_plan_kind"),
        UniqueConstraint("tenant_id", "id", name="uq_wmp_root_tenant_id"),
        Index("ix_wmp_root_tenant_owner", "tenant_id", "owner_user_id"),
        Index("ix_wmp_root_tenant_current", "tenant_id", "current_version"),
        Index(
            "ix_wmp_root_tenant_teacher_class", "tenant_id", "teacher_id", "class_id"
        ),
    )

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    teacher_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    class_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    plan_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    current_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class WeeklyMonthlyPlanVersion(Base):
    """Immutable plan version and detached period/scope/body snapshot fields."""

    __tablename__ = "weekly_monthly_plan_version"
    __table_args__ = (
        CheckConstraint(
            "tenant_id >= 1 AND plan_id >= 1 AND version >= 1 AND created_by >= 1",
            name="ck_wmp_version_positive_identity",
        ),
        _in_check("plan_kind", _PLAN_KINDS, "ck_wmp_version_plan_kind"),
        _in_check("status", _STATUSES, "ck_wmp_version_status"),
        CheckConstraint(
            "predecessor_version IS NULL OR predecessor_version >= 1",
            name="ck_wmp_version_predecessor_positive",
        ),
        *_dialect_checks(
            "length(canonical_payload_sha256) = 64 AND "
            "canonical_payload_sha256 NOT GLOB '*[^0-9a-f]*'",
            "CHAR_LENGTH(canonical_payload_sha256) = 64 AND "
            "REGEXP_LIKE(canonical_payload_sha256, '^[0-9a-f]{64}$', 'c')",
            "ck_wmp_version_payload_sha256_hex",
        ),
        *_dialect_checks(
            "length(CAST(COALESCE(grade, '') AS BLOB)) <= 256 AND "
            "length(CAST(COALESCE(class_name, '') AS BLOB)) <= 256 AND "
            "length(CAST(COALESCE(teacher_names_json, '') AS BLOB)) <= 256 AND "
            "length(CAST(COALESCE(caregiver_name, '') AS BLOB)) <= 256 AND "
            "length(CAST(COALESCE(theme_name, '') AS BLOB)) <= 1024 AND "
            "length(CAST(COALESCE(canonical_payload_json, '') AS BLOB)) <= 1048576",
            "OCTET_LENGTH(COALESCE(grade, '')) <= 256 AND "
            "OCTET_LENGTH(COALESCE(class_name, '')) <= 256 AND "
            "OCTET_LENGTH(COALESCE(teacher_names_json, '')) <= 256 AND "
            "OCTET_LENGTH(COALESCE(caregiver_name, '')) <= 256 AND "
            "OCTET_LENGTH(COALESCE(theme_name, '')) <= 1024 AND "
            "OCTET_LENGTH(COALESCE(canonical_payload_json, '')) <= 1048576",
            "ck_wmp_version_snapshot_utf8_bytes",
        ),
        *_dialect_checks(
            "length(CAST(COALESCE(weekly_focus, '') AS BLOB)) <= 32768 AND "
            "length(CAST(COALESCE(environment_creation, '') AS BLOB)) <= 32768 AND "
            "length(CAST(COALESCE(life_habits, '') AS BLOB)) <= 32768 AND "
            "length(CAST(COALESCE(home_school_cooperation, '') AS BLOB)) <= 32768 AND "
            "length(CAST(COALESCE(previous_month_analysis, '') AS BLOB)) <= 32768 AND "
            "length(CAST(COALESCE(monthly_focus, '') AS BLOB)) <= 32768",
            "OCTET_LENGTH(COALESCE(weekly_focus, '')) <= 32768 AND "
            "OCTET_LENGTH(COALESCE(environment_creation, '')) <= 32768 AND "
            "OCTET_LENGTH(COALESCE(life_habits, '')) <= 32768 AND "
            "OCTET_LENGTH(COALESCE(home_school_cooperation, '')) <= 32768 AND "
            "OCTET_LENGTH(COALESCE(previous_month_analysis, '')) <= 32768 AND "
            "OCTET_LENGTH(COALESCE(monthly_focus, '')) <= 32768",
            "ck_wmp_version_narrative_utf8_bytes",
        ),
        UniqueConstraint(
            "tenant_id", "plan_id", "version", name="uq_wmp_version_tenant_plan_version"
        ),
        UniqueConstraint("tenant_id", "id", name="uq_wmp_version_tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id", "plan_id"],
            ["weekly_monthly_plan.tenant_id", "weekly_monthly_plan.id"],
            ondelete="RESTRICT",
            name="fk_wmp_version_tenant_plan",
        ),
        Index("ix_wmp_version_tenant_plan_status", "tenant_id", "plan_id", "status"),
        Index(
            "ix_wmp_version_tenant_kind_week",
            "tenant_id",
            "plan_kind",
            "week_start",
        ),
        Index(
            "ix_wmp_version_tenant_kind_month",
            "tenant_id",
            "plan_kind",
            "year",
            "month",
        ),
    )

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    plan_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    week_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    week_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    week_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    month_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    month_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    grade: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    class_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    teacher_names_json: Mapped[str] = mapped_column(
        _LONG_TEXT, nullable=False, default="[]"
    )
    caregiver_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    theme_name: Mapped[str] = mapped_column(_LONG_TEXT, nullable=False, default="")
    weekly_focus: Mapped[str | None] = mapped_column(_LONG_TEXT, nullable=True)
    environment_creation: Mapped[str | None] = mapped_column(_LONG_TEXT, nullable=True)
    life_habits: Mapped[str | None] = mapped_column(_LONG_TEXT, nullable=True)
    home_school_cooperation: Mapped[str | None] = mapped_column(
        _LONG_TEXT, nullable=True
    )
    previous_month_analysis: Mapped[str | None] = mapped_column(
        _LONG_TEXT, nullable=True
    )
    monthly_focus: Mapped[str | None] = mapped_column(_LONG_TEXT, nullable=True)
    source_daily_plan_ids_json: Mapped[str] = mapped_column(
        _LONG_TEXT, nullable=False, default="[]"
    )
    source_weekly_plan_ids_json: Mapped[str] = mapped_column(
        _LONG_TEXT, nullable=False, default="[]"
    )
    canonical_payload_json: Mapped[str] = mapped_column(
        _LONG_TEXT, nullable=False, default="{}"
    )
    canonical_payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    predecessor_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class WeeklyActivityPlanDay(Base):
    """One of exactly five ordered weekday rows for a weekly version."""

    __tablename__ = "weekly_activity_plan_day"
    __table_args__ = (
        CheckConstraint(
            "tenant_id >= 1 AND version_id >= 1 AND day_index BETWEEN 0 AND 4 "
            "AND weekday BETWEEN 0 AND 4",
            name="ck_wmp_day_identity_order",
        ),
        *_dialect_checks(
            "length(CAST(COALESCE(morning_talk, '') AS BLOB)) <= 16384 AND "
            "length(CAST(COALESCE(collective_activity, '') AS BLOB)) <= 16384 AND "
            "length(CAST(COALESCE(area_game, '') AS BLOB)) <= 16384 AND "
            "length(CAST(COALESCE(outdoor_game, '') AS BLOB)) <= 16384",
            "OCTET_LENGTH(COALESCE(morning_talk, '')) <= 16384 AND "
            "OCTET_LENGTH(COALESCE(collective_activity, '')) <= 16384 AND "
            "OCTET_LENGTH(COALESCE(area_game, '')) <= 16384 AND "
            "OCTET_LENGTH(COALESCE(outdoor_game, '')) <= 16384",
            "ck_wmp_day_body_utf8_bytes",
        ),
        UniqueConstraint("version_id", "day_index", name="uq_wmp_day_version_index"),
        ForeignKeyConstraint(
            ["tenant_id", "version_id"],
            [
                "weekly_monthly_plan_version.tenant_id",
                "weekly_monthly_plan_version.id",
            ],
            ondelete="CASCADE",
            name="fk_wmp_day_tenant_version",
        ),
        Index("ix_wmp_day_tenant_version", "tenant_id", "version_id"),
    )

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    version_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    day_date: Mapped[date] = mapped_column(Date, nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    weekday_cn: Mapped[str] = mapped_column(String(16), nullable=False)
    morning_talk: Mapped[str] = mapped_column(_LONG_TEXT, nullable=False, default="")
    collective_activity: Mapped[str] = mapped_column(
        _LONG_TEXT, nullable=False, default=""
    )
    area_game: Mapped[str] = mapped_column(_LONG_TEXT, nullable=False, default="")
    outdoor_game: Mapped[str] = mapped_column(_LONG_TEXT, nullable=False, default="")


class MonthlyThemeActivityItem(Base):
    """One ordered category item for a monthly version."""

    __tablename__ = "monthly_theme_activity_item"
    __table_args__ = (
        CheckConstraint(
            "tenant_id >= 1 AND version_id >= 1 AND item_index >= 0",
            name="ck_wmp_month_item_identity_order",
        ),
        _in_check("category", _ITEM_CATEGORIES, "ck_wmp_month_item_category"),
        *_dialect_checks(
            "length(CAST(COALESCE(content, '') AS BLOB)) <= 16384",
            "OCTET_LENGTH(COALESCE(content, '')) <= 16384",
            "ck_wmp_month_item_content_utf8_bytes",
        ),
        UniqueConstraint(
            "version_id", "category", "item_index", name="uq_wmp_month_item_order"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "version_id"],
            [
                "weekly_monthly_plan_version.tenant_id",
                "weekly_monthly_plan_version.id",
            ],
            ondelete="CASCADE",
            name="fk_wmp_month_item_tenant_version",
        ),
        Index("ix_wmp_month_item_tenant_version", "tenant_id", "version_id"),
    )

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    version_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(_LONG_TEXT, nullable=False, default="")


class WeeklyMonthlyScopeGrant(Base):
    """A non-wildcard, tenant-scoped teacher/class capability grant."""

    __tablename__ = "weekly_monthly_scope_grant"
    __table_args__ = (
        CheckConstraint(
            "tenant_id >= 1 AND grantee_user_id >= 1 AND teacher_user_id >= 1 AND class_id >= 1",
            name="ck_wmp_grant_positive_identity",
        ),
        _in_check("action", _GRANT_ACTIONS, "ck_wmp_grant_action"),
        CheckConstraint("revision >= 1", name="ck_wmp_grant_revision_positive"),
        CheckConstraint(
            "(is_active = 1 AND revoked_at IS NULL) OR "
            "(is_active = 0 AND revoked_at IS NOT NULL)",
            name="ck_wmp_grant_active_revocation_xor",
        ),
        UniqueConstraint(
            "tenant_id",
            "grantee_user_id",
            "teacher_user_id",
            "class_id",
            "action",
            name="uq_wmp_grant_exact_scope_action",
        ),
        Index(
            "ix_wmp_grant_lookup",
            "tenant_id",
            "grantee_user_id",
            "teacher_user_id",
            "class_id",
            "action",
        ),
    )

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    grantee_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    teacher_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    class_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class WeeklyMonthlyAuditEvent(Base):
    """Content-free append-only business audit identity.

    There are intentionally no FKs to ``weekly_monthly_plan`` or its version;
    logical IDs remain useful after a body purge/tombstone operation.
    """

    __tablename__ = "weekly_monthly_audit_event"
    __table_args__ = (
        CheckConstraint(
            "tenant_id >= 1 AND actor_id >= 1 AND owner_user_id >= 1 AND teacher_id >= 1 "
            "AND class_id >= 1 AND plan_id >= 1 AND plan_version >= 1",
            name="ck_wmp_audit_positive_identity",
        ),
        _in_check("plan_kind", _PLAN_KINDS, "ck_wmp_audit_plan_kind"),
        CheckConstraint(
            "action IN ('read', 'review', 'export', 'archive', 'submit', 'delete')",
            name="ck_wmp_audit_action",
        ),
        CheckConstraint(
            "outcome IN ('success', 'denied')",
            name="ck_wmp_audit_outcome",
        ),
        CheckConstraint(
            "status_before IS NULL OR status_before IN "
            "('draft', 'submitted', 'returned', 'approved', 'archived')",
            name="ck_wmp_audit_status_before",
        ),
        CheckConstraint(
            "status_after IS NULL OR status_after IN "
            "('draft', 'submitted', 'returned', 'approved', 'archived')",
            name="ck_wmp_audit_status_after",
        ),
        *_dialect_checks(
            "length(session_sha256) = 64 AND session_sha256 NOT GLOB '*[^0-9a-f]*'",
            "CHAR_LENGTH(session_sha256) = 64 AND "
            "REGEXP_LIKE(session_sha256, '^[0-9a-f]{64}$', 'c')",
            "ck_wmp_audit_session_sha256_hex",
        ),
        UniqueConstraint("operation_id", name="uq_wmp_audit_operation_id"),
        Index("ix_wmp_audit_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    operation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    actor_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    teacher_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    class_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    plan_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    status_before: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status_after: Mapped[str | None] = mapped_column(String(16), nullable=True)
    grant_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


# ``Base.metadata.create_all`` is used only by isolated tests and local tooling,
# but it must preserve the same append-only audit invariant as Alembic-created
# production schemas. Alembic builds its own Table objects, so these hooks do
# not duplicate migration-owned triggers.
event.listen(
    WeeklyMonthlyAuditEvent.__table__,
    "after_create",
    DDL(
        "CREATE TRIGGER trg_weekly_monthly_audit_event_no_update "
        "BEFORE UPDATE ON weekly_monthly_audit_event FOR EACH ROW "
        "BEGIN SELECT RAISE(ABORT, 'weekly_monthly_audit_event is append-only'); END"
    ).execute_if(dialect="sqlite"),
)
event.listen(
    WeeklyMonthlyAuditEvent.__table__,
    "after_create",
    DDL(
        "CREATE TRIGGER trg_weekly_monthly_audit_event_no_delete "
        "BEFORE DELETE ON weekly_monthly_audit_event FOR EACH ROW "
        "BEGIN SELECT RAISE(ABORT, 'weekly_monthly_audit_event is append-only'); END"
    ).execute_if(dialect="sqlite"),
)
event.listen(
    WeeklyMonthlyAuditEvent.__table__,
    "after_create",
    DDL(
        "CREATE TRIGGER trg_weekly_monthly_audit_event_no_update "
        "BEFORE UPDATE ON weekly_monthly_audit_event FOR EACH ROW "
        "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = "
        "'weekly_monthly_audit_event is append-only'"
    ).execute_if(dialect="mysql"),
)
event.listen(
    WeeklyMonthlyAuditEvent.__table__,
    "after_create",
    DDL(
        "CREATE TRIGGER trg_weekly_monthly_audit_event_no_delete "
        "BEFORE DELETE ON weekly_monthly_audit_event FOR EACH ROW "
        "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = "
        "'weekly_monthly_audit_event is append-only'"
    ).execute_if(dialect="mysql"),
)


__all__ = [
    "MonthlyThemeActivityItem",
    "WeeklyActivityPlanDay",
    "WeeklyMonthlyAuditEvent",
    "WeeklyMonthlyPlan",
    "WeeklyMonthlyPlanVersion",
    "WeeklyMonthlyScopeGrant",
]
