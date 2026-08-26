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
