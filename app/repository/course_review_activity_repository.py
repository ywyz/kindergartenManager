"""课程审议记录仓库层。"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.course_review_activity import CourseReviewActivity


async def create_course_review_activity(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    grade: str,
    class_name: str,
    teacher_name: str,
    activity_name: str,
    child_count: str,
    activity_time: str,
    lesson_plan_original: str,
    activity_goal: str,
    activity_prep: str,
    activity_process: str,
    goal_adjusted: bool,
    goal_adjustment: str,
    activity_goal_revised: str,
    prep_adjusted: bool,
    prep_adjustment: str,
    activity_prep_revised: str,
    process_adjustment: str,
    activity_process_revised: str,
    review_reason: str,
    revised_lesson_plan: str,
    ai_raw_json: str | None = None,
) -> CourseReviewActivity:
    """创建一条课程审议记录。"""
    record = CourseReviewActivity(
        tenant_id=tenant_id,
        user_id=user_id,
        grade=grade,
        class_name=class_name,
        teacher_name=teacher_name,
        activity_name=activity_name,
        child_count=child_count,
        activity_time=activity_time,
        lesson_plan_original=lesson_plan_original,
        activity_goal=activity_goal,
        activity_prep=activity_prep,
        activity_process=activity_process,
        goal_adjusted=goal_adjusted,
        goal_adjustment=goal_adjustment,
        activity_goal_revised=activity_goal_revised,
        prep_adjusted=prep_adjusted,
        prep_adjustment=prep_adjustment,
        activity_prep_revised=activity_prep_revised,
        process_adjustment=process_adjustment,
        activity_process_revised=activity_process_revised,
        review_reason=review_reason,
        revised_lesson_plan=revised_lesson_plan,
        ai_raw_json=ai_raw_json,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def get_course_review_activity(
    session: AsyncSession,
    *,
    tenant_id: int,
    activity_id: int,
) -> CourseReviewActivity | None:
    """按 id 查询课程审议记录，强制 tenant_id 过滤。"""
    result = await session.execute(
        select(CourseReviewActivity).where(
            CourseReviewActivity.tenant_id == tenant_id,
            CourseReviewActivity.id == activity_id,
        )
    )
    return result.scalar_one_or_none()


async def list_course_review_activities(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    offset: int = 0,
    limit: int = 20,
) -> list[CourseReviewActivity]:
    """按当前用户分页列出课程审议记录，最新在前。"""
    result = await session.execute(
        select(CourseReviewActivity)
        .where(
            CourseReviewActivity.tenant_id == tenant_id,
            CourseReviewActivity.user_id == user_id,
        )
        .order_by(CourseReviewActivity.created_at.desc(), CourseReviewActivity.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def delete_course_review_activity(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    activity_id: int,
) -> bool:
    """删除课程审议记录，强制 tenant_id + user_id 双重过滤。"""
    result = await session.execute(
        delete(CourseReviewActivity).where(
            CourseReviewActivity.tenant_id == tenant_id,
            CourseReviewActivity.user_id == user_id,
            CourseReviewActivity.id == activity_id,
        )
    )
    await session.commit()
    return bool(result.rowcount)
