"""Backup-gated, explicit Alembic migration command."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.core.backup_evidence import BackupEvidenceError, validate_backup_evidence
from app.core.startup import run_migrations


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="显式执行数据库迁移")
    parser.add_argument("--backup-evidence", type=Path, required=True)
    parser.add_argument("--protected-image", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        validate_backup_evidence(
            args.backup_evidence,
            expected_protected_image=args.protected_image,
        )
    except BackupEvidenceError:
        print("❌ 已验证备份证据无效，数据库迁移未执行")
        return 1
    try:
        run_migrations(log_failure_detail=False)
    except Exception:
        print("❌ 数据库迁移失败；请保留备份并按恢复计划人工处置")
        return 1
    print("✅ 数据库迁移完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
