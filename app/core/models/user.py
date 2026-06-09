import enum
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(str, enum.Enum):
    teacher = "teacher"
    teaching_admin = "teaching_admin"
    sys_admin = "sys_admin"


class User(Base):
    __tablename__ = "user"

    __table_args__ = (
        # 同一 tenant_id 下 username 唯一
        UniqueConstraint("tenant_id", "username", name="uq_user_tenant_username"),
    )

    # BigInteger().with_variant(Integer, "sqlite") 解决 SQLite 测试时自增兼容问题
    # MySQL 生产环境仍使用 BIGINT
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # 显示名（真实姓名），可空；为空时 UI 层回退到 username 展示
    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
