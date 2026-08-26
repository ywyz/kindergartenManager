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
    "W007 第四轮 Review 与多轮独立 precheck finding RED 已固定，当前仍待最终"
    "提交前独立 precheck 与第五轮 fixed-SHA 双轴 Review；W008 未进入"
)
INITIAL_GREEN_BASELINE_FACT = (
    "W007 初始 GREEN commit 本地基线为 WRITE `99 passed`、Foundation "
    "`261 passed`、ordinary `847 passed`"
)
FIRST_REVIEW_REPAIR_BASELINE_FACT = (
    "首轮 fixed-SHA Review 为 Standards M2、Spec M1/L1；`cf38725` 后修正"
    "基线为 WRITE `110 passed`、Foundation `261 passed`、ordinary `847 passed`"
)
SECOND_REVIEW_GATE_FACT = (
    "二轮 fixed-SHA Review 为 Standards M1、Spec M1/L1，finding RED 已由 "
    "`40f25b7` 固定；`40f25b7` 后修正基线为 WRITE `112 passed`、Foundation "
    "`261 passed`、ordinary `847 passed`"
)
THIRD_REVIEW_GATE_FACT = (
    "三轮 fixed-SHA Review 为 Standards M1、Spec M1，finding RED 已由 "
    "`43636a0` 固定；`43636a0` 后修正基线为 WRITE `113 passed`、Foundation "
    "`261 passed`、ordinary `847 passed`"
)
PRECOMMIT_IDENTITY_FINDING_FACT = (
    "提交前终态 identity 审计发现 M1，finding RED 已由 `9972aab` 固定"
)
FOURTH_REVIEW_FINDING_FACT = (
    "第四轮 fixed-SHA 双轴 Review 绑定 "
    "`bc742d6c64744234f2702622fd4dbb1988b5650d`，结果为 Standards H0/M1/L0、"
    "Spec H0/M1/L0"
)
FOURTH_REVIEW_BASELINE_FACT = (
    "`bc742d6c64744234f2702622fd4dbb1988b5650d` 的统一测试基线为 WRITE "
    "`115 passed`、Foundation `261 passed`、ordinary `847 passed`"
)
FOURTH_REVIEW_FINDING_RED_FACT = (
    "finding RED 已由 `a58c719796e9136a55932c59c930f1f0c98f14b9` 固定"
)
FOURTH_REVIEW_FINDING_RED_RESULT_FACTS = (
    "稳定为 `10 failed / 9 passed`",
    "node hash `eae4be37be04be28ba2647bac31e1ff57d871810fd29c1437e5c100c2261b7a5`",
)
FIRST_PRECHECK_CANDIDATE_BASELINE_FACT = (
    "`a58c719796e9136a55932c59c930f1f0c98f14b9` 后第一版修复候选统一测试为 "
    "WRITE `125 passed`、Foundation `261 passed`、ordinary `847 passed`"
)
PRECHECK_FINDING_FACTS = (
    "提交前只读 precheck 发现 3M/1L",
    "异 Patch 并发 issue",
    "wrong-plan/invalid-revision exact identity",
    "session guard 迟发 success",
    "close/capability cleanup",
    "finding RED 已由 `e8722f843f99aea4eb3321b06ad8074728adfd4a` 固定",
    "连续两轮为 `6 failed / 15 passed`",
    "combined node hash `157c6a8aed7025a7963af47ef1bcf5f0f332b44be37867fe006d4084de5d796a`",
)
SECOND_PRECHECK_CANDIDATE_BASELINE_FACT = (
    "`e8722f843f99aea4eb3321b06ad8074728adfd4a` 后第二版修复候选统一测试为 "
    "WRITE `131 passed`、Foundation `261 passed`、ordinary `847 passed`"
)
CANCELLATION_SESSION_PRECHECK_FINDING_FACTS = (
    "取消/会话 precheck 复核发现 3M",
    "same-key joiner cancel 取消 owner/shared task",
    "cancelled close/disconnect 跳过 cleanup",
    "commit-unknown 后 session 变化仍重开旧 reconcile",
    "finding RED 已由 `ce8b7756eb1fc1069f4d31109d49dd6d7cccc14f` 固定",
    "连续两轮为 `5 failed / 21 passed`",
    "combined node hash `56d901193c517d284526b39f61a1f0286587ca20d7276838bc0c4a7859ece345`",
)
THIRD_PRECHECK_CANDIDATE_BASELINE_FACT = (
    "`ce8b7756eb1fc1069f4d31109d49dd6d7cccc14f` 后第三版修复候选统一测试为 "
    "WRITE `136 passed`、Foundation `261 passed`、ordinary `847 passed`"
)
INDEPENDENT_CANCELLATION_STATE_AUDIT_FACTS = (
    "独立取消状态审计为 H0/M2",
    "owner cancel 若 inner 吞取消/抛 BaseException 可迟发 APPLIED 或留 PENDING 重放",
    "controller/UI 并发 close/disconnect 无共享 completion barrier",
    "finding RED 已由 `149d45e0fb4a1b7110c3fb3676a4e44d495e810c` 固定",
    "连续两轮为 `8 failed / 26 passed`",
    "combined node hash `e12d635b2fa86999ce626d2763a81f4b9063c5ad83c42176f913b399464ce29b`",
)
FOURTH_PRECHECK_CANDIDATE_BASELINE_FACT = (
    "`149d45e0fb4a1b7110c3fb3676a4e44d495e810c` 后第四版修复候选统一测试为 "
    "WRITE `144 passed`、Foundation `261 passed`、ordinary `847 passed`"
)
GREEN_PRECHECK_FINDING_FACTS = (
    "独立 GREEN precheck 结果为 Standards H0/M0、Spec H0/M1",
    "inner issue 已完成但 owner cancel 在 shield 投递前使 same-key joiner 拿旧 PENDING",
    "finding RED 已由 `c20aaa2f2b0c276bf985bb3d8ecf3fca4b364504` 固定",
    "单节点连续两轮均为 `1 failed`",
    "node hash `1a6cf115cba623fcef1e99cd11d5d3d1cdd8698717f01ec9d4b9971389e49a35`",
)
FIFTH_PRECHECK_CANDIDATE_BASELINE_FACT = (
    "`c20aaa2f2b0c276bf985bb3d8ecf3fca4b364504` 后第五版修复候选统一测试为 "
    "WRITE `145 passed`、Foundation `261 passed`、ordinary `847 passed`"
)
SUCCESSOR_PATCH_IDENTITY_PRECHECK_FACTS = (
    "后继 Patch identity 独立 precheck 结果为 Standards H0/M0、Spec H0/M1",
    "无条件 current snapshot 让旧 apply/reconcile joiner 收到后继 Patch B",
    "finding RED 已由 `827b1113f1679b9b5af4736652c91d6742a63fc4` 固定",
    "代表节点连续两轮均为 `1 failed`",
    "node hash `29b35e46c1ee8f3bc872b09eaf1fcb23fa959e8d4c61b8b5b5b93f9506f551c5`",
    "per-flight cancellation override",
    "两个新节点 `2 passed`、finding 两文件 `36 passed`",
)
SIXTH_PRECHECK_CANDIDATE_BASELINE_FACT = (
    "`827b1113f1679b9b5af4736652c91d6742a63fc4` 后第六版修复候选统一测试为 "
    "WRITE `146 passed`、Foundation `261 passed`、ordinary `847 passed`"
)
LIFECYCLE_WAITER_PRECHECK_FACTS = (
    "后续独立 precheck 发现 Spec M1",
    "done-but-undelivered issue waiter 在 explicit invalidate/close 后仍发布旧 PENDING",
    "finding RED 已由 `b2f91e7c604e92f1ae8461e709399c3842ac6c43` 固定",
    "invalidate/close 两参数连续两轮均为 `2 failed`",
    "combined node hash `f0f3a9b8ea6c99674746d7b8c8fc9d80342b097b5b21c097be40e09a833146b8`",
    "live per-flight waiter registry + lifecycle override",
    "新增 `2 passed`、finding 两文件 `38 passed`",
)
SEVENTH_PRECHECK_CANDIDATE_BASELINE_FACT = (
    "`b2f91e7c604e92f1ae8461e709399c3842ac6c43` 后第七版修复候选统一测试为 "
    "WRITE `148 passed`、Foundation `261 passed`、ordinary `847 passed`"
)
SUPPRESS_FAILURE_AUDIT_FACTS = (
    "独立 lifecycle/cancel 审计为 H0/M2",
    "pre-start cancel non-caller 分支把旧 A waiter 投到后继 B",
    "close/disconnect 的 BaseException 穿透并由 traceback 保留 writer",
    "finding RED 已由 `7d51d63994ceaf939833fc9679db31de3f21baf7` 固定",
    "3 节点连续两轮均为 `3 failed`",
    "combined node hash `d66294717711ef2581d15bcaa1ebe76754267d7d825acdb847574c16da01cf42`",
    "suppress_failure 区分显式 lifecycle/cancel override 与 spontaneous BaseException",
    "`3 passed`、finding 两文件 `41 passed`",
)
EIGHTH_PRECHECK_CANDIDATE_BASELINE_FACT = (
    "`7d51d63994ceaf939833fc9679db31de3f21baf7` 后第八版修复候选统一测试为 "
    "WRITE `151 passed`、Foundation `261 passed`、ordinary `847 passed`"
)
SHIELD_LOOP_HANDLER_AUDIT_FACTS = (
    "joiner-cancel 后 shield loop handler 原始异常泄漏，审计 H0/M1",
    "finding RED 已由 `bb539771f477e068d86e5bc3790f2a503e275ce9` 固定",
    "单节点连续两轮均为 `1 failed`",
    "node hash `915ad0796ad3b8ca96ae4c2efe0e8f2ed4946d0c4e4c5875dfafd19920f866ba`",
    "asyncio.wait + task.result 替代 per-waiter shield",
    "保留 owner spontaneous BaseException",
    "新增 `1 passed`、finding 两文件 `42 passed`",
)
NINTH_PRECHECK_CANDIDATE_BASELINE_FACT = (
    "`bb539771f477e068d86e5bc3790f2a503e275ce9` 后第九版修复候选统一测试为 "
    "WRITE `152 passed`、Foundation `261 passed`、ordinary `847 passed`"
)
OWNER_IDENTITY_AUDIT_FACTS = (
    "owner identity 独立审计为 H0/M1",
    "joiner cancel 先 finally 清全局 `_inflight_owner`",
    "随后 owner cancel 无法收敛，controller/repeat 留 PENDING（20/20）",
    "finding RED 已由 `21c0a9e6a4ed4f8e7a6e91584d4b8cdba37a2d24` 固定",
    "单节点连续两轮均为 `1 failed`",
    "node hash `95dba951ab937642ec1518f5af44dcc5e58ec3d9c146e7c210339bd2d533dfd2`",
    "`_FlightState.owner` + 仅 owner finally 释放 current flight",
    "代表节点 `1 passed`、finding 两文件 `43 passed`",
)
CURRENT_REPAIR_BASELINE_FACT = "本轮最终修复候选统一测试为 WRITE `153 passed`"
FIFTH_REVIEW_FIXED_GATE_FACT = (
    "本轮修复已固定在当前 SHA，当前仍待最终提交前独立 precheck 与第五轮 "
    "fixed-SHA 双轴 Review"
)
FIFTH_REVIEW_GATE_FACT_FILES = (
    "docs/ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md",
    "specs/agent-write/spec.md",
)
STALE_CURRENT_CANDIDATE_FACTS = (
    "本轮修复候选经统一测试为 WRITE `113 passed`",
    "本轮最终修复候选统一测试为 WRITE `115 passed`",
    "本轮最终修复候选统一测试为 WRITE `125 passed`",
    "本轮最终修复候选统一测试为 WRITE `131 passed`",
    "本轮最终修复候选统一测试为 WRITE `136 passed`",
    "本轮最终修复候选统一测试为 WRITE `144 passed`",
    "本轮最终修复候选统一测试为 WRITE `145 passed`",
    "本轮最终修复候选统一测试为 WRITE `146 passed`",
    "本轮最终修复候选统一测试为 WRITE `148 passed`",
    "本轮最终修复候选统一测试为 WRITE `151 passed`",
    "本轮最终修复候选统一测试为 WRITE `152 passed`",
)
STALE_FOURTH_REVIEW_WAIT_FACTS = (
    "本轮修复已固定在当前 SHA，当前门是第四轮 fixed-SHA 双轴 Review",
    "本轮修复已固定在当前 SHA，当前门是第五轮 fixed-SHA 双轴 Review",
    "本轮修复已固定在当前 SHA，当前仍待下一次提交前独立 precheck 与第五轮 fixed-SHA 双轴 Review",
    "等待第四轮 fixed-SHA 双轴 Review",
    "下一门是第四轮 fixed-SHA 双轴 Review",
)
STALE_CURRENT_FACTS = {
    "AGENTS.md": (
        "The current authorized slice ends after",
        "Until an explicit later GREEN gate",
        "下一门是第三轮 fixed-SHA 双轴 Review",
    ),
    "CONTEXT.md": (
        "W007 UI adapter 正在 GREEN 实现",
        "完成 W007 当前页面单 Patch 确认 UI 的最小 GREEN commit",
        "下一门是第三轮 fixed-SHA 双轴 Review",
        "等待第三轮 fixed-SHA 双轴 Review",
        "第三轮 fixed-SHA 双轴 Review、push",
    ),
    "docs/ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md": (
        "W007 当前只有稳定 RED",
        "W007 GREEN commit →",
        "固定本修正候选 commit",
        "等待第三轮 fixed-SHA 双轴 Review",
        "当前门是第三轮 fixed-SHA 双轴 Review",
        "执行第三轮双轴 Review",
    ),
    "docs/design/data-model.md": (
        "稳定 RED 并正在 GREEN 实现",
        "W007 产品 UI 正在 GREEN 实现",
        "仍须执行第三轮 fixed-SHA 双轴 Review",
        "尚未获得第三轮 fixed-SHA Review",
    ),
    "docs/design/system-architecture.md": (
        "W007 UI 正在 GREEN 实现",
        "W007 仍只有稳定 RED 与进行中的 GREEN 实现",
        "当前门是 W007 单 Patch UI GREEN",
        "等待第三轮 fixed-SHA 双轴 Review",
        "须在 fixed SHA 执行第三轮双轴 Review",
        "执行第三轮双轴 Review",
    ),
    "specs/agent-write/spec.md": (
        "须先形成 GREEN commit",
        "W007 候选必须依序经过：最小 GREEN commit",
        "固定本修正候选 commit",
        "当前须先固定本修正候选 commit",
        "执行第三轮双轴 Review",
    ),
}
STALE_DELIVERY_GATE_FACTS = {
    "docs/ROADMAP.md": (
        "当前 GREEN 候选为 WRITE `99 passed`",
        "不预宣称 fixed-SHA Review",
        "finding 修正候选当前本地 WRITE",
        "并等待 fixed-SHA 复审",
        "下一门是第三轮 fixed-SHA 双轴 Review",
        "等待第三轮 fixed-SHA 双轴 Review",
    ),
    "specs/agent-write/tasks.md": (
        "GREEN 候选：稳定 RED `e5f7317…` 后本地 WRITE 99",
        "待 fixed-SHA Review/push/CI/验收/Issue",
        "finding 修正候选当前本地 WRITE",
        "并等待 fixed-SHA 复审",
        "下一门是第三轮 fixed-SHA 双轴 Review",
        "待第三轮 fixed-SHA 双轴 Review",
    ),
    "specs/agent-write/tests/README.md": (
        "GREEN 候选现为 WRITE `99 passed`",
        "尚未取得 fixed-SHA Review",
        "finding 修正候选当前本地 WRITE",
        "并等待 fixed-SHA 复审",
        "下一门是第三轮 fixed-SHA 双轴 Review",
    ),
    "memory-bank/architecture.md": (
        "GREEN 候选现为 WRITE `99 passed`",
        "finding 修正候选当前本地 WRITE",
        "并等待 fixed-SHA 复审",
        "下一门是第三轮 fixed-SHA 双轴 Review",
    ),
}

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
    missing_fifth_review_gate_fact = [
        relative_path
        for relative_path in FIFTH_REVIEW_GATE_FACT_FILES
        if FIFTH_REVIEW_FIXED_GATE_FACT not in normalized_docs[relative_path]
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

    assert missing_gate_fact == [] and missing_fifth_review_gate_fact == [], (
        "current W007 gate fact missing from: "
        f"committed_green={missing_gate_fact}, "
        f"fifth_review={missing_fifth_review_gate_fact}"
    )
    assert stale_claims == {}, (
        f"contradictory W007 current facts remain: {stale_claims}"
    )

    delivery_gate_docs = {
        relative_path: _normalized(
            (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        )
        for relative_path in DELIVERY_GATE_FACT_FILES
    }
    all_current_docs = normalized_docs | delivery_gate_docs
    required_current_progress_facts = (
        THIRD_REVIEW_GATE_FACT,
        PRECOMMIT_IDENTITY_FINDING_FACT,
        FOURTH_REVIEW_FINDING_FACT,
        FOURTH_REVIEW_BASELINE_FACT,
        FOURTH_REVIEW_FINDING_RED_FACT,
        *FOURTH_REVIEW_FINDING_RED_RESULT_FACTS,
        FIRST_PRECHECK_CANDIDATE_BASELINE_FACT,
        *PRECHECK_FINDING_FACTS,
        SECOND_PRECHECK_CANDIDATE_BASELINE_FACT,
        *CANCELLATION_SESSION_PRECHECK_FINDING_FACTS,
        THIRD_PRECHECK_CANDIDATE_BASELINE_FACT,
        *INDEPENDENT_CANCELLATION_STATE_AUDIT_FACTS,
        FOURTH_PRECHECK_CANDIDATE_BASELINE_FACT,
        *GREEN_PRECHECK_FINDING_FACTS,
        FIFTH_PRECHECK_CANDIDATE_BASELINE_FACT,
        *SUCCESSOR_PATCH_IDENTITY_PRECHECK_FACTS,
        SIXTH_PRECHECK_CANDIDATE_BASELINE_FACT,
        *LIFECYCLE_WAITER_PRECHECK_FACTS,
        SEVENTH_PRECHECK_CANDIDATE_BASELINE_FACT,
        *SUPPRESS_FAILURE_AUDIT_FACTS,
        EIGHTH_PRECHECK_CANDIDATE_BASELINE_FACT,
        *SHIELD_LOOP_HANDLER_AUDIT_FACTS,
        NINTH_PRECHECK_CANDIDATE_BASELINE_FACT,
        *OWNER_IDENTITY_AUDIT_FACTS,
        CURRENT_REPAIR_BASELINE_FACT,
    )
    missing_current_progress_facts = {
        relative_path: [
            fact for fact in required_current_progress_facts if fact not in text
        ]
        for relative_path, text in all_current_docs.items()
    }
    missing_current_progress_facts = {
        relative_path: facts
        for relative_path, facts in missing_current_progress_facts.items()
        if facts
    }
    stale_current_candidates = {
        relative_path: [
            stale for stale in STALE_CURRENT_CANDIDATE_FACTS if stale in text
        ]
        for relative_path, text in all_current_docs.items()
    }
    stale_current_candidates = {
        relative_path: facts
        for relative_path, facts in stale_current_candidates.items()
        if facts
    }
    stale_fourth_review_waits = {
        relative_path: [
            stale
            for stale in STALE_FOURTH_REVIEW_WAIT_FACTS
            if _normalized(stale) in text
        ]
        for relative_path, text in all_current_docs.items()
    }
    stale_fourth_review_waits = {
        relative_path: facts
        for relative_path, facts in stale_fourth_review_waits.items()
        if facts
    }
    required_delivery_facts = (
        INITIAL_GREEN_BASELINE_FACT,
        FIRST_REVIEW_REPAIR_BASELINE_FACT,
        SECOND_REVIEW_GATE_FACT,
    )
    missing_delivery_facts = {
        relative_path: [fact for fact in required_delivery_facts if fact not in text]
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

    assert (
        missing_current_progress_facts == {}
        and stale_current_candidates == {}
        and stale_fourth_review_waits == {}
        and missing_delivery_facts == {}
        and stale_delivery_claims == {}
    ), (
        "W007 delivery-gate current facts are stale: "
        f"missing_progress={missing_current_progress_facts}, "
        f"stale_current_candidates={stale_current_candidates}, "
        f"stale_fourth_review_waits={stale_fourth_review_waits}, "
        f"missing_history={missing_delivery_facts}, stale={stale_delivery_claims}"
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
