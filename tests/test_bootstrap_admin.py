"""系统管理员初始化脚本测试。"""

import pytest

from app.auth.password import hash_password, verify_password
from app.core.models.user import User, UserRole
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


@pytest.mark.parametrize("operation", ("init", "reset"))
async def test_bootstrap_password_mutations_reject_legacy_sentinel_without_writes(
    async_session,
    monkeypatch,
    operation: str,
) -> None:
    """bootstrap 同样不得把遗留哨兵重新设为可登录口令。"""
    from app.jobs import bootstrap_admin as module

    class _SessionFactory:
        def __call__(self):
            return self

        async def __aenter__(self):
            return async_session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    sentinel = "not-used-single-user-mode"
    admin = User(
        tenant_id=1,
        username="existing-admin",
        hashed_password=hash_password("OriginalAdminPass!"),
        role=UserRole.sys_admin,
        is_active=True,
    )
    async_session.add(admin)
    await async_session.commit()
    original_hash = admin.hashed_password
    monkeypatch.setattr(module, "AsyncSessionLocal", _SessionFactory())

    if operation == "init":
        message = await module.bootstrap_admin(
            enabled=True,
            tenant_id=1,
            username="new-sentinel-admin",
            password=sentinel,
            allow_remote=False,
            database_url="sqlite+aiosqlite:///:memory:",
        )
    else:
        message = await module.reset_admin_password(
            tenant_id=1,
            username=admin.username,
            old_password="OriginalAdminPass!",
            new_password=sentinel,
            allow_remote=False,
            database_url="sqlite+aiosqlite:///:memory:",
        )

    assert message.startswith("error:")
    await async_session.refresh(admin)
    assert admin.hashed_password == original_hash
    assert not verify_password(sentinel, admin.hashed_password)
    assert (
        await get_user_by_username(
            async_session,
            tenant_id=1,
            username="new-sentinel-admin",
        )
        is None
    )


async def test_bootstrap_admin_recovers_legacy_single_user_without_changing_owner_id(
    async_session,
    monkeypatch,
) -> None:
    """显式本地 bootstrap 可替换旧固定密码，同时保留既有数据 owner。"""
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

    legacy = User(
        tenant_id=1,
        username="admin",
        hashed_password=hash_password("not-used-single-user-mode"),
        role=UserRole.sys_admin,
        is_active=True,
    )
    async_session.add(legacy)
    await async_session.commit()
    legacy_id = legacy.id
    monkeypatch.setattr(module, "AsyncSessionLocal", _SessionFactory(async_session))

    message = await module.bootstrap_admin(
        enabled=True,
        tenant_id=1,
        username="sysadmin",
        password="NewStrongPass!",
        allow_remote=False,
        database_url="sqlite+aiosqlite:///:memory:",
    )

    await async_session.refresh(legacy)
    assert message.startswith("ok:")
    assert legacy.id == legacy_id
    assert legacy.username == "admin"
    assert verify_password("NewStrongPass!", legacy.hashed_password)
    assert not verify_password("not-used-single-user-mode", legacy.hashed_password)


async def test_bootstrap_recovers_inactive_legacy_admin_when_requested_name_is_occupied(
    async_session,
    monkeypatch,
) -> None:
    """普通用户重名不能遮蔽另一用户名下的遗留管理员恢复。"""
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

    occupied = User(
        tenant_id=1,
        username="sysadmin",
        hashed_password=hash_password("TeacherPass!"),
        role=UserRole.teacher,
        is_active=True,
    )
    legacy = User(
        tenant_id=1,
        username="admin",
        hashed_password=hash_password("not-used-single-user-mode"),
        role=UserRole.sys_admin,
        is_active=False,
    )
    async_session.add_all([occupied, legacy])
    await async_session.commit()
    monkeypatch.setattr(module, "AsyncSessionLocal", _SessionFactory(async_session))

    message = await module.bootstrap_admin(
        enabled=True,
        tenant_id=1,
        username="sysadmin",
        password="RecoveredPass!",
        allow_remote=False,
        database_url="sqlite+aiosqlite:///:memory:",
    )

    await async_session.refresh(legacy)
    await async_session.refresh(occupied)
    assert message.startswith("ok:")
    assert legacy.username == "admin"
    assert legacy.is_active is True
    assert verify_password("RecoveredPass!", legacy.hashed_password)
    assert occupied.role is UserRole.teacher


async def test_run_init_redacts_unexpected_bootstrap_failure(
    monkeypatch,
    capsys,
) -> None:
    """CLI 边界不得把密码衍生值或异常正文随 traceback 输出。"""
    from app.jobs import bootstrap_admin as module

    password = "TestOnlyStrongPass!"
    leaked_hash = "$argon2id$test-only-sensitive-hash"

    monkeypatch.setattr(module, "run_startup_migrations", lambda **_kwargs: None)
    monkeypatch.setattr(module.settings, "BOOTSTRAP_ADMIN_ENABLED", True)
    monkeypatch.setattr(module.settings, "BOOTSTRAP_ADMIN_USERNAME", "sysadmin")
    monkeypatch.setattr(module.settings, "BOOTSTRAP_ADMIN_PASSWORD", password)

    async def fail_bootstrap(**_kwargs) -> str:
        raise RuntimeError(f"database failed parameters={leaked_hash}")

    monkeypatch.setattr(module, "bootstrap_admin", fail_bootstrap)

    exit_code = await module._run_init()

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "创建失败" in output
    assert password not in output
    assert leaked_hash not in output
    assert "database failed" not in output


async def test_run_init_stops_after_redacted_migration_failure(
    monkeypatch,
    capsys,
) -> None:
    """迁移失败必须 fail closed，且不得输出异常正文。"""
    from app.jobs import bootstrap_admin as module

    leaked_detail = "mysql://user:secret@example.invalid/database"
    bootstrap_called = False

    def fail_migration() -> None:
        raise RuntimeError(leaked_detail)

    async def record_bootstrap_call(**_kwargs) -> str:
        nonlocal bootstrap_called
        bootstrap_called = True
        return "ok: should not run"

    monkeypatch.setattr(
        module,
        "run_startup_migrations",
        lambda **_kwargs: fail_migration(),
    )
    monkeypatch.setattr(module, "bootstrap_admin", record_bootstrap_call)
    monkeypatch.setattr(module.settings, "BOOTSTRAP_ADMIN_ENABLED", True)
    monkeypatch.setattr(module.settings, "BOOTSTRAP_ADMIN_USERNAME", "sysadmin")
    monkeypatch.setattr(
        module.settings,
        "BOOTSTRAP_ADMIN_PASSWORD",
        "TestOnlyStrongPass!",
    )

    exit_code = await module._run_init()

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "迁移失败" in output
    assert leaked_detail not in output
    assert bootstrap_called is False


async def test_run_init_maps_ok_and_skip_results_to_success(
    monkeypatch,
    capsys,
) -> None:
    """创建成功与已存在的幂等跳过都应返回成功状态。"""
    from app.jobs import bootstrap_admin as module

    monkeypatch.setattr(module, "run_startup_migrations", lambda **_kwargs: None)
    monkeypatch.setattr(module.settings, "BOOTSTRAP_ADMIN_ENABLED", True)
    monkeypatch.setattr(module.settings, "BOOTSTRAP_ADMIN_USERNAME", "sysadmin")
    monkeypatch.setattr(
        module.settings,
        "BOOTSTRAP_ADMIN_PASSWORD",
        "TestOnlyStrongPass!",
    )

    for message in ("ok: created", "skip: already exists"):

        async def return_message(**_kwargs) -> str:
            return message

        monkeypatch.setattr(module, "bootstrap_admin", return_message)
        assert await module._run_init() == 0

    capsys.readouterr()


async def test_run_reset_cancel_and_exception_have_nonzero_sanitized_status(
    monkeypatch,
    capsys,
) -> None:
    """重置取消与异常不得被自动化误判为成功或泄露异常正文。"""
    from app.jobs import bootstrap_admin as module

    monkeypatch.setattr(module, "_prompt_str", lambda *_args: "sysadmin")
    prompts = iter(("old-password", "new-password", "different-password"))
    monkeypatch.setattr(module, "_prompt_password", lambda *_args: next(prompts))
    assert await module._run_reset() == 2

    leaked_detail = "database-secret-test-only"
    prompts = iter(("old-password", "new-password", "new-password"))
    monkeypatch.setattr(module, "_prompt_password", lambda *_args: next(prompts))

    async def fail_reset(**_kwargs) -> str:
        raise RuntimeError(leaked_detail)

    monkeypatch.setattr(module, "reset_admin_password", fail_reset)
    assert await module._run_reset() == 1

    output = capsys.readouterr().out
    assert "已取消" in output
    assert "重置失败" in output
    assert leaked_detail not in output
