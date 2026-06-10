"""邀请码业务逻辑。

由 sys_admin 在账号管理页生成邀请码，分发给待注册教师。

职责：
  - generate_invite_code：生成随机唯一邀请码
  - list_invite_codes：查询租户邀请码列表
  - toggle_invite_code：启用/停用邀请码
"""
from __future__ import annotations

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.models.invite_code import InviteCode
from app.repository.invite_code_repository import (
    create_code,
    list_codes,
    set_code_active,
)

# 邀请码长度（字符数）
_CODE_LENGTH = 12


async def generate_invite_code(
    session: AsyncSession,
    tenant_id: int,
    created_by: int | None = None,
    note: str | None = None,
) -> InviteCode:
    """生成一个随机邀请码并持久化，返回 InviteCode 对象。

    Args:
        session: 异步数据库会话。
        tenant_id: 邀请码绑定的机构 ID。
        created_by: 生成者 user_id（sys_admin）。
        note: 备注说明（可选）。

    Returns:
        新建的 InviteCode 对象（is_active=True）。
    """
    code = secrets.token_urlsafe(_CODE_LENGTH)[:_CODE_LENGTH].upper()

    invite = await create_code(
        session,
        tenant_id=tenant_id,
        code=code,
        note=note,
        created_by=created_by,
    )

    log_audit(
        "invite_code_create",
        tenant_id=tenant_id,
        user_id=created_by,
        code=code,
    )
    return invite


async def list_invite_codes(
    session: AsyncSession,
    tenant_id: int,
) -> list[InviteCode]:
    """查询租户下的所有邀请码（含停用），按创建时间降序。

    Args:
        session: 异步数据库会话。
        tenant_id: 租户 ID。

    Returns:
        InviteCode 对象列表。
    """
    return await list_codes(session, tenant_id=tenant_id)


async def toggle_invite_code(
    session: AsyncSession,
    tenant_id: int,
    code: str,
    is_active: bool,
) -> None:
    """启用或停用邀请码。

    Args:
        session: 异步数据库会话。
        tenant_id: 租户 ID。
        code: 邀请码字符串。
        is_active: True 表示启用，False 表示停用。

    Raises:
        ValueError: 邀请码不存在。
    """
    changed = await set_code_active(
        session,
        tenant_id=tenant_id,
        code=code,
        is_active=is_active,
    )
    if not changed:
        raise ValueError(f"邀请码 {code!r} 不存在")

    log_audit(
        "invite_code_toggle",
        tenant_id=tenant_id,
        code=code,
        is_active=is_active,
    )
