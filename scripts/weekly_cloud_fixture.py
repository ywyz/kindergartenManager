"""Seed the bounded synthetic fixture for the weekly-plan cloud check.

This is a data-only fixture initializer.  The target schema must already have
been migrated by the deployment process; this command deliberately has no
Alembic or ``create_all`` path.  The normal mode accepts only the dedicated
MySQL database ``wp_cloud_20260914`` and refuses a database containing any
tenant-bearing business rows.  The explicit production mode is narrower: it
requires ``--allow-production-synthetic`` and ``--tenant-id`` and only accepts
a tenant with no rows in any tenant-bearing table.  Existing rows in other
tenants are never changed.

The four accounts, identity hierarchy, two shared classes, two short plans,
one long plan and source mappings are created through the real identity and
authoring applications used by the page.  The long plan is intentionally left
for the browser to shorten manually.  No renderer or export code is imported
or called here.

The synthetic account password is read from an owner-only file.  It is never
printed or placed in the body-free receipt.  Database URLs are accepted as a
CLI value or ``DATABASE_URL`` environment variable, but are never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import stat
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

TARGET_DATABASE = "wp_cloud_20260914"
EXPECTED_ALEMBIC_HEAD = "e486fa012359"
# Keep the dedicated cloud fixture on the reviewed qualification tenant used
# by the existing local seed.  Production mode always requires an explicit
# caller-supplied tenant and never reuses this value implicitly.
CLOUD_TENANT_ID = 11
SCHEMA = "weekly-cloud-fixture.v1"

ACCOUNT_SPECS = (
    ("sys_admin", "sys_admin", "synthetic1", "合成系统管理员"),
    ("teaching_admin", "teaching_admin", "synthetic2", "合成教务管理员"),
    ("teacher_a", "teacher", "synthetic3", "合成教师甲"),
    ("teacher_b", "teacher", "synthetic4", "合成教师乙"),
)
TEACHER_NAMES = ("合成教师甲", "合成教师乙")
CAREGIVER_NAME = "合成保育"
CLASS_NAMES = ("合成一班", "合成长文班")
ACTORS = {"合成一班": "teacher_a", "合成长文班": "teacher_b"}
LONG_SENTENCE = "围绕主题进行观察，"

# These scenarios mirror the existing local acceptance seed.  The first row
# retains the incomplete-plan smoke case; the two short rows are the cloud
# five/six-column checks and the long row is the manual-shortening case.
PLAN_SPECS = (
    ("合成一班", date(2026, 9, 7), date(2026, 9, 11), "incomplete"),
    ("合成一班", date(2026, 9, 14), date(2026, 9, 18), "short"),
    ("合成一班", date(2026, 9, 20), date(2026, 9, 25), "short"),
    ("合成一班", date(2026, 9, 28), date(2026, 10, 2), "short"),
    ("合成一班", date(2026, 10, 5), date(2026, 10, 10), "short"),
    ("合成长文班", date(2026, 9, 14), date(2026, 9, 18), "long"),
)
SOURCE_SPECS = (
    ("teacher_a", date(2026, 9, 8), "周二", "活动"),
    ("teacher_a", date(2026, 9, 9), "周三", "活动"),
    ("teacher_b", date(2026, 9, 9), "周三", None),
)

# All tables used by the public identity/authoring/source applications.  A
# missing table is a deployment error; the fixture never creates it.
REQUIRED_TABLES = frozenset(
    {
        "alembic_version",
        "user",
        "tenant_identity_guard",
        "tenant_identity_manager",
        "academic_year",
        "semester",
        "class_instance",
        "class_semester",
        "teacher_class_assignment",
        "identity_audit",
        "daily_plan",
        "identity_mapping_event",
        "daily_plan_identity",
        "shared_weekly_plan",
        "shared_weekly_version",
        "shared_weekly_date",
        "shared_weekly_audit",
        "shared_weekly_source",
        "shared_weekly_source_audit",
        "shared_weekly_export_audit",
        "weekly_person_defaults",
        "weekly_person_defaults_audit",
    }
)

# The latest Alembic chain seeds this immutable reference catalog for the
# listening module.  It is present in a newly migrated database before the
# fixture runs, but is not user or weekly-plan data.  This allowlist is used
# only by the dedicated non-production database preflight; production tenant
# checks remain strictly empty for every tenant-bearing table.
MIGRATION_REFERENCE_SEED_TABLES = frozenset({"indicator_catalog"})


class FixtureRejected(RuntimeError):
    """A body-free, fail-closed fixture rejection."""


def _reject(reason: str) -> None:
    raise FixtureRejected(reason)


def _read_owner_password(raw_path: str | os.PathLike[str]) -> str:
    """Read one synthetic password from a regular owner-only file.

    The password file is opened with ``O_NOFOLLOW`` when available and its
    ownership/mode are checked both before and after opening.  A final line
    ending is accepted for ordinary secret-file ergonomics; any other newline
    or NUL is rejected.  Error messages contain no file contents.
    """

    path = Path(raw_path)
    if not path.is_absolute():
        _reject("password_file_must_be_absolute")
    try:
        metadata = path.lstat()
    except OSError:
        _reject("password_file_unavailable")
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        _reject("password_file_must_be_regular")
    user = getattr(os, "getuid", lambda: metadata.st_uid)()
    if metadata.st_uid != user or stat.S_IMODE(metadata.st_mode) & 0o077:
        _reject("password_file_must_be_owner_only")

    no_follow = getattr(os, "O_NOFOLLOW", 0)
    close_on_exec = getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, os.O_RDONLY | no_follow | close_on_exec)
    except OSError:
        _reject("password_file_unavailable")
    try:
        opened = os.fstat(fd)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != user
            or stat.S_IMODE(opened.st_mode) & 0o077
            or opened.st_dev != metadata.st_dev
            or opened.st_ino != metadata.st_ino
        ):
            _reject("password_file_changed")
        chunks: list[bytes] = []
        size = 0
        while chunk := os.read(fd, 4096):
            size += len(chunk)
            if size > 4096:
                _reject("password_file_too_large")
            chunks.append(chunk)
    except FixtureRejected:
        raise
    except (OSError, UnicodeError):
        _reject("password_file_unavailable")
    finally:
        os.close(fd)

    try:
        text = b"".join(chunks).decode("utf-8")
    except UnicodeDecodeError:
        _reject("password_file_invalid")
    if text.endswith("\n"):
        text = text[:-1].removesuffix("\r")
    if not text or "\r" in text or "\n" in text or "\x00" in text:
        _reject("password_file_invalid")
    if len(text.encode("utf-8")) > 512:
        _reject("password_file_too_large")
    return text


def _database_url(raw: str | None, *, production: bool):
    """Validate a URL without exposing credentials in the error surface."""

    if type(raw) is not str or not raw:
        _reject("database_url_required")
    from sqlalchemy.engine import make_url

    try:
        parsed = make_url(raw)
    except (TypeError, ValueError):
        _reject("database_url_invalid")
    if parsed.drivername.split("+", 1)[0] != "mysql":
        _reject("mysql_required")
    if not parsed.database:
        _reject("database_name_required")
    if not production and parsed.database != TARGET_DATABASE:
        _reject("dedicated_database_required")
    if production and parsed.database == TARGET_DATABASE:
        # Production mode is an explicit escape hatch, but a dedicated test
        # database remains governed by the normal empty-database contract.
        _reject("production_database_must_be_explicit")
    if parsed.drivername not in {"mysql+aiomysql", "mysql+asyncmy"}:
        _reject("async_mysql_driver_required")
    return parsed


def _configure_database(parsed) -> str:
    """Bind app configuration to the already validated URL, without logging it."""

    value = parsed.render_as_string(hide_password=False)
    existing = os.environ.get("DATABASE_URL")
    if existing:
        from sqlalchemy.engine import make_url

        try:
            existing_value = make_url(existing).render_as_string(hide_password=False)
        except (TypeError, ValueError):
            _reject("database_url_environment_invalid")
        if existing_value != value:
            _reject("database_url_environment_mismatch")
    os.environ["DATABASE_URL"] = value
    # The seed uses short-lived in-process JWTs only to call the real
    # application services.  When the caller did not provide the app's
    # configured secrets, keep Settings from persisting generated values into
    # a developer or production data directory.
    if not os.environ.get("JWT_SECRET"):
        os.environ["JWT_SECRET"] = secrets.token_urlsafe(64)
    if not os.environ.get("ENCRYPTION_KEY"):
        os.environ["ENCRYPTION_KEY"] = secrets.token_urlsafe(32)
    return value


def _table_names(sync_connection) -> set[str]:
    from sqlalchemy import inspect

    return set(inspect(sync_connection).get_table_names())


async def _count_rows(connection, table, tenant_id: int | None) -> int:
    from sqlalchemy import func, select

    statement = select(func.count()).select_from(table)
    if tenant_id is not None and "tenant_id" in table.c:
        statement = statement.where(table.c.tenant_id == tenant_id)
    return int((await connection.execute(statement)).scalar_one())


async def _preflight_database(engine, *, tenant_id: int, production: bool) -> None:
    """Require an existing MySQL schema and an unused target scope."""

    if type(tenant_id) is not int or tenant_id <= 0:
        _reject("tenant_id_invalid")
    from sqlalchemy import select, text

    from app.core import models as _models  # noqa: F401  # register metadata
    from app.core.database import Base
    from app.core.models.user import User
    from app.repository.weekly_export_repository import AUDIT as EXPORT_AUDIT

    async with engine.connect() as connection:
        if connection.dialect.name != "mysql":
            _reject("mysql_required")
        names = await connection.run_sync(_table_names)
        missing = sorted(REQUIRED_TABLES - names)
        if missing:
            _reject("schema_missing")
        version_rows = await connection.execute(
            text("SELECT version_num FROM alembic_version")
        )
        versions = tuple(version_rows.scalars())
        if versions != (EXPECTED_ALEMBIC_HEAD,):
            _reject("schema_revision_mismatch")

        allowed_reference_seeds = (
            frozenset() if production else MIGRATION_REFERENCE_SEED_TABLES
        )
        tenant_tables = tuple(
            table
            for name, table in Base.metadata.tables.items()
            if (
                name in names
                and "tenant_id" in table.c
                and name not in allowed_reference_seeds
            )
        ) + (
            (EXPORT_AUDIT,) if EXPORT_AUDIT.name not in allowed_reference_seeds else ()
        )
        # The normal BWH target must be a new business database.  In the
        # explicit production mode, only the selected tenant must be empty;
        # every other tenant is left alone and is never inspected for writes.
        scope = tenant_id if production else None
        usernames = tuple(spec[2] for spec in ACCOUNT_SPECS)
        existing_user = (
            await connection.execute(
                select(User.username).where(
                    User.tenant_id == tenant_id, User.username.in_(usernames)
                )
            )
        ).first()
        if existing_user:
            _reject("synthetic_username_exists")
        for table in tenant_tables:
            count = await _count_rows(connection, table, scope)
            if count:
                _reject(
                    "production_tenant_not_empty"
                    if production
                    else "dedicated_database_not_empty"
                )


def _slot_value(path: str, index: int, kind: str) -> str:
    if kind == "long" and not path.endswith(".name"):
        return LONG_SENTENCE * 10 + str(index)
    return f"项{index}"


def _body_free_receipt(receipt: dict[str, Any], password: str) -> None:
    """Reject accidental body/secrets before a receipt reaches disk/stdout."""

    forbidden = (
        "body",
        "hash",
        "password",
        "secret",
        "token",
        "payload",
        "theme",
    )

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key).lower()
                if any(word in key_text for word in forbidden):
                    _reject("receipt_not_body_free")
                visit(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                visit(child)
        elif (
            password
            and isinstance(value, str)
            and (value == password or password in value)
        ):
            _reject("receipt_contains_secret")

    visit(receipt)


def _write_receipt(
    path: str | os.PathLike[str], receipt: dict[str, Any], password: str
) -> Path:
    """Create one owner-readable receipt without replacing an existing file."""

    _body_free_receipt(receipt, password)
    target = Path(path)
    if not target.is_absolute():
        _reject("receipt_path_must_be_absolute")
    if not target.parent.is_dir():
        _reject("receipt_parent_unavailable")
    if target.exists() or target.is_symlink():
        _reject("receipt_path_exists")
    payload = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(target, flags, 0o600)
    except OSError:
        _reject("receipt_unavailable")
    try:
        view = memoryview(payload.encode("utf-8"))
        while view:
            written = os.write(fd, view)
            if written <= 0:
                _reject("receipt_unavailable")
            view = view[written:]
        os.fchmod(fd, 0o600)
    except FixtureRejected:
        raise
    except OSError:
        _reject("receipt_unavailable")
    finally:
        os.close(fd)
    return target


async def _seed(
    engine,
    *,
    tenant_id: int,
    password: str,
    production: bool,
) -> dict[str, Any]:
    """Seed the cloud fixture using the real public identity/authoring seams."""

    try:
        if type(password) is not str or not password:
            _reject("password_invalid")
        await _preflight_database(engine, tenant_id=tenant_id, production=production)
    except BaseException:
        # `_preflight_database` runs before the normal session lifecycle try
        # block.  Dispose here as well so a rejected remote connection cannot
        # outlive the event loop.
        await engine.dispose()
        raise

    from dataclasses import replace

    from sqlalchemy import insert, select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.auth.jwt import create_access_token
    from app.auth.password import hash_password
    from app.core.models.user import User, UserRole
    from app.jobs.identity_manager import set_manager
    from app.repository.source_mapping_repository import DAILY
    from app.service.academic_identity.application import IdentityApplication
    from app.service.academic_identity.contracts import (
        AcademicYearInput,
        AssignmentInput,
        ClassInput,
        SemesterInput,
    )
    from app.service.shared_weekly.authoring_application import (
        AuthoringApplication,
        SlotChange,
    )
    from app.service.shared_weekly.editor_contracts import ManualWeekEdit
    from app.service.shared_weekly.mapping_application import SourceMappingApplication
    from app.service.shared_weekly.mapping_contracts import MappingTarget
    from app.service.shared_weekly.people_contracts import People
    from app.ui.auth_context import resolve_current_ui_session

    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        # IDs are intentionally omitted.  MySQL allocates them and the
        # resulting IDs are used everywhere else in this fixture.
        async with factory() as session:
            rows = {}
            for key, role, username, display in ACCOUNT_SPECS:
                row = User(
                    tenant_id=tenant_id,
                    role=UserRole(role),
                    username=username,
                    hashed_password=hash_password(password),
                    is_active=True,
                    display_name=display,
                )
                session.add(row)
                rows[key] = row
            await session.flush()
            user_ids = {key: row.id for key, row in rows.items()}
            await session.commit()

        roles = {key: role for key, role, _, _ in ACCOUNT_SPECS}
        tokens = {
            key: create_access_token(
                user_id=user_ids[key],
                tenant_id=tenant_id,
                role=roles[key],
                auth_epoch=1,
            )
            for key in roles
        }
        async with factory() as session:
            sessions = {
                key: await resolve_current_ui_session(session, tokens[key])
                for key in roles
            }
        if any(session is None for session in sessions.values()):
            _reject("session_bootstrap_failed")

        # set_manager is the same controlled operations seam used by the
        # application.  The explicit fixture is allowed to target a remote
        # BWH/production host after all database and tenant guards pass.
        await set_manager(
            session_factory=factory,
            token=tokens["sys_admin"],
            target_id=user_ids["teaching_admin"],
            expected_revision=0,
            active=True,
            confirmed_target_id=user_ids["teaching_admin"],
            enabled=True,
            allow_remote=True,
        )

        manager = IdentityApplication(factory, lambda: tokens["teaching_admin"])
        manager_session = sessions["teaching_admin"]
        year = await manager.create_year(
            manager_session,
            AcademicYearInput("2026", date(2026, 8, 1), date(2027, 7, 31)),
        )
        semester = await manager.create_semester(
            manager_session,
            SemesterInput(
                year.id,
                date(2026, 9, 1),
                date(2027, 1, 31),
                "summer",
                "cold",
            ),
        )
        classes = {}
        for name in CLASS_NAMES:
            classes[name] = await manager.create_class(
                manager_session,
                ClassInput(year.id, semester.id, name, "中班"),
            )

        now = datetime.now(UTC)
        assignment_receipt = []
        for account_key in ("teacher_a", "teacher_b"):
            for class_name in CLASS_NAMES:
                stamp = await manager.grant(
                    manager_session,
                    AssignmentInput(
                        user_ids[account_key],
                        classes[class_name].id,
                        semester.id,
                        now - timedelta(days=1),
                        now + timedelta(days=30),
                        date(2026, 9, 1),
                        date(2027, 1, 31),
                    ),
                )
                assignment_receipt.append(
                    {
                        "assignment_id": stamp.id,
                        "revision": stamp.revision,
                        "user_key": account_key,
                        "user_id": user_ids[account_key],
                        "class": class_name,
                        "class_id": classes[class_name].id,
                    }
                )

        people = People(TEACHER_NAMES, CAREGIVER_NAME)
        authors = {
            key: AuthoringApplication(factory, lambda key=key: tokens[key])
            for key in ("teacher_a", "teacher_b")
        }
        plan_receipt = []
        for class_name, start, end, kind in PLAN_SPECS:
            actor_key = ACTORS[class_name]
            display = await authors[actor_key].calendar.resolve_week(
                sessions[actor_key],
                classes[class_name].id,
                semester.id,
                start,
                end,
            )
            created = await authors[actor_key].create_week(
                sessions[actor_key], display.scope, f"合成主题{start:%m%d}", uuid4()
            )
            edit = await authors[actor_key].begin_authoring(
                sessions[actor_key], created.plan.plan_id
            )
            if kind != "incomplete":
                days = []
                index = 0
                for day, (_, teaching, _label) in zip(
                    edit.body.days, edit.body.calendar.columns
                ):
                    if teaching:
                        days.append(
                            replace(
                                day,
                                activity_name=f"活动{index}",
                                morning_talk_topic=f"晨谈{index}",
                                morning_talk_questions=f"问题{index}",
                            )
                        )
                        index += 1
                    else:
                        days.append(day)
                edit = await authors[actor_key].update_edit(
                    sessions[actor_key],
                    edit.page_id,
                    edit.page,
                    ManualWeekEdit(f"合成主题{start:%m%d}", people, tuple(days)),
                )
                edit = await authors[actor_key].update_slots(
                    sessions[actor_key],
                    edit.page_id,
                    edit.page,
                    tuple(
                        SlotChange(path, _slot_value(path, position, kind))
                        for position, path in enumerate(edit.body.paths[:33])
                    ),
                )
            saved = await authors[actor_key].save_edit(
                sessions[actor_key], edit.page_id, edit.page, uuid4()
            )
            plan_receipt.append(
                {
                    "class": class_name,
                    "class_id": classes[class_name].id,
                    "kind": kind,
                    "requested_start": start.isoformat(),
                    "requested_end": end.isoformat(),
                    "anchor_monday": display.scope.anchor_monday.isoformat(),
                    "columns": len(display.columns),
                    "teaching_days": [
                        day.isoformat() for day in display.facts.teaching_days
                    ],
                    "plan_id": saved.plan_id,
                    "current_version": saved.current_version,
                    "revision": saved.revision,
                    "editor_user_id": user_ids[actor_key],
                }
            )

        # Daily source rows and explicit mappings let the browser exercise the
        # same source-selection surface as the local acceptance fixture.  They
        # contain synthetic values only and remain inside the selected tenant.
        source_ids = []
        async with factory() as session:
            for account_key, plan_date, weekday, activity in SOURCE_SPECS:
                result = await session.execute(
                    insert(DAILY).values(
                        tenant_id=tenant_id,
                        user_id=user_ids[account_key],
                        plan_date=plan_date,
                        week_number=2,
                        weekday_cn=weekday,
                        grade="中班",
                        class_name="合成一班",
                        activity_name=activity,
                        morning_talk_topic="晨谈",
                        daily_reflection="",
                    )
                )
                source_ids.append(result.inserted_primary_key[0])
            await session.commit()

            rows = (
                (
                    await session.execute(
                        select(
                            DAILY.c.id,
                            DAILY.c.user_id,
                            DAILY.c.plan_date,
                            DAILY.c.revision,
                            DAILY.c.grade,
                            DAILY.c.class_name,
                            DAILY.c.activity_name,
                            DAILY.c.morning_talk_topic,
                        )
                        .where(DAILY.c.id.in_(source_ids))
                        .order_by(DAILY.c.id)
                    )
                )
                .mappings()
                .all()
            )
        source_receipt = [
            {
                "daily_plan_id": row["id"],
                "user_id": row["user_id"],
                "plan_date": row["plan_date"].isoformat(),
                "revision": row["revision"],
                "activity_name_present": row["activity_name"] is not None,
            }
            for row in rows
        ]

        mapping_app = SourceMappingApplication(
            factory, lambda: tokens["teaching_admin"]
        )
        mapping_receipt = []
        for source_id in source_ids:
            target = MappingTarget(source_id, classes["合成一班"].id, semester.id)
            preview = await mapping_app.preview(manager_session, target)
            mapping = await mapping_app.confirm(
                manager_session,
                preview.candidate_id,
                confirmed=True,
                operation_id=uuid4(),
            )
            mapping_receipt.append(
                {
                    "daily_plan_id": source_id,
                    "mapping_event_id": mapping.id,
                    "revision": mapping.revision,
                }
            )

        receipt = {
            "schema": SCHEMA,
            "stage": "fixture-seed",
            "mode": "production-synthetic" if production else "bwh-test",
            "database_name": TARGET_DATABASE,
            "schema_revision": EXPECTED_ALEMBIC_HEAD,
            "tenant_id": tenant_id,
            "accounts": [
                {
                    "key": key,
                    "user_id": user_ids[key],
                    "username": username,
                    "role": role,
                    "display_name": display,
                }
                for key, role, username, display in ACCOUNT_SPECS
            ],
            "identity": {
                "academic_year_id": year.id,
                "academic_year_label": "2026",
                "semester_id": semester.id,
                "semester_range": "2026-09-01..2027-01-31",
                "classes": {
                    name: {"id": classes[name].id, "grade": "中班"}
                    for name in CLASS_NAMES
                },
                "assignments": assignment_receipt,
            },
            "plans": plan_receipt,
            "sources": source_receipt,
            "mapping": mapping_receipt,
            "notes": [
                "synthetic fixture only; no application schema migration",
                "short five/six-column plans are ready for browser save/check",
                "long plan is reserved for manual browser shortening",
            ],
        }
        _body_free_receipt(receipt, password)
        return receipt
    finally:
        await engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scripts.weekly_cloud_fixture")
    command = parser.add_subparsers(dest="command", required=True)
    seed = command.add_parser("seed", help="seed an already-migrated MySQL database")
    seed.add_argument(
        "--database-url",
        default=None,
        help="validated mysql+aiomysql URL; defaults to DATABASE_URL",
    )
    seed.add_argument(
        "--password-file",
        required=True,
        help="absolute owner-only file containing the synthetic account password",
    )
    seed.add_argument(
        "--receipt-output",
        required=True,
        help="absolute new owner-only body-free JSON receipt path",
    )
    seed.add_argument(
        "--allow-production-synthetic",
        action="store_true",
        help="explicitly permit seeding one new empty production tenant",
    )
    seed.add_argument(
        "--tenant-id",
        type=int,
        default=None,
        help="new positive synthetic tenant; required with production mode",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "seed":
        return 2
    production = bool(args.allow_production_synthetic)
    if production:
        if type(args.tenant_id) is not int or args.tenant_id <= 0:
            print("fixture_rejected reason=production_tenant_required", file=sys.stderr)
            return 2
        tenant_id = args.tenant_id
    else:
        if args.tenant_id is not None:
            print("fixture_rejected reason=production_flag_required", file=sys.stderr)
            return 2
        tenant_id = CLOUD_TENANT_ID

    try:
        raw_database_url = args.database_url or os.environ.get("DATABASE_URL")
        parsed = _database_url(raw_database_url, production=production)
        _configure_database(parsed)
        password = _read_owner_password(args.password_file)
        from app.core.database import _build_engine

        engine = _build_engine()
        receipt = asyncio.run(
            _seed(
                engine,
                tenant_id=tenant_id,
                password=password,
                production=production,
            )
        )
        receipt["database_name"] = parsed.database
        output = _write_receipt(args.receipt_output, receipt, password)
        password = ""
        print(
            f"fixture_seeded tenant_id={tenant_id} plans={len(receipt['plans'])} "
            f"receipt={output}"
        )
        return 0
    except FixtureRejected as exc:
        print(f"fixture_rejected reason={exc}", file=sys.stderr)
        return 2
    except Exception:  # noqa: BLE001 - sanitize driver/application errors
        # Database drivers and SQLAlchemy may include connection details in
        # their exception text.  Keep the command output body/credential free.
        print("fixture_failed reason=runtime_error", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
