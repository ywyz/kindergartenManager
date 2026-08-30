"""可信 NiceGUI 用户会话的公开行为测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import inspect
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from app.auth.jwt import create_access_token, decode_access_token
from app.auth.password import hash_password
from app.core.models.user import UserRole
from app.repository.user_repository import create_user
from app.service.agent.contracts import TrustedActor
from app.ui.auth_context import TrustedUiSession


class _FakeUiElement:
    def __init__(self, *, value=None) -> None:
        self.value = value
        self.handlers: dict[str, object] = {}
        self.class_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.prop_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.text_calls: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def classes(self, *args, **kwargs):
        self.class_calls.append((args, kwargs))
        return self

    def props(self, *args, **kwargs):
        self.prop_calls.append((args, kwargs))
        return self

    def set_text(self, value: str) -> None:
        self.text_calls.append(value)

    def on(self, event: str, handler):
        self.handlers[event] = handler
        return self


class _FakeLoginUi:
    def __init__(self) -> None:
        self.navigate = SimpleNamespace(to=Mock())
        self.inputs: dict[str, _FakeUiElement] = {}
        self.buttons: dict[str, _FakeUiElement] = {}
        self.labels: list[_FakeUiElement] = []

    def column(self):
        return _FakeUiElement()

    def label(self, _text: str):
        element = _FakeUiElement()
        self.labels.append(element)
        return element

    def input(self, *, label: str, **_kwargs):
        element = _FakeUiElement(value="")
        self.inputs[label] = element
        return element

    def button(self, text: str, **_kwargs):
        element = _FakeUiElement()
        self.buttons[text] = element
        return element


async def test_resolve_current_ui_session_rebuilds_actor_from_active_user(
    async_session,
) -> None:
    from app.ui.auth_context import resolve_current_ui_session

    user = await create_user(
        async_session,
        tenant_id=7,
        username="teacher-a",
        hashed_password=hash_password("Pass1234!"),
        role=UserRole.teacher,
        display_name="李老师",
    )
    token = create_access_token(
        user_id=user.id,
        tenant_id=7,
        role="sys_admin",
        username="stale-name",
        display_name="旧显示名",
    )

    current = await resolve_current_ui_session(async_session, token)

    assert current is not None
    assert current.tenant_id == 7
    assert current.user_id == user.id
    assert current.role == "teacher"
    assert current.username == "teacher-a"
    assert current.display_name == "李老师"
    assert current.session_id == UUID(decode_access_token(token)["jti"])
    assert current.issued_at_utc.tzinfo is not None
    assert current.expires_at_utc.tzinfo is not None
    assert "Pass1234!" not in repr(current)
    assert token not in repr(current)
    assert "session_id" not in current.as_user_dict()


async def test_resolve_current_ui_session_rejects_inactive_or_wrong_tenant_user(
    async_session,
) -> None:
    from app.ui.auth_context import resolve_current_ui_session

    user = await create_user(
        async_session,
        tenant_id=3,
        username="teacher-b",
        hashed_password=hash_password("Pass1234!"),
        role=UserRole.teacher,
    )
    wrong_tenant = create_access_token(
        user_id=user.id,
        tenant_id=4,
        role="teacher",
    )
    assert await resolve_current_ui_session(async_session, wrong_tenant) is None

    user.is_active = False
    await async_session.commit()
    inactive = create_access_token(
        user_id=user.id,
        tenant_id=3,
        role="teacher",
    )
    assert await resolve_current_ui_session(async_session, inactive) is None


def test_each_access_token_has_a_distinct_canonical_session_id() -> None:
    first = decode_access_token(
        create_access_token(user_id=1, tenant_id=1, role="teacher")
    )
    second = decode_access_token(
        create_access_token(user_id=1, tenant_id=1, role="teacher")
    )

    assert UUID(first["jti"])
    assert UUID(second["jti"])
    assert first["jti"] != second["jti"]
    assert type(first["iat"]) is int
    assert type(first["exp"]) is int


async def test_resolve_current_ui_session_rejects_noncanonical_claim_shapes(
    async_session,
) -> None:
    import jwt

    from app.auth.jwt import _ALGORITHM
    from app.core.config import settings
    from app.ui.auth_context import resolve_current_ui_session

    user = await create_user(
        async_session,
        tenant_id=8,
        username="teacher-c",
        hashed_password=hash_password("Pass1234!"),
        role=UserRole.teacher,
    )
    payload = decode_access_token(
        create_access_token(user_id=user.id, tenant_id=8, role="teacher")
    )

    for name, invalid_value in (
        ("sub", f"0{user.id}"),
        ("tenant_id", "8"),
        ("jti", str(UUID(payload["jti"])).upper()),
        ("iat", None),
    ):
        invalid_payload = {**payload, name: invalid_value}
        token = jwt.encode(invalid_payload, settings.JWT_SECRET, algorithm=_ALGORITHM)
        assert await resolve_current_ui_session(async_session, token) is None


async def test_resolve_current_ui_session_rejects_token_without_auth_epoch(
    async_session,
) -> None:
    """升级前或遗漏凭据版本的 token 必须 fail closed 并要求重新登录。"""
    import jwt

    from app.auth.jwt import _ALGORITHM
    from app.core.config import settings
    from app.ui.auth_context import resolve_current_ui_session

    user = await create_user(
        async_session,
        tenant_id=9,
        username="teacher-missing-epoch",
        hashed_password=hash_password("Pass1234!"),
        role=UserRole.teacher,
    )
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "tenant_id": user.tenant_id,
            "role": user.role.value,
            "jti": str(uuid4()),
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        settings.JWT_SECRET,
        algorithm=_ALGORITHM,
    )

    assert await resolve_current_ui_session(async_session, token) is None


async def test_resolve_current_ui_session_rechecks_expiry_after_user_lookup(
    monkeypatch,
) -> None:
    """直接 resolver 也不能返回在数据库等待期间过期的 actor。"""
    from app.ui import auth_context as module

    now = datetime.now(timezone.utc)
    session_id = uuid4()
    payload = {
        "tenant_id": 3,
        "sub": "7",
        "jti": str(session_id),
        "iat": int((now - timedelta(minutes=30)).timestamp()),
        "exp": int((now - timedelta(seconds=1)).timestamp()),
    }
    user = SimpleNamespace(
        tenant_id=3,
        id=7,
        role=UserRole.teacher,
        username="teacher-expired",
        display_name=None,
        is_active=True,
    )

    async def get_user(_session, *, tenant_id, user_id):
        assert (tenant_id, user_id) == (3, 7)
        return user

    monkeypatch.setattr(module, "decode_access_token", lambda _token: payload)
    monkeypatch.setattr(module, "get_user_by_id", get_user)

    current = await module.resolve_current_ui_session(object(), "opaque-token")

    assert current is None


async def test_daily_plan_agent_actor_comes_from_the_verified_ui_session(
    monkeypatch,
) -> None:
    from app.ui.pages import daily_plan as module

    now = datetime.now(timezone.utc)
    trusted_session = TrustedUiSession(
        session_id=uuid4(),
        tenant_id=19,
        user_id=23,
        role="teacher",
        username="teacher-d",
        display_name=None,
        issued_at_utc=now,
        expires_at_utc=now + timedelta(minutes=30),
    )
    observed: list[TrustedActor] = []

    async def require_session() -> TrustedUiSession:
        return trusted_session

    class _ActorObserved(RuntimeError):
        pass

    def create_controller(actor: TrustedActor):
        observed.append(actor)
        raise _ActorObserved

    monkeypatch.setattr(module, "require_current_ui_session", require_session)
    monkeypatch.setattr(module, "create_daily_plan_agent_controller", create_controller)

    with pytest.raises(_ActorObserved):
        await module.daily_plan_page()

    assert observed == [TrustedActor(tenant_id=19, user_id=23)]


def test_application_does_not_publish_anonymous_self_registration() -> None:
    from app import main as module

    source = inspect.getsource(module)
    assert "from app.ui.pages import register" not in source


def test_daily_plan_page_carries_the_loaded_identity_and_revision_into_save() -> None:
    from app.ui.pages import daily_plan as module

    source = inspect.getsource(module)
    assert 'state["loaded_plan_id"] = plan.id' in source
    assert 'state["loaded_revision"] = plan.revision' in source
    assert '"expected_plan_id": target.plan_id' in source
    assert '"expected_revision": target.revision' in source
    assert "**save_payload" in source


async def test_require_current_ui_session_fails_closed_when_database_is_unavailable(
    monkeypatch,
) -> None:
    from app.ui import auth_context as module

    class _FailingSession:
        async def __aenter__(self):
            raise RuntimeError("database unavailable")

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    storage = {"token": "opaque-token"}
    navigate = Mock()
    monkeypatch.setattr(
        module,
        "app",
        SimpleNamespace(storage=SimpleNamespace(user=storage)),
    )
    monkeypatch.setattr(
        module,
        "ui",
        SimpleNamespace(navigate=SimpleNamespace(to=navigate)),
    )
    monkeypatch.setattr(module, "AsyncSessionLocal", _FailingSession)

    current = await module.require_current_ui_session()

    assert current is None
    assert storage == {}
    navigate.assert_called_once_with("/login")


async def test_require_current_ui_session_discards_a_result_after_token_changes(
    monkeypatch,
) -> None:
    """数据库等待期间的新登录不能让旧 token 的校验结果复活。"""
    from app.ui import auth_context as module

    class _Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    now = datetime.now(timezone.utc)
    resolved = TrustedUiSession(
        session_id=uuid4(),
        tenant_id=1,
        user_id=2,
        role="teacher",
        username="teacher",
        display_name=None,
        issued_at_utc=now,
        expires_at_utc=now + timedelta(minutes=30),
    )
    storage = {"token": "old-login-token"}
    navigate = Mock()

    async def resolve(_session, token):
        assert token == "old-login-token"
        storage["token"] = "new-login-token"
        return resolved

    monkeypatch.setattr(
        module,
        "app",
        SimpleNamespace(storage=SimpleNamespace(user=storage)),
    )
    monkeypatch.setattr(
        module,
        "ui",
        SimpleNamespace(navigate=SimpleNamespace(to=navigate)),
    )
    monkeypatch.setattr(module, "AsyncSessionLocal", _Session)
    monkeypatch.setattr(module, "resolve_current_ui_session", resolve)

    current = await module.require_current_ui_session()

    assert current is None
    assert storage == {"token": "new-login-token"}
    navigate.assert_called_once_with("/login")


async def test_require_current_ui_session_rechecks_expiry_after_database_await(
    monkeypatch,
) -> None:
    """数据库查询完成时已经过期的会话必须 fail closed。"""
    from app.ui import auth_context as module

    class _Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    now = datetime.now(timezone.utc)
    resolved = TrustedUiSession(
        session_id=uuid4(),
        tenant_id=1,
        user_id=2,
        role="teacher",
        username="teacher",
        display_name=None,
        issued_at_utc=now - timedelta(minutes=30),
        expires_at_utc=now - timedelta(microseconds=1),
    )
    storage = {"token": "expiring-token"}
    navigate = Mock()

    async def resolve(_session, token):
        assert token == "expiring-token"
        return resolved

    monkeypatch.setattr(
        module,
        "app",
        SimpleNamespace(storage=SimpleNamespace(user=storage)),
    )
    monkeypatch.setattr(
        module,
        "ui",
        SimpleNamespace(navigate=SimpleNamespace(to=navigate)),
    )
    monkeypatch.setattr(module, "AsyncSessionLocal", _Session)
    monkeypatch.setattr(module, "resolve_current_ui_session", resolve)

    current = await module.require_current_ui_session()

    assert current is None
    assert storage == {}
    navigate.assert_called_once_with("/login")


async def test_login_page_initialization_clears_token_when_database_is_unavailable(
    monkeypatch,
) -> None:
    from app.ui.pages import login as module

    class _FailingSession:
        async def __aenter__(self):
            raise RuntimeError("database unavailable")

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    storage = {"token": "opaque-token"}
    monkeypatch.setattr(
        module,
        "app",
        SimpleNamespace(storage=SimpleNamespace(user=storage)),
    )
    monkeypatch.setattr(module, "AsyncSessionLocal", _FailingSession)

    current, admin_ready, database_available = await module._load_login_page_state(
        "opaque-token"
    )

    assert current is None
    assert admin_ready is False
    assert database_available is False
    assert storage == {}


async def test_old_login_page_load_does_not_clear_a_new_token(
    monkeypatch,
) -> None:
    from app.ui.pages import login as module

    storage = {"token": "old-login-token"}
    fake_ui = _FakeLoginUi()

    async def load_state(token):
        assert token == "old-login-token"
        storage["token"] = "new-login-token"
        return None, True, True

    monkeypatch.setattr(
        module,
        "app",
        SimpleNamespace(storage=SimpleNamespace(user=storage)),
    )
    monkeypatch.setattr(module, "ui", fake_ui)
    monkeypatch.setattr(module, "_load_login_page_state", load_state)

    await module.login_page()

    assert storage == {"token": "new-login-token"}
    fake_ui.navigate.to.assert_not_called()


async def test_old_login_page_database_failure_does_not_clear_a_new_token(
    monkeypatch,
) -> None:
    from app.ui.pages import login as module

    storage = {"token": "old-login-token"}
    fake_ui = _FakeLoginUi()

    class _FailingSession:
        async def __aenter__(self):
            storage["token"] = "new-login-token"
            raise RuntimeError("database unavailable")

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        module,
        "app",
        SimpleNamespace(storage=SimpleNamespace(user=storage)),
    )
    monkeypatch.setattr(module, "ui", fake_ui)
    monkeypatch.setattr(module, "AsyncSessionLocal", _FailingSession)

    await module.login_page()

    assert storage == {"token": "new-login-token"}
    fake_ui.navigate.to.assert_not_called()


async def test_login_submit_uses_the_click_time_credentials(
    monkeypatch,
) -> None:
    from app.ui.pages import login as module

    class _Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    storage: dict[str, str] = {}
    fake_ui = _FakeLoginUi()
    observed: list[tuple[str, str]] = []

    async def load_state(_token):
        return None, True, True

    async def authenticate(_session, *, tenant_id, username, password):
        assert tenant_id > 0
        observed.append((username, password))
        return "issued-token"

    monkeypatch.setattr(
        module,
        "app",
        SimpleNamespace(storage=SimpleNamespace(user=storage)),
    )
    monkeypatch.setattr(module, "ui", fake_ui)
    monkeypatch.setattr(module, "_load_login_page_state", load_state)
    monkeypatch.setattr(module, "AsyncSessionLocal", _Session)
    monkeypatch.setattr(module, "login", authenticate)

    await module.login_page()
    fake_ui.inputs["用户名"].value = "click-user"
    fake_ui.inputs["密码"].value = "click-password"

    pending = fake_ui.buttons["登录"].handlers["click"]()
    fake_ui.inputs["用户名"].value = "later-user"
    fake_ui.inputs["密码"].value = "later-password"
    await pending

    assert observed == [("click-user", "click-password")]
    assert storage == {"token": "issued-token"}
    fake_ui.navigate.to.assert_called_once_with("/home")


async def test_login_submit_is_single_flight_across_click_and_enter(
    monkeypatch,
) -> None:
    from app.ui.pages import login as module

    class _Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    storage: dict[str, str] = {}
    fake_ui = _FakeLoginUi()
    observed: list[str] = []

    async def load_state(_token):
        return None, True, True

    async def authenticate(_session, *, tenant_id, username, password):
        assert tenant_id > 0
        assert password == "click-password"
        observed.append(username)
        return "issued-token"

    monkeypatch.setattr(
        module,
        "app",
        SimpleNamespace(storage=SimpleNamespace(user=storage)),
    )
    monkeypatch.setattr(module, "ui", fake_ui)
    monkeypatch.setattr(module, "_load_login_page_state", load_state)
    monkeypatch.setattr(module, "AsyncSessionLocal", _Session)
    monkeypatch.setattr(module, "login", authenticate)

    await module.login_page()
    fake_ui.inputs["用户名"].value = "click-user"
    fake_ui.inputs["密码"].value = "click-password"

    first = fake_ui.buttons["登录"].handlers["click"]()
    second = fake_ui.inputs["密码"].handlers["keydown.enter"]()
    try:
        assert second is None
        await first
    finally:
        if inspect.iscoroutine(first) and first.cr_frame is not None:
            first.close()
        if inspect.iscoroutine(second):
            second.close()

    assert observed == ["click-user"]
    fake_ui.navigate.to.assert_called_once_with("/home")


async def test_late_login_success_does_not_replace_a_new_session_or_finish_old_ui(
    monkeypatch,
) -> None:
    from app.ui.pages import login as module

    class _Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    storage: dict[str, str] = {}
    fake_ui = _FakeLoginUi()

    async def load_state(_token):
        return None, True, True

    async def authenticate(_session, *, tenant_id, username, password):
        assert tenant_id > 0
        assert (username, password) == ("old-user", "old-password")
        storage["token"] = "new-login-token"
        return "late-old-token"

    monkeypatch.setattr(
        module,
        "app",
        SimpleNamespace(storage=SimpleNamespace(user=storage)),
    )
    monkeypatch.setattr(module, "ui", fake_ui)
    monkeypatch.setattr(module, "_load_login_page_state", load_state)
    monkeypatch.setattr(module, "AsyncSessionLocal", _Session)
    monkeypatch.setattr(module, "login", authenticate)

    await module.login_page()
    fake_ui.inputs["用户名"].value = "old-user"
    fake_ui.inputs["密码"].value = "old-password"

    pending = fake_ui.buttons["登录"].handlers["click"]()
    await pending

    assert storage == {"token": "new-login-token"}
    fake_ui.navigate.to.assert_not_called()
    assert not any(
        kwargs.get("remove") == "loading"
        for _args, kwargs in fake_ui.buttons["登录"].prop_calls
    )


@pytest.mark.parametrize("failure_kind", ["auth", "unexpected"])
async def test_late_login_failure_does_not_write_over_a_new_session(
    monkeypatch,
    failure_kind: str,
) -> None:
    from app.ui.pages import login as module

    class _Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    storage: dict[str, str] = {}
    fake_ui = _FakeLoginUi()

    async def load_state(_token):
        return None, True, True

    async def authenticate(_session, *, tenant_id, username, password):
        assert tenant_id > 0
        assert (username, password) == ("old-user", "old-password")
        storage["token"] = "new-login-token"
        if failure_kind == "auth":
            raise module.AuthError()
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        module,
        "app",
        SimpleNamespace(storage=SimpleNamespace(user=storage)),
    )
    monkeypatch.setattr(module, "ui", fake_ui)
    monkeypatch.setattr(module, "_load_login_page_state", load_state)
    monkeypatch.setattr(module, "AsyncSessionLocal", _Session)
    monkeypatch.setattr(module, "login", authenticate)

    await module.login_page()
    error_label = fake_ui.labels[-1]
    fake_ui.inputs["用户名"].value = "old-user"
    fake_ui.inputs["密码"].value = "old-password"

    pending = fake_ui.buttons["登录"].handlers["click"]()
    await pending

    assert storage == {"token": "new-login-token"}
    assert error_label.text_calls == []
    fake_ui.navigate.to.assert_not_called()
    assert not any(
        kwargs.get("remove") == "loading"
        for _args, kwargs in fake_ui.buttons["登录"].prop_calls
    )


async def test_bound_ui_session_rejects_an_old_page_after_a_new_login(
    monkeypatch,
) -> None:
    from app.ui import auth_context as module

    now = datetime.now(timezone.utc)
    old_session = TrustedUiSession(
        session_id=uuid4(),
        tenant_id=1,
        user_id=2,
        role="teacher",
        username="teacher",
        display_name=None,
        issued_at_utc=now,
        expires_at_utc=now + timedelta(minutes=30),
    )
    new_session = TrustedUiSession(
        session_id=uuid4(),
        tenant_id=1,
        user_id=2,
        role="teacher",
        username="teacher",
        display_name=None,
        issued_at_utc=now,
        expires_at_utc=now + timedelta(minutes=30),
    )
    storage = {"token": "new-login-token"}
    navigate = Mock()
    notify = Mock()

    async def require_current(**_kwargs):
        return new_session

    monkeypatch.setattr(module, "require_current_ui_session", require_current)
    monkeypatch.setattr(
        module,
        "app",
        SimpleNamespace(storage=SimpleNamespace(user=storage)),
    )
    monkeypatch.setattr(
        module,
        "ui",
        SimpleNamespace(
            navigate=SimpleNamespace(to=navigate),
            notify=notify,
        ),
    )

    current = await module.require_bound_ui_session(old_session)

    assert current is None
    assert storage == {"token": "new-login-token"}
    notify.assert_called_once()
    navigate.assert_called_once_with("/home")
