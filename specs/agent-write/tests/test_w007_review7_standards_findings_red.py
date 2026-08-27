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


class _LexicalBindingVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.names.add(node.id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.names.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.names.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.names.add(node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        del node

    def visit_Import(self, node: ast.Import) -> None:
        self.names.update(
            alias.asname or alias.name.split(".")[0] for alias in node.names
        )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.names.update(alias.asname or alias.name for alias in node.names)


class _ConfirmationFlowPrivateReadVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.private_reads: set[str] = set()
        self._flow_aliases = {"flow", "confirmation_flow"}
        self._getattr_aliases = {"getattr"}
        self._harness_aliases = {"harness"}

    def _is_harness_reference(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self._harness_aliases
        if isinstance(node, ast.Attribute):
            return node.attr == "harness"
        if isinstance(node, ast.Subscript):
            return self._is_harness_reference(node.value)
        if isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Name):
                return function.id == "_new_harness"
            if isinstance(function, ast.Attribute):
                return function.attr == "new_harness"
        if isinstance(node, ast.IfExp):
            return self._is_harness_reference(node.body) or self._is_harness_reference(
                node.orelse
            )
        return False

    def _is_getattr_reference(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self._getattr_aliases
        return bool(
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "builtins"
            and node.attr == "getattr"
        )

    def _is_flow_reference(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self._flow_aliases
        if isinstance(node, ast.Attribute):
            return node.attr == "flow" and self._is_harness_reference(node.value)
        if isinstance(node, ast.IfExp):
            return self._is_flow_reference(node.body) or self._is_flow_reference(
                node.orelse
            )
        return bool(
            isinstance(node, ast.Call)
            and self._is_getattr_reference(node.func)
            and len(node.args) >= 2
            and self._is_harness_reference(node.args[0])
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == "flow"
        )

    def _state(self) -> tuple[set[str], set[str], set[str]]:
        return (
            set(self._flow_aliases),
            set(self._getattr_aliases),
            set(self._harness_aliases),
        )

    def _set_state(self, state: tuple[set[str], set[str], set[str]]) -> None:
        self._flow_aliases = set(state[0])
        self._getattr_aliases = set(state[1])
        self._harness_aliases = set(state[2])

    @staticmethod
    def _merged_states(
        *states: tuple[set[str], set[str], set[str]],
    ) -> tuple[set[str], set[str], set[str]]:
        return (
            set().union(*(state[0] for state in states)),
            set().union(*(state[1] for state in states)),
            set().union(*(state[2] for state in states)),
        )

    def _visit_block_from(
        self,
        body: list[ast.stmt],
        state: tuple[set[str], set[str], set[str]],
    ) -> tuple[set[str], set[str], set[str]]:
        saved = self._state()
        self._set_state(state)
        for statement in body:
            self.visit(statement)
        result = self._state()
        self._set_state(saved)
        return result

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
        if self._is_harness_reference(value):
            self._harness_aliases.add(target.id)
        else:
            self._harness_aliases.discard(target.id)

    def _discard_target(self, target: ast.expr) -> None:
        if isinstance(target, ast.Name):
            self._flow_aliases.discard(target.id)
            self._getattr_aliases.discard(target.id)
            self._harness_aliases.discard(target.id)
        elif isinstance(target, (ast.List, ast.Tuple)):
            for element in target.elts:
                self._discard_target(element)

    @staticmethod
    def _argument_names(arguments: ast.arguments) -> set[str]:
        positional = (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)
        names = {argument.arg for argument in positional}
        if arguments.vararg is not None:
            names.add(arguments.vararg.arg)
        if arguments.kwarg is not None:
            names.add(arguments.kwarg.arg)
        return names

    @staticmethod
    def _local_names(body: list[ast.stmt]) -> set[str]:
        collector = _LexicalBindingVisitor()
        for statement in body:
            collector.visit(statement)
        return collector.names

    def _visit_function_metadata(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in (*node.args.defaults, *node.args.kw_defaults):
            if default is not None:
                self.visit(default)
        if node.returns is not None:
            self.visit(node.returns)

    def _visit_function_scope(
        self,
        body: list[ast.stmt],
        arguments: ast.arguments,
    ) -> None:
        outer = self._state()
        local_names = self._local_names(body) | self._argument_names(arguments)
        self._flow_aliases = outer[0] - local_names
        self._getattr_aliases = outer[1] - local_names
        self._harness_aliases = outer[2] - local_names
        if "harness" in self._argument_names(arguments):
            self._harness_aliases.add("harness")
        for statement in body:
            self.visit(statement)
        self._set_state(outer)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_metadata(node)
        self._visit_function_scope(node.body, node.args)
        self._discard_target(ast.Name(id=node.name, ctx=ast.Store()))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_metadata(node)
        self._visit_function_scope(node.body, node.args)
        self._discard_target(ast.Name(id=node.name, ctx=ast.Store()))

    def visit_Lambda(self, node: ast.Lambda) -> None:
        outer = self._state()
        local_names = self._argument_names(node.args)
        self._flow_aliases = outer[0] - local_names
        self._getattr_aliases = outer[1] - local_names
        self._harness_aliases = outer[2] - local_names
        if "harness" in local_names:
            self._harness_aliases.add("harness")
        self.visit(node.body)
        self._set_state(outer)

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        initial = self._state()
        body_state = self._visit_block_from(node.body, initial)
        else_state = (
            self._visit_block_from(node.orelse, initial) if node.orelse else initial
        )
        self._set_state(self._merged_states(body_state, else_state))

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
