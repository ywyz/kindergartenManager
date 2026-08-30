"""Stable RED for the seventh W007 Standards Review findings."""

from __future__ import annotations

import ast
from pathlib import Path
import re

from markdown_it import MarkdownIt


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
MARKDOWN_PARSER = MarkdownIt("commonmark")
ALLOWED_STATUS_SHAS = {
    "ca3b7bd922f838c0739ccf9ed0f58655d292dc2f",
    "253d37d92f2983ea55f688340078380d41c78fd4",
    "a50c6f6b9aa941996052c59a301a7a40bdbd706f",
}
DIRECT_FLOW_NAMES = frozenset({"flow", "confirmation_flow"})


def _w007_status_sections(content: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    w007_heading_level: int | None = None
    w007_prose_active = False

    def flush_section() -> None:
        nonlocal current
        if not current:
            return
        sections.append("\n".join(current))
        current = []

    tokens = MARKDOWN_PARSER.parse(content)
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            inline = tokens[index + 1]
            if inline.type != "inline":
                continue
            level = int(token.tag.removeprefix("h"))
            if w007_prose_active:
                flush_section()
                w007_prose_active = False
            if w007_heading_level is not None and level <= w007_heading_level:
                flush_section()
                w007_heading_level = None
            if w007_heading_level is None and "W007" in inline.content:
                w007_heading_level = level
            if w007_heading_level is not None:
                current.append(inline.content)
            continue
        if token.type != "paragraph_open":
            continue
        inline = tokens[index + 1]
        if inline.type != "inline":
            continue
        if w007_heading_level is not None or w007_prose_active:
            current.append(inline.content)
            continue
        if "W007" in inline.content:
            w007_prose_active = True
            current.append(inline.content)
    flush_section()
    return sections


def _w007_status_problems(content: str) -> list[str]:
    problems: list[str] = []
    for section in _w007_status_sections(content):
        if REVIEW_ROUND_PATTERN.search(section):
            problems.append("duplicated W007 review round")
        unexpected_shas = sorted(
            set(FULL_SHA_PATTERN.findall(section)) - ALLOWED_STATUS_SHAS
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


def _is_direct_confirmation_flow_reference(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id in DIRECT_FLOW_NAMES
    return bool(
        isinstance(node, ast.Attribute)
        and node.attr == "flow"
        and isinstance(node.value, ast.Name)
        and node.value.id == "harness"
    )


def _confirmation_flow_private_reads(source: str) -> set[str]:
    """Find syntax-local private reads under the W007 review naming convention."""
    private_reads: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Attribute)
            and node.attr.startswith("_")
            and _is_direct_confirmation_flow_reference(node.value)
        ):
            private_reads.add(node.attr)
            continue
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and _is_direct_confirmation_flow_reference(node.args[0])
        ):
            continue
        attribute = node.args[1]
        if (
            isinstance(attribute, ast.Constant)
            and isinstance(attribute.value, str)
            and attribute.value.startswith("_")
        ):
            private_reads.add(attribute.value)
    return private_reads


def test_confirmation_flow_private_read_guard_covers_direct_receivers() -> None:
    source = (
        "harness.flow._confirmation_id\n"
        "flow._shutdown_task\n"
        "confirmation_flow._pending\n"
        'getattr(harness.flow, "_active_action")\n'
    )

    assert _confirmation_flow_private_reads(source) == {
        "_active_action",
        "_confirmation_id",
        "_pending",
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
