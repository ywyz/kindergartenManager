"""Narrow T005/T006 orchestration for immutable versions and active pointers."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID, uuid4

from app.service.template_center.contracts import (
    AuditOutcome,
    BlobRef,
    CommitReceipt,
    DocumentType,
    PermissionDecision,
    TemplateAuditEvent,
    TemplateBlobStorePort,
    TemplateCapability,
    TemplateCenterError,
    TemplateClockPort,
    TemplateContractManifest,
    TemplateErrorCode,
    TemplatePermissionPolicyPort,
    TemplateRegistryState,
    TemplateSource,
    TemplateTransitionEvent,
    TemplateUnitOfWorkPort,
    TemplateValidationEvidence,
    TemplateValidationReceipt,
    TemplateVersionRef,
    TemplateVersionStorePort,
    TransitionReceipt,
    ValidationStatus,
    VersionAllocation,
)
from app.service.template_center.validator import VALIDATOR_VERSION, validate_upload


class _InvalidVersionEvidence(Exception):
    """Internal marker retaining only safe immutable metadata for rejection audit."""

    def __init__(self, version: TemplateVersionRef | None) -> None:
        self.version = version
        super().__init__(TemplateErrorCode.VALIDATION_FAILED.value)


class TemplateCenter:
    """Upload and CAS lifecycle service; UI/exporter operations remain absent."""

    __slots__ = (
        "_blob_store",
        "_version_store",
        "_transaction_port",
        "_permission_policy",
        "_contract_registry",
        "_clock",
    )

    def __init__(
        self,
        *,
        blob_store: TemplateBlobStorePort,
        version_store: TemplateVersionStorePort | None = None,
        transaction_port: TemplateUnitOfWorkPort,
        permission_policy: TemplatePermissionPolicyPort,
        contract_registry: object,
        clock: TemplateClockPort,
    ) -> None:
        self._blob_store = blob_store
        self._version_store = version_store
        self._transaction_port = transaction_port
        self._permission_policy = permission_policy
        self._contract_registry = contract_registry
        self._clock = clock

    @staticmethod
    def _session_scope(actor: object) -> tuple[int, int, UUID]:
        tenant_id = getattr(actor, "tenant_id", None)
        user_id = getattr(actor, "user_id", None)
        session_id = getattr(actor, "session_id", None)
        if (
            type(tenant_id) is not int
            or tenant_id <= 0
            or type(user_id) is not int
            or user_id <= 0
            or type(session_id) is not UUID
        ):
            raise TemplateCenterError(TemplateErrorCode.TENANT_MISMATCH)
        return tenant_id, user_id, session_id

    @staticmethod
    def _session_hash(session_id: UUID) -> str:
        return sha256(str(session_id).encode("ascii")).hexdigest()

    def _now(self) -> datetime:
        now = self._clock.utcnow()
        if type(now) is not datetime or now.tzinfo is not timezone.utc:
            raise TemplateCenterError(TemplateErrorCode.STORAGE_FAILED)
        return now

    @staticmethod
    def _rejection_event(
        *,
        outcome: AuditOutcome,
        tenant_id: int,
        user_id: int,
        session_id: UUID,
        document_type: DocumentType,
        occurred_at_utc: datetime,
        action: TemplateCapability = TemplateCapability.UPLOAD,
        version: TemplateVersionRef | None = None,
        registry_revision: int | None = None,
    ) -> TemplateAuditEvent:
        return TemplateAuditEvent(
            event_id=uuid4(),
            action=action,
            outcome=outcome,
            tenant_id=tenant_id,
            user_id=user_id,
            session_hash=TemplateCenter._session_hash(session_id),
            document_type=document_type,
            template_version_id=(
                version.template_version_id if version is not None else None
            ),
            content_sha256=version.content_sha256 if version is not None else None,
            contract_id=version.contract_id if version is not None else None,
            contract_version=version.contract_version if version is not None else None,
            registry_revision=registry_revision,
            occurred_at_utc=occurred_at_utc,
        )

    async def _commit_rejection(
        self,
        *,
        outcome: AuditOutcome,
        tenant_id: int,
        user_id: int,
        session_id: UUID,
        document_type: DocumentType,
        action: TemplateCapability = TemplateCapability.UPLOAD,
        version: TemplateVersionRef | None = None,
        registry_revision: int | None = None,
    ) -> None:
        try:
            unit = await self._transaction_port.begin(tenant_id, document_type)
            await unit.stage_audit(
                self._rejection_event(
                    outcome=outcome,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=session_id,
                    document_type=document_type,
                    occurred_at_utc=self._now(),
                    action=action,
                    version=version,
                    registry_revision=registry_revision,
                )
            )
            receipt = await unit.commit()
            if type(receipt) is not CommitReceipt or receipt.committed is not True:
                raise RuntimeError("invalid commit receipt")
        except TemplateCenterError:
            raise
        except Exception as error:
            raise TemplateCenterError(TemplateErrorCode.STORAGE_FAILED) from error

    @staticmethod
    def _receipt_matches(
        receipt: object,
        *,
        content: bytes,
        contract: TemplateContractManifest,
    ) -> bool:
        return (
            type(receipt) is TemplateValidationReceipt
            and receipt.content_sha256 == sha256(content).hexdigest()
            and receipt.size_bytes == len(content)
            and receipt.contract_id == contract.contract_id
            and receipt.contract_version == contract.contract_version
            and receipt.structural_profile_id == contract.structural_profile_id
            and receipt.structural_profile_version
            == contract.structural_profile_version
            and receipt.validator_version == VALIDATOR_VERSION
        )

    async def upload(
        self,
        actor: object,
        *,
        document_type: str | DocumentType,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> TemplateVersionRef:
        tenant_id, user_id, session_id = self._session_scope(actor)
        contract = self._contract_registry.resolve(document_type)
        normalized_type = (
            document_type
            if type(document_type) is DocumentType
            else DocumentType(document_type)
        )

        try:
            decision = await self._permission_policy.authorize(
                actor,
                TemplateCapability.UPLOAD,
                normalized_type,
                tenant_id,
            )
        except Exception as error:
            decision = None
            authorization_error = error
        else:
            authorization_error = None
        if type(decision) is not PermissionDecision or decision.allowed is not True:
            await self._commit_rejection(
                outcome=AuditOutcome.DENIED,
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                document_type=normalized_type,
            )
            denial = TemplateCenterError(TemplateErrorCode.PERMISSION_DENIED)
            if authorization_error is not None:
                denial.__cause__ = authorization_error
            raise denial

        try:
            receipt = validate_upload(content, filename, content_type, contract)
        except Exception as error:
            await self._commit_rejection(
                outcome=AuditOutcome.REJECTED,
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                document_type=normalized_type,
            )
            rejection = TemplateCenterError(TemplateErrorCode.VALIDATION_FAILED)
            rejection.__cause__ = error
            raise rejection
        if not self._receipt_matches(receipt, content=content, contract=contract):
            await self._commit_rejection(
                outcome=AuditOutcome.REJECTED,
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                document_type=normalized_type,
            )
            raise TemplateCenterError(TemplateErrorCode.VALIDATION_FAILED)

        now = self._now()
        evidence = TemplateValidationEvidence.from_receipt(
            uuid4(), receipt, validated_at_utc=now
        )
        try:
            unit = await self._transaction_port.begin(tenant_id, normalized_type)
            allocation = await unit.allocate_version()
            if (
                type(allocation) is not VersionAllocation
                or allocation.tenant_id != tenant_id
                or allocation.document_type is not normalized_type
            ):
                raise RuntimeError("invalid version allocation")
            blob_ref = await self._blob_store.put_if_absent(
                receipt.content_sha256, content
            )
            if (
                type(blob_ref) is not BlobRef
                or blob_ref.content_sha256 != receipt.content_sha256
                or blob_ref.value != f"sha256/{receipt.content_sha256}"
            ):
                raise RuntimeError("invalid blob reference")
            version = TemplateVersionRef(
                template_version_id=allocation.template_version_id,
                tenant_id=tenant_id,
                document_type=normalized_type,
                version=allocation.version,
                content_sha256=receipt.content_sha256,
                size_bytes=receipt.size_bytes,
                mime_type=receipt.mime_type,
                extension=receipt.extension,
                blob_ref=blob_ref.value,
                contract_id=receipt.contract_id,
                contract_version=receipt.contract_version,
                validation_receipt_id=evidence.validation_receipt_id,
                validation_status=ValidationStatus.VALIDATED,
                validated_at_utc=now,
                validator_version=receipt.validator_version,
                source=TemplateSource.UPLOAD,
                created_by_user_id=user_id,
                created_at_utc=now,
                validation_evidence=evidence,
            )
            await unit.stage_version(allocation, version)
            await unit.stage_audit(
                TemplateAuditEvent(
                    event_id=uuid4(),
                    action=TemplateCapability.UPLOAD,
                    outcome=AuditOutcome.ACCEPTED,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_hash=self._session_hash(session_id),
                    document_type=normalized_type,
                    template_version_id=version.template_version_id,
                    content_sha256=version.content_sha256,
                    contract_id=version.contract_id,
                    contract_version=version.contract_version,
                    registry_revision=None,
                    occurred_at_utc=now,
                )
            )
            commit_receipt = await unit.commit()
            if (
                type(commit_receipt) is not CommitReceipt
                or commit_receipt.committed is not True
            ):
                raise RuntimeError("invalid commit receipt")
        except TemplateCenterError:
            raise
        except Exception as error:
            raise TemplateCenterError(TemplateErrorCode.STORAGE_FAILED) from error
        return version

    @staticmethod
    def _expected_pointer(
        expected_registry_revision: object,
        expected_active_version_id: object,
    ) -> tuple[int, UUID | None]:
        if (
            type(expected_registry_revision) is not int
            or expected_registry_revision < 0
            or (
                expected_active_version_id is not None
                and type(expected_active_version_id) is not UUID
            )
        ):
            raise TemplateCenterError(TemplateErrorCode.INPUT_INVALID)
        return expected_registry_revision, expected_active_version_id

    async def _authorize_lifecycle(
        self,
        actor: object,
        *,
        action: TemplateCapability,
        document_type: DocumentType,
        tenant_id: int,
        user_id: int,
        session_id: UUID,
    ) -> None:
        try:
            decision = await self._permission_policy.authorize(
                actor, action, document_type, tenant_id
            )
        except Exception as error:
            decision = None
            authorization_error = error
        else:
            authorization_error = None
        if type(decision) is PermissionDecision and decision.allowed is True:
            return
        await self._commit_rejection(
            outcome=AuditOutcome.DENIED,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            document_type=document_type,
            action=action,
        )
        denial = TemplateCenterError(TemplateErrorCode.PERMISSION_DENIED)
        if authorization_error is not None:
            denial.__cause__ = authorization_error
        raise denial

    async def _snapshot(
        self, tenant_id: int, document_type: DocumentType
    ) -> TemplateRegistryState:
        if self._version_store is None:
            raise TemplateCenterError(TemplateErrorCode.STORAGE_FAILED)
        try:
            snapshot = await self._version_store.snapshot(tenant_id, document_type)
        except TemplateCenterError:
            raise
        except Exception as error:
            raise TemplateCenterError(TemplateErrorCode.STORAGE_FAILED) from error
        if (
            type(snapshot) is not TemplateRegistryState
            or snapshot.tenant_id != tenant_id
            or snapshot.document_type is not document_type
        ):
            raise TemplateCenterError(TemplateErrorCode.STORAGE_FAILED)
        return snapshot

    async def _validated_target(
        self,
        *,
        tenant_id: int,
        document_type: DocumentType,
        version_id: UUID,
    ) -> TemplateVersionRef | None:
        if self._version_store is None:
            raise TemplateCenterError(TemplateErrorCode.STORAGE_FAILED)
        try:
            version = await self._version_store.get_version(tenant_id, version_id)
        except Exception as error:
            raise TemplateCenterError(TemplateErrorCode.STORAGE_FAILED) from error
        if version is None:
            return None
        if type(version) is not TemplateVersionRef:
            raise _InvalidVersionEvidence(None)
        if version.tenant_id != tenant_id or version.document_type is not document_type:
            raise _InvalidVersionEvidence(None)
        try:
            contract = self._contract_registry.resolve(document_type)
            evidence = version.validation_evidence
            blob_ref = BlobRef(
                value=version.blob_ref, content_sha256=version.content_sha256
            )
            exists = await self._blob_store.exists(blob_ref, version.content_sha256)
        except Exception as error:
            raise TemplateCenterError(TemplateErrorCode.STORAGE_FAILED) from error
        if (
            version.validation_status is not ValidationStatus.VALIDATED
            or version.contract_id != contract.contract_id
            or version.contract_version != contract.contract_version
            or evidence.content_sha256 != version.content_sha256
            or evidence.structural_profile_id != contract.structural_profile_id
            or evidence.structural_profile_version
            != contract.structural_profile_version
            or exists is not True
        ):
            raise _InvalidVersionEvidence(version)
        return version

    async def _stale(
        self,
        *,
        tenant_id: int,
        user_id: int,
        session_id: UUID,
        document_type: DocumentType,
        action: TemplateCapability,
        registry_revision: int,
        version: TemplateVersionRef | None = None,
    ) -> None:
        await self._commit_rejection(
            outcome=AuditOutcome.STALE,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            document_type=document_type,
            action=action,
            version=version,
            registry_revision=registry_revision,
        )
        raise TemplateCenterError(TemplateErrorCode.REGISTRY_STALE)

    async def _transition(
        self,
        actor: object,
        *,
        action: TemplateCapability,
        document_type: str | DocumentType,
        target_version_id: UUID | None,
        expected_registry_revision: int,
        expected_active_version_id: UUID | None,
    ) -> TransitionReceipt:
        tenant_id, user_id, session_id = self._session_scope(actor)
        try:
            self._contract_registry.resolve(document_type)
            normalized_type = (
                document_type
                if type(document_type) is DocumentType
                else DocumentType(document_type)
            )
        except Exception as error:
            if isinstance(error, TemplateCenterError):
                raise
            raise TemplateCenterError(
                TemplateErrorCode.UNKNOWN_DOCUMENT_TYPE
            ) from error
        expected_revision, expected_active = self._expected_pointer(
            expected_registry_revision, expected_active_version_id
        )
        if target_version_id is not None and type(target_version_id) is not UUID:
            raise TemplateCenterError(TemplateErrorCode.INPUT_INVALID)
        await self._authorize_lifecycle(
            actor,
            action=action,
            document_type=normalized_type,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
        )
        snapshot = await self._snapshot(tenant_id, normalized_type)
        current_version = None
        if snapshot.active_version_id is not None:
            try:
                current_version = await self._validated_target(
                    tenant_id=tenant_id,
                    document_type=normalized_type,
                    version_id=snapshot.active_version_id,
                )
            except _InvalidVersionEvidence as invalid:
                await self._commit_rejection(
                    outcome=AuditOutcome.REJECTED,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=session_id,
                    document_type=normalized_type,
                    action=action,
                    version=invalid.version,
                    registry_revision=snapshot.registry_revision,
                )
                raise TemplateCenterError(
                    TemplateErrorCode.VALIDATION_FAILED
                ) from invalid
        if (
            snapshot.registry_revision != expected_revision
            or snapshot.active_version_id != expected_active
        ):
            await self._stale(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                document_type=normalized_type,
                action=action,
                registry_revision=snapshot.registry_revision,
                version=current_version,
            )
        if target_version_id is None:
            target = None
        else:
            try:
                target = await self._validated_target(
                    tenant_id=tenant_id,
                    document_type=normalized_type,
                    version_id=target_version_id,
                )
            except _InvalidVersionEvidence as invalid:
                await self._commit_rejection(
                    outcome=AuditOutcome.REJECTED,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=session_id,
                    document_type=normalized_type,
                    action=action,
                    version=invalid.version,
                    registry_revision=snapshot.registry_revision,
                )
                raise TemplateCenterError(
                    TemplateErrorCode.VALIDATION_FAILED
                ) from invalid
            if target is None:
                await self._commit_rejection(
                    outcome=AuditOutcome.DENIED,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=session_id,
                    document_type=normalized_type,
                    action=action,
                    registry_revision=snapshot.registry_revision,
                )
                raise TemplateCenterError(TemplateErrorCode.VERSION_NOT_FOUND)
        new_revision = snapshot.registry_revision + 1
        now = self._now()
        transition = TemplateTransitionEvent(
            event_id=uuid4(),
            tenant_id=tenant_id,
            document_type=normalized_type,
            registry_revision=new_revision,
            active_version_id=(
                target.template_version_id if target is not None else None
            ),
            active_content_sha256=(
                target.content_sha256 if target is not None else None
            ),
            occurred_at_utc=now,
        )
        audit_version = target if target is not None else current_version
        try:
            unit = await self._transaction_port.begin(tenant_id, normalized_type)
            await unit.stage_transition(
                transition,
                expected_registry_revision=expected_revision,
                expected_active_version_id=expected_active,
            )
            await unit.stage_audit(
                TemplateAuditEvent(
                    event_id=uuid4(),
                    action=action,
                    outcome=AuditOutcome.ACCEPTED,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_hash=self._session_hash(session_id),
                    document_type=normalized_type,
                    template_version_id=(
                        audit_version.template_version_id
                        if audit_version is not None
                        else None
                    ),
                    content_sha256=(
                        audit_version.content_sha256
                        if audit_version is not None
                        else None
                    ),
                    contract_id=(
                        audit_version.contract_id if audit_version is not None else None
                    ),
                    contract_version=(
                        audit_version.contract_version
                        if audit_version is not None
                        else None
                    ),
                    registry_revision=new_revision,
                    occurred_at_utc=now,
                )
            )
            receipt = await unit.commit()
            if type(receipt) is not CommitReceipt or receipt.committed is not True:
                raise RuntimeError("invalid commit receipt")
        except TemplateCenterError as error:
            if error.code is TemplateErrorCode.REGISTRY_STALE:
                latest = await self._snapshot(tenant_id, normalized_type)
                await self._stale(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=session_id,
                    document_type=normalized_type,
                    action=action,
                    registry_revision=latest.registry_revision,
                    version=audit_version,
                )
            raise
        except Exception as error:
            raise TemplateCenterError(TemplateErrorCode.STORAGE_FAILED) from error
        return TransitionReceipt(
            document_type=normalized_type,
            active_version_id=transition.active_version_id,
            registry_revision=new_revision,
            content_sha256=transition.active_content_sha256,
        )

    async def activate(
        self,
        actor: object,
        *,
        document_type: str | DocumentType,
        version_id: UUID,
        expected_registry_revision: int,
        expected_active_version_id: UUID | None,
    ) -> TransitionReceipt:
        return await self._transition(
            actor,
            action=TemplateCapability.ACTIVATE,
            document_type=document_type,
            target_version_id=version_id,
            expected_registry_revision=expected_registry_revision,
            expected_active_version_id=expected_active_version_id,
        )

    async def deactivate(
        self,
        actor: object,
        *,
        document_type: str | DocumentType,
        expected_registry_revision: int,
        expected_active_version_id: UUID | None,
    ) -> TransitionReceipt:
        return await self._transition(
            actor,
            action=TemplateCapability.DEACTIVATE,
            document_type=document_type,
            target_version_id=None,
            expected_registry_revision=expected_registry_revision,
            expected_active_version_id=expected_active_version_id,
        )

    async def rollback(
        self,
        actor: object,
        *,
        document_type: str | DocumentType,
        target_version_id: UUID,
        expected_registry_revision: int,
        expected_active_version_id: UUID | None,
    ) -> TransitionReceipt:
        return await self._transition(
            actor,
            action=TemplateCapability.ROLLBACK,
            document_type=document_type,
            target_version_id=target_version_id,
            expected_registry_revision=expected_registry_revision,
            expected_active_version_id=expected_active_version_id,
        )
