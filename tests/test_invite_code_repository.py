"""Phase D — 邀请码仓库层测试。"""
import pytest


@pytest.mark.asyncio
async def test_create_and_get_active_invite_code(async_session):
    """create_code 生成可查询；get_active_by_code 命中。"""
    from app.repository.invite_code_repository import create_code, get_active_by_code

    code = await create_code(
        async_session,
        tenant_id=1,
        code="INVITE001",
        note="测试邀请码",
        created_by=1,
    )

    assert code.id is not None
    assert code.is_active is True

    found = await get_active_by_code(async_session, code="INVITE001")
    assert found is not None
    assert found.tenant_id == 1


@pytest.mark.asyncio
async def test_deactivated_code_not_found(async_session):
    """set_code_active(False) 后 get_active_by_code 返回 None。"""
    from app.repository.invite_code_repository import (
        create_code,
        get_active_by_code,
        set_code_active,
    )

    await create_code(async_session, tenant_id=1, code="INVITE002", created_by=1)

    await set_code_active(async_session, tenant_id=1, code="INVITE002", is_active=False)

    result = await get_active_by_code(async_session, code="INVITE002")
    assert result is None


@pytest.mark.asyncio
async def test_list_codes_returns_all(async_session):
    """list_codes 返回该 tenant 下所有邀请码。"""
    from app.repository.invite_code_repository import create_code, list_codes

    for i in range(3):
        await create_code(
            async_session,
            tenant_id=1,
            code=f"CODE_{i:03d}",
            created_by=1,
        )

    codes = await list_codes(async_session, tenant_id=1)
    assert len(codes) >= 3
