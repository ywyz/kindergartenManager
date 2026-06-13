"""应用配置：通过 pydantic-settings 从 .env 文件和环境变量加载。

首次部署（无 .env 文件）时的行为：
- DATABASE_URL 为空 → database.py 自动降级为嵌入式 SQLite（适合桌面/演示环境）。
- ENCRYPTION_KEY / JWT_SECRET 为空 → 自动生成随机密钥并持久化到 .kindergarten_secrets，
  确保重启后已加密的 AI Key 仍可解密、已登录 token 不失效。
  生产/服务器环境请在 .env 中显式配置固定密钥。
"""
import logging
import secrets
import sys
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("app.config")


def _secrets_file_path() -> Path:
    """返回自动生成密钥的持久化文件路径。"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包模式：保存在可执行文件同目录
        return Path(sys.executable).parent / ".kindergarten_secrets"
    # 开发 / Docker / systemd 模式：保存在工作目录
    return Path.cwd() / ".kindergarten_secrets"


def _read_kv_file(path: Path) -> dict[str, str]:
    """解析 key=value 文件，忽略空行与注释行。"""
    result: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
    except OSError:
        pass
    return result


def _write_kv_file(path: Path, new_values: dict[str, str]) -> None:
    """将新键值追加/覆盖到持久化文件（已有键保留）。"""
    existing = _read_kv_file(path)
    existing.update(new_values)
    try:
        path.write_text(
            "\n".join(f"{k}={v}" for k, v in existing.items()) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("无法写入密钥持久化文件 %s：%s", path, exc)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── 数据库 ───────────────────────────────────────────────────────────────
    # 留空时 database.py 自动降级为嵌入式 SQLite（适合桌面/演示环境）
    DATABASE_URL: str = ""

    # ── 密钥 ─────────────────────────────────────────────────────────────────
    # 留空时 _ensure_secrets 自动生成并持久化；生产/服务器环境请在 .env 中显式配置
    ENCRYPTION_KEY: str = ""
    JWT_SECRET: str = ""
    JWT_EXPIRE_MINUTES: int = 60

    # ── 应用端口 ──────────────────────────────────────────────────────────────
    # 可在 .env 中设置 PORT=xxxx 更改监听端口，修改后需重启生效
    PORT: int = 8080

    # ── 节假日 ───────────────────────────────────────────────────────────────
    HOLIDAY_API_URL: str = "https://timor.tech/api/holiday/info/"
    LOG_LEVEL: str = "INFO"

    # ── 管理员初始化引导 ─────────────────────────────────────────────────────
    BOOTSTRAP_ADMIN_ENABLED: bool = False
    BOOTSTRAP_ADMIN_TENANT_ID: int = 1
    BOOTSTRAP_ADMIN_USERNAME: str = "sysadmin"
    BOOTSTRAP_ADMIN_PASSWORD: str = ""
    BOOTSTRAP_ADMIN_ALLOW_REMOTE: bool = False

    # ── 对外只读 REST API（二期） ─────────────────────────────────────────────
    # API_KEYS：逗号分隔的 "apikey:tenant_id" 映射，例如 "svc-abc:1,svc-xyz:2"
    API_KEYS: str = ""
    # API_SIGNING_SECRET：HMAC-SHA256 请求签名密钥；非空时强制校验签名。
    API_SIGNING_SECRET: str = ""
    # 签名时间戳允许的最大偏移秒数（防重放）。
    API_SIGNATURE_MAX_SKEW: int = 300

    # ── 图片存储（游戏观察子系统） ────────────────────────────────────────────
    IMAGE_STORAGE_BACKEND: str = "mysql_blob"
    IMAGE_MAX_BYTES: int = 1_048_576

    @model_validator(mode="after")
    def _ensure_secrets(self) -> "Settings":
        """自动生成缺失的密钥并持久化，保证重启后可还原。"""
        secrets_path = _secrets_file_path()
        generated: dict[str, str] = {}

        # 优先从持久化文件补充还未从 .env/环境变量读到的密钥
        if not self.ENCRYPTION_KEY or not self.JWT_SECRET:
            saved = _read_kv_file(secrets_path)
            if not self.ENCRYPTION_KEY and "ENCRYPTION_KEY" in saved:
                object.__setattr__(self, "ENCRYPTION_KEY", saved["ENCRYPTION_KEY"])
            if not self.JWT_SECRET and "JWT_SECRET" in saved:
                object.__setattr__(self, "JWT_SECRET", saved["JWT_SECRET"])

        if not self.ENCRYPTION_KEY:
            key = secrets.token_urlsafe(32)
            object.__setattr__(self, "ENCRYPTION_KEY", key)
            generated["ENCRYPTION_KEY"] = key
            logger.warning(
                "ENCRYPTION_KEY 未配置，已自动生成随机密钥。"
                "密钥改变后已加密的 AI Key 将无法解密；生产环境请在 .env 中显式配置。"
            )

        if not self.JWT_SECRET:
            key = secrets.token_urlsafe(64)
            object.__setattr__(self, "JWT_SECRET", key)
            generated["JWT_SECRET"] = key
            logger.warning(
                "JWT_SECRET 未配置，已自动生成随机密钥。"
                "重启应用后已登录用户的 token 将失效；生产环境请在 .env 中显式配置。"
            )

        if generated:
            _write_kv_file(secrets_path, generated)
            logger.info("自动生成的密钥已持久化到 %s", secrets_path)

        return self


settings = Settings()
