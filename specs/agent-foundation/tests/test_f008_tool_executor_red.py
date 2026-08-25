"""F008 public RED tests for the six closed Foundation Tool executors."""

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from importlib import import_module
import inspect
import logging
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.core.models  # noqa: F401 - register every ORM model with Base.metadata
from app.core.database import Base
from app.core.models.class_config import ClassConfig
from app.core.models.daily_plan import DailyPlan
from app.core.models.export_record import ExportRecord
from app.core.models.semester import SemesterConfig
from app.service.agent.contracts import (
    DAILY_PLAN_SECTION_PATHS,
    FOUNDATION_ALLOWED_PERMISSIONS,
    AgentContext,
    CalendarDayType,
    CalendarEvaluationProjection,
    ClassAreasProjection,
    DailyPlanContextProjection,
    DailyPlanProjection,
    DailyPlanScope,
    Permission,
    PlanSection,
    TrustedActor,
)
from app.service.agent.patch import (
    PlanPatch,
    build_plan_patch_from_arguments,
    plan_patch_matches_expected,
)
from app.service.agent.registry import build_foundation_registry
from app.service.agent.runtime import (
    ProviderToolCall,
    ToolExecutionResult,
    ToolExecutionStatus,
)


PLAN_DATE = date(2026, 9, 7)
OPERATION_ID = UUID("11111111-1111-4111-8111-111111111111")
TURN_ID = UUID("22222222-2222-4222-8222-222222222222")
CONTEXT_ID = UUID("33333333-3333-4333-8333-333333333333")
BASE_FINGERPRINT = "a" * 64


def _tools_module():
    return import_module("app.service.agent.tools")


class _TrackedSessionContext:
    def __init__(self, owner: "_TrackedSessionFactory") -> None:
        self._owner = owner
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> AsyncSession:
        self._session = self._owner.raw_factory()
        session = await self._session.__aenter__()
        self._owner.opened += 1
        self._owner.active += 1
        return session

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self._session is None:
            raise AssertionError("tracked_session_was_not_opened")
        try:
            await self._session.__aexit__(exc_type, exc_value, traceback)
        finally:
            self._owner.closed += 1
            self._owner.active -= 1


class _TrackedSessionFactory:
    """Observable database boundary used to prove one short session per READ."""

    def __init__(self, raw_factory: async_sessionmaker[AsyncSession]) -> None:
        self.raw_factory = raw_factory
        self.opened = 0
        self.closed = 0
        self.active = 0

    def __call__(self) -> _TrackedSessionContext:
        return _TrackedSessionContext(self)


class _ForbiddenSessionFactory:
    """Fail if a rejected or DRAFT call tries to open a database session."""

    def __init__(self) -> None:
        self.opened = 0
        self.closed = 0
        self.active = 0

    def __call__(self):
        self.opened += 1
        raise AssertionError("session_must_not_open")


@dataclass(slots=True)
class _ToolDatabase:
    engine: AsyncEngine
    raw_factory: async_sessionmaker[AsyncSession]
    sessions: _TrackedSessionFactory
    plan_id: int


@pytest_asyncio.fixture
async def tool_database() -> AsyncIterator[_ToolDatabase]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    raw_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with raw_factory() as session:
        plan = DailyPlan(
            tenant_id=1,
            user_id=10,
            plan_date=PLAN_DATE,
            week_number=2,
            weekday_cn="周一",
            grade="大班",
            class_name="星星班",
            activity_goal="认识秋天",
            activity_prep="",
            daily_reflection="孩子们主动观察了落叶",
            updated_at=datetime(2026, 9, 6, 8, 30, tzinfo=timezone.utc),
        )
        session.add_all(
            [
                plan,
                DailyPlan(
                    tenant_id=1,
                    user_id=11,
                    plan_date=PLAN_DATE,
                    week_number=2,
                    weekday_cn="周一",
                    grade="中班",
                    class_name="月亮班",
                    activity_goal="另一用户的秘密目标",
                ),
                ClassConfig(
                    tenant_id=1,
                    user_id=10,
                    grade="大班",
                    class_name="星星班",
                    teacher_name="不应进入 ToolResult 的张老师",
                    indoor_areas="建构区、阅读区",
                    outdoor_content="沙水区和攀爬区",
                ),
                SemesterConfig(
                    tenant_id=1,
                    user_id=10,
                    semester_name="2026 秋季学期",
                    start_date=date(2026, 9, 1),
                    end_date=date(2027, 1, 31),
                    is_active=True,
                ),
            ]
        )
        await session.flush()
        session.add(
            ExportRecord(
                tenant_id=1,
                user_id=10,
                daily_plan_id=plan.id,
                file_name="existing.docx",
                file_path="/already/existing.docx",
            )
        )
        await session.commit()
        plan_id = plan.id

    database = _ToolDatabase(
        engine=engine,
        raw_factory=raw_factory,
        sessions=_TrackedSessionFactory(raw_factory),
        plan_id=plan_id,
    )
    try:
        yield database
    finally:
        await engine.dispose()


async def _known_workday(_target_date: date):
    read_service = import_module("app.service.agent.read_service")
    return read_service.HolidayLookupResult(False, False, None)


class _RecordingHolidayLookup:
    def __init__(self) -> None:
        self.calls: list[date] = []

    async def __call__(self, target_date: date):
        self.calls.append(target_date)
        return await _known_workday(target_date)


def _executor(session_factory, *, holiday_lookup=None):
    tools = _tools_module()
    return tools.FoundationToolExecutor(
        session_factory=session_factory,
        registry=build_foundation_registry(),
        holiday_lookup=(_known_workday if holiday_lookup is None else holiday_lookup),
    )


def _projection(plan_id: int) -> DailyPlanProjection:
    contents = {
        "activity_goal": "认识秋天",
        "daily_reflection": "孩子们主动观察了落叶",
    }
    return DailyPlanProjection(
        plan_id=plan_id,
        plan_date=PLAN_DATE,
        week_number=2,
        weekday_cn="周一",
        grade="大班",
        class_name="星星班",
        sections=tuple(
            PlanSection(
                field_path=field_path,
                content=contents.get(field_path, ""),
                truncated=False,
            )
            for field_path in DAILY_PLAN_SECTION_PATHS
        ),
        updated_at_utc=datetime(2026, 9, 6, 8, 30, tzinfo=timezone.utc),
        content_sha256="b" * 64,
    )


def _context(
    plan_id: int,
    *,
    actor: TrustedActor = TrustedActor(tenant_id=1, user_id=10),
    scope: DailyPlanScope | None = None,
) -> AgentContext:
    created_at = datetime(2026, 9, 7, 1, 2, 3, tzinfo=timezone.utc)
    return AgentContext(
        context_id=CONTEXT_ID,
        operation_id=OPERATION_ID,
        turn_id=TURN_ID,
        created_at_utc=created_at,
        expires_at_utc=created_at + timedelta(minutes=5),
        locale="zh-CN",
        actor=actor,
        active_scope=scope or DailyPlanScope(daily_plan_id=plan_id),
        facts=(_projection(plan_id),),
        base_fingerprint=BASE_FINGERPRINT,
        allowed_permissions=FOUNDATION_ALLOWED_PERMISSIONS,
    )


def _call(
    context: AgentContext,
    *,
    tool_name: str,
    permission: Permission,
    arguments: Mapping[str, object] | None = None,
    operation_id: UUID | None = None,
    turn_id: UUID | None = None,
    call_number: int = 1,
) -> ProviderToolCall:
    return ProviderToolCall(
        call_id=UUID(int=call_number),
        operation_id=operation_id or context.operation_id,
        turn_id=turn_id or context.turn_id,
        tool_name=tool_name,
        permission=permission,
        arguments={} if arguments is None else arguments,
    )


def _draft_arguments(
    context: AgentContext,
    *,
    tool_name: str,
) -> dict[str, object]:
    if tool_name == "daily_plan.draft_reflection_patch":
        field_path = "daily_reflection"
        before_value = "孩子们主动观察了落叶"
        after_value = "幼儿能主动比较不同落叶的形状。"
    else:
        field_path = "activity_goal"
        before_value = "认识秋天"
        after_value = "探索秋天"
    return {
        "operation_id": str(context.operation_id),
        "turn_id": str(context.turn_id),
        "target": {
            "daily_plan_id": context.facts[0].plan_id,
            "plan_date": PLAN_DATE.isoformat(),
        },
        "base_fingerprint": context.base_fingerprint,
        "operations": [
            {
                "field_path": field_path,
                "before_value": before_value,
                "after_value": after_value,
            }
        ],
        "warnings": ["请教师复核"],
    }


def _assert_envelope(
    result: ToolExecutionResult,
    call: ProviderToolCall,
    *,
    status: ToolExecutionStatus,
    error_code: str | None,
) -> None:
    assert type(result) is ToolExecutionResult
    assert result.call_id == call.call_id
    assert result.operation_id == call.operation_id
    assert result.turn_id == call.turn_id
    assert result.tool_name == call.tool_name
    assert result.permission is call.permission
    assert result.status is status
    assert result.error_code == error_code


def test_executor_public_surface_is_one_closed_execute_entrypoint():
    executor = _executor(_ForbiddenSessionFactory())
    public_methods = {
        name
        for name, member in inspect.getmembers(type(executor), inspect.isfunction)
        if not name.startswith("_")
    }

    assert public_methods == {"execute"}
    assert not hasattr(executor, "register")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "tool_name",
        "permission",
        "arguments",
        "operation_id",
        "turn_id",
        "expected_code",
    ),
    (
        (
            "daily_plan.unknown",
            Permission.READ,
            {},
            None,
            None,
            "agent.tool_not_allowed",
        ),
        (
            "daily_plan.read_current",
            Permission.WRITE,
            {},
            None,
            None,
            "agent.tool_not_allowed",
        ),
        (
            "daily_plan.read_current",
            Permission.DRAFT,
            {},
            None,
            None,
            "agent.tool_not_allowed",
        ),
        (
            "daily_plan.read_current",
            Permission.READ,
            {},
            UUID("44444444-4444-4444-8444-444444444444"),
            None,
            "agent.tool_schema_invalid",
        ),
        (
            "daily_plan.read_current",
            Permission.READ,
            {},
            None,
            UUID("55555555-5555-4555-8555-555555555555"),
            "agent.tool_schema_invalid",
        ),
        (
            "daily_plan.read_current",
            Permission.READ,
            {"tenant_id": 2, "user_id": 99},
            None,
            None,
            "agent.tool_schema_invalid",
        ),
    ),
)
async def test_rejected_calls_fail_before_opening_a_session(
    tool_name: str,
    permission: Permission,
    arguments: Mapping[str, object],
    operation_id: UUID | None,
    turn_id: UUID | None,
    expected_code: str,
):
    sessions = _ForbiddenSessionFactory()
    executor = _executor(sessions)
    context = _context(7)
    call = _call(
        context,
        tool_name=tool_name,
        permission=permission,
        arguments=arguments,
        operation_id=operation_id,
        turn_id=turn_id,
    )

    result = await executor.execute(call, context)

    _assert_envelope(
        result,
        call,
        status=ToolExecutionStatus.REJECTED,
        error_code=expected_code,
    )
    assert result.value is None
    assert sessions.opened == sessions.closed == sessions.active == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "expected_type"),
    (
        ("daily_plan.read_current", DailyPlanProjection),
        ("daily_plan.read_context", DailyPlanContextProjection),
        ("calendar.read_evaluation", CalendarEvaluationProjection),
        ("settings.read_class_areas", ClassAreasProjection),
    ),
)
async def test_each_read_tool_returns_one_closed_projection_from_one_short_session(
    tool_database: _ToolDatabase,
    tool_name: str,
    expected_type: type,
):
    executor = _executor(tool_database.sessions)
    context = _context(tool_database.plan_id)
    call = _call(context, tool_name=tool_name, permission=Permission.READ)

    result = await executor.execute(call, context)

    _assert_envelope(
        result,
        call,
        status=ToolExecutionStatus.OK,
        error_code=None,
    )
    assert type(result.value) is expected_type
    assert not hasattr(result.value, "_sa_instance_state")
    assert "张老师" not in repr(result)
    assert "认识秋天" not in repr(result)
    assert tool_database.sessions.opened == 1
    assert tool_database.sessions.closed == 1
    assert tool_database.sessions.active == 0
    if type(result.value) is DailyPlanProjection:
        assert result.value.plan_id == tool_database.plan_id
        assert result.value.sections[0].content == "认识秋天"
    elif type(result.value) is DailyPlanContextProjection:
        assert result.value.semester_name == "2026 秋季学期"
    elif type(result.value) is CalendarEvaluationProjection:
        assert result.value.target_date == PLAN_DATE
        assert result.value.day_type is CalendarDayType.WORKDAY
    else:
        assert result.value.indoor_areas == "建构区、阅读区"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "actor",
    (
        TrustedActor(tenant_id=1, user_id=11),
        TrustedActor(tenant_id=2, user_id=10),
    ),
)
async def test_read_tools_cannot_cross_the_context_actor_boundary(
    tool_database: _ToolDatabase,
    actor: TrustedActor,
):
    executor = _executor(tool_database.sessions)
    context = _context(tool_database.plan_id, actor=actor)
    call = _call(
        context,
        tool_name="daily_plan.read_current",
        permission=Permission.READ,
    )

    result = await executor.execute(call, context)

    _assert_envelope(
        result,
        call,
        status=ToolExecutionStatus.FAILED,
        error_code="agent.tool_failed",
    )
    assert result.value is None
    assert tool_database.sessions.opened == tool_database.sessions.closed == 1
    assert tool_database.sessions.active == 0


@pytest.mark.asyncio
async def test_calendar_plan_id_is_resolved_with_an_actor_scoped_read_first(
    tool_database: _ToolDatabase,
):
    lookup = _RecordingHolidayLookup()
    executor = _executor(tool_database.sessions, holiday_lookup=lookup)
    own_context = _context(tool_database.plan_id)
    own_call = _call(
        own_context,
        tool_name="calendar.read_evaluation",
        permission=Permission.READ,
        call_number=11,
    )

    own_result = await executor.execute(own_call, own_context)

    assert own_result.status is ToolExecutionStatus.OK
    assert own_result.value.target_date == PLAN_DATE
    assert lookup.calls == [PLAN_DATE]

    other_context = _context(
        tool_database.plan_id,
        actor=TrustedActor(tenant_id=1, user_id=11),
    )
    other_call = _call(
        other_context,
        tool_name="calendar.read_evaluation",
        permission=Permission.READ,
        call_number=12,
    )

    other_result = await executor.execute(other_call, other_context)

    _assert_envelope(
        other_result,
        other_call,
        status=ToolExecutionStatus.FAILED,
        error_code="agent.tool_failed",
    )
    assert other_result.value is None
    assert lookup.calls == [PLAN_DATE]
    assert tool_database.sessions.opened == tool_database.sessions.closed == 2
    assert tool_database.sessions.active == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "actor"),
    (
        ("daily_plan.read_current", TrustedActor(tenant_id=1, user_id=10)),
        ("daily_plan.read_context", TrustedActor(tenant_id=1, user_id=10)),
        ("calendar.read_evaluation", TrustedActor(tenant_id=1, user_id=10)),
        ("settings.read_class_areas", TrustedActor(tenant_id=2, user_id=10)),
    ),
)
async def test_missing_read_projection_is_sanitized_and_closes_the_session(
    tool_database: _ToolDatabase,
    tool_name: str,
    actor: TrustedActor,
):
    executor = _executor(tool_database.sessions)
    context = _context(999_999, actor=actor)
    call = _call(context, tool_name=tool_name, permission=Permission.READ)

    result = await executor.execute(call, context)

    _assert_envelope(
        result,
        call,
        status=ToolExecutionStatus.FAILED,
        error_code="agent.tool_failed",
    )
    assert result.value is None
    assert tool_database.sessions.opened == tool_database.sessions.closed == 1
    assert tool_database.sessions.active == 0


@pytest.mark.asyncio
async def test_read_exception_is_sanitized_and_closes_the_session(
    tool_database: _ToolDatabase,
):
    async def failing_lookup(_target_date: date):
        raise RuntimeError("secret-token sqlite:////private/children.db")

    executor = _executor(tool_database.sessions, holiday_lookup=failing_lookup)
    context = _context(
        tool_database.plan_id,
        scope=DailyPlanScope(plan_date=PLAN_DATE),
    )
    call = _call(
        context,
        tool_name="calendar.read_evaluation",
        permission=Permission.READ,
    )

    result = await executor.execute(call, context)

    _assert_envelope(
        result,
        call,
        status=ToolExecutionStatus.FAILED,
        error_code="agent.tool_failed",
    )
    assert result.value is None
    assert "secret-token" not in repr(result)
    assert "children.db" not in repr(result)
    assert tool_database.sessions.opened == tool_database.sessions.closed == 1
    assert tool_database.sessions.active == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name",
    (
        "daily_plan.draft_section_patch",
        "daily_plan.draft_reflection_patch",
    ),
)
async def test_each_draft_tool_returns_the_authoritative_in_memory_plan_patch(
    tool_name: str,
):
    sessions = _ForbiddenSessionFactory()
    executor = _executor(sessions)
    context = _context(7)
    arguments = _draft_arguments(context, tool_name=tool_name)
    expected = build_plan_patch_from_arguments(
        context=context,
        tool_name=tool_name,
        arguments=arguments,
    )
    call = _call(
        context,
        tool_name=tool_name,
        permission=Permission.DRAFT,
        arguments=arguments,
    )

    result = await executor.execute(call, context)

    _assert_envelope(
        result,
        call,
        status=ToolExecutionStatus.OK,
        error_code=None,
    )
    assert type(result.value) is PlanPatch
    assert plan_patch_matches_expected(actual=result.value, expected=expected)
    assert tuple(operation.field_path for operation in result.value.operations) == (
        arguments["operations"][0]["field_path"],
    )
    assert sessions.opened == sessions.closed == sessions.active == 0


def _invalid_draft_case(
    context: AgentContext,
    case: str,
) -> tuple[str, dict[str, object]]:
    tool_name = (
        "daily_plan.draft_reflection_patch"
        if case == "reflection_uses_section_path"
        else "daily_plan.draft_section_patch"
    )
    arguments = _draft_arguments(context, tool_name=tool_name)
    if case == "before_mismatch":
        arguments["operations"][0]["before_value"] = "伪造旧值"
    elif case == "fingerprint_mismatch":
        arguments["base_fingerprint"] = "c" * 64
    elif case == "target_mismatch":
        arguments["target"]["daily_plan_id"] = 8
    elif case == "section_uses_reflection_path":
        arguments["operations"][0].update(
            field_path="daily_reflection",
            before_value="孩子们主动观察了落叶",
        )
    elif case == "reflection_uses_section_path":
        arguments["operations"][0].update(
            field_path="activity_goal",
            before_value="认识秋天",
        )
    else:
        raise AssertionError(f"unknown_case:{case}")
    return tool_name, arguments


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    (
        "before_mismatch",
        "fingerprint_mismatch",
        "target_mismatch",
        "section_uses_reflection_path",
        "reflection_uses_section_path",
    ),
)
async def test_invalid_draft_binding_or_tool_path_is_rejected_without_a_session(
    case: str,
):
    sessions = _ForbiddenSessionFactory()
    executor = _executor(sessions)
    context = _context(7)
    tool_name, arguments = _invalid_draft_case(context, case)
    call = _call(
        context,
        tool_name=tool_name,
        permission=Permission.DRAFT,
        arguments=arguments,
    )

    result = await executor.execute(call, context)

    _assert_envelope(
        result,
        call,
        status=ToolExecutionStatus.REJECTED,
        error_code="agent.tool_schema_invalid",
    )
    assert result.value is None
    assert sessions.opened == sessions.closed == sessions.active == 0


async def _database_snapshot(
    factory: async_sessionmaker[AsyncSession],
    plan_id: int,
) -> tuple[tuple[object, ...], int]:
    async with factory() as session:
        plan = await session.get(DailyPlan, plan_id)
        if plan is None:
            raise AssertionError("seeded_plan_missing")
        export_count = await session.scalar(
            select(func.count()).select_from(ExportRecord)
        )
        return (
            (
                plan.activity_goal,
                plan.activity_prep,
                plan.daily_reflection,
                plan.updated_at,
            ),
            int(export_count or 0),
        )


@pytest.mark.asyncio
async def test_draft_changes_no_database_ui_body_audit_or_export_state(
    tool_database: _ToolDatabase,
    caplog: pytest.LogCaptureFixture,
):
    executor = _executor(tool_database.sessions)
    context = _context(tool_database.plan_id)
    arguments = _draft_arguments(
        context,
        tool_name="daily_plan.draft_section_patch",
    )
    call = _call(
        context,
        tool_name="daily_plan.draft_section_patch",
        permission=Permission.DRAFT,
        arguments=arguments,
    )
    ui_body = {
        "activity_goal": "认识秋天",
        "activity_prep": "",
        "daily_reflection": "孩子们主动观察了落叶",
    }
    before_ui = dict(ui_body)
    before_database = await _database_snapshot(
        tool_database.raw_factory,
        tool_database.plan_id,
    )
    caplog.clear()

    with caplog.at_level(logging.INFO):
        result = await executor.execute(call, context)

    after_database = await _database_snapshot(
        tool_database.raw_factory,
        tool_database.plan_id,
    )
    assert result.status is ToolExecutionStatus.OK
    assert result.value.operations[0].after_value == "探索秋天"
    assert after_database == before_database
    assert ui_body == before_ui
    assert not any(hasattr(record, "audit_action") for record in caplog.records)
    assert tool_database.sessions.opened == 0
    assert tool_database.sessions.closed == 0
    assert tool_database.sessions.active == 0
