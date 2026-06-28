"""对外 REST API 响应模型（Pydantic）。

仅暴露教学计划相关的只读字段；不包含密钥、密码等敏感信息。
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.core.models.class_config import ClassConfig
from app.core.models.daily_plan import DailyPlan
from app.core.models.semester import SemesterConfig


class HealthOut(BaseModel):
    status: str = "ok"
    service: str = "kindergarten-teaching-api"
    version: str = "v1"
    time: datetime


class PageMeta(BaseModel):
    total: int = Field(..., description="符合条件的记录总数")
    limit: int = Field(..., description="本页最大返回条数")
    offset: int = Field(..., description="偏移量")


class DailyPlanOut(BaseModel):
    id: int
    tenant_id: int
    user_id: int
    plan_date: date
    week_number: int
    weekday_cn: str
    grade: str
    class_name: str
    activity_goal: str | None = None
    activity_prep: str | None = None
    activity_key: str | None = None
    activity_difficult: str | None = None
    activity_process_original: str | None = None
    activity_process_adapted: str | None = None
    morning_activity: str | None = None
    indoor_area: str | None = None
    outdoor_activity: str | None = None
    morning_talk_topic: str | None = None
    morning_talk_questions: str | None = None
    daily_reflection: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, m: DailyPlan) -> "DailyPlanOut":
        return cls(
            id=m.id,
            tenant_id=m.tenant_id,
            user_id=m.user_id,
            plan_date=m.plan_date,
            week_number=m.week_number,
            weekday_cn=m.weekday_cn,
            grade=m.grade,
            class_name=m.class_name,
            activity_goal=m.activity_goal,
            activity_prep=m.activity_prep,
            activity_key=m.activity_key,
            activity_difficult=m.activity_difficult,
            activity_process_original=m.activity_process_original,
            activity_process_adapted=m.activity_process_adapted,
            morning_activity=m.morning_activity,
            indoor_area=m.indoor_area,
            outdoor_activity=m.outdoor_activity,
            morning_talk_topic=m.morning_talk_topic,
            morning_talk_questions=m.morning_talk_questions,
            daily_reflection=m.daily_reflection,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )


class DailyPlanListOut(BaseModel):
    meta: PageMeta
    items: list[DailyPlanOut]


class SemesterOut(BaseModel):
    id: int
    tenant_id: int
    user_id: int
    semester_name: str
    start_date: date
    end_date: date
    is_active: bool

    @classmethod
    def from_model(cls, m: SemesterConfig) -> "SemesterOut":
        return cls(
            id=m.id,
            tenant_id=m.tenant_id,
            user_id=m.user_id,
            semester_name=m.semester_name,
            start_date=m.start_date,
            end_date=m.end_date,
            is_active=m.is_active,
        )


class ClassConfigOut(BaseModel):
    id: int
    tenant_id: int
    user_id: int
    grade: str
    class_name: str
    teacher_name: str | None = None
    indoor_areas: str | None = None
    outdoor_content: str | None = None

    @classmethod
    def from_model(cls, m: ClassConfig) -> "ClassConfigOut":
        return cls(
            id=m.id,
            tenant_id=m.tenant_id,
            user_id=m.user_id,
            grade=m.grade,
            class_name=m.class_name,
            teacher_name=m.teacher_name,
            indoor_areas=m.indoor_areas,
            outdoor_content=m.outdoor_content,
        )
