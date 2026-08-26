"""One-patch confirmation boundary for future atomic daily-plan writes.

W005 owns only the closed contract, authoritative issue-time validation, and a
short-lived process-local confirmation store.  The successful persistence and
evidence paths remain behind the private W006 seams in this module.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import secrets
from threading import Lock
from typing import Callable
from uuid import UUID, uuid4

from sqlalchemy.exc import DisconnectionError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.models.daily_plan import DailyPlan
from app.repository.confirmed_write_repository import (
    append_agent_write_audit,
    append_daily_plan_operation_version,
    cas_apply_daily_plan_fields,
    get_agent_write_audit_by_confirmation,
    get_daily_plan_operation_version_by_id,
)
from app.repository.daily_plan_repository import get_daily_plan_by_id_for_user
from app.repository.user_repository import get_user_by_id
from app.service.agent.canonical import canonical_json, canonical_sha256
from app.service.agent.patch import PlanPatch, plan_patch_is_canonical
from app.ui.auth_context import TrustedUiSession


_DEFAULT_CONFIRMATION_TTL = timedelta(minutes=5)
_DEFAULT_STORE_CAPACITY = 1_024
_AUDIT_ACTION = "daily_plan.apply_confirmed_patch"
_DAILY_PLAN_SNAPSHOT_FIELDS = frozenset(
    {
        "id",
        "tenant_id",
        "user_id",
        "revision",
        "plan_date",
        "week_number",
        "weekday_cn",
        "grade",
        "class_name",
        "activity_goal",
        "activity_prep",
        "activity_key",
        "activity_difficult",
        "activity_process_original",
        "activity_process_adapted",
        "morning_activity",
        "indoor_area",
        "outdoor_activity",
        "morning_talk_topic",
        "morning_talk_questions",
        "daily_reflection",
        "created_at",
        "updated_at",
    }
)


class ConfirmedWriteRejected(ValueError):
    """Fail closed with one content-free application error code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class PendingPlanPatchConfirmation:
    """The complete safe UI projection of one pending confirmation."""

    confirmation_id: UUID
    expires_at_utc: datetime
    daily_plan_id: int
    expected_revision: int
    patch_id: UUID
    patch_sha256: str
    field_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConfirmedDailyPlanWriteResult:
    """Identifiers and revisions returned by a successful W006 transaction."""

    before_version_id: int
    audit_id: int
    before_revision: int
    after_revision: int


class _ConfirmationState(str, Enum):
    PENDING = "pending"
    CONSUMING = "consuming"
    APPLIED = "applied"
    FAILED = "failed"
    INDETERMINATE = "indeterminate"


class _CommitOutcomeUnknown(Exception):
    """Signal that commit was attempted but its durable outcome is unknown."""


@dataclass(frozen=True, slots=True, repr=False)
class _UiSessionSnapshot:
    session_id: UUID = field(repr=False)
    tenant_id: int
    user_id: int
    role: str
    username: str
    display_name: str | None
    issued_at_utc: datetime
    expires_at_utc: datetime


@dataclass(frozen=True, slots=True, repr=False)
class _StoredConfirmation:
    confirmation_id: UUID
    nonce: bytes = field(repr=False)
    tenant_id: int
    user_id: int
    session_id: UUID = field(repr=False)
    patch: PlanPatch = field(repr=False)
    patch_id: UUID
    patch_sha256: str
    operation_id: UUID
    turn_id: UUID
    tool_name: str
    daily_plan_id: int
    plan_date: date
    expected_revision: int
    field_paths: tuple[str, ...]
    before_sha256s: tuple[str, ...]
    issued_at_utc: datetime
    expires_at_utc: datetime
    state: _ConfirmationState
    claim_token: bytes | None = field(default=None, repr=False)
    result: ConfirmedDailyPlanWriteResult | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True, repr=False)
class _ConfirmationClaim:
    record: _StoredConfirmation = field(repr=False)
    claim_token: bytes = field(repr=False)


def _reject(code: str) -> None:
    raise ConfirmedWriteRejected(code)


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


def _unchecked_session_snapshot(
    ui_session: object,
    *,
    now: datetime,
) -> _UiSessionSnapshot:
    if type(ui_session) is not TrustedUiSession:
        _reject("ui_session_invalid")
    if (
        type(ui_session.session_id) is not UUID
        or type(ui_session.tenant_id) is not int
        or ui_session.tenant_id <= 0
        or type(ui_session.user_id) is not int
        or ui_session.user_id <= 0
        or type(ui_session.role) is not str
        or not ui_session.role
        or type(ui_session.username) is not str
        or not ui_session.username
        or (
            ui_session.display_name is not None
            and type(ui_session.display_name) is not str
        )
        or type(ui_session.issued_at_utc) is not datetime
        or ui_session.issued_at_utc.tzinfo is None
        or type(ui_session.expires_at_utc) is not datetime
        or ui_session.expires_at_utc.tzinfo is None
    ):
        _reject("ui_session_invalid")
    issued_at = _as_utc(ui_session.issued_at_utc)
    expires_at = _as_utc(ui_session.expires_at_utc)
    if issued_at >= expires_at or issued_at > now or now >= expires_at:
        _reject("ui_session_invalid")
    return _UiSessionSnapshot(
        session_id=ui_session.session_id,
        tenant_id=ui_session.tenant_id,
        user_id=ui_session.user_id,
        role=ui_session.role,
        username=ui_session.username,
        display_name=ui_session.display_name,
        issued_at_utc=issued_at,
        expires_at_utc=expires_at,
    )


def _session_snapshot(
    ui_session: object,
    *,
    now: datetime,
) -> _UiSessionSnapshot:
    try:
        return _unchecked_session_snapshot(ui_session, now=now)
    except ConfirmedWriteRejected:
        raise
    except Exception:
        _reject("ui_session_invalid")


def _snapshot_datetime(value: object) -> str:
    if type(value) is not datetime:
        raise ValueError
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat()


def _daily_plan_snapshot(plan: DailyPlan) -> tuple[str, str]:
    snapshot = {
        "id": plan.id,
        "tenant_id": plan.tenant_id,
        "user_id": plan.user_id,
        "revision": plan.revision,
        "plan_date": plan.plan_date.isoformat(),
        "week_number": plan.week_number,
        "weekday_cn": plan.weekday_cn,
        "grade": plan.grade,
        "class_name": plan.class_name,
        "activity_goal": plan.activity_goal,
        "activity_prep": plan.activity_prep,
        "activity_key": plan.activity_key,
        "activity_difficult": plan.activity_difficult,
        "activity_process_original": plan.activity_process_original,
        "activity_process_adapted": plan.activity_process_adapted,
        "morning_activity": plan.morning_activity,
        "indoor_area": plan.indoor_area,
        "outdoor_activity": plan.outdoor_activity,
        "morning_talk_topic": plan.morning_talk_topic,
        "morning_talk_questions": plan.morning_talk_questions,
        "daily_reflection": plan.daily_reflection,
        "created_at": _snapshot_datetime(plan.created_at),
        "updated_at": _snapshot_datetime(plan.updated_at),
    }
    snapshot_json = canonical_json(snapshot)
    snapshot_sha256 = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()
    return snapshot_json, snapshot_sha256


def _nonce_sha256(nonce: bytes) -> str:
    return hashlib.sha256(b"agent-write:nonce:v1\0" + nonce).hexdigest()


def _session_sha256(session_id: UUID) -> str:
    return hashlib.sha256(b"agent-write:session:v1\0" + session_id.bytes).hexdigest()


async def _rollback_quietly(session: AsyncSession) -> None:
    try:
        await session.rollback()
    except BaseException:
        pass


class _InMemoryConfirmationStore:
    """Bounded process-local store with synchronous atomic state transitions."""

    def __init__(self, *, capacity: int = _DEFAULT_STORE_CAPACITY) -> None:
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self._capacity = capacity
        self._records: dict[UUID, _StoredConfirmation] = {}
        self._lock = Lock()

    @staticmethod
    def _binding_error(
        record: _StoredConfirmation,
        actor: _UiSessionSnapshot,
        now: datetime,
    ) -> str | None:
        if record.tenant_id != actor.tenant_id or record.user_id != actor.user_id:
            return "confirmation_actor_mismatch"
        if record.session_id != actor.session_id:
            return "confirmation_session_mismatch"
        if now >= record.expires_at_utc:
            return "confirmation_expired"
        return None

    def put_pending(self, record: _StoredConfirmation, *, now: datetime) -> None:
        with self._lock:
            removable = {
                confirmation_id
                for confirmation_id, existing in self._records.items()
                if existing.expires_at_utc <= now
                and existing.state
                not in {
                    _ConfirmationState.CONSUMING,
                    _ConfirmationState.INDETERMINATE,
                }
            }
            for confirmation_id in removable:
                del self._records[confirmation_id]
            if len(self._records) >= self._capacity:
                _reject("confirmation_store_full")
            if record.confirmation_id in self._records or any(
                secrets.compare_digest(existing.nonce, record.nonce)
                for existing in self._records.values()
            ):
                _reject("confirmation_collision")
            self._records[record.confirmation_id] = record

    def claim_apply(
        self,
        confirmation_id: object,
        *,
        actor: _UiSessionSnapshot,
        now: datetime,
    ) -> _ConfirmationClaim:
        with self._lock:
            record = (
                self._records.get(confirmation_id)
                if type(confirmation_id) is UUID
                else None
            )
            if record is None:
                _reject("confirmation_not_found")
            binding_error = self._binding_error(record, actor, now)
            if binding_error is not None:
                if binding_error == "confirmation_expired" and record.state in {
                    _ConfirmationState.PENDING,
                    _ConfirmationState.APPLIED,
                    _ConfirmationState.FAILED,
                }:
                    self._records[record.confirmation_id] = replace(
                        record,
                        state=_ConfirmationState.FAILED,
                        claim_token=None,
                        result=None,
                    )
                _reject(binding_error)
            if record.state is _ConfirmationState.CONSUMING:
                _reject("confirmation_consuming")
            if record.state is _ConfirmationState.INDETERMINATE:
                _reject("confirmation_indeterminate")
            if record.state is not _ConfirmationState.PENDING:
                _reject("confirmation_consumed")

            try:
                claim_token = secrets.token_bytes(32)
            except Exception:
                self._records[record.confirmation_id] = replace(
                    record,
                    state=_ConfirmationState.FAILED,
                    claim_token=None,
                    result=None,
                )
                _reject("write_unavailable")
            if type(claim_token) is not bytes or len(claim_token) != 32:
                self._records[record.confirmation_id] = replace(
                    record,
                    state=_ConfirmationState.FAILED,
                    claim_token=None,
                    result=None,
                )
                _reject("write_unavailable")
            consuming = replace(
                record,
                state=_ConfirmationState.CONSUMING,
                claim_token=claim_token,
            )
            self._records[record.confirmation_id] = consuming
            return _ConfirmationClaim(record=consuming, claim_token=claim_token)

    def get_for_reconcile(
        self,
        confirmation_id: object,
        *,
        actor: _UiSessionSnapshot,
        now: datetime,
    ) -> _StoredConfirmation:
        with self._lock:
            record = (
                self._records.get(confirmation_id)
                if type(confirmation_id) is UUID
                else None
            )
            if record is None:
                _reject("confirmation_indeterminate")
            binding_error = self._binding_error(record, actor, now)
            if binding_error is not None:
                _reject(binding_error)
            return record

    def _finish(
        self,
        claim: _ConfirmationClaim,
        *,
        state: _ConfirmationState,
        result: ConfirmedDailyPlanWriteResult | None = None,
    ) -> bool:
        with self._lock:
            current = self._records.get(claim.record.confirmation_id)
            if (
                current is None
                or current.state is not _ConfirmationState.CONSUMING
                or current.claim_token is None
                or not secrets.compare_digest(
                    current.claim_token,
                    claim.claim_token,
                )
            ):
                return False
            self._records[current.confirmation_id] = replace(
                current,
                state=state,
                claim_token=None,
                result=result,
            )
            return True

    def finish_applied(
        self,
        claim: _ConfirmationClaim,
        result: ConfirmedDailyPlanWriteResult,
    ) -> bool:
        return self._finish(
            claim,
            state=_ConfirmationState.APPLIED,
            result=result,
        )

    def finish_failed(self, claim: _ConfirmationClaim) -> bool:
        return self._finish(claim, state=_ConfirmationState.FAILED)

    def finish_indeterminate(self, claim: _ConfirmationClaim) -> bool:
        return self._finish(claim, state=_ConfirmationState.INDETERMINATE)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConfirmedDailyPlanWriteService:
    """Issue and consume confirmations without exposing persistence internals."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        clock: Callable[[], datetime] = _utc_now,
        confirmation_ttl: timedelta = _DEFAULT_CONFIRMATION_TTL,
        store_capacity: int = _DEFAULT_STORE_CAPACITY,
    ) -> None:
        if not callable(clock):
            raise TypeError("clock must be callable")
        if type(confirmation_ttl) is not timedelta or confirmation_ttl <= timedelta(0):
            raise ValueError("confirmation_ttl must be positive")
        self._session_factory = session_factory
        self._clock = clock
        self._confirmation_ttl = confirmation_ttl
        self._store = _InMemoryConfirmationStore(capacity=store_capacity)

    def _now(self) -> datetime:
        try:
            value = self._clock()
            if type(value) is not datetime or value.tzinfo is None:
                raise ValueError
            return _as_utc(value)
        except Exception:
            _reject("write_unavailable")

    @staticmethod
    async def _require_active_actor(
        session: AsyncSession,
        actor: _UiSessionSnapshot,
        *,
        for_update: bool = False,
    ) -> None:
        user = await get_user_by_id(
            session,
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            for_update=for_update,
        )
        if (
            user is None
            or not user.is_active
            or user.tenant_id != actor.tenant_id
            or user.id != actor.user_id
            or user.role.value != actor.role
            or user.username != actor.username
            or user.display_name != actor.display_name
        ):
            _reject("ui_session_invalid")

    @staticmethod
    def _authoritative_patch(patch: object) -> PlanPatch:
        try:
            if not plan_patch_is_canonical(patch):
                _reject("patch_invalid")
            copied = deepcopy(patch)
            if not plan_patch_is_canonical(copied):
                _reject("patch_invalid")
        except ConfirmedWriteRejected:
            raise
        except Exception:
            _reject("patch_invalid")
        return copied

    @staticmethod
    def _new_confirmation_material() -> tuple[UUID, bytes]:
        try:
            confirmation_id = uuid4()
            nonce = secrets.token_bytes(32)
        except Exception:
            _reject("write_unavailable")
        if (
            type(confirmation_id) is not UUID
            or type(nonce) is not bytes
            or len(nonce) != 32
        ):
            _reject("write_unavailable")
        return confirmation_id, nonce

    async def issue_confirmation(
        self,
        ui_session: TrustedUiSession,
        patch: PlanPatch,
        *,
        expected_revision: int,
    ) -> PendingPlanPatchConfirmation:
        """Validate one authoritative Patch and issue a short-lived opaque id."""
        authoritative_patch = self._authoritative_patch(patch)
        if type(expected_revision) is not int or expected_revision <= 0:
            _reject("revision_invalid")
        actor = _session_snapshot(ui_session, now=self._now())

        try:
            async with self._session_factory() as session:
                await self._require_active_actor(session, actor)
                plan = await get_daily_plan_by_id_for_user(
                    session,
                    tenant_id=actor.tenant_id,
                    user_id=actor.user_id,
                    plan_id=authoritative_patch.target.daily_plan_id,
                )
                if plan is None:
                    _reject("target_not_found")
                if plan.plan_date != authoritative_patch.target.plan_date:
                    _reject("target_mismatch")
                if plan.revision != expected_revision:
                    _reject("revision_mismatch")

                all_noop = True
                for operation in authoritative_patch.operations:
                    current_value = getattr(plan, operation.field_path) or ""
                    if canonical_sha256(current_value) != operation.before_sha256:
                        _reject("before_mismatch")
                    if current_value != operation.after_value:
                        all_noop = False
                if all_noop:
                    _reject("patch_noop")
        except ConfirmedWriteRejected:
            raise
        except asyncio.CancelledError:
            raise
        except Exception:
            _reject("write_unavailable")

        issued_at = self._now()
        if issued_at >= actor.expires_at_utc:
            _reject("ui_session_invalid")
        try:
            expires_at = min(
                issued_at + self._confirmation_ttl,
                actor.expires_at_utc,
            )
        except Exception:
            _reject("write_unavailable")
        if expires_at <= issued_at:
            _reject("ui_session_invalid")

        confirmation_id, nonce = self._new_confirmation_material()
        field_paths = tuple(
            operation.field_path for operation in authoritative_patch.operations
        )
        record = _StoredConfirmation(
            confirmation_id=confirmation_id,
            nonce=nonce,
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            session_id=actor.session_id,
            patch=authoritative_patch,
            patch_id=authoritative_patch.patch_id,
            patch_sha256=authoritative_patch.canonical_sha256,
            operation_id=authoritative_patch.operation_id,
            turn_id=authoritative_patch.turn_id,
            tool_name=authoritative_patch.tool_name,
            daily_plan_id=authoritative_patch.target.daily_plan_id,
            plan_date=authoritative_patch.target.plan_date,
            expected_revision=expected_revision,
            field_paths=field_paths,
            before_sha256s=tuple(
                operation.before_sha256 for operation in authoritative_patch.operations
            ),
            issued_at_utc=issued_at,
            expires_at_utc=expires_at,
            state=_ConfirmationState.PENDING,
        )
        self._store.put_pending(record, now=issued_at)
        return PendingPlanPatchConfirmation(
            confirmation_id=confirmation_id,
            expires_at_utc=expires_at,
            daily_plan_id=record.daily_plan_id,
            expected_revision=record.expected_revision,
            patch_id=record.patch_id,
            patch_sha256=record.patch_sha256,
            field_paths=record.field_paths,
        )

    @staticmethod
    async def _load_and_validate_plan(
        session: AsyncSession,
        record: _StoredConfirmation,
    ) -> DailyPlan:
        plan = await get_daily_plan_by_id_for_user(
            session,
            tenant_id=record.tenant_id,
            user_id=record.user_id,
            plan_id=record.daily_plan_id,
        )
        if plan is None:
            _reject("target_not_found")
        if plan.plan_date != record.plan_date:
            _reject("target_mismatch")
        if plan.revision != record.expected_revision:
            _reject("revision_mismatch")
        for operation in record.patch.operations:
            current_value = getattr(plan, operation.field_path) or ""
            if canonical_sha256(current_value) != operation.before_sha256:
                _reject("before_mismatch")
        return plan

    async def _apply_claimed(
        self,
        session: AsyncSession,
        claim: _ConfirmationClaim,
        actor: _UiSessionSnapshot,
    ) -> ConfirmedDailyPlanWriteResult:
        """Execute version, CAS, audit and commit in one bounded transaction."""
        record = claim.record
        try:
            plan = await self._load_and_validate_plan(session, record)

            # The first validation keeps stale/before rejection free of DML.
            # Lock and re-read the actor only after those checks, then refresh
            # the plan before the first evidence INSERT.
            await self._require_active_actor(
                session,
                actor,
                for_update=True,
            )
            session.expire(plan)
            plan = await self._load_and_validate_plan(session, record)

            created_at = self._now()
            snapshot_json, snapshot_sha256 = _daily_plan_snapshot(plan)
            field_paths_json = canonical_json(record.field_paths)
            version = await append_daily_plan_operation_version(
                session,
                tenant_id=record.tenant_id,
                user_id=record.user_id,
                daily_plan_id=record.daily_plan_id,
                confirmation_id=str(record.confirmation_id),
                patch_id=str(record.patch_id),
                patch_sha256=record.patch_sha256,
                operation_id=str(record.operation_id),
                turn_id=str(record.turn_id),
                before_revision=record.expected_revision,
                field_paths_json=field_paths_json,
                snapshot_json=snapshot_json,
                snapshot_sha256=snapshot_sha256,
                created_at=created_at,
            )
            if type(version.id) is not int or version.id <= 0:
                _reject("write_failed")

            updated = await cas_apply_daily_plan_fields(
                session,
                tenant_id=record.tenant_id,
                user_id=record.user_id,
                daily_plan_id=record.daily_plan_id,
                expected_revision=record.expected_revision,
                field_values={
                    operation.field_path: operation.after_value
                    for operation in record.patch.operations
                },
                updated_at=created_at,
            )
            if not updated:
                _reject("revision_mismatch")

            audit = await append_agent_write_audit(
                session,
                confirmation_id=str(record.confirmation_id),
                nonce_sha256=_nonce_sha256(record.nonce),
                session_sha256=_session_sha256(record.session_id),
                tenant_id=record.tenant_id,
                user_id=record.user_id,
                daily_plan_id=record.daily_plan_id,
                patch_id=str(record.patch_id),
                patch_sha256=record.patch_sha256,
                operation_id=str(record.operation_id),
                turn_id=str(record.turn_id),
                field_paths_json=field_paths_json,
                before_version_id=version.id,
                before_revision=record.expected_revision,
                after_revision=record.expected_revision + 1,
                action=_AUDIT_ACTION,
                created_at=created_at,
            )
            if type(audit.id) is not int or audit.id <= 0:
                _reject("write_failed")

            result = ConfirmedDailyPlanWriteResult(
                before_version_id=version.id,
                audit_id=audit.id,
                before_revision=record.expected_revision,
                after_revision=record.expected_revision + 1,
            )
            try:
                await session.commit()
            except DisconnectionError:
                await _rollback_quietly(session)
                raise _CommitOutcomeUnknown from None
            return result
        except _CommitOutcomeUnknown:
            raise
        except asyncio.CancelledError:
            await _rollback_quietly(session)
            raise
        except ConfirmedWriteRejected:
            await _rollback_quietly(session)
            raise
        except Exception:
            await _rollback_quietly(session)
            _reject("write_failed")

    async def apply(
        self,
        ui_session: TrustedUiSession,
        confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult:
        """Atomically consume one confirmation before entering the W006 seam."""
        actor = _session_snapshot(ui_session, now=self._now())
        claim = self._store.claim_apply(
            confirmation_id,
            actor=actor,
            now=self._now(),
        )
        try:
            async with self._session_factory() as session:
                await self._require_active_actor(session, actor)
                result = await self._apply_claimed(session, claim, actor)
        except _CommitOutcomeUnknown:
            self._store.finish_indeterminate(claim)
            _reject("commit_outcome_unknown")
        except ConfirmedWriteRejected:
            self._store.finish_failed(claim)
            raise
        except asyncio.CancelledError:
            self._store.finish_failed(claim)
            raise
        except Exception:
            self._store.finish_failed(claim)
            _reject("write_failed")

        if not self._store.finish_applied(claim, result):
            _reject("write_failed")
        return result

    @staticmethod
    def _version_snapshot_matches(
        version,
        record: _StoredConfirmation,
    ) -> bool:
        try:
            if (
                version.tenant_id != record.tenant_id
                or version.user_id != record.user_id
                or version.daily_plan_id != record.daily_plan_id
                or version.confirmation_id != str(record.confirmation_id)
                or version.patch_id != str(record.patch_id)
                or version.patch_sha256 != record.patch_sha256
                or version.operation_id != str(record.operation_id)
                or version.turn_id != str(record.turn_id)
                or version.before_revision != record.expected_revision
                or version.field_paths_json != canonical_json(record.field_paths)
                or hashlib.sha256(version.snapshot_json.encode("utf-8")).hexdigest()
                != version.snapshot_sha256
            ):
                return False
            snapshot = json.loads(version.snapshot_json)
            if (
                type(snapshot) is not dict
                or set(snapshot) != _DAILY_PLAN_SNAPSHOT_FIELDS
                or canonical_json(snapshot) != version.snapshot_json
                or snapshot["id"] != record.daily_plan_id
                or snapshot["tenant_id"] != record.tenant_id
                or snapshot["user_id"] != record.user_id
                or snapshot["revision"] != record.expected_revision
                or snapshot["plan_date"] != record.plan_date.isoformat()
            ):
                return False
            for operation in record.patch.operations:
                before_value = snapshot[operation.field_path] or ""
                if canonical_sha256(before_value) != operation.before_sha256:
                    return False
            return True
        except Exception:
            return False

    async def _reconcile_evidence(
        self,
        session: AsyncSession,
        record: _StoredConfirmation,
    ) -> ConfirmedDailyPlanWriteResult:
        """Reconcile immutable evidence in a new read-only transaction."""
        audit = await get_agent_write_audit_by_confirmation(
            session,
            confirmation_id=str(record.confirmation_id),
        )
        if audit is None:
            if record.state is _ConfirmationState.INDETERMINATE:
                _reject("commit_not_applied")
            _reject("reconcile_integrity_failure")

        version = await get_daily_plan_operation_version_by_id(
            session,
            version_id=audit.before_version_id,
        )
        plan = await get_daily_plan_by_id_for_user(
            session,
            tenant_id=record.tenant_id,
            user_id=record.user_id,
            plan_id=record.daily_plan_id,
        )
        expected_field_paths_json = canonical_json(record.field_paths)
        if (
            version is None
            or plan is None
            or not self._version_snapshot_matches(version, record)
            or audit.confirmation_id != str(record.confirmation_id)
            or audit.nonce_sha256 != _nonce_sha256(record.nonce)
            or audit.session_sha256 != _session_sha256(record.session_id)
            or audit.tenant_id != record.tenant_id
            or audit.user_id != record.user_id
            or audit.daily_plan_id != record.daily_plan_id
            or audit.patch_id != str(record.patch_id)
            or audit.patch_sha256 != record.patch_sha256
            or audit.operation_id != str(record.operation_id)
            or audit.turn_id != str(record.turn_id)
            or audit.field_paths_json != expected_field_paths_json
            or audit.before_version_id != version.id
            or audit.before_revision != record.expected_revision
            or audit.after_revision != record.expected_revision + 1
            or audit.action != _AUDIT_ACTION
            or plan.plan_date != record.plan_date
            or plan.revision != audit.after_revision
            or any(
                (getattr(plan, operation.field_path) or "") != operation.after_value
                for operation in record.patch.operations
            )
        ):
            _reject("reconcile_integrity_failure")

        result = ConfirmedDailyPlanWriteResult(
            before_version_id=version.id,
            audit_id=audit.id,
            before_revision=audit.before_revision,
            after_revision=audit.after_revision,
        )
        if record.state is _ConfirmationState.APPLIED and record.result != result:
            _reject("reconcile_integrity_failure")
        return result

    async def reconcile(
        self,
        ui_session: TrustedUiSession,
        confirmation_id: UUID,
    ) -> ConfirmedDailyPlanWriteResult:
        """Read one bound terminal state; never replay a confirmation."""
        actor = _session_snapshot(ui_session, now=self._now())
        record = self._store.get_for_reconcile(
            confirmation_id,
            actor=actor,
            now=self._now(),
        )
        try:
            async with self._session_factory() as session:
                await self._require_active_actor(session, actor)
                if record.state in {
                    _ConfirmationState.APPLIED,
                    _ConfirmationState.INDETERMINATE,
                }:
                    return await self._reconcile_evidence(session, record)
        except ConfirmedWriteRejected:
            raise
        except asyncio.CancelledError:
            raise
        except Exception:
            _reject("write_unavailable")

        if record.state is _ConfirmationState.CONSUMING:
            _reject("confirmation_consuming")
        if record.state is _ConfirmationState.FAILED:
            _reject("confirmation_consumed")
        _reject("confirmation_not_applied")
