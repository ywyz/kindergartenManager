import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.exceptions import AiCallError, AiParseError, ConfigError
from app.integration.ai_client import adapt_client, lesson_plan_client
from app.integration.ai_client.base import call_ai
from app.ui import auth_context


class Session:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class Element:
    def __init__(self):
        self.value = None
        self.text = ""
        self.loading = False

    def classes(self, **_kwargs):
        return self

    def props(self, value=None, remove=None):
        if value == "loading":
            self.loading = True
        if remove == "loading":
            self.loading = False


def split_handler(process):
    """Execute the actual nested UI callback with isolated UI/DB seams."""
    source = Path("app/ui/pages/daily_plan.py").read_text()
    tree = ast.parse(source)
    function = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "_do_split")
    for i, node in enumerate(function.body):
        if isinstance(node, ast.Nonlocal):
            function.body[i] = ast.Global(names=node.names)
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    env = {
        "asyncio": asyncio, "DailyPlanUiTarget": object,
        "AiCallError": AiCallError, "AiParseError": AiParseError,
        "ConfigError": ConfigError, "tenant_id": 1, "user_id": 1,
        "AsyncSessionLocal": Session, "process_lesson_plan": process,
        "_require_live_session": AsyncMock(return_value=object()),
        "_is_current_plan_target": lambda _: True,
        "page_client": SimpleNamespace(is_deleted=False),
        "split_operations": SimpleNamespace(owns=lambda _: True),
        "form_generation": SimpleNamespace(advance=lambda: None),
        "state": {}, "split_task": None,
    }
    for name in ("split_msg", "split_btn", "name_input", "goal_area", "prep_area", "key_area", "difficult_area", "adapted_area", "original_area"):
        env[name] = Element()
    exec(compile(module, "daily_plan_callback", "exec"), env)  # noqa: S102 - execute fixed repository AST, never user input
    return env


@pytest.mark.asyncio
async def test_success_refills_and_releases_button():
    result = SimpleNamespace(activity_name="名称", activity_goal="目标", activity_prep="准备", activity_key="重点", activity_difficult="难点", activity_process_adapted="适配", activity_process_original="原文", diff_result=[], activity_name_hint="")
    env = split_handler(AsyncMock(return_value=result))
    await env["_do_split"](object(), (object(), "教案", "中班"))
    assert env["goal_area"].value == "目标"
    assert "拆分完成" in env["split_msg"].text
    assert not env["split_btn"].loading
    assert env["split_task"] is None


@pytest.mark.asyncio
async def test_timeout_is_visible_and_button_recovers():
    env = split_handler(AsyncMock(side_effect=AiCallError("AI 请求超时")))
    await env["_do_split"](object(), (object(), "教案", "中班"))
    assert "响应超时" in env["split_msg"].text
    assert not env["split_btn"].loading
    assert env["goal_area"].value is None


@pytest.mark.asyncio
async def test_provider_error_never_displays_raw_message():
    env = split_handler(AsyncMock(side_effect=AiCallError("secret-provider-payload")))
    await env["_do_split"](object(), (object(), "教案", "中班"))
    assert "secret-provider-payload" not in env["split_msg"].text


@pytest.mark.asyncio
async def test_changed_form_is_not_overwritten_and_explains_discard():
    async def process(**_kwargs):
        env["_is_current_plan_target"] = lambda _: False
        return object()
    env = split_handler(process)
    await env["_do_split"](object(), (object(), "教案", "中班"))
    assert "未回填" in env["split_msg"].text
    assert env["goal_area"].value is None
    assert not env["split_btn"].loading


@pytest.mark.asyncio
async def test_deleted_page_does_not_revalidate_in_finally():
    async def process(**_kwargs):
        env["page_client"].is_deleted = True
        raise asyncio.CancelledError
    env = split_handler(process)
    with pytest.raises(asyncio.CancelledError):
        await env["_do_split"](object(), (object(), "教案", "中班"))
    assert env["_require_live_session"].await_count == 1
    assert env["split_task"] is None


@pytest.mark.asyncio
async def test_page_delete_callback_cancels_inflight_split():
    tree = ast.parse(Path("app/ui/pages/daily_plan.py").read_text())
    function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_cancel_deleted_page_split")
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    task = asyncio.create_task(asyncio.sleep(30))
    env = {"split_task": task}
    exec(compile(module, "page_delete_callback", "exec"), env)  # noqa: S102 - fixed repository AST with isolated seams
    env["_cancel_deleted_page_split"]()
    with pytest.raises(asyncio.CancelledError):
        await task


class MissingStorage:
    @property
    def user(self):
        raise AssertionError("storage removed")


def auth_seams(monkeypatch, *, deleted=False, storage=None):
    monkeypatch.setattr(auth_context, "context", SimpleNamespace(client=SimpleNamespace(is_deleted=deleted, has_socket_connection=not deleted)))
    monkeypatch.setattr(auth_context, "app", SimpleNamespace(storage=storage or MissingStorage()))
    routes = []
    monkeypatch.setattr(auth_context, "ui", SimpleNamespace(navigate=SimpleNamespace(to=routes.append)))
    monkeypatch.setattr(auth_context, "AsyncSessionLocal", Session)
    return routes


@pytest.mark.asyncio
async def test_deleted_client_does_not_touch_user_storage(monkeypatch):
    routes = auth_seams(monkeypatch, deleted=True)
    assert await auth_context.require_current_ui_session() is None
    assert routes == []


@pytest.mark.asyncio
async def test_missing_storage_fails_closed_without_assertion(monkeypatch):
    routes = auth_seams(monkeypatch)
    assert await auth_context.require_current_ui_session() is None
    assert routes == ["/login"]


@pytest.mark.asyncio
async def test_storage_removed_during_db_validation(monkeypatch):
    class Storage:
        calls = 0
        @property
        def user(self):
            self.calls += 1
            if self.calls > 1:
                raise AssertionError("pruned during await")
            return {"token": "synthetic"}
    routes = auth_seams(monkeypatch, storage=Storage())
    monkeypatch.setattr(auth_context, "resolve_current_ui_session", AsyncMock(return_value=object()))
    assert await auth_context.require_current_ui_session() is None
    assert routes == ["/login"]


@pytest.mark.asyncio
async def test_db_failure_and_missing_storage_are_both_handled(monkeypatch):
    class Storage:
        calls = 0
        @property
        def user(self):
            self.calls += 1
            if self.calls > 1:
                raise AssertionError("pruned")
            return {"token": "synthetic"}
    routes = auth_seams(monkeypatch, storage=Storage())
    monkeypatch.setattr(auth_context, "resolve_current_ui_session", AsyncMock(side_effect=RuntimeError("db failure")))
    assert await auth_context.require_current_ui_session() is None
    assert routes == ["/login"]


@pytest.mark.asyncio
async def test_lesson_split_uses_long_read_and_no_hidden_retries():
    requests = []
    def respond(request):
        requests.append(request)
        assert request.extensions["timeout"]["read"] == 180.0
        assert request.extensions["timeout"]["connect"] == 10.0
        raise httpx.ReadTimeout("synthetic", request=request)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(AiCallError, match="AI 请求超时"):
            await lesson_plan_client.split_lesson_plan("合成教案", "https://synthetic.invalid", "synthetic", _client=client)
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_adaptation_uses_long_read_and_no_hidden_retries():
    requests = []
    def respond(request):
        requests.append(request)
        assert request.extensions["timeout"]["read"] == 180.0
        raise httpx.ReadTimeout("synthetic", request=request)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(AiCallError):
            await adapt_client.adapt_activity_process("合成过程", "中班", "https://synthetic.invalid", "synthetic", _client=client)
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_other_json_tasks_keep_default_timeout():
    def respond(request):
        assert request.extensions["timeout"]["read"] == 60.0
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        assert await call_ai([], "https://synthetic.invalid", "synthetic", _client=client) == {}


def test_reconnect_window_is_configured_in_actual_entrypoint():
    tree = ast.parse(Path("app/main.py").read_text())
    run = next(n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "ui" and n.func.attr == "run")
    assert next(ast.literal_eval(k.value) for k in run.keywords if k.arg == "reconnect_timeout") == 120.0
