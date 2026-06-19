"""ListeningImage — 一对一倾听绘画图片数据模型。

每个领域 3 张（共 15 张/记录）。复用游戏观察图片的可插拔 BLOB 存储，
新增 domain（所属领域）与 image_description（AI：图上文字或绘画内容描述）。
"""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Index, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ListeningImage(Base):
    __tablename__ = "listening_image"

    __table_args__ = (
        Index("ix_listening_image_record", "record_id"),
        Index("ix_listening_image_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 逻辑外键 → listening_record.id
    record_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 所属领域
    domain: Mapped[str] = mapped_column(String(8), nullable=False)
    # 1~3，控制同领域内图片排序（对应 date_1/2/3）
    image_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # 存储后端标识：mysql_blob / s3 / webdav
    storage_backend: Mapped[str] = mapped_column(
        String(16), nullable=False, default="mysql_blob"
    )

    # BLOB 后端：压缩后图片二进制（MySQL 使用 LONGBLOB variant）
    try:
        from sqlalchemy.dialects.mysql import LONGBLOB as _LONGBLOB
        blob_content: Mapped[bytes | None] = mapped_column(
            LargeBinary().with_variant(_LONGBLOB, "mysql"),
            nullable=True,
        )
    except ImportError:  # pragma: no cover
        blob_content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)  # type: ignore[no-redef]

    # 远端后端：对象键（本期 NULL）
    object_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    mime_type: Mapped[str] = mapped_column(String(32), nullable=False, default="image/jpeg")
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # AI：图上文字识别结果或绘画内容描述
    image_description: Mapped[str | None] = mapped_column(Text, nullable=True)

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
