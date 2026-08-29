"""Stable RED for the corrected final W008 Standards Review findings."""

from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTEXT_PATH = REPOSITORY_ROOT / "CONTEXT.md"
MANUAL_ROOT = REPOSITORY_ROOT / "specs/agent-write/manual"
SHARED_FIXED_SHA_GATE = MANUAL_ROOT / "w008_fixed_sha.py"
MANUAL_HELPERS = (
    MANUAL_ROOT / "w008_browser.py",
    MANUAL_ROOT / "w008_mysql.py",
)
CANONICAL_LEDGER = "specs/agent-write/tests/README.md"
SHARED_GATE_DEFINITIONS = frozenset(
    {
        "_sha",
        "_git",
        "require_isolated_worktree",
        "_activate_worktree_imports",
    }
)


def _section(markdown: str, heading: str) -> str:
    body = markdown.split(heading, maxsplit=1)[1]
    return body.split("\n## ", maxsplit=1)[0]


def _top_level_definitions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_context_remote_status_advances_from_w006_to_the_w008_gate() -> None:
    """Current context must not contradict the canonical delivery ledger."""
    context = CONTEXT_PATH.read_text(encoding="utf-8")
    branch_status = _section(context, "## 7. 分支与仓库状态")

    assert "已到 W006 fixed SHA" not in branch_status
    assert "远端 `feat/agent-write` 已闭合 W007 并进入 W008 交付门" in branch_status
    assert CANONICAL_LEDGER in branch_status


def test_w008_manual_helpers_share_one_fixed_sha_worktree_gate() -> None:
    """Both evidence runners must use one drift-resistant trust root."""
    problems: list[str] = []
    if not SHARED_FIXED_SHA_GATE.is_file():
        problems.append("missing shared fixed-SHA gate")

    for helper_path in MANUAL_HELPERS:
        duplicated = sorted(
            _top_level_definitions(helper_path) & SHARED_GATE_DEFINITIONS
        )
        if duplicated:
            problems.append(f"{helper_path.name}: duplicated {duplicated}")
        source = helper_path.read_text(encoding="utf-8")
        if "from w008_fixed_sha import" not in source:
            problems.append(f"{helper_path.name}: missing shared gate import")

    assert problems == [], "\n".join(problems)
