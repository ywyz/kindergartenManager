"""ListeningDomain — 一对一倾听单领域内容。

每条 listening_record 对应 5 条本表（健康/语言/社会/艺术/科学各一）。
年月与 3 个工作日均为领域级独立字段；目标/综合评价/支持策略为 AI 生成。
"""
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ListeningDomain(Base):
    __tablename__ = "listening_domain"

    __table_args__ = (
        Index("ix_listening_domain_record", "record_id"),
        Index("ix_listening_domain_tenant_user", "tenant_id", "user_id"),
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
    # 健康 / 语言 / 社会 / 艺术 / 科学
    domain: Mapped[str] = mapped_column(String(8), nullable=False)

    # 领域级独立观察年月
    obs_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    obs_month: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 三个工作日（对应 3 张绘画 image_index 1/2/3）
    date_1: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_2: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_3: Mapped[date | None] = mapped_column(Date, nullable=True)

    # AI 生成内容（保存后可编辑）
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation: Mapped[str | None] = mapped_column(Text, nullable=True)
    support_strategy: Mapped[str | None] = mapped_column(Text, nullable=True)

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
