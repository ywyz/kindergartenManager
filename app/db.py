"""PyMySQL 数据库连接封装与自动建表"""
import json
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from typing import Any

from app.config import DBConfig

# ---------------------------------------------------------------------------
# DDL - 表结构
# ---------------------------------------------------------------------------
_DDL_STATEMENTS = [
    # 学期设置
    """
    CREATE TABLE IF NOT EXISTS semester_settings (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        semester_name VARCHAR(50) NOT NULL COMMENT '学期名称，如 2025-2026学年第二学期',
        start_date  DATE NOT NULL COMMENT '学期开始日期',
        end_date    DATE NOT NULL COMMENT '学期结束日期',
        grade       VARCHAR(20) NOT NULL COMMENT '年级：小班/中班/大班',
        class_name  VARCHAR(20) NOT NULL COMMENT '班级：1班/2班/3班/4班',
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学期设置';
    """,

    # AI 配置
    """
    CREATE TABLE IF NOT EXISTS ai_config (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        api_url     VARCHAR(500) NOT NULL COMMENT 'AI API 地址',
        api_key     VARCHAR(1000) NOT NULL COMMENT 'API Key（加密存储）',
        model_name  VARCHAR(100) NOT NULL COMMENT '模型名称',
        is_global   TINYINT(1) DEFAULT 1 COMMENT '是否为全局配置',
        user_id     INT NULL COMMENT '用户ID（预留，单用户版为NULL）',
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI配置';
    """,

    # 每日活动计划
    """
    CREATE TABLE IF NOT EXISTS daily_plans (
        id                      INT AUTO_INCREMENT PRIMARY KEY,
        plan_date               DATE NOT NULL COMMENT '计划日期',
        week_number             INT COMMENT '第几周',
        day_of_week             VARCHAR(10) COMMENT '星期几（中文）',
        grade                   VARCHAR(20) COMMENT '年级',
        class_name              VARCHAR(20) COMMENT '班级',
        semester_id             INT NULL COMMENT '学期ID（FK）',
        morning_activity_json   JSON COMMENT '晨间活动所有字段',
        morning_talk_json       JSON COMMENT '晨间谈话所有字段',
        group_activity_json     JSON COMMENT '集体活动所有字段',
        indoor_area_json        JSON COMMENT '室内区域活动所有字段',
        outdoor_game_json       JSON COMMENT '户外游戏活动所有字段',
        daily_reflection        TEXT COMMENT '一日活动反思',
        original_lesson_text    LONGTEXT COMMENT '原始教案文本',
        ai_modified_parts_json  JSON COMMENT 'AI修改部分（用于红色标记）',
        status                  ENUM('draft','completed') DEFAULT 'draft',
        created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_plan_date_grade_class (plan_date, grade, class_name),
        FOREIGN KEY (semester_id) REFERENCES semester_settings(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日活动计划';
    """,

    # 提示词管理
    """
    CREATE TABLE IF NOT EXISTS prompts (
        id               INT AUTO_INCREMENT PRIMARY KEY,
        prompt_name      VARCHAR(100) NOT NULL COMMENT '提示词名称',
        prompt_category  VARCHAR(50)  NOT NULL COMMENT '分类：lesson_split/daily_plan/morning_activity等',
        prompt_content   LONGTEXT     NOT NULL COMMENT '提示词内容（支持占位符变量）',
        is_active        TINYINT(1) DEFAULT 1 COMMENT '是否激活',
        created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提示词管理';
    """,

    # 设置（键值对，存储区域/户外游戏内容等）
    """
    CREATE TABLE IF NOT EXISTS app_settings (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        setting_key VARCHAR(100) NOT NULL UNIQUE COMMENT '设置键',
        setting_val LONGTEXT COMMENT '设置值（JSON或纯文本）',
        updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='应用设置';
    """,

    # AI 调用日志
    """
    CREATE TABLE IF NOT EXISTS ai_call_logs (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        category      VARCHAR(60)  COMMENT '调用分类：lesson_split/process_modify/morning_activity 等',
        model_name    VARCHAR(100) COMMENT '使用的模型名称',
        prompt_text   LONGTEXT     COMMENT '发送的 prompt（user message）',
        response_text LONGTEXT     COMMENT 'AI 返回的原始响应',
        status        ENUM('success','error') DEFAULT 'success',
        error_msg     TEXT         COMMENT '错误信息（status=error 时）',
        duration_ms   INT          COMMENT '耗时（毫秒）',
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 调用日志';
    """,
]


# ---------------------------------------------------------------------------
# 连接管理
# ---------------------------------------------------------------------------

def get_connection() -> pymysql.connections.Connection:
    """获取数据库连接"""
    return pymysql.connect(
        cursorclass=DictCursor,
        **DBConfig.as_dict(),
    )


@contextmanager
def db_cursor():
    """上下文管理器，自动关闭连接"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 通用操作
# ---------------------------------------------------------------------------

def execute_query(sql: str, args: tuple | list | None = None) -> list[dict]:
    """执行查询，返回结果列表"""
    with db_cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.fetchall() or []


def execute_one(sql: str, args: tuple | list | None = None) -> dict | None:
    """执行查询，返回单行"""
    with db_cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.fetchone()


def execute_update(sql: str, args: tuple | list | None = None) -> int:
    """执行 INSERT/UPDATE/DELETE，返回影响行数"""
    with db_cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.rowcount


def execute_insert(sql: str, args: tuple | list | None = None) -> int:
    """执行 INSERT，返回最后插入的 ID"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, args)
            last_id = cursor.lastrowid or 0
            if not last_id:
                # 兼容 ON DUPLICATE KEY UPDATE 等场景，尽量从连接级状态获取 ID
                cursor.execute("SELECT LAST_INSERT_ID() AS id")
                row = cursor.fetchone() or {}
                last_id = row.get("id", 0) if isinstance(row, dict) else (row[0] if row else 0)
        conn.commit()
        return int(last_id or 0)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_many(sql: str, args_list: list) -> int:
    """批量执行，返回影响行数"""
    with db_cursor() as cursor:
        cursor.executemany(sql, args_list)
        return cursor.rowcount


def json_encode(obj: Any) -> str | None:
    """将 Python 对象转为 JSON 字符串，用于存储"""
    if obj is None:
        return None
    return json.dumps(obj, ensure_ascii=False)


def json_decode(text: str | None) -> Any:
    """将 JSON 字符串解析为 Python 对象"""
    if not text:
        return None
    if isinstance(text, (dict, list)):
        return text
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


# ---------------------------------------------------------------------------
# 自动建表
# ---------------------------------------------------------------------------

def init_db() -> None:
    """启动时执行：检查数据库连接并自动创建所有表"""
    try:
        conn = pymysql.connect(
            host=DBConfig.HOST,
            port=DBConfig.PORT,
            user=DBConfig.USER,
            password=DBConfig.PASSWORD,
            charset="utf8mb4",
            autocommit=True,
        )
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DBConfig.NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
            cursor.execute(f"USE `{DBConfig.NAME}`;")
            for ddl in _DDL_STATEMENTS:
                cursor.execute(ddl)
            # 迁移：为已存在的 daily_plans 表补加唯一索引（若不存在）
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM information_schema.statistics "
                "WHERE table_schema = %s AND table_name = 'daily_plans' "
                "AND index_name = 'uq_plan_date_grade_class'",
                (DBConfig.NAME,),
            )
            row = cursor.fetchone()
            cnt = row["cnt"] if isinstance(row, dict) else row[0]
            if cnt == 0:
                cursor.execute(
                    "ALTER TABLE daily_plans "
                    "ADD UNIQUE KEY uq_plan_date_grade_class (plan_date, grade, class_name)"
                )
            # 迁移：为 ai_config 补加 weight 列（若不存在）
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = 'ai_config' AND column_name = 'weight'",
                (DBConfig.NAME,),
            )
            row2 = cursor.fetchone()
            cnt2 = row2["cnt"] if isinstance(row2, dict) else row2[0]
            if cnt2 == 0:
                cursor.execute(
                    "ALTER TABLE ai_config ADD COLUMN weight INT NOT NULL DEFAULT 1 "
                    "COMMENT '负载均衡权重（越大分配概率越高）'"
                )
        conn.close()
        print(f"[DB] 数据库 {DBConfig.NAME} 初始化成功")
    except Exception as e:
        print(f"[DB] 数据库初始化失败：{e}")
        raise


# ---------------------------------------------------------------------------
# AI 调用日志（fire-and-forget，失败不影响主流程）
# ---------------------------------------------------------------------------

def log_ai_call(
    category: str,
    model_name: str,
    prompt_text: str,
    response_text: str,
    status: str = "success",
    error_msg: str = "",
    duration_ms: int = 0,
) -> None:
    """写入 AI 调用日志，任何异常都静默忽略。"""
    try:
        execute_insert(
            "INSERT INTO ai_call_logs "
            "(category, model_name, prompt_text, response_text, status, error_msg, duration_ms) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                category[:60],
                model_name[:100],
                prompt_text[:20000],
                response_text[:20000],
                status,
                error_msg[:2000],
                duration_ms,
            ),
        )
    except Exception:
        pass  # 日志失败绝不影响主流程
