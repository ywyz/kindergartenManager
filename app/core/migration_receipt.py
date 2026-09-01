"""Closed, owner-only receipt binding a verified backup to a completed migration."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

IMAGE_RE = re.compile(r"^[a-z0-9][a-z0-9._:/-]*[a-z0-9]@sha256:[0-9a-f]{64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SOURCE_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_RECEIPT_BYTES = 64 * 1024
MAX_RECEIPT_AGE = timedelta(hours=24)
FIELDS = {
    "schema_version",
    "status",
    "created_at",
    "backup_evidence_sha256",
    "backup_artifact_sha256",
    "database_identity_sha256",
    "before_revision",
    "after_revision",
    "protected_image",
    "target_image",
    "source_sha",
}


class MigrationReceiptError(ValueError):
    """The migration receipt cannot authorize the post-migration deploy."""


@dataclass(frozen=True)
class VerifiedMigrationReceipt:
    backup_evidence_sha256: str
    backup_artifact_sha256: str
    database_identity_sha256: str
    before_revision: str
    after_revision: str
    protected_image: str
    target_image: str
    source_sha: str
    created_at: datetime


def _secure_file_bytes(path: Path, *, label: str) -> bytes:
    if not path.is_absolute():
        raise MigrationReceiptError(f"{label} path is unsafe")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise MigrationReceiptError(f"{label} is unavailable") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise MigrationReceiptError(f"{label} must be a regular file")
        if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
            raise MigrationReceiptError(f"{label} must be owned by the current user")
        if stat.S_IMODE(info.st_mode) != 0o600:
            raise MigrationReceiptError(f"{label} permissions must be 0600")
        if info.st_size > MAX_RECEIPT_BYTES:
            raise MigrationReceiptError(f"{label} is too large")
        chunks: list[bytes] = []
        remaining = MAX_RECEIPT_BYTES + 1
        while remaining > 0 and (chunk := os.read(descriptor, min(65536, remaining))):
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_RECEIPT_BYTES:
            raise MigrationReceiptError(f"{label} is too large")
        return raw
    finally:
        os.close(descriptor)


def _require_secure_output_parent(path: Path) -> None:
    parent = path.parent
    if parent.is_symlink():
        raise MigrationReceiptError("Migration receipt output directory is unsafe")
    try:
        info = parent.stat()
    except OSError as exc:
        raise MigrationReceiptError(
            "Migration receipt output directory is unavailable"
        ) from exc
    if (
        not stat.S_ISDIR(info.st_mode)
        or (hasattr(os, "geteuid") and info.st_uid != os.geteuid())
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise MigrationReceiptError(
            "Migration receipt output directory must be owner-only mode 0700"
        )


def _validate_scalar(value: object, *, field: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise MigrationReceiptError(f"Migration receipt {field} is invalid")
    return value


def _validate_revision(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise MigrationReceiptError(f"Migration receipt {field} is invalid")
    return value


def _parse_created_at(value: object, *, now: datetime) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise MigrationReceiptError("Migration receipt created_at is invalid")
    try:
        created = datetime.fromisoformat(value)
    except ValueError as exc:
        raise MigrationReceiptError("Migration receipt created_at is invalid") from exc
    if created.tzinfo != UTC or created > now or now - created > MAX_RECEIPT_AGE:
        raise MigrationReceiptError("Migration receipt is stale or from the future")
    return created


def create_migration_receipt(
    output_path: Path,
    *,
    evidence_path: Path,
    backup_artifact_sha256: str,
    database_identity_sha256: str,
    before_revision: str,
    after_revision: str,
    protected_image: str,
    target_image: str,
    source_sha: str,
    now: datetime | None = None,
) -> Path:
    """Atomically create the receipt after the caller verified the migrated DB."""
    if not output_path.is_absolute() or output_path.is_symlink():
        raise MigrationReceiptError("Migration receipt output path is unsafe")
    _require_secure_output_parent(output_path)
    evidence_bytes = _secure_file_bytes(evidence_path, label="Backup evidence")
    _validate_scalar(
        backup_artifact_sha256,
        field="backup_artifact_sha256",
        pattern=SHA256_RE,
    )
    _validate_scalar(
        database_identity_sha256,
        field="database_identity_sha256",
        pattern=SHA256_RE,
    )
    _validate_revision(before_revision, field="before_revision")
    _validate_revision(after_revision, field="after_revision")
    _validate_scalar(protected_image, field="protected_image", pattern=IMAGE_RE)
    _validate_scalar(target_image, field="target_image", pattern=IMAGE_RE)
    _validate_scalar(source_sha, field="source_sha", pattern=SOURCE_SHA_RE)
    created = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "migrated",
        "created_at": created.isoformat().replace("+00:00", "Z"),
        "backup_evidence_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
        "backup_artifact_sha256": backup_artifact_sha256,
        "database_identity_sha256": database_identity_sha256,
        "before_revision": before_revision,
        "after_revision": after_revision,
        "protected_image": protected_image,
        "target_image": target_image,
        "source_sha": source_sha,
    }
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", dir=output_path.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output_path)
        output_path.chmod(0o600)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    return output_path


def validate_migration_receipt(
    receipt_path: Path,
    *,
    evidence_path: Path,
    expected_protected_image: str,
    expected_target_image: str,
    expected_source_sha: str,
    expected_database_identity_sha256: str,
    expected_after_revision: str,
    now: datetime | None = None,
) -> VerifiedMigrationReceipt:
    """Validate the closed receipt against evidence, images, and the current DB."""
    raw = _secure_file_bytes(receipt_path, label="Migration receipt")
    evidence_bytes = _secure_file_bytes(evidence_path, label="Backup evidence")
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MigrationReceiptError("Migration receipt is invalid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != FIELDS:
        raise MigrationReceiptError("Migration receipt fields are invalid")
    if payload["schema_version"] != 1 or payload["status"] != "migrated":
        raise MigrationReceiptError("Migration receipt status is invalid")
    created = _parse_created_at(payload["created_at"], now=now or datetime.now(UTC))
    evidence_sha = _validate_scalar(
        payload["backup_evidence_sha256"],
        field="backup_evidence_sha256",
        pattern=SHA256_RE,
    )
    artifact_sha = _validate_scalar(
        payload["backup_artifact_sha256"],
        field="backup_artifact_sha256",
        pattern=SHA256_RE,
    )
    identity = _validate_scalar(
        payload["database_identity_sha256"],
        field="database_identity_sha256",
        pattern=SHA256_RE,
    )
    before_revision = _validate_revision(
        payload["before_revision"], field="before_revision"
    )
    after_revision = _validate_revision(
        payload["after_revision"], field="after_revision"
    )
    protected_image = _validate_scalar(
        payload["protected_image"], field="protected_image", pattern=IMAGE_RE
    )
    target_image = _validate_scalar(
        payload["target_image"], field="target_image", pattern=IMAGE_RE
    )
    source_sha = _validate_scalar(
        payload["source_sha"], field="source_sha", pattern=SOURCE_SHA_RE
    )
    if evidence_sha != hashlib.sha256(evidence_bytes).hexdigest():
        raise MigrationReceiptError("Migration receipt backup evidence was changed")
    if (
        protected_image != expected_protected_image
        or target_image != expected_target_image
        or source_sha != expected_source_sha
        or identity != expected_database_identity_sha256
        or after_revision != expected_after_revision
    ):
        raise MigrationReceiptError("Migration receipt binding does not match")
    return VerifiedMigrationReceipt(
        backup_evidence_sha256=evidence_sha,
        backup_artifact_sha256=artifact_sha,
        database_identity_sha256=identity,
        before_revision=before_revision,
        after_revision=after_revision,
        protected_image=protected_image,
        target_image=target_image,
        source_sha=source_sha,
        created_at=created,
    )
