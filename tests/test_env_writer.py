"""测试 app.core.env_writer 模块。

覆盖：
- read_dot_env()：文件不存在返回 {}；解析 key=value；忽略注释和空行
- write_dot_env()：创建文件；更新已有 key；保留其他 key；异常时抛出 RuntimeError
"""
from pathlib import Path
from unittest.mock import patch

import pytest


class TestReadDotEnv:
    def test_returns_empty_dict_when_file_absent(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            from app.core.env_writer import read_dot_env
            assert read_dot_env() == {}

    def test_parses_key_value_pairs(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("DATABASE_URL=sqlite:///./db.db\nPORT=8080\n")
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            from app.core.env_writer import read_dot_env
            result = read_dot_env()
        assert result["DATABASE_URL"] == "sqlite:///./db.db"
        assert result["PORT"] == "8080"

    def test_ignores_comment_lines(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("# This is a comment\nFOO=bar\n")
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            from app.core.env_writer import read_dot_env
            result = read_dot_env()
        assert "FOO" in result
        assert len(result) == 1

    def test_ignores_blank_lines(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("\nFOO=bar\n\nBAZ=qux\n")
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            from app.core.env_writer import read_dot_env
            result = read_dot_env()
        assert result == {"FOO": "bar", "BAZ": "qux"}

    def test_value_with_equals_sign(self, tmp_path: Path) -> None:
        """值中包含 = 时，仅在第一个 = 处分割。"""
        env_file = tmp_path / ".env"
        env_file.write_text("URL=mysql://user:pass@host/db?option=1\n")
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            from app.core.env_writer import read_dot_env
            result = read_dot_env()
        assert result["URL"] == "mysql://user:pass@host/db?option=1"


class TestWriteDotEnv:
    def test_creates_file_when_absent(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            from app.core.env_writer import write_dot_env
            write_dot_env({"PORT": "9090"})
        assert env_file.exists()
        assert "PORT=9090" in env_file.read_text()

    def test_updates_existing_key(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8080\n")
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            from app.core.env_writer import write_dot_env
            write_dot_env({"PORT": "9090"})
        assert "PORT=9090" in env_file.read_text()
        assert "PORT=8080" not in env_file.read_text()

    def test_preserves_other_keys(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("DATABASE_URL=sqlite:///./db.db\nPORT=8080\n")
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            from app.core.env_writer import write_dot_env
            write_dot_env({"PORT": "9090"})
        content = env_file.read_text()
        assert "DATABASE_URL=sqlite:///./db.db" in content
        assert "PORT=9090" in content

    def test_adds_new_key(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8080\n")
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            from app.core.env_writer import write_dot_env
            write_dot_env({"DATABASE_URL": "sqlite:///./new.db"})
        content = env_file.read_text()
        assert "DATABASE_URL=sqlite:///./new.db" in content
        assert "PORT=8080" in content

    def test_raises_runtime_error_on_write_failure(self, tmp_path: Path) -> None:
        env_file = tmp_path / "no_such_dir" / ".env"
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            from app.core.env_writer import write_dot_env
            with pytest.raises(RuntimeError, match="无法写入配置文件"):
                write_dot_env({"PORT": "9090"})
