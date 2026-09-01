"""Closed R5-P coordinator for post-migration deploy and rollback gates.

The coordinator owns ordering only.  Callers provide the already reviewed,
narrow operations for migration, image changes, acceptance, and state
finalization.  This module does not invoke Alembic, Docker, secret handling,
volume operations, or release APIs itself.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass

Operation = Callable[[], None]


@dataclass(frozen=True)
class PostMigrationResult:
    """Terminal, non-persistent result of one coordinated R5-P attempt."""

    status: str
    failed_gate: str | None = None
    primary_failure: str | None = None
    rollback_failure: str | None = None


def _failure_text(exc: Exception) -> str:
    """Return a non-reversible reason fingerprint without exception contents."""
    digest = hashlib.sha256(str(exc).encode("utf-8", errors="replace")).hexdigest()
    return f"{type(exc).__name__}:sha256:{digest}"


def _run_named_gates(gates: tuple[tuple[str, Operation], ...]) -> None:
    for name, operation in gates:
        try:
            operation()
        except Exception as exc:
            raise _GateFailure(name, _failure_text(exc)) from exc


class _GateFailure(RuntimeError):
    def __init__(self, gate: str, reason: str) -> None:
        super().__init__(reason)
        self.gate = gate
        self.reason = reason


def run_post_migration_rollback(
    *,
    migrate: Operation,
    target_start: Operation,
    target_liveness: Operation,
    target_readiness: Operation,
    target_login: Operation,
    target_business: Operation,
    rollback_start: Operation,
    rollback_liveness: Operation,
    rollback_readiness: Operation,
    rollback_login: Operation,
    rollback_business: Operation,
    finalize_deployment: Operation,
) -> PostMigrationResult:
    """Run the frozen R5-P gates and finalize only a fully accepted target.

    A target failure always attempts the old immutable image.  An old image
    which starts but cannot pass the new-schema acceptance gates requires a
    separate database restore plan.  No failure path calls either finalizer.
    """
    try:
        migrate()
    except Exception as exc:  # noqa: BLE001 - caller operation boundary
        return PostMigrationResult(
            status="MIGRATION_FAILED",
            failed_gate="migration",
            primary_failure=_failure_text(exc),
        )

    target_gates = (
        ("target_start", target_start),
        ("target_liveness", target_liveness),
        ("target_readiness", target_readiness),
        ("target_login", target_login),
        ("target_business", target_business),
    )
    try:
        _run_named_gates(target_gates)
    except _GateFailure as primary:
        try:
            rollback_start()
        except Exception as exc:  # noqa: BLE001 - caller operation boundary
            return PostMigrationResult(
                status="ROLLBACK_FAILED",
                failed_gate="rollback_start",
                primary_failure=primary.reason,
                rollback_failure=_failure_text(exc),
            )

        rollback_gates = (
            ("rollback_liveness", rollback_liveness),
            ("rollback_readiness", rollback_readiness),
            ("rollback_login", rollback_login),
            ("rollback_business", rollback_business),
        )
        try:
            _run_named_gates(rollback_gates)
        except _GateFailure as rollback:
            return PostMigrationResult(
                status="DATABASE_RESTORE_REQUIRED",
                failed_gate=rollback.gate,
                primary_failure=primary.reason,
                rollback_failure=rollback.reason,
            )

        return PostMigrationResult(
            status="ROLLED_BACK",
            failed_gate=primary.gate,
            primary_failure=primary.reason,
        )

    try:
        finalize_deployment()
    except Exception as exc:  # noqa: BLE001 - atomic caller-owned finalizer boundary
        return PostMigrationResult(
            status="FINALIZE_RECONCILE_REQUIRED",
            failed_gate="deployment_finalize",
            primary_failure=_failure_text(exc),
        )
    return PostMigrationResult(status="DEPLOYED")
