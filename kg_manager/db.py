"""
数据库操作模块：学期管理、教案数据存取
"""

import sqlite3
import json
from pathlib import Path
from datetime import date, datetime


def save_semester(db_path, start_date, end_date):
    """保存学期信息到数据库"""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS semesters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO semesters "
            "(start_date, end_date, created_at) "
            "VALUES (?, ?, ?)",
            (
                start_date.isoformat(),
                end_date.isoformat(),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )


def load_latest_semester(db_path):
    """加载最新的学期信息"""
    db_path = Path(db_path)
    if not db_path.exists():
        return None
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT start_date, end_date "
            "FROM semesters "
            "ORDER BY id DESC "
            "LIMIT 1"
        ).fetchone()
    if not row:
        return None
    return date.fromisoformat(row[0]), date.fromisoformat(row[1])


def init_plan_db(db_path):
    """初始化教案数据库表"""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS plan_entries ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  plan_date TEXT NOT NULL UNIQUE,"
            "  plan_data TEXT NOT NULL,"
            "  created_at TEXT NOT NULL,"
            "  updated_at TEXT NOT NULL"
            ")"
        )


def save_plan_data(db_path, plan_date, plan_data):
    """保存或更新教案数据"""
    db_path = Path(db_path)
    init_plan_db(db_path)
    now = datetime.now().isoformat(timespec="seconds")
    payload = json.dumps(plan_data, ensure_ascii=False)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO plan_entries (plan_date, plan_data, created_at, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(plan_date) DO UPDATE SET "
            "plan_data=excluded.plan_data, updated_at=excluded.updated_at",
            (plan_date, payload, now, now),
        )


def load_plan_data(db_path, plan_date):
    """加载指定日期的教案数据"""
    db_path = Path(db_path)
    if not db_path.exists():
        return None
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT plan_data FROM plan_entries WHERE plan_date = ?",
            (plan_date,),
        ).fetchone()
    if not row:
        return None
    return json.loads(row[0])


def list_plan_dates(db_path):
    """列出数据库中所有教案的日期"""
    db_path = Path(db_path)
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT plan_date FROM plan_entries ORDER BY plan_date ASC"
        ).fetchall()
    return [row[0] for row in rows]


def delete_plan_data(db_path, plan_date):
    """删除指定日期的教案"""
    db_path = Path(db_path)
    if not db_path.exists():
        return False
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM plan_entries WHERE plan_date = ?",
            (plan_date,),
        )
    return cursor.rowcount > 0


def get_plan_data_info(db_path, plan_date):
    """获取教案的元数据（创建时间、更新时间）"""
    db_path = Path(db_path)
    if not db_path.exists():
        return None
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT created_at, updated_at FROM plan_entries WHERE plan_date = ?",
            (plan_date,),
        ).fetchone()
    if not row:
        return None
    return {"created_at": row[0], "updated_at": row[1]}


def init_ai_config_db(db_path):
    """初始化AI配置表"""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS ai_config ("
            "  config_key TEXT PRIMARY KEY,"
            "  config_value TEXT NOT NULL,"
            "  updated_at TEXT NOT NULL"
            ")"
        )


def save_ai_prompt(db_path, prompt_text):
    """保存AI提示词到数据库"""
    db_path = Path(db_path)
    init_ai_config_db(db_path)
    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO ai_config (config_key, config_value, updated_at) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(config_key) DO UPDATE SET "
            "config_value=excluded.config_value, "
            "updated_at=excluded.updated_at",
            ("custom_prompt", prompt_text, now),
        )


def load_ai_prompt(db_path):
    """加载AI提示词"""
    db_path = Path(db_path)
    if not db_path.exists():
        return ""
    init_ai_config_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT config_value FROM ai_config WHERE config_key = ?",
            ("custom_prompt",),
        ).fetchone()
    if not row:
        return ""
    return row[0]


def init_ai_prompt_db(db_path):
    """初始化AI提示词模板表"""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS ai_prompt_templates ("
            "  template_key TEXT PRIMARY KEY,"
            "  template_json TEXT NOT NULL,"
            "  updated_at TEXT NOT NULL"
            ")"
        )


def save_ai_prompt_template(db_path, template_key, template_data):
    """保存AI提示词模板到数据库"""
    db_path = Path(db_path)
    init_ai_prompt_db(db_path)
    now = datetime.now().isoformat(timespec="seconds")
    payload = json.dumps(template_data, ensure_ascii=False)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO ai_prompt_templates "
            "(template_key, template_json, updated_at) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(template_key) DO UPDATE SET "
            "template_json=excluded.template_json, "
            "updated_at=excluded.updated_at",
            (template_key, payload, now),
        )


def load_ai_prompt_template(db_path, template_key):
    """加载AI提示词模板"""
    db_path = Path(db_path)
    if not db_path.exists():
        return None
    init_ai_prompt_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT template_json FROM ai_prompt_templates "
            "WHERE template_key = ?",
            (template_key,),
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        return None
