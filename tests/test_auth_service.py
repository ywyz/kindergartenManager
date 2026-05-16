"""登录服务集成测试（SQLite 内存库）。"""
import pytest

from app.auth.jwt import decode_access_token
from app.auth.password import hash_password
from app.core.exceptions import AuthError
from app.repository.user_repository import create_user
from app.service.auth_service import change_password, login


# ── 辅助函数 ──────────────────────────────────────────────────────────────────

async def _make_user(session, *, tenant_id=1, username="alice", password="Pass1234!", role="teacher"):
    """在测试库中插入一个已哈希密码的用户，返回 User 对象。"""
    return await create_user(
        session,
        tenant_id=tenant_id,
        username=username,
        hashed_password=hash_password(password),
        role=role,
    )


# ── login 测试 ────────────────────────────────────────────────────────────────

async def test_login_correct_credentials_returns_token(async_session):
    """正确凭证登录返回可解码的有效 JWT token。"""
    user = await _make_user(async_session)

    token = await login(async_session, tenant_id=1, username="alice", password="Pass1234!")

    payload = decode_access_token(token)
    assert payload["sub"] == str(user.id)
    assert payload["tenant_id"] == 1
    assert payload["role"] == "teacher"


async def test_login_wrong_password_raises_auth_error(async_session):
    """密码错误时抛出 AuthError。"""
    await _make_user(async_session)

    with pytest.raises(AuthError):
        await login(async_session, tenant_id=1, username="alice", password="WrongPass!")


async def test_login_nonexistent_username_raises_auth_error(async_session):
    """不存在的用户名抛出 AuthError（与密码错误相同错误，防止枚举）。"""
    with pytest.raises(AuthError):
        await login(async_session, tenant_id=1, username="nobody", password="AnyPass!")


async def test_login_inactive_user_raises_auth_error(async_session):
    """is_active=False 的账号登录时抛出 AuthError。"""
    user = await _make_user(async_session)
    # 直接修改 is_active 状态
    user.is_active = False
    await async_session.commit()

    with pytest.raises(AuthError):
        await login(async_session, tenant_id=1, username="alice", password="Pass1234!")


async def test_login_wrong_tenant_raises_auth_error(async_session):
    """跨租户登录（正确用户名密码但 tenant_id 不同）抛出 AuthError。"""
    await _make_user(async_session, tenant_id=1)

    with pytest.raises(AuthError):
        await login(async_session, tenant_id=2, username="alice", password="Pass1234!")


# ── change_password 测试 ──────────────────────────────────────────────────────

async def test_change_password_success(async_session):
    """改密后旧密码登录失败，新密码登录成功。"""
    user = await _make_user(async_session, password="OldPass!")

    await change_password(
        async_session,
        tenant_id=1,
        user_id=user.id,
        old_password="OldPass!",
        new_password="NewPass!",
    )

    # 旧密码登录失败
    with pytest.raises(AuthError):
        await login(async_session, tenant_id=1, username="alice", password="OldPass!")

    # 新密码登录成功
    token = await login(async_session, tenant_id=1, username="alice", password="NewPass!")
    assert token is not None


async def test_change_password_wrong_old_password_raises(async_session):
    """旧密码错误时抛出 AuthError，密码不被修改。"""
    user = await _make_user(async_session, password="OldPass!")

    with pytest.raises(AuthError):
        await change_password(
            async_session,
            tenant_id=1,
            user_id=user.id,
            old_password="WrongOld!",
            new_password="NewPass!",
        )

    # 原密码仍可正常登录
    token = await login(async_session, tenant_id=1, username="alice", password="OldPass!")
    assert token is not None
