"""Narrow T005 upload orchestration for validated immutable versions."""

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
    TemplateSource,
    TemplateUnitOfWorkPort,
    TemplateValidationEvidence,
    TemplateValidationReceipt,
    TemplateVersionRef,
    ValidationStatus,
    VersionAllocation,
)
from app.service.template_center.validator import VALIDATOR_VERSION, validate_upload


class TemplateCenter:
    """T005-only service; lifecycle and exporter operations are intentionally absent."""

    __slots__ = (
        "_blob_store",
        "_transaction_port",
        "_permission_policy",
        "_contract_registry",
        "_clock",
    )

    def __init__(
        self,
        *,
        blob_store: TemplateBlobStorePort,
        transaction_port: TemplateUnitOfWorkPort,
        permission_policy: TemplatePermissionPolicyPort,
        contract_registry: object,
        clock: TemplateClockPort,
    ) -> None:
        self._blob_store = blob_store
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
    ) -> TemplateAuditEvent:
        return TemplateAuditEvent(
            event_id=uuid4(),
            action=TemplateCapability.UPLOAD,
            outcome=outcome,
            tenant_id=tenant_id,
            user_id=user_id,
            session_hash=TemplateCenter._session_hash(session_id),
            document_type=document_type,
            template_version_id=None,
            content_sha256=None,
            contract_id=None,
            contract_version=None,
            registry_revision=None,
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
