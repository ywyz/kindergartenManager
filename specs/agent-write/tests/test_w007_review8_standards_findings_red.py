"""Stable RED for the eighth W007 Standards Review findings."""

from __future__ import annotations

from pathlib import Path

from test_w007_review7_standards_findings_red import (
    _confirmation_flow_private_reads,
    _w007_status_problems,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
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


def test_w007_status_guard_follows_a_markdown_section_across_blank_lines() -> None:
    """A W007 heading governs its body until the next peer heading."""
    review_sha = "1234567890abcdef1234567890abcdef12345678"
    content = f"## W007\n\n当前为第九轮 Review，SHA {review_sha}。\n"

    assert _w007_status_problems(content) == [
        "duplicated W007 review round",
        f"duplicated W007 review SHA: {review_sha}",
    ]


def test_confirmation_flow_private_guard_covers_direct_getattr() -> None:
    """The syntax-local smoke guard covers direct ``getattr`` access."""
    source = """
confirmation_flow._confirmation_id
harness.flow._pending
getattr(flow, "_shutdown_task")
"""

    assert _confirmation_flow_private_reads(source) == {
        "_confirmation_id",
        "_pending",
        "_shutdown_task",
    }
