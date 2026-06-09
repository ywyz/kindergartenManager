"""InviteCode — 邀请码数据模型。

由 sys_admin 在账号管理页生成邀请码，分发给待注册教师。
邀请码绑定 tenant_id，注册时取得机构归属。
"""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InviteCode(Base):
    __tablename__ = "invite_code"

    __table_args__ = (
        UniqueConstraint("code", name="uq_invite_code"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 生成者 user_id（sys_admin）
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

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
