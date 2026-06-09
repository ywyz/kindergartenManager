"""GameObservationImage — 游戏观察图片数据模型。

可插拔存储：本期实现 MySQL BLOB 后端（blob_content 存压缩后二进制），
预留 S3 / WebDAV 后端（object_key 字段存对象键，blob_content 为 NULL）。
"""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Index, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GameObservationImage(Base):
    __tablename__ = "game_observation_image"

    __table_args__ = (
        Index("ix_game_obs_image_obs_id", "observation_id"),
        Index("ix_game_obs_image_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 逻辑外键（不建数据库级外键，简化迁移）
    observation_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 1~3，控制同一观察下的图片排序
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
