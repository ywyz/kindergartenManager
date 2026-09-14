"""Focused safety checks for the cloud weekly-plan fixture initializer."""

import inspect
import json
import stat

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


def test_fixture_seed_has_no_schema_creation_or_export_boundary():
    source = inspect.getsource(fixture._seed)
    assert "alembic" not in source.lower()
    assert "create_all" not in source
    assert "export_saved" not in source


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
