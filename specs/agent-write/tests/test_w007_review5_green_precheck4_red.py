"""Stable RED for the fifth W007 repair's single-flight evidence gaps."""

from __future__ import annotations

import inspect
from pathlib import Path

from app.ui.daily_plan_target import UiSingleFlightSlot


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PRECHECK_TEST = (
    REPOSITORY_ROOT / "specs/agent-write/tests/test_w007_review5_green_precheck2_red.py"
)


def test_single_flight_lease_contract_and_evidence_are_current() -> None:
    """The Handle lease needs an explicit contract and non-obsolete coverage."""

    contract = inspect.getdoc(UiSingleFlightSlot.bind) or ""
    evidence = PRECHECK_TEST.read_text(encoding="utf-8")
    checks = {
        "one_wrapper_turn": "one event-loop wrapper turn" in contract,
        "expired_operation_closes": "closes the unstarted operation" in contract,
        "explicit_retry_only": "only a new explicit trigger may retry" in contract,
        "no_obsolete_task_probe": "PRESTART_GUARD_TASK_NAME" not in evidence,
        "lease_expiry_covered": (
            "test_abandoned_operation_expires_without_a_background_task" in evidence
        ),
        "second_stage_failure_covered": (
            "test_second_stage_lease_schedule_failure_is_fail_closed" in evidence
        ),
    }

    assert all(checks.values()), checks
