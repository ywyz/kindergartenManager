"""Complete, disposable SQLite recovery rehearsal for R5-R.

This module is deliberately a local acceptance harness.  It creates only
synthetic data below the caller supplied work root, exercises the production
backup/restore producer, damages the source and file assets, and then checks
the restored database through the same application seams used by the service.
It never reads the configured production database and never starts a network
or Docker process.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token
from app.auth.password import hash_password
from app.core import crypto
from app.core.backup_evidence import validate_backup_evidence
from app.core.models.ai_key import AiApiKey
from app.core.models.course_review_activity import CourseReviewActivity
from app.core.models.daily_plan import DailyPlan
from app.core.models.game_observation import GameObservation
from app.core.models.game_observation_image import GameObservationImage
from app.core.models.homemade_teaching import HomemadeTeachingToy
from app.core.models.listening_domain import ListeningDomain
from app.core.models.listening_image import ListeningImage
from app.core.models.listening_record import ListeningRecord
from app.core.models.user import User, UserRole
from app.core.startup import get_migration_head
from app.integration.word_export import exporter as daily_exporter
from app.integration.word_export.course_review_activity_exporter import (
    export_course_review_activity,
)
from app.integration.word_export.exporter import export_daily_plan
from app.integration.word_export.homemade_teaching_exporter import (
    export_homemade_teaching,
)
from app.integration.word_export.listening_exporter import export_combined
from app.integration.word_export.observation_exporter import export_observation
from app.jobs.backup_restore import (
    BackupRestoreError,
    create_sqlite_backup_attestation,
    restore_backup_artifact,
)
from app.repository.ai_key_repository import get_active_ai_key
from app.service.auth_service import login


class RecoveryDrillError(RuntimeError):
    """The complete local recovery rehearsal failed closed."""


_TENANT_ID = 17
_USER_ID = 1
_USERNAME = "r5-r-recovery-admin"
_SYNTHETIC_ENCRYPTION_KEY = "r5-r-recovery-encryption-key"
_SYNTHETIC_JWT_SECRET = "r5-r-jwt-secret-32-bytes-minimum-2026"
_IMAGE_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
_MODULE_TABLES = (
    "daily_plan",
    "game_observation",
    "listening_record",
    "homemade_teaching_toy",
    "course_review_activity",
)
_IMAGE_TABLES = ("game_observation_image", "listening_image")
_TEMPLATE_NAMES = (
    "teacherplan.docx",
    "ObservationRecord.docx",
    "OneOnOneListeningSmallSecond.docx",
    "homemadeteaching.docx",
    "coursereviewactivity.docx",
)
_CHECKS = {
    "database_corruption": "passed",
    "asset_corruption": "passed",
    "isolated_restore": "passed",
    "readiness": "passed",
    "login": "passed",
    "module_records": "passed",
    "blob_images": "passed",
    "ai_key_decryption": "passed",
    "word_reexport": "passed",
    "zero_data_loss": "passed",
}


def run_full_recovery_drill(
    *,
    work_root: Path,
    protected_image: str,
    synthetic_login_password: str,
    synthetic_ai_key: str,
    evidence_path: Path | None = None,
    restore_root: Path | None = None,
) -> dict[str, Any]:
    """Run one complete local backup/corruption/restore acceptance rehearsal.

    With no explicit evidence path, synthetic source data and file assets are
    created, backed up, damaged, and restored.  Supplying ``evidence_path``
    is the consumer-only mode used to prove invalid handwritten evidence is
    rejected before a restore directory is created.
    """

    root = Path(work_root)
    if not root.is_absolute():
        raise RecoveryDrillError("Recovery work root must be absolute")
    if not isinstance(synthetic_login_password, str) or not synthetic_login_password:
        raise RecoveryDrillError("Synthetic login password is invalid")
    if not isinstance(synthetic_ai_key, str) or not synthetic_ai_key:
        raise RecoveryDrillError("Synthetic AI key is invalid")

    if evidence_path is not None:
        return _restore_supplied_evidence(
            Path(evidence_path),
            Path(restore_root) if restore_root is not None else root / "restore",
            protected_image,
        )

    try:
        _secure_new_directory(root)
        source_root = root / "source"
        source_root.mkdir(mode=0o700)
        source_database = source_root / "kindergarten.db"
        secrets_file, exports_root, templates_root = _make_assets(
            source_root, _SYNTHETIC_ENCRYPTION_KEY
        )
        revision = get_migration_head()
        _seed_database(
            source_database,
            revision=revision,
            login_password=synthetic_login_password,
            ai_key=synthetic_ai_key,
            encryption_key=_SYNTHETIC_ENCRYPTION_KEY,
        )
        source_snapshot = _sqlite_snapshot(source_database)

        backup_root = root / "backups"
        evidence = create_sqlite_backup_attestation(
            source_database=source_database,
            backup_root=backup_root,
            secrets_file=secrets_file,
            exports_root=exports_root,
            templates_root=templates_root,
            protected_image=protected_image,
        )
        payload = json.loads(evidence.read_text(encoding="utf-8"))
        artifact = Path(payload["artifact"]["path"])

        _corrupt_source(source_database)
        _corrupt_assets(secrets_file, exports_root, templates_root)
        isolated_root = (
            Path(restore_root)
            if restore_root is not None
            else root / "isolated-restore"
        )
        _restore_and_verify_archive(artifact, isolated_root, protected_image, evidence)
        restored_database = isolated_root / "database.sqlite3"

        _verify_application_readiness_and_login(
            restored_database,
            restored_secrets=isolated_root / "secrets" / ".kindergarten_secrets",
            tenant_id=_TENANT_ID,
            username=_USERNAME,
            password=synthetic_login_password,
            revision=revision,
        )
        module_counts, tenant_ids = _verify_module_records(restored_database)
        blob_counts, blob_sha256 = _verify_image_blobs(restored_database)
        _verify_ai_key(
            restored_database,
            isolated_root / "secrets" / ".kindergarten_secrets",
            synthetic_ai_key,
        )
        word_exports = _reexport_word_documents(
            restored_database,
            root / "word-reexports",
            isolated_root / "templates",
        )
        restored_snapshot = _sqlite_snapshot(restored_database)
        if restored_snapshot != source_snapshot:
            raise RecoveryDrillError("Restored database has data loss")
        if _sqlite_snapshot(source_database) == source_snapshot:
            raise RecoveryDrillError("Database corruption was not simulated")

        # The consumer validator is intentionally called after the full
        # application checks as an additional producer-provenance boundary.
        verified = validate_backup_evidence(
            evidence,
            expected_protected_image=protected_image,
        )
        return {
            "status": "verified",
            "environment": "synthetic-local",
            "source_database": str(source_database.resolve()),
            "restore_root": str(isolated_root.resolve()),
            "artifact_path": str(artifact.resolve()),
            "evidence_path": str(evidence.resolve()),
            "database_revision": verified.database_revision,
            "checks": dict(_CHECKS),
            "module_counts": module_counts,
            "tenant_ids": tenant_ids,
            "blob_counts": blob_counts,
            "blob_sha256": blob_sha256,
            "word_exports": word_exports,
            "source_corrupted": True,
            "assets_corrupted": True,
            "source_snapshot": source_snapshot,
        }
    except RecoveryDrillError:
        raise
    except (
        BackupRestoreError,
        OSError,
        sqlite3.Error,
        ValueError,
        RuntimeError,
    ) as exc:
        raise RecoveryDrillError(
            f"Recovery drill failed: {type(exc).__name__}"
        ) from None


def _restore_supplied_evidence(
    evidence: Path,
    restore_root: Path,
    protected_image: str,
) -> dict[str, Any]:
    if not evidence.is_absolute() or not restore_root.is_absolute():
        raise RecoveryDrillError("Recovery evidence and destination must be absolute")
    try:
        from app.jobs.backup_restore import validate_generated_attestation

        verified = validate_generated_attestation(
            evidence,
            expected_protected_image=protected_image,
        )
        restore_backup_artifact(verified.artifact_path, restore_root)
    except Exception as exc:  # noqa: BLE001 - this is a redacted CLI boundary
        if restore_root.exists():
            _remove_tree(restore_root)
        raise RecoveryDrillError(
            f"Recovery evidence is invalid: {type(exc).__name__}"
        ) from None
    return {
        "status": "verified",
        "environment": "synthetic-local",
        "evidence_path": str(evidence.resolve()),
        "restore_root": str(restore_root.resolve()),
    }


def _secure_new_directory(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise RecoveryDrillError("Recovery work root must be new")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir(mode=0o700)
    if os.name == "posix":
        path.chmod(0o700)


def _make_assets(source_root: Path, encryption_key: str) -> tuple[Path, Path, Path]:
    secrets_file = source_root / ".kindergarten_secrets"
    exports_root = source_root / "exports"
    templates_root = source_root / "templates"
    exports_root.mkdir(mode=0o700)
    templates_root.mkdir(mode=0o700)
    _write_secure(
        secrets_file,
        (
            f"ENCRYPTION_KEY={encryption_key}\nJWT_SECRET={_SYNTHETIC_JWT_SECRET}\n"
        ).encode(),
    )
    _write_secure(exports_root / "before-recovery.docx", b"synthetic export")
    repository_templates = Path(__file__).parents[1] / "templates"
    for name in _TEMPLATE_NAMES:
        source = repository_templates / name
        destination = templates_root / name
        shutil.copyfile(source, destination)
        if os.name == "posix":
            destination.chmod(0o600)
        _validate_docx(destination)
    return secrets_file, exports_root, templates_root


def _write_secure(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)
    if os.name == "posix":
        path.chmod(0o600)


def _seed_database(
    database: Path,
    *,
    revision: str,
    login_password: str,
    ai_key: str,
    encryption_key: str,
) -> None:
    migration_env = _migration_environment(database, encryption_key)
    try:
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=Path(__file__).parents[1],
            env=migration_env,
            check=True,
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        raise RecoveryDrillError("Synthetic Alembic migration failed") from None
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    try:
        with engine.connect() as connection:
            actual_revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            if actual_revision != revision:
                raise RecoveryDrillError("Synthetic migration revision mismatch")
        with Session(engine) as session:
            user = User(
                id=_USER_ID,
                tenant_id=_TENANT_ID,
                username=_USERNAME,
                hashed_password=hash_password(login_password),
                role=UserRole.sys_admin,
                is_active=True,
                auth_epoch=1,
                display_name="R5-R synthetic administrator",
            )
            session.add(user)
            session.flush()

            plan = DailyPlan(
                tenant_id=_TENANT_ID,
                user_id=_USER_ID,
                plan_date=date(2026, 9, 1),
                week_number=1,
                weekday_cn="周二",
                grade="小班",
                class_name="合成一班",
                activity_goal="恢复演练目标",
                activity_prep="恢复演练材料",
                activity_process_original="恢复演练原始过程",
                activity_process_adapted="恢复演练适配过程",
            )
            observation = GameObservation(
                tenant_id=_TENANT_ID,
                user_id=_USER_ID,
                obs_date=date(2026, 9, 1),
                big_env="室内",
                game_area="合成区域",
                grade="小班",
                class_name="合成一班",
                child_names="合成幼儿",
                observation_goal="观察目标",
                observation_record="观察记录",
                evaluation_analysis="评价分析",
                support_strategy="支持策略",
            )
            listening = ListeningRecord(
                tenant_id=_TENANT_ID,
                user_id=_USER_ID,
                obs_year=2026,
                obs_month=9,
                child_name="合成幼儿",
                adult_count=1,
                child_age="3岁",
                grade="小班",
                term="下学期",
                class_name="合成一班",
                observer="合成教师",
            )
            homemade = HomemadeTeachingToy(
                tenant_id=_TENANT_ID,
                user_id=_USER_ID,
                grade="小班",
                class_name="合成一班",
                teacher_name="合成教师",
                toy_name="恢复演练教玩具",
                materials="合成材料",
                play_methods="合成玩法",
            )
            course_review = CourseReviewActivity(
                tenant_id=_TENANT_ID,
                user_id=_USER_ID,
                grade="小班",
                class_name="合成一班",
                teacher_name="合成教师",
                activity_name="恢复演练课程",
                child_count="20",
                activity_time="2026-09-01",
                lesson_plan_original="合成原始教案",
                activity_goal="合成目标",
                activity_prep="合成准备",
                activity_process="合成过程",
                goal_adjusted=False,
                goal_adjustment="",
                activity_goal_revised="合成目标",
                prep_adjusted=False,
                prep_adjustment="",
                activity_prep_revised="合成准备",
                process_adjustment="",
                activity_process_revised="合成过程",
                review_reason="合成审议原因",
                revised_lesson_plan="合成修订教案",
            )
            session.add_all([plan, observation, listening, homemade, course_review])
            session.flush()
            session.add_all(
                [
                    GameObservationImage(
                        tenant_id=_TENANT_ID,
                        user_id=_USER_ID,
                        observation_id=observation.id,
                        image_index=1,
                        storage_backend="mysql_blob",
                        blob_content=_IMAGE_BYTES,
                        mime_type="image/png",
                        file_size=len(_IMAGE_BYTES),
                        width=1,
                        height=1,
                    ),
                    ListeningDomain(
                        tenant_id=_TENANT_ID,
                        user_id=_USER_ID,
                        record_id=listening.id,
                        domain="健康",
                        obs_year=2026,
                        obs_month=9,
                        goals="倾听目标",
                        evaluation="倾听评价",
                        support_strategy="倾听支持",
                    ),
                    ListeningImage(
                        tenant_id=_TENANT_ID,
                        user_id=_USER_ID,
                        record_id=listening.id,
                        domain="健康",
                        image_index=1,
                        storage_backend="mysql_blob",
                        blob_content=_IMAGE_BYTES,
                        mime_type="image/png",
                        file_size=len(_IMAGE_BYTES),
                        width=1,
                        height=1,
                        image_description="合成图像描述",
                    ),
                    AiApiKey(
                        tenant_id=_TENANT_ID,
                        user_id=_USER_ID,
                        api_base_url="https://synthetic.invalid/v1",
                        model_name="synthetic-model",
                        api_key_encrypted=crypto._build_fernet(encryption_key)
                        .encrypt(ai_key.encode("utf-8"))
                        .decode("utf-8"),
                        key_type="text",
                        is_active=True,
                    ),
                ]
            )
            session.commit()
    finally:
        engine.dispose()


def _migration_environment(database: Path, encryption_key: str) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": f"sqlite+aiosqlite:///{database.as_posix()}",
            "KINDERGARTEN_DATA_DIR": str(database.parent.resolve()),
            "ENCRYPTION_KEY": encryption_key,
            "JWT_SECRET": _SYNTHETIC_JWT_SECRET,
        }
    )
    return environment


def _corrupt_source(database: Path) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE daily_plan SET activity_goal = ?, "
            "revision = revision + 1, updated_at = CURRENT_TIMESTAMP "
            "WHERE tenant_id = ?",
            ("CORRUPTED-SOURCE-DATABASE", _TENANT_ID),
        )
        connection.commit()


def _corrupt_assets(
    secrets_file: Path,
    exports_root: Path,
    templates_root: Path,
) -> None:
    _write_secure(secrets_file, b"CORRUPTED-SECRETS")
    _write_secure(exports_root / "before-recovery.docx", b"CORRUPTED-EXPORT")
    _write_secure(templates_root / _TEMPLATE_NAMES[0], b"CORRUPTED-TEMPLATE")


def _restore_and_verify_archive(
    artifact: Path,
    restore_root: Path,
    protected_image: str,
    evidence: Path,
) -> None:
    if not restore_root.is_absolute() or restore_root.exists():
        raise RecoveryDrillError(
            "Recovery restore root must be a new absolute directory"
        )
    from app.jobs.backup_restore import validate_generated_attestation

    try:
        verified = validate_generated_attestation(
            evidence,
            expected_protected_image=protected_image,
        )
        if verified.artifact_path != artifact.resolve():
            raise RecoveryDrillError("Evidence artifact path mismatch")
        restore_backup_artifact(artifact, restore_root)
    except RecoveryDrillError:
        raise
    except Exception as exc:  # noqa: BLE001 - redacted recovery boundary
        raise RecoveryDrillError(
            f"Isolated restore failed: {type(exc).__name__}"
        ) from None


async def _readiness_and_login(
    database: Path,
    *,
    restored_secrets: Path,
    tenant_id: int,
    username: str,
    password: str,
    revision: str,
) -> None:
    from app.api import routes

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{database.as_posix()}")
    factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    original_factory = routes.AsyncSessionLocal
    try:
        routes.AsyncSessionLocal = factory
        response = await routes.readiness()
        if response.status_code != 200:
            raise RecoveryDrillError("Restored database readiness failed")
        payload = json.loads(response.body)
        if payload.get("status") != "ready":
            raise RecoveryDrillError("Restored database is not ready")
        restored_jwt_secret = _read_secret_value(restored_secrets, "JWT_SECRET")
        from app.auth import jwt as jwt_module

        original_jwt_secret = jwt_module.settings.JWT_SECRET
        try:
            jwt_module.settings.JWT_SECRET = restored_jwt_secret
            async with factory() as session:
                token = await login(session, tenant_id, username, password)
            token_payload = decode_access_token(token)
        finally:
            jwt_module.settings.JWT_SECRET = original_jwt_secret
        if token_payload.get("tenant_id") != tenant_id or token_payload.get(
            "sub"
        ) != str(_USER_ID):
            raise RecoveryDrillError("Restored application login identity mismatch")
    finally:
        routes.AsyncSessionLocal = original_factory
        await async_engine.dispose()


def _verify_application_readiness_and_login(
    database: Path,
    *,
    restored_secrets: Path,
    tenant_id: int,
    username: str,
    password: str,
    revision: str,
) -> None:
    import asyncio

    try:
        asyncio.run(
            _readiness_and_login(
                database,
                restored_secrets=restored_secrets,
                tenant_id=tenant_id,
                username=username,
                password=password,
                revision=revision,
            )
        )
    except RecoveryDrillError:
        raise
    except Exception as exc:  # noqa: BLE001 - redacted application boundary
        raise RecoveryDrillError(
            f"Restored application checks failed: {type(exc).__name__}"
        ) from None


def _verify_module_records(database: Path) -> tuple[dict[str, int], list[int]]:
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    try:
        with engine.connect() as connection:
            counts: dict[str, int] = {}
            tenant_ids: set[int] = set()
            for table in _MODULE_TABLES:
                quoted = '"' + table.replace('"', '""') + '"'
                counts[table] = int(
                    connection.execute(
                        text(f"SELECT COUNT(*) FROM {quoted}")
                    ).scalar_one()
                )
                tenant_ids.update(
                    int(row[0])
                    for row in connection.execute(
                        text(f"SELECT DISTINCT tenant_id FROM {quoted}")
                    )
                    if row[0] is not None
                )
            if set(tenant_ids) != {_TENANT_ID}:
                raise RecoveryDrillError("Restored module tenant boundary is invalid")
            if not all(counts[table] >= 1 for table in _MODULE_TABLES):
                raise RecoveryDrillError("Restored module records are incomplete")
            return counts, sorted(tenant_ids)
    finally:
        engine.dispose()


def _verify_image_blobs(database: Path) -> tuple[dict[str, int], dict[str, str]]:
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    try:
        with engine.connect() as connection:
            counts: dict[str, int] = {}
            hashes: dict[str, str] = {}
            for table in _IMAGE_TABLES:
                quoted = '"' + table.replace('"', '""') + '"'
                values = [
                    bytes(row[0])
                    for row in connection.execute(
                        text(
                            f"SELECT blob_content FROM {quoted} WHERE blob_content IS NOT NULL"
                        )
                    )
                ]
                if not values or any(value != _IMAGE_BYTES for value in values):
                    raise RecoveryDrillError(f"Restored {table} BLOB is invalid")
                counts[table] = len(values)
                hashes[table] = hashlib.sha256(values[0]).hexdigest()
            return counts, hashes
    finally:
        engine.dispose()


def _verify_ai_key(
    database: Path,
    restored_secrets: Path,
    expected_plaintext: str,
) -> None:
    import asyncio

    restored_fernet = crypto._build_fernet(
        _read_secret_value(restored_secrets, "ENCRYPTION_KEY")
    )

    async def verify() -> None:
        async_engine = create_async_engine(f"sqlite+aiosqlite:///{database.as_posix()}")
        factory = async_sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )
        try:
            async with factory() as session:
                record = await get_active_ai_key(session, _TENANT_ID, _USER_ID)
                if record is None:
                    raise RecoveryDrillError("Restored AI key cannot be decrypted")
                plaintext = restored_fernet.decrypt(
                    record.api_key_encrypted.encode("utf-8")
                ).decode("utf-8")
                if plaintext != expected_plaintext:
                    raise RecoveryDrillError("Restored AI key cannot be decrypted")
        finally:
            await async_engine.dispose()

    try:
        asyncio.run(verify())
    except RecoveryDrillError:
        raise
    except Exception as exc:  # noqa: BLE001 - redacted crypto boundary
        raise RecoveryDrillError(
            f"Restored AI key check failed: {type(exc).__name__}"
        ) from None


def _reexport_word_documents(
    database: Path,
    output_root: Path,
    restored_templates: Path,
) -> dict[str, dict[str, Any]]:
    output_root.mkdir(mode=0o700)
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    try:
        with Session(engine) as session:
            plan = session.query(DailyPlan).filter_by(tenant_id=_TENANT_ID).one()
            observation = (
                session.query(GameObservation).filter_by(tenant_id=_TENANT_ID).one()
            )
            observation_image = (
                session.query(GameObservationImage)
                .filter_by(tenant_id=_TENANT_ID)
                .one()
            )
            listening = (
                session.query(ListeningRecord).filter_by(tenant_id=_TENANT_ID).one()
            )
            domain = (
                session.query(ListeningDomain).filter_by(tenant_id=_TENANT_ID).one()
            )
            listening_image = (
                session.query(ListeningImage).filter_by(tenant_id=_TENANT_ID).one()
            )
            homemade = (
                session.query(HomemadeTeachingToy).filter_by(tenant_id=_TENANT_ID).one()
            )
            course_review = (
                session.query(CourseReviewActivity)
                .filter_by(tenant_id=_TENANT_ID)
                .one()
            )

            original_daily_template = daily_exporter.TEMPLATE_PATH
            try:
                daily_exporter.TEMPLATE_PATH = restored_templates / "teacherplan.docx"
                daily_plan_document = export_daily_plan(plan, [])
            finally:
                daily_exporter.TEMPLATE_PATH = original_daily_template
            documents: dict[str, bytes] = {
                "daily_plan": daily_plan_document,
                "game_observation": export_observation(
                    {
                        "big_env": observation.big_env,
                        "grade": observation.grade,
                        "class_name": observation.class_name,
                        "obs_date": observation.obs_date,
                        "time_range": observation.time_range,
                        "adult_count": observation.adult_count,
                        "child_count": observation.child_count,
                        "child_names": observation.child_names,
                        "child_age": observation.child_age,
                        "observer": observation.observer,
                        "observation_goal": observation.observation_goal,
                        "observation_record": observation.observation_record,
                        "evaluation_analysis": observation.evaluation_analysis,
                        "support_strategy": observation.support_strategy,
                    },
                    [observation_image.blob_content or b""],
                    template_path=restored_templates / "ObservationRecord.docx",
                ),
                "listening_record": export_combined(
                    {
                        "child_name": listening.child_name,
                        "child_age": listening.child_age,
                        "adult_count": listening.adult_count,
                        "grade": listening.grade,
                        "class_name": listening.class_name,
                        "observer": listening.observer,
                    },
                    [
                        {
                            "domain": domain.domain,
                            "obs_year": domain.obs_year,
                            "obs_month": domain.obs_month,
                            "goals": domain.goals,
                            "evaluation": domain.evaluation,
                            "support_strategy": domain.support_strategy,
                            "images": [
                                (
                                    listening_image.blob_content,
                                    listening_image.image_description,
                                )
                            ],
                            "indicators": [],
                        }
                    ],
                    template_path=(
                        restored_templates / "OneOnOneListeningSmallSecond.docx"
                    ),
                ),
                "homemade_teaching_toy": export_homemade_teaching(
                    homemade,
                    template_path=restored_templates / "homemadeteaching.docx",
                ),
                "course_review_activity": export_course_review_activity(
                    course_review,
                    template_path=restored_templates / "coursereviewactivity.docx",
                ),
            }
    finally:
        engine.dispose()

    result: dict[str, dict[str, Any]] = {}
    for module, payload in documents.items():
        _validate_docx_bytes(payload)
        output = output_root / f"{module}.docx"
        _write_secure(output, payload)
        result[module] = {
            "path": str(output.resolve()),
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    return result


def _read_secret_value(secrets: Path, key: str) -> str:
    try:
        lines = secrets.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        raise RecoveryDrillError("Restored secrets cannot be read") from None
    prefix = f"{key}="
    values = [line.removeprefix(prefix) for line in lines if line.startswith(prefix)]
    if len(values) != 1 or not values[0]:
        raise RecoveryDrillError("Restored secret is invalid")
    return values[0]


def _validate_docx(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise RecoveryDrillError("Restored Word template has a bad CRC")
        Document(str(path))
    except (OSError, ValueError, zipfile.BadZipFile):
        raise RecoveryDrillError("Restored Word template is invalid") from None


def _validate_docx_bytes(payload: bytes) -> None:
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            if archive.testzip() is not None:
                raise RecoveryDrillError("Re-exported Word document has a bad CRC")
        Document(BytesIO(payload))
    except (OSError, ValueError, zipfile.BadZipFile):
        raise RecoveryDrillError("Re-exported Word document is invalid") from None


def _sqlite_snapshot(path: Path) -> dict[str, list[tuple[Any, ...]]]:
    def safe(value: Any) -> Any:
        if isinstance(value, bytes):
            return {"length": len(value), "sha256": hashlib.sha256(value).hexdigest()}
        return value

    with sqlite3.connect(path) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        snapshot: dict[str, list[tuple[Any, ...]]] = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            rows = connection.execute(f"SELECT * FROM {quoted}").fetchall()
            snapshot[table] = sorted(
                [tuple(safe(value) for value in row) for row in rows],
                key=repr,
            )
        return snapshot


def _remove_tree(path: Path) -> None:
    if not path.exists() or path.is_symlink():
        return
    if path.is_dir():
        for child in path.iterdir():
            _remove_tree(child)
        path.rmdir()
    else:
        path.unlink()


__all__ = ["RecoveryDrillError", "run_full_recovery_drill"]
