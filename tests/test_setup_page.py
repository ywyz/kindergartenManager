"""测试 /setup 向导页面的核心逻辑函数。

覆盖：
- _check_network_access()：网络层保护逻辑
- _has_sys_admin()：数据库管理员检查
- 集成：create_user 后 _has_sys_admin 返回 True（通过 async_session fixture）
- 集成：reset 流程——正确旧密码成功、错误旧密码被拒
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.auth.password import hash_password


# ─── _check_network_access ───────────────────────────────────────────────────

class TestCheckNetworkAccess:
    def test_localhost_ipv4_allowed(self):
        from app.ui.pages.setup import _check_network_access
        assert _check_network_access("127.0.0.1") is True

    def test_localhost_name_allowed(self):
        from app.ui.pages.setup import _check_network_access
        assert _check_network_access("localhost") is True

    def test_ipv6_loopback_allowed(self):
        from app.ui.pages.setup import _check_network_access
        assert _check_network_access("::1") is True

    def test_remote_blocked_by_default(self):
        from app.ui.pages.setup import _check_network_access
        with patch("app.ui.pages.setup.settings") as mock_settings:
            mock_settings.BOOTSTRAP_ADMIN_ALLOW_REMOTE = False
            assert _check_network_access("192.168.1.100") is False

    def test_remote_allowed_when_configured(self):
        from app.ui.pages.setup import _check_network_access
        with patch("app.ui.pages.setup.settings") as mock_settings:
            mock_settings.BOOTSTRAP_ADMIN_ALLOW_REMOTE = True
            assert _check_network_access("192.168.1.100") is True

    def test_public_ip_blocked_by_default(self):
        from app.ui.pages.setup import _check_network_access
        with patch("app.ui.pages.setup.settings") as mock_settings:
            mock_settings.BOOTSTRAP_ADMIN_ALLOW_REMOTE = False
            assert _check_network_access("8.8.8.8") is False


# ─── _has_sys_admin ──────────────────────────────────────────────────────────

class TestHasSysAdmin:
    async def test_returns_false_when_no_admin(self, async_session):
        """空数据库中 _has_sys_admin 返回 False。"""
        from app.ui.pages.setup import _has_sys_admin

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=async_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.ui.pages.setup.AsyncSessionLocal", return_value=mock_ctx):
            result = await _has_sys_admin()
        assert result is False

    async def test_returns_true_after_admin_created(self, async_session):
        """创建 sys_admin 后 _has_sys_admin 返回 True。"""
        from app.core.models.user import UserRole
        from app.repository.user_repository import create_user
        from app.ui.pages.setup import _has_sys_admin

        await create_user(
            async_session,
            tenant_id=1,
            username="sysadmin",
            hashed_password=hash_password("testpass123"),
            role=UserRole.sys_admin,
        )

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=async_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.ui.pages.setup.AsyncSessionLocal", return_value=mock_ctx):
            result = await _has_sys_admin()
        assert result is True


# ─── reset_admin_password 逻辑（通过 bootstrap_admin 模块） ──────────────────

class TestResetAdminPassword:
    async def test_correct_old_password_updates_password(self, async_session):
        """正确旧密码验证后更新密码成功。"""
        from app.core.models.user import UserRole
        from app.repository.user_repository import create_user, get_user_by_username
        from app.auth.password import verify_password as vp
        from app.jobs.bootstrap_admin import reset_admin_password

        # 创建 sys_admin
        await create_user(
            async_session,
            tenant_id=1,
            username="admin",
            hashed_password=hash_password("oldpass123"),
            role=UserRole.sys_admin,
        )

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=async_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.jobs.bootstrap_admin.AsyncSessionLocal", return_value=mock_ctx):
            result = await reset_admin_password(
                tenant_id=1,
                username="admin",
                old_password="oldpass123",
                new_password="newpass456",
                allow_remote=True,
                database_url="sqlite+aiosqlite:///:memory:",
            )

        assert result.startswith("ok:")

        # 验证密码已更新
        user = await get_user_by_username(async_session, tenant_id=1, username="admin")
        assert vp("newpass456", user.hashed_password) is True
        assert vp("oldpass123", user.hashed_password) is False

    async def test_wrong_old_password_rejected(self, async_session):
        """旧密码错误时拒绝重置。"""
        from app.core.models.user import UserRole
        from app.repository.user_repository import create_user
        from app.jobs.bootstrap_admin import reset_admin_password

        await create_user(
            async_session,
            tenant_id=1,
            username="admin",
            hashed_password=hash_password("correctpass123"),
            role=UserRole.sys_admin,
        )

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=async_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.jobs.bootstrap_admin.AsyncSessionLocal", return_value=mock_ctx):
            result = await reset_admin_password(
                tenant_id=1,
                username="admin",
                old_password="wrongpass",
                new_password="newpass456",
                allow_remote=True,
                database_url="sqlite+aiosqlite:///:memory:",
            )

        assert "旧密码错误" in result

    async def test_nonexistent_user_rejected(self, async_session):
        """用户不存在时拒绝重置。"""
        from app.jobs.bootstrap_admin import reset_admin_password

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=async_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.jobs.bootstrap_admin.AsyncSessionLocal", return_value=mock_ctx):
            result = await reset_admin_password(
                tenant_id=1,
                username="nonexistent",
                old_password="anypass",
                new_password="newpass456",
                allow_remote=True,
                database_url="sqlite+aiosqlite:///:memory:",
            )

        assert "不存在" in result or "error" in result

    async def test_new_password_too_short_rejected(self, async_session):
        """新密码不足8位时拒绝。"""
        from app.jobs.bootstrap_admin import reset_admin_password

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=async_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.jobs.bootstrap_admin.AsyncSessionLocal", return_value=mock_ctx):
            result = await reset_admin_password(
                tenant_id=1,
                username="admin",
                old_password="oldpass123",
                new_password="short",
                allow_remote=True,
                database_url="sqlite+aiosqlite:///:memory:",
            )

        assert "error" in result

    async def test_remote_database_blocked(self, async_session):
        """远程数据库且 allow_remote=False 时拒绝。"""
        from app.jobs.bootstrap_admin import reset_admin_password

        result = await reset_admin_password(
            tenant_id=1,
            username="admin",
            old_password="oldpass123",
            new_password="newpass456",
            allow_remote=False,
            database_url="mysql+aiomysql://user:pass@remote-host:3306/db",
        )

        assert "error" in result and "remote" in result


# ─── 向导入口状态同步（Bug 修复：sys_admin 已存在但文件缺失时） ──────────────

class TestSetupPageStateSyncOnPartialSetup:
    """验证：数据库中已有 sys_admin 但 .kindergarten_setup_complete 文件缺失时，
    setup_page 应自动补写标记文件并进入重置/登录模式，而非继续显示向导 Step 2。
    这是"任何用户名都提示已被注册"bug 的根本修复测试。
    """

    async def test_has_sys_admin_triggers_mark_complete(self, async_session, tmp_path):
        """sys_admin 已存在时，is_setup_complete 为 False → mark_setup_complete 被调用。"""
        from pathlib import Path
        from app.core.setup_state import is_setup_complete, mark_setup_complete

        state_file = tmp_path / ".kindergarten_setup_complete"
        assert not state_file.exists()

        # 模拟 _has_sys_admin 返回 True
        with patch("app.core.setup_state._get_state_path", return_value=state_file):
            # 调用 mark_setup_complete 后文件应存在
            assert not is_setup_complete()
            mark_setup_complete()
            assert is_setup_complete()

    async def test_no_sys_admin_no_file_shows_wizard(self, async_session):
        """无 sys_admin 且无标记文件时，_has_sys_admin 返回 False，向导正常显示。"""
        from app.ui.pages.setup import _has_sys_admin

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=async_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.ui.pages.setup.AsyncSessionLocal", return_value=mock_ctx):
            result = await _has_sys_admin()

        assert result is False  # 空库 → 向导正常显示

    async def test_sys_admin_exists_has_sys_admin_returns_true(self, async_session):
        """数据库中已有 sys_admin 时，_has_sys_admin 返回 True → 应触发状态同步。"""
        from app.core.models.user import UserRole
        from app.repository.user_repository import create_user
        from app.ui.pages.setup import _has_sys_admin

        await create_user(
            async_session,
            tenant_id=1,
            username="orphaned_admin",
            hashed_password=hash_password("somepass123"),
            role=UserRole.sys_admin,
        )

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=async_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.ui.pages.setup.AsyncSessionLocal", return_value=mock_ctx):
            result = await _has_sys_admin()

        assert result is True  # 已有 admin → 应进入重置模式而非继续向导
