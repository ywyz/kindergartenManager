"""登录服务集成测试（SQLite 内存库）。"""
import pytest
from unittest.mock import patch

from app.auth.jwt import decode_access_token
from app.auth.password import hash_password
from app.core.exceptions import AuthError
from app.repository.invite_code_repository import create_code
from app.repository.user_repository import create_user
from app.service.auth_service import (
    approve_user,
    change_password,
    create_user_by_admin,
    list_users_for_admin,
    login,
    register_user,
    reset_user_password_by_admin,
    set_user_active_by_admin,
    update_profile_display_name,
)


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


async def test_create_user_by_admin_success(async_session):
    """系统管理员可创建新账号，新账号可登录。"""
    admin = await _make_user(async_session, username="root", role="sys_admin", password="RootPass!")

    created = await create_user_by_admin(
        async_session,
        tenant_id=1,
        admin_user_id=admin.id,
        admin_role="sys_admin",
        username="new_teacher",
        password="TeacherPass!",
        role="teacher",
    )

    assert created.username == "new_teacher"
    assert created.role.value == "teacher"

    token = await login(async_session, tenant_id=1, username="new_teacher", password="TeacherPass!")
    assert token is not None


async def test_create_user_by_admin_forbidden_role(async_session):
    """非系统管理员无权创建账号。"""
    creator = await _make_user(async_session, username="admin", role="teaching_admin", password="AdminPass!")

    with pytest.raises(AuthError):
        await create_user_by_admin(
            async_session,
            tenant_id=1,
            admin_user_id=creator.id,
            admin_role="teaching_admin",
            username="blocked_user",
            password="TeacherPass!",
            role="teacher",
        )


async def test_create_user_by_admin_duplicate_username(async_session):
    """同租户重复用户名创建失败。"""
    admin = await _make_user(async_session, username="root2", role="sys_admin", password="RootPass!")
    await _make_user(async_session, username="dup_name", role="teacher", password="TeacherPass!")

    with pytest.raises(ValueError):
        await create_user_by_admin(
            async_session,
            tenant_id=1,
            admin_user_id=admin.id,
            admin_role="sys_admin",
            username="dup_name",
            password="NewPass123",
            role="teacher",
        )


async def test_create_user_by_admin_invalid_role(async_session):
    """非法角色值应被拒绝。"""
    admin = await _make_user(async_session, username="root3", role="sys_admin", password="RootPass!")

    with pytest.raises(ValueError):
        await create_user_by_admin(
            async_session,
            tenant_id=1,
            admin_user_id=admin.id,
            admin_role="sys_admin",
            username="new_user",
            password="TeacherPass!",
            role="invalid_role",
        )


async def test_set_user_active_by_admin(async_session):
    """系统管理员停用后目标账号无法登录，启用后恢复。"""
    admin = await _make_user(async_session, username="root4", role="sys_admin", password="RootPass!")
    target = await _make_user(async_session, username="target_user", role="teacher", password="UserPass!")

    await set_user_active_by_admin(
        async_session,
        tenant_id=1,
        admin_user_id=admin.id,
        admin_role="sys_admin",
        target_user_id=target.id,
        is_active=False,
    )

    with pytest.raises(AuthError):
        await login(async_session, tenant_id=1, username="target_user", password="UserPass!")

    await set_user_active_by_admin(
        async_session,
        tenant_id=1,
        admin_user_id=admin.id,
        admin_role="sys_admin",
        target_user_id=target.id,
        is_active=True,
    )

    token = await login(async_session, tenant_id=1, username="target_user", password="UserPass!")
    assert token is not None


async def test_reset_user_password_by_admin(async_session):
    """系统管理员重置密码后，旧密码失效，新密码生效。"""
    admin = await _make_user(async_session, username="root5", role="sys_admin", password="RootPass!")
    target = await _make_user(async_session, username="target_user2", role="teacher", password="OldUserPass!")

    await reset_user_password_by_admin(
        async_session,
        tenant_id=1,
        admin_user_id=admin.id,
        admin_role="sys_admin",
        target_user_id=target.id,
        new_password="NewUserPass!",
    )

    with pytest.raises(AuthError):
        await login(async_session, tenant_id=1, username="target_user2", password="OldUserPass!")

    token = await login(async_session, tenant_id=1, username="target_user2", password="NewUserPass!")
    assert token is not None


async def test_list_users_for_admin_with_filter(async_session):
    """系统管理员列表支持筛选并返回总数。"""
    await _make_user(async_session, username="admin_main", role="sys_admin", password="RootPass!")
    await _make_user(async_session, username="teacher_a", role="teacher", password="TeacherPass!")
    await _make_user(async_session, username="teacher_b", role="teacher", password="TeacherPass!")
    await _make_user(async_session, username="manager_a", role="teaching_admin", password="TeacherPass!")

    users, total = await list_users_for_admin(
        async_session,
        tenant_id=1,
        admin_role="sys_admin",
        username_keyword="teacher",
        role="teacher",
        limit=10,
        offset=0,
    )
    assert total == 2
    assert {u.username for u in users} == {"teacher_a", "teacher_b"}


# ── register_user / approve_user / update_profile_display_name 测试 ──────────


async def test_register_user_invalid_invite_code_raises(async_session):
    """无效邀请码注册时抛出业务异常。"""
    from app.core.exceptions import AppError
    with pytest.raises((AppError, AuthError, ValueError)):
        await register_user(
            async_session,
            invite_code="NOTEXIST",
            username="newuser",
            password="Pass1234!",
            display_name="新教师",
        )


async def test_register_user_deactivated_invite_code_raises(async_session):
    """已停用邀请码注册时抛出业务异常。"""
    from app.core.exceptions import AppError
    # 创建一个停用的邀请码
    invite = await create_code(
        async_session,
        tenant_id=1,
        code="DEACTIVATED",
        created_by=None,
    )
    # 先停用
    from app.repository.invite_code_repository import set_code_active
    await set_code_active(async_session, tenant_id=1, code="DEACTIVATED", is_active=False)

    with pytest.raises((AppError, AuthError, ValueError)):
        await register_user(
            async_session,
            invite_code="DEACTIVATED",
            username="newuser",
            password="Pass1234!",
        )


async def test_register_user_valid_invite_code_creates_pending_user(async_session):
    """有效邀请码注册后，创建 is_active=False, role=teacher 的用户，tenant 来自邀请码。"""
    invite = await create_code(
        async_session,
        tenant_id=2,
        code="VALID123",
        created_by=None,
    )

    user = await register_user(
        async_session,
        invite_code="VALID123",
        username="pending_teacher",
        password="Pass1234!",
        display_name="待审核教师",
    )

    assert user.is_active is False
    assert user.role.value == "teacher"
    assert user.tenant_id == 2
    assert user.username == "pending_teacher"


async def test_approve_user_allows_login(async_session):
    """审核通过后，用户可以正常登录。"""
    # 先注册一个待审核用户
    invite = await create_code(
        async_session,
        tenant_id=1,
        code="APPROVE123",
        created_by=None,
    )
    user = await register_user(
        async_session,
        invite_code="APPROVE123",
        username="pending2",
        password="Pass1234!",
    )

    # 未审核时不能登录
    with pytest.raises(AuthError):
        await login(async_session, tenant_id=1, username="pending2", password="Pass1234!")

    # 审核通过
    await approve_user(async_session, tenant_id=1, user_id=user.id)

    # 审核后可以登录
    token = await login(async_session, tenant_id=1, username="pending2", password="Pass1234!")
    assert token is not None


async def test_update_profile_display_name(async_session):
    """更新显示名后，从 DB 取回的用户的 display_name 字段正确。"""
    from app.repository.user_repository import get_user_by_id
    user = await _make_user(async_session, username="disp_user", password="Pass1234!")

    await update_profile_display_name(
        async_session,
        tenant_id=1,
        user_id=user.id,
        display_name="王老师",
    )

    updated = await get_user_by_id(async_session, tenant_id=1, user_id=user.id)
    assert updated is not None
    assert updated.display_name == "王老师"


async def test_create_user_by_admin_writes_audit(async_session):
    """创建账号成功后写入 create_user 审计日志。"""
    admin = await _make_user(async_session, username="root6", role="sys_admin", password="RootPass!")

    with patch("app.service.auth_service.log_audit") as mock_audit:
        await create_user_by_admin(
            async_session,
            tenant_id=1,
            admin_user_id=admin.id,
            admin_role="sys_admin",
            username="audit_teacher",
            password="TeacherPass!",
            role="teacher",
        )

    mock_audit.assert_called_once()
    args, kwargs = mock_audit.call_args
    assert args[0] == "create_user"
    assert kwargs["tenant_id"] == 1
    assert kwargs["user_id"] == admin.id
    assert kwargs["created_username"] == "audit_teacher"


async def test_set_user_active_by_admin_writes_audit(async_session):
    """启停操作成功后写入 set_user_active 审计日志。"""
    admin = await _make_user(async_session, username="root7", role="sys_admin", password="RootPass!")
    target = await _make_user(async_session, username="target_audit", role="teacher", password="UserPass!")

    with patch("app.service.auth_service.log_audit") as mock_audit:
        await set_user_active_by_admin(
            async_session,
            tenant_id=1,
            admin_user_id=admin.id,
            admin_role="sys_admin",
            target_user_id=target.id,
            is_active=False,
        )

    mock_audit.assert_called_once()
    args, kwargs = mock_audit.call_args
    assert args[0] == "set_user_active"
    assert kwargs["target_user_id"] == target.id
    assert kwargs["is_active"] is False


async def test_reset_user_password_by_admin_writes_audit(async_session):
    """重置密码成功后写入 reset_user_password 审计日志。"""
    admin = await _make_user(async_session, username="root8", role="sys_admin", password="RootPass!")
    target = await _make_user(async_session, username="target_pwd", role="teacher", password="UserPass!")

    with patch("app.service.auth_service.log_audit") as mock_audit:
        await reset_user_password_by_admin(
            async_session,
            tenant_id=1,
            admin_user_id=admin.id,
            admin_role="sys_admin",
            target_user_id=target.id,
            new_password="NewUserPass!",
        )

    mock_audit.assert_called_once()
    args, kwargs = mock_audit.call_args
    assert args[0] == "reset_user_password"
    assert kwargs["target_user_id"] == target.id
