"""Stable RED for the eighth W007 Standards Review findings."""

from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REVIEW7_GUARD = (
    REPOSITORY_ROOT
    / "specs/agent-write/tests/test_w007_review7_standards_findings_red.py"
)
STATUS_DOCS = (
    "AGENTS.md",
    "CONTEXT.md",
    "docs/ROADMAP.md",
    "docs/ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md",
    "docs/design/data-model.md",
    "docs/design/system-architecture.md",
    "memory-bank/architecture.md",
    "specs/agent-write/spec.md",
    "specs/agent-write/tasks.md",
)
CANONICAL_LEDGER_FACT = (
    "精确本地交付状态、Review 轮次、SHA 与测试证据仅以 "
    "`specs/agent-write/tests/README.md` 为准"
)
ISSUE_GATE_FACT = "Issue #52 仅在对应门回写后作为外部证据"


def _normalized(text: str) -> str:
    return "".join(text.replace(">", "").split())


def test_w007_status_docs_keep_one_local_authority_and_separate_issue_gate() -> None:
    """A stale Issue cannot be a co-authority for the current local state."""
    failures: dict[str, list[str]] = {}
    for relative_path in STATUS_DOCS:
        content = _normalized(
            (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        )
        missing = [
            fact
            for fact in (CANONICAL_LEDGER_FACT, ISSUE_GATE_FACT)
            if _normalized(fact) not in content
        ]
        if "和 Issue #52 实时回读为准" in content:
            missing.append("Issue #52 must not be a current-state co-authority")
        if missing:
            failures[relative_path] = missing

    assert failures == {}, (
        "W007 local status must have one canonical ledger and a separate "
        f"Issue evidence gate: {failures}"
    )


def test_w007_review_guard_is_general_instead_of_incident_specific() -> None:
    """The guard must cover any review round/SHA and flow-private attribute."""
    source = REVIEW7_GUARD.read_text(encoding="utf-8")

    assert "第五轮 finding" not in source
    assert "68e4c340e0188f456ff8bc1caca5181f07410b15" not in source
    assert 'node.attr == "_shutdown_task"' not in source
    assert "REVIEW_ROUND_PATTERN" in source
    assert "FULL_SHA_PATTERN" in source
    assert 'node.attr.startswith("_")' in source
    assert "test_w007_review*.py" in source
