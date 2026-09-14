"""Focused safety checks for the cloud weekly-plan fixture initializer."""

import asyncio
import json
import stat
from types import SimpleNamespace

import pytest

from scripts import weekly_cloud_fixture as fixture


def test_database_url_is_bound_to_dedicated_mysql_target():
    parsed = fixture._database_url(
        "mysql+aiomysql://fixture:secret@bwh.example:3306/wp_cloud_20260914",
        production=False,
    )
    assert parsed.database == fixture.TARGET_DATABASE

    with pytest.raises(fixture.FixtureRejected, match="mysql_required"):
        fixture._database_url(
            "sqlite+aiosqlite:////tmp/wp_cloud_20260914.db", production=False
        )
    with pytest.raises(fixture.FixtureRejected, match="dedicated_database_required"):
        fixture._database_url(
            "mysql+aiomysql://fixture:secret@bwh.example:3306/kindergarten_db",
            production=False,
        )
    with pytest.raises(
        fixture.FixtureRejected, match="production_database_must_be_explicit"
    ):
        fixture._database_url(
            "mysql+aiomysql://fixture:secret@bwh.example:3306/wp_cloud_20260914",
            production=True,
        )


def test_password_file_requires_owner_only_and_never_returns_a_trimmed_secret(tmp_path):
    password_path = tmp_path / "fixture-password"
    password_path.write_text("中文Fixture-9!\n", encoding="utf-8")
    password_path.chmod(0o600)
    assert fixture._read_owner_password(password_path) == "中文Fixture-9!"

    password_path.chmod(0o640)
    with pytest.raises(fixture.FixtureRejected, match="owner_only"):
        fixture._read_owner_password(password_path)


def test_receipt_rejects_body_hash_and_secret_fields(tmp_path):
    receipt = {
        "schema": fixture.SCHEMA,
        "tenant_id": fixture.CLOUD_TENANT_ID,
        "plans": [{"plan_id": 1, "columns": 5}],
    }
    output = tmp_path / "receipt.json"
    path = fixture._write_receipt(output, receipt, "secret-value")
    assert path == output
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert json.loads(output.read_text(encoding="utf-8")) == receipt

    with pytest.raises(fixture.FixtureRejected, match="receipt_path_exists"):
        fixture._write_receipt(output, receipt, "secret-value")
    with pytest.raises(fixture.FixtureRejected, match="receipt_not_body_free"):
        fixture._body_free_receipt({"body_json": "content"}, "secret-value")
    with pytest.raises(fixture.FixtureRejected, match="receipt_not_body_free"):
        fixture._body_free_receipt({"payload_sha256": "abc"}, "secret-value")
    with pytest.raises(fixture.FixtureRejected, match="receipt_contains_secret"):
        fixture._body_free_receipt({"note": "secret-value"}, "secret-value")


class _FakeResult:
    def __init__(self, *, versions=(), first=None):
        self._versions = versions
        self._first = first

    def scalars(self):
        return iter(self._versions)

    def first(self):
        return self._first


class _FakeConnection:
    dialect = SimpleNamespace(name="mysql")

    async def run_sync(self, callback):
        return callback(object())

    async def execute(self, statement, _parameters=None):
        if "version_num" in str(statement):
            return _FakeResult(versions=(fixture.EXPECTED_ALEMBIC_HEAD,))
        return _FakeResult(first=None)


class _FakeConnectContext:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, *_args):
        return None


class _FakeEngine:
    def __init__(self):
        self.connection = _FakeConnection()

    def connect(self):
        return _FakeConnectContext(self.connection)


def _preflight_with_counts(monkeypatch, counts, *, production=False):
    seen = []

    monkeypatch.setattr(
        fixture,
        "_table_names",
        lambda _sync_connection: set(fixture.REQUIRED_TABLES)
        | fixture.MIGRATION_REFERENCE_SEED_TABLES,
    )

    async def count_rows(_connection, table, tenant_id):
        seen.append((table.name, tenant_id))
        return counts.get(table.name, 0)

    monkeypatch.setattr(fixture, "_count_rows", count_rows)
    asyncio.run(
        fixture._preflight_database(
            _FakeEngine(), tenant_id=fixture.CLOUD_TENANT_ID, production=production
        )
    )
    return seen


def test_default_preflight_allows_only_the_migration_reference_seed(
    monkeypatch,
):
    seen = _preflight_with_counts(
        monkeypatch,
        {"indicator_catalog": 30},
    )

    assert "indicator_catalog" not in {name for name, _tenant_id in seen}


def test_default_preflight_rejects_existing_business_rows(monkeypatch):
    with pytest.raises(fixture.FixtureRejected, match="dedicated_database_not_empty"):
        _preflight_with_counts(monkeypatch, {"daily_plan": 1})


def test_production_preflight_does_not_allow_reference_seed_rows(monkeypatch):
    with pytest.raises(fixture.FixtureRejected, match="production_tenant_not_empty"):
        _preflight_with_counts(
            monkeypatch,
            {"indicator_catalog": 1},
            production=True,
        )


def test_seed_disposes_engine_when_preflight_fails(monkeypatch):
    class DisposableEngine:
        disposed = False

        async def dispose(self):
            self.disposed = True

    async def fail_preflight(*_args, **_kwargs):
        raise fixture.FixtureRejected("dedicated_database_not_empty")

    engine = DisposableEngine()
    monkeypatch.setattr(fixture, "_preflight_database", fail_preflight)
    with pytest.raises(fixture.FixtureRejected, match="dedicated_database_not_empty"):
        asyncio.run(
            fixture._seed(
                engine,
                tenant_id=fixture.CLOUD_TENANT_ID,
                password="synthetic-only",
                production=False,
            )
        )
    assert engine.disposed is True


def test_production_mode_requires_explicit_tenant_before_database_access(
    monkeypatch, tmp_path
):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    result = fixture.main(
        [
            "seed",
            "--password-file",
            str(tmp_path / "missing"),
            "--receipt-output",
            str(tmp_path / "receipt.json"),
            "--allow-production-synthetic",
        ]
    )
    assert result == 2
