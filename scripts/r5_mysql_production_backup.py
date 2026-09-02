"""Produce a restore-verified MySQL backup from the running production app.

This module is intentionally self contained.  Production only has a Python
standard library and Docker CLI available, so it must not import the
application (or a database driver) and must not rely on a shell.  The source
database is discovered from the running app container's ``DATABASE_URL``;
identity and Alembic revision are always read by this module and are never
operator inputs.

The operation is deliberately one-way with respect to the source database:
the only source operations are ``SELECT`` statements and a transaction-safe
``mysqldump``.  The dump is restored to a newly created MySQL 8.4 container on
an internal, random network with tmpfs storage.  A consumer-compatible
``mysql-backup-v1.zip`` and ``backup-evidence.json`` are emitted only after
the isolated restore, row snapshot, tenant/blob checks, and asset checks pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets as _secrets
import shutil
import stat
import subprocess
import sys
import time
import uuid
import zipfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit


class ProductionMySQLBackupError(RuntimeError):
    """A production MySQL backup could not be proven safe and complete."""


# ``app.core.backup_evidence.IMAGE_RE`` is intentionally duplicated here so
# the producer remains usable with stdlib-only Python on the server.
_IMAGE_RE = re.compile(r"^[a-z0-9][a-z0-9._:/-]*[a-z0-9]@sha256:[0-9a-f]{64}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CONTAINER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_NETWORK_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_DATABASE_RE = re.compile(r"^[A-Za-z0-9_$-]{1,64}$")
_USER_RE = re.compile(r"^[A-Za-z0-9_$.-]{1,128}$")
_SCHEMA_VERSION = 1
_ARCHIVE_NAME = "mysql-backup-v1.zip"
_EVIDENCE_NAME = "backup-evidence.json"
_DATABASE_NAME = "database.sql"
_MANIFEST_NAME = "manifest.json"
_SECRET_MEMBER = "secrets/.kindergarten_secrets"
_TEMPLATE_NAMES = (
    "teacherplan.docx",
    "ObservationRecord.docx",
    "OneOnOneListeningSmallSecond.docx",
    "homemadeteaching.docx",
    "coursereviewactivity.docx",
)
_TEMPLATE_MEMBERS = tuple(f"templates/{name}" for name in _TEMPLATE_NAMES)
_MAX_REVISION_LENGTH = 128
_VALIDITY = timedelta(hours=24)
_COMMAND_TIMEOUT = 180
_READY_TIMEOUT = 180
_READONLY_ENV_NAMES = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "DOCKER_HOST",
    "DOCKER_CONTEXT",
    "DOCKER_CONFIG",
    "TMPDIR",
)
_DUMP_OPTIONS = (
    "--single-transaction",
    "--quick",
    "--skip-lock-tables",
    "--hex-blob",
    "--triggers",
    "--routines",
    "--events",
    "--set-gtid-purged=OFF",
    "--no-tablespaces",
)
_TRANSIENT_SUFFIXES = (
    ".lock",
    ".lck",
    ".tmp",
    ".temp",
    ".part",
    ".swp",
    ".swo",
    "-wal",
    "-shm",
    "-journal",
)
_CACHE_NAMES = {"cache", ".cache", "__pycache__"}
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


Runner = Callable[..., subprocess.CompletedProcess[bytes]]


def _error(message: str) -> ProductionMySQLBackupError:
    """Build the one redacted exception type used by this module."""
    return ProductionMySQLBackupError(message)


def _safe_environment() -> dict[str, str]:
    """Keep Docker subprocesses from inheriting arbitrary application secrets."""
    return {
        name: value for name in _READONLY_ENV_NAMES if (value := os.environ.get(name))
    }


def _normalise_runner(runner: Runner | None) -> Runner:
    return runner or subprocess.run


def _run_command(
    command: Sequence[str],
    *,
    runner: Runner | None = None,
    input_path: Path | None = None,
    output_path: Path | None = None,
    check: bool = True,
    timeout: int = _COMMAND_TIMEOUT,
) -> subprocess.CompletedProcess[bytes]:
    """Run one list-form Docker command with redacted failure handling."""
    words = [str(part) for part in command]
    if not words or words[0] != "docker":
        raise _error("Only Docker CLI commands are allowed")
    if any(_CONTROL_RE.search(word) for word in words):
        raise _error("Docker command contains unsafe control characters")

    try:
        with ExitStack() as stack:
            stream = (
                stack.enter_context(input_path.open("rb"))
                if input_path is not None
                else None
            )
            stdout: Any = subprocess.PIPE
            stream_out = None
            if output_path is not None:
                stream_out = stack.enter_context(output_path.open("wb"))
                stdout = stream_out
            result = _normalise_runner(runner)(
                words,
                check=check,
                stdin=stream,
                stdout=stdout,
                stderr=subprocess.PIPE,
                env=_safe_environment(),
                timeout=timeout,
            )
            if stream_out is not None:
                stream_out.flush()
                os.fsync(stream_out.fileno())
    except ProductionMySQLBackupError:
        raise
    except (OSError, subprocess.SubprocessError):
        raise _error("Docker command failed") from None
    if check and result.returncode != 0:
        raise _error("Docker command failed")
    return result


def _decode_output(result: subprocess.CompletedProcess[bytes]) -> str:
    raw = result.stdout or b""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise _error("Docker query returned invalid text") from None


def _docker_output(command: Sequence[str], *, runner: Runner | None = None) -> bytes:
    result = _run_command(command, runner=runner)
    return result.stdout or b""


def _validate_container(value: str, *, label: str = "Container") -> str:
    if not isinstance(value, str) or _CONTAINER_RE.fullmatch(value) is None:
        raise _error(f"{label} identity is unsafe")
    return value


def _validate_network(value: str, *, label: str = "Network") -> str:
    if not isinstance(value, str) or _NETWORK_RE.fullmatch(value) is None:
        raise _error(f"{label} identity is unsafe")
    return value


def _validate_image(value: str, *, label: str) -> str:
    if not isinstance(value, str) or _IMAGE_RE.fullmatch(value) is None:
        raise _error(f"{label} must be an immutable OCI digest")
    return value


def _validate_mysql_image(value: str) -> str:
    if not isinstance(value, str) or not (
        value.startswith("mysql@sha256:")
        and _DIGEST_RE.fullmatch(value.removeprefix("mysql@sha256:"))
    ):
        raise _error("MySQL image must be an immutable official MySQL digest")
    return value


def _require_absolute(path: Path, *, label: str) -> Path:
    value = Path(path)
    if not value.is_absolute():
        raise _error(f"{label} must be absolute")
    return value


def _reject_symlink_ancestors(path: Path, *, label: str) -> None:
    current = Path(path.anchor) if path.anchor else Path()
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            break
        except OSError:
            raise _error(f"{label} cannot be inspected") from None
        if stat.S_ISLNK(info.st_mode):
            raise _error(f"{label} contains a symlink")


def _owner_uid() -> int | None:
    return os.geteuid() if hasattr(os, "geteuid") else None


def _validate_directory(path: Path, *, label: str) -> Path:
    value = _require_absolute(path, label=label)
    _reject_symlink_ancestors(value, label=label)
    try:
        info = value.lstat()
    except OSError:
        raise _error(f"{label} is unavailable") from None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise _error(f"{label} must be a directory")
    uid = _owner_uid()
    if uid is not None and info.st_uid != uid:
        raise _error(f"{label} has an unsafe owner")
    if os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o002:
        raise _error(f"{label} is writable by other users")
    return value.resolve()


def _ensure_backup_root(path: Path) -> Path:
    value = _require_absolute(path, label="Backup root")
    _reject_symlink_ancestors(value, label="Backup root")
    if value.exists() or value.is_symlink():
        root = _validate_directory(value, label="Backup root")
        if os.name == "posix" and stat.S_IMODE(root.stat().st_mode) != 0o700:
            try:
                os.chmod(root, 0o700)
            except OSError:
                raise _error("Backup root permissions are unsafe") from None
        return root
    parent = value.parent
    if not parent.exists() or not parent.is_dir() or parent.is_symlink():
        raise _error("Backup root parent is unavailable")
    try:
        value.mkdir(mode=0o700)
        os.chmod(value, 0o700)
    except OSError:
        try:
            value.rmdir()
        except OSError:
            pass
        raise _error("Backup root cannot be created securely") from None
    return value.resolve()


def _validate_file(
    path: Path,
    *,
    label: str,
    owner_only: bool = False,
    owner_required: bool = True,
) -> Path:
    value = _require_absolute(path, label=label)
    _reject_symlink_ancestors(value, label=label)
    try:
        info = value.lstat()
    except OSError:
        raise _error(f"{label} is unavailable") from None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise _error(f"{label} must be a regular file")
    uid = _owner_uid()
    if owner_required and uid is not None and info.st_uid != uid:
        raise _error(f"{label} has an unsafe owner")
    mode = stat.S_IMODE(info.st_mode)
    if os.name == "posix" and (mode & 0o002 or (owner_only and mode != 0o600)):
        raise _error(f"{label} has unsafe permissions")
    return value.resolve()


def _ensure_disjoint(*paths: Path) -> None:
    resolved = [Path(path).resolve(strict=False) for path in paths]
    for index, first in enumerate(resolved):
        for second in resolved[index + 1 :]:
            if (
                first == second
                or first.is_relative_to(second)
                or second.is_relative_to(first)
            ):
                raise _error("Backup paths must be separate")


def _create_run_directory(root: Path) -> Path:
    for _ in range(32):
        candidate = root / f"run-{uuid.uuid4().hex}"
        try:
            candidate.mkdir(mode=0o700)
            os.chmod(candidate, 0o700)
            return candidate
        except FileExistsError:
            continue
        except OSError:
            raise _error("Backup run directory cannot be created") from None
    raise _error("Backup run directory name collision")


def _cleanup_run_directory(path: Path) -> None:
    try:
        shutil.rmtree(path)
    except OSError:
        raise _error(f"Backup cleanup required at {path}") from None
    if path.exists() or path.is_symlink():
        raise _error(f"Backup cleanup required at {path}")


def _secure_create(path: Path, payload: bytes = b"") -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(path, flags, 0o600)
        if os.name == "posix":
            os.fchmod(descriptor, 0o600)
        if payload:
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                view = view[written:]
        os.fsync(descriptor)
    except OSError:
        if descriptor >= 0:
            os.close(descriptor)
        path.unlink(missing_ok=True)
        raise _error("Secure file creation failed") from None
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _file_digest(path: Path) -> tuple[int, str]:
    value = _validate_file(path, label="Backup file", owner_only=True)
    digest = hashlib.sha256()
    size = 0
    try:
        with value.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError:
        raise _error("Backup file cannot be read") from None
    return size, digest.hexdigest()


def _copy_input(
    source: Path,
    destination: Path,
    *,
    label: str,
    allow_foreign_owner: bool = False,
) -> tuple[int, str]:
    source = _validate_file(
        source,
        label=label,
        owner_required=not allow_foreign_owner,
    )
    _secure_create(destination)
    digest = hashlib.sha256()
    size = 0
    try:
        source_fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        source_info = os.fstat(source_fd)
        if not stat.S_ISREG(source_info.st_mode):
            raise _error(f"{label} must be a regular file")
        destination_fd = os.open(
            destination, os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            while chunk := os.read(source_fd, 1024 * 1024):
                os.write(destination_fd, chunk)
                digest.update(chunk)
                size += len(chunk)
            final_info = os.fstat(source_fd)
            if (
                final_info.st_dev != source_info.st_dev
                or final_info.st_ino != source_info.st_ino
                or final_info.st_size != source_info.st_size
                or size != source_info.st_size
            ):
                raise _error(f"{label} changed while being backed up")
            os.fsync(destination_fd)
        finally:
            os.close(destination_fd)
            os.close(source_fd)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return size, digest.hexdigest()


def _is_transient(name: str) -> bool:
    lower = name.casefold()
    return (
        lower.startswith((".~lock.", "~$"))
        or lower in {".ds_store", "thumbs.db", ".directory"}
        or lower.endswith(_TRANSIENT_SUFFIXES)
    )


def _is_cache(name: str) -> bool:
    return name.casefold() in _CACHE_NAMES or name.casefold().endswith(".cache")


def _archive_path(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise _error(f"{label} path is invalid")
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        raise _error(f"{label} path is invalid")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or any(part in {"", ".", ".."} for part in parsed.parts):
        raise _error(f"{label} path is invalid")
    if any(":" in part for part in parsed.parts) or parsed.as_posix() != value:
        raise _error(f"{label} path is invalid")
    return value


def _iter_export_files(root: Path) -> Iterator[tuple[str, Path]]:
    root = _validate_directory(root, label="Exports source")

    def walk(directory: Path, prefix: PurePosixPath) -> Iterator[tuple[str, Path]]:
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError:
            raise _error("Exports source cannot be read") from None
        for entry in entries:
            path = Path(entry.path)
            if entry.is_symlink():
                raise _error("Exports source contains a symlink")
            if entry.is_dir(follow_symlinks=False):
                if not _is_cache(entry.name):
                    yield from walk(path, prefix / entry.name)
            elif entry.is_file(follow_symlinks=False):
                if _is_transient(entry.name):
                    continue
                name = _archive_path(
                    f"exports/{(prefix / entry.name).as_posix()}", label="Export"
                )
                yield name, _validate_file(path, label="Export file")
            else:
                raise _error("Exports source contains a non-regular entry")

    yield from walk(root, PurePosixPath())


def _collect_templates(
    root: Path,
    *,
    allow_foreign_owner: bool = False,
) -> list[tuple[str, Path]]:
    root = _validate_directory(root, label="Templates source")
    expected = set(_TEMPLATE_NAMES)
    found: dict[str, Path] = {}
    try:
        entries = sorted(os.scandir(root), key=lambda entry: entry.name)
    except OSError:
        raise _error("Templates source cannot be read") from None
    for entry in entries:
        path = Path(entry.path)
        if entry.is_symlink():
            raise _error("Templates source contains a symlink")
        if entry.is_dir(follow_symlinks=False):
            if not _is_cache(entry.name):
                raise _error("Templates source contains an unknown directory")
            continue
        if not entry.is_file(follow_symlinks=False):
            raise _error("Templates source contains a non-regular entry")
        if _is_transient(entry.name):
            continue
        if entry.name not in expected:
            raise _error("Templates source contains an unknown file")
        found[entry.name] = _validate_file(
            path,
            label="Template file",
            owner_required=not allow_foreign_owner,
        )
    if set(found) != expected:
        raise _error("A required template is missing")
    return [(f"templates/{name}", found[name]) for name in _TEMPLATE_NAMES]


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o600) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def _write_archive(
    destination: Path,
    staged: Sequence[tuple[str, Path, int, str]],
    manifest: Mapping[str, Any],
) -> None:
    _secure_create(destination)
    try:
        with (
            destination.open("r+b") as stream,
            zipfile.ZipFile(
                stream, mode="w", compression=zipfile.ZIP_DEFLATED
            ) as archive,
        ):
            manifest_bytes = (
                json.dumps(
                    manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                + "\n"
            ).encode("utf-8")
            archive.writestr(_zip_info(_MANIFEST_NAME), manifest_bytes)
            for name, source, _, _ in sorted(staged, key=lambda item: item[0]):
                with (
                    source.open("rb") as input_stream,
                    archive.open(_zip_info(name), mode="w") as output_stream,
                ):
                    shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(destination, 0o600)
    except BaseException:
        destination.unlink(missing_ok=True)
        if isinstance(sys.exc_info()[1], (KeyboardInterrupt, SystemExit)):
            raise
        raise _error("MySQL backup archive cannot be written") from None


def _json_pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _error("JSON contains duplicate fields")
        result[key] = value
    return result


def _verify_archive(
    artifact: Path,
    *,
    expected_manifest: Mapping[str, Any],
) -> None:
    """Re-open the exact archive and verify every member after writing."""
    try:
        with zipfile.ZipFile(artifact, mode="r") as archive:
            infos: dict[str, zipfile.ZipInfo] = {}
            for info in archive.infolist():
                name = _archive_path(info.filename, label="Archive member")
                if name in infos or info.is_dir():
                    raise _error("Backup archive members are invalid")
                mode = (info.external_attr >> 16) & 0xFFFF
                if mode and stat.S_IFMT(mode) not in {0, stat.S_IFREG}:
                    raise _error("Backup archive contains a non-regular member")
                infos[name] = info
            if _MANIFEST_NAME not in infos:
                raise _error("Backup manifest is missing")
            with archive.open(infos[_MANIFEST_NAME], "r") as stream:
                manifest = json.loads(
                    stream.read(1024 * 1024 + 1),
                    object_pairs_hook=_json_pairs_no_duplicates,
                )
            if manifest != dict(expected_manifest):
                raise _error("Backup manifest changed after writing")
            expected: dict[str, Mapping[str, Any]] = {
                manifest["database"]["path"]: manifest["database"],
                **{asset["path"]: asset for asset in manifest["assets"]},
            }
            if set(infos) != set(expected) | {_MANIFEST_NAME}:
                raise _error("Backup archive members do not match manifest")
            for name, descriptor in expected.items():
                info = infos[name]
                if info.file_size != descriptor["size_bytes"]:
                    raise _error("Backup archive member size does not match manifest")
                digest = hashlib.sha256()
                size = 0
                with archive.open(info, "r") as stream:
                    while chunk := stream.read(1024 * 1024):
                        size += len(chunk)
                        digest.update(chunk)
                if (
                    size != descriptor["size_bytes"]
                    or digest.hexdigest() != descriptor["sha256"]
                ):
                    raise _error(
                        "Backup archive member checksum does not match manifest"
                    )
    except ProductionMySQLBackupError:
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile, json.JSONDecodeError):
        raise _error("Backup archive cannot be verified") from None


def _app_facts(
    app_container: str, network: str, *, runner: Runner | None = None
) -> dict[str, str]:
    """Read the quiesced container/database binding in one Docker inspection."""
    output = _docker_output(["docker", "inspect", app_container], runner=runner)
    try:
        inspected = json.loads(output)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise _error("Application binding cannot be read") from None
    if not isinstance(inspected, list) or len(inspected) != 1:
        raise _error("Application binding is invalid")
    payload = inspected[0]
    if not isinstance(payload, dict):
        raise _error("Application binding is invalid")
    container_id = payload.get("Id")
    config = payload.get("Config")
    state = payload.get("State")
    network_settings = payload.get("NetworkSettings")
    if (
        not isinstance(container_id, str)
        or re.fullmatch(r"[0-9a-f]{64}", container_id) is None
        or not isinstance(config, dict)
        or not isinstance(state, dict)
        or state.get("Running") is not True
        or state.get("Paused") is not True
        or not isinstance(network_settings, dict)
    ):
        raise _error("Application must be running and paused for a consistent backup")
    image = _validate_image(config.get("Image"), label="Running application image")
    memberships = network_settings.get("Networks")
    if not isinstance(memberships, dict) or network not in memberships:
        raise _error("Application is not attached to the requested database network")
    membership = memberships[network]
    if not isinstance(membership, dict):
        raise _error("Application network binding is invalid")
    network_id = membership.get("NetworkID")
    if (
        not isinstance(network_id, str)
        or re.fullmatch(r"[0-9a-f]{64}", network_id) is None
    ):
        raise _error("Application network binding is invalid")
    values = config.get("Env")
    if not isinstance(values, list):
        raise _error("Application environment is invalid")
    environment: dict[str, str] = {}
    for entry in values:
        if not isinstance(entry, str) or "=" not in entry:
            raise _error("Application environment is invalid")
        key, value = entry.split("=", 1)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or key in environment:
            raise _error("Application environment is invalid")
        environment[key] = value
    database_url = environment.get("DATABASE_URL")
    if not database_url:
        raise _error("Application DATABASE_URL is unavailable")
    return {
        "container_id": container_id,
        "image": image,
        "network_id": network_id,
        "database_url": database_url,
    }


def _parse_database_url(value: str) -> dict[str, Any]:
    if not isinstance(value, str) or _CONTROL_RE.search(value):
        raise _error("Application database URL is invalid")
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise _error("Application database URL is invalid") from None
    if parsed.scheme not in {"mysql", "mysql+pymysql", "mysql+aiomysql"}:
        raise _error("Application database URL is not MySQL")
    if parsed.fragment or not parsed.hostname or not parsed.username:
        raise _error("Application database URL is invalid")
    try:
        query = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise _error("Application database URL is invalid") from None
    allowed_query = {
        "charset",
        "collation",
        "connect_timeout",
        "read_timeout",
        "write_timeout",
    }
    if any(
        key not in allowed_query or not value or _CONTROL_RE.search(value)
        for key, value in query
    ):
        raise _error("Application database URL query is invalid")
    if parsed.password is None:
        raise _error("Application database URL has no database password")
    try:
        host = parsed.hostname.casefold().rstrip(".")
        explicit_port = parsed.port
        port = explicit_port or 3306
    except ValueError:
        raise _error("Application database URL is invalid") from None
    database = unquote(parsed.path.removeprefix("/"))
    user = unquote(parsed.username)
    password = unquote(parsed.password)
    if (
        not host
        or not _DATABASE_RE.fullmatch(database)
        or _USER_RE.fullmatch(user) is None
        or not password
        or not 1 <= port <= 65535
        or _CONTROL_RE.search(host + database + user + password)
    ):
        raise _error("Application database URL is invalid")
    return {
        "scheme": parsed.scheme,
        "host": host,
        "port": port,
        "port_explicit": explicit_port is not None,
        "database": database,
        "user": user,
        "password": password,
    }


def database_identity_sha256(database_url: str) -> str:
    """Return the app-compatible identity without credentials or query data."""
    target = _parse_database_url(database_url)
    scheme = (
        "mysql+pymysql" if target["scheme"] == "mysql+aiomysql" else target["scheme"]
    )
    port = f":{target['port']}" if target["port_explicit"] else ""
    canonical = f"{scheme}://{target['host']}{port}/{target['database']}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_mysql_env(path: Path, values: Mapping[str, str]) -> None:
    if not values or any(
        not isinstance(key, str)
        or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is None
        or not isinstance(value, str)
        or _CONTROL_RE.search(value)
        for key, value in values.items()
    ):
        raise _error("Temporary MySQL credentials are invalid")
    # Docker's env-file parser consumes one KEY=value per line.  Newlines are
    # rejected above so a password cannot inject an additional variable.
    payload = "".join(f"{key}={value}\n" for key, value in values.items()).encode()
    _secure_create(path, payload)


def build_mysqldump_command(
    *,
    network: str,
    mysql_image: str,
    credentials_file: Path,
    host: str,
    port: int,
    user: str,
    database: str,
) -> list[str]:
    """Build a password-free, consistent dump command for test inspection."""
    _validate_network(network)
    _validate_mysql_image(mysql_image)
    credentials = _require_absolute(credentials_file, label="Credentials file")
    if _CONTROL_RE.search(host) or not 1 <= port <= 65535:
        raise _error("MySQL dump target is invalid")
    if _USER_RE.fullmatch(user) is None or _DATABASE_RE.fullmatch(database) is None:
        raise _error("MySQL dump target is invalid")
    return [
        "docker",
        "run",
        "--rm",
        "--network",
        network,
        "--env-file",
        str(credentials),
        mysql_image,
        "mysqldump",
        *_DUMP_OPTIONS,
        f"--host={host}",
        f"--port={port}",
        f"--user={user}",
        database,
    ]


def _build_mysql_query_command(
    *,
    network: str,
    mysql_image: str,
    credentials_file: Path,
    host: str,
    port: int,
    user: str,
    database: str,
    query: str,
) -> list[str]:
    if not query or _CONTROL_RE.search(query):
        raise _error("MySQL query is invalid")
    command = build_mysqldump_command(
        network=network,
        mysql_image=mysql_image,
        credentials_file=credentials_file,
        host=host,
        port=port,
        user=user,
        database=database,
    )
    return [
        *command[: command.index("mysqldump")],
        "mysql",
        "--protocol=tcp",
        "--batch",
        "--raw",
        "--skip-column-names",
        "--binary-mode",
        f"--host={host}",
        f"--port={port}",
        f"--user={user}",
        f"--database={database}",
        "--execute",
        query,
    ]


def _mysql_query(
    *,
    target: Mapping[str, Any],
    network: str,
    mysql_image: str,
    credentials_file: Path,
    query: str,
    runner: Runner | None = None,
) -> str:
    result = _run_command(
        _build_mysql_query_command(
            network=network,
            mysql_image=mysql_image,
            credentials_file=credentials_file,
            host=str(target["host"]),
            port=int(target["port"]),
            user=str(target["user"]),
            database=str(target["database"]),
            query=query,
        ),
        runner=runner,
    )
    return _decode_output(result)


def _quote_identifier(value: str) -> str:
    if not value or _CONTROL_RE.search(value):
        raise _error("Database identifier is invalid")
    return "`" + value.replace("`", "``") + "`"


def _quote_sql_string(value: str) -> str:
    if _CONTROL_RE.search(value):
        raise _error("Database string is invalid")
    return "'" + value.replace("'", "''") + "'"


def _query_lines(output: str) -> list[list[str]]:
    lines: list[list[str]] = []
    for raw in output.splitlines():
        if not raw:
            continue
        fields = raw.split("\t")
        if any(_CONTROL_RE.search(field) for field in fields):
            raise _error("Database query returned unsafe identifiers")
        lines.append(fields)
    return lines


def _read_revision(
    *,
    target: Mapping[str, Any],
    network: str,
    mysql_image: str,
    credentials_file: Path,
    runner: Runner | None,
) -> str:
    output = _mysql_query(
        target=target,
        network=network,
        mysql_image=mysql_image,
        credentials_file=credentials_file,
        query="SELECT version_num FROM alembic_version",
        runner=runner,
    )
    rows = _query_lines(output)
    if len(rows) != 1 or len(rows[0]) != 1:
        raise _error("Current Alembic revision is unavailable")
    revision = rows[0][0]
    if (
        not revision
        or len(revision) > _MAX_REVISION_LENGTH
        or _CONTROL_RE.search(revision)
    ):
        raise _error("Current Alembic revision is invalid")
    return revision


def _read_database_name(
    *,
    target: Mapping[str, Any],
    network: str,
    mysql_image: str,
    credentials_file: Path,
    runner: Runner | None,
) -> None:
    output = _mysql_query(
        target=target,
        network=network,
        mysql_image=mysql_image,
        credentials_file=credentials_file,
        query="SELECT DATABASE()",
        runner=runner,
    )
    rows = _query_lines(output)
    if len(rows) != 1 or rows[0] != [target["database"]]:
        raise _error("Database URL does not identify the current database")


def _capture_snapshot(
    *,
    target: Mapping[str, Any],
    network: str,
    mysql_image: str,
    credentials_file: Path,
    runner: Runner | None,
) -> dict[str, Any]:
    table_output = _mysql_query(
        target=target,
        network=network,
        mysql_image=mysql_image,
        credentials_file=credentials_file,
        query=(
            "SELECT TABLE_NAME,TABLE_TYPE,ENGINE FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_TYPE IN ('BASE TABLE','VIEW') "
            "ORDER BY TABLE_NAME"
        ),
        runner=runner,
    )
    table_rows = _query_lines(table_output)
    tables: dict[str, Any] = {}
    tenants: set[int] = set()
    blob_digests: list[str] = []
    for table_row in table_rows:
        if len(table_row) != 3 or table_row[1] not in {"BASE TABLE", "VIEW"}:
            raise _error("Database table inventory is invalid")
        table_name, table_type, engine = table_row
        if table_type == "BASE TABLE" and engine != "InnoDB":
            raise _error("Every backed-up production table must use InnoDB")
        if not table_name or _CONTROL_RE.search(table_name):
            raise _error("Database table inventory is invalid")
        columns_output = _mysql_query(
            target=target,
            network=network,
            mysql_image=mysql_image,
            credentials_file=credentials_file,
            query=(
                "SELECT COLUMN_NAME,DATA_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME="
                f"{_quote_sql_string(table_name)} "
                "ORDER BY ORDINAL_POSITION"
            ),
            runner=runner,
        )
        column_rows = _query_lines(columns_output)
        if not column_rows or any(len(row) != 2 or not row[0] for row in column_rows):
            raise _error("Database column inventory is invalid")
        columns = [row[0] for row in column_rows]
        data_types = [row[1] for row in column_rows]
        expressions = ",".join(
            "CASE WHEN {column} IS NULL THEN 'N' ELSE CONCAT('V',HEX({column})) END".format(
                column=_quote_identifier(column)
            )
            for column in columns
        )
        row_output = _mysql_query(
            target=target,
            network=network,
            mysql_image=mysql_image,
            credentials_file=credentials_file,
            query=(
                f"SELECT CONCAT_WS(CHAR(31),{expressions}) "
                f"FROM {_quote_identifier(table_name)}"
            ),
            runner=runner,
        )
        encoded_rows: list[list[str]] = []
        for line in row_output.splitlines():
            if not line:
                continue
            fields = line.split("\x1f")
            if len(fields) != len(columns) or any(
                not re.fullmatch(r"N|V[0-9A-Fa-f]*", field) for field in fields
            ):
                raise _error("Database row snapshot is invalid")
            encoded_rows.append(fields)
            for column, field, data_type in zip(
                columns, fields, data_types, strict=True
            ):
                if column.casefold() == "tenant_id" and field.startswith("V"):
                    try:
                        tenant = int(bytes.fromhex(field[1:]).decode("ascii"))
                    except (ValueError, UnicodeDecodeError):
                        raise _error("Tenant boundary value is invalid") from None
                    if tenant < 0:
                        raise _error("Tenant boundary value is invalid")
                    tenants.add(tenant)
                if any(
                    token in data_type.casefold() for token in ("blob", "binary")
                ) and field.startswith("V"):
                    blob_digests.append(
                        hashlib.sha256(bytes.fromhex(field[1:])).hexdigest()
                    )
        encoded_rows.sort()
        tables[table_name] = {
            "type": table_type,
            "engine": engine,
            "columns": [
                {"name": name, "data_type": data_type}
                for name, data_type in zip(columns, data_types, strict=True)
            ],
            "rows": encoded_rows,
        }
    return {
        "tables": tables,
        "tenant_ids": sorted(tenants),
        "blob_sha256": sorted(blob_digests),
    }


def _compare_snapshots(source: Mapping[str, Any], restored: Mapping[str, Any]) -> None:
    if source.get("tables") != restored.get("tables"):
        raise _error("Restored table or row contents do not match source")
    if source.get("tenant_ids") != restored.get("tenant_ids"):
        raise _error("Restored tenant boundary does not match source")
    if source.get("blob_sha256") != restored.get("blob_sha256"):
        raise _error("Restored BLOB contents do not match source")


def _write_dump(
    destination: Path,
    *,
    target: Mapping[str, Any],
    network: str,
    mysql_image: str,
    credentials_file: Path,
    runner: Runner | None,
) -> None:
    _secure_create(destination)
    try:
        _run_command(
            build_mysqldump_command(
                network=network,
                mysql_image=mysql_image,
                credentials_file=credentials_file,
                host=str(target["host"]),
                port=int(target["port"]),
                user=str(target["user"]),
                database=str(target["database"]),
            ),
            runner=runner,
            output_path=destination,
        )
        if destination.stat().st_size == 0:
            raise _error("MySQL dump is empty")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def _build_restore_network_name() -> str:
    return f"r5p-backup-{uuid.uuid4().hex[:24]}"


def _build_restore_container_name() -> str:
    return f"r5p-mysql-{uuid.uuid4().hex[:24]}"


def _restore_mysql(
    *,
    dump: Path,
    source_snapshot: Mapping[str, Any],
    source_revision: str,
    production_network: str,
    mysql_image: str,
    run_dir: Path,
    runner: Runner | None,
) -> dict[str, Any]:
    # Random credentials are kept in a 0600 env-file.  They are never part of
    # a Docker argv element and are removed in the caller's finally block.
    restore_network = _build_restore_network_name()
    restore_container = _build_restore_container_name()
    restore_env = run_dir / ".restore-mysql.env.tmp"
    database = f"r5_restore_{uuid.uuid4().hex[:16]}"
    user = "r5_restore"
    root_password = _secrets.token_urlsafe(32)
    _write_mysql_env(
        restore_env,
        {
            "MYSQL_ROOT_PASSWORD": root_password,
            "MYSQL_DATABASE": database,
            "MYSQL_USER": user,
            "MYSQL_PASSWORD": _secrets.token_urlsafe(32),
            # The server's healthcheck and all client commands consume
            # MYSQL_PWD; MYSQL_ROOT_PASSWORD is an entrypoint setting only.
            "MYSQL_PWD": root_password,
        },
    )
    created_network = False
    created_container = False
    try:
        if production_network == restore_network:
            raise _error("Restore network collides with production network")
        created_network = True
        _run_command(
            [
                "docker",
                "network",
                "create",
                "--internal",
                "--label",
                "com.kindergarten-manager.r5p=backup-restore",
                restore_network,
            ],
            runner=runner,
        )
        created_container = True
        _run_command(
            [
                "docker",
                "run",
                "--detach",
                "--name",
                restore_container,
                "--network",
                restore_network,
                "--tmpfs",
                "/var/lib/mysql:rw,noexec,nosuid,nodev",
                "--tmpfs",
                "/run/mysqld:rw,noexec,nosuid,nodev",
                "--env-file",
                str(restore_env),
                mysql_image,
                "--log-bin-trust-function-creators=1",
            ],
            runner=runner,
        )
        restore_target = {
            "host": restore_container,
            "port": 3306,
            "database": database,
            "user": "root",
            "password": "",
        }
        deadline = time.monotonic() + _READY_TIMEOUT
        ready = False
        while time.monotonic() < deadline:
            probe = _run_command(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    restore_network,
                    "--env-file",
                    str(restore_env),
                    mysql_image,
                    "mysqladmin",
                    "ping",
                    "--protocol=tcp",
                    f"--host={restore_container}",
                    "--user=root",
                    "--silent",
                ],
                runner=runner,
                check=False,
                timeout=15,
            )
            if probe.returncode == 0:
                ready = True
                break
            time.sleep(1)
        if not ready:
            raise _error("Isolated MySQL did not become ready")
        table_output = _mysql_query(
            target=restore_target,
            network=restore_network,
            mysql_image=mysql_image,
            credentials_file=restore_env,
            query="SHOW TABLES",
            runner=runner,
        )
        if _query_lines(table_output):
            raise _error("Isolated restore target was not fresh")
        _run_command(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                restore_network,
                "--env-file",
                str(restore_env),
                mysql_image,
                "mysql",
                "--protocol=tcp",
                "--binary-mode",
                "--host=" + restore_container,
                "--user=root",
                "--database=" + database,
            ],
            runner=runner,
            input_path=dump,
        )
        restored_snapshot = _capture_snapshot(
            target=restore_target,
            network=restore_network,
            mysql_image=mysql_image,
            credentials_file=restore_env,
            runner=runner,
        )
        _compare_snapshots(source_snapshot, restored_snapshot)
        restored_revision = _read_revision(
            target=restore_target,
            network=restore_network,
            mysql_image=mysql_image,
            credentials_file=restore_env,
            runner=runner,
        )
        if restored_revision != source_revision:
            raise _error("Restored Alembic revision does not match source")
        return restored_snapshot
    finally:
        restore_env.unlink(missing_ok=True)
        # Only the random, label-scoped container and network are cleaned up;
        # no volume, production network, or broad Docker prune is attempted.
        cleanup_error = False
        if created_container:
            try:
                _run_command(
                    ["docker", "rm", "--force", restore_container],
                    runner=runner,
                    timeout=30,
                )
            except ProductionMySQLBackupError:
                cleanup_error = True
        if created_network:
            try:
                _run_command(
                    ["docker", "network", "rm", restore_network],
                    runner=runner,
                    timeout=30,
                )
            except ProductionMySQLBackupError:
                cleanup_error = True
        if cleanup_error:
            raise _error("Isolated MySQL cleanup failed")


def _stage_templates_from_app(
    *,
    app_container: str,
    run_dir: Path,
    runner: Runner | None,
) -> Path:
    source = run_dir / ".container-templates.tmp"
    source.mkdir(mode=0o700)
    try:
        for name in _TEMPLATE_NAMES:
            destination = source / name
            _run_command(
                [
                    "docker",
                    "cp",
                    f"{app_container}:/app/templates/{name}",
                    str(destination),
                ],
                runner=runner,
                timeout=60,
            )
            # ``docker cp`` may create files owned by root.  They are copied
            # immediately into an owner-only staging file and never archived
            # through a path supplied by the container.
            info = destination.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise _error("Application template is not a regular file")
        return source
    except BaseException:
        shutil.rmtree(source, ignore_errors=True)
        raise


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _manifest(
    *,
    identity: str,
    revision: str,
    database_size: int,
    database_sha256: str,
    assets: Sequence[tuple[str, Path, int, str]],
) -> dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "kind": "kindergarten-manager-backup",
        "database": {
            "backend": "mysql",
            "path": _DATABASE_NAME,
            "identity_sha256": identity,
            "revision": revision,
            "size_bytes": database_size,
            "sha256": database_sha256,
        },
        "assets": [
            {"path": name, "size_bytes": size, "sha256": digest}
            for name, _, size, digest in sorted(assets, key=lambda item: item[0])
        ],
    }


def _evidence(
    *,
    artifact: Path,
    protected_image: str,
    identity: str,
    revision: str,
    created: datetime,
) -> dict[str, Any]:
    size, digest = _file_digest(artifact)
    return {
        "schema_version": 1,
        "status": "verified",
        "created_at": _utc(created),
        "expires_at": _utc(created + _VALIDITY),
        "protected_image": protected_image,
        "database_identity_sha256": identity,
        "database_revision": revision,
        "artifact": {
            "path": str(artifact.resolve()),
            "size_bytes": size,
            "sha256": digest,
        },
        "checks": {
            "database_integrity": "passed",
            "isolated_restore": "passed",
            "required_assets": "passed",
        },
    }


def _write_json_file(path: Path, payload: Mapping[str, Any]) -> None:
    raw = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        _secure_create(temporary, raw)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except BaseException:
        temporary.unlink(missing_ok=True)
        path.unlink(missing_ok=True)
        raise


def create_mysql_production_backup_attestation(
    *,
    app_container: str,
    network: str,
    mysql_image: str,
    backup_root: Path,
    secrets_path: Path,
    exports_source: Path,
    protected_image: str,
    templates_source: Path | None = None,
    now: datetime | None = None,
    runner: Runner | None = None,
) -> Path:
    """Create a production MySQL ``backup-evidence.json``.

    ``database_identity_sha256`` and ``database_revision`` intentionally do
    not appear in this signature.  Both facts come from the app container and
    live source database, then are re-read from the fresh isolated restore.
    ``runner`` exists only for deterministic unit tests; the production CLI
    uses the real Docker subprocess.
    """
    app_container = _validate_container(app_container, label="Application container")
    network = _validate_network(network)
    mysql_image = _validate_mysql_image(mysql_image)
    protected_image = _validate_image(protected_image, label="Protected image")
    root = _ensure_backup_root(backup_root)
    secrets_path = _validate_file(secrets_path, label="Secrets file", owner_only=True)
    exports_source = _validate_directory(exports_source, label="Exports source")
    if templates_source is not None:
        templates_source = _validate_directory(
            templates_source, label="Templates source"
        )
        _ensure_disjoint(root, secrets_path, exports_source, templates_source)
    else:
        _ensure_disjoint(root, secrets_path, exports_source)
    created = now or datetime.now(UTC)
    if created.tzinfo is None:
        raise _error("Backup time must be timezone-aware")
    created = created.astimezone(UTC)
    app_facts = _app_facts(app_container, network, runner=runner)
    if app_facts["image"] != protected_image:
        raise _error("Protected image does not match the running application")
    database_url = app_facts["database_url"]
    target = _parse_database_url(database_url)
    identity = database_identity_sha256(database_url)

    run_dir = _create_run_directory(root)
    source_env = run_dir / ".source-mysql.env.tmp"
    dump = run_dir / ".database.sql.tmp"
    artifact_tmp = run_dir / f".{_ARCHIVE_NAME}.tmp"
    artifact = run_dir / _ARCHIVE_NAME
    evidence = run_dir / _EVIDENCE_NAME
    staged_paths: list[Path] = []
    template_tmp: Path | None = None
    try:
        _write_mysql_env(source_env, {"MYSQL_PWD": target["password"]})
        _read_database_name(
            target=target,
            network=network,
            mysql_image=mysql_image,
            credentials_file=source_env,
            runner=runner,
        )
        source_revision = _read_revision(
            target=target,
            network=network,
            mysql_image=mysql_image,
            credentials_file=source_env,
            runner=runner,
        )
        source_snapshot_before = _capture_snapshot(
            target=target,
            network=network,
            mysql_image=mysql_image,
            credentials_file=source_env,
            runner=runner,
        )
        _write_dump(
            dump,
            target=target,
            network=network,
            mysql_image=mysql_image,
            credentials_file=source_env,
            runner=runner,
        )
        source_snapshot_after = _capture_snapshot(
            target=target,
            network=network,
            mysql_image=mysql_image,
            credentials_file=source_env,
            runner=runner,
        )
        if source_snapshot_before != source_snapshot_after:
            raise _error("Source database changed during backup")
        source_revision_after = _read_revision(
            target=target,
            network=network,
            mysql_image=mysql_image,
            credentials_file=source_env,
            runner=runner,
        )
        if source_revision_after != source_revision:
            raise _error("Source Alembic revision changed during backup")
        if _app_facts(app_container, network, runner=runner) != app_facts:
            raise _error("Application/database binding changed during backup")

        database_size, database_sha256 = _file_digest(dump)
        staged: list[tuple[str, Path, int, str]] = [
            ("database.sql", dump, database_size, database_sha256)
        ]
        secret_stage = run_dir / ".asset-secrets.tmp"
        staged_paths.append(secret_stage)
        secret_size, secret_digest = _copy_input(
            secrets_path, secret_stage, label="Secrets file"
        )
        staged.append((_SECRET_MEMBER, secret_stage, secret_size, secret_digest))

        if templates_source is None:
            template_tmp = _stage_templates_from_app(
                app_container=app_facts["container_id"],
                run_dir=run_dir,
                runner=runner,
            )
            templates_source = template_tmp
        for index, (archive_name, source_path) in enumerate(
            _collect_templates(
                templates_source,
                allow_foreign_owner=template_tmp is not None,
            )
        ):
            destination = run_dir / f".asset-template-{index:02d}.tmp"
            staged_paths.append(destination)
            size, digest = _copy_input(
                source_path,
                destination,
                label="Template file",
                allow_foreign_owner=template_tmp is not None,
            )
            staged.append((archive_name, destination, size, digest))
        for index, (archive_name, source_path) in enumerate(
            _iter_export_files(exports_source)
        ):
            destination = run_dir / f".asset-export-{index:05d}.tmp"
            staged_paths.append(destination)
            size, digest = _copy_input(source_path, destination, label="Export file")
            staged.append((archive_name, destination, size, digest))

        if _app_facts(app_container, network, runner=runner) != app_facts:
            raise _error("Application/database binding changed during asset staging")

        manifest = _manifest(
            identity=identity,
            revision=source_revision,
            database_size=database_size,
            database_sha256=database_sha256,
            assets=staged[1:],
        )
        _write_archive(artifact_tmp, staged, manifest)
        _verify_archive(artifact_tmp, expected_manifest=manifest)
        _restore_mysql(
            dump=dump,
            source_snapshot=source_snapshot_before,
            source_revision=source_revision,
            production_network=network,
            mysql_image=mysql_image,
            run_dir=run_dir,
            runner=runner,
        )
        os.replace(artifact_tmp, artifact)
        os.chmod(artifact, 0o600)
        _verify_archive(artifact, expected_manifest=manifest)
        _write_json_file(
            evidence,
            _evidence(
                artifact=artifact,
                protected_image=protected_image,
                identity=identity,
                revision=source_revision,
                created=created,
            ),
        )
        # Remove all temporary files only after both consumer-visible files
        # have been atomically committed.
        for child in list(run_dir.iterdir()):
            if child.name not in {_ARCHIVE_NAME, _EVIDENCE_NAME}:
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                else:
                    child.unlink(missing_ok=True)
        return evidence
    except BaseException as exc:
        # No partial evidence/artifact may survive any failure.  The run root
        # is random and was created by us; the caller's backup root is kept.
        _cleanup_run_directory(run_dir)
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        if isinstance(exc, ProductionMySQLBackupError):
            raise
        raise _error("Production MySQL backup failed") from None
    finally:
        try:
            source_env.unlink(missing_ok=True)
        except OSError:
            raise _error(f"Backup cleanup required at {run_dir}") from None


# Concise alias for callers that use the operation name rather than the
# evidence terminology.  Both names intentionally have the same closed API.
create_production_mysql_backup = create_mysql_production_backup_attestation


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Produce a fresh, isolated-restore-verified production MySQL backup."
    )
    parser.add_argument("--app-container", required=True)
    parser.add_argument("--network", required=True)
    parser.add_argument("--mysql-image", required=True)
    parser.add_argument("--backup-root", required=True, type=Path)
    parser.add_argument("--secrets-path", required=True, type=Path)
    parser.add_argument("--exports-source", required=True, type=Path)
    parser.add_argument("--templates-source", type=Path)
    parser.add_argument("--protected-image", required=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate static inputs only; never inspect Docker or emit evidence.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        _validate_container(args.app_container, label="Application container")
        _validate_network(args.network)
        _validate_mysql_image(args.mysql_image)
        _validate_image(args.protected_image, label="Protected image")
        if args.dry_run:
            _require_absolute(args.backup_root, label="Backup root")
            _require_absolute(args.secrets_path, label="Secrets file")
            _require_absolute(args.exports_source, label="Exports source")
            if args.templates_source is not None:
                _require_absolute(args.templates_source, label="Templates source")
            print("DRY_RUN: no image binding or backup evidence generated")
            return 0
        evidence = create_mysql_production_backup_attestation(
            app_container=args.app_container,
            network=args.network,
            mysql_image=args.mysql_image,
            backup_root=args.backup_root,
            secrets_path=args.secrets_path,
            exports_source=args.exports_source,
            templates_source=args.templates_source,
            protected_image=args.protected_image,
        )
        print(str(evidence))
        return 0
    except ProductionMySQLBackupError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
