"""AiApiKey — AI 接口 Key 数据模型。

安全约束：
- `api_key_encrypted` 字段仅存密文，明文禁止入库、禁止写入日志。
- 加解密统一由 app.core.crypto 模块处理。
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AiApiKey(Base):
    __tablename__ = "ai_api_key"

    __table_args__ = (
        # 联合索引：按 tenant_id + user_id 查询激活 Key
        Index("ix_ai_api_key_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    api_base_url: Mapped[str] = mapped_column(String(256), nullable=False)
    # 仅存密文；明文禁止出现在此字段
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
