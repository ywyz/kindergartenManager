"""Stable RED for the R5-P post-migration rollback coordinator."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

Gate = Callable[[], None]


def _api() -> Any:
    from scripts import r5_post_migration_rollback

    return r5_post_migration_rollback


def _fail(message: str) -> Gate:
    def raise_failure() -> None:
        raise RuntimeError(message)

    return raise_failure


def _run(
    *,
    target_start: Gate = lambda: None,
    target_liveness: Gate = lambda: None,
    target_readiness: Gate = lambda: None,
    target_login: Gate = lambda: None,
    target_business: Gate = lambda: None,
    rollback_start: Gate = lambda: None,
    rollback_liveness: Gate = lambda: None,
    rollback_readiness: Gate = lambda: None,
    rollback_login: Gate = lambda: None,
    rollback_business: Gate = lambda: None,
) -> tuple[Any, list[str], list[str]]:
    api = _api()
    deployment_updates: list[str] = []
    release_updates: list[str] = []
    result = api.run_post_migration_rollback(
        migrate=lambda: None,
        target_start=target_start,
        target_liveness=target_liveness,
        target_readiness=target_readiness,
        target_login=target_login,
        target_business=target_business,
        rollback_start=rollback_start,
        rollback_liveness=rollback_liveness,
        rollback_readiness=rollback_readiness,
        rollback_login=rollback_login,
        rollback_business=rollback_business,
        finalize_deployment=lambda: deployment_updates.append("finalized"),
    )
    return result, deployment_updates, release_updates


def test_target_start_failure_rolls_back_old_image_without_finalizing() -> None:
    result, deployment, release = _run(target_start=_fail("target start failed"))

    assert result.status == "ROLLED_BACK"
    assert result.failed_gate == "target_start"
    assert deployment == []
    assert release == []


def test_target_liveness_success_but_readiness_failure_rolls_back() -> None:
    result, deployment, release = _run(
        target_readiness=_fail("target readiness failed")
    )

    assert result.status == "ROLLED_BACK"
    assert result.failed_gate == "target_readiness"
    assert deployment == []
    assert release == []


@pytest.mark.parametrize(
    ("gate", "expected"),
    [
        ("login", "target_login"),
        ("business", "target_business"),
    ],
)
def test_post_readiness_acceptance_failure_rolls_back(gate: str, expected: str) -> None:
    kwargs = {f"target_{gate}": _fail(f"target {gate} failed")}
    result, deployment, release = _run(**kwargs)

    assert result.status == "ROLLED_BACK"
    assert result.failed_gate == expected
    assert deployment == []
    assert release == []


def test_all_target_gates_finalize_deployment_before_release() -> None:
    api = _api()
    events: list[str] = []

    result = api.run_post_migration_rollback(
        migrate=lambda: events.append("migration"),
        target_start=lambda: events.append("target_start"),
        target_liveness=lambda: events.append("target_liveness"),
        target_readiness=lambda: events.append("target_readiness"),
        target_login=lambda: events.append("target_login"),
        target_business=lambda: events.append("target_business"),
        rollback_start=lambda: events.append("unexpected_rollback"),
        rollback_liveness=lambda: events.append("unexpected_rollback_liveness"),
        rollback_readiness=lambda: events.append("unexpected_rollback_readiness"),
        rollback_login=lambda: events.append("unexpected_rollback_login"),
        rollback_business=lambda: events.append("unexpected_rollback_business"),
        finalize_deployment=lambda: events.append("deployment_finalize"),
    )

    assert result.status == "DEPLOYED"
    assert events == [
        "migration",
        "target_start",
        "target_liveness",
        "target_readiness",
        "target_login",
        "target_business",
        "deployment_finalize",
    ]


def test_old_image_incompatible_with_new_schema_requires_database_restore() -> None:
    result, deployment, release = _run(
        target_start=_fail("target start failed"),
        rollback_readiness=_fail("old image schema mismatch"),
    )

    assert result.status == "DATABASE_RESTORE_REQUIRED"
    assert result.failed_gate == "rollback_readiness"
    assert result.primary_failure.startswith("RuntimeError:sha256:")
    assert result.rollback_failure.startswith("RuntimeError:sha256:")
    assert result.primary_failure != result.rollback_failure
    assert deployment == []
    assert release == []


def test_primary_and_rollback_start_failures_are_both_reported() -> None:
    result, deployment, release = _run(
        target_start=_fail("target failed"),
        rollback_start=_fail("rollback failed"),
    )

    assert result.status == "ROLLBACK_FAILED"
    assert result.primary_failure.startswith("RuntimeError:sha256:")
    assert result.rollback_failure.startswith("RuntimeError:sha256:")
    assert result.primary_failure != result.rollback_failure
    assert deployment == []
    assert release == []


def test_migration_failure_does_not_start_images_or_update_states() -> None:
    api = _api()
    events: list[str] = []

    result = api.run_post_migration_rollback(
        migrate=_fail("migration failed"),
        target_start=lambda: events.append("target"),
        target_liveness=lambda: events.append("target_liveness"),
        target_readiness=lambda: events.append("target_readiness"),
        target_login=lambda: events.append("target_login"),
        target_business=lambda: events.append("target_business"),
        rollback_start=lambda: events.append("rollback"),
        rollback_liveness=lambda: events.append("rollback_liveness"),
        rollback_readiness=lambda: events.append("rollback_readiness"),
        rollback_login=lambda: events.append("rollback_login"),
        rollback_business=lambda: events.append("rollback_business"),
        finalize_deployment=lambda: events.append("deployment_finalize"),
    )

    assert result.status == "MIGRATION_FAILED"
    assert result.failed_gate == "migration"
    assert events == []


def test_finalize_failure_is_controlled_and_release_is_separate() -> None:
    api = _api()

    result = api.run_post_migration_rollback(
        migrate=lambda: None,
        target_start=lambda: None,
        target_liveness=lambda: None,
        target_readiness=lambda: None,
        target_login=lambda: None,
        target_business=lambda: None,
        rollback_start=lambda: None,
        rollback_liveness=lambda: None,
        rollback_readiness=lambda: None,
        rollback_login=lambda: None,
        rollback_business=lambda: None,
        finalize_deployment=_fail("atomic state finalizer failed"),
    )

    assert result.status == "FINALIZE_RECONCILE_REQUIRED"
    assert result.failed_gate == "deployment_finalize"
