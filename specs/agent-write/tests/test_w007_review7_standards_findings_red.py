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
MARKDOWN_FENCE_PATTERN = re.compile(r"^\s*(`{3,}|~{3,})")
ALLOWED_STATUS_SHAS = {
    "ca3b7bd922f838c0739ccf9ed0f58655d292dc2f",
    "253d37d92f2983ea55f688340078380d41c78fd4",
    "a50c6f6b9aa941996052c59a301a7a40bdbd706f",
}


def _w007_status_sections(content: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    w007_heading_level: int | None = None
    w007_prose_active = False
    fence: str | None = None

    def flush_section() -> None:
        nonlocal current
        if not current:
            return
        sections.append("\n".join(current))
        current = []

    for line in content.splitlines():
        fence_match = MARKDOWN_FENCE_PATTERN.match(line)
        if fence is not None:
            if (
                fence_match is not None
                and fence_match.group(1)[0] == fence[0]
                and len(fence_match.group(1)) >= len(fence)
            ):
                fence = None
            continue
        if fence_match is not None:
            fence = fence_match.group(1)
            continue

        heading = MARKDOWN_HEADING_PATTERN.match(line)
        if heading is not None:
            level = len(heading.group(1))
            if w007_prose_active:
                flush_section()
                w007_prose_active = False
            if w007_heading_level is not None and level <= w007_heading_level:
                flush_section()
                w007_heading_level = None
            if w007_heading_level is None and "W007" in heading.group(2):
                w007_heading_level = level
            if w007_heading_level is not None:
                current.append(line)
            continue

        if w007_heading_level is not None or w007_prose_active:
            current.append(line)
            continue
        if "W007" in line:
            w007_prose_active = True
            current.append(line)
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


class _ConfirmationFlowPrivateReadVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.private_reads: set[str] = set()
        self._flow_aliases = {"flow", "confirmation_flow"}
        self._getattr_aliases = {"getattr"}

    @staticmethod
    def _looks_like_harness(node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return node.id == "harness" or node.id.endswith("_harness")
        if isinstance(node, ast.Attribute):
            return node.attr == "harness" or node.attr.endswith("_harness")
        if isinstance(node, ast.Subscript):
            return _ConfirmationFlowPrivateReadVisitor._looks_like_harness(node.value)
        if isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Name):
                return "harness" in function.id
            if isinstance(function, ast.Attribute):
                return "harness" in function.attr
        return False

    def _is_getattr_reference(self, node: ast.expr) -> bool:
        return isinstance(node, ast.Name) and node.id in self._getattr_aliases

    def _is_flow_reference(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self._flow_aliases
        if isinstance(node, ast.Attribute):
            return node.attr == "flow" and self._looks_like_harness(node.value)
        return bool(
            isinstance(node, ast.Call)
            and self._is_getattr_reference(node.func)
            and len(node.args) >= 2
            and self._looks_like_harness(node.args[0])
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == "flow"
        )

    def _bind_target(self, target: ast.expr, value: ast.expr) -> None:
        if isinstance(target, (ast.List, ast.Tuple)) and isinstance(
            value, (ast.List, ast.Tuple)
        ):
            if len(target.elts) == len(value.elts):
                for target_element, value_element in zip(
                    target.elts, value.elts, strict=True
                ):
                    self._bind_target(target_element, value_element)
                return
        if isinstance(target, (ast.List, ast.Tuple)):
            for element in target.elts:
                self._discard_target(element)
            return
        if not isinstance(target, ast.Name):
            return
        if self._is_flow_reference(value):
            self._flow_aliases.add(target.id)
        else:
            self._flow_aliases.discard(target.id)
        if self._is_getattr_reference(value):
            self._getattr_aliases.add(target.id)
        else:
            self._getattr_aliases.discard(target.id)

    def _discard_target(self, target: ast.expr) -> None:
        if isinstance(target, ast.Name):
            self._flow_aliases.discard(target.id)
            self._getattr_aliases.discard(target.id)
        elif isinstance(target, (ast.List, ast.Tuple)):
            for element in target.elts:
                self._discard_target(element)

    def _visit_function_scope(
        self,
        body: list[ast.stmt],
    ) -> None:
        outer_flow_aliases = self._flow_aliases
        outer_getattr_aliases = self._getattr_aliases
        self._flow_aliases = {"flow", "confirmation_flow"}
        self._getattr_aliases = {"getattr"}
        for statement in body:
            self.visit(statement)
        self._flow_aliases = outer_flow_aliases
        self._getattr_aliases = outer_getattr_aliases

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_scope(node.body)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_scope(node.body)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        outer_flow_aliases = self._flow_aliases
        outer_getattr_aliases = self._getattr_aliases
        self._flow_aliases = {"flow", "confirmation_flow"}
        self._getattr_aliases = {"getattr"}
        self.visit(node.body)
        self._flow_aliases = outer_flow_aliases
        self._getattr_aliases = outer_getattr_aliases

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        for target in node.targets:
            self.visit(target)
            self._bind_target(target, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self.visit(node.value)
            self.visit(node.target)
            self._bind_target(node.target, node.value)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.visit(node.value)
        self.visit(node.target)
        self._bind_target(node.target, node.value)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("_") and self._is_flow_reference(node.value):
            self.private_reads.add(node.attr)
        self.visit(node.value)

    def visit_Call(self, node: ast.Call) -> None:
        if (
            self._is_getattr_reference(node.func)
            and len(node.args) >= 2
            and self._is_flow_reference(node.args[0])
        ):
            attribute = node.args[1]
            if (
                isinstance(attribute, ast.Constant)
                and isinstance(attribute.value, str)
                and attribute.value.startswith("_")
            ):
                self.private_reads.add(attribute.value)
        self.generic_visit(node)


def _confirmation_flow_private_reads(source: str) -> set[str]:
    visitor = _ConfirmationFlowPrivateReadVisitor()
    visitor.visit(ast.parse(source))
    return visitor.private_reads


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
