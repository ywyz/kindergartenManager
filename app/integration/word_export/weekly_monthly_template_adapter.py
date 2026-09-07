# ruff: noqa: BLE001, I001 - the closed external boundary sanitizes all errors
"""Released weekly/monthly template adapter for the WMP-8 exporter.

The WMP-8 formal exporter deliberately returns an opaque result.  This
adapter is the only application-owned object allowed to unwrap that result
into bytes for a download.  It delegates rendering and parsing to the
approved Word boundary and never writes a file, preview, or export record.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from app.service.template_center.contracts import DocumentType
from app.service.template_center.contracts import (
    ExportParseReport as CenterExportParseReport,
)
from app.service.template_center.contracts import (
    RenderedTemplate as CenterRenderedTemplate,
)
from app.service.template_center.contracts import (
    TemplateExportBinding as CenterTemplateExportBinding,
    TemplateExportBindingKind,
)
from app.service.weekly_monthly_plans.export_contracts import ExportResult
from app.service.weekly_monthly_plans.qualification_orchestration import (
    WeeklyMonthlyQualificationReceipt,
)


class ReleasedTemplateAdapterError(Exception):
    """Stable, body-free rejection at the released template boundary."""

    def __init__(self, code: str) -> None:
        if type(code) is not str or not code:
            raise TypeError("released_template_adapter_error_invalid")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class FormalExportArtifact:
    """Exact in-memory artifact returned by the released adapter."""

    content_bytes: bytes
    content_sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if (
            type(self.content_bytes) is not bytes
            or not self.content_bytes
            or type(self.content_sha256) is not str
            or sha256(self.content_bytes).hexdigest() != self.content_sha256
            or type(self.size_bytes) is not int
            or self.size_bytes != len(self.content_bytes)
        ):
            raise ReleasedTemplateAdapterError("artifact_invalid")


def _document_type(value: object) -> DocumentType:
    if type(value) is DocumentType:
        return value
    try:
        return DocumentType(value)
    except (TypeError, ValueError):
        raise ReleasedTemplateAdapterError("document_type_invalid") from None


class ReleasedWeeklyMonthlyTemplateAdapter:
    """Adapter that binds the qualified pair to the external Word port.

    ``external_port`` is the production Word/render/parse implementation in
    application composition.  It is intentionally a narrow dependency; the
    adapter exposes no blob/path/URL handle and owns the opaque-result
    conversion used by the application download boundary.
    """

    __slots__ = ("__external_port", "__qualification_receipt")

    def __init__(self, *, qualification_receipt: object, external_port: object) -> None:
        if type(qualification_receipt) is not WeeklyMonthlyQualificationReceipt:
            raise ReleasedTemplateAdapterError("qualification_receipt_invalid")
        if not all(
            callable(getattr(external_port, name, None))
            for name in ("resolve_active", "render", "parse")
        ):
            raise ReleasedTemplateAdapterError("external_port_invalid")
        self.__qualification_receipt = qualification_receipt
        self.__external_port = external_port

    async def resolve_active(
        self, tenant_id: int, document_type: DocumentType
    ) -> CenterTemplateExportBinding:
        if type(tenant_id) is not int or tenant_id <= 0:
            raise ReleasedTemplateAdapterError("tenant_invalid")
        key = _document_type(document_type)
        try:
            binding = await self.__external_port.resolve_active(tenant_id, key)
        except BaseException:
            raise ReleasedTemplateAdapterError("active_binding_unavailable") from None
        if (
            type(binding) is not CenterTemplateExportBinding
            or binding.kind is not TemplateExportBindingKind.ACTIVE
            or binding.tenant_id != tenant_id
            or binding.document_type is not key
        ):
            raise ReleasedTemplateAdapterError("active_binding_invalid")
        return binding

    async def render(
        self, binding: CenterTemplateExportBinding, payload: object
    ) -> CenterRenderedTemplate:
        if type(binding) is not CenterTemplateExportBinding:
            raise ReleasedTemplateAdapterError("binding_invalid")
        try:
            rendered = await self.__external_port.render(binding, payload)
        except BaseException:
            raise ReleasedTemplateAdapterError("render_failed") from None
        if type(rendered) is not CenterRenderedTemplate:
            raise ReleasedTemplateAdapterError("render_invalid")
        return rendered

    async def parse(
        self, binding: CenterTemplateExportBinding, rendered_bytes: bytes
    ) -> CenterExportParseReport:
        if (
            type(binding) is not CenterTemplateExportBinding
            or type(rendered_bytes) is not bytes
            or not rendered_bytes
        ):
            raise ReleasedTemplateAdapterError("parse_input_invalid")
        try:
            report = await self.__external_port.parse(binding, rendered_bytes)
        except BaseException:
            raise ReleasedTemplateAdapterError("parse_failed") from None
        if type(report) is not CenterExportParseReport:
            raise ReleasedTemplateAdapterError("parse_invalid")
        return report

    def deliver(self, result: ExportResult) -> FormalExportArtifact:
        """Unwrap one validated WMP-8 result without persisting it."""
        if type(result) is not ExportResult:
            raise ReleasedTemplateAdapterError("export_result_invalid")
        try:
            rendered = result.rendered
            report = result.parse_report
            content = rendered.opaque_result
            valid = (
                type(content) is bytes
                and bool(content)
                and rendered.binding == result.binding
                and report.binding == result.binding
                and report.valid is True
                and not report.unresolved_tokens
                and not report.external_relationships
                and not report.macros
                and report.content_sha256 == sha256(content).hexdigest()
            )
        except BaseException:
            valid = False
        if not valid:
            raise ReleasedTemplateAdapterError("opaque_result_invalid")
        digest = sha256(content).hexdigest()
        return FormalExportArtifact(
            content_bytes=content,
            content_sha256=digest,
            size_bytes=len(content),
        )


__all__ = (
    "FormalExportArtifact",
    "ReleasedTemplateAdapterError",
    "ReleasedWeeklyMonthlyTemplateAdapter",
)
