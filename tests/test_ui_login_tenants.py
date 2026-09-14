"""Only explicitly configured tenants can enter the ordinary UI login flow."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.ui.pages import login as module
from tests.test_ui_auth_context import _FakeLoginUi


@pytest.mark.parametrize(
    "configured,requested", [("", 11), ("11", 12), ("11, x", 1), ("0", 1)]
)
def test_unknown_or_malformed_tenant_fails_closed(monkeypatch, configured, requested):
    monkeypatch.setattr(module.settings, "UI_LOGIN_TENANT_IDS", configured)
    with pytest.raises(HTTPException):
        module._login_tenant(requested)


async def test_explicit_tenant_reaches_authentication_unchanged(monkeypatch):
    monkeypatch.setattr(module.settings, "UI_LOGIN_TENANT_IDS", "11")
    assert module._login_tenant(None) == module.settings.BOOTSTRAP_ADMIN_TENANT_ID
    ui = _FakeLoginUi()
    storage = {}
    observed = []

    class Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *args):
            return False

    async def state(token, *, tenant_id):
        observed.append(("state", tenant_id))
        return None, True, True

    async def authenticate(session, *, tenant_id, username, password):
        observed.append(("login", tenant_id, username, password))
        return "test-token"

    monkeypatch.setattr(module, "ui", ui)
    monkeypatch.setattr(
        module, "app", SimpleNamespace(storage=SimpleNamespace(user=storage))
    )
    monkeypatch.setattr(module, "_load_login_page_state", state)
    monkeypatch.setattr(module, "AsyncSessionLocal", Session)
    monkeypatch.setattr(module, "login", authenticate)
    await module.login_page(tenant_id=11)
    ui.inputs["用户名"].value = "synthetic3"
    ui.inputs["密码"].value = "test-password"
    await ui.buttons["登录"].handlers["click"]()
    assert observed == [("state", 11), ("login", 11, "synthetic3", "test-password")]
    assert storage == {"token": "test-token"}
