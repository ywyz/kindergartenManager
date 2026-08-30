"""Append-only evidence for one confirmed daily-plan Patch application."""

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


_JSON_TEXT = Text().with_variant(mysql.LONGTEXT(), "mysql")


class DailyPlanOperationVersion(Base):
    """Complete authoritative snapshot taken immediately before one write."""

    __tablename__ = "daily_plan_operation_version"
    __table_args__ = (
        CheckConstraint(
            "before_revision >= 1",
            name="ck_daily_plan_operation_version_revision_positive",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    daily_plan_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    confirmation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    patch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    patch_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    turn_id: Mapped[str] = mapped_column(String(36), nullable=False)
    before_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    field_paths_json: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_json: Mapped[str] = mapped_column(_JSON_TEXT, nullable=False)
    snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class AgentWriteAudit(Base):
    """Minimal immutable audit evidence for one successful confirmed write."""

    __tablename__ = "agent_write_audit"
    __table_args__ = (
        UniqueConstraint(
            "confirmation_id",
            name="uq_agent_write_audit_confirmation_id",
        ),
        UniqueConstraint(
            "nonce_sha256",
            name="uq_agent_write_audit_nonce_sha256",
        ),
        CheckConstraint(
            "before_revision >= 1",
            name="ck_agent_write_audit_before_revision_positive",
        ),
        CheckConstraint(
            "after_revision = before_revision + 1",
            name="ck_agent_write_audit_revision_step",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    confirmation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    nonce_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    session_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    daily_plan_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    patch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    patch_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    turn_id: Mapped[str] = mapped_column(String(36), nullable=False)
    field_paths_json: Mapped[str] = mapped_column(Text, nullable=False)
    before_version_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    before_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    after_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
