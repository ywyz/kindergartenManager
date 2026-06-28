"""导出记录仓库层。"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.export_record import ExportRecord


async def save_export_record(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    daily_plan_id: int | None,
    file_name: str,
    file_path: str,
    observation_id: int | None = None,
    listening_record_id: int | None = None,
    homemade_teaching_id: int | None = None,
    course_review_activity_id: int | None = None,
) -> ExportRecord:
    """写入一条导出记录。

    Args:
        session: 异步数据库会话（调用方负责事务管理）。
        tenant_id: 机构 ID。
        user_id: 用户 ID。
        daily_plan_id: 关联的教案 ID，可为 None。
        file_name: 导出文件名（含扩展名）。
        file_path: 导出文件的绝对路径。
        observation_id: 关联的游戏观察记录 ID，可为 None。
        listening_record_id: 关联的一对一倾听记录 ID，可为 None。
        homemade_teaching_id: 关联的自制教玩具记录 ID，可为 None。
        course_review_activity_id: 关联的课程审议记录 ID，可为 None。

    Returns:
        已持久化的 ExportRecord 对象。
    """
    record = ExportRecord(
        tenant_id=tenant_id,
        user_id=user_id,
        daily_plan_id=daily_plan_id,
        file_name=file_name,
        file_path=file_path,
        observation_id=observation_id,
        listening_record_id=listening_record_id,
        homemade_teaching_id=homemade_teaching_id,
        course_review_activity_id=course_review_activity_id,
    )
    session.add(record)
    await session.flush()
    return record
