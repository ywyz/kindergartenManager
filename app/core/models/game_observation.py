"""GameObservation — 游戏观察记录数据模型。

每条记录对应教师的一次游戏观察，包含元数据（日期/环境/人员）
和 AI 生成的四段内容（观察目标/记录/评价/策略）。
同一用户同日期允许多条记录（无 upsert，按 id 区分）。
"""
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Date, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GameObservation(Base):
    __tablename__ = "game_observation"

    __table_args__ = (
        Index("ix_game_observation_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # 基础元数据
    obs_date: Mapped[date] = mapped_column(Date, nullable=False)
    time_range: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 大环境：户外 / 室内 / 公共（应用层校验取值）
    big_env: Mapped[str] = mapped_column(String(8), nullable=False, default="户外")
    game_area: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 班级信息（冗余存储，取自班级配置）
    grade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    class_name: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # 参与人员
    adult_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    child_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    child_names: Mapped[str | None] = mapped_column(String(255), nullable=True)
    child_age: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observer: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # AI 生成内容（保存后可编辑）
    observation_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    observation_record: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
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
