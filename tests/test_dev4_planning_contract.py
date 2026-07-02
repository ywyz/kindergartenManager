from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_PLAN = ROOT / "memory-bank" / "dev4.0-plan.md"
P0_DEV_PLAN = ROOT / "memory-bank" / "dev4.0" / "p0-dev-plan.md"
P0_TEST_PLAN = ROOT / "memory-bank" / "dev4.0" / "p0-test-plan.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_dev4_plans_exist() -> None:
    assert MAIN_PLAN.exists()
    assert P0_DEV_PLAN.exists()
    assert P0_TEST_PLAN.exists()


def test_main_plan_records_required_dev4_capabilities() -> None:
    text = _read(MAIN_PLAN)

    required_phrases = [
        "提示词优化系统",
        "功能权限矩阵",
        "S3",
        "WebDAV",
        "备份与恢复",
        "清理与归档策略",
        "grade_lead",
        "academic_director",
        "principal",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_p0_docs_require_docs_and_tests_before_implementation() -> None:
    dev_plan = _read(P0_DEV_PLAN)
    test_plan = _read(P0_TEST_PLAN)

    assert "每个 P 阶段开始前必须先有 `dev-plan.md`、`test-plan.md` 和对应自动测试" in dev_plan
    assert "Gate Tests" in test_plan
    assert "tests/test_dev4_planning_contract.py" in test_plan


def test_cleanup_policy_keeps_legacy_until_migration_is_verified() -> None:
    main_plan = _read(MAIN_PLAN)
    p0_plan = _read(P0_DEV_PLAN)

    assert "旧系统不能在计划阶段直接清空" in main_plan
    assert "不删除 dev3.4 业务代码、迁移、模板和测试" in p0_plan
    assert "直到对应 dev4.0 workflow 完成迁移和回归" in p0_plan
