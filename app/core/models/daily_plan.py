"""每日活动计划数据模型。

对应数据库表：daily_plan
包含教案拆分、年龄适配改写、一日活动生成等所有字段。
"""

from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DailyPlan(Base):
    """每日活动计划表。

    字段说明：
    - plan_date：计划日期（对应学期中的某一天）
    - week_number：第几周（由 date_service 计算）
    - weekday_cn：中文星期（如"周一"）
    - grade / class_name：年级/班级（冗余存储，避免关联查询）
    - activity_goal/prep/key/difficult：教案拆分字段
    - activity_process_original：AI 拆分得到的活动过程原文
    - activity_process_adapted：年龄适配改写后的活动过程
    - morning_activity / indoor_area / outdoor_activity：一日活动生成内容（可为空）
    - morning_talk_topic / morning_talk_questions：晨间谈话（可为空）
    - daily_reflection：一日活动反思（可为空，由教师手工填写）
    """

    __tablename__ = "daily_plan"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # 日期与教学周信息
    plan_date: Mapped[date] = mapped_column(Date, nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    weekday_cn: Mapped[str] = mapped_column(String(4), nullable=False)

    # 班级信息（冗余存储）
    grade: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    class_name: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    # 教案拆分字段
    activity_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_prep: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_difficult: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 活动过程（原文 + 改写文）
    activity_process_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_process_adapted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 一日活动生成内容（可为空，AI 生成后回填）
    morning_activity: Mapped[str | None] = mapped_column(Text, nullable=True)
    indoor_area: Mapped[str | None] = mapped_column(Text, nullable=True)
    outdoor_activity: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 晨间谈话（可为空）
    morning_talk_topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    morning_talk_questions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 一日活动反思（可为空，教师手工填写）
    daily_reflection: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 时间戳
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
