"""WP-D weekly prompt activation and bounded integration contracts."""

import pytest

from app.repository.prompt_repository import get_active_prompt, save_new_version


@pytest.mark.parametrize(
    "task",
    [
        "weekly_morning_talk",
        "weekly_games",
        "weekly_area",
        "weekly_materials",
        "weekly_focus",
        "weekly_environment",
        "weekly_habits",
        "weekly_home",
    ],
)
async def test_weekly_prompt_can_activate(async_session, task):
    from app.core.models.user import User

    async_session.add(
        User(
            id=1,
            tenant_id=1,
            username="synthetic",
            hashed_password="unusable",
            role="teacher",
            is_active=True,
        )
    )
    await async_session.commit()
    saved = await save_new_version(async_session, 1, 1, task, "周计划分项提示词")
    active = await get_active_prompt(async_session, 1, 1, task)
    assert active.id == saved.id
    assert active.content == "周计划分项提示词"


from tests.test_wpc_identity import world as _world

world = _world


async def test_weekly_activation_waits_for_actor_transaction(world):
    import asyncio

    from sqlalchemy import select, text

    from app.core.models.user import User

    factory = world[0]
    async with factory() as held:
        if held.bind.dialect.name == "sqlite":
            await held.execute(text("BEGIN IMMEDIATE"))
        await held.execute(
            select(User).where(User.tenant_id == 11, User.id == 3).with_for_update()
        )
        started = asyncio.Event()

        async def activate():
            async with factory() as session:
                started.set()
                return await save_new_version(
                    session, 11, 3, "weekly_focus", "三条本周重点"
                )

        task = asyncio.create_task(activate())
        await started.wait()
        try:
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(task), 0.15)
        finally:
            await held.rollback()
            await task


async def test_stamp_activation_rollback_and_actor_isolation(world):
    from app.repository.prompt_repository import rollback_to_version
    from app.service.shared_weekly.prompt_contracts import read_stamp

    factory, _, actors, _ = world
    async with factory() as session:
        initial, default = await read_stamp(session, actors[3], "weekly_focus")
        assert initial.id is None and default
        one = await save_new_version(session, 11, 3, "weekly_focus", "three points v1")
        first, _ = await read_stamp(session, actors[3], "weekly_focus")
        await save_new_version(session, 11, 3, "weekly_focus", "three points v2")
        second, _ = await read_stamp(session, actors[3], "weekly_focus")
        assert first != second
        await rollback_to_version(session, 11, 3, "weekly_focus", one.version)
        assert (await read_stamp(session, actors[3], "weekly_focus"))[0] == first
        assert (await read_stamp(session, actors[4], "weekly_focus"))[0] == initial
        await save_new_version(session, 11, 3, "weekly_focus", "x" * 8193)
        from app.service.academic_identity.contracts import IdentityRejected

        with pytest.raises(IdentityRejected, match="prompt_invalid"):
            await read_stamp(session, actors[3], "weekly_focus")


async def test_prompt_migration_preserves_old_and_refuses_populated_downgrade(world):
    from alembic.config import Config

    from alembic import command
    from app.core.models.prompt_template import PromptTemplate

    factory = world[0]
    async with factory() as session:
        old = await save_new_version(session, 11, 3, "split", "old exact")
        old_id = old.id
    command.downgrade(Config("alembic.ini"), "b153c7e9f026")
    command.upgrade(Config("alembic.ini"), "head")
    async with factory() as session:
        old = await session.get(PromptTemplate, old_id)
        assert (old.content, old.version, old.is_active) == ("old exact", 1, True)
        for task in [
            "weekly_morning_talk",
            "weekly_games",
            "weekly_area",
            "weekly_materials",
            "weekly_focus",
            "weekly_environment",
            "weekly_habits",
            "weekly_home",
        ]:
            await save_new_version(session, 11, 3, task, "weekly exact")
    with pytest.raises(RuntimeError, match="weekly_prompt_nonempty_downgrade_denied"):
        command.downgrade(Config("alembic.ini"), "b153c7e9f026")
    async with factory() as session:
        assert (
            await get_active_prompt(session, 11, 3, "weekly_focus")
        ).content == "weekly exact"


@pytest.mark.parametrize(
    "kind",
    [
        "valid",
        "timeout",
        "network",
        "status",
        "malformed",
        "duplicate",
        "extra",
        "refusal",
        "oversize",
        "outputsize",
        "tools",
        "cancel",
    ],
)
async def test_one_request_closed_transport(kind):
    import asyncio
    import json

    import httpx

    from app.integration.ai_client.weekly_authoring_client import (
        WeeklyAIConfig,
        generate,
    )
    from app.service.academic_identity.contracts import IdentityRejected

    requests = []

    async def respond(request):
        requests.append(request)
        sent = json.loads(request.content)
        assert set(sent) == {"messages", "model", "response_format"}
        assert len(sent["messages"]) == 2
        if kind == "timeout":
            raise httpx.ReadTimeout("sensitive")
        if kind == "network":
            raise httpx.ConnectError("sensitive")
        if kind == "cancel":
            raise asyncio.CancelledError
        if kind == "status":
            return httpx.Response(503, text="sensitive")
        if kind == "oversize":
            return httpx.Response(200, content=b" " * 65537)
        content = '{"values":{"focus.0":"内容"}}'
        if kind == "malformed":
            content = "{"
        if kind == "duplicate":
            content = '{"values":{"focus.0":"a","focus.0":"b"}}'
        if kind == "extra":
            content = '{"values":{"focus.0":"a"},"save":true}'
        if kind == "outputsize":
            content = json.dumps({"values": {"focus.0": "x" * 16385}})
        message = {"content": content}
        if kind == "refusal":
            message["refusal"] = "no"
        if kind == "tools":
            message["tool_calls"] = [{"name": "save"}]
        return httpx.Response(
            200, json={"choices": [{"message": message, "finish_reason": "stop"}]}
        )

    config = WeeklyAIConfig("https://synthetic.invalid/v1", "synthetic-secret", "model")
    assert "synthetic-secret" not in repr(config)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        if kind == "valid":
            assert await generate("p", {}, config, _client=client) == {
                "values": {"focus.0": "内容"}
            }
        elif kind == "cancel":
            with pytest.raises(asyncio.CancelledError):
                await generate("p", {}, config, _client=client)
        else:
            code = (
                "ai_timeout"
                if kind == "timeout"
                else "ai_unavailable"
                if kind in ("status", "network")
                else "ai_invalid"
            )
            with pytest.raises(IdentityRejected, match="^" + code + "$"):
                await generate("p", {}, config, _client=client)
    assert len(requests) == 1


@pytest.mark.parametrize(
    "url,key,model",
    [
        ("http://synthetic.invalid", "k", "m"),
        ("https://user:pass@synthetic.invalid", "k", "m"),
        ("https://synthetic.invalid/#x", "k", "m"),
        ("https://synthetic.invalid", "", "m"),
        ("https://synthetic.invalid", "k", ""),
    ],
)
def test_unsafe_config_rejects(url, key, model):
    from app.integration.ai_client.weekly_authoring_client import WeeklyAIConfig
    from app.service.academic_identity.contracts import IdentityRejected

    with pytest.raises(IdentityRejected, match="config_invalid"):
        WeeklyAIConfig(url, key, model)


async def test_oversize_request_zero_requests():
    import httpx

    from app.integration.ai_client.weekly_authoring_client import (
        WeeklyAIConfig,
        generate,
    )
    from app.service.academic_identity.contracts import IdentityRejected

    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(IdentityRejected, match="ai_invalid"):
            await generate(
                "x" * 17000,
                {},
                WeeklyAIConfig("https://synthetic.invalid", "k", "m"),
                _client=client,
            )
    assert requests == []


async def test_config_uses_current_actor_and_unsafe_secret_file_fails(
    world, monkeypatch, tmp_path
):
    from app.integration.ai_client import weekly_authoring_client as client
    from app.repository.ai_key_repository import save_ai_key
    from app.service.academic_identity.contracts import IdentityRejected

    factory, _, actors, _ = world
    path = tmp_path / ".kindergarten_secrets"
    path.touch(mode=0o600)
    monkeypatch.setattr(client, "_secrets_file_path", lambda: path)
    async with factory() as session:
        await save_ai_key(
            session, 11, 4, "https://synthetic.invalid/v1", "source-teacher-secret"
        )
        with pytest.raises(IdentityRejected, match="config_invalid"):
            await client.load_config(session, actors[3])
        await save_ai_key(
            session, 11, 3, "https://synthetic.invalid/v1", "actor-secret"
        )
        config = await client.load_config(session, actors[3])
        assert config.api_key == "actor-secret"
        path.chmod(0o644)
        with pytest.raises(IdentityRejected, match="config_invalid"):
            await client.load_config(session, actors[3])


async def test_weekly_prompt_ui_callback_never_calls_generic_text_client(
    world, monkeypatch
):
    """Invoke the real rendered callback; replace only UI widget surfaces and HTTP."""
    from types import SimpleNamespace

    from app.ui.pages import prompt_mgmt

    buttons = {}
    expansions = []
    calls = []

    class Widget:
        def __init__(self, *args, **kwargs):
            self.value = kwargs.get("value", "synthetic weekly text")
            self.visible = True

        def classes(self, *args, **kwargs):
            return self

        def props(self, *args, **kwargs):
            return self

        def on_value_change(self, *args, **kwargs):
            return self

        def set_visibility(self, value):
            self.visible = value

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def button(label, *, on_click):
        buttons[label] = on_click
        return Widget()

    def expansion(*args, **kwargs):
        result = Widget()
        expansions.append(result)
        return result

    async def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("weekly prompt UI must require authorized authoring")

    async def live():
        return world[2][3]

    monkeypatch.setattr(prompt_mgmt, "AsyncSessionLocal", world[0])
    monkeypatch.setattr(prompt_mgmt, "call_ai_text", forbidden)
    monkeypatch.setattr(prompt_mgmt, "get_active_ai_key", forbidden)
    monkeypatch.setattr(
        prompt_mgmt,
        "ui",
        SimpleNamespace(
            card=Widget,
            label=Widget,
            badge=Widget,
            textarea=Widget,
            column=Widget,
            expansion=expansion,
            button=button,
        ),
    )
    for task in prompt_mgmt.WEEKLY_LABELS:
        await prompt_mgmt._build_task_panel(world[2][3], live, task)
        assert not expansions[-1].visible
        await buttons["测试当前提示词"]()
    assert calls == []
