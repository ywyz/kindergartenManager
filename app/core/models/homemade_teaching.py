"""自制教玩具数据模型。"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HomemadeTeachingToy(Base):
    """教师自制教玩具记录。

    每条记录保存一次 AI 生成或教师编辑后的教玩具方案。班级与教师姓名
    采用冗余快照，避免后续设置变更影响历史导出。
    """

    __tablename__ = "homemade_teaching_toy"

    __table_args__ = (
        Index("ix_homemade_teaching_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    grade: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    class_name: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    teacher_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    toy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    materials: Mapped[str] = mapped_column(Text, nullable=False)
    play_methods: Mapped[str] = mapped_column(Text, nullable=False)
    ai_raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)

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
