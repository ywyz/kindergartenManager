"""tests/test_settings_database.py — 数据库配置区域功能测试。

验证：
- write_dot_env 正确写入 DATABASE_URL
- MySQL 字段组装为正确的连接字符串格式
- SQLite 模式清空 DATABASE_URL
- 端口配置保存
"""
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.env_writer import read_dot_env, write_dot_env


class TestDatabaseConfigSave:
    def test_mysql_url_assembled_correctly(self, tmp_path: Path):
        """MySQL 独立字段应被组装为 mysql+aiomysql:// 格式写入 .env。"""
        env_file = tmp_path / ".env"
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            # 模拟用户填写的字段组装
            host = "192.168.1.100"
            port = "3306"
            user = "root"
            password = "mypass"
            dbname = "kindergarten"
            url = f"mysql+aiomysql://{user}:{password}@{host}:{port}/{dbname}"

            write_dot_env({"DATABASE_URL": url})

            result = read_dot_env()
            assert result["DATABASE_URL"] == "mysql+aiomysql://root:mypass@192.168.1.100:3306/kindergarten"

    def test_sqlite_mode_clears_database_url(self, tmp_path: Path):
        """切换到 SQLite 时，DATABASE_URL 应为空（触发 config.py 的 fallback）。"""
        env_file = tmp_path / ".env"
        env_file.write_text("DATABASE_URL=mysql+aiomysql://old:old@host/db\n")
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            write_dot_env({"DATABASE_URL": ""})
            result = read_dot_env()
            assert result.get("DATABASE_URL") == ""

    def test_port_config_save(self, tmp_path: Path):
        """端口配置写入 .env 的 PORT 字段。"""
        env_file = tmp_path / ".env"
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            write_dot_env({"PORT": "9090"})
            result = read_dot_env()
            assert result["PORT"] == "9090"

    def test_preserves_existing_keys(self, tmp_path: Path):
        """更新 DATABASE_URL 时不丢失已有的其他配置项。"""
        env_file = tmp_path / ".env"
        env_file.write_text("JWT_SECRET=abc123\nPORT=8080\n")
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            write_dot_env({"DATABASE_URL": "mysql+aiomysql://u:p@h:3306/db"})
            result = read_dot_env()
            assert result["JWT_SECRET"] == "abc123"
            assert result["PORT"] == "8080"
            assert result["DATABASE_URL"] == "mysql+aiomysql://u:p@h:3306/db"

    def test_mysql_password_with_special_chars(self, tmp_path: Path):
        """密码含特殊字符时仍能正确写入和读取。"""
        env_file = tmp_path / ".env"
        with patch("app.core.env_writer.get_env_path", return_value=env_file):
            url = "mysql+aiomysql://user:p@ss=w0rd!@host:3306/db"
            write_dot_env({"DATABASE_URL": url})
            result = read_dot_env()
            assert result["DATABASE_URL"] == url


class TestMigrationAppPathConsistency:
    """回归：打包模式下 Alembic 迁移目标库必须与应用运行时连接的 SQLite 文件一致。

    历史 bug：env.py 用 ``{exe_dir}/kindergarten.db``，而 database.py 用
    ``app_data_dir()/kindergarten.db``，导致迁移建表在 A 库、应用读 B 库，
    页面报 ``no such table: class_config``。
    """

    def test_empty_url_migration_and_app_resolve_same_sqlite_file(self, monkeypatch):
        """DATABASE_URL 为空时，迁移（build_sync_url）与应用（_resolve_database_url）
        必须指向同一个 SQLite 文件，仅驱动前缀不同。"""
        from app.core import database
        from app.core.paths import app_data_dir
        from app.core.startup import build_sync_url

        monkeypatch.setattr(database.settings, "DATABASE_URL", "")

        expected = (app_data_dir() / "kindergarten.db").as_posix()

        migration_url = build_sync_url("")
        app_url = database._resolve_database_url()

        assert migration_url == f"sqlite:///{expected}"
        assert app_url == f"sqlite+aiosqlite:///{expected}"
        # 去掉异步驱动差异后必须是同一个文件
        assert app_url.replace("+aiosqlite", "") == migration_url

    def test_explicit_mysql_url_passthrough(self):
        """显式配置 MySQL 异步 URL 时，迁移侧应转换为同步 pymysql 驱动且库名不变。"""
        from app.core.startup import build_sync_url

        sync = build_sync_url("mysql+aiomysql://u:p@h:3306/db")
        assert sync == "mysql+pymysql://u:p@h:3306/db"
