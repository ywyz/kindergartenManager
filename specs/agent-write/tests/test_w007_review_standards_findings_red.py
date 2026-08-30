"""Stable RED for the W007 Standards Review findings."""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest

from app.service.agent.composition import DailyPlanAgentController
from app.service.agent.confirmed_write import (
    ConfirmedDailyPlanWriteResult,
    ConfirmedWriteRejected,
    PendingPlanPatchConfirmation,
)
from app.service.agent.confirmation_flow import (
    DailyPlanPatchConfirmationController,
    PatchConfirmationStatus,
)
from app.service.agent.contracts import DailyPlanScope, TrustedActor
from app.service.agent.patch import PlanPatch
from app.service.agent.runtime import AgentTurnOutcome, AgentTurnStatus

from conftest import (
    ACTOR_TENANT_ID,
    ACTOR_USER_ID,
    NOW,
    OPERATION_ID,
    PLAN_DATE,
    PLAN_ID,
    TURN_ID,
    build_patch,
    trusted_ui_session,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DAILY_PLAN_PAGE = REPOSITORY_ROOT / "app/ui/pages/daily_plan.py"

CAPABILITY_FACT_FILES = (
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
EVIDENCE_LEDGER_PATH = "specs/agent-write/tests/README.md"
CURRENT_GATE_FACTS = (
    "精确本地交付状态",
    "Review 轮次、SHA 与测试证据仅以",
    "Issue #52 仅在对应门回写后作为外部证据",
    "不复制",
    "逐轮事实",
)
CURRENT_BOUNDARY_FACTS = (
    "Provider/Tool 能力面仍恰好为四个 READ + 两个 DRAFT",
    "不得增加 Provider WRITE",
    "自动重试、批量或跨页面采用",
    "设置/文件/Word/删除/创建写入",
    "长期 Patch 持久化、新 Tool 或多 Agent",
)
CANONICAL_LEDGER_FACTS = (
    "`7bd5c11ccee6af26d55959803a0594ff0a277ccc`",
    "Standards H0/M3/L1、Spec H0/M0/L0",
    "`68e4c340e0188f456ff8bc1caca5181f07410b15`",
    "连续两轮均为 `7 failed`",
    "node hash",
    "`980d2c23c873546843b385700cbb1d4f4680d8aa5213eeccc5da02af2ef56052`",
)

SECOND_OPERATION_ID = UUID("abababab-abab-4bab-8bab-abababababab")
SECOND_TURN_ID = UUID("cdcdcdcd-cdcd-4dcd-8dcd-cdcdcdcdcdcd")


@dataclass(slots=True)
class _TwoPatchDraftCoordinator:
    """Publish two authoritative Patches through the existing Agent seam."""

    patches: tuple[PlanPatch, PlanPatch]

    async def execute(
        self,
        *,
        owner_id: UUID,
        actor: TrustedActor,
        scope: DailyPlanScope,
        intent: str,
        scope_reader: Callable[[], DailyPlanScope | None],
    ) -> AgentTurnOutcome:
        del owner_id, actor, intent
        assert scope_reader() == scope
        return AgentTurnOutcome(
            status=AgentTurnStatus.DRAFT_READY,
            assistant_content="同一页面 generation 的两份独立草案。",
            patches=self.patches,
        )

    def invalidate(self, owner_id: UUID) -> None:
        del owner_id

    def plan_changed(self, actor: TrustedActor, scope: DailyPlanScope) -> None:
        del actor, scope

    async def cancel(self, owner_id: UUID) -> bool:
        del owner_id
        return True


@dataclass(slots=True)
class _RecordingConfirmedWritePort:
    """Observe only calls crossing the frozen confirmed-write service port."""

    apply_error_code: str | None = None
    reconcile_error_code: str | None = None
    issue_patch_ids: list[UUID] = field(default_factory=list)
    apply_confirmation_ids: list[UUID] = field(default_factory=list)
    reconcile_confirmation_ids: list[UUID] = field(default_factory=list)
    _expected_revision_by_confirmation: dict[UUID, int] = field(
        default_factory=dict,
        repr=False,
    )

    async def issue_confirmation(
        self,
        ui_session: object,
        patch: PlanPatch,
        *,
        expected_revision: int,
    ) -> PendingPlanPatchConfirmation:
        del ui_session
        self.issue_patch_ids.append(patch.patch_id)
        confirmation_id = UUID(int=100 + len(self.issue_patch_ids))
        self._expected_revision_by_confirmation[confirmation_id] = expected_revision
        return PendingPlanPatchConfirmation(
            confirmation_id=confirmation_id,
            expires_at_utc=NOW + timedelta(minutes=4),
            daily_plan_id=patch.target.daily_plan_id,
            expected_revision=expected_revision,
            patch_id=patch.patch_id,
            patch_sha256=patch.canonical_sha256,
            field_paths=tuple(operation.field_path for operation in patch.operations),
        )

    async def apply(
        self,
        ui_session: object,
        confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult:
        del ui_session
        self.apply_confirmation_ids.append(confirmation_id)
        if self.apply_error_code is not None:
            raise ConfirmedWriteRejected(self.apply_error_code)
        expected_revision = self._expected_revision_by_confirmation[confirmation_id]
        return ConfirmedDailyPlanWriteResult(
            before_version_id=41,
            audit_id=42,
            before_revision=expected_revision,
            after_revision=expected_revision + 1,
        )

    async def reconcile(
        self,
        ui_session: object,
        confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult:
        del ui_session
        self.reconcile_confirmation_ids.append(confirmation_id)
        if self.reconcile_error_code is not None:
            raise ConfirmedWriteRejected(self.reconcile_error_code)
        expected_revision = self._expected_revision_by_confirmation[confirmation_id]
        return ConfirmedDailyPlanWriteResult(
            before_version_id=41,
            audit_id=42,
            before_revision=expected_revision,
            after_revision=expected_revision + 1,
        )


async def _two_patch_flow() -> tuple[
    DailyPlanPatchConfirmationController,
    _RecordingConfirmedWritePort,
    PlanPatch,
    PlanPatch,
]:
    patch_a = build_patch(
        operation_id=OPERATION_ID,
        turn_id=TURN_ID,
        after_goal="应用层终态草案 A",
    )
    patch_b = build_patch(
        operation_id=SECOND_OPERATION_ID,
        turn_id=SECOND_TURN_ID,
        after_goal="应用层终态草案 B",
    )
    assert patch_a.patch_id != patch_b.patch_id
    agent_controller = DailyPlanAgentController(
        coordinator=_TwoPatchDraftCoordinator((patch_a, patch_b)),  # type: ignore[arg-type]
        actor=TrustedActor(
            tenant_id=ACTOR_TENANT_ID,
            user_id=ACTOR_USER_ID,
        ),
    )
    agent_controller.scope_changed(PLAN_DATE)
    panel = await agent_controller.run("生成同一页面的两份独立草案")
    assert panel.status.value == "draft_ready"
    assert tuple(patch.patch_id for patch in panel.patches) == (
        patch_a.patch_id,
        patch_b.patch_id,
    )
    writer = _RecordingConfirmedWritePort()
    return (
        DailyPlanPatchConfirmationController(
            agent_controller=agent_controller,
            write_service=writer,
        ),
        writer,
        patch_a,
        patch_b,
    )


def _normalized(text: str) -> str:
    return "".join(text.replace(">", "").split())


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
            isinstance(decorator_name, ast.Name) and decorator_name.id == "dataclass"
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
        node.id for node in ast.walk(functions[0].returns) if isinstance(node, ast.Name)
    }
    service_classes = {
        node.name: node for node in service_tree.body if isinstance(node, ast.ClassDef)
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
        f"W007 UI callback crosses the database/repository/ORM boundary: {forbidden}"
    )
    assert service_calls, (
        "W007 authoritative reload must call an app.service projection"
    )
    assert any(_returns_frozen_dto(call) for call in service_calls), (
        "W007 authoritative reload service must return a frozen DTO: "
        f"{sorted(service_calls)}"
    )


def test_w007_current_facts_keep_boundary_and_canonical_pointer() -> None:
    normalized_docs = {
        relative_path: _normalized(
            (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        )
        for relative_path in CAPABILITY_FACT_FILES
    }
    required_facts = (
        EVIDENCE_LEDGER_PATH,
        *CURRENT_GATE_FACTS,
        *CURRENT_BOUNDARY_FACTS,
    )
    missing_facts = {
        relative_path: [
            fact for fact in required_facts if _normalized(fact) not in content
        ]
        for relative_path, content in normalized_docs.items()
    }
    missing_facts = {
        relative_path: facts for relative_path, facts in missing_facts.items() if facts
    }

    ledger = _normalized(
        (REPOSITORY_ROOT / EVIDENCE_LEDGER_PATH).read_text(encoding="utf-8")
    )
    missing_ledger_facts = [
        fact for fact in CANONICAL_LEDGER_FACTS if _normalized(fact) not in ledger
    ]

    assert missing_facts == {}, (
        f"W007 capability/gate facts or canonical pointer missing: {missing_facts}"
    )
    assert missing_ledger_facts == [], (
        f"W007 canonical evidence ledger is incomplete: {missing_ledger_facts}"
    )


@pytest.mark.asyncio
async def test_w007_flow_keeps_a_terminal_after_b_terminal() -> None:
    """A page-local terminal Patch cannot regain a WRITE issue path via B."""
    flow, writer, patch_a, patch_b = await _two_patch_flow()
    ui_session = trusted_ui_session()
    writer.apply_error_code = "write_failed"

    for patch in (patch_a, patch_b):
        pending = await flow.issue(
            ui_session,
            patch.patch_id,
            expected_plan_id=PLAN_ID,
            expected_revision=1,
        )
        assert pending.status is PatchConfirmationStatus.PENDING
        terminal = await flow.apply(ui_session)
        assert terminal.status is PatchConfirmationStatus.FAILED
        assert terminal.error_code == "write_failed"

    reissued_a = await flow.issue(
        ui_session,
        patch_a.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )

    assert {
        "status": reissued_a.status,
        "patch_id": reissued_a.patch_id,
        "error_code": reissued_a.error_code,
        "writer_issue_patch_ids": tuple(writer.issue_patch_ids),
    } == {
        "status": PatchConfirmationStatus.FAILED,
        "patch_id": patch_a.patch_id,
        "error_code": "write_failed",
        "writer_issue_patch_ids": (patch_a.patch_id, patch_b.patch_id),
    }


@pytest.mark.asyncio
async def test_w007_flow_latches_integrity_failure_across_patches() -> None:
    """Integrity failure closes every Patch at the application flow seam."""
    flow, writer, patch_a, patch_b = await _two_patch_flow()
    ui_session = trusted_ui_session()

    pending = await flow.issue(
        ui_session,
        patch_a.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )
    assert pending.status is PatchConfirmationStatus.PENDING

    writer.apply_error_code = "commit_outcome_unknown"
    unknown = await flow.apply(ui_session)
    assert unknown.status is PatchConfirmationStatus.INDETERMINATE

    writer.reconcile_error_code = "reconcile_integrity_failure"
    integrity_failure = await flow.reconcile(ui_session)
    assert integrity_failure.status is PatchConfirmationStatus.FAILED
    assert integrity_failure.error_code == "reconcile_integrity_failure"

    blocked_b = await flow.issue(
        ui_session,
        patch_b.patch_id,
        expected_plan_id=PLAN_ID,
        expected_revision=1,
    )

    assert {
        "status": blocked_b.status,
        "patch_id": blocked_b.patch_id,
        "error_code": blocked_b.error_code,
        "writer_issue_patch_ids": tuple(writer.issue_patch_ids),
    } == {
        "status": PatchConfirmationStatus.FAILED,
        "patch_id": patch_a.patch_id,
        "error_code": "reconcile_integrity_failure",
        "writer_issue_patch_ids": (patch_a.patch_id,),
    }
