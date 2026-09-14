"""Regression tests for scripts/render_environment.py."""

import asyncio
import importlib.util
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from app.service.shared_weekly.layout_contracts import FONT_FAMILY

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_environment.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("render_environment", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["render_environment"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def render_env():
    return _load_script()


def _seed(tmp_path, content: bytes):
    path = tmp_path / "weekplan.docx"
    path.write_bytes(content)
    return path, sha256(content).hexdigest()


def _patch(render_env, monkeypatch, tmp_path, *, font: str, seed_content: bytes):
    path, digest = _seed(tmp_path, seed_content)
    monkeypatch.setattr(render_env, "SEED_PATH", path)
    monkeypatch.setattr(render_env, "SEED_SHA256", digest)

    async def fake_run(name: str, args: list[str]) -> str:
        if name == "fc-match":
            return str(path) if "%{file}" in args else font
        return f"{name} version 1.2.3"

    async def fake_dpkg(package: str) -> str:
        return "1.0-1"

    monkeypatch.setattr(render_env, "_run", fake_run)
    monkeypatch.setattr(render_env, "_dpkg_version", fake_dpkg)


def test_ok_report_passes(render_env, monkeypatch, tmp_path):
    _patch(render_env, monkeypatch, tmp_path, font=FONT_FAMILY, seed_content=b"seed")
    report, errors = asyncio.run(render_env.verify())
    assert not errors
    assert report["font_ok"] is True
    assert report["seed_sha256_ok"] is True
    assert report["packages"]["fonts-noto-cjk"] == "1.0-1"


def test_missing_font_family_fails(render_env, monkeypatch, tmp_path):
    _patch(render_env, monkeypatch, tmp_path, font="DejaVu Sans", seed_content=b"seed")
    report, errors = asyncio.run(render_env.verify())
    assert errors
    assert report["font_ok"] is False
    assert any("font family mismatch" in e for e in errors)


def test_missing_seed_file_fails(render_env, monkeypatch, tmp_path):
    _patch(render_env, monkeypatch, tmp_path, font=FONT_FAMILY, seed_content=b"seed")
    monkeypatch.setattr(render_env, "SEED_PATH", tmp_path / "missing.docx")
    report, errors = asyncio.run(render_env.verify())
    assert errors
    assert report["seed_sha256_ok"] is False
    assert any("seed file missing" in e for e in errors)


def test_seed_sha_mismatch_fails(render_env, monkeypatch, tmp_path):
    _patch(render_env, monkeypatch, tmp_path, font=FONT_FAMILY, seed_content=b"seed")
    monkeypatch.setattr(render_env, "SEED_SHA256", "0" * 64)
    report, errors = asyncio.run(render_env.verify())
    assert errors
    assert report["seed_sha256_ok"] is False


def test_missing_package_fails(render_env, monkeypatch, tmp_path):
    _patch(render_env, monkeypatch, tmp_path, font=FONT_FAMILY, seed_content=b"seed")

    async def missing_dpkg(package: str) -> str | None:
        return None

    monkeypatch.setattr(render_env, "_dpkg_version", missing_dpkg)
    _report, errors = asyncio.run(render_env.verify())
    assert errors
    assert any("package missing" in e for e in errors)


def test_missing_tool_fails(render_env, monkeypatch, tmp_path):
    _patch(render_env, monkeypatch, tmp_path, font=FONT_FAMILY, seed_content=b"seed")

    async def failing_run(name: str, args: list[str]) -> str:
        raise RuntimeError("not found")

    monkeypatch.setattr(render_env, "_run", failing_run)
    report, errors = asyncio.run(render_env.verify())
    assert errors
    assert report["tools"]["libreoffice"] is None
    assert any("libreoffice" in e for e in errors)


async def test_tool_error_with_output_fails(render_env):
    with pytest.raises(RuntimeError, match="exited 3"):
        await render_env._run(
            sys.executable, ["-c", "print('error'); raise SystemExit(3)"]
        )
