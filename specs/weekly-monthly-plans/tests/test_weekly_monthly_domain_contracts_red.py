"""周/月计划领域契约的稳定 RED。

这些测试故意只穿过未来的公开 domain seam。当前正式模块尚未建立时，
测试应完整收集并稳定失败；不得在测试中写临时 DTO、skip 或 xfail。
"""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, timedelta
from importlib import import_module
from inspect import iscoroutinefunction, signature

import pytest


MODULE_NAME = "app.service.weekly_monthly_plans.contracts"


def _contracts():
    return import_module(MODULE_NAME)


def _scope(c):
    return c.PlanScope(
        tenant_id=7,
        teacher_id=11,
        class_id=23,
        grade="中班",
        class_name="彩虹班",
        teacher_names=("甲老师", "乙老师"),
        caregiver_name="丙老师",
    )


def _week(c):
    return c.WeekPeriod(
        week_start=date(2026, 9, 28),
        week_end=date(2026, 10, 4),
        week_number=5,
    )


def _days(c):
    labels = ("周一", "周二", "周三", "周四", "周五")
    return tuple(
        c.WeeklyDay(
            day_date=date(2026, 9, 28) + timedelta(days=offset),
            weekday=offset,
            weekday_cn=label,
            morning_talk=f"晨谈 {offset}",
            collective_activity=f"集体活动 {offset}",
            area_game=f"区域游戏 {offset}",
            outdoor_game=f"户外游戏 {offset}",
        )
        for offset, label in enumerate(labels)
    )


def _monthly_period(c):
    return c.MonthPeriod(
        year=2026,
        month=9,
        month_start=date(2026, 9, 1),
        month_end=date(2026, 9, 30),
    )


def _weekly_plan(
    c,
    *,
    plan_id=101,
    days=None,
    version=1,
    source_daily_plan_ids=(),
):
    if days is None:
        days = _days(c)
    return c.WeeklyActivityPlan(
        plan_id=plan_id,
        scope=_scope(c),
        period=_week(c),
        theme_name="新学期",
        days=days,
        weekly_focus="本周重点",
        environment_creation="环境创设",
        life_habits="生活习惯",
        home_school_cooperation="家园共育",
        version=version,
        status=c.ReviewStatus.DRAFT,
        source_daily_plan_ids=source_daily_plan_ids,
    )


def _monthly_plan(
    c,
    *,
    plan_id=102,
    version=1,
    source_daily_plan_ids=(),
    source_weekly_plan_ids=(),
):
    return c.MonthlyThemeActivityPlan(
        plan_id=plan_id,
        scope=_scope(c),
        period=_monthly_period(c),
        theme_name="我升中班啦",
        previous_month_analysis="上月分析",
        monthly_focus="本月重点",
        theme_goals=("主题目标一",),
        life_habits=("生活习惯一",),
        play_activities=("游戏活动一",),
        environment_creation=("环境创设一",),
        home_school_cooperation=("家园共育一",),
        other=("其它一",),
        activity_contents=("活动内容一",),
        version=version,
        status=c.ReviewStatus.DRAFT,
        source_daily_plan_ids=source_daily_plan_ids,
        source_weekly_plan_ids=source_weekly_plan_ids,
    )


def test_domain_public_contracts_are_closed_and_present():
    c = _contracts()
    expected = {
        "PlanKind",
        "ReviewStatus",
        "PlanAction",
        "PlanScope",
        "WeekPeriod",
        "MonthPeriod",
        "WeeklyDay",
        "WeeklyActivityPlan",
        "MonthlyThemeActivityPlan",
        "PlanAuthorizationRequest",
        "AuthorizationDecision",
        "PlanAuthorizationPort",
    }
    assert expected.issubset(vars(c))


def test_plan_kind_and_review_status_are_exact_closed_sets():
    c = _contracts()
    assert [item.value for item in c.PlanKind] == [
        "weekly_activity_plan",
        "monthly_theme_activity_plan",
    ]
    assert [item.value for item in c.ReviewStatus] == [
        "draft",
        "submitted",
        "returned",
        "approved",
        "archived",
    ]


def test_plan_action_exposes_only_policy_actions():
    c = _contracts()
    assert [item.value for item in c.PlanAction] == [
        "read",
        "create",
        "edit",
        "submit",
        "review",
        "export",
        "delete",
    ]


def test_scope_is_an_immutable_tenant_teacher_class_snapshot():
    c = _contracts()
    scope = _scope(c)
    assert is_dataclass(scope)
    assert {field.name for field in fields(scope)} == {
        "tenant_id",
        "teacher_id",
        "class_id",
        "grade",
        "class_name",
        "teacher_names",
        "caregiver_name",
    }
    with pytest.raises(FrozenInstanceError):
        scope.class_name = "被篡改"


def test_week_period_accepts_a_single_cross_month_natural_week():
    c = _contracts()
    period = _week(c)
    assert period.week_start == date(2026, 9, 28)
    assert period.week_end == date(2026, 10, 4)
    assert period.week_number == 5


def test_month_period_is_a_closed_calendar_month():
    c = _contracts()
    period = _monthly_period(c)
    assert period.month_start == date(2026, 9, 1)
    assert period.month_end == date(2026, 9, 30)


def test_weekly_day_slots_are_exactly_monday_to_friday_and_ordered():
    c = _contracts()
    days = _days(c)
    assert len(days) == 5
    assert tuple(day.weekday for day in days) == (0, 1, 2, 3, 4)
    assert tuple(day.day_date for day in days) == tuple(
        date(2026, 9, 28) + timedelta(days=offset) for offset in range(5)
    )


def test_weekly_aggregate_contains_frozen_scope_period_days_version_and_status():
    c = _contracts()
    plan = c.WeeklyActivityPlan(
        plan_id=101,
        scope=_scope(c),
        period=_week(c),
        theme_name="新学期",
        days=_days(c),
        weekly_focus="本周重点",
        environment_creation="环境创设",
        life_habits="生活习惯",
        home_school_cooperation="家园共育",
        version=2,
        status=c.ReviewStatus.DRAFT,
        source_daily_plan_ids=(301, 302),
    )
    assert plan.plan_id == 101
    assert plan.scope.tenant_id == 7
    assert plan.period.week_start.month != plan.period.week_end.month
    assert plan.version == 2
    assert plan.status is c.ReviewStatus.DRAFT
    assert isinstance(plan.days, tuple)


def test_monthly_aggregate_carries_all_month_template_sections_as_ordered_items():
    c = _contracts()
    plan = c.MonthlyThemeActivityPlan(
        plan_id=102,
        scope=_scope(c),
        period=_monthly_period(c),
        theme_name="我升中班啦",
        previous_month_analysis="上月分析",
        monthly_focus="本月重点",
        theme_goals=("主题目标一", "主题目标二"),
        life_habits=("生活习惯一",),
        play_activities=("游戏活动一",),
        environment_creation=("环境创设一",),
        home_school_cooperation=("家园共育一",),
        other=("其它一",),
        activity_contents=("活动内容一", "活动内容二"),
        version=3,
        status=c.ReviewStatus.SUBMITTED,
        source_daily_plan_ids=(401,),
        source_weekly_plan_ids=(501,),
    )
    assert plan.period.year == 2026
    assert plan.period.month == 9
    assert plan.theme_goals == ("主题目标一", "主题目标二")
    assert plan.activity_contents[-1] == "活动内容二"
    assert isinstance(plan.home_school_cooperation, tuple)


def test_scope_rejects_bool_tenant_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.PlanScope(
            tenant_id=True,
            teacher_id=11,
            class_id=23,
            grade="中班",
            class_name="彩虹班",
            teacher_names=("甲老师",),
            caregiver_name=None,
        )


def test_scope_rejects_bool_teacher_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.PlanScope(
            tenant_id=7,
            teacher_id=True,
            class_id=23,
            grade="中班",
            class_name="彩虹班",
            teacher_names=("甲老师",),
            caregiver_name=None,
        )


def test_scope_rejects_bool_class_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.PlanScope(
            tenant_id=7,
            teacher_id=11,
            class_id=True,
            grade="中班",
            class_name="彩虹班",
            teacher_names=("甲老师",),
            caregiver_name=None,
        )


def test_scope_rejects_nonpositive_tenant_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.PlanScope(
            tenant_id=0,
            teacher_id=11,
            class_id=23,
            grade="中班",
            class_name="彩虹班",
            teacher_names=("甲老师",),
            caregiver_name=None,
        )


def test_scope_rejects_nonpositive_teacher_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.PlanScope(
            tenant_id=7,
            teacher_id=-1,
            class_id=23,
            grade="中班",
            class_name="彩虹班",
            teacher_names=("甲老师",),
            caregiver_name=None,
        )


def test_scope_rejects_nonpositive_class_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.PlanScope(
            tenant_id=7,
            teacher_id=11,
            class_id=0,
            grade="中班",
            class_name="彩虹班",
            teacher_names=("甲老师",),
            caregiver_name=None,
        )


def test_week_period_rejects_non_monday_start():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.WeekPeriod(
            week_start=date(2026, 9, 29),
            week_end=date(2026, 10, 5),
            week_number=5,
        )


def test_week_period_rejects_end_that_is_not_six_days_after_start():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.WeekPeriod(
            week_start=date(2026, 9, 28),
            week_end=date(2026, 10, 5),
            week_number=5,
        )


@pytest.mark.parametrize("week_number", (0, -1))
def test_week_period_rejects_nonpositive_week_number(week_number):
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.WeekPeriod(
            week_start=date(2026, 9, 28),
            week_end=date(2026, 10, 4),
            week_number=week_number,
        )


def test_week_period_rejects_bool_week_number():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.WeekPeriod(
            week_start=date(2026, 9, 28),
            week_end=date(2026, 10, 4),
            week_number=True,
        )


def test_month_period_rejects_nonfirst_month_start():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.MonthPeriod(
            year=2026,
            month=9,
            month_start=date(2026, 9, 2),
            month_end=date(2026, 9, 30),
        )


def test_month_period_rejects_nonlast_month_end():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.MonthPeriod(
            year=2026,
            month=9,
            month_start=date(2026, 9, 1),
            month_end=date(2026, 9, 29),
        )


def test_month_period_rejects_year_month_boundary_mismatch():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.MonthPeriod(
            year=2026,
            month=10,
            month_start=date(2026, 9, 1),
            month_end=date(2026, 9, 30),
        )


def test_month_period_rejects_month_outside_one_to_twelve():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.MonthPeriod(
            year=2026,
            month=13,
            month_start=date(2026, 9, 1),
            month_end=date(2026, 9, 30),
        )


def test_month_period_rejects_non_four_digit_year():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.MonthPeriod(
            year=999,
            month=9,
            month_start=date(999, 9, 1),
            month_end=date(999, 9, 30),
        )


def test_weekly_day_rejects_weekday_outside_monday_to_friday():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.WeeklyDay(
            day_date=date(2026, 9, 28),
            weekday=5,
            weekday_cn="周六",
            morning_talk="",
            collective_activity="",
            area_game="",
            outdoor_game="",
        )


def test_weekly_day_rejects_bool_weekday():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.WeeklyDay(
            day_date=date(2026, 9, 29),
            weekday=True,
            weekday_cn="周二",
            morning_talk="",
            collective_activity="",
            area_game="",
            outdoor_game="",
        )


def test_weekly_day_rejects_weekday_date_mismatch():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.WeeklyDay(
            day_date=date(2026, 9, 29),
            weekday=0,
            weekday_cn="周一",
            morning_talk="",
            collective_activity="",
            area_game="",
            outdoor_game="",
        )


def test_weekly_day_rejects_inconsistent_chinese_weekday_label():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.WeeklyDay(
            day_date=date(2026, 9, 28),
            weekday=0,
            weekday_cn="周二",
            morning_talk="",
            collective_activity="",
            area_game="",
            outdoor_game="",
        )


def test_weekly_plan_rejects_bool_plan_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _weekly_plan(c, plan_id=True)


def test_weekly_plan_rejects_nonpositive_plan_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _weekly_plan(c, plan_id=0)


def test_weekly_plan_rejects_fewer_than_five_days():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _weekly_plan(c, days=_days(c)[:4])


def test_weekly_plan_rejects_more_than_five_days():
    c = _contracts()
    days = _days(c)
    with pytest.raises((TypeError, ValueError)):
        _weekly_plan(c, days=days + (days[-1],))


def test_weekly_plan_rejects_days_out_of_order():
    c = _contracts()
    days = list(_days(c))
    days[0], days[1] = days[1], days[0]
    with pytest.raises((TypeError, ValueError)):
        _weekly_plan(c, days=tuple(days))


def test_weekly_plan_rejects_a_day_outside_the_week_range():
    c = _contracts()
    days = _days(c)[:-1] + (
        c.WeeklyDay(
            day_date=date(2026, 10, 9),
            weekday=4,
            weekday_cn="周五",
            morning_talk="",
            collective_activity="",
            area_game="",
            outdoor_game="",
        ),
    )
    with pytest.raises((TypeError, ValueError)):
        _weekly_plan(c, days=days)


@pytest.mark.parametrize("version", (0, -1))
def test_weekly_plan_rejects_nonpositive_version(version):
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _weekly_plan(c, version=version)


def test_weekly_plan_rejects_bool_version():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _weekly_plan(c, version=True)


def test_weekly_plan_rejects_duplicate_source_daily_plan_ids():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _weekly_plan(c, source_daily_plan_ids=(301, 301))


def test_weekly_plan_rejects_nonpositive_source_daily_plan_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _weekly_plan(c, source_daily_plan_ids=(0,))


def test_weekly_plan_rejects_bool_source_daily_plan_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _weekly_plan(c, source_daily_plan_ids=(True,))


def test_weekly_plan_rejects_noninteger_source_daily_plan_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _weekly_plan(c, source_daily_plan_ids=("301",))


def test_monthly_plan_rejects_duplicate_source_daily_plan_ids():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _monthly_plan(c, source_daily_plan_ids=(401, 401))


def test_monthly_plan_rejects_duplicate_source_weekly_plan_ids():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _monthly_plan(c, source_weekly_plan_ids=(501, 501))


def test_monthly_plan_rejects_nonpositive_source_daily_plan_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _monthly_plan(c, source_daily_plan_ids=(0,))


def test_monthly_plan_rejects_nonpositive_source_weekly_plan_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _monthly_plan(c, source_weekly_plan_ids=(-1,))


def test_monthly_plan_rejects_bool_source_daily_plan_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _monthly_plan(c, source_daily_plan_ids=(False,))


def test_monthly_plan_rejects_bool_source_weekly_plan_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _monthly_plan(c, source_weekly_plan_ids=(True,))


def test_monthly_plan_rejects_bool_plan_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _monthly_plan(c, plan_id=True)


def test_monthly_plan_rejects_nonpositive_plan_id():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _monthly_plan(c, plan_id=-1)


def test_monthly_plan_rejects_nonpositive_version():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _monthly_plan(c, version=0)


def test_monthly_plan_rejects_bool_version():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _monthly_plan(c, version=True)


def test_scope_rejects_empty_grade_snapshot():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.PlanScope(
            tenant_id=7,
            teacher_id=11,
            class_id=23,
            grade="",
            class_name="彩虹班",
            teacher_names=("甲老师",),
            caregiver_name=None,
        )


def test_scope_rejects_empty_class_name_snapshot():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.PlanScope(
            tenant_id=7,
            teacher_id=11,
            class_id=23,
            grade="中班",
            class_name="",
            teacher_names=("甲老师",),
            caregiver_name=None,
        )


def test_scope_rejects_empty_teacher_snapshot():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.PlanScope(
            tenant_id=7,
            teacher_id=11,
            class_id=23,
            grade="中班",
            class_name="彩虹班",
            teacher_names=(),
            caregiver_name=None,
        )


def test_weekly_plan_rejects_a_non_domain_period_object():
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        c.WeeklyActivityPlan(
            plan_id=101,
            scope=_scope(c),
            period="2026-W40",
            theme_name="新学期",
            days=_days(c),
            weekly_focus="",
            environment_creation="",
            life_habits="",
            home_school_cooperation="",
            version=1,
            status=c.ReviewStatus.DRAFT,
            source_daily_plan_ids=(),
        )


def test_aggregate_children_are_not_mutable_lists_or_shared_orm_objects():
    c = _contracts()
    plan_fields = {field.name for field in fields(c.WeeklyActivityPlan)}
    assert "days" in plan_fields
    assert "source_daily_plan_ids" in plan_fields
    assert not any(name in plan_fields for name in ("session", "repository", "model"))
    plan = c.WeeklyActivityPlan(
        plan_id=101,
        scope=_scope(c),
        period=_week(c),
        theme_name="新学期",
        days=_days(c),
        weekly_focus="",
        environment_creation="",
        life_habits="",
        home_school_cooperation="",
        version=1,
        status=c.ReviewStatus.DRAFT,
        source_daily_plan_ids=(),
    )
    with pytest.raises(FrozenInstanceError):
        plan.theme_name = "其它主题"


def test_authorization_port_is_async_and_has_one_authorize_entrypoint():
    c = _contracts()
    method = c.PlanAuthorizationPort.authorize
    assert iscoroutinefunction(method)
    assert list(signature(method).parameters) == ["self", "request"]
    assert hasattr(c, "PlanAuthorizationRequest")
    assert hasattr(c, "AuthorizationDecision")


def test_authorization_request_contains_actor_tenant_teacher_class_target_and_status():
    c = _contracts()
    names = {field.name for field in fields(c.PlanAuthorizationRequest)}
    assert names == {
        "action",
        "actor_id",
        "actor_role",
        "tenant_id",
        "owner_teacher_id",
        "class_id",
        "plan_kind",
        "plan_id",
        "plan_version",
        "status",
    }


def _authorization_request(c, **overrides):
    values = {
        "action": c.PlanAction.READ,
        "actor_id": 31,
        "actor_role": "teacher",
        "tenant_id": 7,
        "owner_teacher_id": 11,
        "class_id": 23,
        "plan_kind": c.PlanKind.WEEKLY_ACTIVITY,
        "plan_id": 101,
        "plan_version": 2,
        "status": c.ReviewStatus.DRAFT,
    }
    values.update(overrides)
    return c.PlanAuthorizationRequest(**values)


def test_week_period_rejects_an_unrepresentable_natural_week_as_a_value_error():
    c = _contracts()
    with pytest.raises(ValueError):
        c.WeekPeriod(
            week_start=date(9999, 12, 27),
            week_end=date(9999, 12, 31),
            week_number=1,
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "actor_id",
        "tenant_id",
        "owner_teacher_id",
        "class_id",
        "plan_id",
        "plan_version",
    ),
)
@pytest.mark.parametrize("invalid", (True, 0, "1"))
def test_authorization_request_rejects_invalid_ids_and_version(field_name, invalid):
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _authorization_request(c, **{field_name: invalid})


@pytest.mark.parametrize(
    ("field_name", "invalid"),
    (
        ("action", "read"),
        ("plan_kind", "weekly_activity_plan"),
        ("status", "draft"),
    ),
)
def test_authorization_request_rejects_raw_string_enums(field_name, invalid):
    c = _contracts()
    with pytest.raises((TypeError, ValueError)):
        _authorization_request(c, **{field_name: invalid})


def test_authorization_contracts_are_immutable_and_decision_bool_is_strict():
    c = _contracts()
    request = _authorization_request(c)
    decision = c.AuthorizationDecision(allowed=False, reason_code="policy_denied")
    with pytest.raises(FrozenInstanceError):
        request.plan_version = 3
    with pytest.raises(FrozenInstanceError):
        decision.allowed = True
    with pytest.raises((TypeError, ValueError)):
        c.AuthorizationDecision(allowed=1, reason_code="policy_denied")
