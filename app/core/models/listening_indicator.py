"""ListeningIndicatorResult — 一对一倾听二级指标达成结果。

每条 listening_record 的每个领域每个二级指标一条，记录达成星级（1~3）。
catalog_id 逻辑外键指向 indicator_catalog（指标定义）。
"""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ListeningIndicatorResult(Base):
    __tablename__ = "listening_indicator_result"

    __table_args__ = (
        Index("ix_listening_indicator_record", "record_id"),
        Index("ix_listening_indicator_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 逻辑外键 → listening_record.id
    record_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 所属领域
    domain: Mapped[str] = mapped_column(String(8), nullable=False)
    # 逻辑外键 → indicator_catalog.id
    catalog_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 达成星级 1~3（默认 3）
    stars: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
