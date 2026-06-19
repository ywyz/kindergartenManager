"""ListeningRecord — 一对一倾听观察记录主表。

一条记录对应一个幼儿的一次「一对一倾听」观察，覆盖五大领域。
领域级内容（目标/日期/图片/指标/评价/策略）存于 listening_domain 等子表。
同一用户同年月允许多条记录（无 upsert，按 id 区分）。
"""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ListeningRecord(Base):
    __tablename__ = "listening_record"

    __table_args__ = (
        Index("ix_listening_record_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # 主观察年月（历史筛选用；各领域可独立覆盖，见 listening_domain）
    obs_year: Mapped[int] = mapped_column(Integer, nullable=False)
    obs_month: Mapped[int] = mapped_column(Integer, nullable=False)

    # 幼儿信息（单个幼儿）
    child_name: Mapped[str] = mapped_column(String(64), nullable=False)
    adult_count: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)
    child_age: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # 班级信息（冗余存储）
    grade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    term: Mapped[str | None] = mapped_column(String(16), nullable=True)
    class_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    observer: Mapped[str | None] = mapped_column(String(64), nullable=True)

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
