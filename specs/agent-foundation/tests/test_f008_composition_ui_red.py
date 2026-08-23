"""F008 RED tests for application composition and the daily-plan Agent UI seam."""

import ast
import asyncio
from contextlib import asynccontextmanager
from dataclasses import FrozenInstanceError, dataclass, field
from datetime import date
from importlib import import_module
import inspect
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.models  # noqa: F401 - register all ORM models
from app.core.crypto import encrypt
from app.core.database import Base
from app.core.models.ai_key import AiApiKey
from app.core.models.daily_plan import DailyPlan
from app.service.agent.contracts import DailyPlanProjection, TrustedActor


PLAN_DATE = date(2026, 9, 7)
OTHER_DATE = date(2026, 9, 8)
PLAIN_KEY = "sk-f008-secret-never-render"


def _composition():
    return import_module("app.service.agent.composition")


def _runtime():
    return import_module("app.service.agent.runtime")


@pytest_asyncio.fixture
async def agent_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        session.add_all(
            [
                DailyPlan(
                    tenant_id=1,
                    user_id=10,
                    plan_date=PLAN_DATE,
                    week_number=2,
                    weekday_cn="周一",
                    grade="大班",
                    class_name="星星班",
                    activity_goal="认识秋天",
                ),
                DailyPlan(
                    tenant_id=1,
                    user_id=10,
                    plan_date=OTHER_DATE,
                    week_number=2,
                    weekday_cn="周二",
                    grade="大班",
                    class_name="星星班",
                    activity_goal="观察落叶",
                ),
                DailyPlan(
                    tenant_id=2,
                    user_id=20,
                    plan_date=PLAN_DATE,
                    week_number=2,
                    weekday_cn="周一",
                    grade="中班",
                    class_name="月亮班",
                    activity_goal="另一租户秘密",
                ),
                AiApiKey(
                    tenant_id=1,
                    user_id=10,
                    api_base_url="https://ai.example/v1",
                    model_name="fictional-agent-model",
                    api_key_encrypted=encrypt(PLAIN_KEY),
                    key_type="text",
                    is_active=True,
                ),
            ]
        )
        await session.commit()

    yield factory
    await engine.dispose()


@dataclass
class ImmediateProvider:
    content: str = "当前计划的目标是认识秋天。"
    requests: list[object] = field(default_factory=list)

    async def complete(self, request: object) -> object:
        runtime = _runtime()
        self.requests.append(request)
        return runtime.ProviderTurnResult(
            assistant_content=self.content,
            finish_reason=runtime.ProviderFinishReason.COMPLETED,
            provider_request_id="fictional-request",
        )


@dataclass
class BlockingProvider:
    entered: asyncio.Event
    release: asyncio.Event
    content: str = "不得发布的迟到正文"
    requests: list[object] = field(default_factory=list)

    async def complete(self, request: object) -> object:
        runtime = _runtime()
        self.requests.append(request)
        self.entered.set()
        await self.release.wait()
        return runtime.ProviderTurnResult(
            assistant_content=self.content,
            finish_reason=runtime.ProviderFinishReason.COMPLETED,
        )


def _controller(module: Any, factory: object, provider: object):
    captured_configs: list[object] = []

    def provider_factory(config: object) -> object:
        captured_configs.append(config)
        return provider

    coordinator = module.DailyPlanAgentCoordinator(
        session_factory=factory,
        provider_factory=provider_factory,
    )
    controller = coordinator.create_controller(TrustedActor(tenant_id=1, user_id=10))
    return coordinator, controller, captured_configs


def test_composition_is_an_application_seam_without_nicegui_or_http_types():
    module = _composition()
    tree = ast.parse(inspect.getsource(module))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert hasattr(module, "DailyPlanAgentCoordinator")
    assert hasattr(module, "DailyPlanAgentController")
    assert hasattr(module, "AgentPanelSnapshot")
    assert hasattr(module, "AgentPanelStatus")
    assert not any(
        name == "nicegui" or name.startswith("app.ui") for name in imported_modules
    )
    assert not any(
        name.startswith("openai") or name == "httpx" for name in imported_modules
    )


def test_provider_config_and_panel_snapshot_are_frozen_and_secret_safe():
    module = _composition()
    config = module.AgentProviderConfig(
        api_base_url="https://ai.example/v1",
        model_name="fictional-agent-model",
        api_key=PLAIN_KEY,
    )
    snapshot = module.AgentPanelSnapshot(
        status=module.AgentPanelStatus.IDLE,
        selected_date=PLAN_DATE,
        assistant_content=None,
        patches=(),
        error_code=None,
    )

    assert PLAIN_KEY not in repr(config)
    assert "api_key" not in repr(config)
    with pytest.raises(FrozenInstanceError):
        config.model_name = "changed"
    with pytest.raises(FrozenInstanceError):
        snapshot.status = module.AgentPanelStatus.RUNNING


@pytest.mark.asyncio
async def test_controller_builds_fresh_actor_scoped_context_and_short_lived_credentials(
    agent_session_factory,
):
    module = _composition()
    provider = ImmediateProvider()
    _, controller, configs = _controller(module, agent_session_factory, provider)
    controller.scope_changed(PLAN_DATE)

    snapshot = await controller.run("概括当前计划")

    assert snapshot.status is module.AgentPanelStatus.SUCCEEDED
    assert snapshot.selected_date == PLAN_DATE
    assert snapshot.assistant_content == provider.content
    assert snapshot.patches == ()
    assert snapshot.error_code is None
    assert len(configs) == 1
    assert configs[0].api_base_url == "https://ai.example/v1"
    assert configs[0].model_name == "fictional-agent-model"
    assert configs[0].api_key == PLAIN_KEY
    assert PLAIN_KEY not in repr(configs[0])
    request = provider.requests[0]
    assert request.context.actor == TrustedActor(tenant_id=1, user_id=10)
    projection = next(
        fact for fact in request.context.facts if isinstance(fact, DailyPlanProjection)
    )
    assert projection.plan_date == PLAN_DATE
    assert projection.sections[0].content == "认识秋天"
    assert "另一租户秘密" not in repr(request)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("actor", "selected_date", "expected_code"),
    (
        (TrustedActor(tenant_id=1, user_id=10), None, "agent.scope_required"),
        (
            TrustedActor(tenant_id=1, user_id=10),
            date(2026, 9, 9),
            "agent.plan_not_found",
        ),
        (
            TrustedActor(tenant_id=2, user_id=20),
            PLAN_DATE,
            "agent.configuration_missing",
        ),
    ),
)
async def test_controller_fails_closed_before_provider_for_missing_prerequisites(
    agent_session_factory,
    actor,
    selected_date,
    expected_code,
):
    module = _composition()
    provider = ImmediateProvider()
    captured: list[object] = []
    coordinator = module.DailyPlanAgentCoordinator(
        session_factory=agent_session_factory,
        provider_factory=lambda config: captured.append(config) or provider,
    )
    controller = coordinator.create_controller(actor)
    controller.scope_changed(selected_date)

    snapshot = await controller.run("概括当前计划")

    assert snapshot.status is module.AgentPanelStatus.FAILED
    assert snapshot.error_code == expected_code
    assert snapshot.assistant_content is None
    assert snapshot.patches == ()
    assert provider.requests == []
    assert captured == []


@pytest.mark.asyncio
async def test_application_coordinator_enforces_busy_across_two_page_controllers(
    agent_session_factory,
):
    module = _composition()
    entered = asyncio.Event()
    release = asyncio.Event()
    provider = BlockingProvider(entered, release, content="第一个页面结果")
    coordinator = module.DailyPlanAgentCoordinator(
        session_factory=agent_session_factory,
        provider_factory=lambda _config: provider,
    )
    first = coordinator.create_controller(TrustedActor(tenant_id=1, user_id=10))
    second = coordinator.create_controller(TrustedActor(tenant_id=1, user_id=10))
    first.scope_changed(PLAN_DATE)
    second.scope_changed(OTHER_DATE)

    first_task = asyncio.create_task(first.run("第一个页面运行"))
    await entered.wait()
    second_snapshot = await second.run("第二个页面不得并发")
    release.set()
    first_snapshot = await first_task

    assert second_snapshot.status is module.AgentPanelStatus.FAILED
    assert second_snapshot.error_code == "agent.busy"
    assert first_snapshot.status is module.AgentPanelStatus.SUCCEEDED
    assert first_snapshot.assistant_content == "第一个页面结果"
    assert len(provider.requests) == 1


@pytest.mark.asyncio
async def test_scope_generation_discards_old_result_and_allows_a_fresh_turn(
    agent_session_factory,
):
    module = _composition()
    entered = asyncio.Event()
    release = asyncio.Event()
    late = BlockingProvider(entered, release)
    fresh = ImmediateProvider(content="新日期的回答")
    providers = [late, fresh]
    coordinator = module.DailyPlanAgentCoordinator(
        session_factory=agent_session_factory,
        provider_factory=lambda _config: providers.pop(0),
    )
    controller = coordinator.create_controller(TrustedActor(tenant_id=1, user_id=10))
    controller.scope_changed(PLAN_DATE)

    old_task = asyncio.create_task(controller.run("旧日期问题"))
    await entered.wait()
    controller.scope_changed(OTHER_DATE)
    release.set()
    old_snapshot = await old_task

    assert old_snapshot.selected_date == OTHER_DATE
    assert old_snapshot.status is module.AgentPanelStatus.IDLE
    assert old_snapshot.assistant_content is None
    assert old_snapshot.patches == ()

    new_snapshot = await controller.run("新日期问题")
    assert new_snapshot.status is module.AgentPanelStatus.SUCCEEDED
    assert new_snapshot.assistant_content == "新日期的回答"


@pytest.mark.asyncio
async def test_cancel_and_close_never_publish_blocked_provider_content(
    agent_session_factory,
):
    module = _composition()
    entered = asyncio.Event()
    release = asyncio.Event()
    provider = BlockingProvider(entered, release)
    _, controller, _ = _controller(module, agent_session_factory, provider)
    controller.scope_changed(PLAN_DATE)

    run_task = asyncio.create_task(controller.run("等待取消"))
    await entered.wait()
    cancelled = await controller.cancel()
    outcome = await run_task

    assert cancelled is True
    assert outcome.status is module.AgentPanelStatus.CANCELLED
    assert outcome.assistant_content is None
    assert outcome.patches == ()
    assert outcome.error_code == "agent.cancelled"

    await controller.close()
    closed = await controller.run("关闭后不得重启")
    assert closed.status is module.AgentPanelStatus.FAILED
    assert closed.error_code == "agent.page_closed"
    assert provider.content not in repr(closed)


@pytest.mark.asyncio
async def test_cancel_during_context_assembly_never_starts_provider(
    agent_session_factory,
):
    module = _composition()
    entered = asyncio.Event()
    release = asyncio.Event()

    @asynccontextmanager
    async def gated_session_factory():
        entered.set()
        await release.wait()
        async with agent_session_factory() as session:
            yield session

    provider = ImmediateProvider()
    captured_configs: list[object] = []
    coordinator = module.DailyPlanAgentCoordinator(
        session_factory=gated_session_factory,
        provider_factory=lambda config: captured_configs.append(config) or provider,
    )
    controller = coordinator.create_controller(TrustedActor(tenant_id=1, user_id=10))
    controller.scope_changed(PLAN_DATE)

    run_task = asyncio.create_task(controller.run("装配期间取消"))
    await entered.wait()
    cancel_accepted = await controller.cancel()
    release.set()
    snapshot = await run_task

    assert cancel_accepted is True
    assert provider.requests == []
    assert captured_configs == []
    assert snapshot.status is module.AgentPanelStatus.CANCELLED
    assert snapshot.error_code == "agent.cancelled"
    assert snapshot.assistant_content is None
    assert snapshot.patches == ()


@pytest.mark.asyncio
async def test_plan_change_invalidates_same_scope_fingerprint_before_publish(
    agent_session_factory,
):
    module = _composition()
    assert hasattr(module.DailyPlanAgentController, "plan_changed")

    entered = asyncio.Event()
    release = asyncio.Event()
    provider = BlockingProvider(entered, release, content="旧 fingerprint 的迟到回答")
    coordinator = module.DailyPlanAgentCoordinator(
        session_factory=agent_session_factory,
        provider_factory=lambda _config: provider,
    )
    running = coordinator.create_controller(TrustedActor(tenant_id=1, user_id=10))
    notifier = coordinator.create_controller(TrustedActor(tenant_id=1, user_id=10))
    running.scope_changed(PLAN_DATE)

    run_task = asyncio.create_task(running.run("等待同日期计划变化"))
    await entered.wait()
    async with agent_session_factory() as session:
        plan = (
            await session.execute(
                select(DailyPlan).where(
                    DailyPlan.tenant_id == 1,
                    DailyPlan.user_id == 10,
                    DailyPlan.plan_date == PLAN_DATE,
                )
            )
        ).scalar_one()
        plan.activity_goal = "已经改变 fingerprint 的新目标"
        await session.commit()

    notifier.plan_changed(PLAN_DATE)
    release.set()
    snapshot = await run_task

    assert snapshot.status is module.AgentPanelStatus.FAILED
    assert snapshot.error_code == "agent.context_stale"
    assert snapshot.assistant_content is None
    assert snapshot.patches == ()


@pytest.mark.asyncio
async def test_same_controller_reentry_does_not_replace_running_attempt(
    agent_session_factory,
):
    module = _composition()
    entered = asyncio.Event()
    release = asyncio.Event()
    provider = BlockingProvider(entered, release, content="唯一运行的结果")
    _, controller, _ = _controller(module, agent_session_factory, provider)
    controller.scope_changed(PLAN_DATE)

    first_task = asyncio.create_task(controller.run("第一次运行"))
    await entered.wait()
    second_snapshot = await controller.run("同一页面重复点击")
    published_while_blocked = controller.snapshot
    release.set()
    first_snapshot = await first_task

    assert second_snapshot.status is module.AgentPanelStatus.RUNNING
    assert published_while_blocked.status is module.AgentPanelStatus.RUNNING
    assert first_snapshot.status is module.AgentPanelStatus.SUCCEEDED
    assert first_snapshot.assistant_content == "唯一运行的结果"
    assert len(provider.requests) == 1


@pytest.mark.asyncio
async def test_disconnect_cancels_attempt_but_controller_can_run_after_reconnect(
    agent_session_factory,
):
    module = _composition()
    assert hasattr(module.DailyPlanAgentController, "disconnect")

    entered = asyncio.Event()
    release = asyncio.Event()
    provider = BlockingProvider(entered, release, content="重连后的回答")
    _, controller, _ = _controller(module, agent_session_factory, provider)
    controller.scope_changed(PLAN_DATE)

    old_task = asyncio.create_task(controller.run("断线前运行"))
    await entered.wait()
    await controller.disconnect()
    release.set()
    old_snapshot = await old_task

    assert old_snapshot.status is module.AgentPanelStatus.IDLE
    assert old_snapshot.assistant_content is None
    fresh_snapshot = await controller.run("重连后重新运行")
    assert fresh_snapshot.status is module.AgentPanelStatus.SUCCEEDED
    assert fresh_snapshot.assistant_content == "重连后的回答"
    assert len(provider.requests) == 2


@pytest.mark.asyncio
async def test_host_cancel_propagates_without_leaving_controller_running(
    agent_session_factory,
):
    module = _composition()
    entered = asyncio.Event()
    release = asyncio.Event()
    blocked = BlockingProvider(entered, release, content="不得发布")
    fresh = ImmediateProvider(content="宿主取消后的新回答")
    providers = [blocked, fresh]
    coordinator = module.DailyPlanAgentCoordinator(
        session_factory=agent_session_factory,
        provider_factory=lambda _config: providers.pop(0),
    )
    controller = coordinator.create_controller(TrustedActor(tenant_id=1, user_id=10))
    controller.scope_changed(PLAN_DATE)

    cancelled_task = asyncio.create_task(controller.run("等待宿主取消"))
    await entered.wait()
    cancelled_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await cancelled_task

    assert controller.snapshot.status is module.AgentPanelStatus.IDLE
    assert controller.snapshot.assistant_content is None
    retry = await controller.run("取消后重试")
    assert retry.status is module.AgentPanelStatus.SUCCEEDED
    assert retry.assistant_content == "宿主取消后的新回答"
    assert len(blocked.requests) == 1
    assert len(fresh.requests) == 1


@pytest.mark.asyncio
async def test_discard_only_clears_agent_memory_not_caller_owned_body(
    agent_session_factory,
):
    module = _composition()
    provider = ImmediateProvider()
    _, controller, _ = _controller(module, agent_session_factory, provider)
    body = {
        "activity_goal": "正文哨兵：认识秋天",
        "daily_reflection": "正文哨兵：教师反思",
    }
    before = body.copy()
    controller.scope_changed(PLAN_DATE)
    await controller.run("只回答，不改正文")

    discarded = controller.discard()

    assert discarded.status is module.AgentPanelStatus.IDLE
    assert discarded.assistant_content is None
    assert discarded.patches == ()
    assert body == before


def test_agent_ui_surface_is_closed_and_patch_rows_are_detached_primitives():
    component = import_module("app.ui.components.agent_draft")
    panel_source = inspect.getsource(component.DailyPlanAgentPanel)

    assert component.AGENT_ACTION_LABELS == ("运行", "取消", "丢弃建议")
    assert component.AGENT_FIXED_NOTICE == "仅生成建议，不会保存或修改当前计划。"
    assert not hasattr(component, "adopt_patch")
    assert not hasattr(component, "apply_patch")
    assert not hasattr(component, "confirm_write")
    assert callable(component.render_daily_plan_agent_panel)
    assert "on_disconnect(self.disconnect)" in panel_source
    assert "on_disconnect(self.close)" not in panel_source
    assert "on_delete(self.close)" in panel_source


def test_date_selection_guard_invalidates_out_of_order_callbacks():
    date_panel = import_module("app.ui.components.date_panel")
    guard = date_panel.DateSelectionGuard()

    first = guard.select(PLAN_DATE)
    second = guard.select(OTHER_DATE)

    assert first.generation + 1 == second.generation
    assert guard.is_current(second) is True
    assert guard.is_current(first) is False
    assert guard.current == second


def test_daily_plan_page_wires_immediate_selection_and_agent_panel_without_write_actions():
    page = import_module("app.ui.pages.daily_plan")
    source = inspect.getsource(page)

    assert "on_date_selected=" in source
    assert "render_daily_plan_agent_panel" in source
    assert "scope_changed" in source
    assert source.count("plan_changed(") >= 3
    save_call = source.index("await save_daily_plan(")
    assert source.index("agent_panel.plan_changed(d)") < save_call

    direct_delete = source.index("await delete_daily_plan(")
    captured_date = source.index('deleting_date = state["selected_date"]')
    direct_invalidation = source.index("agent_panel.plan_changed(deleting_date)")
    assert captured_date < direct_invalidation < direct_delete
    assert source.index("plan_date=deleting_date", direct_delete) > direct_delete

    history_delete = source.index("await delete_daily_plan(", direct_delete + 1)
    history_invalidation = source.index("agent_panel.plan_changed(p.plan_date)")
    assert history_invalidation < history_delete
    assert "agent_controller" in source
    assert "adopt_patch" not in source
    assert "confirm_write" not in source
