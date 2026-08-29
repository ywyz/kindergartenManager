"""安全边界文档必须和当前脱敏实现、冻结命名保持一致。"""

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
