"""Closed-contract tests for pre-migration/deployment backup evidence."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


PROTECTED_IMAGE = "ghcr.io/ywyz/kindergartenmanager@sha256:" + "a" * 64


def _write_evidence(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    artifact = tmp_path / "database.backup"
    artifact.write_bytes(b"consistent synthetic backup")
    artifact.chmod(0o600)
    now = datetime(2026, 9, 1, 4, 0, tzinfo=UTC)
    payload: dict[str, object] = {
        "schema_version": 1,
        "status": "verified",
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "protected_image": PROTECTED_IMAGE,
        "database_revision": "20260825_0001",
        "artifact": {
            "path": str(artifact),
            "size_bytes": artifact.stat().st_size,
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        },
        "checks": {
            "database_integrity": "passed",
            "isolated_restore": "passed",
            "required_assets": "passed",
        },
    }
    evidence = tmp_path / "backup-evidence.json"
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    evidence.chmod(0o600)
    return evidence, artifact, payload


def test_valid_backup_evidence_is_rechecked_at_consumption(tmp_path: Path) -> None:
    from app.core.backup_evidence import validate_backup_evidence

    evidence, _, _ = _write_evidence(tmp_path)
    result = validate_backup_evidence(
        evidence,
        expected_protected_image=PROTECTED_IMAGE,
        now=datetime(2026, 9, 1, 4, 30, tzinfo=UTC),
    )

    assert result.database_revision == "20260825_0001"
    assert result.protected_image == PROTECTED_IMAGE


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (lambda payload: payload.update(extra="open-schema"), "fields"),
        (lambda payload: payload.update(status="claimed"), "status"),
        (
            lambda payload: payload["checks"].update(isolated_restore="failed"),
            "checks",
        ),
        (lambda payload: payload.update(protected_image="no-running-image"), "image"),
        (
            lambda payload: payload.update(expires_at="2026-09-03T04:00:00Z"),
            "24 hours",
        ),
        (
            lambda payload: payload.update(created_at="2026-09-01T05:00:00Z"),
            "future",
        ),
    ],
)
def test_backup_evidence_rejects_untrusted_claims(
    tmp_path: Path, mutation, match: str
) -> None:
    from app.core.backup_evidence import BackupEvidenceError, validate_backup_evidence

    evidence, _, payload = _write_evidence(tmp_path)
    mutation(payload)
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BackupEvidenceError, match=match):
        validate_backup_evidence(
            evidence,
            expected_protected_image=PROTECTED_IMAGE,
            now=datetime(2026, 9, 1, 4, 30, tzinfo=UTC),
        )


def test_backup_evidence_rejects_expired_or_tampered_artifact(tmp_path: Path) -> None:
    from app.core.backup_evidence import BackupEvidenceError, validate_backup_evidence

    evidence, artifact, _ = _write_evidence(tmp_path)
    with pytest.raises(BackupEvidenceError, match="expired"):
        validate_backup_evidence(
            evidence,
            expected_protected_image=PROTECTED_IMAGE,
            now=datetime(2026, 9, 1, 6, 0, tzinfo=UTC),
        )

    artifact.write_bytes(b"tampered")
    with pytest.raises(BackupEvidenceError, match="checksum|size"):
        validate_backup_evidence(
            evidence,
            expected_protected_image=PROTECTED_IMAGE,
            now=datetime(2026, 9, 1, 4, 30, tzinfo=UTC),
        )


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission contract")
def test_backup_evidence_rejects_wide_mode_and_symlink(tmp_path: Path) -> None:
    from app.core.backup_evidence import BackupEvidenceError, validate_backup_evidence

    evidence, artifact, _ = _write_evidence(tmp_path)
    evidence.chmod(0o640)
    with pytest.raises(BackupEvidenceError, match="0600"):
        validate_backup_evidence(evidence, expected_protected_image=PROTECTED_IMAGE)

    evidence.chmod(0o600)
    link = tmp_path / "artifact-link"
    link.symlink_to(artifact)
    payload = json.loads(evidence.read_text())
    payload["artifact"]["path"] = str(link)
    evidence.write_text(json.dumps(payload))
    with pytest.raises(BackupEvidenceError, match="symlink"):
        validate_backup_evidence(evidence, expected_protected_image=PROTECTED_IMAGE)
