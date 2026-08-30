"""跨平台可写数据目录解析。

优先级：

- 若设置 ``KINDERGARTEN_DATA_DIR``，直接使用该值（必须是绝对路径）；
- 打包（PyInstaller ``frozen``）模式：回退到用户可写目录；
- 其他模式：使用当前工作目录。
"""

import os
import stat
import sys
from pathlib import Path

_APP_DIR_NAME = "KindergartenManager"


def _posix_directory_flags() -> int:
    required = ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC")
    if not all(getattr(os, name, 0) for name in required):
        raise RuntimeError("当前 POSIX 平台不支持安全打开应用数据目录")
    return sum(getattr(os, name) for name in required)


def _validate_ancestor(metadata: os.stat_result, expected_uid: int) -> None:
    if not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError("应用数据目录祖先必须是目录")
    if metadata.st_uid not in (0, expected_uid):
        raise RuntimeError("应用数据目录祖先必须由 root 或当前用户拥有")
    if metadata.st_mode & 0o022 and not metadata.st_mode & stat.S_ISVTX:
        raise RuntimeError("应用数据目录祖先不得由 group/other 可写")


def _validate_directory(metadata: os.stat_result) -> None:
    if not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError("应用数据目录祖先必须是目录")


def _validate_final_directory(
    directory_fd: int, expected_uid: int, *, harden: bool = True
) -> os.stat_result:
    metadata = os.fstat(directory_fd)
    if not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError("应用数据目录必须是目录")
    if metadata.st_uid != expected_uid:
        raise RuntimeError("应用数据目录必须由当前用户拥有")

    if not harden:
        return metadata

    try:
        os.fchmod(directory_fd, 0o700)
        verified = os.fstat(directory_fd)
    except OSError as exc:
        raise RuntimeError("无法安全设置应用数据目录权限") from exc
    if (
        not stat.S_ISDIR(verified.st_mode)
        or verified.st_uid != expected_uid
        or stat.S_IMODE(verified.st_mode) != 0o700
    ):
        raise RuntimeError("应用数据目录未通过安全检查")
    return verified


def _open_secure_data_dir_fd(
    data_dir: Path,
    *,
    create: bool = True,
    harden_final: bool = True,
    check_ancestors: bool = True,
) -> tuple[Path, int]:
    """Open every POSIX path component without following symlinks.

    The returned descriptor remains owned by the caller.  It is the anchor
    used by ``env_writer`` for all final-component operations.
    """
    directory_flags = _posix_directory_flags()
    normalized = Path(os.path.abspath(data_dir))
    if normalized == Path("/"):
        raise RuntimeError("应用数据目录不得是文件系统根目录")
    expected_uid = os.geteuid()

    try:
        current_fd = os.open(Path("/"), os.O_RDONLY | directory_flags)
    except OSError as exc:
        raise RuntimeError("无法安全打开应用数据目录") from exc

    current_path = Path("/")
    try:
        components = normalized.parts[1:]
        if not components:
            verified = _validate_final_directory(
                current_fd, expected_uid, harden=harden_final
            )
        else:
            root_metadata = os.fstat(current_fd)
            if check_ancestors:
                _validate_ancestor(root_metadata, expected_uid)
            else:
                _validate_directory(root_metadata)
            verified = root_metadata

        for index, component in enumerate(components):
            is_final = index == len(components) - 1
            child_path = current_path / component
            try:
                child_fd = os.open(
                    component,
                    os.O_RDONLY | directory_flags,
                    dir_fd=current_fd,
                )
            except FileNotFoundError:
                if not create:
                    raise RuntimeError("应用数据目录不存在")
                # Create beneath the already verified parent descriptor; do
                # not let an attacker replace an ancestor between mkdir and
                # the descriptor open.
                try:
                    os.mkdir(component, mode=0o700, dir_fd=current_fd)
                except FileExistsError:
                    pass
                try:
                    child_fd = os.open(
                        component,
                        os.O_RDONLY | directory_flags,
                        dir_fd=current_fd,
                    )
                except OSError as exc:
                    raise RuntimeError("无法安全打开应用数据目录") from exc
            except OSError as exc:
                raise RuntimeError("无法安全打开应用数据目录") from exc

            try:
                if is_final:
                    verified = _validate_final_directory(
                        child_fd, expected_uid, harden=harden_final
                    )
                else:
                    metadata = os.fstat(child_fd)
                    if check_ancestors:
                        _validate_ancestor(metadata, expected_uid)
                    else:
                        _validate_directory(metadata)
                    verified = metadata
            except BaseException:
                try:
                    os.close(child_fd)
                except OSError:
                    pass
                raise
            try:
                os.close(current_fd)
            except OSError:
                pass
            current_fd = child_fd
            current_path = child_path

        try:
            path_metadata = normalized.lstat()
        except OSError as exc:
            raise RuntimeError("无法安全检查应用数据目录") from exc
        if (
            not stat.S_ISDIR(path_metadata.st_mode)
            or stat.S_ISLNK(path_metadata.st_mode)
            or path_metadata.st_dev != verified.st_dev
            or path_metadata.st_ino != verified.st_ino
        ):
            raise RuntimeError("应用数据目录路径在检查期间发生变化")
        return normalized, current_fd
    except BaseException:
        try:
            os.close(current_fd)
        except OSError:
            pass
        raise


def _secure_posix_data_dir(data_dir: Path) -> Path:
    normalized, directory_fd = _open_secure_data_dir_fd(data_dir)
    try:
        return normalized
    finally:
        try:
            os.close(directory_fd)
        except OSError:
            pass


def app_data_dir() -> Path:
    """返回应用可写数据目录，用于 SQLite、密钥、.env、状态标记等运行期文件。"""
    explicit_data_dir = os.environ.get("KINDERGARTEN_DATA_DIR")
    if explicit_data_dir:
        data_dir = Path(explicit_data_dir).expanduser()
        if not data_dir.is_absolute():
            raise ValueError("KINDERGARTEN_DATA_DIR must be an absolute path")
        if os.name == "posix":
            return _secure_posix_data_dir(data_dir)
        data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        return data_dir

    if not getattr(sys, "frozen", False):
        return Path.cwd()

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME")
        root = Path(base) if base else Path.home() / ".local" / "share"

    data_dir = root / _APP_DIR_NAME
    if os.name == "posix":
        return _secure_posix_data_dir(data_dir)
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    return data_dir
