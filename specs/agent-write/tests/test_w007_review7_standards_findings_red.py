"""Stable RED for the seventh W007 Standards Review findings."""

from __future__ import annotations

import ast
from pathlib import Path
import re


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
REVIEW_ROUND_PATTERN = re.compile(r"第[一二三四五六七八九十百0-9]+轮")
FULL_SHA_PATTERN = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])")
ALLOWED_STATUS_SHAS = {
    "ca3b7bd922f838c0739ccf9ed0f58655d292dc2f",
    "253d37d92f2983ea55f688340078380d41c78fd4",
    "a50c6f6b9aa941996052c59a301a7a40bdbd706f",
}


def _w007_status_problems(content: str) -> list[str]:
    problems: list[str] = []
    paragraphs = re.split(r"\n\s*\n", content)
    for paragraph in paragraphs:
        if "W007" not in paragraph:
            continue
        if REVIEW_ROUND_PATTERN.search(paragraph):
            problems.append("duplicated W007 review round")
        unexpected_shas = sorted(
            set(FULL_SHA_PATTERN.findall(paragraph)) - ALLOWED_STATUS_SHAS
        )
        problems.extend(f"duplicated W007 review SHA: {sha}" for sha in unexpected_shas)
    return problems


def test_w007_status_docs_delegate_review_rounds_to_canonical_ledger() -> None:
    """Current-state docs must not duplicate a review round or its SHA."""
    failures: dict[str, list[str]] = {}
    for relative_path in STATUS_DOCS:
        content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        problems = _w007_status_problems(content)
        if EVIDENCE_LEDGER_PATH not in content:
            problems.append(f"missing canonical ledger: {EVIDENCE_LEDGER_PATH}")
        if problems:
            failures[relative_path] = problems

    assert failures == {}, (
        "W007 status docs must use the canonical ledger without locking an "
        f"obsolete review round: {failures}"
    )


def test_w007_status_guard_covers_any_review_round_and_sha() -> None:
    review_sha = "1234567890abcdef1234567890abcdef12345678"
    content = f"W007 当前为第七轮 Review，finding RED 固定在 {review_sha}。"

    assert _w007_status_problems(content) == [
        "duplicated W007 review round",
        f"duplicated W007 review SHA: {review_sha}",
    ]


def _confirmation_flow_private_reads(source: str) -> set[str]:
    tree = ast.parse(source)
    private_reads: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or not node.attr.startswith("_"):
            continue
        target = node.value
        is_flow = isinstance(target, ast.Name) and target.id in {
            "flow",
            "confirmation_flow",
        }
        is_harness_flow = isinstance(target, ast.Attribute) and target.attr == "flow"
        if is_flow or is_harness_flow:
            private_reads.add(node.attr)
    return private_reads


def test_confirmation_flow_private_read_guard_covers_any_private_attribute() -> None:
    source = "harness.flow._confirmation_id\nflow._shutdown_task\n"

    assert _confirmation_flow_private_reads(source) == {
        "_confirmation_id",
        "_shutdown_task",
    }


def test_w007_review_tests_do_not_read_confirmation_flow_private_state() -> None:
    """Review tests must prove public effects without reading service internals."""
    review_tests = sorted(
        (REPOSITORY_ROOT / "specs/agent-write/tests").glob("test_w007_review*.py")
    )
    private_reads = {
        review_test.relative_to(REPOSITORY_ROOT).as_posix(): sorted(
            _confirmation_flow_private_reads(review_test.read_text(encoding="utf-8"))
        )
        for review_test in review_tests
    }
    private_reads = {path: names for path, names in private_reads.items() if names}

    assert private_reads == {}, (
        "W007 review tests must not inspect confirmation-flow private state: "
        f"{private_reads}"
    )
