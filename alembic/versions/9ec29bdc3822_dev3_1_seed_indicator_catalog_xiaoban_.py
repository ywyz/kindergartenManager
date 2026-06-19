"""dev3.1 seed indicator catalog xiaoban xia

Revision ID: 9ec29bdc3822
Revises: e3c0e63a65c4
Create Date: 2026-06-19 18:48:47.063421

预置「小班 / 下学期」五大领域指标目录，数据源：
alembic/seed_data/listening_indicators_xiaoban_xia.json（30 个二级指标，每个 3 档标准）。
seed 到默认租户 tenant_id=1。
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ec29bdc3822'
down_revision: Union[str, Sequence[str], None] = 'e3c0e63a65c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TENANT_ID = 1
_SEED_PATH = Path(__file__).resolve().parents[1] / "seed_data" / "listening_indicators_xiaoban_xia.json"

# 与 indicator_catalog 表对应的轻量表定义（用于 bulk_insert）
_catalog = sa.table(
    "indicator_catalog",
    sa.column("tenant_id", sa.BigInteger),
    sa.column("grade", sa.String),
    sa.column("term", sa.String),
    sa.column("domain", sa.String),
    sa.column("level1_name", sa.String),
    sa.column("level2_name", sa.String),
    sa.column("sort_order", sa.Integer),
    sa.column("standard_star1", sa.Text),
    sa.column("standard_star2", sa.Text),
    sa.column("standard_star3", sa.Text),
    sa.column("max_stars", sa.Integer),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)


def upgrade() -> None:
    """Upgrade schema."""
    data = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    grade = data["grade"]
    term = data["term"]
    now = datetime.now(timezone.utc)

    rows = []
    for domain, indicators in data["domains"].items():
        for ind in indicators:
            std = ind.get("standards", {})
            rows.append({
                "tenant_id": _TENANT_ID,
                "grade": grade,
                "term": term,
                "domain": domain,
                "level1_name": ind["level1"],
                "level2_name": ind["level2"],
                "sort_order": ind["sort_order"],
                "standard_star1": std.get("1"),
                "standard_star2": std.get("2"),
                "standard_star3": std.get("3"),
                "max_stars": 3,
                "created_at": now,
                "updated_at": now,
            })

    if rows:
        op.bulk_insert(_catalog, rows)


def downgrade() -> None:
    """Downgrade schema."""
    data = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    op.execute(
        sa.text(
            "DELETE FROM indicator_catalog "
            "WHERE tenant_id = :t AND grade = :g AND term = :term"
        ).bindparams(t=_TENANT_ID, g=data["grade"], term=data["term"])
    )
