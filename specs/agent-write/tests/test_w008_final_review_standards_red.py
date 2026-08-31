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
SHARED_GATE_IMPORTS = frozenset(
    {
        "ManualHelperError",
        "_activate_worktree_imports",
        "_sha",
        "require_isolated_worktree",
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


def _shared_gate_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "w008_fixed_sha"
        for alias in node.names
    }


def test_context_remote_status_records_w008_integration_closure() -> None:
    """Current context must not contradict the canonical delivery ledger."""
    context = CONTEXT_PATH.read_text(encoding="utf-8")
    branch_status = _section(context, "## 7. 分支与仓库状态")

    assert "已到 W006 fixed SHA" not in branch_status
    assert "PR #53 已于 2026-08-30 no-ff 合并" in branch_status
    assert "Issue #52 已关闭" in branch_status
    assert CANONICAL_LEDGER in branch_status


def test_context_current_next_step_advances_beyond_closed_w008() -> None:
    """The current-next-step section must advance with the delivery ledger."""
    context = CONTEXT_PATH.read_text(encoding="utf-8")
    next_steps = _section(context, "## 10. 当前共同下一步")

    assert "W007 上述门全部闭合后才进入 W008" not in next_steps
    assert "Issue #54" in next_steps
    assert "docs/PRODUCT_DIRECTION.md" in next_steps


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
        imported = _shared_gate_imports(helper_path)
        if imported != SHARED_GATE_IMPORTS:
            problems.append(f"{helper_path.name}: shared imports {sorted(imported)}")

    assert problems == [], "\n".join(problems)
