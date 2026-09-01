"""Backup-gated, explicit Alembic migration command."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.backup_evidence import BackupEvidenceError, validate_backup_evidence
from app.core.config import settings
from app.core.migration_receipt import create_migration_receipt
from app.core.startup import (
    configured_database_identity_sha256,
    get_migration_head,
    read_configured_database_revision,
    run_migrations,
)
from scripts.deploy import _validate_oci_index_ref, _validate_oci_source_revision
from scripts.release_convergence import (
    OCI_INDEX_MEDIA_TYPE,
    REQUIRED_PLATFORMS,
    ConvergenceError,
    validate_descriptor,
    validate_expected_values,
    verify_release,
)

ISOLATION_RUN_RE = re.compile(r"^[a-z0-9][a-z0-9-]{7,63}$")
LOOPBACK_IMAGE_RE = re.compile(
    r"^(?:localhost|127\.0\.0\.1):[0-9]{2,5}/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$"
)
REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_SOURCE_PATHS = (
    "alembic",
    "alembic.ini",
    "app/core/migration_receipt.py",
    "app/core/startup.py",
    "app/jobs/migrate_database.py",
    "scripts/deploy.py",
    "scripts/release_convergence.py",
)


def _validate_local_migration_source(source_sha: str) -> None:
    """Bind the actual local Alembic/job implementation to the target source SHA."""
    try:
        head = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
        changes = subprocess.run(
            [
                "git",
                "-C",
                str(REPO_ROOT),
                "status",
                "--porcelain",
                "--",
                *MIGRATION_SOURCE_PATHS,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConvergenceError("Migration source checkout is unavailable") from exc
    if head != source_sha or changes:
        raise ConvergenceError("Migration source checkout does not match source SHA")


def _validate_isolation_scope(
    *, run_id: str, protected_image: str, target_image: str, release_tag: str
) -> None:
    if (
        not ISOLATION_RUN_RE.fullmatch(run_id)
        or not LOOPBACK_IMAGE_RE.fullmatch(protected_image)
        or not LOOPBACK_IMAGE_RE.fullmatch(target_image)
        or release_tag != f"r5p-isolation-{run_id}"
    ):
        raise ConvergenceError("Isolation candidate scope is invalid")
    try:
        database_name = make_url(settings.DATABASE_URL).database
    except Exception as exc:
        raise ConvergenceError("Isolation database scope is invalid") from exc
    expected_database = f"r5_p_{run_id.replace('-', '_')}"
    if database_name != expected_database:
        raise ConvergenceError("Isolation database is not bound to the run id")


def _validate_target_release(
    descriptor_path: Path,
    *,
    target_image: str,
    source_sha: str,
    release_repo: str | None,
    release_id: str | None,
    isolation_run_id: str | None,
    protected_image: str,
) -> None:
    if not descriptor_path.is_absolute():
        raise ConvergenceError("Release descriptor path is unsafe")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(descriptor_path, flags)
    except OSError as exc:
        raise ConvergenceError("Release descriptor is unavailable") from exc
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or (hasattr(os, "geteuid") and info.st_uid != os.geteuid())
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > 64 * 1024
        ):
            raise ConvergenceError("Release descriptor must be owner-only mode 0600")
        raw = os.read(descriptor, 64 * 1024 + 1)
        if len(raw) > 64 * 1024:
            raise ConvergenceError("Release descriptor is too large")
    finally:
        os.close(descriptor)
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ConvergenceError("Release descriptor must be a JSON object")
    repository, separator, digest = target_image.partition("@")
    if not separator:
        raise ConvergenceError("Target image is not immutable")
    tag = payload.get("release_tag")
    if not isinstance(tag, str):
        raise ConvergenceError("Release descriptor tag is invalid")
    validate_expected_values(
        tag=tag,
        source_sha=source_sha,
        repository=repository,
        digest=digest,
        immutable_ref=target_image,
        media_type=OCI_INDEX_MEDIA_TYPE,
        platforms=list(REQUIRED_PLATFORMS),
    )
    validate_descriptor(
        payload,
        tag=tag,
        source_sha=source_sha,
        repository=repository,
        digest=digest,
        immutable_ref=target_image,
        media_type=OCI_INDEX_MEDIA_TYPE,
        platforms=list(REQUIRED_PLATFORMS),
    )
    _validate_local_migration_source(source_sha)
    if isolation_run_id is not None:
        _validate_isolation_scope(
            run_id=isolation_run_id,
            protected_image=protected_image,
            target_image=target_image,
            release_tag=tag,
        )
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token or release_repo is None or release_id is None:
            raise ConvergenceError("GitHub Release binding is unavailable")
        verify_release(
            repo=release_repo,
            token=token,
            descriptor_path=descriptor_path,
            tag=tag,
            source_sha=source_sha,
            repository=repository,
            digest=digest,
            immutable_ref=target_image,
            media_type=OCI_INDEX_MEDIA_TYPE,
            platforms=list(REQUIRED_PLATFORMS),
            release_id=release_id,
        )
    _validate_oci_index_ref(target_image, dry_run=False)
    _validate_oci_source_revision(target_image, source_sha)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="显式执行数据库迁移")
    parser.add_argument("--backup-evidence", type=Path, required=True)
    parser.add_argument("--protected-image", required=True)
    parser.add_argument("--target-image")
    parser.add_argument("--source-sha")
    parser.add_argument("--receipt-output", type=Path)
    parser.add_argument("--release-descriptor", type=Path)
    parser.add_argument("--release-repo")
    parser.add_argument("--release-id")
    parser.add_argument(
        "--isolation-run-id",
        help="Loopback-only candidate mode bound to r5_p_<run-id> synthetic DB.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    receipt_values = (
        args.target_image,
        args.source_sha,
        args.receipt_output,
        args.release_descriptor,
    )
    if any(receipt_values) and not all(receipt_values):
        print("❌ 迁移收据参数不完整，数据库迁移未执行")
        return 1
    release_values = (args.release_repo, args.release_id)
    if any(release_values) and not all(release_values):
        print("❌ Release 绑定参数不完整，数据库迁移未执行")
        return 1
    if all(receipt_values) and (
        bool(args.isolation_run_id) == bool(all(release_values))
    ):
        print("❌ 必须且只能选择生产 Release 或隔离候选绑定，数据库迁移未执行")
        return 1
    try:
        database_identity = configured_database_identity_sha256()
        before_revision = read_configured_database_revision()
        evidence = validate_backup_evidence(
            args.backup_evidence,
            expected_protected_image=args.protected_image,
            expected_database_identity_sha256=database_identity,
        )
        if evidence.database_revision != before_revision:
            raise BackupEvidenceError(
                "Backup evidence revision does not match the configured database"
            )
    except Exception:  # noqa: BLE001 - redact config/driver/connection details
        print("❌ 已验证备份证据无效，数据库迁移未执行")
        return 1
    target_revision = get_migration_head()
    if before_revision != target_revision and not all(receipt_values):
        print("❌ 数据库 revision 将变化，必须先配置完整迁移收据，迁移未执行")
        return 1
    if all(receipt_values):
        try:
            _validate_target_release(
                args.release_descriptor,
                target_image=args.target_image,
                source_sha=args.source_sha,
                release_repo=args.release_repo,
                release_id=args.release_id,
                isolation_run_id=args.isolation_run_id,
                protected_image=args.protected_image,
            )
        except Exception:  # noqa: BLE001 - redact registry/descriptor details
            print("❌ 目标发布元组或 OCI index 无效，数据库迁移未执行")
            return 1
    try:
        run_migrations(log_failure_detail=False)
    except Exception:  # noqa: BLE001 - redact migration/driver failure details
        print("❌ 数据库迁移失败；请保留备份并按恢复计划人工处置")
        return 1
    if args.receipt_output is not None:
        try:
            after_identity = configured_database_identity_sha256()
            after_revision = read_configured_database_revision()
            if after_identity != database_identity or after_revision != target_revision:
                raise BackupEvidenceError(
                    "Migrated database identity or revision does not match"
                )
            create_migration_receipt(
                args.receipt_output,
                evidence_path=args.backup_evidence,
                backup_artifact_sha256=evidence.artifact_sha256,
                database_identity_sha256=after_identity,
                before_revision=before_revision,
                after_revision=after_revision,
                protected_image=args.protected_image,
                target_image=args.target_image,
                source_sha=args.source_sha,
            )
        except Exception:  # noqa: BLE001 - migration may already be durable; redact details
            print("❌ 数据库迁移已执行但迁移收据未能验证；不得继续部署")
            return 1
    print("✅ 数据库迁移完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
