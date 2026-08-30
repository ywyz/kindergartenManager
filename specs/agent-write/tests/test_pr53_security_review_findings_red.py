"""PR #53 远端安全 Review finding 的稳定 RED 合同。"""

from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys


_ROOT = Path(__file__).resolve().parents[3]


def _settings_page() -> ast.AsyncFunctionDef:
    tree = ast.parse((_ROOT / "app/ui/pages/settings.py").read_text(encoding="utf-8"))
    return next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "settings_page"
    )


def test_deployment_settings_are_sys_admin_only_and_never_echo_db_password() -> None:
    """教师设置页不得读取/呈现/写入进程级部署配置。"""
    page = _settings_page()
    admin_branch = next(
        (
            node
            for node in ast.walk(page)
            if isinstance(node, ast.If)
            and ast.unparse(node.test)
            == "current_session.role == UserRole.sys_admin.value"
        ),
        None,
    )

    assert admin_branch is not None, "deployment controls need a sys_admin gate"
    assert "current_session = await require_live_session()" in ast.unparse(page)
    admin_source = ast.unparse(admin_branch)
    assert "read_dot_env()" in admin_source
    assert "数据库配置" in admin_source
    assert "应用端口" in admin_source

    page_source = ast.unparse(page)
    assert "value=_parsed_password" not in page_source

    live_guard = next(
        node
        for node in ast.walk(page)
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "require_deployment_session"
    )
    assert "allowed_roles={UserRole.sys_admin.value}" in ast.unparse(live_guard)

    for callback_name in ("_save_db_config", "_save_port"):
        callback = next(
            node
            for node in ast.walk(admin_branch)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == callback_name
        )
        callback_source = ast.unparse(callback)
        assert callback_source.index(
            "await require_deployment_session()"
        ) < callback_source.index("write_dot_env(")


def test_bootstrap_cli_migration_failure_has_nonzero_process_exit() -> None:
    """部署自动化不得把迁移失败误报为成功。"""
    test_password = "TestOnlyDatabasePassword!"
    env = os.environ.copy()
    env.update(
        {
            "BOOTSTRAP_ADMIN_ENABLED": "true",
            "BOOTSTRAP_ADMIN_USERNAME": "sysadmin",
            "BOOTSTRAP_ADMIN_PASSWORD": "TestOnlyAdminPassword!",
            "BOOTSTRAP_ADMIN_ALLOW_REMOTE": "false",
            "DATABASE_URL": (
                "mysql+aiomysql://test_only_user:"
                f"{test_password}@127.0.0.1:1/test_only_db"
            ),
        }
    )

    completed = subprocess.run(
        [sys.executable, "-m", "app.jobs.bootstrap_admin", "--init"],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    output = completed.stdout + completed.stderr

    assert "迁移失败" in output
    assert test_password not in output
    assert "Traceback" not in output
    assert "Connection refused" not in output
    assert "sqlalchemy.exc" not in output
    assert completed.returncode != 0
