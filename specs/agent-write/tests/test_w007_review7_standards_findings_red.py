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
MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")
ALLOWED_STATUS_SHAS = {
    "ca3b7bd922f838c0739ccf9ed0f58655d292dc2f",
    "253d37d92f2983ea55f688340078380d41c78fd4",
    "a50c6f6b9aa941996052c59a301a7a40bdbd706f",
}


def _w007_status_sections(content: str) -> list[str]:
    sections: list[str] = []
    paragraph: list[str] = []
    paragraph_in_w007_section = False
    w007_heading_level: int | None = None

    def flush_paragraph() -> None:
        nonlocal paragraph, paragraph_in_w007_section
        if not paragraph:
            return
        text = "\n".join(paragraph)
        if paragraph_in_w007_section or "W007" in text:
            sections.append(text)
        paragraph = []
        paragraph_in_w007_section = w007_heading_level is not None

    for line in content.splitlines():
        heading = MARKDOWN_HEADING_PATTERN.match(line)
        if heading is not None:
            flush_paragraph()
            level = len(heading.group(1))
            if w007_heading_level is not None and level <= w007_heading_level:
                w007_heading_level = None
            if "W007" in heading.group(2):
                w007_heading_level = level
            paragraph_in_w007_section = w007_heading_level is not None
        if not line.strip():
            flush_paragraph()
            continue
        if not paragraph:
            paragraph_in_w007_section = w007_heading_level is not None
        paragraph.append(line)
    flush_paragraph()
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


def _is_confirmation_flow_reference(node: ast.expr, aliases: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in aliases
    if isinstance(node, ast.Attribute):
        return node.attr == "flow"
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == "flow"
    ):
        return True
    return False


def _assigned_names(target: ast.expr) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.List, ast.Tuple)):
        return {name for element in target.elts for name in _assigned_names(element)}
    return set()


def _confirmation_flow_private_reads(source: str) -> set[str]:
    tree = ast.parse(source)
    aliases = {"flow", "confirmation_flow"}
    assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr))
    ]
    changed = True
    while changed:
        changed = False
        for assignment in assignments:
            if isinstance(assignment, ast.Assign):
                targets = assignment.targets
                value = assignment.value
            else:
                targets = [assignment.target]
                value = assignment.value
            if value is None or not _is_confirmation_flow_reference(value, aliases):
                continue
            assigned = {name for target in targets for name in _assigned_names(target)}
            new_aliases = assigned - aliases
            if new_aliases:
                aliases.update(new_aliases)
                changed = True

    private_reads: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            if _is_confirmation_flow_reference(node.value, aliases):
                private_reads.add(node.attr)
            continue
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and _is_confirmation_flow_reference(node.args[0], aliases)
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
