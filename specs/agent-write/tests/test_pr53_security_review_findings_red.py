"""PR #53 远端安全 Review finding 的稳定 RED 合同。"""

from __future__ import annotations

import ast
from pathlib import Path


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
            and ast.unparse(node.test) == "ui_session.role == UserRole.sys_admin.value"
        ),
        None,
    )

    assert admin_branch is not None, "deployment controls need an explicit sys_admin gate"
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
