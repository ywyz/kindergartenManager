"""Build immutable, canonical PlanPatch suggestions without side effects."""

from dataclasses import dataclass, field
from datetime import date
import re
from uuid import UUID, uuid4

from app.service.agent.canonical import canonical_sha256
from app.service.agent.contracts import (
    DAILY_PLAN_SECTION_PATHS,
    AgentContext,
    DailyPlanProjection,
    Permission,
    PlanSection,
)

PATCH_SCHEMA_VERSION = 1
MAX_PATCH_VALUE_LENGTH = 4096
MAX_PATCH_WARNING_LENGTH = 256
MAX_PATCH_WARNINGS = 8
ALLOWED_PLAN_PATCH_PATHS = DAILY_PLAN_SECTION_PATHS
SECTION_PATCH_PATHS = frozenset(
    path for path in ALLOWED_PLAN_PATCH_PATHS if path != "daily_reflection"
)
REFLECTION_PATCH_PATHS = frozenset({"daily_reflection"})
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class PlanPatchRejected(ValueError):
    """Reject an untrusted draft proposal with a stable local code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class PlanPatchTarget:
    """Resolved daily-plan identity bound by both id and date."""

    daily_plan_id: int
    plan_date: date


@dataclass(frozen=True, slots=True)
class DraftPatchOperation:
    """Closed, untrusted before/after proposal for one registered leaf path."""

    field_path: str
    before_value: str = field(repr=False)
    after_value: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class DraftPatchProposal:
    """Untrusted DRAFT output carrying every binding required by F005."""

    operation_id: UUID
    turn_id: UUID
    tool_name: str
    target: PlanPatchTarget
    base_fingerprint: str
    operations: tuple[DraftPatchOperation, ...] = field(repr=False)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PatchOperation:
    """Validated canonical operation displayed to the teacher, never applied."""

    field_path: str
    before_sha256: str
    before_display: str = field(repr=False)
    after_value: str = field(repr=False)
    after_display: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class PlanPatch:
    """Immutable, discardable suggestion bound to one frozen Agent turn."""

    patch_id: UUID
    schema_version: int
    operation_id: UUID
    turn_id: UUID
    tool_name: str
    target: PlanPatchTarget
    base_fingerprint: str
    operations: tuple[PatchOperation, ...] = field(repr=False)
    warnings: tuple[str, ...]
    canonical_sha256: str


def _reject(code: str) -> None:
    raise PlanPatchRejected(code)


def _validate_binding(
    context: AgentContext,
    proposal: DraftPatchProposal,
    projection: DailyPlanProjection,
) -> PlanPatchTarget:
    if proposal.operation_id != context.operation_id:
        _reject("operation_mismatch")
    if proposal.turn_id != context.turn_id:
        _reject("turn_mismatch")

    target = PlanPatchTarget(
        daily_plan_id=projection.plan_id,
        plan_date=projection.plan_date,
    )
    scope = context.active_scope
    scope_matches = (
        scope.daily_plan_id == target.daily_plan_id
        if scope.daily_plan_id is not None
        else scope.plan_date == target.plan_date
    )
    if not scope_matches or proposal.target != target:
        _reject("target_mismatch")

    if (
        _SHA256_PATTERN.fullmatch(context.base_fingerprint) is None
        or _SHA256_PATTERN.fullmatch(proposal.base_fingerprint) is None
    ):
        _reject("fingerprint_invalid")
    if proposal.base_fingerprint != context.base_fingerprint:
        _reject("fingerprint_mismatch")
    return target


def _validate_tool(context: AgentContext, tool_name: str) -> frozenset[str]:
    if Permission.DRAFT not in context.allowed_permissions:
        _reject("draft_permission_missing")
    if tool_name == "daily_plan.draft_section_patch":
        return SECTION_PATCH_PATHS
    if tool_name == "daily_plan.draft_reflection_patch":
        return REFLECTION_PATCH_PATHS
    _reject("tool_not_allowed")


def _validate_path_set(operations: tuple[DraftPatchOperation, ...]) -> None:
    if not isinstance(operations, tuple) or not operations:
        _reject("patch_requires_operations")
    if len(operations) > len(ALLOWED_PLAN_PATCH_PATHS):
        _reject("too_many_operations")

    paths: list[str] = []
    for operation in operations:
        if not isinstance(operation, DraftPatchOperation):
            _reject("patch_operation_invalid")
        if not isinstance(operation.field_path, str):
            _reject("field_path_invalid")
        if operation.field_path in paths:
            _reject("duplicate_field_path")
        if any(
            operation.field_path.startswith(f"{other}.")
            or other.startswith(f"{operation.field_path}.")
            for other in paths
        ):
            _reject("overlapping_field_path")
        paths.append(operation.field_path)


def _validate_value(value: object, *, side: str) -> str:
    if not isinstance(value, str):
        _reject(f"{side}_value_invalid")
    if len(value) > MAX_PATCH_VALUE_LENGTH:
        _reject(f"{side}_value_too_large")
    return value


def _projection_sections(
    context: AgentContext,
) -> tuple[DailyPlanProjection, dict[str, PlanSection]]:
    projections = tuple(
        fact for fact in context.facts if isinstance(fact, DailyPlanProjection)
    )
    if len(projections) != 1:
        _reject("current_plan_required")
    projection = projections[0]
    sections = {section.field_path: section for section in projection.sections}
    if set(sections) != set(ALLOWED_PLAN_PATCH_PATHS):
        _reject("current_plan_incomplete")
    return projection, sections


def _normalize_operations(
    proposal: DraftPatchProposal,
    sections: dict[str, PlanSection],
    tool_paths: frozenset[str],
) -> tuple[PatchOperation, ...]:
    _validate_path_set(proposal.operations)
    normalized: list[PatchOperation] = []
    for operation in proposal.operations:
        if operation.field_path not in ALLOWED_PLAN_PATCH_PATHS:
            _reject("field_path_not_allowed")
        if operation.field_path not in tool_paths:
            _reject("field_path_not_allowed_for_tool")
        before_value = _validate_value(operation.before_value, side="before")
        after_value = _validate_value(operation.after_value, side="after")
        section = sections[operation.field_path]
        if section.truncated:
            _reject("before_value_unavailable")
        if before_value != section.content:
            _reject("before_value_mismatch")
        normalized.append(
            PatchOperation(
                field_path=operation.field_path,
                before_sha256=canonical_sha256(before_value),
                before_display=before_value,
                after_value=after_value,
                after_display=after_value,
            )
        )
    return tuple(sorted(normalized, key=lambda operation: operation.field_path))


def _normalize_warnings(warnings: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(warnings, tuple) or len(warnings) > MAX_PATCH_WARNINGS:
        _reject("warnings_invalid")
    normalized: set[str] = set()
    for warning in warnings:
        if not isinstance(warning, str):
            _reject("warning_invalid")
        value = warning.strip()
        if not value or len(value) > MAX_PATCH_WARNING_LENGTH:
            _reject("warning_invalid")
        normalized.add(value)
    return tuple(sorted(normalized))


def build_plan_patch(
    *,
    context: AgentContext,
    proposal: DraftPatchProposal,
) -> PlanPatch:
    """Validate and canonicalize one DRAFT proposal without touching DB or UI."""
    if not isinstance(context, AgentContext):
        _reject("context_invalid")
    if not isinstance(proposal, DraftPatchProposal):
        _reject("proposal_invalid")

    projection, sections = _projection_sections(context)
    target = _validate_binding(context, proposal, projection)
    tool_paths = _validate_tool(context, proposal.tool_name)
    operations = _normalize_operations(proposal, sections, tool_paths)
    warnings = _normalize_warnings(proposal.warnings)
    canonical_payload = {
        "schema_version": PATCH_SCHEMA_VERSION,
        "operation_id": proposal.operation_id,
        "turn_id": proposal.turn_id,
        "tool_name": proposal.tool_name,
        "target": target,
        "base_fingerprint": proposal.base_fingerprint,
        "operations": operations,
        "warnings": warnings,
    }
    return PlanPatch(
        patch_id=uuid4(),
        schema_version=PATCH_SCHEMA_VERSION,
        operation_id=proposal.operation_id,
        turn_id=proposal.turn_id,
        tool_name=proposal.tool_name,
        target=target,
        base_fingerprint=proposal.base_fingerprint,
        operations=operations,
        warnings=warnings,
        canonical_sha256=canonical_sha256(canonical_payload),
    )
