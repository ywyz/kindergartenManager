"""prompt_repository — 提示词模板数据访问层。

支持提示词多版本管理：保存新版本、回滚、查询激活版本、列出所有版本。

约束：
- 同一用户同一 task_type 只能有一条 is_active=True 的记录。
- version 在同一用户同一 task_type 下单调递增（从 1 开始）。
- 所有查询携带 tenant_id + user_id 过滤，确保租户隔离。
"""

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.prompt_template import PromptTemplate


async def get_active_prompt(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    task_type: str,
) -> PromptTemplate | None:
    """查询该用户指定任务类型的当前激活提示词。

    Args:
        session: 异步数据库会话。
        tenant_id: 租户 ID。
        user_id: 用户 ID。
        task_type: 任务类型（"split" / "adapt" / "generate"）。

    Returns:
        激活的 PromptTemplate 记录，若不存在则返回 None。
    """
    result = await session.execute(
        select(PromptTemplate).where(
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.user_id == user_id,
            PromptTemplate.task_type == task_type,
            PromptTemplate.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def save_new_version(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    task_type: str,
    content: str,
) -> PromptTemplate:
    """保存新版本提示词，自动递增版本号并将旧激活记录设为 inactive。

    Args:
        session: 异步数据库会话。
        tenant_id: 租户 ID。
        user_id: 用户 ID。
        task_type: 任务类型（"split" / "adapt" / "generate"）。
        content: 提示词正文。

    Returns:
        新建的 PromptTemplate 记录，is_active=True，version 自动递增。
    """
    now = datetime.now(timezone.utc)

    # 将同用户同任务类型的当前 active 记录设为 inactive
    await session.execute(
        update(PromptTemplate)
        .where(
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.user_id == user_id,
            PromptTemplate.task_type == task_type,
            PromptTemplate.is_active.is_(True),
        )
        .values(is_active=False, updated_at=now)
    )

    # 计算下一个版本号
    max_version_result = await session.execute(
        select(func.max(PromptTemplate.version)).where(
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.user_id == user_id,
            PromptTemplate.task_type == task_type,
        )
    )
    max_version = max_version_result.scalar_one_or_none() or 0
    next_version = max_version + 1

    new_prompt = PromptTemplate(
        tenant_id=tenant_id,
        user_id=user_id,
        task_type=task_type,
        version=next_version,
        content=content,
        is_active=True,
    )
    session.add(new_prompt)
    await session.commit()
    await session.refresh(new_prompt)
    return new_prompt


async def rollback_to_version(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    task_type: str,
    version: int,
) -> PromptTemplate:
    """将指定版本设为激活，其余版本设为 inactive。

    Args:
        session: 异步数据库会话。
        tenant_id: 租户 ID。
        user_id: 用户 ID。
        task_type: 任务类型。
        version: 目标版本号。

    Returns:
        目标版本的 PromptTemplate 记录（is_active=True）。

    Raises:
        ValueError: 目标版本不存在。
    """
    now = datetime.now(timezone.utc)

    # 先确认目标版本存在
    target_result = await session.execute(
        select(PromptTemplate).where(
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.user_id == user_id,
            PromptTemplate.task_type == task_type,
            PromptTemplate.version == version,
        )
    )
    target = target_result.scalar_one_or_none()
    if target is None:
        raise ValueError(
            f"版本 {version} 不存在（tenant_id={tenant_id}, user_id={user_id}, task_type={task_type}）"
        )

    # 将所有记录设为 inactive
    await session.execute(
        update(PromptTemplate)
        .where(
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.user_id == user_id,
            PromptTemplate.task_type == task_type,
        )
        .values(is_active=False, updated_at=now)
    )

    # 目标版本设为 active
    await session.execute(
        update(PromptTemplate)
        .where(
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.user_id == user_id,
            PromptTemplate.task_type == task_type,
            PromptTemplate.version == version,
        )
        .values(is_active=True, updated_at=now)
    )

    await session.commit()
    await session.refresh(target)
    return target


async def list_versions(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    task_type: str,
) -> list[PromptTemplate]:
    """返回指定任务类型的所有版本，按版本号降序排列。

    Args:
        session: 异步数据库会话。
        tenant_id: 租户 ID。
        user_id: 用户 ID。
        task_type: 任务类型。

    Returns:
        PromptTemplate 列表，版本号从大到小排列。
    """
    result = await session.execute(
        select(PromptTemplate)
        .where(
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.user_id == user_id,
            PromptTemplate.task_type == task_type,
        )
        .order_by(PromptTemplate.version.desc())
    )
    return list(result.scalars().all())
