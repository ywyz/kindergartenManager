"""运行时 .env 文件读写工具。

路径策略：
- PyInstaller 打包模式：平台用户数据目录
- 开发 / Docker 模式：当前工作目录

这与 app.core.config 中 _secrets_file_path() 的路径逻辑一致，
保证 .env 文件始终与 .kindergarten_secrets 文件位于同一目录。
"""

import os
import secrets
import stat
import sys
import tempfile
from pathlib import Path

from app.core.paths import _open_secure_data_dir_fd, app_data_dir


def _posix_open_flags(base_flags: int) -> int:
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    non_block = getattr(os, "O_NONBLOCK", 0)
    close_on_exec = getattr(os, "O_CLOEXEC", 0)
    if not no_follow or not non_block or not close_on_exec:
        raise RuntimeError("当前 POSIX 平台不支持安全打开配置文件")
    return base_flags | no_follow | non_block | close_on_exec


def _env_file_error(action: str, path: Path) -> RuntimeError:
    """Return an error that identifies only the path, never configuration values."""
    return RuntimeError(f"无法{action}配置文件：{path}")


def _absolute_env_path(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _open_env_directory(path: Path) -> tuple[Path, int]:
    absolute_path = _absolute_env_path(path)
    harden_final = bool(
        os.environ.get("KINDERGARTEN_DATA_DIR") or getattr(sys, "frozen", False)
    )
    try:
        return _open_secure_data_dir_fd(
            absolute_path.parent,
            create=False,
            harden_final=harden_final,
            check_ancestors=harden_final,
        )
    except (OSError, RuntimeError) as exc:
        raise _env_file_error("安全访问", absolute_path) from exc


def _read_posix_text_from_fd(
    directory_fd: int, filename: str, path: Path
) -> str | None:
    try:
        fd = os.open(
            filename,
            _posix_open_flags(os.O_RDONLY),
            dir_fd=directory_fd,
        )
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise _env_file_error("安全读取", path) from exc

    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise _env_file_error("安全读取", path)
        if metadata.st_uid != os.geteuid():
            raise _env_file_error("安全读取", path)
        try:
            os.fchmod(fd, 0o600)
        except OSError as exc:
            raise _env_file_error("安全读取", path) from exc

        verified = os.fstat(fd)
        if (
            not stat.S_ISREG(verified.st_mode)
            or verified.st_uid != os.geteuid()
            or stat.S_IMODE(verified.st_mode) != 0o600
        ):
            raise _env_file_error("安全读取", path)

        chunks: list[bytes] = []
        while chunk := os.read(fd, 65_536):
            chunks.append(chunk)
        try:
            return b"".join(chunks).decode("utf-8")
        except UnicodeError as exc:
            raise _env_file_error("读取", path) from exc
    except RuntimeError:
        raise
    except OSError as exc:
        raise _env_file_error("读取", path) from exc
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def _read_posix_text(path: Path) -> str | None:
    """Read a POSIX .env snapshot through a verified parent directory fd."""
    absolute_path = _absolute_env_path(path)
    _, directory_fd = _open_env_directory(absolute_path)
    try:
        return _read_posix_text_from_fd(directory_fd, absolute_path.name, absolute_path)
    finally:
        try:
            os.close(directory_fd)
        except OSError:
            pass


def _posix_file_metadata(
    directory_fd: int, filename: str, path: Path
) -> os.stat_result | None:
    """Inspect .env through its verified parent without following symlinks."""
    try:
        metadata = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise _env_file_error("安全检查", path) from exc

    if (
        stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
    ):
        raise _env_file_error("安全访问", path)
    return metadata


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("配置文件写入未取得进展")
        view = view[written:]


def _create_posix_temp_file(directory_fd: int, target_name: str) -> tuple[str, int]:
    flags = _posix_open_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    for _ in range(128):
        filename = f".{target_name}.{secrets.token_hex(16)}"
        try:
            fd = os.open(filename, flags, 0o600, dir_fd=directory_fd)
        except FileExistsError:
            continue
        return filename, fd
    raise OSError("无法创建配置文件临时文件")


def _write_posix_file(path: Path, payload: bytes) -> None:
    absolute_path = _absolute_env_path(path)
    _, directory_fd = _open_env_directory(absolute_path)
    target_name = absolute_path.name
    temp_name: str | None = None
    temp_fd: int | None = None
    try:
        # Validate the target through the same directory fd used for every
        # subsequent final-component operation.
        _posix_file_metadata(directory_fd, target_name, absolute_path)
        temp_name, temp_fd = _create_posix_temp_file(directory_fd, target_name)
        metadata = os.fstat(temp_fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid():
            raise _env_file_error("安全写入", absolute_path)
        os.fchmod(temp_fd, 0o600)
        _write_all(temp_fd, payload)
        os.fsync(temp_fd)
        os.close(temp_fd)
        temp_fd = None

        # Recheck immediately before replacement.  A missing target is valid
        # for first creation; symlink/non-regular/foreign targets are not.
        _posix_file_metadata(directory_fd, target_name, absolute_path)
        os.replace(
            temp_name,
            target_name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        temp_name = None

        verified = _posix_file_metadata(directory_fd, target_name, absolute_path)
        if verified is None or stat.S_IMODE(verified.st_mode) != 0o600:
            raise _env_file_error("安全写入", absolute_path)
        os.fsync(directory_fd)
    except RuntimeError:
        raise
    except OSError as exc:
        raise _env_file_error("写入", absolute_path) from exc
    finally:
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except OSError:
                pass
        if temp_name is not None:
            try:
                os.unlink(temp_name, dir_fd=directory_fd)
            except OSError:
                pass
        try:
            os.close(directory_fd)
        except OSError:
            pass


def _read_portable_text(path: Path) -> str | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise _env_file_error("读取", path) from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise _env_file_error("安全读取", path)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise _env_file_error("读取", path) from exc


def _write_portable_file(path: Path, payload: bytes) -> None:
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
            os.chmod(temp_path, 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
        temp_path = None
    except OSError as exc:
        raise _env_file_error("写入", path) from exc
    finally:
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except OSError:
                pass
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def get_env_path() -> Path:
    """返回 .env 文件的绝对路径（位于用户可写数据目录）。"""
    return app_data_dir() / ".env"


def read_dot_env_snapshot() -> tuple[Path, str | None]:
    """Return the path and one safe, non-following read of the .env file."""
    path = get_env_path()
    text = _read_posix_text(path) if os.name == "posix" else _read_portable_text(path)
    return path, text


def read_dot_env() -> dict[str, str]:
    """解析 .env 文件，返回 key-value 字典。

    忽略空行与 # 开头的注释行。文件不存在时返回空字典。
    """
    _, text = read_dot_env_snapshot()
    if text is None:
        return {}

    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def write_dot_env(updates: dict[str, str]) -> None:
    """将 updates 中的 key-value 原子写入 .env，保留其余行不动。

    若 .env 不存在则自动创建。写入失败时抛出 RuntimeError。
    """
    path = get_env_path()
    try:
        existing = read_dot_env()
    except RuntimeError:
        raise _env_file_error("写入", path) from None
    existing.update(updates)
    try:
        payload = ("\n".join(f"{k}={v}" for k, v in existing.items()) + "\n").encode(
            "utf-8"
        )
        if os.name == "posix":
            _write_posix_file(path, payload)
        else:
            _write_portable_file(path, payload)
    except (OSError, RuntimeError, UnicodeError):
        raise _env_file_error("写入", path) from None
