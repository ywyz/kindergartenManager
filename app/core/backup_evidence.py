"""Strict consumer for short-lived, restore-verified backup evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

IMAGE_RE = re.compile(r"^[a-z0-9][a-z0-9._:/-]*[a-z0-9]@sha256:[0-9a-f]{64}$")
NO_RUNNING_IMAGE = "no-running-image"
MAX_EVIDENCE_BYTES = 64 * 1024
MAX_VALIDITY = timedelta(hours=24)
ROOT_FIELDS = {
    "schema_version",
    "status",
    "created_at",
    "expires_at",
    "protected_image",
    "database_identity_sha256",
    "database_revision",
    "artifact",
    "checks",
}
ARTIFACT_FIELDS = {"path", "size_bytes", "sha256"}
CHECK_FIELDS = {"database_integrity", "isolated_restore", "required_assets"}


class BackupEvidenceError(ValueError):
    """The supplied evidence cannot authorize a migration or deployment."""


@dataclass(frozen=True)
class VerifiedBackupEvidence:
    protected_image: str
    database_identity_sha256: str
    database_revision: str
    artifact_path: Path
    artifact_sha256: str
    expires_at: datetime


def _open_secure_file(path: Path, *, label: str) -> tuple[int, os.stat_result]:
    if not path.is_absolute():
        raise BackupEvidenceError(f"{label} path must be absolute")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        if path.is_symlink():
            raise BackupEvidenceError(f"{label} must not be a symlink") from exc
        raise BackupEvidenceError(f"{label} is unavailable") from exc
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode):
        os.close(descriptor)
        raise BackupEvidenceError(f"{label} must be a regular file")
    if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        os.close(descriptor)
        raise BackupEvidenceError(f"{label} must be owned by the current user")
    if os.name == "posix" and stat.S_IMODE(info.st_mode) != 0o600:
        os.close(descriptor)
        raise BackupEvidenceError(f"{label} must have mode 0600")
    return descriptor, info


def _read_evidence(path: Path) -> dict[str, Any]:
    descriptor, info = _open_secure_file(path, label="Backup evidence")
    try:
        if info.st_size > MAX_EVIDENCE_BYTES:
            raise BackupEvidenceError("Backup evidence is too large")
        raw = os.read(descriptor, MAX_EVIDENCE_BYTES + 1)
    finally:
        os.close(descriptor)
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BackupEvidenceError("Backup evidence is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise BackupEvidenceError("Backup evidence must be a JSON object")
    return payload


def _parse_utc(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise BackupEvidenceError(f"{field} must be UTC RFC3339")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise BackupEvidenceError(f"{field} must be UTC RFC3339") from exc
    if parsed.tzinfo != UTC:
        raise BackupEvidenceError(f"{field} must be UTC RFC3339")
    return parsed


def _hash_artifact(path: Path) -> tuple[int, str]:
    descriptor, info = _open_secure_file(path, label="Backup artifact")
    digest = hashlib.sha256()
    try:
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
    finally:
        os.close(descriptor)
    return info.st_size, digest.hexdigest()


def validate_backup_evidence(
    evidence_path: Path,
    *,
    expected_protected_image: str,
    expected_database_identity_sha256: str | None = None,
    now: datetime | None = None,
) -> VerifiedBackupEvidence:
    """Validate closed evidence and re-hash its protected backup artifact."""
    if not (
        expected_protected_image == NO_RUNNING_IMAGE
        or IMAGE_RE.fullmatch(expected_protected_image)
    ):
        raise BackupEvidenceError("Expected protected image is invalid")
    payload = _read_evidence(evidence_path)
    if set(payload) != ROOT_FIELDS:
        raise BackupEvidenceError("Backup evidence fields do not match the closed schema")
    if payload["schema_version"] != 1:
        raise BackupEvidenceError("Backup evidence schema version is unsupported")
    if payload["status"] != "verified":
        raise BackupEvidenceError("Backup evidence status is not verified")
    if payload["protected_image"] != expected_protected_image:
        raise BackupEvidenceError("Backup evidence image binding does not match")
    database_identity = payload["database_identity_sha256"]
    if not isinstance(database_identity, str) or not re.fullmatch(
        r"[0-9a-f]{64}", database_identity
    ):
        raise BackupEvidenceError("Backup evidence database identity is invalid")
    if (
        expected_database_identity_sha256 is not None
        and database_identity != expected_database_identity_sha256
    ):
        raise BackupEvidenceError("Backup evidence database identity does not match")
    revision = payload["database_revision"]
    if not isinstance(revision, str) or not revision or len(revision) > 128:
        raise BackupEvidenceError("Backup evidence database revision is invalid")

    created_at = _parse_utc(payload["created_at"], field="created_at")
    expires_at = _parse_utc(payload["expires_at"], field="expires_at")
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise BackupEvidenceError("Validation time must be timezone-aware")
    current = current.astimezone(UTC)
    if created_at > current:
        raise BackupEvidenceError("Backup evidence creation time is in the future")
    if expires_at <= current:
        raise BackupEvidenceError("Backup evidence has expired")
    if expires_at <= created_at or expires_at - created_at > MAX_VALIDITY:
        raise BackupEvidenceError("Backup evidence validity must not exceed 24 hours")

    checks = payload["checks"]
    if not isinstance(checks, dict) or set(checks) != CHECK_FIELDS:
        raise BackupEvidenceError("Backup evidence checks do not match the closed schema")
    if any(checks[field] != "passed" for field in CHECK_FIELDS):
        raise BackupEvidenceError("Backup evidence checks have not all passed")

    artifact = payload["artifact"]
    if not isinstance(artifact, dict) or set(artifact) != ARTIFACT_FIELDS:
        raise BackupEvidenceError("Backup artifact fields do not match the closed schema")
    artifact_path_value = artifact["path"]
    expected_size = artifact["size_bytes"]
    expected_sha256 = artifact["sha256"]
    if not isinstance(artifact_path_value, str):
        raise BackupEvidenceError("Backup artifact path is invalid")
    if not isinstance(expected_size, int) or isinstance(expected_size, bool) or expected_size < 0:
        raise BackupEvidenceError("Backup artifact size is invalid")
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise BackupEvidenceError("Backup artifact checksum is invalid")
    artifact_path = Path(artifact_path_value)
    actual_size, actual_sha256 = _hash_artifact(artifact_path)
    if actual_size != expected_size:
        raise BackupEvidenceError("Backup artifact size does not match evidence")
    if actual_sha256 != expected_sha256:
        raise BackupEvidenceError("Backup artifact checksum does not match evidence")

    return VerifiedBackupEvidence(
        protected_image=expected_protected_image,
        database_identity_sha256=database_identity,
        database_revision=revision,
        artifact_path=artifact_path,
        artifact_sha256=actual_sha256,
        expires_at=expires_at,
    )
