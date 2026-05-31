"""导出记录数据模型。

对应数据库表：export_records
记录每次 Word 导出操作的元信息（文件名、路径、关联教案）。
导出记录为只增不改（immutable），因此只有 created_at 无 updated_at。
"""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExportRecord(Base):
    """Word 导出记录表。"""

    __tablename__ = "export_records"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # 关联教案（外键逻辑约束，不做数据库级外键以简化迁移）
    daily_plan_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # 文件信息
    file_name: Mapped[str] = mapped_column(String(256), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
