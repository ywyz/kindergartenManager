from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ClassConfig(Base):
    __tablename__ = "class_config"

    __table_args__ = (
        Index("ix_class_config_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    grade: Mapped[str] = mapped_column(String(16), nullable=False)       # 小班/中班/大班
    class_name: Mapped[str] = mapped_column(String(32), nullable=False)  # 如"阳光班"
    teacher_name: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 如"张老师"
    indoor_areas: Mapped[str | None] = mapped_column(Text, nullable=True)   # 区域内容描述
    outdoor_content: Mapped[str | None] = mapped_column(Text, nullable=True) # 户外内容描述
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
