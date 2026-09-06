"""Active-only weekly/monthly formal export orchestration."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from hashlib import sha256

from app.service.template_center.contracts import (
    ExportParseReport as CenterParseReport,
)
from app.service.template_center.contracts import (
    RenderedTemplate as CenterRenderedTemplate,
)
from app.service.template_center.contracts import (
    TemplateExportBinding as CenterBinding,
)
from app.service.template_center.contracts import TemplateExportBindingKind
from app.service.weekly_monthly_plans.export_contracts import (
    ExportParseReport,
    ExportResult,
    ExportSnapshot,
    MonthlyThemeActivityPlan,
    PlanDocumentType,
    PlanExportRequest,
    RenderedTemplate,
    TemplateExportBinding,
    WeeklyActivityPlan,
    build_export_filename,
)
from app.service.weekly_monthly_plans.template_enablement import (
    build_weekly_monthly_active_binding_gate,
)

FORMAL_EXPORT_CONTRACT_VERSION = "weekly-monthly-formal-export.v1"


class FormalExportErrorCode(str, Enum):
    INPUT_INVALID = "input_invalid"
    ENABLEMENT_INVALID = "enablement_invalid"
    ACTIVE_BINDING_UNAVAILABLE = "active_binding_unavailable"
    ACTIVE_BINDING_CHANGED = "active_binding_changed"
    RENDER_FAILED = "render_failed"
    RENDER_MISMATCH = "render_mismatch"
    PARSE_FAILED = "parse_failed"
    PARSE_MISMATCH = "parse_mismatch"
    RESULT_INVALID = "result_invalid"


class FormalExportError(Exception):
    """Stable error that never includes a dependency's exception body."""

    def __init__(self, code: FormalExportErrorCode) -> None:
        if type(code) is not FormalExportErrorCode:
            raise TypeError("formal_export_error_code_invalid")
        self.code = code
        super().__init__(code.value)


def _reject(code: FormalExportErrorCode) -> FormalExportError:
    return FormalExportError(code)


def _document_type(value: PlanDocumentType) -> str:
    if type(value) is not PlanDocumentType:
        raise _reject(FormalExportErrorCode.INPUT_INVALID)
    return value.value


def _validate_request(request: object) -> PlanExportRequest:
    try:
        if type(request) is not PlanExportRequest:
            raise _reject(FormalExportErrorCode.INPUT_INVALID)
        snapshot = request.snapshot
        if type(snapshot) is not ExportSnapshot:
            raise _reject(FormalExportErrorCode.INPUT_INVALID)
        if type(snapshot.document_type) is not PlanDocumentType:
            raise _reject(FormalExportErrorCode.INPUT_INVALID)
        expected = {
            PlanDocumentType.WEEKLY_ACTIVITY_PLAN: WeeklyActivityPlan,
            PlanDocumentType.MONTHLY_THEME_ACTIVITY_PLAN: MonthlyThemeActivityPlan,
        }.get(snapshot.document_type)
        if expected is None or type(snapshot.plan) is not expected:
            raise _reject(FormalExportErrorCode.INPUT_INVALID)
        PlanExportRequest(
            actor_id=request.actor_id,
            actor_role=request.actor_role,
            snapshot=ExportSnapshot(
                plan=snapshot.plan,
                document_type=snapshot.document_type,
                captured_at_utc=snapshot.captured_at_utc,
            ),
        )
        return request
    except FormalExportError:
        raise
    except BaseException:  # noqa: BLE001 - sanitize malformed exact-class objects
        raise _reject(FormalExportErrorCode.INPUT_INVALID) from None


def _same_binding(left: object, right: CenterBinding) -> bool:
    return (
        type(left) is CenterBinding
        and left == right
        and left.kind is TemplateExportBindingKind.ACTIVE
    )


def _canonical_payload(value: object) -> object:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is date:
        return {"date": value.isoformat()}
    if isinstance(value, Enum):
        return {"enum": type(value).__name__, "value": value.value}
    if type(value) is tuple:
        return [_canonical_payload(item) for item in value]
    if is_dataclass(value) and type(value).__module__ == WeeklyActivityPlan.__module__:
        return {
            "type": type(value).__name__,
            "fields": {
                field.name: _canonical_payload(getattr(value, field.name))
                for field in fields(value)
            },
        }
    raise _reject(FormalExportErrorCode.INPUT_INVALID)


def _payload_sha256(document_type: PlanDocumentType, plan: object) -> str:
    try:
        encoded = json.dumps(
            {
                "document_type": _document_type(document_type),
                "plan": _canonical_payload(plan),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except FormalExportError:
        raise
    except BaseException:  # noqa: BLE001 - sanitize canonicalization failures
        raise _reject(FormalExportErrorCode.INPUT_INVALID) from None
    return sha256(encoded).hexdigest()


def _freeze_snapshot(snapshot: ExportSnapshot) -> tuple[ExportSnapshot, str]:
    try:
        frozen = ExportSnapshot(
            plan=deepcopy(snapshot.plan),
            document_type=snapshot.document_type,
            captured_at_utc=snapshot.captured_at_utc,
        )
        payload_sha256 = _payload_sha256(frozen.document_type, frozen.plan)
    except BaseException:  # noqa: BLE001 - sanitize snapshot freezing failures
        raise _reject(FormalExportErrorCode.INPUT_INVALID) from None
    return frozen, payload_sha256


def _assert_snapshot_unchanged(
    snapshot: object, frozen: ExportSnapshot, payload_sha256: str
) -> None:
    try:
        unchanged = (
            type(snapshot) is ExportSnapshot
            and snapshot.document_type is frozen.document_type
            and type(snapshot.captured_at_utc) is datetime
            and snapshot.captured_at_utc == frozen.captured_at_utc
            and type(snapshot.plan) is type(frozen.plan)
            and _payload_sha256(snapshot.document_type, snapshot.plan) == payload_sha256
        )
    except BaseException:  # noqa: BLE001 - sanitize concurrent input drift
        unchanged = False
    if not unchanged:
        raise _reject(FormalExportErrorCode.INPUT_INVALID) from None


def _public_binding(binding: CenterBinding) -> TemplateExportBinding:
    try:
        return TemplateExportBinding(
            tenant_id=binding.tenant_id,
            document_type=PlanDocumentType(binding.document_type.value),
            template_version_id=binding.template_version_id,
            version=binding.version,
            content_sha256=binding.content_sha256,
            contract_id=binding.contract_id,
            contract_version=binding.contract_version,
        )
    except BaseException:  # noqa: BLE001 - sanitize the closed boundary
        raise _reject(FormalExportErrorCode.ACTIVE_BINDING_UNAVAILABLE) from None


def _validated_render(
    rendered: object, binding: CenterBinding, payload_sha256: str
) -> tuple[bytes, str]:
    try:
        valid = (
            type(rendered) is CenterRenderedTemplate
            and _same_binding(rendered.binding, binding)
            and type(rendered.rendered_bytes) is bytes
            and bool(rendered.rendered_bytes)
            and type(rendered.rendered_sha256) is str
            and sha256(rendered.rendered_bytes).hexdigest() == rendered.rendered_sha256
            and type(rendered.payload_sha256) is str
            and rendered.payload_sha256 == payload_sha256
        )
        if valid:
            return rendered.rendered_bytes, rendered.rendered_sha256
    except BaseException:  # noqa: BLE001 - sanitize provider DTO validation
        raise _reject(FormalExportErrorCode.RENDER_MISMATCH) from None
    raise _reject(FormalExportErrorCode.RENDER_MISMATCH) from None


def _validate_parse_report(
    report: object,
    binding: CenterBinding,
    rendered_sha256: str,
    payload_sha256: str,
) -> None:
    try:
        valid = (
            type(report) is CenterParseReport
            and _same_binding(report.binding, binding)
            and report.valid is True
            and type(report.unresolved_token_ids) is tuple
            and not report.unresolved_token_ids
            and report.has_macros is False
            and report.has_external_relationships is False
            and type(report.rendered_sha256) is str
            and report.rendered_sha256 == rendered_sha256
            and type(report.payload_sha256) is str
            and report.payload_sha256 == payload_sha256
        )
        if valid:
            return
    except BaseException:  # noqa: BLE001 - sanitize provider DTO validation
        raise _reject(FormalExportErrorCode.PARSE_MISMATCH) from None
    raise _reject(FormalExportErrorCode.PARSE_MISMATCH) from None


class WeeklyMonthlyFormalExporter:
    """Stateless active-binding consumer for the two closed plan types."""

    __slots__ = ("__active_gate", "__template_port")

    def __init__(self, active_gate: object, template_port: object) -> None:
        self.__active_gate = active_gate
        self.__template_port = template_port

    async def _resolve(
        self, tenant_id: int, document_type: PlanDocumentType
    ) -> CenterBinding:
        try:
            binding = await self.__active_gate.resolve_active(
                tenant_id,
                _document_type(document_type),
            )
        except FormalExportError:
            raise
        except BaseException:  # noqa: BLE001 - sanitize the closed boundary
            raise _reject(FormalExportErrorCode.ACTIVE_BINDING_UNAVAILABLE) from None
        if type(binding) is not CenterBinding:
            raise _reject(FormalExportErrorCode.ACTIVE_BINDING_UNAVAILABLE)
        return binding

    async def _assert_current(
        self,
        tenant_id: int,
        document_type: PlanDocumentType,
        expected: CenterBinding,
    ) -> None:
        try:
            current = await self.__active_gate.resolve_active(
                tenant_id,
                _document_type(document_type),
            )
        except BaseException:  # noqa: BLE001 - sanitize the closed boundary
            raise _reject(FormalExportErrorCode.ACTIVE_BINDING_CHANGED) from None
        try:
            unchanged = _same_binding(current, expected)
        except BaseException:  # noqa: BLE001 - sanitize provider DTO validation
            unchanged = False
        if not unchanged:
            raise _reject(FormalExportErrorCode.ACTIVE_BINDING_CHANGED)

    async def export(self, request: PlanExportRequest) -> ExportResult:
        closed_request = _validate_request(request)
        source_snapshot = closed_request.snapshot
        snapshot, payload_sha256 = _freeze_snapshot(source_snapshot)
        tenant_id = snapshot.plan.scope.tenant_id
        document_type = snapshot.document_type
        binding = await self._resolve(tenant_id, document_type)
        _assert_snapshot_unchanged(source_snapshot, snapshot, payload_sha256)
        public_binding = _public_binding(binding)

        try:
            rendered = await self.__template_port.render(binding, snapshot.plan)
        except BaseException:  # noqa: BLE001 - sanitize the closed boundary
            raise _reject(FormalExportErrorCode.RENDER_FAILED) from None
        rendered_bytes, rendered_sha256 = _validated_render(
            rendered, binding, payload_sha256
        )
        _assert_snapshot_unchanged(source_snapshot, snapshot, payload_sha256)

        await self._assert_current(tenant_id, document_type, binding)
        _assert_snapshot_unchanged(source_snapshot, snapshot, payload_sha256)
        try:
            report = await self.__template_port.parse(binding, rendered_bytes)
        except BaseException:  # noqa: BLE001 - sanitize the closed boundary
            raise _reject(FormalExportErrorCode.PARSE_FAILED) from None
        _validate_parse_report(report, binding, rendered_sha256, payload_sha256)
        _assert_snapshot_unchanged(source_snapshot, snapshot, payload_sha256)

        await self._assert_current(tenant_id, document_type, binding)
        _assert_snapshot_unchanged(source_snapshot, snapshot, payload_sha256)
        public_rendered = RenderedTemplate(
            binding=public_binding,
            opaque_result=rendered_bytes,
        )
        public_report = ExportParseReport(
            binding=public_binding,
            valid=True,
            unresolved_tokens=(),
            external_relationships=(),
            macros=(),
            content_sha256=rendered_sha256,
        )
        try:
            return ExportResult(
                document_type=snapshot.document_type,
                plan_id=snapshot.plan.plan_id,
                plan_version=snapshot.plan.version,
                binding=public_binding,
                rendered=public_rendered,
                parse_report=public_report,
                filename=build_export_filename(snapshot, public_binding),
            )
        except BaseException:  # noqa: BLE001 - sanitize the closed boundary
            raise _reject(FormalExportErrorCode.RESULT_INVALID) from None


def build_weekly_monthly_formal_exporter(
    qualification_receipt: object, template_export_port: object
) -> WeeklyMonthlyFormalExporter:
    try:
        valid_port = (
            callable(getattr(template_export_port, "resolve_active", None))
            and callable(getattr(template_export_port, "render", None))
            and callable(getattr(template_export_port, "parse", None))
        )
    except BaseException:  # noqa: BLE001 - sanitize the closed boundary
        raise _reject(FormalExportErrorCode.INPUT_INVALID) from None
    if not valid_port:
        raise _reject(FormalExportErrorCode.INPUT_INVALID)
    try:
        active_gate = build_weekly_monthly_active_binding_gate(
            qualification_receipt, template_export_port
        )
    except BaseException:  # noqa: BLE001 - sanitize the closed boundary
        raise _reject(FormalExportErrorCode.ENABLEMENT_INVALID) from None
    return WeeklyMonthlyFormalExporter(active_gate, template_export_port)


__all__ = (
    "FORMAL_EXPORT_CONTRACT_VERSION",
    "FormalExportError",
    "FormalExportErrorCode",
    "WeeklyMonthlyFormalExporter",
    "build_weekly_monthly_formal_exporter",
)
