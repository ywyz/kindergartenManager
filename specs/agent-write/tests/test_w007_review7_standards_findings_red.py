"""Stable RED for the seventh W007 Standards Review findings."""

from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_LEDGER_PATH = "specs/agent-write/tests/README.md"
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
STALE_CURRENT_FACTS = (
    "第五轮 finding",
    "68e4c340e0188f456ff8bc1caca5181f07410b15",
)


def test_w007_status_docs_delegate_review_rounds_to_canonical_ledger() -> None:
    """Current-state docs must not duplicate a review round or its SHA."""
    failures: dict[str, list[str]] = {}
    for relative_path in STATUS_DOCS:
        content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        problems = [marker for marker in STALE_CURRENT_FACTS if marker in content]
        if EVIDENCE_LEDGER_PATH not in content:
            problems.append(f"missing canonical ledger: {EVIDENCE_LEDGER_PATH}")
        if problems:
            failures[relative_path] = problems

    assert failures == {}, (
        "W007 status docs must use the canonical ledger without locking an "
        f"obsolete review round: {failures}"
    )


def test_w007_review_tests_do_not_read_confirmation_flow_private_state() -> None:
    """Review tests must prove public effects without reading service internals."""
    review_test = (
        REPOSITORY_ROOT
        / "specs/agent-write/tests/test_w007_review6_standards_findings_red.py"
    )
    tree = ast.parse(review_test.read_text(encoding="utf-8"))
    private_reads = sorted(
        {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "_shutdown_task"
        }
    )

    assert private_reads == [], (
        "W007 review tests must not inspect confirmation-flow private state: "
        f"{private_reads}"
    )
