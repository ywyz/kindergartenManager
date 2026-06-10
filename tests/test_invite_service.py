"""tests/test_invite_service.py — 邀请码服务层测试。

测试覆盖：
  1. generate_invite_code 生成随机 code，toggle 启停正常
  2. 两次生成的 code 不同（随机唯一性）
"""

import pytest

from app.service.invite_service import generate_invite_code, toggle_invite_code


async def test_generate_invite_code_creates_usable_code(async_session):
    """generate_invite_code 生成可查询邀请码；toggle 停用后 get_active 返回 None，再次启用后恢复。"""
    from app.repository.invite_code_repository import get_active_by_code

    invite = await generate_invite_code(
        async_session,
        tenant_id=1,
        created_by=42,
        note="测试邀请码",
    )

    assert invite.code
    assert invite.is_active is True
    assert invite.tenant_id == 1
    assert invite.note == "测试邀请码"

    # 可通过 get_active_by_code 查到
    found = await get_active_by_code(async_session, invite.code)
    assert found is not None
    assert found.id == invite.id

    # 停用
    await toggle_invite_code(async_session, tenant_id=1, code=invite.code, is_active=False)
    found_again = await get_active_by_code(async_session, invite.code)
    assert found_again is None

    # 再次启用
    await toggle_invite_code(async_session, tenant_id=1, code=invite.code, is_active=True)
    found_back = await get_active_by_code(async_session, invite.code)
    assert found_back is not None


async def test_generate_invite_code_is_unique(async_session):
    """两次生成的邀请码不同（随机唯一）。"""
    code1 = await generate_invite_code(async_session, tenant_id=1)
    code2 = await generate_invite_code(async_session, tenant_id=1)

    assert code1.code != code2.code
