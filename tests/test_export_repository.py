"""tests/test_export_repository.py — 导出记录仓库层测试。

使用 SQLite 内存库（async_session fixture）验证写入与租户隔离。
"""

import pytest
from sqlalchemy import select

from app.core.models.export_record import ExportRecord
from app.repository.export_repository import save_export_record


@pytest.mark.asyncio
async def test_save_export_record_persists_fields(async_session):
    """写入一条导出记录后，各字段正确持久化。"""
    record = await save_export_record(
        async_session,
        tenant_id=1,
        user_id=2,
        daily_plan_id=10,
        file_name="1_2_小班_阳光班_20260531_日计划.docx",
        file_path="/abs/path/exports/1_2_小班_阳光班_20260531_日计划.docx",
    )

    assert record.id is not None
    assert record.tenant_id == 1
    assert record.user_id == 2
    assert record.daily_plan_id == 10
    assert record.file_name == "1_2_小班_阳光班_20260531_日计划.docx"
    assert record.file_path.endswith("20260531_日计划.docx")
    assert record.created_at is not None


@pytest.mark.asyncio
async def test_save_export_record_allows_null_daily_plan_id(async_session):
    """daily_plan_id 可为 None。"""
    record = await save_export_record(
        async_session,
        tenant_id=1,
        user_id=2,
        daily_plan_id=None,
        file_name="plan.docx",
        file_path="/abs/path/plan.docx",
    )
    assert record.daily_plan_id is None


@pytest.mark.asyncio
async def test_save_export_record_tenant_isolation(async_session):
    """不同租户写入的记录通过 tenant_id 过滤互不可见。"""
    await save_export_record(
        async_session,
        tenant_id=1,
        user_id=2,
        daily_plan_id=None,
        file_name="t1.docx",
        file_path="/abs/t1.docx",
    )
    await save_export_record(
        async_session,
        tenant_id=99,
        user_id=2,
        daily_plan_id=None,
        file_name="t99.docx",
        file_path="/abs/t99.docx",
    )
    await async_session.flush()

    rows = (
        await async_session.execute(
            select(ExportRecord).where(ExportRecord.tenant_id == 1)
        )
    ).scalars().all()

    assert len(rows) == 1
    assert rows[0].file_name == "t1.docx"


@pytest.mark.asyncio
async def test_save_observation_export_record_with_observation_id(async_session):
    """写入观察导出记录时，observation_id 字段正确持久化。"""
    record = await save_export_record(
        async_session,
        tenant_id=1,
        user_id=2,
        daily_plan_id=None,
        file_name="obs_export.docx",
        file_path="/abs/obs_export.docx",
        observation_id=42,
    )
    assert record.observation_id == 42


@pytest.mark.asyncio
async def test_save_export_record_observation_id_defaults_to_none(async_session):
    """未传 observation_id 时，字段默认为 None（向后兼容）。"""
    record = await save_export_record(
        async_session,
        tenant_id=1,
        user_id=2,
        daily_plan_id=10,
        file_name="plan_export.docx",
        file_path="/abs/plan_export.docx",
    )
    assert record.observation_id is None


@pytest.mark.asyncio
async def test_save_export_record_with_listening_record_id(async_session):
    """写入倾听导出记录时，listening_record_id 字段正确持久化。"""
    record = await save_export_record(
        async_session,
        tenant_id=1,
        user_id=2,
        daily_plan_id=None,
        file_name="listening_export.docx",
        file_path="/abs/listening_export.docx",
        listening_record_id=77,
    )
    assert record.listening_record_id == 77


@pytest.mark.asyncio
async def test_save_export_record_listening_id_defaults_to_none(async_session):
    """未传 listening_record_id 时，字段默认为 None（向后兼容）。"""
    record = await save_export_record(
        async_session,
        tenant_id=1,
        user_id=2,
        daily_plan_id=None,
        file_name="plan.docx",
        file_path="/abs/plan.docx",
    )
    assert record.listening_record_id is None
