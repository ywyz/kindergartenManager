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
