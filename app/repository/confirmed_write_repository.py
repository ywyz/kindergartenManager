"""Narrow persistence helpers for one confirmed daily-plan write transaction."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.agent_write_evidence import (
    AgentWriteAudit,
    DailyPlanOperationVersion,
)
from app.core.models.daily_plan import DailyPlan


async def append_daily_plan_operation_version(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    daily_plan_id: int,
    confirmation_id: str,
    patch_id: str,
    patch_sha256: str,
    operation_id: str,
    turn_id: str,
    before_revision: int,
    field_paths_json: str,
    snapshot_json: str,
    snapshot_sha256: str,
    created_at: datetime,
) -> DailyPlanOperationVersion:
    """Append and flush the complete operation-before snapshot."""
    version = DailyPlanOperationVersion(
        tenant_id=tenant_id,
        user_id=user_id,
        daily_plan_id=daily_plan_id,
        confirmation_id=confirmation_id,
        patch_id=patch_id,
        patch_sha256=patch_sha256,
        operation_id=operation_id,
        turn_id=turn_id,
        before_revision=before_revision,
        field_paths_json=field_paths_json,
        snapshot_json=snapshot_json,
        snapshot_sha256=snapshot_sha256,
        created_at=created_at,
    )
    session.add(version)
    await session.flush()
    return version


async def cas_apply_daily_plan_fields(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    daily_plan_id: int,
    expected_revision: int,
    field_values: dict[str, str],
    updated_at: datetime,
) -> bool:
    """Apply registered fields with an exact actor/id/old-revision CAS."""
    values: dict[object, object] = {
        getattr(DailyPlan, field_path): value
        for field_path, value in field_values.items()
    }
    values[DailyPlan._revision] = expected_revision + 1
    values[DailyPlan.updated_at] = updated_at
    result = await session.execute(
        update(DailyPlan)
        .where(
            DailyPlan.id == daily_plan_id,
            DailyPlan.tenant_id == tenant_id,
            DailyPlan.user_id == user_id,
            DailyPlan.revision == expected_revision,
        )
        .values(values)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


async def append_agent_write_audit(
    session: AsyncSession,
    *,
    confirmation_id: str,
    nonce_sha256: str,
    session_sha256: str,
    tenant_id: int,
    user_id: int,
    daily_plan_id: int,
    patch_id: str,
    patch_sha256: str,
    operation_id: str,
    turn_id: str,
    field_paths_json: str,
    before_version_id: int,
    before_revision: int,
    after_revision: int,
    action: str,
    created_at: datetime,
) -> AgentWriteAudit:
    """Append and flush the content-free success audit."""
    audit = AgentWriteAudit(
        confirmation_id=confirmation_id,
        nonce_sha256=nonce_sha256,
        session_sha256=session_sha256,
        tenant_id=tenant_id,
        user_id=user_id,
        daily_plan_id=daily_plan_id,
        patch_id=patch_id,
        patch_sha256=patch_sha256,
        operation_id=operation_id,
        turn_id=turn_id,
        field_paths_json=field_paths_json,
        before_version_id=before_version_id,
        before_revision=before_revision,
        after_revision=after_revision,
        action=action,
        created_at=created_at,
    )
    session.add(audit)
    await session.flush()
    return audit


async def get_agent_write_audit_by_confirmation(
    session: AsyncSession,
    *,
    confirmation_id: str,
) -> AgentWriteAudit | None:
    """Read the unique success audit for reconciliation."""
    result = await session.execute(
        select(AgentWriteAudit).where(
            AgentWriteAudit.confirmation_id == confirmation_id,
        )
    )
    return result.scalar_one_or_none()


async def get_daily_plan_operation_version_by_id(
    session: AsyncSession,
    *,
    version_id: int,
) -> DailyPlanOperationVersion | None:
    """Read one immutable operation-before snapshot by primary key."""
    return await session.get(DailyPlanOperationVersion, version_id)
