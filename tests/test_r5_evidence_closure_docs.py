"""Stable documentation contracts for the R5-P evidence closure."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
LEDGER = ROOT / "specs/operations-r5/evidence-ledger.md"

SOURCE_SHA = "f4687f05e8fdca5d22f5921922ec5c77a4d28bea"
ISOLATED_TESTED_CODE_SHA = "340d23d1581038056ce3eed27517fb1d5a953175"
R5_R_TESTED_CODE_SHA = "b329bf6cf4bbf5518390644b24908ce29bd16894"
R5_R_CLOSURE_SHA = "8b06f89bf8a7533788bec8e4d19c2be4ae289541"
TAG = "v3.4.0-beta9"
REPOSITORY = "ghcr.io/ywyz/kindergartenmanager"
DIGEST = "sha256:bfa93aebe5ea617a62c98e095e5cd18c5573dbd10a3fca936aeb753e66545bfe"
IMMUTABLE_REF = f"{REPOSITORY}@{DIGEST}"


def _ledger() -> str:
    return LEDGER.read_text(encoding="utf-8")


def test_r5_p_release_tuple_and_exact_source_runs_are_frozen() -> None:
    ledger = _ledger()

    for fact in (TAG, SOURCE_SHA, REPOSITORY, DIGEST, IMMUTABLE_REF):
        assert fact in ledger
    assert "application/vnd.oci.image.index.v1+json" in ledger
    assert "仅 `linux/amd64`、`linux/arm64`" in ledger
    assert "actions/runs/33607674505" in ledger
    assert "actions/runs/33607924279" in ledger
    assert "releases/tag/v3.4.0-beta9" in ledger


def test_r5_p_six_evidence_classes_are_independent_and_passed() -> None:
    ledger = _ledger()
    evidence_rows = (
        "1. exact-SHA CI",
        "2. OCI / Release 元数据收敛",
        "3. 隔离 migration → target failure → old-image rollback",
        "4. 生产新鲜备份",
        "5. 生产故障注入与 beta5 回切",
        "6. 最终 beta9 部署与验收",
    )

    for label in evidence_rows:
        row = next(line for line in ledger.splitlines() if f"| {label} |" in line)
        assert "| `PASS` |" in row
    assert (
        "dry-run、本地测试、source exact-SHA CI、生产验收和 Release closure" in ledger
    )
    assert "互不替代" in ledger


def test_r5_p_release_and_isolation_sha_bindings_are_not_conflated() -> None:
    ledger = _ledger()
    r5_p_row = next(
        line
        for line in ledger.splitlines()
        if "| D | R5-P release/digest/deploy/rollback 收敛 |" in line
    )

    assert f"`release_source_sha={SOURCE_SHA}`" in r5_p_row
    assert f"`isolated_tested_code_sha={ISOLATED_TESTED_CODE_SHA}`" in r5_p_row
    assert "隔离 migration/failure/rollback 绑定独立 tested SHA" in r5_p_row


def test_r5_p_failure_injection_and_final_acceptance_contracts_are_frozen() -> None:
    ledger = _ledger()
    isolation_row = next(
        line
        for line in ledger.splitlines()
        if "| 3. 隔离 migration → target failure → old-image rollback |" in line
    )
    rollback_row = next(
        line
        for line in ledger.splitlines()
        if "| 5. 生产故障注入与 beta5 回切 |" in line
    )
    final_row = next(
        line for line in ledger.splitlines() if "| 6. 最终 beta9 部署与验收 |" in line
    )

    assert f"`tested_code_sha={ISOLATED_TESTED_CODE_SHA}`" in isolation_row
    assert (
        "receipt、目标故障、旧镜像在新 schema 的完整验收及 state 不变" in isolation_row
    )
    for claim in (
        "beta5 基线先通过双探针、登录和业务矩阵",
        "只拒绝 beta9 `target/business`",
        "deploy 非零后自动恢复 beta5",
        "rollback 双探针、登录与业务矩阵通过",
        "state 原始字节不变",
        "wrapper 随后删除且原 runner 保留",
    ):
        assert claim in rollback_row
    for claim in (
        "live image/state current 均为 immutable ref",
        "app/MySQL running、healthy、未暂停",
        "liveness `200/ok`、readiness `200/ready`",
        "每日计划、游戏观察、一对一倾听、自制教玩具、课程审议、图片 BLOB、AI key 解密、Word 导出和数据快照均 passed",
    ):
        assert claim in final_row


def test_issue_54_stays_open_and_digest_delivery_is_out_of_scope() -> None:
    ledger = _ledger()

    assert "Issue #54 仍为 OPEN" in ledger
    assert "digest 部署/回滚自动化是其明确非目标" in ledger
    assert "不能推断或操作 Issue 关闭" in ledger


def test_r5_r_history_is_not_rewritten_as_r5_p_evidence() -> None:
    ledger = _ledger()
    r5_r_row = next(
        line for line in ledger.splitlines() if "| C | R5-R 备份与恢复 |" in line
    )

    assert R5_R_TESTED_CODE_SHA in r5_r_row
    assert R5_R_CLOSURE_SHA in r5_r_row
    assert SOURCE_SHA not in r5_r_row
    assert "R5-R 的 `tested_code_sha=" + R5_R_TESTED_CODE_SHA in ledger


def test_closure_sha_is_formed_after_commit_and_requires_its_own_ci() -> None:
    ledger = _ledger()

    assert "commit 产生前不得预填或猜测 SHA" in ledger
    assert "提交后用 `git rev-parse HEAD` 回读" in ledger
    assert "不通过第二个文档 commit 自引用" in ledger
    assert "PRODUCTION_CLOSED / CLOSURE_CI_PENDING" in ledger


def test_graphify_failure_is_explicit_and_old_graph_is_not_evidence() -> None:
    ledger = _ledger()

    assert "Graphify | `unavailable`" in ledger
    assert "OpenAI-compatible → DeepSeek → `luna_worker`" in ledger
    assert "旧图、旧 diagnostics 和 partial 输出均不" in ledger
    assert "支持 `PRODUCTION_CLOSED` 或最终 closure 声明" in ledger


def test_authoritative_status_docs_record_production_closure_without_closing_issue_54() -> (
    None
):
    context = (ROOT / "CONTEXT.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
    architecture = (ROOT / "memory-bank/architecture.md").read_text(encoding="utf-8")

    assert "R5-P 生产门已闭合" in context
    assert "R5-P 生产闭环完成" in roadmap
    assert "完成 Release/OCI 与生产故障回切、最终部署验收" in architecture
    assert "Issue #54 保持 OPEN" in context
    assert "Issue #54" in roadmap
    assert "R5-P 不能外推关闭它" in context
