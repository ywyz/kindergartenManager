"""Stable RED for the first W007 Standards Review findings."""

from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DAILY_PLAN_PAGE = REPOSITORY_ROOT / "app/ui/pages/daily_plan.py"

CURRENT_FACT_FILES = (
    "AGENTS.md",
    "CONTEXT.md",
    "docs/ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md",
    "docs/design/data-model.md",
    "docs/design/system-architecture.md",
    "specs/agent-write/spec.md",
)
DELIVERY_GATE_FACT_FILES = (
    "docs/ROADMAP.md",
    "specs/agent-write/tasks.md",
    "specs/agent-write/tests/README.md",
    "memory-bank/architecture.md",
)
CURRENT_GATE_FACT = (
    "W007 GREEN commit 已存在，当前门是固定 SHA Review/finding RED；W008 未进入"
)
INITIAL_GREEN_BASELINE_FACT = (
    "W007 初始 GREEN commit 本地基线为 WRITE `99 passed`、Foundation "
    "`261 passed`、ordinary `847 passed`"
)
FINDING_CANDIDATE_REVIEW_FACT = (
    "首轮 fixed-SHA Review 已完成；finding 修正候选当前本地 WRITE "
    "`110 passed`、Foundation `261 passed`、ordinary `847 passed`，并等待 "
    "fixed-SHA 复审"
)
STALE_CURRENT_FACTS = {
    "AGENTS.md": (
        "The current authorized slice ends after",
        "Until an explicit later GREEN gate",
    ),
    "CONTEXT.md": (
        "W007 UI adapter 正在 GREEN 实现",
        "完成 W007 当前页面单 Patch 确认 UI 的最小 GREEN commit",
    ),
    "docs/ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md": (
        "W007 当前只有稳定 RED",
        "W007 GREEN commit →",
    ),
    "docs/design/data-model.md": (
        "稳定 RED 并正在 GREEN 实现",
        "W007 产品 UI 正在 GREEN 实现",
    ),
    "docs/design/system-architecture.md": (
        "W007 UI 正在 GREEN 实现",
        "W007 仍只有稳定 RED 与进行中的 GREEN 实现",
        "当前门是 W007 单 Patch UI GREEN",
    ),
    "specs/agent-write/spec.md": (
        "须先形成 GREEN commit",
        "W007 候选必须依序经过：最小 GREEN commit",
    ),
}
STALE_DELIVERY_GATE_FACTS = {
    "docs/ROADMAP.md": (
        "当前 GREEN 候选为 WRITE `99 passed`",
        "不预宣称 fixed-SHA Review",
    ),
    "specs/agent-write/tasks.md": (
        "GREEN 候选：稳定 RED `e5f7317…` 后本地 WRITE 99",
        "待 fixed-SHA Review/push/CI/验收/Issue",
    ),
    "specs/agent-write/tests/README.md": (
        "GREEN 候选现为 WRITE `99 passed`",
        "尚未取得 fixed-SHA Review",
    ),
    "memory-bank/architecture.md": (
        "GREEN 候选现为 WRITE `99 passed`",
    ),
}


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _imports(tree: ast.AST) -> dict[str, str]:
    imported: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imported[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported[alias.asname or alias.name.split(".")[0]] = alias.name
    return imported


def _function(tree: ast.AST, name: str) -> ast.AsyncFunctionDef:
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name
    ]
    assert len(matches) == 1, f"expected one async {name}, found {len(matches)}"
    return matches[0]


def _qualified_source(qualified_name: str) -> tuple[ast.Module, str]:
    module_name, symbol = qualified_name.rsplit(".", 1)
    module_path = REPOSITORY_ROOT / Path(*module_name.split("."))
    source_path = module_path.with_suffix(".py")
    assert source_path.is_file(), f"service source missing: {source_path}"
    return ast.parse(source_path.read_text(encoding="utf-8")), symbol


def _is_frozen_dataclass(class_node: ast.ClassDef) -> bool:
    for decorator in class_node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        decorator_name = decorator.func
        if not (
            isinstance(decorator_name, ast.Name)
            and decorator_name.id == "dataclass"
        ):
            continue
        return any(
            keyword.arg == "frozen"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in decorator.keywords
        )
    return False


def _returns_frozen_dto(qualified_function: str) -> bool:
    service_tree, function_name = _qualified_source(qualified_function)
    functions = [
        node
        for node in ast.walk(service_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]
    if len(functions) != 1 or functions[0].returns is None:
        return False

    return_names = {
        node.id
        for node in ast.walk(functions[0].returns)
        if isinstance(node, ast.Name)
    }
    service_classes = {
        node.name: node
        for node in service_tree.body
        if isinstance(node, ast.ClassDef)
    }
    service_imports = _imports(service_tree)

    for return_name in return_names:
        local_class = service_classes.get(return_name)
        if local_class is not None and _is_frozen_dataclass(local_class):
            return True
        imported_class = service_imports.get(return_name)
        if imported_class is None or not imported_class.startswith("app.service."):
            continue
        imported_tree, imported_name = _qualified_source(imported_class)
        imported_classes = {
            node.name: node
            for node in imported_tree.body
            if isinstance(node, ast.ClassDef)
        }
        imported_node = imported_classes.get(imported_name)
        if imported_node is not None and _is_frozen_dataclass(imported_node):
            return True
    return False


def test_w007_authoritative_reload_uses_a_frozen_service_projection() -> None:
    tree = ast.parse(DAILY_PLAN_PAGE.read_text(encoding="utf-8"))
    imported = _imports(tree)
    callback = _function(tree, "_publish_confirmed_plan")

    used_imports = {
        node.id: imported[node.id]
        for node in ast.walk(callback)
        if isinstance(node, ast.Name) and node.id in imported
    }
    forbidden = {
        alias: qualified
        for alias, qualified in used_imports.items()
        if qualified == "app.core.database.AsyncSessionLocal"
        or qualified.startswith("app.repository.")
        or qualified.startswith("app.core.models.")
        or qualified.startswith("app.models.")
        or qualified.startswith("sqlalchemy.")
    }
    service_calls = {
        imported[node.func.id]
        for node in ast.walk(callback)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in imported
        and imported[node.func.id].startswith("app.service.")
    }

    assert forbidden == {}, (
        "W007 UI callback crosses the database/repository/ORM boundary: "
        f"{forbidden}"
    )
    assert service_calls, "W007 authoritative reload must call an app.service projection"
    assert any(_returns_frozen_dto(call) for call in service_calls), (
        "W007 authoritative reload service must return a frozen DTO: "
        f"{sorted(service_calls)}"
    )


def test_w007_current_facts_name_the_committed_green_review_gate() -> None:
    normalized_docs = {
        relative_path: _normalized(
            (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        )
        for relative_path in CURRENT_FACT_FILES
    }
    missing_gate_fact = [
        relative_path
        for relative_path, text in normalized_docs.items()
        if CURRENT_GATE_FACT not in text
    ]
    stale_claims = {
        relative_path: [
            stale
            for stale in STALE_CURRENT_FACTS[relative_path]
            if _normalized(stale) in text
        ]
        for relative_path, text in normalized_docs.items()
    }
    stale_claims = {
        relative_path: claims
        for relative_path, claims in stale_claims.items()
        if claims
    }

    assert missing_gate_fact == [], (
        f"current W007 gate fact missing from: {missing_gate_fact}"
    )
    assert stale_claims == {}, f"contradictory W007 current facts remain: {stale_claims}"

    delivery_gate_docs = {
        relative_path: _normalized(
            (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        )
        for relative_path in DELIVERY_GATE_FACT_FILES
    }
    required_delivery_facts = (
        INITIAL_GREEN_BASELINE_FACT,
        FINDING_CANDIDATE_REVIEW_FACT,
    )
    missing_delivery_facts = {
        relative_path: [
            fact for fact in required_delivery_facts if fact not in text
        ]
        for relative_path, text in delivery_gate_docs.items()
    }
    missing_delivery_facts = {
        relative_path: facts
        for relative_path, facts in missing_delivery_facts.items()
        if facts
    }
    stale_delivery_claims = {
        relative_path: [
            stale
            for stale in STALE_DELIVERY_GATE_FACTS[relative_path]
            if _normalized(stale) in text
        ]
        for relative_path, text in delivery_gate_docs.items()
    }
    stale_delivery_claims = {
        relative_path: claims
        for relative_path, claims in stale_delivery_claims.items()
        if claims
    }

    assert missing_delivery_facts == {} and stale_delivery_claims == {}, (
        "W007 delivery-gate current facts are stale: "
        f"missing={missing_delivery_facts}, stale={stale_delivery_claims}"
    )
