import pytest


def _payload(**overrides):
    data = {
        "tenant_id": 1,
        "user_id": 2,
        "grade": "小班",
        "class_name": "阳光班",
        "teacher_name": "张老师",
        "activity_name": "圆形灯笼",
        "child_count": "30",
        "activity_time": "2026.06.28",
        "lesson_plan_original": "原始教案全文",
        "activity_goal": "目标原稿",
        "activity_prep": "准备原稿",
        "activity_process": "过程原稿",
        "goal_adjusted": True,
        "goal_adjustment": "目标调整内容",
        "activity_goal_revised": "目标修改稿",
        "prep_adjusted": False,
        "prep_adjustment": "",
        "activity_prep_revised": "准备修改稿",
        "process_adjustment": "增加动作预备环节",
        "activity_process_revised": "过程修改稿",
        "review_reason": "更符合小班动作发展水平。",
        "revised_lesson_plan": "完整二次修改稿",
        "ai_raw_json": '{"activity_goal":"目标原稿"}',
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_create_course_review_activity_persists_fields(async_session):
    from app.repository.course_review_activity_repository import (
        create_course_review_activity,
    )

    record = await create_course_review_activity(async_session, **_payload())

    assert record.id is not None
    assert record.tenant_id == 1
    assert record.user_id == 2
    assert record.grade == "小班"
    assert record.class_name == "阳光班"
    assert record.teacher_name == "张老师"
    assert record.activity_name == "圆形灯笼"
    assert record.child_count == "30"
    assert record.goal_adjusted is True
    assert record.prep_adjusted is False
    assert "动作预备" in record.process_adjustment
    assert record.ai_raw_json is not None


@pytest.mark.asyncio
async def test_get_course_review_activity_tenant_isolation(async_session):
    from app.repository.course_review_activity_repository import (
        create_course_review_activity,
        get_course_review_activity,
    )

    record = await create_course_review_activity(async_session, **_payload())

    found = await get_course_review_activity(
        async_session,
        tenant_id=1,
        activity_id=record.id,
    )
    assert found is not None
    assert found.activity_name == "圆形灯笼"

    missing = await get_course_review_activity(
        async_session,
        tenant_id=99,
        activity_id=record.id,
    )
    assert missing is None


@pytest.mark.asyncio
async def test_list_course_review_activities_user_isolation_and_order(async_session):
    from app.repository.course_review_activity_repository import (
        create_course_review_activity,
        list_course_review_activities,
    )

    first = await create_course_review_activity(
        async_session,
        **_payload(activity_name="第一次审议"),
    )
    second = await create_course_review_activity(
        async_session,
        **_payload(activity_name="第二次审议"),
    )
    await create_course_review_activity(
        async_session,
        **_payload(user_id=3, activity_name="其他用户"),
    )

    rows = await list_course_review_activities(
        async_session,
        tenant_id=1,
        user_id=2,
    )

    assert [r.id for r in rows] == [second.id, first.id]
    assert [r.activity_name for r in rows] == ["第二次审议", "第一次审议"]


@pytest.mark.asyncio
async def test_delete_course_review_activity_requires_tenant_and_user(async_session):
    from app.repository.course_review_activity_repository import (
        create_course_review_activity,
        delete_course_review_activity,
        get_course_review_activity,
    )

    record = await create_course_review_activity(async_session, **_payload())

    assert await delete_course_review_activity(
        async_session,
        tenant_id=1,
        user_id=99,
        activity_id=record.id,
    ) is False
    assert await get_course_review_activity(
        async_session,
        tenant_id=1,
        activity_id=record.id,
    )

    assert await delete_course_review_activity(
        async_session,
        tenant_id=1,
        user_id=2,
        activity_id=record.id,
    ) is True
    assert await get_course_review_activity(
        async_session,
        tenant_id=1,
        activity_id=record.id,
    ) is None
