"""课程审议记录数据模型。"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CourseReviewActivity(Base):
    """课程审议记录。

    每条记录保存一次课程审议生成与教师编辑后的结果。班级、年龄段与教师姓名
    采用冗余快照，避免后续系统设置变更影响历史导出。
    """

    __tablename__ = "course_review_activity"

    __table_args__ = (
        Index("ix_course_review_activity_tenant_user", "tenant_id", "user_id"),
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

    activity_name: Mapped[str] = mapped_column(String(128), nullable=False)
    child_count: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    activity_time: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    lesson_plan_original: Mapped[str] = mapped_column(Text, nullable=False)

    activity_goal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    activity_prep: Mapped[str] = mapped_column(Text, nullable=False, default="")
    activity_process: Mapped[str] = mapped_column(Text, nullable=False, default="")

    goal_adjusted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    goal_adjustment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    activity_goal_revised: Mapped[str] = mapped_column(Text, nullable=False, default="")

    prep_adjusted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prep_adjustment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    activity_prep_revised: Mapped[str] = mapped_column(Text, nullable=False, default="")

    process_adjustment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    activity_process_revised: Mapped[str] = mapped_column(Text, nullable=False, default="")
    review_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    revised_lesson_plan: Mapped[str] = mapped_column(Text, nullable=False, default="")

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
