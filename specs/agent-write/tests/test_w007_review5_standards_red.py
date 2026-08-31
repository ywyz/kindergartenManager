"""Stable fifth-review RED for W007 privacy, typing, and evidence hygiene."""

from __future__ import annotations

import ast
from dataclasses import fields
from datetime import date
from pathlib import Path
import re
from typing import TYPE_CHECKING

from app.service.agent.confirmed_plan_read import ConfirmedDailyPlanProjection
from app.service.agent.confirmation_flow import PatchConfirmationSnapshot

if TYPE_CHECKING:
    from app.service.agent.confirmation_flow import (
        DailyPlanPatchConfirmationController,
    )
    from app.ui.components.agent_write_confirmation import (
        PatchConfirmationController,
    )

    def _controller_port_witness(
        controller: DailyPlanPatchConfirmationController,
    ) -> PatchConfirmationController:
        """Keep the concrete controller statically assignable to the UI port."""
        return controller


PROJECT_ROOT = Path(__file__).resolve().parents[3]
UI_PORT_PATH = PROJECT_ROOT / "app/ui/components/agent_write_confirmation.py"
EVIDENCE_LEDGER = PROJECT_ROOT / "specs/agent-write/tests/README.md"
EVIDENCE_LEDGER_REF = "specs/agent-write/tests/README.md"
CAPABILITY_DOCS = (
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
# These prefixes identify the integrated baseline, release workflow, or an older
# architecture baseline. They are current-state references, not W007 review
# lineage copied from the canonical evidence ledger.
NON_W007_LINEAGE_PREFIXES = frozenset({"ca3b7bd", "ec592de", "3331263"})
SNAPSHOT_FIELDS = (
    "status",
    "patch_id",
    "patch_sha256",
    "daily_plan_id",
    "expected_revision",
    "expires_at_utc",
    "field_paths",
    "before_revision",
    "after_revision",
    "error_code",
)
CONTROLLER_MEMBERS = (
    "snapshot",
    "issue",
    "apply",
    "reconcile",
    "invalidate",
    "disconnect",
    "close",
)


def _class_node(module: ast.Module, name: str) -> ast.ClassDef:
    return next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == name
    )


def _function_nodes(
    class_node: ast.ClassDef,
) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        node.name: node
        for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _is_property(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        isinstance(decorator, ast.Name) and decorator.id == "property"
        for decorator in node.decorator_list
    )


def _is_ellipsis_stub(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = list(node.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body.pop(0)
    return bool(
        len(body) == 1
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and body[0].value.value is Ellipsis
    )


def test_confirmed_projection_repr_hides_body_but_keeps_safe_identity() -> None:
    private_marker = "W007_PRIVATE_DAILY_PLAN_BODY"
    projection = ConfirmedDailyPlanProjection(
        plan_id=901,
        plan_date=date(2026, 8, 27),
        revision=7,
        activity_goal=private_marker,
        activity_prep=private_marker,
        activity_key=private_marker,
        activity_difficult=private_marker,
        activity_process_original=private_marker,
        activity_process_adapted=private_marker,
        morning_activity=private_marker,
        morning_talk_topic=private_marker,
        morning_talk_questions=private_marker,
        indoor_area=private_marker,
        outdoor_activity=private_marker,
        daily_reflection=private_marker,
    )

    rendered = repr(projection)

    assert private_marker not in rendered
    assert "plan_id=901" in rendered
    assert "plan_date=" in rendered
    assert "revision=7" in rendered


def test_confirmation_ports_are_read_only_real_protocol_stubs() -> None:
    module = ast.parse(UI_PORT_PATH.read_text(encoding="utf-8"))
    snapshot_node = _class_node(module, "PatchConfirmationSnapshotView")
    controller_node = _class_node(module, "PatchConfirmationController")
    snapshot_methods = _function_nodes(snapshot_node)
    controller_methods = _function_nodes(controller_node)
    violations: list[str] = []

    for name in SNAPSHOT_FIELDS:
        method = snapshot_methods.get(name)
        if method is None or not _is_property(method) or not _is_ellipsis_stub(method):
            violations.append(f"snapshot.{name} must be a read-only property stub")

    for name in CONTROLLER_MEMBERS:
        method = controller_methods.get(name)
        if method is None or not _is_ellipsis_stub(method):
            violations.append(f"controller.{name} must be an ellipsis Protocol stub")
        if name == "snapshot" and method is not None and not _is_property(method):
            violations.append("controller.snapshot must stay read-only")

    concrete_fields = {field.name for field in fields(PatchConfirmationSnapshot)}
    missing_concrete_fields = set(SNAPSHOT_FIELDS) - concrete_fields
    if missing_concrete_fields:
        violations.append(
            "concrete snapshot misses view fields: "
            + ", ".join(sorted(missing_concrete_fields))
        )

    # Pytest verifies the public shape without requiring a machine-global type
    # checker. The TYPE_CHECKING witness above and the focused Pyright command in
    # this finding's evidence verify concrete return covariance and daily-plan
    # Optional narrowing.
    assert not violations, "\n".join(violations)


def test_w007_detailed_lineage_has_one_canonical_evidence_ledger() -> None:
    ledger = EVIDENCE_LEDGER.read_text(encoding="utf-8")
    w007_lineage = ledger.split("## 2026-08-26 W007 RED 证据", maxsplit=1)[1]
    historical_prefixes = {
        token[:7] for token in re.findall(r"`([0-9a-f]{7,64})(?:…)?`", w007_lineage)
    }
    write_pass_counts = set(
        re.findall(r"WRITE[^\n]{0,40}?`?(\d+) passed", w007_lineage)
    )
    violations: list[str] = []

    assert historical_prefixes, "canonical W007 ledger must retain its lineage"
    for relative_path in CAPABILITY_DOCS:
        content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        if EVIDENCE_LEDGER_REF not in content:
            violations.append(f"{relative_path}: missing canonical ledger pointer")
        copied_prefixes = sorted(
            prefix
            for prefix in historical_prefixes - NON_W007_LINEAGE_PREFIXES
            if prefix in content
        )
        # A capability document may cite the one current candidate/fixed SHA;
        # the complete ancestry belongs only in the evidence ledger.
        if len(copied_prefixes) > 1:
            violations.append(
                f"{relative_path}: duplicates W007 historical evidence "
                + ", ".join(copied_prefixes)
            )
        copied_write_counts = sorted(
            count for count in write_pass_counts if f"WRITE `{count} passed`" in content
        )
        # Likewise, retain at most the current aggregate count at the point of
        # delivery rather than cloning every intermediate test baseline.
        if len(copied_write_counts) > 1:
            violations.append(
                f"{relative_path}: duplicates W007 WRITE pass lineage "
                + ", ".join(copied_write_counts)
            )

    assert not violations, "\n".join(violations)
