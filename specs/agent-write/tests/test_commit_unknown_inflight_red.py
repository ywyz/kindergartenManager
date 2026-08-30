"""Stable RED for an in-flight commit-unknown reconciliation race.

The existing commit-unknown tests cover a commit that has already completed or
has already rolled back.  This file keeps the third state explicit: the write
transaction is still open, so a fresh reader cannot see its immutable audit
yet.  A missing audit in that window is not evidence of a rollback.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DisconnectionError
from sqlalchemy.ext.asyncio import AsyncSession

from conftest import (
    WriteDatabase,
    build_patch,
    capture_sql,
    dml_statements,
    MutableClock,
    trusted_ui_session,
    write_api,
)


class _CommitRace:
    """Coordinate one real session whose commit acknowledgement is delayed."""

    def __init__(self) -> None:
        self.armed = False
        self.commit_sent = asyncio.Event()
        self.context_exited = asyncio.Event()
        self.release_commit = asyncio.Event()
        self.commit_finished = asyncio.Event()
        self.session: _CommitRaceSession | None = None
        self.commit_task: asyncio.Task[None] | None = None
        self.rollback_suppressed = False


class _CommitRaceSession(AsyncSession):
    """Keep the apply transaction open after its client loses commit outcome."""

    def __init__(self, *, race: _CommitRace, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._race = race

    async def commit(self) -> None:
        if self._race.armed and self._race.session is self:
            self._race.armed = False
            self._race.commit_sent.set()
            self._race.commit_task = asyncio.create_task(self._finish_commit())
            # The transport has accepted COMMIT but disconnected before the
            # application received its outcome.  The real DB commit remains
            # pending behind release_commit, so another connection cannot see
            # the version/audit rows during the first reconciliation.
            raise DisconnectionError("synthetic unknown commit acknowledgement")
        await super().commit()

    async def _finish_commit(self) -> None:
        await self._race.release_commit.wait()
        try:
            await AsyncSession.commit(self)
        finally:
            self._race.commit_finished.set()

    async def rollback(self) -> None:
        # confirmed_write.py attempts a quiet rollback after it receives the
        # unknown outcome.  A real driver may have already sent COMMIT; this
        # harness therefore keeps that transaction alive until its outcome is
        # known instead of turning the race into a rollback-only test.
        if (
            self._race.commit_task is not None
            and not self._race.commit_finished.is_set()
        ):
            self._race.rollback_suppressed = True
            return
        await super().rollback()


class _HeldSessionContext:
    """Do not close the in-flight apply session before its commit settles."""

    def __init__(self, session: _CommitRaceSession, race: _CommitRace) -> None:
        self._session = session
        self._race = race

    async def __aenter__(self) -> _CommitRaceSession:
        return await self._session.__aenter__()

    async def __aexit__(self, type_: Any, value: Any, traceback: Any) -> None:
        if (
            self._race.commit_task is not None
            and not self._race.commit_finished.is_set()
        ):
            self._race.context_exited.set()
            return
        await self._session.__aexit__(type_, value, traceback)


class _RaceSessionFactory:
    """Use one held session for apply and ordinary sessions for observers."""

    def __init__(self, database: WriteDatabase, race: _CommitRace) -> None:
        self._database = database
        self._race = race

    def __call__(self):
        if self._race.armed:
            session = _CommitRaceSession(
                bind=self._database.engine,
                expire_on_commit=False,
                race=self._race,
            )
            self._race.session = session
            return _HeldSessionContext(session, self._race)
        return self._database.session_factory()


async def _audit_count(database: WriteDatabase, confirmation_id: object) -> int:
    async with database.session_factory() as session:
        value = await session.scalar(
            text(
                "SELECT COUNT(*) FROM agent_write_audit "
                "WHERE confirmation_id = :confirmation_id"
            ),
            {"confirmation_id": str(confirmation_id)},
        )
    assert type(value) is int
    return value


@pytest.mark.asyncio
async def test_inflight_commit_unknown_stays_reconcilable_until_audit_is_visible(
    write_database: WriteDatabase,
) -> None:
    """A transiently absent audit must not become terminal NOT_APPLIED."""

    api = write_api()
    race = _CommitRace()
    service = api.ConfirmedDailyPlanWriteService(
        session_factory=_RaceSessionFactory(write_database, race),
        clock=MutableClock(),
    )
    ui_session = trusted_ui_session()
    pending = await service.issue_confirmation(
        ui_session,
        build_patch(),
        expected_revision=1,
    )
    race.armed = True

    try:
        apply_task = asyncio.create_task(
            service.apply(ui_session, pending.confirmation_id)
        )
        await asyncio.wait_for(race.commit_sent.wait(), timeout=1)
        await asyncio.wait_for(race.context_exited.wait(), timeout=1)
        assert race.commit_task is not None
        assert not race.commit_task.done()
        assert race.rollback_suppressed is True
        assert await _audit_count(write_database, pending.confirmation_id) == 0

        with pytest.raises(api.ConfirmedWriteRejected) as unknown:
            await apply_task
        assert unknown.value.code == "commit_outcome_unknown"

        # The first explicit read races the original transaction.  Absence of
        # immutable evidence here is still indeterminate, not definitive
        # NOT_APPLIED; the current implementation incorrectly terminalizes it.
        with pytest.raises(api.ConfirmedWriteRejected) as first_reconcile:
            await service.reconcile(ui_session, pending.confirmation_id)
        assert first_reconcile.value.code == "confirmation_indeterminate"

        race.release_commit.set()
        await asyncio.wait_for(race.commit_task, timeout=1)
        assert race.commit_finished.is_set()
        assert await _audit_count(write_database, pending.confirmation_id) == 1

        with capture_sql(write_database.engine) as reconcile_statements:
            result = await service.reconcile(ui_session, pending.confirmation_id)
            repeated = await service.reconcile(ui_session, pending.confirmation_id)
        assert repeated == result
        assert result.before_revision == 1
        assert result.after_revision == 2
        assert dml_statements(reconcile_statements) == []

        # Reconciliation is read-only and must not make the original Patch
        # applicable again, regardless of how many readers observed it.
        with capture_sql(write_database.engine) as replay_statements:
            with pytest.raises(api.ConfirmedWriteRejected) as replay:
                await service.apply(ui_session, pending.confirmation_id)
        assert replay.value.code == "confirmation_indeterminate"
        assert dml_statements(replay_statements) == []
    finally:
        race.release_commit.set()
        if race.commit_task is not None:
            await race.commit_task
        if race.session is not None:
            await race.session.close()


@pytest.mark.asyncio
async def test_absent_audit_after_commit_unknown_remains_indeterminate(
    write_database: WriteDatabase,
) -> None:
    """A client-side rollback observation is not durable negative evidence."""

    api = write_api()
    service = api.ConfirmedDailyPlanWriteService(
        session_factory=write_database.session_factory,
        clock=MutableClock(),
    )
    ui_session = trusted_ui_session()
    pending = await service.issue_confirmation(
        ui_session,
        build_patch(),
        expected_revision=1,
    )

    def disconnect_before_commit(_connection) -> None:
        raise DisconnectionError("synthetic disconnect before COMMIT")

    event.listen(write_database.engine.sync_engine, "commit", disconnect_before_commit)
    try:
        with pytest.raises(api.ConfirmedWriteRejected) as unknown:
            await service.apply(ui_session, pending.confirmation_id)
    finally:
        event.remove(
            write_database.engine.sync_engine,
            "commit",
            disconnect_before_commit,
        )

    assert unknown.value.code == "commit_outcome_unknown"
    assert await _audit_count(write_database, pending.confirmation_id) == 0
    with pytest.raises(api.ConfirmedWriteRejected) as reconciled:
        await service.reconcile(ui_session, pending.confirmation_id)
    assert reconciled.value.code == "confirmation_indeterminate"
    assert await _audit_count(write_database, pending.confirmation_id) == 0

    # The consumed confirmation is still non-replayable.  Without durable
    # database-level negative evidence the application must not guess that an
    # unknown COMMIT was rolled back merely because the audit is absent now.
    with pytest.raises(api.ConfirmedWriteRejected) as replay:
        await service.apply(ui_session, pending.confirmation_id)
    assert replay.value.code == "confirmation_indeterminate"
