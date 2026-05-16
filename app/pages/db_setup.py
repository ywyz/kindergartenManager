"""数据库连接配置页面 — 首次部署或无 .env 时使用"""
import os
import re
import base64
import hashlib
from pathlib import Path

import pymysql
from cryptography.fernet import Fernet
from nicegui import run, ui

from app.config import BASE_DIR, DBConfig, AppConfig


# ---------------------------------------------------------------------------
# .env 读写工具
# ---------------------------------------------------------------------------

def _read_env_file(path: Path) -> dict[str, str]:
    """读取 .env 文件，返回键值字典（跳过注释行）"""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line)
        if m:
            result[m.group(1)] = m.group(2).strip('"').strip("'")
    return result


_SENSITIVE_ENV_KEYS = {"DB_PASSWORD", "APP_SECRET_KEY"}


def _build_fernet() -> Fernet:
    """从 APP_CONFIG_MASTER_KEY 派生 Fernet key。"""
    master = os.environ.get("APP_CONFIG_MASTER_KEY", "").strip()
    if not master:
        raise ValueError("缺少 APP_CONFIG_MASTER_KEY，无法安全保存敏感配置")
    digest = hashlib.sha256(master.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt_if_sensitive(key: str, value: str) -> str:
    """敏感键写入前加密，返回可写入 .env 的值。"""
    if key not in _SENSITIVE_ENV_KEYS:
        return value
    token = _build_fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    return f"ENC({token})"


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    """将键值字典写入 .env 文件（覆盖已有同名键，追加新键）"""
    existing: dict[str, str] = {}
    lines: list[str] = []

    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=', stripped)
                if m:
                    key = m.group(1)
                    existing[key] = line
                    # 用新值替换
                    if key in values:
                        safe_value = _encrypt_if_sensitive(key, values[key])
                        lines.append(f'{key}="{safe_value}"')
                        continue
            lines.append(line)
    # 追加不存在的新键
    for k, v in values.items():
        if k not in existing:
            safe_value = _encrypt_if_sensitive(k, v)
            lines.append(f'{k}="{safe_value}"')

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _apply_db_config_runtime(host: str, port: int, user: str, password: str, name: str) -> None:
    """在运行时更新 DBConfig 类属性，使改动立即生效（无需重启）"""
    DBConfig.HOST = host
    DBConfig.PORT = port
    DBConfig.USER = user
    DBConfig.PASSWORD = password
    DBConfig.NAME = name


def _test_connection(host: str, port: int, user: str, password: str, name: str) -> tuple[bool, str]:
    """同步测试数据库连接（供 io_bound 调用）"""
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=name,
            charset="utf8mb4",
            connect_timeout=5,
        )
        conn.close()
        return True, "连接成功"
    except Exception as e:
        return False, str(e)


def _do_init_db() -> tuple[bool, str]:
    """初始化数据库表（io_bound 调用）"""
    try:
        from app.db import init_db
        init_db()
        return True, "数据库表初始化完成"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# 页面
# ---------------------------------------------------------------------------

def db_setup_page():
    """数据库连接配置页面"""

    ui.label("🔧 数据库连接配置").classes("text-2xl font-bold mb-2")
    ui.label(
        "首次使用请填写 MySQL 数据库连接信息，配置将保存至应用目录的 .env 文件。"
    ).classes("text-sm text-gray-500 mb-4")

    # 读取已有配置作为默认值
    env_vals = _read_env_file(BASE_DIR / ".env")

    with ui.card().classes("w-full max-w-xl"):
        ui.label("MySQL 连接信息").classes("text-lg font-semibold mb-3")

        host_input = ui.input(
            "数据库地址 (DB_HOST)",
            value=env_vals.get("DB_HOST", DBConfig.HOST),
            placeholder="例：localhost 或 192.168.1.100",
        ).classes("w-full")

        with ui.row().classes("w-full gap-4"):
            port_input = ui.input(
                "端口 (DB_PORT)",
                value=env_vals.get("DB_PORT", str(DBConfig.PORT)),
                placeholder="3306",
            ).classes("flex-1")
            db_input = ui.input(
                "数据库名 (DB_NAME)",
                value=env_vals.get("DB_NAME", DBConfig.NAME),
                placeholder="kindergarten",
            ).classes("flex-1")

        user_input = ui.input(
            "用户名 (DB_USER)",
            value=env_vals.get("DB_USER", DBConfig.USER),
            placeholder="root",
        ).classes("w-full")

        pwd_input = ui.input(
            "密码 (DB_PASSWORD)",
            value=env_vals.get("DB_PASSWORD", ""),
            placeholder="数据库密码",
            password=True,
            password_toggle_button=True,
        ).classes("w-full")

        ui.separator().classes("my-2")

        secret_input = ui.input(
            "应用密钥 (APP_SECRET_KEY)",
            value=env_vals.get("APP_SECRET_KEY", AppConfig.SECRET_KEY),
            placeholder="随机字符串，用于加密 AI Key",
            password=True,
            password_toggle_button=True,
        ).classes("w-full")
        ui.label(
            "⚠️ 密钥一旦保存后请勿修改，否则已保存的 AI Key 将无法解密。"
        ).classes("text-xs text-amber-600")

        status_label = ui.label("").classes("text-sm mt-2 min-h-[20px]")

        with ui.row().classes("gap-3 mt-3"):
            async def on_test():
                status_label.set_text("⏳ 正在测试连接…")
                try:
                    port = int(port_input.value.strip() or "3306")
                except ValueError:
                    status_label.set_text("❌ 端口号必须是数字")
                    return

                ok, msg = await run.io_bound(
                    _test_connection,
                    host_input.value.strip(),
                    port,
                    user_input.value.strip(),
                    pwd_input.value,
                    db_input.value.strip(),
                )
                if ok:
                    status_label.set_text("✅ 连接测试成功").classes("text-green-600")
                else:
                    status_label.set_text(f"❌ 连接失败：{msg}").classes("text-red-600")

            async def on_save():
                status_label.set_text("⏳ 保存中…")
                try:
                    port = int(port_input.value.strip() or "3306")
                except ValueError:
                    status_label.set_text("❌ 端口号必须是数字")
                    return

                host = host_input.value.strip()
                user = user_input.value.strip()
                password = pwd_input.value
                name = db_input.value.strip()
                secret = secret_input.value.strip()

                # 先测试连接
                ok, msg = await run.io_bound(_test_connection, host, port, user, password, name)
                if not ok:
                    status_label.set_text(f"❌ 连接失败，配置未保存：{msg}")
                    return

                # 写入 .env
                env_path = BASE_DIR / ".env"
                _write_env_file(env_path, {
                    "DB_HOST": host,
                    "DB_PORT": str(port),
                    "DB_USER": user,
                    "DB_PASSWORD": password,
                    "DB_NAME": name,
                    "APP_SECRET_KEY": secret,
                })

                # 更新运行时配置
                _apply_db_config_runtime(host, port, user, password, name)
                AppConfig.SECRET_KEY = secret
                os.environ["APP_SECRET_KEY"] = secret

                # 初始化数据库表
                init_ok, init_msg = await run.io_bound(_do_init_db)
                if init_ok:
                    status_label.set_text("✅ 配置已保存，数据库表初始化完成，正在跳转…")
                    ui.timer(1.5, lambda: ui.navigate.to("/settings"), once=True)
                else:
                    status_label.set_text(f"⚠️ 配置已保存，但建表失败：{init_msg}")

            ui.button("测试连接", icon="wifi_find", on_click=on_test).props("outline")
            ui.button("保存并进入系统", icon="save", on_click=on_save).props("color=primary")

    ui.separator().classes("my-4 max-w-xl")

    with ui.card().classes("w-full max-w-xl bg-blue-50"):
        ui.label("📋 配置说明").classes("font-semibold mb-2")
        ui.html("""
        <ul class="text-sm text-gray-700 list-disc pl-5 space-y-1">
          <li>配置信息保存在应用程序同级目录的 <code>.env</code> 文件中</li>
          <li>MySQL 服务器需开启远程访问权限并允许该用户连接</li>
          <li>数据库需提前创建（例：<code>CREATE DATABASE kindergarten CHARACTER SET utf8mb4;</code>）</li>
          <li>数据表会在首次保存配置后自动创建</li>
          <li>如需重置配置，删除 <code>.env</code> 文件后重启应用即可</li>
        </ul>
        """)
