"""IndicatorCatalog — 一对一倾听指标目录（参考数据，迁移预置）。

按 (grade, term, domain) 组织一级/二级指标及三档（★/★★/★★★）具体标准。
本期预置「小班 / 下学期」五大领域共 30 个二级指标。
sort_order 必须与 Word 模板内指标行序严格一致（用于导出时定位打勾单元格）。
后期可扩展中/大班、上学期等（仅增数据，无需改结构）。
"""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IndicatorCatalog(Base):
    __tablename__ = "indicator_catalog"

    __table_args__ = (
        Index(
            "ix_indicator_catalog_lookup",
            "tenant_id", "grade", "term", "domain", "sort_order",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    grade: Mapped[str] = mapped_column(String(16), nullable=False)
    term: Mapped[str] = mapped_column(String(16), nullable=False)
    domain: Mapped[str] = mapped_column(String(8), nullable=False)

    level1_name: Mapped[str] = mapped_column(String(64), nullable=False)
    level2_name: Mapped[str] = mapped_column(String(512), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    standard_star1: Mapped[str | None] = mapped_column(Text, nullable=True)
    standard_star2: Mapped[str | None] = mapped_column(Text, nullable=True)
    standard_star3: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_stars: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

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
