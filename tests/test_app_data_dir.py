"""测试应用数据目录解析策略。"""

import os
import sqlite3
import stat
from pathlib import Path

import pytest

from app.core import config as config_module
from app.core import env_writer
from app.core import paths
from app.core import startup
from app.core.paths import app_data_dir


def test_explicit_data_dir_is_required_to_be_absolute(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("KINDERGARTEN_DATA_DIR", "relative/kg")
    # 相对路径会被拒绝（fail-closed）
    monkeypatch.setattr(paths.sys, "frozen", False, raising=False)
    with pytest.raises(ValueError, match="KINDERGARTEN_DATA_DIR"):
        app_data_dir()


def test_explicit_absolute_data_dir_routes_runtime_files(
    monkeypatch, tmp_path: Path
) -> None:
    data_dir = tmp_path / "kg-data"
    monkeypatch.setenv("KINDERGARTEN_DATA_DIR", str(data_dir))
    monkeypatch.setattr(paths.sys, "frozen", False, raising=False)

    assert app_data_dir() == data_dir
    assert data_dir.exists()
    assert (
        startup.build_sync_url("")
        == f"sqlite:///{(data_dir / 'kindergarten.db').as_posix()}"
    )
    assert env_writer.get_env_path() == data_dir / ".env"
    assert config_module._secrets_file_path() == data_dir / ".kindergarten_secrets"


def test_explicit_absolute_data_dir_is_used_in_frozen_mode(
    monkeypatch, tmp_path: Path
) -> None:
    data_dir = tmp_path / "kg-data-frozen"
    monkeypatch.setenv("KINDERGARTEN_DATA_DIR", str(data_dir))
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)

    assert app_data_dir() == data_dir


def test_permission_error_creating_data_dir_is_not_swallowed(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("KINDERGARTEN_DATA_DIR", str(tmp_path / "kg-noperms"))

    def _permission_denied(*_args, **_kwargs) -> None:
        raise PermissionError("denied")

    with pytest.raises(PermissionError, match="denied"):
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(paths.Path, "mkdir", _permission_denied)
            app_data_dir()


def test_existing_posix_data_dir_is_private_before_runtime_files(
    monkeypatch, tmp_path: Path
) -> None:
    """已有 0755 数据目录不得在运行文件访问前保持对外可读。"""
    if os.name != "posix":
        pytest.skip("POSIX directory permission contract")

    data_dir = tmp_path / "insecure-existing-data"
    data_dir.mkdir(mode=0o755)
    data_dir.chmod(0o755)
    monkeypatch.setenv("KINDERGARTEN_DATA_DIR", str(data_dir))

    try:
        resolved = app_data_dir()
    except (OSError, RuntimeError, ValueError):
        # Fail-closed is valid: no runtime file may be created or read after rejection.
        assert not (data_dir / ".env").exists()
        assert not (data_dir / "kindergarten.db").exists()
        return

    assert resolved == data_dir
    assert stat.S_IMODE(data_dir.stat().st_mode) == 0o700

    # Only after the directory is private may runtime writers/readers touch .env/SQLite.
    env_writer.write_dot_env({"PATH_SECURITY_SENTINEL": "owner-only"})
    database_path = data_dir / "kindergarten.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE path_security_probe (value TEXT)")

    assert env_writer.read_dot_env()["PATH_SECURITY_SENTINEL"] == "owner-only"
    assert startup.build_sync_url("") == (f"sqlite:///{database_path.as_posix()}")

    directory_mode = stat.S_IMODE(data_dir.stat().st_mode)
    assert not directory_mode & 0o077
    for runtime_file in (data_dir / ".env", database_path):
        file_mode = stat.S_IMODE(runtime_file.stat().st_mode)
        # Effective group/other readability is impossible through an owner-only directory.
        assert not (directory_mode & 0o077 and file_mode & 0o044)


def test_explicit_posix_data_dir_rejects_symlink(monkeypatch, tmp_path: Path) -> None:
    """显式数据目录的末级路径不得通过 symlink 绕过目录身份检查。"""
    if os.name != "posix":
        pytest.skip("POSIX symlink contract")

    target = tmp_path / "real-data"
    target.mkdir(mode=0o700)
    linked = tmp_path / "linked-data"
    linked.symlink_to(target, target_is_directory=True)
    monkeypatch.setenv("KINDERGARTEN_DATA_DIR", str(linked))

    with pytest.raises((OSError, RuntimeError, ValueError)):
        app_data_dir()


def test_explicit_posix_data_dir_rejects_foreign_owner(
    monkeypatch, tmp_path: Path
) -> None:
    """应用不得在非当前有效用户拥有的数据目录中落盘敏感文件。"""
    if os.name != "posix":
        pytest.skip("POSIX ownership contract")

    data_dir = tmp_path / "foreign-data"
    data_dir.mkdir(mode=0o700)
    monkeypatch.setenv("KINDERGARTEN_DATA_DIR", str(data_dir))
    monkeypatch.setattr(paths.os, "geteuid", lambda: data_dir.stat().st_uid + 1)

    with pytest.raises((OSError, RuntimeError, ValueError)):
        app_data_dir()


def test_posix_env_file_is_private_and_rejects_symlink(
    monkeypatch, tmp_path: Path
) -> None:
    """设置页持久化的明文连接配置必须是 owner-only 且不跟随 symlink。"""
    if os.name != "posix":
        pytest.skip("POSIX file permission contract")

    data_dir = tmp_path / "secure-env-data"
    monkeypatch.setenv("KINDERGARTEN_DATA_DIR", str(data_dir))
    env_writer.write_dot_env({"PORT": "49173"})
    env_path = data_dir / ".env"

    assert stat.S_IMODE(env_path.stat().st_mode) == 0o600

    env_path.unlink()
    victim = tmp_path / "must-not-change"
    victim.write_text("sentinel\n", encoding="utf-8")
    env_path.symlink_to(victim)

    with pytest.raises(RuntimeError):
        env_writer.write_dot_env({"PORT": "49174"})
    assert victim.read_text(encoding="utf-8") == "sentinel\n"
