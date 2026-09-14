"""WP-E A1-SEED + A2-SERVE: isolated local synthetic acceptance helper.

Explicitly local helper for the WP-E quality acceptance worktree; never a
production install, deployment target or product capability.  Stage A1-SEED
only: `seed` initializes a NEW exclusive local directory (any pre-existing
path is refused, never reset) with mode 0700, migrates a local SQLite
database via Alembic (no create_all), seeds synthetic tenant-11 accounts,
the real identity hierarchy, shared weekly plans and one synthetic daily
source mapping through the real applications, then writes a body-free JSON
seed receipt for later read-only database checks.

Stage A2-SERVE adds `serve`: it re-runs the real application entrypoint
(`app.main.main`) over an ALREADY-SEEDED exclusive directory without creating,
resetting or migrating anything. The AI client is only ever the explicit local
mock boundary (never a network request); the server binds 127.0.0.1 only.
Mode `local-synthetic` additionally injects ONLY a `LayoutAuthority` built
from the reviewed synthetic catalog helper of tests.test_wpe_word_authority
(local-only activation for tenant 11) into the existing
configure_shared_weekly_production startup seam; that authority is a local
test authority and is never a qualification installation or release artifact.

The fixed local password below is a synthetic fixture value documented here
on purpose; it is not a real credential.  The local database stores only the
synthetic accounts' Argon2 authentication hashes; bearer tokens and the
plaintext password are never persisted, and the receipt contains neither
tokens, passwords nor password hashes.
"""

import argparse
import asyncio
import hashlib
import json
import os
import stat
import tempfile
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
TENANT_ID = 11
LOCAL_PASSWORD = "WpE-local-Only-2026!"
LONG_SENTENCE = "围绕主题进行观察，"
TEACHERS = ("合成教师甲", "合成教师乙")
CAREGIVER = "合成保育"
ACCOUNTS = (
    (1, "sys_admin", "合成系统管理员"),
    (2, "teaching_admin", "合成教务管理员"),
    (3, "teacher", "合成教师甲"),
    (4, "teacher", "合成教师乙"),
)
CLASS_NAMES = ("合成一班", "合成长文班")
ACTORS = {"合成一班": 3, "合成长文班": 4}
PLAN_SPECS = (
    ("合成一班", date(2026, 9, 7), date(2026, 9, 11), "incomplete", "合成主题"),
    ("合成一班", date(2026, 9, 14), date(2026, 9, 18), "short", "合成主题0914"),
    ("合成一班", date(2026, 9, 20), date(2026, 9, 25), "short", "合成主题0920"),
    ("合成一班", date(2026, 9, 28), date(2026, 10, 2), "short", "合成主题0928"),
    ("合成一班", date(2026, 10, 5), date(2026, 10, 10), "short", "合成主题1005"),
    ("合成长文班", date(2026, 9, 14), date(2026, 9, 18), "long", "合成长文主题"),
)
SOURCE_SPECS = (
    (3, date(2026, 9, 8), "周二", "活动"),
    (3, date(2026, 9, 9), "周三", "活动"),
    (4, date(2026, 9, 9), "周三", None),
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slot_value(path: str, index: int, kind: str) -> str:
    if kind == "long" and not path.endswith(".name"):
        return LONG_SENTENCE * 10 + str(index)
    return f"项{index}"


def _check_environment() -> None:
    for name in ("DATABASE_URL", "KINDERGARTEN_DATA_DIR"):
        if os.environ.get(name):
            raise SystemExit(f"{name} is already set; refusing redirected environment")


def _prepare_directory(raw: str) -> Path:
    given = Path(raw)
    if not given.is_absolute():
        raise SystemExit("seed --data-dir must be an absolute path")
    if given.exists() or given.is_symlink():
        raise SystemExit(f"seed refuses any pre-existing path: {given}")
    path = given.resolve()
    if path.exists() or path.is_symlink():
        raise SystemExit(f"seed refuses any pre-existing path: {path}")
    if not path.parent.is_dir():
        raise SystemExit(f"seed requires an existing parent directory: {path.parent}")
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700)
    return path


def _prepare_environment(data_dir: Path) -> None:
    os.environ["DATABASE_URL"] = (
        f"sqlite+aiosqlite:///{(data_dir / 'local_acceptance.db').as_posix()}"
    )
    os.environ["KINDERGARTEN_DATA_DIR"] = str(data_dir)
    os.environ["BOOTSTRAP_ADMIN_TENANT_ID"] = str(TENANT_ID)
    for name in ("JWT_SECRET", "ENCRYPTION_KEY", "API_SIGNING_SECRET"):
        os.environ[name] = ""


def _migrate() -> None:
    from alembic.config import Config

    from alembic import command

    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    command.upgrade(config, "head")


SERVE_PORT = {"default": 18777, "local-synthetic": 18778}


def _check_seeded_directory(raw: str) -> Path:
    """Validate an already-seeded exclusive directory; create or reset nothing."""
    given = Path(raw)
    if not given.is_absolute():
        raise SystemExit("serve --data-dir must be an absolute path")
    if given.is_symlink():
        raise SystemExit(f"serve refuses a symlinked data directory: {given}")
    path = given.resolve()
    if path.is_symlink():
        raise SystemExit(f"serve refuses a symlinked data directory: {given}")
    user = os.getuid()
    try:
        location = path.lstat()
    except OSError:
        raise SystemExit(f"serve requires an existing data directory: {given}") from None
    if not stat.S_ISDIR(location.st_mode):
        raise SystemExit(f"serve requires an existing directory: {given}")
    if stat.S_IMODE(location.st_mode) != 0o700:
        raise SystemExit(f"serve requires directory mode 0700: {path}")
    if location.st_uid != user:
        raise SystemExit(f"serve requires the directory owner {user}: {path}")
    database = path / "local_acceptance.db"
    try:
        entry = database.lstat()
    except OSError:
        raise SystemExit(f"serve requires the seeded database: {database}") from None
    if not stat.S_ISREG(entry.st_mode) or entry.st_uid != user:
        raise SystemExit(f"serve requires an owned regular database file: {database}")
    receipt_path = path / "seed_receipt.json"
    try:
        meta = receipt_path.lstat()
    except OSError:
        raise SystemExit(f"serve requires the seed receipt: {receipt_path}") from None
    if not stat.S_ISREG(meta.st_mode) or meta.st_uid != user:
        raise SystemExit(f"serve requires an owned regular seed receipt: {receipt_path}")
    try:
        raw_receipt = receipt_path.read_bytes()
    except OSError:
        raise SystemExit(f"serve cannot read the seed receipt: {receipt_path}") from None
    if len(raw_receipt) > 65536:
        raise SystemExit(f"serve refuses a oversized receipt: {receipt_path}")
    try:
        receipt = json.loads(raw_receipt)
    except (ValueError, UnicodeDecodeError):
        raise SystemExit(f"serve cannot parse the seed receipt: {receipt_path}") from None
    plans = receipt.get("plans") if isinstance(receipt, dict) else None
    mapping = receipt.get("mapping") if isinstance(receipt, dict) else None
    identity = (
        receipt.get("identity") if isinstance(receipt, dict) and receipt else None
    )
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema") != "local-synthetic"
        or receipt.get("stage") != "A1-SEED"
        or receipt.get("data_dir") != str(path)
        or "local_acceptance.db" not in str(receipt.get("database", ""))
        or not isinstance(identity, dict)
        or identity.get("tenant_id") != TENANT_ID
        or not isinstance(plans, list)
        or len(plans) != 6
        or not isinstance(mapping, list)
        or len(mapping) != 3
        or any(
            not isinstance(plan, dict) or plan.get("columns") not in (5, 6)
            for plan in plans
        )
    ):
        raise SystemExit(f"serve refuses an unreviewed receipt: {receipt_path}")
    return path


async def _mock_load_config(_session, _actor):
    """Local mock AI boundary: never read per-user configs, never use the network."""
    from app.integration.ai_client.weekly_authoring_client import WeeklyAIConfig

    return WeeklyAIConfig("https://synthetic.invalid", "synthetic-only", "mock-local")


async def _mock_generate(prompt, payload, config, *, _client=None):
    """Local mock AI boundary: deterministic values only; no request, no retry."""
    from app.integration.ai_client.weekly_authoring_client import WeeklyAIConfig
    from app.service.academic_identity.contracts import IdentityRejected
    from app.service.shared_weekly.reduction_application import (
        shorten_preserving_facts,
    )

    if (
        type(config) is not WeeklyAIConfig
        or type(prompt) is not str
        or type(payload) is not dict
    ):
        raise IdentityRejected("ai_invalid")
    task = payload["task"] if isinstance(payload.get("task"), str) else ""
    fields = payload["fields"] if isinstance(payload.get("fields"), dict) else {}
    print(f"mock_ai task={task} fields={len(fields)}")
    await asyncio.sleep(0.5)
    if task == "weekly_reduction":
        values = {
            path: shorten_preserving_facts(field["original"])
            for path, field in fields.items()
        }
    else:
        values = {
            path: f"合成值{index}" for index, path in enumerate(sorted(fields))
        }
    return {"values": values}


async def _actual_renderer_version() -> str:
    from app.integration.word_export.shared_weekly_word import _process

    return (await _process("libreoffice", "--version")).decode().strip()


def _serve(args: argparse.Namespace) -> int:
    expected_port = SERVE_PORT[args.mode]
    if args.port != expected_port:
        raise SystemExit(
            f"serve --mode {args.mode} requires the isolated port {expected_port}"
        )
    _check_environment()
    data_dir = _check_seeded_directory(args.data_dir)
    _prepare_environment(data_dir)
    from nicegui import ui

    production_run = ui.run

    def forced_run(*arguments, **keyword_arguments):
        keyword_arguments["host"] = "127.0.0.1"
        keyword_arguments["port"] = args.port
        return production_run(*arguments, **keyword_arguments)

    ui.run = forced_run

    from app.integration.ai_client import weekly_authoring_client

    weekly_authoring_client.load_config = _mock_load_config
    weekly_authoring_client.generate = _mock_generate

    if args.mode == "local-synthetic":
        fixture = Path(tempfile.mkdtemp(prefix="layout-synthetic-", dir=data_dir))
        os.chmod(fixture, 0o700)
        from app.integration.word_export.shared_weekly_word import SharedWeeklyWordPort
        from app.service.shared_weekly import production_composition as composition
        from app.service.shared_weekly.layout_authority import LayoutAuthority
        from tests.test_wpe_word_authority import catalog as build_catalog

        authority = LayoutAuthority(
            build_catalog(fixture, renderer_version=asyncio.run(_actual_renderer_version())),
            local_only=True,
        )
        original = composition.configure_shared_weekly_production

        async def configure_local():
            await authority.activate(TENANT_ID, "synthetic", expected=None)
            print(
                "serve startup role=local-synthetic "
                "local test authority, never a qualification installation"
            )
            await original(word_port=SharedWeeklyWordPort(authority))

        composition.configure_shared_weekly_production = configure_local

    if args.mode == "default":
        print(
            "serve startup role=default-unqualified, empty catalog; mock AI "
            "default composition unmodified, no authority activation"
        )

    import app.main as application

    application.main()
    return 0


async def _seed(data_dir: Path) -> dict:
    from sqlalchemy import insert, select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.auth.jwt import create_access_token
    from app.auth.password import hash_password
    from app.core.database import _build_engine
    from app.core.models.user import User
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
    from app.service.shared_weekly.root_contracts import canonical
    from app.ui.auth_context import resolve_current_ui_session

    engine = _build_engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            for uid, role, display in ACCOUNTS:
                session.add(
                    User(
                        id=uid,
                        tenant_id=TENANT_ID,
                        role=role,
                        username=f"synthetic{uid}",
                        hashed_password=hash_password(LOCAL_PASSWORD),
                        is_active=True,
                        display_name=display,
                    )
                )
            await session.commit()

        roles = {uid: role for uid, role, _ in ACCOUNTS}
        tokens = {
            uid: create_access_token(
                user_id=uid, tenant_id=TENANT_ID, role=roles[uid], auth_epoch=1
            )
            for uid, _, _ in ACCOUNTS
        }
        async with factory() as session:
            sessions = {
                uid: await resolve_current_ui_session(session, tokens[uid])
                for uid, _, _ in ACCOUNTS
            }
        manager = IdentityApplication(factory, lambda: tokens[2])
        await set_manager(
            session_factory=factory,
            token=tokens[1],
            target_id=2,
            expected_revision=0,
            active=True,
            confirmed_target_id=2,
            enabled=True,
        )

        year = await manager.create_year(
            sessions[2], AcademicYearInput("2026", date(2026, 8, 1), date(2027, 7, 31))
        )
        semester = await manager.create_semester(
            sessions[2],
            SemesterInput(year.id, date(2026, 9, 1), date(2027, 1, 31), "summer", "cold"),
        )
        classes = {}
        for name in CLASS_NAMES:
            classes[name] = await manager.create_class(
                sessions[2], ClassInput(year.id, semester.id, name, "中班")
            )
        now = datetime.now(UTC)
        assignment_receipt = []
        for uid in (3, 4):
            for name in CLASS_NAMES:
                stamp = await manager.grant(
                    sessions[2],
                    AssignmentInput(
                        uid,
                        classes[name].id,
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
                        "user_id": uid,
                        "class": name,
                    }
                )

        people = People(TEACHERS, CAREGIVER)
        people_sha256 = _sha256(people.serialize())
        authors = {
            uid: AuthoringApplication(factory, lambda uid=uid: tokens[uid])
            for uid in set(ACTORS.values())
        }
        plan_receipt = []
        for class_name, start, end, kind, theme in PLAN_SPECS:
            uid = ACTORS[class_name]
            display = await authors[uid].calendar.resolve_week(
                sessions[uid], classes[class_name].id, semester.id, start, end
            )
            created = await authors[uid].create_week(
                sessions[uid], display.scope, theme, uuid4()
            )
            edit = await authors[uid].begin_authoring(
                sessions[uid], created.plan.plan_id
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
                edit = await authors[uid].update_edit(
                    sessions[uid],
                    edit.page_id,
                    edit.page,
                    ManualWeekEdit(theme, people, tuple(days)),
                )
                edit = await authors[uid].update_slots(
                    sessions[uid],
                    edit.page_id,
                    edit.page,
                    tuple(
                        SlotChange(path, _slot_value(path, position, kind))
                        for position, path in enumerate(edit.body.paths[:33])
                    ),
                )
            body_sha256 = _sha256(edit.body.serialize())
            saved = await authors[uid].save_edit(
                sessions[uid], edit.page_id, edit.page, uuid4()
            )
            plan_receipt.append(
                {
                    "class": class_name,
                    "kind": kind,
                    "theme": theme,
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
                    "body_sha256": body_sha256,
                    "people_sha256": people_sha256 if kind != "incomplete" else None,
                }
            )

        async with factory() as session:
            source_ids = []
            for user_id, plan_date, weekday, activity in SOURCE_SPECS:
                result = await session.execute(
                    insert(DAILY).values(
                        tenant_id=TENANT_ID,
                        user_id=user_id,
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
            ).mappings().all()
        source_receipt = [
            {
                "daily_plan_id": row["id"],
                "user_id": row["user_id"],
                "plan_date": row["plan_date"].isoformat(),
                "revision": row["revision"],
                "activity_name_missing": row["activity_name"] is None,
                "source_sha256": _sha256(
                    canonical(
                        {
                            "activity_name": row["activity_name"],
                            "class_name": row["class_name"],
                            "grade": row["grade"],
                            "morning_talk_topic": row["morning_talk_topic"],
                            "plan_date": row["plan_date"].isoformat(),
                            "revision": row["revision"],
                            "user_id": row["user_id"],
                        }
                    )
                ),
            }
            for row in rows
        ]

        mapping_app = SourceMappingApplication(factory, lambda: tokens[2])
        mapping_receipt = []
        for source_id in source_ids:
            target = MappingTarget(source_id, classes["合成一班"].id, semester.id)
            preview = await mapping_app.preview(sessions[2], target)
            mapping = await mapping_app.confirm(
                sessions[2], preview.candidate_id, confirmed=True, operation_id=uuid4()
            )
            mapping_receipt.append(
                {
                    "daily_plan_id": source_id,
                    "mapping_event_id": mapping.id,
                    "revision": mapping.revision,
                }
            )

        receipt = {
            "schema": "local-synthetic",
            "stage": "A1-SEED",
            "created_at_utc": datetime.now(UTC).isoformat(),
            "data_dir": str(data_dir),
            "database": "local SQLite local_acceptance.db under data_dir, Alembic migrated",
            "accounts": [
                {
                    "user_id": uid,
                    "username": f"synthetic{uid}",
                    "role": role,
                    "display_name": display,
                }
                for uid, role, display in ACCOUNTS
            ],
            "identity": {
                "tenant_id": TENANT_ID,
                "academic_year_id": year.id,
                "academic_year_label": "2026",
                "semester_id": semester.id,
                "semester_range": "2026-09-01..2027-01-31",
                "classes": {name: classes[name].id for name in CLASS_NAMES},
                "assignments": assignment_receipt,
            },
            "plans": plan_receipt,
            "sources": source_receipt,
            "mapping": mapping_receipt,
            "notes": [
                "local synthetic fixture only; never a production install",
                "accounts use the fixed synthetic password documented in this script",
                "no tokens, passwords or password hashes are recorded in this receipt",
            ],
        }
        payload = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True)
        receipt_path = data_dir / "seed_receipt.json"
        descriptor = os.open(receipt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            view = memoryview(payload.encode("utf-8"))
            while view:
                view = view[os.write(descriptor, view):]
        finally:
            os.close(descriptor)
        return receipt
    finally:
        await engine.dispose()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts.wpe_local_acceptance",
        description=__doc__,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser(
        "serve",
        help="run the real app on 127.0.0.1 over an ALREADY-SEEDED exclusive directory",
    )
    serve.add_argument(
        "--data-dir",
        required=True,
        help="absolute path of an existing reviewed seed directory; never created or reset",
    )
    serve.add_argument("--port", type=int, required=True, help="18777 or 18778")
    serve.add_argument(
        "--mode",
        required=True,
        choices=("default", "local-synthetic"),
        help="default: unmodified startup; local-synthetic: inject the local test authority",
    )
    seed = commands.add_parser(
        "seed",
        help="initialize a NEW exclusive local synthetic fixture directory (A1-SEED only)",
    )
    seed.add_argument(
        "--data-dir",
        required=True,
        help="absolute path of a NEW local directory; any pre-existing path is refused",
    )
    args = parser.parse_args(argv)
    if args.command == "seed":
        _check_environment()
        data_dir = _prepare_directory(args.data_dir)
        _prepare_environment(data_dir)
        _migrate()
        receipt = asyncio.run(_seed(data_dir))
        print(
            f"seeded {data_dir} "
            f"plans={len(receipt['plans'])} sources={len(receipt['sources'])}"
        )
        return 0
    if args.command == "serve":
        return _serve(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
