"""显式迁移执行器测试。"""

import pytest


def test_run_migrations_fails_closed(monkeypatch):
    """Alembic 失败必须阻断启动，不能降级为未知 schema 的可访问应用。"""
    from alembic import command

    from app.core.startup import run_migrations

    def fail_upgrade(*args, **kwargs):
        raise RuntimeError("injected migration failure")

    monkeypatch.setattr(command, "upgrade", fail_upgrade)

    with pytest.raises(RuntimeError, match="injected migration failure"):
        run_migrations()


def test_run_migrations_can_defer_failure_logging(monkeypatch, caplog):
    """脱敏 CLI 可负责输出固定错误，同时迁移仍须 fail closed。"""
    from alembic import command

    from app.core.startup import run_migrations

    def fail_upgrade(*args, **kwargs):
        raise RuntimeError("sensitive migration detail")

    monkeypatch.setattr(command, "upgrade", fail_upgrade)

    with pytest.raises(RuntimeError, match="sensitive migration detail"):
        run_migrations(log_failure_detail=False)

    assert not any(record.exc_info for record in caplog.records)
