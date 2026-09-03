"""SQLite backup, isolated restore, and attestation production.

This module deliberately owns the complete ``backup -> restore -> evidence``
chain for the first R5-R slice.  The public producer does not accept any
attestation facts from its caller: the database identity, schema revision,
checks, artifact checksum, and status are derived here from the files that
are actually backed up and restored.

The archive format is intentionally small and closed.  It is not a general
archive extractor and must not be used for arbitrary user supplied ZIP files.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import uuid
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO
from urllib.parse import quote

from app.core.backup_evidence import (
    IMAGE_RE,
    NO_RUNNING_IMAGE,
    VerifiedBackupEvidence,
    validate_backup_evidence,
)


class BackupRestoreError(RuntimeError):
    """A backup or isolated restore cannot be completed safely."""


_ARCHIVE_NAME = "sqlite-backup-v1.zip"
_EVIDENCE_NAME = "backup-evidence.json"
_DATABASE_NAME = "database.sqlite3"
_MYSQL_DATABASE_NAME = "database.sql"
_MANIFEST_NAME = "manifest.json"
_MANIFEST_SCHEMA_VERSION = 1
_MANIFEST_KIND = "kindergarten-manager-backup"
_MAX_MANIFEST_BYTES = 1024 * 1024
_MAX_REVISION_LENGTH = 128
_VALIDITY = timedelta(hours=24)
_SECRETS_ARCHIVE_NAME = "secrets/.kindergarten_secrets"
_TEMPLATE_NAMES = (
    "teacherplan.docx",
    "ObservationRecord.docx",
    "OneOnOneListeningSmallSecond.docx",
    "homemadeteaching.docx",
    "coursereviewactivity.docx",
)
_TEMPLATE_ARCHIVE_NAMES = tuple(f"templates/{name}" for name in _TEMPLATE_NAMES)
_ASSET_FIELDS = {"path", "size_bytes", "sha256"}
_DATABASE_FIELDS = {
    "backend",
    "path",
    "identity_sha256",
    "revision",
    "size_bytes",
    "sha256",
}
_HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def create_sqlite_backup_attestation(
    source_database: Path,
    backup_root: Path,
    secrets_file: Path,
    exports_root: Path,
    templates_root: Path,
    protected_image: str,
    now: datetime | None = None,
) -> Path:
    """Create and verify a SQLite backup, returning its owner-only evidence.

    ``backup_root`` is the caller-owned retention root.  A fresh random run
    directory is created below it and is the only location touched by the
    operation.  The run is removed on every failure; an already existing root
    is never removed.
    """

    root = _ensure_backup_root(backup_root)
    source = _validated_file(source_database, label="Source database")
    secrets = _validated_file(secrets_file, label="Secrets file", require_0600=True)
    exports = _validated_directory(exports_root, label="Exports root")
    templates = _validated_directory(templates_root, label="Templates root")
    _ensure_paths_are_disjoint(
        root,
        source,
        secrets,
        exports,
        templates,
    )
    _validate_protected_image(protected_image)
    created = _normalise_creation_time(now)

    # Validate and freeze the source inventory before creating any run files.
    # The subsequent secure copies also check that each input remains the same
    # inode/size while it is read.
    export_sources = list(_iter_export_files(exports))
    template_sources = _collect_template_files(templates)

    run_dir = _create_run_directory(root)
    restore_root: Path | None = None
    try:
        snapshot = run_dir / ".database.sqlite3.tmp"
        _create_sqlite_snapshot(source, snapshot)
        database_size, database_sha256 = _file_digest(snapshot)
        database_revision = _read_sqlite_revision(snapshot)
        database_identity = _sqlite_identity(source)

        staged_files: list[tuple[str, Path, int, str]] = []
        staged_files.append(
            (
                _DATABASE_NAME,
                snapshot,
                database_size,
                database_sha256,
            )
        )

        for stage_index, (archive_name, source_path) in enumerate(
            (
                (_SECRETS_ARCHIVE_NAME, secrets),
                *template_sources,
                *export_sources,
            )
        ):
            stage_path = run_dir / f".asset-{stage_index:04d}.tmp"
            size, digest = _stage_regular_file(
                source_path, stage_path, label=archive_name
            )
            staged_files.append((archive_name, stage_path, size, digest))

        manifest = _build_manifest(
            database_identity=database_identity,
            database_revision=database_revision,
            database_size=database_size,
            database_sha256=database_sha256,
            assets=staged_files[1:],
        )
        manifest_bytes = _json_bytes(manifest)

        artifact_tmp = run_dir / f".{_ARCHIVE_NAME}.tmp"
        _write_archive(artifact_tmp, staged_files, manifest_bytes)
        artifact = run_dir / _ARCHIVE_NAME
        _atomic_replace(artifact_tmp, artifact)
        _ensure_owner_only_file(artifact, label="Backup artifact")

        # A consumer-visible attestation may only be emitted after a real,
        # fresh-directory restore has completed all of its checks.
        restore_root = run_dir / f"restore-{uuid.uuid4().hex}"
        restore_backup_artifact(artifact, restore_root)
        _remove_directory(restore_root)
        restore_root = None

        artifact_size, artifact_sha256 = _file_digest(artifact)
        evidence_payload = {
            "schema_version": 1,
            "status": "verified",
            "created_at": _utc_rfc3339(created),
            "expires_at": _utc_rfc3339(created + _VALIDITY),
            "protected_image": protected_image,
            "database_identity_sha256": database_identity,
            "database_revision": database_revision,
            "artifact": {
                "path": str(artifact.resolve()),
                "size_bytes": artifact_size,
                "sha256": artifact_sha256,
            },
            "checks": {
                "database_integrity": "passed",
                "isolated_restore": "passed",
                "required_assets": "passed",
            },
        }
        evidence_tmp = run_dir / f".{_EVIDENCE_NAME}.tmp"
        _write_secure_bytes(evidence_tmp, _json_bytes(evidence_payload))
        evidence = run_dir / _EVIDENCE_NAME
        _atomic_replace(evidence_tmp, evidence)
        _ensure_owner_only_file(evidence, label="Backup evidence")
        _fsync_directory(run_dir)

        # Temporary source snapshots/staged assets are not part of the
        # retention contract.  They are removed only after evidence is safely
        # renamed into place, leaving exactly the two controlled output files.
        for temporary in run_dir.iterdir():
            if temporary.name not in {_ARCHIVE_NAME, _EVIDENCE_NAME}:
                _remove_path(temporary)
        _fsync_directory(run_dir)
        return evidence
    except BaseException as exc:
        if restore_root is not None:
            _safe_remove_directory(restore_root)
        _safe_remove_directory(run_dir)
        if isinstance(exc, BackupRestoreError):
            raise
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise BackupRestoreError("SQLite backup production failed") from None


def restore_backup_artifact(artifact: Path, restore_root: Path) -> None:
    """Restore one verified-format archive into a brand-new directory.

    The destination must not exist before this call.  Every archive member is
    checked against the closed manifest before any destination is created; on
    any later failure the newly created destination is removed.
    """

    artifact_path = _validated_file(
        artifact, label="Backup artifact", require_0600=True
    )
    destination = _validated_new_destination(restore_root)
    _ensure_paths_are_disjoint(artifact_path, destination)

    restore_created = False
    try:
        with (
            _open_readonly(artifact_path, label="Backup artifact") as artifact_stream,
            zipfile.ZipFile(artifact_stream, mode="r") as archive,
        ):
            infos = _validate_zip_members(archive)
            manifest = _read_and_validate_manifest(archive, infos)
            expected = _validate_manifest_members(manifest, infos)

            _mkdir_secure(destination)
            restore_created = True
            extracted: dict[str, Path] = {}
            for archive_name in sorted(expected):
                if archive_name == _MANIFEST_NAME:
                    continue
                info = infos[archive_name]
                target = _safe_destination_path(destination, archive_name)
                _make_parent_directories(destination, target.parent)
                _extract_member(
                    archive,
                    info,
                    target,
                    expected[archive_name],
                )
                extracted[archive_name] = target

            database_target = extracted.get(_DATABASE_NAME)
            if database_target is None:
                raise BackupRestoreError("Backup database is missing")
            actual_size, actual_sha256 = _file_digest(database_target)
            database_manifest = manifest["database"]
            if (
                actual_size != database_manifest["size_bytes"]
                or actual_sha256 != database_manifest["sha256"]
            ):
                raise BackupRestoreError(
                    "Restored database checksum does not match manifest"
                )
            revision = _read_sqlite_revision(database_target)
            if revision != database_manifest["revision"]:
                raise BackupRestoreError(
                    "Restored database revision does not match manifest"
                )

            # Re-open and checksum every restored asset.  This is
            # intentionally separate from streaming extraction so the
            # post-write bytes, not only the ZIP stream, are attested.
            for archive_name, expected_asset in expected.items():
                if archive_name in {_MANIFEST_NAME, _DATABASE_NAME}:
                    continue
                target = extracted[archive_name]
                size, digest = _file_digest(target)
                if (
                    size != expected_asset["size_bytes"]
                    or digest != expected_asset["sha256"]
                ):
                    raise BackupRestoreError(
                        f"Restored asset checksum does not match manifest: {archive_name}"
                    )

            _assert_restore_contents(destination, set(extracted.values()))
    except BaseException as exc:
        if restore_created:
            _safe_remove_directory(destination)
        if isinstance(exc, BackupRestoreError):
            raise
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise BackupRestoreError("Backup restore failed") from None


def validate_generated_attestation(
    evidence_path: Path,
    *,
    expected_protected_image: str,
    now: datetime | None = None,
) -> VerifiedBackupEvidence:
    """Validate evidence against the producer-owned archive manifest.

    This is the deployment boundary: the database identity and revision are
    read from the evidence and independently matched to the immutable archive
    manifest.  They are never supplied by an operator.  SQLite archives are
    also restored into a fresh temporary directory so the consumer repeats
    the producer's integrity, revision, and asset checks.
    """

    verified = validate_backup_evidence(
        evidence_path,
        expected_protected_image=expected_protected_image,
        now=now,
    )
    manifest = _validated_attestation_manifest(verified.artifact_path)
    database = manifest["database"]
    if database["identity_sha256"] != verified.database_identity_sha256:
        raise BackupRestoreError(
            "Backup manifest database identity does not match evidence"
        )
    if database["revision"] != verified.database_revision:
        raise BackupRestoreError("Backup manifest revision does not match evidence")

    if database["backend"] == "sqlite":
        with tempfile.TemporaryDirectory(prefix="r5-r-attestation-") as temporary:
            restore_root = Path(temporary) / "restore"
            restore_backup_artifact(verified.artifact_path, restore_root)
    return verified


def _validated_attestation_manifest(artifact: Path) -> dict[str, Any]:
    artifact_path = _validated_file(
        artifact, label="Backup artifact", require_0600=True
    )
    try:
        with (
            _open_readonly(artifact_path, label="Backup artifact") as stream,
            zipfile.ZipFile(stream, mode="r") as archive,
        ):
            infos = _validate_zip_members(archive)
            manifest = _read_and_validate_manifest(archive, infos)
            expected = _validate_manifest_members(manifest, infos)
            _verify_archive_member_hashes(archive, infos, expected)
            return manifest
    except BackupRestoreError:
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile):
        raise BackupRestoreError("Backup producer provenance is invalid") from None


def _verify_archive_member_hashes(
    archive: zipfile.ZipFile,
    infos: dict[str, zipfile.ZipInfo],
    expected: dict[str, dict[str, Any]],
) -> None:
    for name, descriptor in expected.items():
        digest = hashlib.sha256()
        size = 0
        try:
            with archive.open(infos[name], mode="r") as stream:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    digest.update(chunk)
        except (OSError, RuntimeError, zipfile.BadZipFile):
            raise BackupRestoreError(
                f"Backup archive member cannot be verified: {name}"
            ) from None
        if (
            size != descriptor["size_bytes"]
            or digest.hexdigest() != descriptor["sha256"]
        ):
            raise BackupRestoreError(
                f"Backup archive member checksum does not match manifest: {name}"
            )


def _validate_protected_image(value: str) -> None:
    if value != NO_RUNNING_IMAGE and IMAGE_RE.fullmatch(value) is None:
        raise BackupRestoreError("Protected image is invalid")


def _normalise_creation_time(value: datetime | None) -> datetime:
    current = value if value is not None else datetime.now(UTC)
    if current.tzinfo is None:
        raise BackupRestoreError("Backup time must be timezone-aware")
    return current.astimezone(UTC)


def _utc_rfc3339(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _is_posix() -> bool:
    return os.name == "posix"


def _current_uid() -> int | None:
    return os.geteuid() if hasattr(os, "geteuid") else None


def _lexists(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _require_absolute(path: Path, *, label: str) -> Path:
    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_absolute():
        raise BackupRestoreError(f"{label} path must be absolute")
    return path


def _validated_file(
    path: Path,
    *,
    label: str,
    require_0600: bool = False,
) -> Path:
    candidate = _require_absolute(path, label=label)
    _reject_symlink_ancestors(candidate, label=label)
    try:
        info = candidate.lstat()
    except OSError:
        raise BackupRestoreError(f"{label} is unavailable") from None
    if stat.S_ISLNK(info.st_mode):
        raise BackupRestoreError(f"{label} must not be a symlink")
    if not stat.S_ISREG(info.st_mode):
        raise BackupRestoreError(f"{label} must be a regular file")
    uid = _current_uid()
    if uid is not None and info.st_uid != uid:
        raise BackupRestoreError(f"{label} must be owned by the current user")
    mode = stat.S_IMODE(info.st_mode)
    if require_0600 and _is_posix() and mode != 0o600:
        raise BackupRestoreError(f"{label} must have mode 0600")
    # Inputs may be readable by other users, but must never be writable by
    # them.  Secrets use the stricter exact-0600 check above.
    if _is_posix() and mode & 0o002:
        raise BackupRestoreError(f"{label} has unsafe permissions")
    return candidate.resolve()


def _validated_directory(path: Path, *, label: str) -> Path:
    candidate = _require_absolute(path, label=label)
    _reject_symlink_ancestors(candidate, label=label)
    try:
        info = candidate.lstat()
    except OSError:
        raise BackupRestoreError(f"{label} is unavailable") from None
    if stat.S_ISLNK(info.st_mode):
        raise BackupRestoreError(f"{label} must not be a symlink")
    if not stat.S_ISDIR(info.st_mode):
        raise BackupRestoreError(f"{label} must be a directory")
    uid = _current_uid()
    if uid is not None and info.st_uid != uid:
        raise BackupRestoreError(f"{label} must be owned by the current user")
    if _is_posix() and stat.S_IMODE(info.st_mode) & 0o002:
        raise BackupRestoreError(f"{label} has unsafe permissions")
    return candidate.resolve()


def _ensure_backup_root(path: Path) -> Path:
    candidate = _require_absolute(path, label="Backup root")
    _reject_symlink_ancestors(candidate, label="Backup root")
    if _lexists(candidate):
        root = _validated_directory(candidate, label="Backup root")
        # Tighten an existing directory rather than leaving a caller's broad
        # mode in place.  This is safe because it only removes access.
        if _is_posix() and stat.S_IMODE(root.stat().st_mode) != 0o700:
            try:
                os.chmod(root, 0o700)
            except OSError:
                raise BackupRestoreError("Backup root permissions are unsafe") from None
        return root
    parent = candidate.parent
    if not parent.exists() or not parent.is_dir() or parent.is_symlink():
        raise BackupRestoreError("Backup root parent is unavailable")
    try:
        os.mkdir(candidate, 0o700)
    except FileExistsError:
        return _ensure_backup_root(candidate)
    except OSError:
        raise BackupRestoreError("Backup root cannot be created") from None
    try:
        os.chmod(candidate, 0o700)
    except OSError:
        _safe_remove_directory(candidate)
        raise BackupRestoreError("Backup root permissions are unsafe") from None
    return candidate.resolve()


def _ensure_paths_are_disjoint(*paths: Path) -> None:
    resolved = [path.resolve(strict=False) for path in paths]
    for index, first in enumerate(resolved):
        for second in resolved[index + 1 :]:
            if (
                first == second
                or first.is_relative_to(second)
                or second.is_relative_to(first)
            ):
                raise BackupRestoreError("Backup paths must be separate")


def _create_run_directory(root: Path) -> Path:
    for _ in range(16):
        candidate = root / f"run-{uuid.uuid4().hex}"
        try:
            os.mkdir(candidate, 0o700)
        except FileExistsError:
            continue
        except OSError:
            raise BackupRestoreError("Backup run directory cannot be created") from None
        try:
            os.chmod(candidate, 0o700)
        except OSError:
            _safe_remove_directory(candidate)
            raise BackupRestoreError(
                "Backup run directory permissions are unsafe"
            ) from None
        return candidate
    raise BackupRestoreError("Backup run directory name collision")


def _validated_new_destination(path: Path) -> Path:
    candidate = _require_absolute(path, label="Restore root")
    _reject_symlink_ancestors(candidate, label="Restore root")
    if _lexists(candidate):
        raise BackupRestoreError("Restore root must be a new directory")
    parent = candidate.parent
    if not parent.exists() or not parent.is_dir() or parent.is_symlink():
        raise BackupRestoreError("Restore root parent is unavailable")
    return candidate.resolve(strict=False)


def _mkdir_secure(path: Path) -> None:
    try:
        os.mkdir(path, 0o700)
        os.chmod(path, 0o700)
    except OSError:
        _safe_remove_directory(path)
        raise BackupRestoreError("Restore root cannot be created securely") from None


def _reject_symlink_ancestors(path: Path, *, label: str) -> None:
    """Reject symlinked components before any path is opened or created."""

    current = Path(path.anchor) if path.anchor else Path()
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            # Once a component is absent, all later components are absent too
            # for a normal path lookup.  The caller will validate/create it.
            break
        except OSError:
            raise BackupRestoreError(f"{label} path cannot be inspected") from None
        if stat.S_ISLNK(info.st_mode):
            raise BackupRestoreError(f"{label} path must not contain symlinks")


def _open_secure_read(
    path: Path,
    *,
    label: str,
    require_0600: bool = True,
) -> tuple[int, os.stat_result]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise BackupRestoreError(f"{label} cannot be opened securely") from None
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode):
        os.close(descriptor)
        raise BackupRestoreError(f"{label} must be a regular file")
    uid = _current_uid()
    if uid is not None and info.st_uid != uid:
        os.close(descriptor)
        raise BackupRestoreError(f"{label} must be owned by the current user")
    if require_0600 and _is_posix() and stat.S_IMODE(info.st_mode) != 0o600:
        os.close(descriptor)
        raise BackupRestoreError(f"{label} must have mode 0600")
    return descriptor, info


class _OwnedReadHandle:
    def __init__(self, descriptor: int):
        self._descriptor = descriptor
        self._stream = os.fdopen(descriptor, "rb", closefd=True)

    def __enter__(self) -> BinaryIO:
        return self._stream

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self._stream.close()


def _open_readonly(path: Path, *, label: str) -> _OwnedReadHandle:
    descriptor, _ = _open_secure_read(path, label=label, require_0600=True)
    return _OwnedReadHandle(descriptor)


def _new_secure_file(path: Path) -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
        if _is_posix():
            os.fchmod(descriptor, 0o600)
        return descriptor
    except OSError:
        raise BackupRestoreError("Secure file cannot be created") from None


def _write_secure_bytes(path: Path, payload: bytes) -> None:
    descriptor = _new_secure_file(path)
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
    except BaseException:
        try:
            os.close(descriptor)
        finally:
            _safe_remove_path(path)
        raise
    os.close(descriptor)


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise BackupRestoreError("Secure file write failed")
        offset += written


def _atomic_replace(source: Path, target: Path) -> None:
    try:
        os.replace(source, target)
    except OSError:
        raise BackupRestoreError("Backup output cannot be finalized") from None


def _fsync_directory(path: Path) -> None:
    if not _is_posix():
        return
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sqlite_uri(path: Path, *, read_only: bool = False) -> str:
    encoded = quote(path.resolve().as_posix(), safe="/")
    suffix = "?mode=ro" if read_only else ""
    return f"file:{encoded}{suffix}"


def _create_sqlite_snapshot(source: Path, destination: Path) -> None:
    descriptor = _new_secure_file(destination)
    os.close(descriptor)
    source_connection: sqlite3.Connection | None = None
    destination_connection: sqlite3.Connection | None = None
    try:
        source_connection = sqlite3.connect(
            _sqlite_uri(source, read_only=True),
            uri=True,
            isolation_level=None,
            timeout=30.0,
        )
        destination_connection = sqlite3.connect(
            str(destination),
            isolation_level=None,
            timeout=30.0,
        )
        destination_connection.execute("PRAGMA journal_mode=DELETE")
        source_connection.backup(
            destination_connection,
            pages=128,
            progress=None,
            name="main",
            sleep=0.05,
        )
        destination_connection.execute("PRAGMA journal_mode=DELETE")
        destination_connection.commit()
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise BackupRestoreError("SQLite online backup failed") from None
    finally:
        if destination_connection is not None:
            destination_connection.close()
        if source_connection is not None:
            source_connection.close()
    _ensure_owner_only_file(destination, label="SQLite snapshot")


def _sqlite_identity(source: Path) -> str:
    # This is intentionally byte-for-byte equivalent to
    # app.core.startup.configured_database_identity_sha256 for a SQLite URL:
    # absolute path normalization, no credentials, no query parameters.
    normalized = f"sqlite:///{source.resolve().as_posix()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _read_sqlite_revision(database: Path) -> str:
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(
            _sqlite_uri(database, read_only=True),
            uri=True,
            isolation_level=None,
            timeout=30.0,
        )
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if integrity != ("ok",):
            raise BackupRestoreError("SQLite integrity check failed")
        rows = connection.execute("SELECT version_num FROM alembic_version").fetchall()
        if len(rows) != 1 or not isinstance(rows[0][0], str) or not rows[0][0]:
            raise BackupRestoreError("SQLite Alembic revision is unavailable")
        revision = rows[0][0]
        if len(revision) > _MAX_REVISION_LENGTH:
            raise BackupRestoreError("SQLite Alembic revision is invalid")
        return revision
    except BackupRestoreError:
        raise
    except (sqlite3.Error, OSError):
        raise BackupRestoreError("SQLite revision validation failed") from None
    finally:
        if connection is not None:
            connection.close()


def _file_digest(path: Path) -> tuple[int, str]:
    descriptor, _ = _open_secure_read(path, label="Backup file")
    digest = hashlib.sha256()
    size = 0
    try:
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    finally:
        os.close(descriptor)
    return size, digest.hexdigest()


def _stage_regular_file(
    source: Path, destination: Path, *, label: str
) -> tuple[int, str]:
    source_descriptor, source_info = _open_input_file(source, label=label)
    destination_descriptor = _new_secure_file(destination)
    digest = hashlib.sha256()
    size = 0
    try:
        while True:
            chunk = os.read(source_descriptor, 1024 * 1024)
            if not chunk:
                break
            _write_all(destination_descriptor, chunk)
            digest.update(chunk)
            size += len(chunk)
        final_info = os.fstat(source_descriptor)
        if (
            final_info.st_dev != source_info.st_dev
            or final_info.st_ino != source_info.st_ino
            or final_info.st_size != source_info.st_size
            or size != source_info.st_size
        ):
            raise BackupRestoreError(f"{label} changed while being backed up")
        os.fsync(destination_descriptor)
    except BaseException:
        try:
            os.close(destination_descriptor)
        finally:
            os.close(source_descriptor)
            _safe_remove_path(destination)
        raise
    os.close(destination_descriptor)
    os.close(source_descriptor)
    return size, digest.hexdigest()


def _open_input_file(path: Path, *, label: str) -> tuple[int, os.stat_result]:
    descriptor, info = _open_secure_read(path, label=label, require_0600=False)
    # _open_secure_read enforces output-file mode for artifacts.  Input assets
    # may be readable by others, so use its low-level equivalent here.
    if _is_posix() and stat.S_IMODE(info.st_mode) & 0o002:
        os.close(descriptor)
        raise BackupRestoreError(f"{label} has unsafe permissions")
    return descriptor, info


def _is_transient_name(name: str) -> bool:
    lower = name.lower()
    return (
        lower.startswith((".~lock.", "~$"))
        or lower in {".ds_store", "thumbs.db", ".directory"}
        or lower.endswith(
            (
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
        )
    )


def _is_cache_directory(name: str) -> bool:
    return name.lower() in {"cache", ".cache", "__pycache__"} or name.lower().endswith(
        ".cache"
    )


def _validate_archive_relative_path(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise BackupRestoreError(f"{label} path is invalid")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise BackupRestoreError(f"{label} path is invalid")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or any(part in {"", ".", ".."} for part in parsed.parts):
        raise BackupRestoreError(f"{label} path is invalid")
    if any(":" in part for part in parsed.parts):
        raise BackupRestoreError(f"{label} path is invalid")
    normalized = parsed.as_posix()
    if normalized != value:
        raise BackupRestoreError(f"{label} path is not normalized")
    return normalized


def _iter_export_files(root: Path) -> Iterator[tuple[str, Path]]:
    def walk(directory: Path, prefix: PurePosixPath) -> Iterator[tuple[str, Path]]:
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name)
        except OSError:
            raise BackupRestoreError("Exports root cannot be read") from None
        for entry in entries:
            entry_path = Path(entry.path)
            if entry.is_symlink():
                raise BackupRestoreError("Exports must not contain symlinks")
            if entry.is_dir(follow_symlinks=False):
                if _is_cache_directory(entry.name):
                    continue
                yield from walk(entry_path, prefix / entry.name)
            elif entry.is_file(follow_symlinks=False):
                if _is_transient_name(entry.name):
                    continue
                archive_path = _validate_archive_relative_path(
                    f"exports/{(prefix / entry.name).as_posix()}",
                    label="Export",
                )
                _validated_file(entry_path, label="Export file")
                yield archive_path, entry_path.resolve()
            else:
                raise BackupRestoreError("Exports must contain regular files only")

    yield from walk(root, PurePosixPath())


def _collect_template_files(root: Path) -> list[tuple[str, Path]]:
    expected = set(_TEMPLATE_NAMES)
    found: dict[str, Path] = {}
    try:
        with os.scandir(root) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
    except OSError:
        raise BackupRestoreError("Templates root cannot be read") from None
    for entry in entries:
        entry_path = Path(entry.path)
        if entry.is_symlink():
            raise BackupRestoreError("Templates must not contain symlinks")
        if entry.is_dir(follow_symlinks=False):
            if _is_cache_directory(entry.name):
                continue
            raise BackupRestoreError("Templates contain an unknown directory")
        if not entry.is_file(follow_symlinks=False):
            raise BackupRestoreError("Templates must contain regular files only")
        if _is_transient_name(entry.name):
            continue
        if entry.name not in expected:
            raise BackupRestoreError("Templates contain an unknown file")
        _validated_file(entry_path, label="Template file")
        found[entry.name] = entry_path.resolve()
    if set(found) != expected:
        raise BackupRestoreError("Required template is missing")
    return [(f"templates/{name}", found[name]) for name in _TEMPLATE_NAMES]


def _build_manifest(
    *,
    database_identity: str,
    database_revision: str,
    database_size: int,
    database_sha256: str,
    assets: list[tuple[str, Path, int, str]],
) -> dict[str, Any]:
    return {
        "schema_version": _MANIFEST_SCHEMA_VERSION,
        "kind": _MANIFEST_KIND,
        "database": {
            "backend": "sqlite",
            "path": _DATABASE_NAME,
            "identity_sha256": database_identity,
            "revision": database_revision,
            "size_bytes": database_size,
            "sha256": database_sha256,
        },
        "assets": [
            {"path": name, "size_bytes": size, "sha256": digest}
            for name, _, size, digest in sorted(assets, key=lambda item: item[0])
        ],
    }


def _json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o600) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def _write_archive(
    destination: Path,
    staged_files: list[tuple[str, Path, int, str]],
    manifest_bytes: bytes,
) -> None:
    descriptor = _new_secure_file(destination)
    try:
        with os.fdopen(descriptor, "w+b", closefd=True) as stream:
            with zipfile.ZipFile(
                stream, mode="w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                archive.writestr(_zip_info(_MANIFEST_NAME), manifest_bytes)
                for archive_name, source, _, _ in sorted(
                    staged_files, key=lambda item: item[0]
                ):
                    info = _zip_info(archive_name)
                    with (
                        archive.open(info, mode="w") as member,
                        source.open("rb") as source_stream,
                    ):
                        shutil.copyfileobj(source_stream, member, length=1024 * 1024)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException as exc:
        _safe_remove_path(destination)
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise BackupRestoreError("SQLite archive cannot be written") from None
    _ensure_owner_only_file(destination, label="Backup archive temporary")


def _ensure_owner_only_file(path: Path, *, label: str) -> None:
    try:
        info = path.lstat()
    except OSError:
        raise BackupRestoreError(f"{label} is unavailable") from None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise BackupRestoreError(f"{label} must be a regular file")
    uid = _current_uid()
    if uid is not None and info.st_uid != uid:
        raise BackupRestoreError(f"{label} must be owned by the current user")
    if _is_posix() and stat.S_IMODE(info.st_mode) != 0o600:
        raise BackupRestoreError(f"{label} must have mode 0600")


def _read_json_no_duplicates(raw: bytes) -> object:
    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise BackupRestoreError("Manifest contains duplicate fields")
            result[key] = value
        return result

    def invalid_constant(value: str) -> object:
        raise BackupRestoreError(f"Manifest contains invalid number: {value}")

    try:
        return json.loads(
            raw,
            object_pairs_hook=object_pairs,
            parse_constant=invalid_constant,
        )
    except BackupRestoreError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise BackupRestoreError("Manifest is invalid JSON") from None


def _validate_zip_members(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    infos: dict[str, zipfile.ZipInfo] = {}
    try:
        members = archive.infolist()
    except (OSError, zipfile.BadZipFile):
        raise BackupRestoreError("Backup archive is invalid") from None
    for info in members:
        name = _validate_archive_relative_path(info.filename, label="Archive member")
        if name in infos:
            raise BackupRestoreError("Backup archive contains duplicate members")
        if info.flag_bits & 0x1:
            raise BackupRestoreError("Encrypted archive members are not supported")
        if info.is_dir():
            raise BackupRestoreError("Backup archive must not contain directories")
        mode = (info.external_attr >> 16) & 0xFFFF
        if mode and stat.S_IFMT(mode) not in {0, stat.S_IFREG}:
            raise BackupRestoreError("Backup archive contains a non-regular member")
        if info.file_size < 0 or info.compress_size < 0:
            raise BackupRestoreError("Backup archive member size is invalid")
        infos[name] = info
    if _MANIFEST_NAME not in infos:
        raise BackupRestoreError("Backup manifest is missing")
    return infos


def _read_and_validate_manifest(
    archive: zipfile.ZipFile,
    infos: dict[str, zipfile.ZipInfo],
) -> dict[str, Any]:
    info = infos[_MANIFEST_NAME]
    if info.file_size > _MAX_MANIFEST_BYTES:
        raise BackupRestoreError("Backup manifest is too large")
    try:
        with archive.open(info, mode="r") as stream:
            raw = stream.read(_MAX_MANIFEST_BYTES + 1)
    except (OSError, RuntimeError, zipfile.BadZipFile):
        raise BackupRestoreError("Backup manifest cannot be read") from None
    if len(raw) > _MAX_MANIFEST_BYTES:
        raise BackupRestoreError("Backup manifest is too large")
    payload = _read_json_no_duplicates(raw)
    if not isinstance(payload, dict):
        raise BackupRestoreError("Backup manifest must be an object")
    if set(payload) != {"schema_version", "kind", "database", "assets"}:
        raise BackupRestoreError(
            "Backup manifest fields do not match the closed schema"
        )
    if payload["schema_version"] != _MANIFEST_SCHEMA_VERSION:
        raise BackupRestoreError("Backup manifest schema version is unsupported")
    if payload["kind"] != _MANIFEST_KIND:
        raise BackupRestoreError("Backup manifest kind is invalid")
    database = payload["database"]
    if not isinstance(database, dict) or set(database) != _DATABASE_FIELDS:
        raise BackupRestoreError("Backup manifest database fields are invalid")
    database_descriptors = {
        "sqlite": _DATABASE_NAME,
        "mysql": _MYSQL_DATABASE_NAME,
    }
    if (
        database.get("backend") not in database_descriptors
        or database.get("path") != database_descriptors[database["backend"]]
    ):
        raise BackupRestoreError("Backup manifest database descriptor is invalid")
    if (
        not isinstance(database["identity_sha256"], str)
        or _HEX_SHA256_RE.fullmatch(database["identity_sha256"]) is None
    ):
        raise BackupRestoreError("Backup manifest database identity is invalid")
    _validate_revision(database["revision"])
    _validate_size_and_hash(database, label="Backup manifest database")
    assets = payload["assets"]
    if not isinstance(assets, list):
        raise BackupRestoreError("Backup manifest assets are invalid")
    for asset in assets:
        if not isinstance(asset, dict) or set(asset) != _ASSET_FIELDS:
            raise BackupRestoreError("Backup manifest asset fields are invalid")
        _validate_asset_descriptor(asset)
    return payload


def _validate_revision(value: object) -> None:
    if not isinstance(value, str) or not value or len(value) > _MAX_REVISION_LENGTH:
        raise BackupRestoreError("Backup manifest revision is invalid")


def _validate_size_and_hash(value: dict[str, Any], *, label: str) -> None:
    size = value["size_bytes"]
    digest = value["sha256"]
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise BackupRestoreError(f"{label} size is invalid")
    if not isinstance(digest, str) or _HEX_SHA256_RE.fullmatch(digest) is None:
        raise BackupRestoreError(f"{label} checksum is invalid")


def _validate_asset_descriptor(value: dict[str, Any]) -> None:
    path = _validate_archive_relative_path(value["path"], label="Manifest asset")
    if path == _SECRETS_ARCHIVE_NAME or path in _TEMPLATE_ARCHIVE_NAMES:
        pass
    elif path.startswith("exports/") and len(path) > len("exports/"):
        if _is_transient_name(PurePosixPath(path).name):
            raise BackupRestoreError("Backup manifest contains a transient export")
        if any(_is_cache_directory(part) for part in PurePosixPath(path).parts[1:-1]):
            raise BackupRestoreError("Backup manifest contains a cached export")
    else:
        raise BackupRestoreError("Backup manifest asset path is not allowed")
    _validate_size_and_hash(value, label="Backup manifest asset")


def _validate_manifest_members(
    manifest: dict[str, Any],
    infos: dict[str, zipfile.ZipInfo],
) -> dict[str, dict[str, Any]]:
    assets = manifest["assets"]
    database_path = manifest["database"]["path"]
    expected: dict[str, dict[str, Any]] = {database_path: manifest["database"]}
    for asset in assets:
        path = asset["path"]
        if path in expected:
            raise BackupRestoreError("Backup manifest contains duplicate assets")
        expected[path] = asset
    if _SECRETS_ARCHIVE_NAME not in expected:
        raise BackupRestoreError("Backup manifest secrets asset is missing")
    if any(name not in expected for name in _TEMPLATE_ARCHIVE_NAMES):
        raise BackupRestoreError("Backup manifest template asset is missing")
    expected_names = set(expected) | {_MANIFEST_NAME}
    if set(infos) != expected_names:
        raise BackupRestoreError("Backup archive members do not match manifest")
    for name, descriptor in expected.items():
        info = infos[name]
        if info.file_size != descriptor["size_bytes"]:
            raise BackupRestoreError(
                f"Backup archive member size does not match manifest: {name}"
            )
    return expected


def _safe_destination_path(root: Path, archive_name: str) -> Path:
    relative = PurePosixPath(archive_name)
    target = root.joinpath(*relative.parts)
    try:
        target.relative_to(root)
    except ValueError:
        raise BackupRestoreError("Backup archive path escapes restore root") from None
    return target


def _make_parent_directories(root: Path, parent: Path) -> None:
    relative = parent.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if _lexists(current):
            if current.is_symlink() or not current.is_dir():
                raise BackupRestoreError("Restore path parent is unsafe")
            continue
        try:
            os.mkdir(current, 0o700)
            os.chmod(current, 0o700)
        except OSError:
            raise BackupRestoreError("Restore path parent cannot be created") from None


def _extract_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    target: Path,
    descriptor: dict[str, Any],
) -> None:
    output_descriptor = _new_secure_file(target)
    digest = hashlib.sha256()
    size = 0
    try:
        with archive.open(info, mode="r") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > descriptor["size_bytes"]:
                    raise BackupRestoreError("Backup member exceeds manifest size")
                _write_all(output_descriptor, chunk)
                digest.update(chunk)
        if (
            size != descriptor["size_bytes"]
            or digest.hexdigest() != descriptor["sha256"]
        ):
            raise BackupRestoreError(
                f"Backup member checksum does not match manifest: {info.filename}"
            )
        os.fsync(output_descriptor)
    except BaseException:
        try:
            os.close(output_descriptor)
        finally:
            _safe_remove_path(target)
        raise
    os.close(output_descriptor)
    _ensure_owner_only_file(target, label="Restored file")


def _assert_restore_contents(root: Path, expected_files: set[Path]) -> None:
    actual: set[Path] = set()
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in dirnames:
            path = directory_path / name
            if path.is_symlink():
                raise BackupRestoreError("Restore contains a symlink")
        for name in filenames:
            path = directory_path / name
            actual.add(path)
            _ensure_owner_only_file(path, label="Restored file")
    if actual != expected_files:
        raise BackupRestoreError("Restore contains unexpected files")


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _safe_remove_path(path: Path) -> None:
    try:
        if _lexists(path) and not path.is_dir():
            path.unlink()
    except OSError:
        pass


def _remove_directory(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink() or not path.is_dir():
        raise BackupRestoreError("Temporary restore path is unsafe")
    shutil.rmtree(path)


def _safe_remove_directory(path: Path) -> None:
    try:
        if _lexists(path) and path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
    except OSError:
        pass


__all__ = [
    "BackupRestoreError",
    "create_sqlite_backup_attestation",
    "restore_backup_artifact",
]
