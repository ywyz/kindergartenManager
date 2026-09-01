"""对外 REST API 路由集成测试（httpx ASGITransport + SQLite 内存库）。"""
import asyncio
import hashlib
import hmac
import time
from datetime import date

import pytest_asyncio
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import create_api_router
from app.api.deps import get_db
from app.core.config import settings
from app.core.models.class_config import ClassConfig
from app.core.models.daily_plan import DailyPlan
from app.core.models.semester import SemesterConfig

API_KEY = "testkey"
TENANT = 1
OTHER_TENANT = 2


@pytest_asyncio.fixture
async def api_client(async_session, monkeypatch):
    monkeypatch.setattr(settings, "API_KEYS", f"{API_KEY}:{TENANT}")
    monkeypatch.setattr(settings, "API_SIGNING_SECRET", "")

    fastapi_app = FastAPI()
    fastapi_app.include_router(create_api_router())

    async def _override_db():
        yield async_session

    fastapi_app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _seed(session):
    # 本租户两条计划 + 另一租户一条计划
    session.add_all(
        [
            DailyPlan(
                tenant_id=TENANT, user_id=11, plan_date=date(2026, 3, 2),
                week_number=1, weekday_cn="周一", grade="小班", class_name="阳光班",
                activity_goal="目标A",
            ),
            DailyPlan(
                tenant_id=TENANT, user_id=12, plan_date=date(2026, 3, 9),
                week_number=2, weekday_cn="周一", grade="中班", class_name="星星班",
                activity_goal="目标B",
            ),
            DailyPlan(
                tenant_id=OTHER_TENANT, user_id=99, plan_date=date(2026, 3, 2),
                week_number=1, weekday_cn="周一", grade="大班", class_name="月亮班",
            ),
        ]
    )
    session.add(
        SemesterConfig(
            tenant_id=TENANT, user_id=11, semester_name="2026春季",
            start_date=date(2026, 2, 23), end_date=date(2026, 7, 1), is_active=True,
        )
    )
    session.add(
        SemesterConfig(
            tenant_id=OTHER_TENANT, user_id=99, semester_name="其它租户学期",
            start_date=date(2026, 2, 23), end_date=date(2026, 7, 1), is_active=True,
        )
    )
    session.add(
        ClassConfig(
            tenant_id=TENANT, user_id=11, grade="小班", class_name="阳光班",
            indoor_areas="积木区", outdoor_content="攀爬",
        )
    )
    session.add(
        ClassConfig(
            tenant_id=OTHER_TENANT, user_id=99, grade="大班", class_name="其它租户班级",
        )
    )
    await session.flush()


class TestAuth:
    async def test_health_no_auth(self, api_client):
        resp = await api_client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_health_never_opens_a_database_session(self, api_client, monkeypatch):
        from app.api import routes

        def forbidden_session():
            raise AssertionError("liveness must not touch the database")

        monkeypatch.setattr(routes, "AsyncSessionLocal", forbidden_session)

        resp = await api_client.get("/api/v1/health")

        assert resp.status_code == 200


class _ReadinessSession:
    def __init__(self, *, error: Exception | None = None, block: bool = False) -> None:
        self.error = error
        self.block = block
        self.statements: list[str] = []
        self.entered = False
        self.exited = False
        self.cancelled = False
        self.commit_calls = 0
        self.flush_calls = 0

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, *_args: object) -> None:
        self.exited = True

    async def execute(self, statement: object) -> object:
        self.statements.append(str(statement))
        if self.error is not None:
            raise self.error
        if self.block:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled = True
                raise
        return object()

    async def commit(self) -> None:
        self.commit_calls += 1
        raise AssertionError("readiness must not commit")

    async def flush(self) -> None:
        self.flush_calls += 1
        raise AssertionError("readiness must not flush")


class _ReadinessFactory:
    def __init__(self, sessions: list[_ReadinessSession]) -> None:
        self.pending = list(sessions)
        self.created: list[_ReadinessSession] = []

    def __call__(self) -> _ReadinessSession:
        session = self.pending.pop(0)
        self.created.append(session)
        return session


class TestReadiness:
    async def test_readiness_is_unauthenticated_and_executes_only_select_one(
        self, api_client, monkeypatch
    ) -> None:
        from app.api import routes

        session = _ReadinessSession()
        monkeypatch.setattr(routes, "AsyncSessionLocal", _ReadinessFactory([session]))

        response = await api_client.get("/api/v1/readiness")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ready",
            "service": "kindergarten-teaching-api",
            "version": "v1",
            "time": response.json()["time"],
            "checks": {"database": "ok"},
        }
        assert session.entered and session.exited
        assert session.statements == ["SELECT 1"]
        assert session.commit_calls == session.flush_calls == 0

    @pytest.mark.parametrize(
        "failure",
        [
            RuntimeError("connection refused at mysql://secret-user:secret-pass@db"),
            ValueError("SELECT 1 failed with api-key=secret-key tenant=77 user=88"),
        ],
    )
    async def test_readiness_failure_is_503_and_redacted(
        self, api_client, monkeypatch, caplog, failure
    ) -> None:
        from app.api import routes

        session = _ReadinessSession(error=failure)
        monkeypatch.setattr(routes, "AsyncSessionLocal", _ReadinessFactory([session]))

        response = await api_client.get("/api/v1/readiness")

        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"
        assert response.json()["checks"] == {"database": "failed"}
        exposed = response.text + caplog.text
        for secret in ("secret-user", "secret-pass", "secret-key", "tenant=77", "user=88", "SELECT 1"):
            assert secret not in exposed

    async def test_readiness_timeout_cancels_query_and_closes_session(
        self, api_client, monkeypatch
    ) -> None:
        from app.api import routes

        session = _ReadinessSession(block=True)
        monkeypatch.setattr(routes, "AsyncSessionLocal", _ReadinessFactory([session]))
        monkeypatch.setattr(routes, "READINESS_TIMEOUT_SECONDS", 0.01)

        response = await api_client.get("/api/v1/readiness")

        assert response.status_code == 503
        assert session.cancelled
        assert session.exited

    async def test_host_cancellation_propagates(self, monkeypatch) -> None:
        from app.api import routes

        session = _ReadinessSession(block=True)
        monkeypatch.setattr(routes, "AsyncSessionLocal", _ReadinessFactory([session]))
        task = asyncio.create_task(routes.readiness())
        await asyncio.sleep(0)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task
        assert session.cancelled
        assert session.exited

    async def test_database_recovery_uses_a_new_session_without_app_restart(
        self, api_client, monkeypatch
    ) -> None:
        from app.api import routes

        failed = _ReadinessSession(error=ConnectionError("synthetic disconnect"))
        recovered = _ReadinessSession()
        factory = _ReadinessFactory([failed, recovered])
        monkeypatch.setattr(routes, "AsyncSessionLocal", factory)

        first = await api_client.get("/api/v1/readiness")
        second = await api_client.get("/api/v1/readiness")

        assert first.status_code == 503
        assert second.status_code == 200
        assert factory.created == [failed, recovered]

    async def test_concurrent_readiness_requests_use_independent_sessions(
        self, api_client, monkeypatch
    ) -> None:
        from app.api import routes

        first = _ReadinessSession()
        second = _ReadinessSession()
        factory = _ReadinessFactory([first, second])
        monkeypatch.setattr(routes, "AsyncSessionLocal", factory)

        responses = await asyncio.gather(
            api_client.get("/api/v1/readiness"),
            api_client.get("/api/v1/readiness"),
        )

        assert [response.status_code for response in responses] == [200, 200]
        assert factory.created == [first, second]


class TestApiKeyAuth:
    async def test_missing_api_key_rejected(self, api_client):
        resp = await api_client.get("/api/v1/daily-plans")
        assert resp.status_code == 401

    async def test_invalid_api_key_rejected(self, api_client):
        resp = await api_client.get(
            "/api/v1/daily-plans", headers={"X-Api-Key": "wrong"}
        )
        assert resp.status_code == 401

    async def test_valid_api_key_accepted(self, api_client):
        resp = await api_client.get(
            "/api/v1/daily-plans", headers={"X-Api-Key": API_KEY}
        )
        assert resp.status_code == 200


class TestDailyPlans:
    async def test_list_returns_only_own_tenant(self, api_client, async_session):
        await _seed(async_session)
        resp = await api_client.get(
            "/api/v1/daily-plans", headers={"X-Api-Key": API_KEY}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 2
        tenants = {item["tenant_id"] for item in body["items"]}
        assert tenants == {TENANT}

    async def test_tenant_projection_includes_multiple_users(self, api_client, async_session):
        """API Key 代表 tenant；不传 user 过滤时可读本 tenant 内多个教师。"""
        await _seed(async_session)
        resp = await api_client.get(
            "/api/v1/daily-plans", headers={"X-Api-Key": API_KEY}
        )

        assert {item["user_id"] for item in resp.json()["items"]} == {11, 12}

    async def test_filter_by_grade(self, api_client, async_session):
        await _seed(async_session)
        resp = await api_client.get(
            "/api/v1/daily-plans",
            params={"grade": "中班"},
            headers={"X-Api-Key": API_KEY},
        )
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["grade"] == "中班"

    async def test_filter_by_date_range(self, api_client, async_session):
        await _seed(async_session)
        resp = await api_client.get(
            "/api/v1/daily-plans",
            params={"start_date": "2026-03-05", "end_date": "2026-03-31"},
            headers={"X-Api-Key": API_KEY},
        )
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["plan_date"] == "2026-03-09"

    async def test_pagination(self, api_client, async_session):
        await _seed(async_session)
        resp = await api_client.get(
            "/api/v1/daily-plans",
            params={"limit": 1, "offset": 0},
            headers={"X-Api-Key": API_KEY},
        )
        body = resp.json()
        assert body["meta"]["total"] == 2
        assert len(body["items"]) == 1

    async def test_get_by_id(self, api_client, async_session):
        await _seed(async_session)
        list_resp = await api_client.get(
            "/api/v1/daily-plans", headers={"X-Api-Key": API_KEY}
        )
        plan_id = list_resp.json()["items"][0]["id"]
        resp = await api_client.get(
            f"/api/v1/daily-plans/{plan_id}", headers={"X-Api-Key": API_KEY}
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == plan_id

    async def test_get_by_id_cross_tenant_404(self, api_client, async_session):
        await _seed(async_session)
        # 取另一租户记录的 id
        from sqlalchemy import select

        other = (
            await async_session.execute(
                select(DailyPlan).where(DailyPlan.tenant_id == OTHER_TENANT)
            )
        ).scalar_one()
        resp = await api_client.get(
            f"/api/v1/daily-plans/{other.id}", headers={"X-Api-Key": API_KEY}
        )
        assert resp.status_code == 404

    async def test_get_by_id_not_found(self, api_client, async_session):
        await _seed(async_session)
        resp = await api_client.get(
            "/api/v1/daily-plans/999999", headers={"X-Api-Key": API_KEY}
        )
        assert resp.status_code == 404


class TestConfigEndpoints:
    async def test_semesters(self, api_client, async_session):
        await _seed(async_session)
        resp = await api_client.get(
            "/api/v1/semesters", headers={"X-Api-Key": API_KEY}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["semester_name"] == "2026春季"
        assert {item["tenant_id"] for item in data} == {TENANT}

    async def test_classes(self, api_client, async_session):
        await _seed(async_session)
        resp = await api_client.get(
            "/api/v1/classes", headers={"X-Api-Key": API_KEY}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["class_name"] == "阳光班"
        assert {item["tenant_id"] for item in data} == {TENANT}


class TestSignature:
    @pytest_asyncio.fixture
    async def signed_client(self, async_session, monkeypatch):
        monkeypatch.setattr(settings, "API_KEYS", f"{API_KEY}:{TENANT}")
        monkeypatch.setattr(settings, "API_SIGNING_SECRET", "topsecret")
        monkeypatch.setattr(settings, "API_SIGNATURE_MAX_SKEW", 300)

        fastapi_app = FastAPI()
        fastapi_app.include_router(create_api_router())

        async def _override_db():
            yield async_session

        fastapi_app.dependency_overrides[get_db] = _override_db
        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    def _sign(self, ts, method, path, query):
        msg = f"{ts}\n{method}\n{path}\n{query}"
        return hmac.new(b"topsecret", msg.encode(), hashlib.sha256).hexdigest()

    async def test_missing_signature_rejected(self, signed_client):
        resp = await signed_client.get(
            "/api/v1/classes", headers={"X-Api-Key": API_KEY}
        )
        assert resp.status_code == 401

    async def test_valid_signature_accepted(self, signed_client, async_session):
        await _seed(async_session)
        ts = str(int(time.time()))
        sig = self._sign(ts, "GET", "/api/v1/classes", "")
        resp = await signed_client.get(
            "/api/v1/classes",
            headers={
                "X-Api-Key": API_KEY,
                "X-Timestamp": ts,
                "X-Signature": sig,
            },
        )
        assert resp.status_code == 200

    async def test_tampered_signature_rejected(self, signed_client):
        ts = str(int(time.time()))
        resp = await signed_client.get(
            "/api/v1/classes",
            headers={
                "X-Api-Key": API_KEY,
                "X-Timestamp": ts,
                "X-Signature": "deadbeef",
            },
        )
        assert resp.status_code == 401
