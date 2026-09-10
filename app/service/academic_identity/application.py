"""Session-bound identity management. No page-provided actor or teaching body."""

from asyncio import CancelledError
from contextlib import asynccontextmanager
from hashlib import sha256

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.models.user import User
from app.repository.academic_identity_repository import IdentityRepository
from app.service.academic_identity.contracts import (
    AcademicYearInput,
    AssignmentInput,
    ClassInput,
    ClassSemesterInput,
    IdentityRejected,
    IdentityStamp,
    SemesterInput,
    positive,
)
from app.ui.auth_context import TrustedUiSession, resolve_current_ui_session


class IdentityApplication:
    def __init__(self, session_factory, token_source):
        # Composition supplies the current browser storage accessor, never a page flag.
        self._factory = session_factory
        self._token_source = token_source

    @asynccontextmanager
    async def transaction(self, expected, target_ids=(), *, commit_unknown=False):
        if type(expected) is not TrustedUiSession:
            raise IdentityRejected("session_invalid")
        token = self._token_source()
        try:
            async with self._factory() as session:
                if session.bind.dialect.name == "sqlite":
                    await session.execute(text("PRAGMA foreign_keys=ON"))
                    await session.execute(text("BEGIN IMMEDIATE"))
                else:
                    # A pre-lock consistent read must not survive a concurrent
                    # revocation commit while this transaction waits for User.
                    await session.connection(
                        execution_options={"isolation_level": "READ COMMITTED"}
                    )
                current = await resolve_current_ui_session(session, token)
                if current is None or (
                    current.session_id,
                    current.tenant_id,
                    current.user_id,
                    current.role,
                ) != (
                    expected.session_id,
                    expected.tenant_id,
                    expected.user_id,
                    expected.role,
                ):
                    raise IdentityRejected("session_invalid")
                ids = sorted({current.user_id, *target_ids})
                for user_id in ids:
                    user = (
                        await session.execute(
                            select(User)
                            .where(
                                User.tenant_id == current.tenant_id, User.id == user_id
                            )
                            .with_for_update()
                            .execution_options(populate_existing=True)
                        )
                    ).scalar_one_or_none()
                    if user is None:
                        raise IdentityRejected("scope_denied")
                # Repeat token/epoch validation after waiting for User locks.
                session.expire_all()
                locked = await resolve_current_ui_session(session, token)
                if locked != current or self._token_source() != token:
                    raise IdentityRejected("session_invalid")
                repository = IdentityRepository(session, current.tenant_id)
                yield repository, current
                # Time can advance during awaited fact reads, even with User locked.
                session.expire_all()
                final = await resolve_current_ui_session(session, token)
                if final != current or self._token_source() != token:
                    raise IdentityRejected("session_invalid")
                try:
                    await session.commit()
                except (SQLAlchemyError, CancelledError):
                    if commit_unknown:
                        raise IdentityRejected("commit_unknown") from None
                    raise
        except SQLAlchemyError:
            raise IdentityRejected("identity_conflict") from None

    async def _manage(self, expected, command, command_type, method, target_ids=()):
        if type(command) is not command_type:
            raise IdentityRejected("input_invalid")
        async with self.transaction(expected, target_ids) as (repository, actor):
            await repository.manager(actor.user_id)
            if method != "grant":
                await repository.lock_configuration()
            result = await getattr(repository, method)(command)
            await repository.audit(
                actor.user_id,
                result.id,
                method,
                sha256(str(actor.session_id).encode()).hexdigest(),
            )
        return result

    async def create_year(
        self, expected: TrustedUiSession, command: AcademicYearInput
    ) -> IdentityStamp:
        return await self._manage(expected, command, AcademicYearInput, "create_year")

    async def create_semester(
        self, expected: TrustedUiSession, command: SemesterInput
    ) -> IdentityStamp:
        return await self._manage(expected, command, SemesterInput, "create_semester")

    async def create_class(
        self, expected: TrustedUiSession, command: ClassInput
    ) -> IdentityStamp:
        return await self._manage(expected, command, ClassInput, "create_class")

    async def bind_class(
        self, expected: TrustedUiSession, command: ClassSemesterInput
    ) -> IdentityStamp:
        return await self._manage(expected, command, ClassSemesterInput, "bind_class")

    async def grant(
        self, expected: TrustedUiSession, command: AssignmentInput
    ) -> IdentityStamp:
        if type(command) is not AssignmentInput:
            raise IdentityRejected("input_invalid")
        return await self._manage(
            expected, command, AssignmentInput, "grant", (command.user_id,)
        )

    async def revoke(
        self, expected: TrustedUiSession, assignment_id: int, expected_revision: int
    ) -> IdentityStamp:
        positive(assignment_id)
        positive(expected_revision)
        # Find only the target User for lock ordering; publish no identity/body.
        async with self._factory() as session:
            current = await resolve_current_ui_session(session, self._token_source())
            if current is None or current != expected:
                raise IdentityRejected("session_invalid")
            before = await IdentityRepository(session, current.tenant_id).require(
                "teacher_class_assignment", id=assignment_id
            )
        async with self.transaction(expected, (before["user_id"],)) as (
            repository,
            actor,
        ):
            await repository.manager(actor.user_id)
            locked = await repository.require(
                "teacher_class_assignment", id=assignment_id
            )
            if locked["user_id"] != before["user_id"]:
                raise IdentityRejected("membership_stale")
            result = await repository.revoke(assignment_id, expected_revision)
            await repository.audit(
                actor.user_id,
                result.id,
                "revoke",
                sha256(str(actor.session_id).encode()).hexdigest(),
            )
        return result


def build_identity_application() -> IdentityApplication:
    from nicegui import app

    from app.core.database import AsyncSessionLocal

    return IdentityApplication(AsyncSessionLocal, lambda: app.storage.user.get("token"))
