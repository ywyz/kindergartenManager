"""PromptTemplate — 提示词模板数据模型。

支持以下任务类型，每种类型独立维护版本历史，同一用户同一类型只能有一条 is_active=True 的记录：
- split：教案拆分
- adapt：年龄适配
- morning_exercise：晨间活动
- morning_talk：晨间谈话
- area_game：区域游戏
- outdoor_game：户外游戏
- daily_reflection：一日活动反思
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_template"

    __table_args__ = (
        # 联合索引：按 tenant_id + user_id + task_type 查询激活版本
        Index("ix_prompt_template_tenant_user_task", "tenant_id", "user_id", "task_type"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    task_type: Mapped[str] = mapped_column(
        Enum(
            "split",
            "adapt",
            "morning_exercise",
            "morning_talk",
            "area_game",
            "outdoor_game",
            "daily_reflection",
            "game_observation",
            "one_on_one_listening",
            name="prompt_task_type",
        ),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
