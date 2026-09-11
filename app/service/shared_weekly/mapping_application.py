"""Explicit manager preview/confirm; waiting for confirmation holds no transaction."""

from dataclasses import dataclass, replace
from hashlib import sha256
from uuid import UUID

from app.repository.source_mapping_repository import SourceMappingRepository
from app.service.academic_identity.application import IdentityApplication
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.candidates import CandidateStore
from app.service.shared_weekly.mapping_contracts import (
    MappingPreview,
    MappingStamp,
    MappingTarget,
)
from app.service.shared_weekly.root_contracts import canonical, operation
from app.ui.auth_context import TrustedUiSession, resolve_current_ui_session


@dataclass(frozen=True, slots=True)
class MappingBinding:
    target: MappingTarget
    preview: MappingPreview
    signature: str


class SourceMappingApplication:
    def __init__(self, factory, token_source):
        self._identity = IdentityApplication(factory, token_source)
        self._candidates = CandidateStore()

    async def _before(self, expected, target):
        if type(target) is not MappingTarget:
            raise IdentityRejected("input_invalid")
        async with self._identity._factory() as s:
            actor = await resolve_current_ui_session(s, self._identity._token_source())
            if actor is None or actor != expected:
                raise IdentityRejected("session_invalid")
            from app.repository.academic_identity_repository import IdentityRepository

            await IdentityRepository(s, actor.tenant_id).manager(actor.user_id)
            repo = SourceMappingRepository(s, actor.tenant_id)
            return dict(
                await repo.source_identity(target.daily_plan_id)
            ), await repo.mapping(target.daily_plan_id)

    async def _locked(self, identity, actor, target, before, old):
        await identity.manager(actor.user_id)
        repo = SourceMappingRepository(identity.session, actor.tenant_id)
        scopes = [(target.class_instance_id, target.semester_id)]
        if old:
            scopes.append((old["class_instance_id"], old["semester_id"]))
        assignments = await repo.lock_scopes(identity, scopes)
        binding = await repo.require_day_member(
            identity,
            before["user_id"],
            target.class_instance_id,
            target.semester_id,
            before["plan_date"],
            assignments,
        )
        source = await repo.source_identity(target.daily_plan_id, lock=True)
        mapping = await repo.mapping(target.daily_plan_id)
        if dict(source) != before or mapping != old:
            raise IdentityRejected("mapping_conflict")
        guards = [
            dict(
                await identity.require(
                    "class_semester", class_instance_id=c, semester_id=s
                )
            )
            for c, s in sorted(set(scopes))
        ]
        manager = dict(
            await identity.require("tenant_identity_manager", user_id=actor.user_id)
        )
        signature = sha256(
            canonical(
                [
                    str(binding),
                    str(guards),
                    str(manager),
                    str(dict(source)),
                    str(dict(mapping) if mapping else None),
                ]
            ).encode()
        ).hexdigest()
        preview = MappingPreview(
            "",
            source["id"],
            source["user_id"],
            source["plan_date"],
            source["revision"],
            source["grade"],
            source["class_name"],
            target.class_instance_id,
            target.semester_id,
            MappingStamp(mapping["mapping_id"], mapping["revision"])
            if mapping
            else None,
        )
        return repo, source, mapping, signature, preview

    async def preview(
        self, expected: TrustedUiSession, target: MappingTarget
    ) -> MappingPreview:
        before, old = await self._before(expected, target)
        async with self._identity.transaction(expected, (before["user_id"],)) as (
            identity,
            actor,
        ):
            _, _, _, signature, preview = await self._locked(
                identity, actor, target, before, old
            )
        key = self._candidates.put(expected, MappingBinding(target, preview, signature))
        return replace(preview, candidate_id=key)

    async def confirm(
        self,
        expected: TrustedUiSession,
        candidate_id: str,
        *,
        confirmed: bool,
        operation_id: UUID,
    ) -> MappingStamp:
        op = operation(operation_id)
        binding = self._candidates.take(expected, candidate_id)
        if confirmed is not True:
            raise IdentityRejected("confirmation_required")
        before, old = await self._before(expected, binding.target)
        async with self._identity.transaction(
            expected, (before["user_id"],), commit_unknown=True
        ) as (identity, actor):
            repo, source, mapping, signature, preview = await self._locked(
                identity, actor, binding.target, before, old
            )
            if signature != binding.signature or preview != binding.preview:
                raise IdentityRejected("mapping_conflict")
            result = await repo.save(
                binding.target,
                source,
                mapping,
                actor,
                sha256(str(actor.session_id).encode()).hexdigest(),
                signature,
                op,
            )
            # Event is the immutable body-free management audit and operation ledger.
        return result

    def cancel(self, expected: TrustedUiSession, candidate_id: str) -> None:
        self._candidates.cancel(expected, candidate_id)

    async def reconcile(
        self, expected: TrustedUiSession, operation_id: UUID
    ) -> MappingStamp | None:
        op = operation(operation_id)
        async with self._identity.transaction(expected) as (identity, actor):
            await identity.manager(actor.user_id)
            row = await SourceMappingRepository(
                identity.session, actor.tenant_id
            ).operation(op)
            if row is None:
                result = None
            elif (row["actor_id"], row["session_hash"]) != (
                actor.user_id,
                sha256(str(actor.session_id).encode()).hexdigest(),
            ):
                raise IdentityRejected("scope_denied")
            else:
                result = MappingStamp(row["id"], row["revision"])
        return result
