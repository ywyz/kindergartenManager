"""Bug #81 回归：游戏照片 multi-upload 完成与「生成」点击之间的异步竞态。

浏览器侧文件全部读取完成后才触发 on_multi_upload，但服务端
handle_upload 仍需先 await 会话重验与 await file.read()；这段 pending
窗口内点击「生成观察记录」会用旧的空 images 快照校验，用户已看到上传
完成却仍被提示「请先上传 1~3 张游戏照片」。

这些测试沿用 test_activity_name_ui 的做法：仅从页面源码抽取受信的本页
handler，在受控作用域内用 widget double 执行，不启动浏览器、不发真实
网络/AI 请求。
"""

from __future__ import annotations

import ast
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Self

from app.ui.bound_operation import UiOperationGuard
from app.ui.helpers import validate_image_count
from app.ui.pages.game_observation import validate_big_env

_PAGE_PATH = Path(__file__).parents[1] / "app" / "ui" / "pages" / "game_observation.py"
_HANDLER_NAMES = {
    "handle_upload",
    "trigger_upload",
    "do_generate",
    "trigger_generate",
}


class _Label:
    def __init__(self) -> None:
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text

    def classes(self, *args, **kwargs):
        return self


class _Button:
    def __init__(self) -> None:
        self.props_calls: list[tuple] = []

    def props(self, *args, **kwargs):
        self.props_calls.append((args, kwargs))
        return self


class _PreviewRow:
    def __init__(self) -> None:
        self.images: list[str] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc) -> bool:
        return False


class _TextArea:
    def __init__(self) -> None:
        self.value = ""


class _Authorizer:
    """模拟 require_bound_ui_session：可在 pending 中途切换为未绑定。"""

    def __init__(self) -> None:
        self.bound = True
        self.calls = 0

    async def __call__(self) -> object | None:
        self.calls += 1
        return object() if self.bound else None


class _PendingRead:
    def __init__(self) -> None:
        self.read_entered = asyncio.Event()
        self.release = asyncio.Event()


class _ReadyFile:
    def __init__(self, data: bytes) -> None:
        self._data = data

    async def read(self) -> bytes:
        return self._data


class _PendingFile:
    def __init__(self, gate: _PendingRead, data: bytes) -> None:
        self._gate = gate
        self._data = data
        self.reads = 0

    async def read(self) -> bytes:
        self.reads += 1
        self._gate.read_entered.set()
        await self._gate.release.wait()
        return self._data


class _FailingFile:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def read(self) -> bytes:
        raise self._exc


def _load_handler_scope() -> dict:
    tree = ast.parse(_PAGE_PATH.read_text(encoding="utf-8"))
    nodes: list[ast.stmt] = []
    seen: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in _HANDLER_NAMES
            and node.name not in seen
        ):
            nodes.append(node)
            seen.add(node.name)
    assert seen == _HANDLER_NAMES, f"缺少 handler: {_HANDLER_NAMES - seen}"
    module = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__",
                names=[ast.alias(name="annotations")],
                level=0,
            ),
            *nodes,
        ],
        type_ignores=[],
    )

    state: dict = {
        "images": [],
        "compressed_images": [],
        "observation_id": None,
        "generation": 0,
        "upload_generation": 0,
        "upload_pending": False,
        "upload_error": False,
    }
    error_label = _Label()
    success_label = _Label()
    image_count_label = _Label()
    generate_btn = _Button()
    preview_row = _PreviewRow()
    goal_area = _TextArea()
    record_area = _TextArea()
    eval_area = _TextArea()
    strategy_area = _TextArea()
    authorizer = _Authorizer()
    ai_calls: list[dict] = []

    def show_error(msg: str) -> None:
        error_label.set_text(msg)

    def show_success(msg: str) -> None:
        success_label.set_text(msg)

    def show_info(msg: str) -> None:
        success_label.set_text(msg)

    async def generate_observation_content(
        *, session, tenant_id, user_id, images, context
    ):
        ai_calls.append(
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "images": list(images),
                "context": context,
            }
        )
        return {"compressed_images": []}

    @asynccontextmanager
    async def session_factory():
        yield object()

    def current_payload() -> dict:
        return {
            "game_area": "建构区",
            "big_env": "户外",
            "child_names": "小明",
            "child_age": "5岁",
        }

    class _UiImageStub:
        def __init__(self, src: str) -> None:
            preview_row.images.append(src)

        def classes(self, *args, **kwargs):
            return self

    class _Logger:
        def __init__(self) -> None:
            self.errors: list[str] = []

        def error(self, msg: str, *args) -> None:
            self.errors.append(msg % args if args else msg)

    scope: dict = {
        "asyncio": asyncio,
        "state": state,
        "error_label": error_label,
        "success_label": success_label,
        "image_count_label": image_count_label,
        "generate_btn": generate_btn,
        "preview_row": preview_row,
        "goal_area": goal_area,
        "record_area": record_area,
        "eval_area": eval_area,
        "strategy_area": strategy_area,
        "show_error": show_error,
        "show_success": show_success,
        "show_info": show_info,
        "validate_image_count": validate_image_count,
        "validate_big_env": validate_big_env,
        "generate_observation_content": generate_observation_content,
        "AsyncSessionLocal": session_factory,
        "_require_bound_session": authorizer,
        "_current_observation_payload": current_payload,
        "action_guard": UiOperationGuard(),
        "tenant_id": 11,
        "user_id": 7,
        "grade_val": "中班",
        "ui": SimpleNamespace(image=_UiImageStub),
        "logger": _Logger(),
        "ai_calls": ai_calls,
        "authorizer": authorizer,
    }
    # 仅编译受信的本地产页面 handler；不执行任何用户/AI 文本。
    exec(compile(ast.fix_missing_locations(module), str(_PAGE_PATH), "exec"), scope)  # noqa: S102 - compile only trusted repository handlers
    return scope


def _start_upload(scope: dict, files: list) -> asyncio.Task:
    result = scope["trigger_upload"](SimpleNamespace(files=files))
    if asyncio.iscoroutine(result):
        return asyncio.ensure_future(result)
    return result


async def test_completed_upload_adopts_images_preview_and_new_generation() -> None:
    scope = _load_handler_scope()
    state = scope["state"]

    upload = _start_upload(scope, [_ReadyFile(b"img-ready")])
    await upload

    assert state["images"] == [b"img-ready"]
    assert state["generation"] == 1
    assert state["compressed_images"] == []
    assert state["observation_id"] is None
    assert scope["image_count_label"].text == "已上传：1 张"
    assert len(scope["preview_row"].images) == 1
    assert scope["preview_row"].images[0].startswith("data:image/jpeg;base64,")
    assert scope["error_label"].text == ""


async def test_generate_during_upload_requires_explicit_retry_and_releases_guard() -> (
    None
):
    scope = _load_handler_scope()
    gate = _PendingRead()
    upload = _start_upload(scope, [_PendingFile(gate, b"pending-photo")])
    await gate.read_entered.wait()
    await scope["trigger_generate"]()
    assert scope["ai_calls"] == []
    assert "照片正在处理中" in scope["success_label"].text
    assert "请先上传" not in scope["error_label"].text
    gate.release.set()
    await upload
    # The previous click did not silently adopt the late photo or retain a lock.
    assert scope["ai_calls"] == []
    retry = scope["trigger_generate"]()
    assert retry is not None
    await retry
    assert len(scope["ai_calls"]) == 1
    assert scope["ai_calls"][0]["images"] == [b"pending-photo"]
    assert scope["ai_calls"][0]["tenant_id"] == 11
    assert scope["ai_calls"][0]["user_id"] == 7


async def test_failed_upload_read_shows_error_and_blocks_generation() -> None:
    scope = _load_handler_scope()
    state = scope["state"]

    upload = _start_upload(scope, [_FailingFile(RuntimeError("disk gone"))])
    result = await upload

    assert result is None
    assert state["images"] == []
    assert state["generation"] == 0
    assert "照片读取失败" in scope["error_label"].text
    assert scope["preview_row"].images == []

    # 紧接着点击生成：不得带着空照片调用 AI，也不得吞掉上传错误。
    error_text = scope["error_label"].text
    await scope["trigger_generate"]()
    assert scope["ai_calls"] == []
    assert scope["error_label"].text == error_text


async def test_pending_upload_rejected_after_form_generation_invalidation() -> None:
    scope = _load_handler_scope()
    state = scope["state"]
    gate = _PendingRead()

    upload = _start_upload(scope, [_PendingFile(gate, b"stale-photo")])
    await gate.read_entered.wait()

    # 上传 pending 期间表单被编辑（等价于 _invalidate_form）。
    state["generation"] += 1
    gate.release.set()
    result = await upload

    assert result is None
    assert state["images"] == []
    assert state["generation"] == 1  # 迟到上传不得再推进代次
    assert scope["preview_row"].images == []
    assert scope["image_count_label"].text == ""


async def test_pending_upload_rejected_when_session_binding_lost() -> None:
    scope = _load_handler_scope()
    state = scope["state"]
    authorizer = scope["authorizer"]
    gate = _PendingRead()

    upload = _start_upload(scope, [_PendingFile(gate, b"rebind-photo")])
    await gate.read_entered.wait()
    assert authorizer.calls >= 1

    # 读取返回前登录会话失效（旧 jti / 登出）。
    authorizer.bound = False
    gate.release.set()
    result = await upload

    assert result is None
    assert state["images"] == []
    assert state["generation"] == 0
    assert scope["preview_row"].images == []
    assert scope["error_label"].text == ""


async def test_concurrent_upload_batches_discard_the_older_pending_batch() -> None:
    scope = _load_handler_scope()
    state = scope["state"]
    gate_a = _PendingRead()
    gate_b = _PendingRead()

    upload_a = _start_upload(scope, [_PendingFile(gate_a, b"batch-a")])
    await gate_a.read_entered.wait()

    # 第二个批量上传事件立即使第一批的 upload_generation 失效。
    upload_b = _start_upload(scope, [_PendingFile(gate_b, b"batch-b")])
    await gate_b.read_entered.wait()

    gate_a.release.set()
    gate_b.release.set()
    result_a = await upload_a
    result_b = await upload_b

    assert result_a is None
    assert result_b is None
    assert state["images"] == [b"batch-b"]
    assert state["generation"] == 1
    assert len(scope["preview_row"].images) == 1


async def test_failed_batch_is_atomic_and_can_retry_without_a_retained_lock() -> None:
    scope = _load_handler_scope()
    await _start_upload(
        scope, [_ReadyFile(b"first"), _FailingFile(OSError("private path"))]
    )
    assert scope["state"]["images"] == []
    assert scope["preview_row"].images == []
    await scope["trigger_generate"]()
    assert scope["ai_calls"] == []
    assert "private path" not in scope["error_label"].text
    await _start_upload(scope, [_ReadyFile(b"retry")])
    request = scope["trigger_generate"]()
    assert request is not None
    await request
    assert scope["ai_calls"][0]["images"] == [b"retry"]


async def test_older_completion_does_not_clear_newer_pending_state() -> None:
    scope = _load_handler_scope()
    first, second = _PendingRead(), _PendingRead()
    a = _start_upload(scope, [_PendingFile(first, b"older")])
    await first.read_entered.wait()
    b = _start_upload(scope, [_PendingFile(second, b"newer")])
    await second.read_entered.wait()
    first.release.set()
    await a
    assert scope["state"]["upload_pending"] is True
    await scope["trigger_generate"]()
    assert scope["ai_calls"] == []
    second.release.set()
    await b
    assert scope["state"]["upload_pending"] is False
    assert scope["state"]["images"] == [b"newer"]


async def test_upload_start_during_generation_auth_rejects_frozen_old_click() -> None:
    scope = _load_handler_scope()
    await _start_upload(scope, [_ReadyFile(b"existing")])
    entered, resume = asyncio.Event(), asyncio.Event()

    async def blocked_auth():
        entered.set()
        await resume.wait()
        return True

    scope["_require_bound_session"] = blocked_auth
    request = asyncio.create_task(scope["trigger_generate"]())
    await entered.wait()
    pending = scope["trigger_upload"](SimpleNamespace(files=[_ReadyFile(b"new")]))
    resume.set()
    await request
    assert scope["ai_calls"] == []
    # Explicit retry after the new upload is the only operation allowed to use it.
    await pending
    retry = scope["trigger_generate"]()
    assert retry is not None
    await retry
    assert scope["ai_calls"][0]["images"] == [b"existing", b"new"]
