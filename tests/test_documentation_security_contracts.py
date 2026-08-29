"""安全边界文档必须和当前脱敏实现、冻结命名保持一致。"""

import re
from pathlib import Path


_ROOT = Path(__file__).parents[1]


def test_system_architecture_does_not_claim_raw_exception_logging() -> None:
    architecture = (_ROOT / "docs/design/system-architecture.md").read_text(
        encoding="utf-8"
    )

    assert "类型、消息和 traceback" not in architecture
    assert "异常正文与 traceback" in architecture
    assert "禁止跨越日志边界" in architecture


def test_agent_runtime_uses_the_frozen_write_audit_name() -> None:
    runtime = (_ROOT / "docs/design/agent-runtime.md").read_text(encoding="utf-8")

    assert "agent_action_audit" not in runtime
    assert "agent_write_audit" in runtime


def test_release_instructions_use_explicit_admin_bootstrap() -> None:
    workflow = (_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert "访问 http://localhost:8080/setup 创建管理员账号" not in workflow
    assert "# http://localhost:8080/setup" not in workflow
    assert "KindergartenManager.exe --init" in workflow
    assert "KindergartenManager --init" in workflow
    assert "python -m app.jobs.bootstrap_admin --init" in workflow
    assert "http://localhost:8080/login" in workflow
    assert "cp .env.example .env" in workflow
    assert "-v kg-data:/data" in workflow
    assert "-v kg-data:/app" not in workflow


def test_debian_init_instructions_run_as_the_service_user() -> None:
    """Every published Debian init command must preserve the service identity."""
    missing_user_property: list[str] = []
    for relative_path in ("docs/USER_MANUAL.md", ".github/workflows/release.yml"):
        document = (_ROOT / relative_path).read_text(encoding="utf-8")
        command = re.search(
            r"sudo systemd-run\b(?:(?!\n```).)*?--init",
            document,
            flags=re.DOTALL,
        )
        if (
            command is None
            or "--property=User=kindergarten-manager" not in command.group(0)
        ):
            missing_user_property.append(relative_path)

    assert not missing_user_property, (
        "Debian systemd-run --init must set the service user in: "
        + ", ".join(missing_user_property)
    )


def test_debian_postinstall_does_not_advertise_anonymous_admin_setup() -> None:
    postinstall = (_ROOT / "packaging/debian/DEBIAN/postinst").read_text(
        encoding="utf-8"
    )

    assert "http://localhost:8080/setup" not in postinstall
    assert "KindergartenManager --init" in postinstall


def test_user_manual_describes_current_explicit_bootstrap_boundary() -> None:
    manual = (_ROOT / "docs/USER_MANUAL.md").read_text(encoding="utf-8")

    assert "该改动尚未提交、\n发布" not in manual
    assert "KindergartenManager.exe --init" in manual
    assert "KindergartenManager --init" in manual
    assert "python -m app.jobs.bootstrap_admin --init" in manual


def test_readme_matches_current_login_agent_and_deployment_boundaries() -> None:
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")

    assert "没有有效登录保护" not in readme
    assert "受控 AI Agent（尚未实现）" not in readme
    assert "创建固定的默认管理员记录" not in readme
    assert "当前工作树 Alembic head：`e5f7a9c2d4b6`" in readme
    assert "python -m app.jobs.bootstrap_admin --init" in readme
    assert "4 个 READ Tool、2 个 DRAFT Tool" in readme
    assert "Provider WRITE" in readme
    assert "cp .env.example .env" in readme


def test_environment_template_declares_required_compose_secrets() -> None:
    example = (_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "MYSQL_ROOT_PASSWORD=" in example
    assert "MYSQL_PASSWORD=" in example
    assert "kg_root_2024" not in example
    assert "kg_pass_2024" not in example


def test_runtime_volume_names_are_preserved_in_readme_and_user_manual() -> None:
    """Deployment docs must name every volume whose data must survive upgrades."""
    required_volumes = ("app_data", "db_data", "exports")
    missing = {
        relative_path: [
            volume
            for volume in required_volumes
            if volume not in (_ROOT / relative_path).read_text(encoding="utf-8")
        ]
        for relative_path in ("README.md", "docs/USER_MANUAL.md")
    }

    assert not any(missing.values()), (
        "README.md and docs/USER_MANUAL.md must retain app_data, db_data, "
        f"and exports: {missing}"
    )


def test_sqlite_environment_comment_names_the_application_data_directory() -> None:
    """The SQLite template must not imply that data lives beside the program."""
    example = (_ROOT / ".env.example").read_text(encoding="utf-8")
    architecture = (_ROOT / "docs/design/system-architecture.md").read_text(
        encoding="utf-8"
    )

    assert "源码模式位于当前工作目录" in example
    assert "打包桌面模式位于操作系统用户数据目录" in example
    assert "程序同目录" not in example
    assert "源码模式默认数据库位于当前工作目录" in architecture


def test_current_migration_head_is_consistent_across_operator_docs() -> None:
    """Developer and manual migration checks must reach every current table/trigger."""
    expected_head = "`e5f7a9c2d4b6`"
    missing = [
        relative_path
        for relative_path in ("docs/DEVELOPER.md", "docs/MANUAL_TESTING.md")
        if expected_head not in (_ROOT / relative_path).read_text(encoding="utf-8")
    ]

    assert not missing, f"current Alembic head missing from: {missing}"


def test_all_authoritative_docs_distinguish_source_and_packaged_data_dirs() -> None:
    """Every operator entry point must describe the same runtime path behavior."""
    required = {
        "README.md": "源码模式默认为当前工作目录",
        "docs/ADR/ADR-0003-sqlite-default-mysql-optional-alembic.md": (
            "源码模式使用当前工作目录"
        ),
        "docs/design/system-architecture.md": (
            "源码模式的自动密钥写入当前工作目录"
        ),
    }
    missing = [
        relative_path
        for relative_path, expected in required.items()
        if expected not in (_ROOT / relative_path).read_text(encoding="utf-8")
    ]

    assert not missing, f"source/package data directory split missing from: {missing}"


def test_developer_status_points_to_the_canonical_agent_write_ledger() -> None:
    """The developer guide must not describe the current branch as uncommitted RED."""
    developer = (_ROOT / "docs/DEVELOPER.md").read_text(encoding="utf-8")

    assert "正在实现尚未提交" not in developer
    assert "specs/agent-write/tests/README.md" in developer


def test_compose_bootstrap_docs_use_an_explicit_one_shot_remote_override() -> None:
    """Compose bootstrap reaches db without enabling remote bootstrap at runtime."""
    required_command = (
        "docker compose exec -e BOOTSTRAP_ADMIN_ALLOW_REMOTE=true app "
        "python -m app.jobs.bootstrap_admin --init"
    )
    missing = [
        relative_path
        for relative_path in (
            "README.md",
            "docs/USER_MANUAL.md",
            ".github/workflows/release.yml",
        )
        if required_command
        not in (_ROOT / relative_path).read_text(encoding="utf-8")
    ]

    assert not missing, f"safe Compose bootstrap command missing from: {missing}"
