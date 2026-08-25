"""启动迁移策略测试。"""
import pytest


def test_run_startup_migrations_fails_closed(monkeypatch):
    """Alembic 失败必须阻断启动，不能降级为未知 schema 的可访问应用。"""
    from alembic import command

    from app.core.startup import run_startup_migrations

    def fail_upgrade(*args, **kwargs):
        raise RuntimeError("injected migration failure")

    monkeypatch.setattr(command, "upgrade", fail_upgrade)

    with pytest.raises(RuntimeError, match="injected migration failure"):
        run_startup_migrations()
