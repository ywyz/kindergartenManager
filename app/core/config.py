"""应用配置：通过 pydantic-settings 从 .env 文件和环境变量加载。

首次部署（无 .env 文件）时的行为：
- DATABASE_URL 为空 → database.py 自动降级为嵌入式 SQLite（适合桌面/演示环境）。
- ENCRYPTION_KEY / JWT_SECRET 为空 → 自动生成随机密钥并持久化到 .kindergarten_secrets，
  确保重启后已加密的 AI Key 仍可解密、已登录 token 不失效。
  生产/服务器环境请在 .env 中显式配置固定密钥。
"""

import logging
import os
import secrets
import stat
import tempfile
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import app_data_dir

logger = logging.getLogger("app.config")


class _SecretsFileError(RuntimeError):
    """密钥文件无法安全访问；消息不得包含密钥正文。"""


def _secrets_file_path() -> Path:
    """返回自动生成密钥的持久化文件路径（位于用户可写数据目录）。"""
    return app_data_dir() / ".kindergarten_secrets"


def _parse_kv_text(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def _posix_open_flags(base_flags: int) -> int:
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    if not no_follow:
        raise _SecretsFileError("当前 POSIX 平台不支持安全打开密钥文件")
    return base_flags | no_follow | getattr(os, "O_CLOEXEC", 0)


def _harden_regular_fd(fd: int, path: Path) -> None:
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise _SecretsFileError(f"密钥文件不是普通文件：{path}")
        os.fchmod(fd, 0o600)
    except _SecretsFileError:
        raise
    except OSError:
        raise _SecretsFileError(f"无法安全设置密钥文件权限：{path}") from None


def _read_posix_text(path: Path) -> str | None:
    try:
        fd = os.open(path, _posix_open_flags(os.O_RDONLY))
    except FileNotFoundError:
        return None
    except OSError:
        raise _SecretsFileError(f"无法安全打开密钥文件：{path}") from None

    try:
        _harden_regular_fd(fd, path)
        chunks: list[bytes] = []
        while chunk := os.read(fd, 65_536):
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8")
    except _SecretsFileError:
        raise
    except (OSError, UnicodeError):
        raise _SecretsFileError(f"无法安全读取密钥文件：{path}") from None
    finally:
        os.close(fd)


def _read_kv_file(path: Path) -> dict[str, str]:
    """先收紧安全边界，再解析 key=value；仅文件不存在视为空。"""
    if os.name == "posix":
        text = _read_posix_text(path)
    else:
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            text = None
        except (OSError, UnicodeError):
            raise _SecretsFileError(f"无法读取密钥文件：{path}") from None

    return {} if text is None else _parse_kv_text(text)


def _serialize_kv(values: dict[str, str]) -> bytes:
    return ("\n".join(f"{key}={value}" for key, value in values.items()) + "\n").encode(
        "utf-8"
    )


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("密钥文件写入未取得进展")
        view = view[written:]


def _path_entry_exists(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        raise _SecretsFileError(f"无法检查密钥文件：{path}") from None
    return True


def _remove_failed_artifact(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        raise _SecretsFileError(f"无法清理失败的密钥文件：{path}") from None


def _cleanup_temp_artifact(
    fd: int | None,
    temp_path: Path | None,
    target_path: Path,
) -> None:
    cleanup_failed = False
    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            cleanup_failed = True
    if temp_path is not None:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            cleanup_failed = True
    if cleanup_failed:
        raise _SecretsFileError(f"无法清理临时密钥文件：{target_path}") from None


def _create_posix_file(path: Path, payload: bytes) -> None:
    created = False
    try:
        fd = os.open(
            path,
            _posix_open_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL),
            0o600,
        )
        created = True
        try:
            _harden_regular_fd(fd, path)
            _write_all(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)
    except (OSError, _SecretsFileError):
        if created:
            _remove_failed_artifact(path)
        raise _SecretsFileError(f"无法安全持久化密钥文件：{path}") from None


def _replace_posix_file(path: Path, payload: bytes) -> None:
    temp_path: Path | None = None
    temp_fd: int | None = None
    try:
        temp_fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            dir=path.parent,
        )
        temp_path = Path(temp_name)
        _harden_regular_fd(temp_fd, temp_path)
        _write_all(temp_fd, payload)
        os.fsync(temp_fd)
        os.close(temp_fd)
        temp_fd = None

        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise _SecretsFileError(f"密钥文件不是普通文件：{path}")
        os.replace(temp_path, path)
        temp_path = None
    except (OSError, _SecretsFileError):
        raise _SecretsFileError(f"无法安全持久化密钥文件：{path}") from None
    finally:
        _cleanup_temp_artifact(temp_fd, temp_path, path)


def _replace_portable_file(path: Path, payload: bytes) -> None:
    temp_path: Path | None = None
    temp_fd: int | None = None
    try:
        temp_fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            dir=path.parent,
        )
        temp_path = Path(temp_name)
        with os.fdopen(temp_fd, "wb") as stream:
            temp_fd = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
        temp_path = None
    except OSError:
        raise _SecretsFileError(f"无法持久化密钥文件：{path}") from None
    finally:
        _cleanup_temp_artifact(temp_fd, temp_path, path)


def _write_kv_file(path: Path, new_values: dict[str, str]) -> None:
    """原子合并新键；首次 POSIX 创建直接以最终路径和 0600 完成。"""
    existing = _read_kv_file(path)
    existing.update(new_values)
    payload = _serialize_kv(existing)
    entry_exists = _path_entry_exists(path)

    if os.name == "posix":
        if entry_exists:
            _replace_posix_file(path, payload)
        else:
            _create_posix_file(path, payload)
    else:
        _replace_portable_file(path, payload)


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

        # 即使环境变量已覆盖两个 Key，也先验证既有文件的类型与权限。
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
