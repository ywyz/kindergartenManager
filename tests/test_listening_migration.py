"""P1 — 一对一倾听迁移与种子集成测试。

在临时 sqlite 文件库上实际执行 `alembic upgrade head`，验证：
- 5 个新表创建成功
- indicator_catalog 种子 30 条且分布正确
- export_records 增列 listening_record_id
另含种子 JSON 数据源完整性测试（无需数据库）。
"""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SEED_PATH = _PROJECT_ROOT / "alembic" / "seed_data" / "listening_indicators_xiaoban_xia.json"

_EXPECTED_BY_DOMAIN = {"健康": 7, "语言": 6, "社会": 7, "科学": 6, "艺术": 4}


# ─── 种子 JSON 数据源完整性（无 DB）──────────────────────────────────────────


def test_seed_json_integrity():
    """种子 JSON：5 领域共 30 个二级指标，每个含 3 档标准、sort_order 连续。"""
    data = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    assert data["grade"] == "小班"
    assert data["term"] == "下学期"
    total = 0
    for domain, expected in _EXPECTED_BY_DOMAIN.items():
        inds = data["domains"][domain]
        assert len(inds) == expected, f"{domain} 应有 {expected} 个，实得 {len(inds)}"
        for i, ind in enumerate(inds):
            assert ind["sort_order"] == i, f"{domain} sort_order 不连续"
            assert ind["level1"] and ind["level2"]
            for s in ("1", "2", "3"):
                assert ind["standards"].get(s), f"{domain}[{i}] 缺 {s} 星标准"
        total += len(inds)
    assert total == 30


# ─── 实际迁移（临时 sqlite + subprocess）─────────────────────────────────────


@pytest.fixture
def migrated_db(tmp_path):
    """在临时 sqlite 文件库上执行 alembic upgrade head，返回库路径。"""
    db_file = tmp_path / "mig_test.db"
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_file}"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(_PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic 失败:\n{result.stderr}"
    yield db_file


def test_upgrade_head_creates_listening_tables(migrated_db):
    """升级到 head 后 5 个新表存在。"""
    conn = sqlite3.connect(str(migrated_db))
    names = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()
    for t in (
        "listening_record", "listening_domain", "listening_image",
        "listening_indicator_result", "indicator_catalog",
    ):
        assert t in names, f"缺表 {t}"


def test_indicator_seed_count_and_distribution(migrated_db):
    """指标种子总数 30，按领域分布正确。"""
    conn = sqlite3.connect(str(migrated_db))
    total = conn.execute("SELECT COUNT(*) FROM indicator_catalog").fetchone()[0]
    by_domain = dict(
        conn.execute("SELECT domain, COUNT(*) FROM indicator_catalog GROUP BY domain").fetchall()
    )
    conn.close()
    assert total == 30
    assert by_domain == _EXPECTED_BY_DOMAIN


def test_indicator_seed_integrity(migrated_db):
    """每条种子三档标准非空，tenant_id=1，max_stars=3。"""
    conn = sqlite3.connect(str(migrated_db))
    missing = conn.execute(
        "SELECT COUNT(*) FROM indicator_catalog "
        "WHERE standard_star1 IS NULL OR standard_star2 IS NULL OR standard_star3 IS NULL"
    ).fetchone()[0]
    bad_tenant = conn.execute(
        "SELECT COUNT(*) FROM indicator_catalog WHERE tenant_id != 1"
    ).fetchone()[0]
    bad_max = conn.execute(
        "SELECT COUNT(*) FROM indicator_catalog WHERE max_stars != 3"
    ).fetchone()[0]
    conn.close()
    assert missing == 0
    assert bad_tenant == 0
    assert bad_max == 0


def test_export_records_has_listening_col(migrated_db):
    """export_records 含 listening_record_id 列。"""
    conn = sqlite3.connect(str(migrated_db))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(export_records)").fetchall()}
    conn.close()
    assert "listening_record_id" in cols
