"""对外 REST API v1 路由（只读）。

所有业务端点强制经过 API Key 鉴权，并以鉴权得到的 tenant_id 作为查询隔离条件，
调用方无法越权读取其他租户数据。
"""
# ruff: noqa: B008

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.auth import ApiPrincipal, get_api_principal
from app.api.deps import get_db
from app.api.schemas import (
    ClassConfigOut,
    DailyPlanListOut,
    DailyPlanOut,
    HealthOut,
    PageMeta,
    ReadinessChecks,
    ReadinessOut,
    SemesterOut,
)
from app.core.database import AsyncSessionLocal
from app.repository.class_repository import list_class_configs_for_tenant
from app.repository.daily_plan_repository import (
    get_daily_plan_by_id_for_tenant,
    list_daily_plans_for_tenant,
)
from app.repository.semester_repository import list_semesters_for_tenant

router = APIRouter(prefix="/api/v1", tags=["v1"])
READINESS_TIMEOUT_SECONDS = 3.0


@router.get("/health", response_model=HealthOut, summary="健康检查（免鉴权）")
async def health() -> HealthOut:
    return HealthOut(time=datetime.now(UTC))


@router.get(
    "/readiness",
    response_model=ReadinessOut,
    responses={503: {"model": ReadinessOut}},
    summary="数据库就绪检查（免鉴权）",
)
async def readiness() -> JSONResponse:
    """Probe the database without reading or mutating application data."""
    database_status = "ok"
    response_status = "ready"
    status_code = http_status.HTTP_200_OK

    try:
        async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - infrastructure boundary must fail closed
        # Deliberately omit the exception and SQL from both response and logs.
        database_status = "failed"
        response_status = "not_ready"
        status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE

    payload = ReadinessOut(
        status=response_status,
        time=datetime.now(UTC),
        checks=ReadinessChecks(database=database_status),
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


@router.get(
    "/daily-plans",
    response_model=DailyPlanListOut,
    summary="分页查询每日活动计划",
)
async def query_daily_plans(
    principal: ApiPrincipal = Depends(get_api_principal),
    session=Depends(get_db),
    user_id: int | None = Query(None, description="按用户（教师）过滤"),
    start_date: date | None = Query(None, description="计划日期下界（含）"),
    end_date: date | None = Query(None, description="计划日期上界（含）"),
    grade: str | None = Query(None, description="按年级过滤，如 小班/中班/大班"),
    class_name: str | None = Query(None, description="按班级名过滤"),
    limit: int = Query(50, ge=1, le=200, description="每页条数（1~200）"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> DailyPlanListOut:
    records, total = await list_daily_plans_for_tenant(
        session,
        principal.tenant_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        grade=grade,
        class_name=class_name,
        limit=limit,
        offset=offset,
    )
    return DailyPlanListOut(
        meta=PageMeta(total=total, limit=limit, offset=offset),
        items=[DailyPlanOut.from_model(r) for r in records],
    )


@router.get(
    "/daily-plans/{plan_id}",
    response_model=DailyPlanOut,
    summary="按 ID 查询单条每日活动计划",
)
async def get_daily_plan(
    plan_id: int,
    principal: ApiPrincipal = Depends(get_api_principal),
    session=Depends(get_db),
) -> DailyPlanOut:
    plan = await get_daily_plan_by_id_for_tenant(session, principal.tenant_id, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="计划不存在",
        )
    return DailyPlanOut.from_model(plan)


@router.get(
    "/semesters",
    response_model=list[SemesterOut],
    summary="查询学期配置",
)
async def query_semesters(
    principal: ApiPrincipal = Depends(get_api_principal),
    session=Depends(get_db),
    user_id: int | None = Query(None, description="按用户过滤"),
    active_only: bool = Query(False, description="仅返回当前激活学期"),
) -> list[SemesterOut]:
    records = await list_semesters_for_tenant(
        session,
        principal.tenant_id,
        user_id=user_id,
        active_only=active_only,
    )
    return [SemesterOut.from_model(r) for r in records]


@router.get(
    "/classes",
    response_model=list[ClassConfigOut],
    summary="查询班级配置",
)
async def query_classes(
    principal: ApiPrincipal = Depends(get_api_principal),
    session=Depends(get_db),
    user_id: int | None = Query(None, description="按用户过滤"),
) -> list[ClassConfigOut]:
    records = await list_class_configs_for_tenant(
        session,
        principal.tenant_id,
        user_id=user_id,
    )
    return [ClassConfigOut.from_model(r) for r in records]
