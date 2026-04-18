"""计划相关业务逻辑 - 整合数据库操作与设置读取"""
from datetime import date
from typing import Optional

from app.db import execute_one, execute_query, execute_update, execute_insert, json_encode, json_decode
from app.models.daily_plan import DailyPlan, save_plan, get_plan_by_date, get_plans


# ---------------------------------------------------------------------------
# 学期设置
# ---------------------------------------------------------------------------

def get_latest_semester() -> Optional[dict]:
    """获取最近一条学期设置"""
    return execute_one("SELECT * FROM semester_settings ORDER BY id DESC LIMIT 1")


def save_semester(
    semester_name: str,
    start_date: date,
    end_date: date,
    grade: str,
    class_name: str,
    semester_id: Optional[int] = None,
) -> int:
    """保存或更新学期设置，返回 ID"""
    if semester_id:
        execute_update(
            "UPDATE semester_settings SET semester_name=%s, start_date=%s, end_date=%s, "
            "grade=%s, class_name=%s WHERE id=%s",
            (semester_name, start_date, end_date, grade, class_name, semester_id),
        )
        return semester_id
    return execute_insert(
        "INSERT INTO semester_settings (semester_name, start_date, end_date, grade, class_name) "
        "VALUES (%s, %s, %s, %s, %s)",
        (semester_name, start_date, end_date, grade, class_name),
    )


# ---------------------------------------------------------------------------
# 应用设置（键值对）
# ---------------------------------------------------------------------------

def get_setting(key: str, default: str = "") -> str:
    """读取应用设置"""
    row = execute_one("SELECT setting_val FROM app_settings WHERE setting_key = %s", (key,))
    return (row["setting_val"] if row else None) or default


def set_setting(key: str, value: str) -> None:
    """写入或更新应用设置"""
    existing = execute_one("SELECT id FROM app_settings WHERE setting_key = %s", (key,))
    if existing:
        execute_update(
            "UPDATE app_settings SET setting_val = %s WHERE setting_key = %s",
            (value, key),
        )
    else:
        execute_insert(
            "INSERT INTO app_settings (setting_key, setting_val) VALUES (%s, %s)",
            (key, value),
        )


# ---------------------------------------------------------------------------
# AI 配置
# ---------------------------------------------------------------------------

def get_ai_config() -> Optional[dict]:
    """获取当前激活的AI配置"""
    return execute_one("SELECT * FROM ai_config ORDER BY id DESC LIMIT 1")


def save_ai_config(api_url: str, api_key: str, model_name: str, config_id: Optional[int] = None) -> int:
    """保存 AI 配置。api_key 使用 Fernet 对称加密后存储。"""
    from app.services.crypto import encrypt
    encrypted_key = encrypt(api_key)

    if config_id:
        execute_update(
            "UPDATE ai_config SET api_url=%s, api_key=%s, model_name=%s WHERE id=%s",
            (api_url, encrypted_key, model_name, config_id),
        )
        return config_id
    return execute_insert(
        "INSERT INTO ai_config (api_url, api_key, model_name) VALUES (%s, %s, %s)",
        (api_url, encrypted_key, model_name),
    )


def get_decrypted_api_key(config_id: Optional[int] = None) -> str:
    """解密并返回 API Key（兼容历史 Base64 存储）"""
    from app.services.crypto import decrypt
    row = (
        execute_one("SELECT api_key FROM ai_config WHERE id=%s", (config_id,))
        if config_id
        else execute_one("SELECT api_key FROM ai_config ORDER BY id DESC LIMIT 1")
    )
    if not row or not row.get("api_key"):
        return ""
    return decrypt(row["api_key"])


# ---------------------------------------------------------------------------
# 提示词管理
# ---------------------------------------------------------------------------

PROMPT_CATEGORIES = {
    "lesson_split": "教案拆分",
    "process_modify": "活动过程修改",
    "morning_activity": "晨间活动",
    "morning_talk": "晨间谈话",
    "indoor_area": "室内区域",
    "outdoor_game": "户外游戏",
}


def get_prompts(category: Optional[str] = None) -> list[dict]:
    """获取提示词列表"""
    if category:
        return execute_query(
            "SELECT * FROM prompts WHERE prompt_category = %s ORDER BY id DESC",
            (category,),
        )
    return execute_query("SELECT * FROM prompts ORDER BY prompt_category, id")


def save_prompt(name: str, category: str, content: str, prompt_id: Optional[int] = None) -> int:
    """保存或更新提示词"""
    if prompt_id:
        execute_update(
            "UPDATE prompts SET prompt_name=%s, prompt_category=%s, prompt_content=%s WHERE id=%s",
            (name, category, content, prompt_id),
        )
        return prompt_id
    return execute_insert(
        "INSERT INTO prompts (prompt_name, prompt_category, prompt_content) VALUES (%s, %s, %s)",
        (name, category, content),
    )


def set_prompt_active(prompt_id: int, category: str) -> None:
    """将指定提示词设为激活，同时取消同类别其他提示词的激活"""
    execute_update(
        "UPDATE prompts SET is_active = 0 WHERE prompt_category = %s",
        (category,),
    )
    execute_update(
        "UPDATE prompts SET is_active = 1 WHERE id = %s",
        (prompt_id,),
    )


def delete_prompt(prompt_id: int) -> None:
    """删除提示词"""
    execute_update("DELETE FROM prompts WHERE id = %s", (prompt_id,))


# ---------------------------------------------------------------------------
# 计划 CRUD（代理模型层）
# ---------------------------------------------------------------------------

__all__ = [
    "get_latest_semester", "save_semester",
    "get_setting", "set_setting",
    "get_ai_config", "save_ai_config", "get_decrypted_api_key",
    "PROMPT_CATEGORIES", "get_prompts", "save_prompt", "set_prompt_active", "delete_prompt",
    "get_plan_by_date", "get_plans", "save_plan",
]
