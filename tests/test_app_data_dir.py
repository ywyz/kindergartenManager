"""测试应用数据目录解析策略。"""

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
