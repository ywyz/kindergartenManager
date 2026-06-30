"""系统管理员初始化脚本测试。"""

from app.jobs.bootstrap_admin import bootstrap_admin
from app.repository.user_repository import get_user_by_username


async def test_bootstrap_admin_disabled(async_session):
    """未启用时应直接跳过。"""
    message = await bootstrap_admin(
        enabled=False,
        tenant_id=1,
        username="sysadmin",
        password="StrongPass!",
        allow_remote=False,
        database_url="sqlite+aiosqlite:///:memory:",
    )
    assert message.startswith("skip:")


async def test_bootstrap_admin_create_and_idempotent(async_session, monkeypatch):
    """首次创建成功，重复执行应跳过。"""
    from app.jobs import bootstrap_admin as module

    class _SessionFactory:
        def __init__(self, session):
            self.session = session

        def __call__(self):
            return self

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(module, "AsyncSessionLocal", _SessionFactory(async_session))

    created = await module.bootstrap_admin(
        enabled=True,
        tenant_id=1,
        username="sysadmin",
        password="StrongPass!",
        allow_remote=False,
        database_url="sqlite+aiosqlite:///:memory:",
    )
    assert created.startswith("ok:")

    user = await get_user_by_username(async_session, tenant_id=1, username="sysadmin")
    assert user is not None
    assert user.role.value == "sys_admin"

    skipped = await module.bootstrap_admin(
        enabled=True,
        tenant_id=1,
        username="sysadmin",
        password="StrongPass!",
        allow_remote=False,
        database_url="sqlite+aiosqlite:///:memory:",
    )
    assert skipped.startswith("skip:")


async def test_bootstrap_admin_password_too_short(async_session, monkeypatch):
    """密码过短应拒绝。"""
    from app.jobs import bootstrap_admin as module

    class _SessionFactory:
        def __init__(self, session):
            self.session = session

        def __call__(self):
            return self

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(module, "AsyncSessionLocal", _SessionFactory(async_session))

    message = await module.bootstrap_admin(
        enabled=True,
        tenant_id=1,
        username="sysadmin",
        password="short",
        allow_remote=False,
        database_url="sqlite+aiosqlite:///:memory:",
    )
    assert message.startswith("error:")


async def test_bootstrap_admin_remote_blocked(async_session, monkeypatch):
    """默认禁止对远程数据库执行初始化。"""
    from app.jobs import bootstrap_admin as module

    class _SessionFactory:
        def __init__(self, session):
            self.session = session

        def __call__(self):
            return self

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(module, "AsyncSessionLocal", _SessionFactory(async_session))

    message = await module.bootstrap_admin(
        enabled=True,
        tenant_id=1,
        username="sysadmin",
        password="StrongPass!",
        allow_remote=False,
        database_url="mysql+aiomysql://user:pwd@47.116.40.89:3306/kindergarten_db",
    )
    assert message.startswith("error:")


def test_resolve_password_from_file(tmp_path):
    """CLI 可从临时文件读取密码，便于安装器安全传入。"""
    from app.jobs.bootstrap_admin import resolve_password_source

    pwd_file = tmp_path / "pwd.txt"
    pwd_file.write_text("StrongPass!\n", encoding="utf-8")

    assert resolve_password_source(
        password=None,
        password_file=str(pwd_file),
        password_stdin=False,
    ) == "StrongPass!"


def test_resolve_password_prefers_explicit_password(tmp_path):
    """显式 password 优先于文件。"""
    from app.jobs.bootstrap_admin import resolve_password_source

    pwd_file = tmp_path / "pwd.txt"
    pwd_file.write_text("FilePass!", encoding="utf-8")

    assert resolve_password_source(
        password="ExplicitPass!",
        password_file=str(pwd_file),
        password_stdin=False,
    ) == "ExplicitPass!"
