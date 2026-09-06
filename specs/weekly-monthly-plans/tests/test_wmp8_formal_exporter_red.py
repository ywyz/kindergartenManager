"""WMP-8 formal exporter stable RED.

The suite uses only frozen weekly/monthly snapshots and an in-memory template
port.  It never reads a template, filesystem export, database, or network.
"""

from __future__ import annotations

import ast
import asyncio
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from uuid import UUID

import pytest
from test_weekly_monthly_export_contracts_red import _monthly_plan, _weekly_plan
from test_wmp7_template_enablement_gate_red import _receipt

MODULE_NAME = "app.service.weekly_monthly_plans.formal_exporter"
WEEKLY = "weekly_activity_plan"
MONTHLY = "monthly_theme_activity_plan"


def _api():
    return import_module(MODULE_NAME)


def _exports():
    return import_module("app.service.weekly_monthly_plans.export_contracts")


def _domain():
    return import_module("app.service.weekly_monthly_plans.contracts")


def _tc():
    return import_module("app.service.template_center")


def _snapshot(document_type: str = WEEKLY):
    exports = _exports()
    plan = (
        _weekly_plan(_domain()) if document_type == WEEKLY else _monthly_plan(_domain())
    )
    return exports.ExportSnapshot(
        plan=plan,
        document_type=exports.PlanDocumentType(document_type),
        captured_at_utc=datetime(2026, 9, 28, tzinfo=UTC),
    )


def _request(document_type: str = WEEKLY):
    return _exports().PlanExportRequest(
        actor_id=11,
        actor_role="teacher",
        snapshot=_snapshot(document_type),
    )


class MemoryFormalTemplatePort:
    """Closed fake with explicit drift/failure injection and side-effect probes."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.resolve_count = 0
        self.fail_at: str | None = None
        self.binding_overrides: dict[str, object] = {}
        self.render_binding_override = None
        self.parse_binding_override = None
        self.render_bytes = b"formal-docx-artifact"
        self.render_hash_override: str | None = None
        self.last_payload_sha256: str | None = None
        self.parse_valid = True
        self.unresolved: tuple[str, ...] = ()
        self.has_macros = False
        self.has_external = False
        self.drift_after_resolve: int | None = None
        self.barrier: asyncio.Barrier | None = None
        self.business_writes = 0
        self.audit_writes = 0
        self.preview_writes = 0
        self.export_writes = 0

    def _binding(self, tenant_id, document_type, resolve_number=None):
        tc = _tc()
        profile = next(
            item
            for item in tc.CANDIDATE_QUALIFICATION_PROFILES
            if item.document_type is document_type and item.profile_version == 2
        )
        values = {
            "document_type": document_type,
            "content_sha256": profile.seed_handle.expected_sha256,
            "contract_id": profile.contract.contract_id,
            "contract_version": profile.contract.contract_version,
            "tenant_id": tenant_id,
            "template_version_id": UUID(
                "00000000-0000-0000-0000-000000000801"
                if document_type.value == WEEKLY
                else "00000000-0000-0000-0000-000000000802"
            ),
            "version": 8,
        }
        values.update(self.binding_overrides)
        if (
            self.drift_after_resolve is not None
            and (resolve_number or self.resolve_count) > self.drift_after_resolve
        ):
            values["version"] = 9
            values["template_version_id"] = UUID("00000000-0000-0000-0000-000000000809")
        return tc.TemplateExportBinding(**values)

    async def resolve_active(self, tenant_id, document_type):
        self.resolve_count += 1
        resolve_number = self.resolve_count
        self.calls.append(("resolve_active", (tenant_id, document_type)))
        if self.fail_at == "resolve":
            raise RuntimeError("secret registry /srv/templates tenant=17")
        if self.barrier is not None and self.resolve_count <= 2:
            await self.barrier.wait()
        return self._binding(tenant_id, document_type, resolve_number)

    async def render(self, binding, payload):
        self.calls.append(("render", (binding, payload)))
        if self.fail_at == "render":
            raise RuntimeError("s3://private-bucket/template.docx")
        rendered_binding = self.render_binding_override or binding
        rendered_hash = (
            self.render_hash_override or sha256(self.render_bytes).hexdigest()
        )
        self.last_payload_sha256 = _api()._payload_sha256(
            _exports().PlanDocumentType(binding.document_type.value), payload
        )
        return _tc().RenderedTemplate(
            binding=rendered_binding,
            rendered_bytes=self.render_bytes,
            rendered_sha256=rendered_hash,
            payload_sha256=self.last_payload_sha256,
        )

    async def parse(self, binding, rendered_bytes):
        self.calls.append(("parse", (binding, rendered_bytes)))
        if self.fail_at == "parse":
            raise RuntimeError("provider dto at /internal/parser")
        return _tc().ExportParseReport(
            binding=self.parse_binding_override or binding,
            valid=self.parse_valid,
            structure_summary_sha256="b" * 64,
            unresolved_token_ids=self.unresolved,
            has_macros=self.has_macros,
            has_external_relationships=self.has_external,
            rendered_sha256=sha256(rendered_bytes).hexdigest(),
            payload_sha256=self.last_payload_sha256,
        )

    def persistence(self) -> tuple[int, int, int, int]:
        return (
            self.business_writes,
            self.audit_writes,
            self.preview_writes,
            self.export_writes,
        )


async def _exporter(port: MemoryFormalTemplatePort | None = None):
    api = _api()
    selected = port or MemoryFormalTemplatePort()
    return (
        api.build_weekly_monthly_formal_exporter(await _receipt(), selected),
        selected,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("document_type", [WEEKLY, MONTHLY])
async def test_formal_export_positive_weekly_and_monthly(document_type):
    exporter, port = await _exporter()
    request = _request(document_type)

    result = await exporter.export(request)

    assert type(result) is _exports().ExportResult
    assert result.document_type.value == document_type
    assert result.plan_id == request.snapshot.plan.plan_id
    assert result.plan_version == request.snapshot.plan.version
    assert result.binding.tenant_id == request.snapshot.plan.scope.tenant_id
    assert result.binding.version == 8
    assert result.rendered.opaque_result == port.render_bytes
    assert result.parse_report.content_sha256 == sha256(port.render_bytes).hexdigest()
    assert result.filename.endswith("_t8.docx")
    assert [name for name, _ in port.calls] == [
        "resolve_active",
        "render",
        "resolve_active",
        "parse",
        "resolve_active",
    ]


@pytest.mark.asyncio
async def test_no_valid_active_binding_makes_zero_render_or_parse_calls():
    api = _api()
    port = MemoryFormalTemplatePort()
    port.fail_at = "resolve"
    exporter, _ = await _exporter(port)

    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(_request())

    assert caught.value.code is api.FormalExportErrorCode.ACTIVE_BINDING_UNAVAILABLE
    assert [name for name, _ in port.calls] == ["resolve_active"]


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [None, object(), "weekly_activity_plan"])
async def test_non_closed_request_or_document_type_is_rejected_before_template_calls(
    bad,
):
    api = _api()
    exporter, port = await _exporter()
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(bad)
    assert caught.value.code is api.FormalExportErrorCode.INPUT_INVALID
    assert port.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenant_id", 18),
        ("content_sha256", "0" * 64),
        ("contract_version", 1),
        ("version", 0),
    ],
)
async def test_missing_disabled_or_mismatched_active_binding_fails_closed(field, value):
    api = _api()
    port = MemoryFormalTemplatePort()
    port.binding_overrides[field] = value
    exporter, _ = await _exporter(port)
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(_request())
    assert caught.value.code is api.FormalExportErrorCode.ACTIVE_BINDING_UNAVAILABLE
    assert not any(name in {"render", "parse"} for name, _ in port.calls)


@pytest.mark.asyncio
async def test_candidate_profile_or_qualification_evidence_mismatch_blocks_construction():
    api = _api()
    receipt = await _receipt()
    object.__setattr__(receipt, "weekly_mapping_sha256", "0" * 64)
    port = MemoryFormalTemplatePort()
    with pytest.raises(api.FormalExportError) as caught:
        api.build_weekly_monthly_formal_exporter(receipt, port)
    assert caught.value.code is api.FormalExportErrorCode.ENABLEMENT_INVALID
    assert port.calls == []


@pytest.mark.asyncio
async def test_port_capability_probe_exception_is_sanitized():
    api = _api()

    class HostilePort:
        def __getattribute__(self, name):
            raise RuntimeError("s3://private-bucket/internal")

    with pytest.raises(api.FormalExportError) as caught:
        api.build_weekly_monthly_formal_exporter(await _receipt(), HostilePort())
    assert caught.value.code is api.FormalExportErrorCode.INPUT_INVALID
    assert str(caught.value) == "input_invalid"
    assert caught.value.__cause__ is None


@pytest.mark.asyncio
async def test_corrupted_snapshot_document_type_is_rejected_before_port_calls():
    api = _api()
    exporter, port = await _exporter()
    request = _request()
    object.__setattr__(request.snapshot, "document_type", [])

    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(request)
    assert caught.value.code is api.FormalExportErrorCode.INPUT_INVALID
    assert str(caught.value) == "input_invalid"
    assert caught.value.__cause__ is None
    assert port.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("checkpoint", [1, 2])
async def test_active_binding_drift_during_render_or_parse_fails_closed(checkpoint):
    api = _api()
    port = MemoryFormalTemplatePort()
    port.drift_after_resolve = checkpoint
    exporter, _ = await _exporter(port)
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(_request())
    assert caught.value.code is api.FormalExportErrorCode.ACTIVE_BINDING_CHANGED
    assert port.persistence() == (0, 0, 0, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["render", "parse"])
async def test_port_failures_are_stable_body_free_and_do_not_persist(stage):
    api = _api()
    port = MemoryFormalTemplatePort()
    port.fail_at = stage
    exporter, _ = await _exporter(port)
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(_request())
    assert caught.value.code is getattr(
        api.FormalExportErrorCode, f"{stage.upper()}_FAILED"
    )
    assert str(caught.value) == caught.value.code.value
    assert caught.value.__cause__ is None
    assert port.persistence() == (0, 0, 0, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["render", "parse"])
async def test_render_or_parse_binding_mismatch_is_rejected(stage):
    api = _api()
    port = MemoryFormalTemplatePort()
    wrong = port._binding(18, _tc().DocumentType.WEEKLY_ACTIVITY_PLAN)
    if stage == "render":
        port.render_binding_override = wrong
    else:
        port.parse_binding_override = wrong
    exporter, _ = await _exporter(port)
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(_request())
    assert caught.value.code is getattr(
        api.FormalExportErrorCode, f"{stage.upper()}_MISMATCH"
    )


@pytest.mark.asyncio
async def test_rendered_artifact_hash_mismatch_is_rejected_before_parse():
    api = _api()
    port = MemoryFormalTemplatePort()
    port.render_hash_override = "0" * 64
    exporter, _ = await _exporter(port)
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(_request())
    assert caught.value.code is api.FormalExportErrorCode.RENDER_MISMATCH
    assert not any(name == "parse" for name, _ in port.calls)


def test_template_render_receipt_carries_payload_identity():
    _api()
    assert "payload_sha256" in {field.name for field in fields(_tc().RenderedTemplate)}


def test_template_parse_report_carries_rendered_artifact_identity():
    _api()
    assert "rendered_sha256" in {
        field.name for field in fields(_tc().ExportParseReport)
    }


def test_template_parse_report_carries_artifact_payload_identity():
    _api()
    assert "payload_sha256" in {field.name for field in fields(_tc().ExportParseReport)}


@pytest.mark.asyncio
async def test_replayed_cross_plan_artifact_identity_is_rejected():
    api = _api()

    class ReplayedArtifactPort(MemoryFormalTemplatePort):
        async def render(self, binding, payload):
            self.calls.append(("render", (binding, payload)))
            return _tc().RenderedTemplate(
                binding=binding,
                rendered_bytes=self.render_bytes,
                rendered_sha256=sha256(self.render_bytes).hexdigest(),
                payload_sha256="0" * 64,
            )

    exporter, port = await _exporter(ReplayedArtifactPort())
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(_request())
    assert caught.value.code is api.FormalExportErrorCode.RENDER_MISMATCH
    assert not any(name == "parse" for name, _ in port.calls)


@pytest.mark.asyncio
async def test_parse_report_for_another_rendered_artifact_is_rejected():
    api = _api()

    class ReplayedParsePort(MemoryFormalTemplatePort):
        async def parse(self, binding, rendered_bytes):
            self.calls.append(("parse", (binding, rendered_bytes)))
            return _tc().ExportParseReport(
                binding=binding,
                valid=True,
                structure_summary_sha256="b" * 64,
                unresolved_token_ids=(),
                has_macros=False,
                has_external_relationships=False,
                rendered_sha256="0" * 64,
            )

    exporter, _ = await _exporter(ReplayedParsePort())
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(_request())
    assert caught.value.code is api.FormalExportErrorCode.PARSE_MISMATCH


@pytest.mark.asyncio
async def test_replayed_artifact_with_forged_current_render_receipt_is_rejected():
    api = _api()

    class ReplayedBytesPort(MemoryFormalTemplatePort):
        async def render(self, binding, payload):
            self.calls.append(("render", (binding, payload)))
            self.render_bytes = b"weekly-plan-v1-replayed-artifact"
            self.last_payload_sha256 = api._payload_sha256(
                _exports().PlanDocumentType(binding.document_type.value), payload
            )
            return _tc().RenderedTemplate(
                binding=binding,
                rendered_bytes=self.render_bytes,
                rendered_sha256=sha256(self.render_bytes).hexdigest(),
                payload_sha256=self.last_payload_sha256,
            )

        async def parse(self, binding, rendered_bytes):
            self.calls.append(("parse", (binding, rendered_bytes)))
            return _tc().ExportParseReport(
                binding=binding,
                valid=True,
                structure_summary_sha256="b" * 64,
                unresolved_token_ids=(),
                has_macros=False,
                has_external_relationships=False,
                rendered_sha256=sha256(rendered_bytes).hexdigest(),
                payload_sha256="0" * 64,
            )

    exporter, _ = await _exporter(ReplayedBytesPort())
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(_request())
    assert caught.value.code is api.FormalExportErrorCode.PARSE_MISMATCH


class _PoisonedComparison:
    def __eq__(self, other):
        raise RuntimeError("internal provider DTO s3://private-bucket")

    def __ne__(self, other):
        raise RuntimeError("internal provider DTO s3://private-bucket")


@pytest.mark.asyncio
async def test_poisoned_render_dto_validation_is_sanitized_as_mismatch():
    api = _api()

    class PoisonedRenderPort(MemoryFormalTemplatePort):
        async def render(self, binding, payload):
            result = await super().render(binding, payload)
            object.__setattr__(result, "rendered_sha256", _PoisonedComparison())
            return result

    exporter, _ = await _exporter(PoisonedRenderPort())
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(_request())
    assert caught.value.code is api.FormalExportErrorCode.RENDER_MISMATCH
    assert str(caught.value) == "render_mismatch"
    assert caught.value.__cause__ is None


@pytest.mark.asyncio
async def test_poisoned_parse_dto_validation_is_sanitized_as_mismatch():
    api = _api()

    class PoisonedParsePort(MemoryFormalTemplatePort):
        async def parse(self, binding, rendered_bytes):
            result = await super().parse(binding, rendered_bytes)
            object.__setattr__(result, "rendered_sha256", _PoisonedComparison())
            return result

    exporter, _ = await _exporter(PoisonedParsePort())
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(_request())
    assert caught.value.code is api.FormalExportErrorCode.PARSE_MISMATCH
    assert str(caught.value) == "parse_mismatch"
    assert caught.value.__cause__ is None


@pytest.mark.asyncio
async def test_snapshot_version_drift_during_first_resolve_fails_closed():
    api = _api()
    request = _request()

    class SnapshotDriftPort(MemoryFormalTemplatePort):
        async def resolve_active(self, tenant_id, document_type):
            result = await super().resolve_active(tenant_id, document_type)
            if self.resolve_count == 1:
                object.__setattr__(request.snapshot.plan, "version", 999)
            return result

    exporter, port = await _exporter(SnapshotDriftPort())
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(request)
    assert caught.value.code is api.FormalExportErrorCode.INPUT_INVALID
    assert not any(name in {"render", "parse"} for name, _ in port.calls)


@pytest.mark.asyncio
async def test_uninitialized_exact_request_is_sanitized_before_port_calls():
    api = _api()
    malformed = object.__new__(_exports().PlanExportRequest)
    exporter, port = await _exporter()
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(malformed)
    assert caught.value.code is api.FormalExportErrorCode.INPUT_INVALID
    assert str(caught.value) == "input_invalid"
    assert caught.value.__cause__ is None
    assert port.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("parse_valid", False),
        ("unresolved", ("{{kg.weekly_activity_plan.theme_name}}",)),
        ("has_macros", True),
        ("has_external", True),
    ],
)
async def test_unresolved_tokens_missing_structure_or_security_failure_is_rejected(
    attribute, value
):
    api = _api()
    port = MemoryFormalTemplatePort()
    setattr(port, attribute, value)
    exporter, _ = await _exporter(port)
    with pytest.raises(api.FormalExportError) as caught:
        await exporter.export(_request())
    assert caught.value.code is api.FormalExportErrorCode.PARSE_MISMATCH


def test_formal_export_surface_has_no_requested_historical_version_or_crud():
    api = _api()
    assert list(fields(_exports().PlanExportRequest)) == list(
        fields(_exports().PlanExportRequest)
    )
    assert {item.name for item in fields(_exports().PlanExportRequest)} == {
        "actor_id",
        "actor_role",
        "snapshot",
    }
    forbidden = {
        "requested_version",
        "requested_template_version",
        "resolve_version",
        "fallback",
        "retry",
        "upload",
        "activate",
        "rollback",
        "delete",
        "download",
        "discover",
    }
    assert forbidden.isdisjoint(vars(api))


@pytest.mark.asyncio
async def test_result_is_frozen_redacted_and_contains_no_provider_dto():
    exporter, port = await _exporter()
    result = await exporter.export(_request())
    assert is_dataclass(result)
    assert type(result.rendered.opaque_result) is bytes
    assert type(result.binding) is _exports().TemplateExportBinding
    assert type(result.parse_report) is _exports().ExportParseReport
    rendered = repr(result).lower()
    for forbidden in (
        "registry",
        "descriptor",
        "bucket",
        "storage_handle",
        "seed_relative_path",
        "candidatequalificationevidence",
        "service.template_center.contracts.renderedtemplate",
    ):
        assert forbidden not in rendered
    assert port.persistence() == (0, 0, 0, 0)


@pytest.mark.asyncio
async def test_success_and_failure_have_zero_business_audit_preview_export_persistence():
    api = _api()
    success, success_port = await _exporter()
    await success.export(_request())
    assert success_port.persistence() == (0, 0, 0, 0)

    failed_port = MemoryFormalTemplatePort()
    failed_port.parse_valid = False
    failed, _ = await _exporter(failed_port)
    with pytest.raises(api.FormalExportError):
        await failed.export(_request())
    assert failed_port.persistence() == (0, 0, 0, 0)


def test_wmp7_capability_surface_remains_read_only():
    api = _api()
    tc = _tc()
    assert api.FORMAL_EXPORT_CONTRACT_VERSION == "weekly-monthly-formal-export.v1"
    source = Path(
        import_module("app.service.weekly_monthly_plans.template_enablement").__file__
    ).read_text(encoding="utf-8")
    assert "capabilities=(TemplateCapability.READ,)" in source
    assert tuple(item.value for item in tc.TemplateCapability) != ()


def test_formal_exporter_has_closed_dependencies_and_no_persistence_or_agent_imports():
    api = _api()
    path = Path(api.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = {
        node.module
        for node in ast.walk(tree)
        if type(node) is ast.ImportFrom and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if type(node) is ast.Import
        for alias in node.names
    }
    assert imports <= {
        "__future__",
        "asyncio",
        "copy",
        "dataclasses",
        "datetime",
        "enum",
        "hashlib",
        "json",
        "app.service.template_center.contracts",
        "app.service.weekly_monthly_plans.export_contracts",
        "app.service.weekly_monthly_plans.template_enablement",
    }
    lowered = path.read_text(encoding="utf-8").lower()
    for forbidden in (
        "sqlalchemy",
        "repository",
        "exportrecord",
        "audit",
        "preview",
        "alembic",
        "app.service.agent",
        "pathlib",
        "open(",
        "http",
        "url",
        "bucket",
        "storage_handle",
        "import_module",
    ):
        assert forbidden not in lowered


def test_wmp8_roadmap_records_current_gate_date_without_premature_ci_closure():
    roadmap = (Path(__file__).parents[3] / "docs" / "ROADMAP.md").read_text(
        encoding="utf-8"
    )
    assert "WMP-8 已于 2026-09-07 完成本地门" in roadmap
    assert "最终 exact-SHA 证据以本轮 Issue #56/#57 回写为准" in roadmap


def test_weekly_monthly_spec_next_gate_converges_on_wmp9():
    spec = (Path(__file__).parents[1] / "spec.md").read_text(encoding="utf-8")
    current_next_step = spec.split("## 11. 下一步", maxsplit=1)[1]
    assert "WMP-8 已完成" in current_next_step
    assert "下一道独立门为 WMP-9 正式业务验收" in current_next_step


@pytest.mark.asyncio
async def test_concurrent_cross_version_composition_fails_closed():
    api = _api()
    port = MemoryFormalTemplatePort()
    port.barrier = asyncio.Barrier(2)
    port.drift_after_resolve = 2
    exporter, _ = await _exporter(port)
    outcomes = await asyncio.gather(
        exporter.export(_request(WEEKLY)),
        exporter.export(_request(MONTHLY)),
        return_exceptions=True,
    )
    assert all(type(item) is api.FormalExportError for item in outcomes)
    assert all(
        item.code is api.FormalExportErrorCode.ACTIVE_BINDING_CHANGED
        for item in outcomes
    )
    assert port.persistence() == (0, 0, 0, 0)


@pytest.mark.asyncio
async def test_replayed_or_cross_version_provider_objects_cannot_be_injected():
    exporter, port = await _exporter()
    assert list(vars(exporter)) == [] if hasattr(exporter, "__dict__") else True
    with pytest.raises(TypeError):
        await exporter.export(
            _request(),
            binding=port._binding(17, _tc().DocumentType.WEEKLY_ACTIVITY_PLAN),
        )
