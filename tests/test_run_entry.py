"""run.py 启动入口分派测试。"""

import pytest

import run


def test_run_dispatch_to_bootstrap_with_init(monkeypatch):
    """带 --init 时应走 bootstrap_admin 的 CLI。"""

    called = {"app": 0, "bootstrap": 0}

    monkeypatch.setattr(
        run, "_run_main_app", lambda: called.__setitem__("app", called["app"] + 1)
    )
    monkeypatch.setattr(
        run,
        "_run_bootstrap_admin_cli",
        lambda: called.__setitem__("bootstrap", called["bootstrap"] + 1),
    )

    run._run_entrypoint(["run.py", "--init"])

    assert called["bootstrap"] == 1
    assert called["app"] == 0


def test_run_dispatch_to_bootstrap_with_reset_password(monkeypatch):
    """带 --reset-password 时应走 bootstrap_admin 的 CLI。"""

    called = {"app": 0, "bootstrap": 0}

    monkeypatch.setattr(
        run, "_run_main_app", lambda: called.__setitem__("app", called["app"] + 1)
    )
    monkeypatch.setattr(
        run,
        "_run_bootstrap_admin_cli",
        lambda: called.__setitem__("bootstrap", called["bootstrap"] + 1),
    )

    run._run_entrypoint(["run.py", "--reset-password"])

    assert called["bootstrap"] == 1
    assert called["app"] == 0


def test_run_dispatch_to_main_without_bootstrap_args(monkeypatch):
    """无 bootstrap 参数时仍应走 app.main.main。"""

    called = {"app": 0, "bootstrap": 0}

    monkeypatch.setattr(
        run, "_run_main_app", lambda: called.__setitem__("app", called["app"] + 1)
    )
    monkeypatch.setattr(
        run,
        "_run_bootstrap_admin_cli",
        lambda: called.__setitem__("bootstrap", called["bootstrap"] + 1),
    )

    run._run_entrypoint(["run.py"])

    assert called["app"] == 1
    assert called["bootstrap"] == 0


@pytest.mark.parametrize("exit_code", [0, 1, 2])
def test_packaged_bootstrap_cli_propagates_exit_code(monkeypatch, exit_code):
    """打包入口必须把初始化成功、失败和取消状态传给调用进程。"""
    from app.jobs import bootstrap_admin

    async def fake_main():
        return exit_code

    monkeypatch.setattr(bootstrap_admin, "_main", fake_main)

    with pytest.raises(SystemExit) as exc_info:
        run._run_bootstrap_admin_cli()

    assert exc_info.value.code == exit_code
