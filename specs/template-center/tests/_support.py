"""Deterministic fakes and synthetic OOXML bytes for template-center RED tests.

This module deliberately contains no production imports from the not-yet-existing
template-center service.  Every test imports that public seam lazily so collection
stays clean while the formal implementation is absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


KNOWN_TYPES = (
    "daily_plan",
    "game_observation",
    "one_on_one_listening",
    "homemade_teaching",
    "course_review_activity",
    "weekly_activity_plan",
    "monthly_theme_activity_plan",
)

INITIAL_TYPES = KNOWN_TYPES[:5]
RESERVED_TYPES = KNOWN_TYPES[5:]


class MemoryVersionStore:
    """Read-side store; writes are visible only through MemoryUnitOfWork.commit."""

    def __init__(self) -> None:
        self.versions: list[object] = []
        self.transitions: list[object] = []
        self.active: dict[tuple[int, str], object | None] = {}

    async def get_version(self, tenant_id: int, version_id: UUID) -> object | None:
        return next(
            (
                version
                for version in self.versions
                if getattr(version, "tenant_id", None) == tenant_id
                and getattr(version, "template_version_id", None) == version_id
            ),
            None,
        )

    async def snapshot(self, tenant_id: int, document_type: str) -> object:
        key = (tenant_id, document_type)
        return SimpleNamespace(
            tenant_id=tenant_id,
            document_type=document_type,
            registry_revision=sum(
                1
                for event in self.transitions
                if getattr(event, "tenant_id", None) == tenant_id
                and getattr(event, "document_type", None) == document_type
            ),
            active_version_id=self.active.get(key),
        )


class MemoryAuditSink:
    """Committed audit events only; staging is owned by MemoryUnitOfWork."""

    def __init__(self) -> None:
        self.events: list[object] = []
        self.fail = False


class MemoryUnitOfWork:
    """A deterministic staged transaction with no record-level delete/update."""

    def __init__(
        self,
        version_store: MemoryVersionStore,
        audit_sink: MemoryAuditSink,
        owner: "MemoryTransactionPort",
        tenant_id: int,
        document_type: object,
    ) -> None:
        self.version_store = version_store
        self.audit_sink = audit_sink
        self.owner = owner
        self.tenant_id = tenant_id
        self.document_type = document_type
        self.staged_versions: list[object] = []
        self.staged_transitions: list[object] = []
        self.staged_audits: list[object] = []
        self.stage_calls: list[str] = []
        self.committed = False
        self.allocations: dict[UUID, object] = {}
        self.consumed_allocations: set[UUID] = set()

    async def allocate_version(self) -> object:
        from app.service import template_center as api

        self.owner.events.append("allocate_version")
        key = (
            self.tenant_id,
            getattr(self.document_type, "value", self.document_type),
        )
        version = self.owner.version_sequences.get(key, 0) + 1
        self.owner.version_sequences[key] = version
        allocation = api.VersionAllocation(
            template_version_id=uuid4(),
            tenant_id=self.tenant_id,
            document_type=api.DocumentType(key[1]),
            version=version,
        )
        self.allocations[allocation.template_version_id] = allocation
        return allocation

    async def stage_version(self, allocation: object, version: object) -> None:
        from app.service import template_center as api

        self.owner.events.append("stage_version")
        if self.owner.fail_stage_version:
            raise RuntimeError("synthetic version staging failure")
        if (
            type(allocation) is not api.VersionAllocation
            or self.allocations.get(allocation.template_version_id) is not allocation
            or allocation.template_version_id in self.consumed_allocations
            or type(version) is not api.TemplateVersionRef
            or version.template_version_id != allocation.template_version_id
            or version.tenant_id != allocation.tenant_id
            or version.document_type is not allocation.document_type
            or version.version != allocation.version
        ):
            raise api.TemplateCenterError(api.TemplateErrorCode.STORAGE_FAILED)
        self.consumed_allocations.add(allocation.template_version_id)
        self.stage_calls.append("version")
        self.staged_versions.append(version)

    async def stage_transition(self, event: object) -> None:
        self.owner.events.append("stage_transition")
        self.stage_calls.append("transition")
        self.staged_transitions.append(event)

    async def stage_audit(self, event: object) -> None:
        self.owner.events.append("stage_audit")
        if self.owner.fail_stage_audit:
            raise RuntimeError("synthetic audit staging failure")
        self.stage_calls.append("audit")
        self.staged_audits.append(event)

    async def commit(self) -> object:
        from app.service import template_center as api

        self.owner.events.append("commit")
        if self.committed:
            raise RuntimeError("synthetic unit of work committed twice")
        self.owner.commit_attempts += 1
        if self.audit_sink.fail or self.owner.fail_commit:
            raise RuntimeError("synthetic audit failure")
        # No operation below can fail in this deterministic fake.  The real
        # implementation must provide the same all-or-nothing visibility.
        self.version_store.versions.extend(self.staged_versions)
        self.version_store.transitions.extend(self.staged_transitions)
        for event in self.staged_transitions:
            key = (getattr(event, "tenant_id"), getattr(event, "document_type"))
            self.version_store.active[key] = getattr(event, "active_version_id", None)
        self.audit_sink.events.extend(self.staged_audits)
        self.committed = True
        self.owner.commit_calls += 1
        return api.CommitReceipt(committed=True)


class MemoryTransactionPort:
    """Begin-only write port; uncommitted stages never enter read-side lists."""

    def __init__(
        self,
        version_store: MemoryVersionStore,
        audit_sink: MemoryAuditSink,
        *,
        events: list[str] | None = None,
    ) -> None:
        self.version_store = version_store
        self.audit_sink = audit_sink
        self.begin_calls = 0
        self.commit_attempts = 0
        self.commit_calls = 0
        self.version_sequences: dict[tuple[int, str], int] = {}
        self.units: list[MemoryUnitOfWork] = []
        self.events = events if events is not None else []
        self.fail_stage_version = False
        self.fail_stage_audit = False
        self.fail_commit = False

    async def begin(self, tenant_id: int, document_type: str) -> MemoryUnitOfWork:
        from app.service import template_center as api

        self.events.append("begin")
        if type(tenant_id) is not int or tenant_id <= 0:
            raise api.TemplateCenterError(api.TemplateErrorCode.INPUT_INVALID)
        try:
            normalized = (
                document_type
                if type(document_type) is api.DocumentType
                else api.DocumentType(document_type)
            )
        except (TypeError, ValueError) as error:
            raise api.TemplateCenterError(
                api.TemplateErrorCode.UNKNOWN_DOCUMENT_TYPE
            ) from error
        if not api.build_initial_document_registry().is_enabled(normalized):
            raise api.TemplateCenterError(
                api.TemplateErrorCode.DOCUMENT_TYPE_RESERVED_UNTIL_GATE
            )
        self.begin_calls += 1
        unit = MemoryUnitOfWork(
            self.version_store,
            self.audit_sink,
            self,
            tenant_id,
            normalized,
        )
        self.units.append(unit)
        return unit


# The initial enabled slice deliberately excludes these known future types.
@dataclass(frozen=True, slots=True)
class FakeSession:
    """A safe structural stand-in for the existing verified UI session."""

    session_id: UUID
    tenant_id: int
    user_id: int
    role: str
    username: str = "teacher@example.test"
    display_name: str = "合成用户"
    issued_at_utc: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)
    expires_at_utc: datetime = datetime(2026, 1, 2, tzinfo=timezone.utc)


def actor(
    *, tenant_id: int = 7, user_id: int = 11, role: str = "sys_admin"
) -> FakeSession:
    return FakeSession(
        session_id=uuid4(), tenant_id=tenant_id, user_id=user_id, role=role
    )


class MemoryBlobStore:
    def __init__(self, *, events: list[str] | None = None) -> None:
        self.blobs: dict[str, bytes] = {}
        self.calls: list[tuple[str, str]] = []
        self.events = events if events is not None else []
        self.fail_put = False

    async def put_if_absent(self, content_sha256: str, content: bytes) -> object:
        from app.service import template_center as api

        self.events.append("put_blob")
        self.calls.append(("put", content_sha256))
        if self.fail_put:
            raise RuntimeError("synthetic blob failure")
        self.blobs.setdefault(content_sha256, bytes(content))
        return api.BlobRef(
            value=f"sha256/{content_sha256}", content_sha256=content_sha256
        )

    async def read(self, blob_ref: str, expected_sha256: str) -> bytes:
        self.calls.append(("read", expected_sha256))
        assert blob_ref == f"sha256/{expected_sha256}"
        return self.blobs[expected_sha256]

    async def exists(self, blob_ref: str, expected_sha256: str) -> bool:
        self.calls.append(("exists", expected_sha256))
        return blob_ref == f"sha256/{expected_sha256}" and expected_sha256 in self.blobs


class AllowPolicy:
    def __init__(
        self,
        *,
        allowed: set[str] | None = None,
        events: list[str] | None = None,
        force_invalid_decision: bool = False,
    ) -> None:
        self.allowed = allowed or {
            "list",
            "read",
            "upload",
            "activate",
            "deactivate",
            "rollback",
            "preview",
            "backup",
            "restore",
            "render",
            "parse",
        }
        self.calls: list[tuple[str, int, int, str]] = []
        self.events = events if events is not None else []
        self.force_invalid_decision = force_invalid_decision

    async def project(
        self, session: object, document_type: str | None = None
    ) -> object:
        return SimpleNamespace(
            tenant_id=getattr(session, "tenant_id"),
            document_type=document_type,
            allowed_actions=tuple(sorted(self.allowed)),
            versions=(),
            active_version=None,
        )

    async def authorize(
        self,
        session: object,
        action: str,
        document_type: str,
        tenant_id: int,
    ) -> object:
        from app.service import template_center as api

        self.events.append("authorize")
        self.calls.append(
            (
                action,
                getattr(session, "tenant_id"),
                getattr(session, "user_id"),
                document_type,
            )
        )
        if self.force_invalid_decision:
            return SimpleNamespace(allowed=True)
        allowed = getattr(
            action, "value", action
        ) in self.allowed and tenant_id == getattr(session, "tenant_id")
        return api.PermissionDecision(
            allowed=allowed,
            policy_version="issue-55.v1",
            reason_code="allowed" if allowed else "default_deny",
        )


class MemoryExportPort:
    def __init__(self, version_store: MemoryVersionStore | None = None) -> None:
        self.version_store = version_store
        self.render_calls: list[tuple[object, object]] = []
        self.parse_calls: list[tuple[object, bytes]] = []
        self.resolve_calls: list[tuple[int, str]] = []

    async def resolve_active(self, tenant_id: int, document_type: str) -> object:
        self.resolve_calls.append((tenant_id, document_type))
        if self.version_store is None:
            return SimpleNamespace(document_type=document_type, tenant_id=tenant_id)
        snapshot = await self.version_store.snapshot(tenant_id, document_type)
        active_id = snapshot.active_version_id
        if active_id is None:
            return SimpleNamespace(
                document_type=document_type,
                tenant_id=tenant_id,
                active_version_id=None,
            )
        version = await self.version_store.get_version(tenant_id, active_id)
        if version is None:
            return SimpleNamespace(
                document_type=document_type,
                tenant_id=tenant_id,
                active_version_id=None,
            )
        return SimpleNamespace(
            tenant_id=tenant_id,
            document_type=document_type,
            template_version_id=version.template_version_id,
            version=version.version,
            content_sha256=version.content_sha256,
            contract_id=version.contract_id,
            contract_version=version.contract_version,
        )

    async def render(self, binding: object, payload: object) -> object:
        self.render_calls.append((binding, payload))
        return SimpleNamespace(
            content=_docx_with_text("合成预览"),
            binding=binding,
        )

    async def parse(self, binding: object, rendered_bytes: bytes) -> object:
        self.parse_calls.append((binding, rendered_bytes))
        return SimpleNamespace(
            valid=True,
            content_sha256="c" * 64,
            unresolved_tokens=(),
            external_relationships=(),
            macros=(),
        )


class MemoryControlledSeedStore:
    """Only opaque seed handles are accepted; no path or business repository exists."""

    def __init__(self, *, extra_seeds: dict[str, bytes] | None = None) -> None:
        self.seeds = {
            "controlled-weekplan-seed-v1": docx_with_text("weekly candidate seed"),
            "controlled-monthplan-seed-v1": docx_with_text("monthly candidate seed"),
        }
        if extra_seeds:
            self.seeds.update(
                {handle: bytes(content) for handle, content in extra_seeds.items()}
            )
        self.read_calls: list[tuple[str, str]] = []

    def register_controlled_seed(self, seed_handle: str, content: bytes) -> None:
        self.seeds[seed_handle] = bytes(content)

    async def read_controlled_seed(self, seed_handle: str, document_type: str) -> bytes:
        self.read_calls.append((seed_handle, document_type))
        return self.seeds[seed_handle]


OFFICE_CLIENT_VERSIONS = (
    "word/16.0.17328.20124",
    "libreoffice/24.2.7.2",
)


class MemoryOfficeQualificationPort:
    def __init__(
        self,
        *,
        status: str = "passed",
        evidence_id: str | None = "office-qualification-v1",
        client_versions: tuple[str, ...] = OFFICE_CLIENT_VERSIONS,
    ) -> None:
        self.calls: list[tuple[object, object, str]] = []
        self.status = status
        self.evidence_id = evidence_id
        self.client_versions = client_versions

    async def qualify(
        self, binding: object, parse_report: object, profile_id: str
    ) -> object:
        self.calls.append((binding, parse_report, profile_id))
        return SimpleNamespace(
            evidence_id=self.evidence_id,
            status=self.status,
            client_versions=self.client_versions,
        )


class MemoryQualificationEvidenceStore:
    def __init__(self) -> None:
        self.items: list[object] = []

    async def append(self, evidence: object) -> object:
        self.items.append(evidence)
        return evidence


class MemoryBackupPort:
    def __init__(self) -> None:
        self.created: list[object] = []
        self.restored: list[object] = []

    async def create_template_backup(
        self,
        snapshot: object,
        destination_handle: str,
        *,
        protected_image: str,
        now: datetime,
    ) -> object:
        result = SimpleNamespace(
            schema_version=1,
            artifact_sha256="synthetic-artifact-sha",
            artifact_size=123,
            protected_image=protected_image,
            created_at_utc=now,
            status="verified",
        )
        self.created.append((snapshot, result))
        return result

    async def restore_template_backup(
        self,
        artifact_handle: str,
        target_handle: str,
        *,
        expected_tenant_id: int,
    ) -> object:
        result = SimpleNamespace(
            expected_tenant_id=expected_tenant_id,
            committed=True,
        )
        self.restored.append(result)
        return result


class FixedClock:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    def utcnow(self) -> datetime:
        return self.now


def make_center(
    api: object, *, policy: AllowPolicy | None = None
) -> tuple[object, dict[str, object]]:
    """Construct the future public service using only documented injected ports."""
    blobs = MemoryBlobStore()
    versions = MemoryVersionStore()
    audit = MemoryAuditSink()
    transactions = MemoryTransactionPort(versions, audit)
    permissions = policy or AllowPolicy()
    exports = MemoryExportPort(versions)
    backups = MemoryBackupPort()
    center = api.TemplateCenter(
        blob_store=blobs,
        version_store=versions,
        transaction_port=transactions,
        permission_policy=permissions,
        contract_registry=api.build_initial_contract_registry(),
        export_port=exports,
        backup_port=backups,
        clock=FixedClock(),
    )
    return center, {
        "blobs": blobs,
        "versions": versions,
        "audit": audit,
        "transactions": transactions,
        "permissions": permissions,
        "exports": exports,
        "backups": backups,
    }


def make_upload_center(
    api: object, *, policy: AllowPolicy | None = None
) -> tuple[object, dict[str, object]]:
    """Construct only the T005 upload slice; no exporter or backup wiring."""

    events: list[str] = []
    blobs = MemoryBlobStore(events=events)
    versions = MemoryVersionStore()
    audit = MemoryAuditSink()
    transactions = MemoryTransactionPort(versions, audit, events=events)
    permissions = policy or AllowPolicy(events=events)
    center = api.TemplateCenter(
        blob_store=blobs,
        transaction_port=transactions,
        permission_policy=permissions,
        contract_registry=api.build_initial_contract_registry(),
        clock=FixedClock(),
    )
    return center, {
        "blobs": blobs,
        "versions": versions,
        "audit": audit,
        "transactions": transactions,
        "permissions": permissions,
        "events": events,
    }


def _document_xml(text: str, *, table_rows: int = 19) -> bytes:
    safe_text = escape(text, quote=False)
    table_rows = "".join(
        "<w:tr><w:tc><w:p><w:r><w:t>label</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>value</w:t></w:r></w:p></w:tc></w:tr>"
        for _ in range(table_rows)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>"
        + safe_text
        + '</w:t></w:r></w:p><w:tbl><w:tblGrid><w:gridCol w:w="4500"/><w:gridCol w:w="4500"/></w:tblGrid>'
        + table_rows
        + "</w:tbl>"
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>'
        "</w:body></w:document>"
    ).encode()


def _docx_with_text(
    text: str,
    *,
    members: dict[str, bytes] | None = None,
    table_rows: int = 19,
) -> bytes:
    files = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>"
        ).encode(),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>'
        ).encode(),
        "word/document.xml": _document_xml(text, table_rows=table_rows),
        "word/_rels/document.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
        ).encode(),
    }
    if members:
        files.update(members)
    out = BytesIO()
    with ZipFile(out, "w", ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return out.getvalue()


def docx_with_external_relationship() -> bytes:
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
        'Target="https://example.invalid/template" TargetMode="External"/></Relationships>'
    ).encode()
    return _docx_with_text(
        "safe", members={"word/_rels/document.xml.rels": relationships}
    )


def docx_with_symlink_member() -> bytes:
    out = BytesIO()
    with ZipFile(out, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", b"<Types/>")
        info = ZipInfo("word/link")
        info.external_attr = (0o120777 & 0xFFFF) << 16
        archive.writestr(info, b"/etc/passwd")
    return out.getvalue()


def docx_with_macro_member() -> bytes:
    return _docx_with_text(
        "safe", members={"word/vbaProject.bin": b"not executable here"}
    )


def docx_with_zipbomb() -> bytes:
    # A small compressed payload with an intentionally extreme ratio is enough
    # to exercise the validator without allocating a 50 MiB fixture.
    return _docx_with_text("safe", members={"word/large.xml": b"A" * (2 * 1024 * 1024)})


def docx_with_text(text: str, *, table_rows: int = 19) -> bytes:
    return _docx_with_text(text, table_rows=table_rows)


def docx_with_structure_profile_mismatch() -> bytes:
    """Safe OOXML whose table shape cannot satisfy the registered candidate profile."""
    return _docx_with_text("candidate structure mismatch", table_rows=1)
