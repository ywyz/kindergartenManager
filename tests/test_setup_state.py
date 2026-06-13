"""测试 app.core.setup_state 模块。

覆盖：
- is_setup_complete()：标记文件不存在返回 False，存在返回 True
- mark_setup_complete()：创建标记文件
- 边界：写入权限异常时静默忽略，不抛出
"""
from pathlib import Path
from unittest.mock import patch

import pytest


class TestIsSetupComplete:
    def test_returns_false_when_file_absent(self, tmp_path: Path) -> None:
        state_file = tmp_path / ".kindergarten_setup_complete"
        with patch("app.core.setup_state._get_state_path", return_value=state_file):
            from app.core.setup_state import is_setup_complete
            assert is_setup_complete() is False

    def test_returns_true_when_file_present(self, tmp_path: Path) -> None:
        state_file = tmp_path / ".kindergarten_setup_complete"
        state_file.touch()
        with patch("app.core.setup_state._get_state_path", return_value=state_file):
            from app.core.setup_state import is_setup_complete
            assert is_setup_complete() is True


class TestMarkSetupComplete:
    def test_creates_marker_file(self, tmp_path: Path) -> None:
        state_file = tmp_path / ".kindergarten_setup_complete"
        with patch("app.core.setup_state._get_state_path", return_value=state_file):
            from app.core.setup_state import mark_setup_complete
            assert not state_file.exists()
            mark_setup_complete()
            assert state_file.exists()

    def test_is_idempotent(self, tmp_path: Path) -> None:
        state_file = tmp_path / ".kindergarten_setup_complete"
        with patch("app.core.setup_state._get_state_path", return_value=state_file):
            from app.core.setup_state import mark_setup_complete
            mark_setup_complete()
            mark_setup_complete()  # 不应抛出
            assert state_file.exists()

    def test_silently_ignores_os_error(self, tmp_path: Path) -> None:
        """写入失败时静默忽略，不向调用方抛出异常。"""
        state_file = tmp_path / "nonexistent_dir" / ".kindergarten_setup_complete"
        with patch("app.core.setup_state._get_state_path", return_value=state_file):
            from app.core.setup_state import mark_setup_complete
            mark_setup_complete()  # 目录不存在，touch() 会失败，但不应抛出


class TestRoundTrip:
    def test_mark_then_check(self, tmp_path: Path) -> None:
        state_file = tmp_path / ".kindergarten_setup_complete"
        with patch("app.core.setup_state._get_state_path", return_value=state_file):
            from app.core.setup_state import is_setup_complete, mark_setup_complete
            assert not is_setup_complete()
            mark_setup_complete()
            assert is_setup_complete()
