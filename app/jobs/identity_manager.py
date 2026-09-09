"""Explicit operations-only identity qualification job; never called by a page.

The signed session establishes the actor; explicit deployment enablement and
exact target confirmation authorize this narrow job. No schema migration.
"""

import argparse
import asyncio
import getpass
import os
from hashlib import sha256

from sqlalchemy import insert, select, update
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from app.core.models.academic_identity import TABLES
from app.core.models.user import User
from app.repository.academic_identity_repository import utcnow
from app.service.academic_identity.application import IdentityApplication
from app.service.academic_identity.contracts import IdentityRejected, positive
from app.ui.auth_context import resolve_current_ui_session


async def set_manager(
    *,
    session_factory,
    token,
    target_id,
    expected_revision,
    active,
    confirmed_target_id,
    enabled,
    allow_remote=False,
):
    positive(target_id)
    if (
        enabled is not True
        or type(active) is not bool
        or type(expected_revision) is not int
        or expected_revision < 0
        or type(confirmed_target_id) is not int
        or confirmed_target_id != target_id
    ):
        raise IdentityRejected("operation_confirmation_required")
    async with session_factory() as session:
        if (
            make_url(str(session.bind.url)).host
            not in (None, "localhost", "127.0.0.1", "::1")
            and not allow_remote
        ):
            raise IdentityRejected("remote_operation_denied")
        expected = await resolve_current_ui_session(session, token)
    if expected is None:
        raise IdentityRejected("session_invalid")
    application = IdentityApplication(session_factory, lambda: token)
    async with application.transaction(expected, (target_id,)) as (repository, actor):
        if actor.role != "sys_admin":
            raise IdentityRejected("operations_actor_required")
        user = (
            await repository.session.execute(
                select(User).where(
                    User.tenant_id == actor.tenant_id, User.id == target_id
                )
            )
        ).scalar_one()
        if not user.is_active:
            raise IdentityRejected("scope_denied")
        # Atomically create/lock the tenant guard, including concurrent first use.
        guard = TABLES["tenant_identity_guard"]
        if repository.session.bind.dialect.name == "mysql":
            from sqlalchemy.dialects.mysql import insert as dialect_insert

            stmt = dialect_insert(guard).values(tenant_id=actor.tenant_id)
            await repository.session.execute(
                stmt.on_duplicate_key_update(tenant_id=stmt.inserted.tenant_id)
            )
        else:
            from sqlalchemy.dialects.sqlite import insert as dialect_insert

            await repository.session.execute(
                dialect_insert(guard)
                .values(tenant_id=actor.tenant_id)
                .on_conflict_do_nothing()
            )
        await repository.lock_configuration()
        old = await repository.row(
            "tenant_identity_manager", user_id=target_id, lock=True
        )
        if (old["revision"] if old else 0) != expected_revision:
            raise IdentityRejected("manager_stale")
        table = TABLES["tenant_identity_manager"]
        if old:
            await repository.session.execute(
                update(table)
                .where(
                    table.c.tenant_id == actor.tenant_id, table.c.user_id == target_id
                )
                .values(
                    is_active=active,
                    revision=expected_revision + 1,
                    updated_at=utcnow(),
                )
            )
        else:
            await repository.session.execute(
                insert(table).values(
                    tenant_id=actor.tenant_id, user_id=target_id, is_active=active
                )
            )
        await repository.audit(
            actor.user_id,
            target_id,
            "manager_grant" if active else "manager_revoke",
            sha256(str(actor.session_id).encode()).hexdigest(),
        )
    return expected_revision + 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-id", type=int, required=True)
    parser.add_argument("--expected-revision", type=int, required=True)
    parser.add_argument("--revoke", action="store_true")
    args = parser.parse_args()
    if os.environ.get("IDENTITY_MANAGER_JOB_ENABLED") != "true":
        print("operation_disabled")
        return 1
    token = getpass.getpass("Signed login token (hidden): ")
    confirmation = input("Confirm exact target user ID: ")
    try:
        from app.core.database import AsyncSessionLocal

        asyncio.run(
            set_manager(
                session_factory=AsyncSessionLocal,
                token=token,
                target_id=args.target_id,
                expected_revision=args.expected_revision,
                active=not args.revoke,
                confirmed_target_id=int(confirmation),
                enabled=True,
                allow_remote=os.environ.get("IDENTITY_MANAGER_JOB_ALLOW_REMOTE")
                == "true",
            )
        )
    except (IdentityRejected, ValueError, SQLAlchemyError):
        print("identity_operation_rejected")
        return 1
    finally:
        token = None
    print("identity_operation_completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
