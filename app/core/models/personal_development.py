"""PersonalDevelopmentRecord — 幼儿个体发展档案主表。

每条记录对应一个幼儿的一份发展档案，同一幼儿同一学期只能有一份。
关联 semester_config，体检数据只存最新值，支持从一对一倾听/游戏观察自动提取数据。

模板结构（templates/personal.docx）：
  Row 0: 姓名 / 性别 / 出生年月 / 入园时间
  Row 1: 身高 / 体重 / 胸围 / 血色素 / 视力
  Row 2: 幼儿发展情况
  Row 3: 采取措施
  Row 4: 家园联系
  Row 5: 突出表现
  Row 6: 进步情况
  Row 7: 保教老师寄语
"""
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PersonalDevelopmentRecord(Base):
    __tablename__ = "personal_development_record"

    __table_args__ = (
        Index("ix_personal_development_tenant_user", "tenant_id", "user_id"),
        UniqueConstraint("tenant_id", "child_name", "semester_id", name="uq_personal_child_semester"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    semester_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    child_name: Mapped[str] = mapped_column(String(64), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(8), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    enrollment_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    chest_circumference: Mapped[float | None] = mapped_column(Float, nullable=True)
    hemoglobin: Mapped[float | None] = mapped_column(Float, nullable=True)
    vision_left: Mapped[float | None] = mapped_column(Float, nullable=True)
    vision_right: Mapped[float | None] = mapped_column(Float, nullable=True)

    grade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    class_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    observer: Mapped[str | None] = mapped_column(String(64), nullable=True)

    development_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    measures_taken: Mapped[str | None] = mapped_column(Text, nullable=True)
    home_contact: Mapped[str | None] = mapped_column(Text, nullable=True)
    outstanding_performance: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_message: Mapped[str | None] = mapped_column(Text, nullable=True)

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