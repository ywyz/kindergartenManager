"""Isolated application/database fixtures for the Agent WRITE contract tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import importlib
from pathlib import Path
from typing import Any
from uuid import UUID

from alembic import command
from alembic.config import Config
import pytest_asyncio
from sqlalchemy import MetaData, Table, event, inspect, select
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.core.models  # noqa: F401 - register the complete application metadata
from app.core.config import settings
from app.core.database import Base
from app.core.models.ai_key import AiApiKey
from app.core.models.daily_plan import DailyPlan
from app.core.models.user import User, UserRole
from app.service.agent.contracts import (
    DAILY_PLAN_SECTION_PATHS,
    FOUNDATION_ALLOWED_PERMISSIONS,
    AgentContext,
    DailyPlanProjection,
    DailyPlanScope,
    PlanSection,
    TrustedActor,
)
from app.service.agent.patch import (
    DraftPatchOperation,
    DraftPatchProposal,
    PlanPatch,
    PlanPatchTarget,
    build_plan_patch,
)
from app.ui.auth_context import TrustedUiSession


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PLAN_DATE = date(2026, 9, 7)
OTHER_DATE = date(2026, 9, 8)
PLAN_ID = 701
DUPLICATE_DATE_PLAN_ID = 702
ACTOR_TENANT_ID = 1
ACTOR_USER_ID = 10
NOW = datetime(2026, 9, 7, 9, 0, tzinfo=timezone.utc)
SESSION_ID = UUID("11111111-1111-4111-8111-111111111111")
OPERATION_ID = UUID("22222222-2222-4222-8222-222222222222")
TURN_ID = UUID("33333333-3333-4333-8333-333333333333")
CONTEXT_ID = UUID("44444444-4444-4444-8444-444444444444")
BASE_FINGERPRINT = "b" * 64

BEFORE_GOAL = "before-body::认识秋天"
AFTER_GOAL = "after-body::探索秋天"
AFTER_PREP = "after-prep::落叶、放大镜与记录纸"
UNRELATED_SECRET = "sk-test::must-not-enter-write-evidence"
UNRELATED_ENDPOINT = "https://provider.invalid/must-not-enter-write-evidence"
PROVIDER_SENTINEL = "provider-response::must-not-enter-write-evidence"
PLAN_CLASS_NAME = "星星班"
PLAN_REFLECTION = "孩子们主动观察了落叶"
PLAN_CREATED_AT = datetime(2026, 9, 7, 8, 0, tzinfo=timezone.utc)
PLAN_UPDATED_AT = datetime(2026, 9, 7, 8, 30, tzinfo=timezone.utc)


@dataclass(slots=True)
class MutableClock:
    """Deterministic UTC clock; time is the only mocked system boundary."""

    current: datetime = NOW

    def __call__(self) -> datetime:
        return self.current

    def move_to(self, value: datetime) -> None:
        self.current = value

    def advance(self, delta: timedelta) -> None:
        self.current += delta


@dataclass(slots=True)
class WriteDatabase:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]


def write_api() -> Any:
    """Import the future public seam inside a test, keeping collection clean."""
    return importlib.import_module("app.service.agent.confirmed_write")


def trusted_ui_session(
    *,
    tenant_id: int = ACTOR_TENANT_ID,
    user_id: int = ACTOR_USER_ID,
    session_id: UUID = SESSION_ID,
    expires_at_utc: datetime = NOW + timedelta(hours=1),
) -> TrustedUiSession:
    username = (
        "agent-write-teacher"
        if tenant_id == ACTOR_TENANT_ID and user_id == ACTOR_USER_ID
        else f"teacher-{tenant_id}-{user_id}"
    )
    return TrustedUiSession(
        session_id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        role=UserRole.teacher.value,
        username=username,
        display_name="测试教师",
        issued_at_utc=NOW - timedelta(minutes=5),
        expires_at_utc=expires_at_utc,
    )


def build_patch(
    *,
    plan_id: int = PLAN_ID,
    plan_date: date = PLAN_DATE,
    before_goal: str = BEFORE_GOAL,
    after_goal: str = AFTER_GOAL,
    before_prep: str = "",
    after_prep: str | None = None,
    operation_id: UUID = OPERATION_ID,
    turn_id: UUID = TURN_ID,
    tool_name: str = "daily_plan.draft_section_patch",
) -> PlanPatch:
    """Build a real F005 PlanPatch instead of inventing a test-only patch shape."""
    content_by_path = {path: "" for path in DAILY_PLAN_SECTION_PATHS}
    content_by_path.update(
        {
            "activity_goal": before_goal,
            "activity_prep": before_prep,
            "daily_reflection": PLAN_REFLECTION,
        }
    )
    sections = tuple(
        PlanSection(
            field_path=field_path,
            content=content_by_path[field_path],
            truncated=False,
        )
        for field_path in DAILY_PLAN_SECTION_PATHS
    )
    projection = DailyPlanProjection(
        plan_id=plan_id,
        plan_date=plan_date,
        week_number=2,
        weekday_cn="周一",
        grade="大班",
        class_name=PLAN_CLASS_NAME,
        sections=sections,
        updated_at_utc=NOW - timedelta(minutes=5),
        content_sha256="c" * 64,
    )
    context = AgentContext(
        context_id=CONTEXT_ID,
        operation_id=operation_id,
        turn_id=turn_id,
        created_at_utc=NOW - timedelta(minutes=1),
        expires_at_utc=NOW + timedelta(minutes=4),
        locale="zh-CN",
        actor=TrustedActor(
            tenant_id=ACTOR_TENANT_ID,
            user_id=ACTOR_USER_ID,
        ),
        active_scope=DailyPlanScope(daily_plan_id=plan_id),
        facts=(projection,),
        base_fingerprint=BASE_FINGERPRINT,
        allowed_permissions=FOUNDATION_ALLOWED_PERMISSIONS,
    )
    operations = [
        DraftPatchOperation(
            field_path="activity_goal",
            before_value=before_goal,
            after_value=after_goal,
        )
    ]
    if after_prep is not None:
        operations.append(
            DraftPatchOperation(
                field_path="activity_prep",
                before_value=before_prep,
                after_value=after_prep,
            )
        )
    proposal = DraftPatchProposal(
        operation_id=operation_id,
        turn_id=turn_id,
        tool_name=tool_name,
        target=PlanPatchTarget(daily_plan_id=plan_id, plan_date=plan_date),
        base_fingerprint=BASE_FINGERPRINT,
        operations=tuple(operations),
        warnings=(PROVIDER_SENTINEL,),
    )
    return build_plan_patch(context=context, proposal=proposal)


async def _seed_database(factory: async_sessionmaker[AsyncSession]) -> None:
    async with factory() as session:
        session.add(
            User(
                id=ACTOR_USER_ID,
                tenant_id=ACTOR_TENANT_ID,
                username="agent-write-teacher",
                hashed_password=UNRELATED_SECRET,
                role=UserRole.teacher,
                is_active=True,
                display_name="测试教师",
            )
        )
        session.add(
            AiApiKey(
                tenant_id=ACTOR_TENANT_ID,
                user_id=ACTOR_USER_ID,
                api_base_url=UNRELATED_ENDPOINT,
                model_name="synthetic-model",
                api_key_encrypted=UNRELATED_SECRET,
                key_type="text",
                is_active=True,
            )
        )
        session.add_all(
            [
                DailyPlan(
                    id=PLAN_ID,
                    tenant_id=ACTOR_TENANT_ID,
                    user_id=ACTOR_USER_ID,
                    plan_date=PLAN_DATE,
                    week_number=2,
                    weekday_cn="周一",
                    grade="大班",
                    class_name=PLAN_CLASS_NAME,
                    activity_goal=BEFORE_GOAL,
                    activity_prep="",
                    daily_reflection=PLAN_REFLECTION,
                    created_at=PLAN_CREATED_AT,
                    updated_at=PLAN_UPDATED_AT,
                ),
                # Deliberately preserve the live schema fact that dates need not be unique.
                DailyPlan(
                    id=DUPLICATE_DATE_PLAN_ID,
                    tenant_id=ACTOR_TENANT_ID,
                    user_id=ACTOR_USER_ID,
                    plan_date=PLAN_DATE,
                    week_number=2,
                    weekday_cn="周一",
                    grade="大班",
                    class_name="同日另一计划",
                    activity_goal="同日重复记录",
                    activity_prep="",
                    daily_reflection="",
                    created_at=PLAN_CREATED_AT,
                    updated_at=PLAN_UPDATED_AT,
                ),
            ]
        )
        await session.commit()


@pytest_asyncio.fixture
async def write_database(tmp_path: Path) -> AsyncIterator[WriteDatabase]:
    database_path = tmp_path / "agent-write.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await _seed_database(factory)
    try:
        yield WriteDatabase(engine=engine, session_factory=factory)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def migrated_write_database(
    tmp_path: Path,
    monkeypatch,
) -> AsyncIterator[WriteDatabase]:
    """Use the real migration path for database-trigger immutability checks."""
    database_path = tmp_path / "agent-write-migrated.db"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)
    command.upgrade(Config(str(REPOSITORY_ROOT / "alembic.ini")), "head")

    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await _seed_database(factory)
    try:
        yield WriteDatabase(engine=engine, session_factory=factory)
    finally:
        await engine.dispose()


def _normalize_database_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


def _reflect_database(connection: Connection) -> tuple[object, ...]:
    reflected: list[object] = []
    inspector = inspect(connection)
    for table_name in sorted(inspector.get_table_names()):
        metadata = MetaData()
        table = Table(table_name, metadata, autoload_with=connection)
        rows = connection.execute(select(table)).mappings()
        normalized_rows = [
            tuple((name, _normalize_database_value(row[name])) for name in sorted(row))
            for row in rows
        ]
        reflected.append((table_name, tuple(sorted(normalized_rows, key=repr))))
    return tuple(reflected)


async def database_snapshot(database: WriteDatabase) -> tuple[object, ...]:
    async with database.engine.connect() as connection:
        return await connection.run_sync(_reflect_database)


@contextmanager
def capture_sql(engine: AsyncEngine) -> Iterator[list[str]]:
    statements: list[str] = []

    def before_cursor_execute(
        _connection,
        _cursor,
        statement: str,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        statements.append(" ".join(statement.split()))

    event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", before_cursor_execute)


def dml_statements(statements: list[str]) -> list[str]:
    return [
        statement
        for statement in statements
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]


@contextmanager
def checked_out_connections(engine: AsyncEngine) -> Iterator[dict[str, int]]:
    state = {"active": 0, "maximum": 0}

    def checkout(*_args) -> None:
        state["active"] += 1
        state["maximum"] = max(state["maximum"], state["active"])

    def checkin(*_args) -> None:
        state["active"] -= 1

    event.listen(engine.sync_engine, "checkout", checkout)
    event.listen(engine.sync_engine, "checkin", checkin)
    try:
        yield state
    finally:
        event.remove(engine.sync_engine, "checkout", checkout)
        event.remove(engine.sync_engine, "checkin", checkin)
