"""Regression guards for the first independent ADR/spec review findings."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ADR = (
    ROOT / "docs/ADR/ADR-0009-weekly-monthly-production-lifecycle-and-authorization.md"
)
SPEC = ROOT / "specs/wmp9-production-prerequisites/spec.md"


def _texts() -> tuple[str, str]:
    return ADR.read_text(encoding="utf-8"), SPEC.read_text(encoding="utf-8")


def test_h1_archive_uses_the_single_closed_authorization_port() -> None:
    adr, spec = _texts()
    assert "PlanAction.ARCHIVE" in adr
    assert "read/review/export/archive" in adr
    assert "ARCHIVE" in spec and "PlanAuthorizationPort" in spec


def test_m1_delivery_seam_owns_opaque_result_unwrapping() -> None:
    adr, spec = _texts()
    assert "FormalExportDelivery" in adr
    assert "adapter-owned" in spec
    assert "UI 不得读取或 downcast `opaque_result`" in spec


def test_m2_draft_delete_retains_root_tombstone_without_audit_fk() -> None:
    adr, spec = _texts()
    assert "保留聚合根 tombstone" in adr
    assert "audit 不建立指向 root/version 的 FK" in adr
    assert "plan ID 永不复用" in spec


def test_m3_all_text_limits_use_exact_utf8_byte_units() -> None:
    adr, spec = _texts()
    assert "1,048,576 UTF-8 bytes" in adr
    assert "16,384 UTF-8 bytes" in spec
    assert "OCTET_LENGTH" in spec and "CAST(value AS BLOB)" in spec


def test_m4_presence_red_cannot_be_used_as_the_functional_green_gate() -> None:
    _, spec = _texts()
    assert "存在性 RED 永远不能作为功能 GREEN 门" in spec
    for term in ("SQLite", "MySQL", "CAS", "audit", "delivery"):
        assert term in spec


def test_l1_alembic_scope_is_exactly_six_tables() -> None:
    adr, _ = _texts()
    assert "上述六张表" in adr
    assert "上述五张表" not in adr


def test_m5_every_scalar_narrative_field_has_an_exact_utf8_limit() -> None:
    adr, spec = _texts()
    fields = (
        "weekly_focus",
        "environment_creation",
        "life_habits",
        "home_school_cooperation",
        "previous_month_analysis",
        "monthly_focus",
    )
    for field in fields:
        assert field in adr
    assert "32,768 UTF-8 bytes" in adr
    assert "scalar narrative" in spec
