"""周计划数据模型与 CRUD 操作"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from app.db import execute_query, execute_one, execute_insert, execute_update, json_encode, json_decode


@dataclass
class WeekDayPlan:
    """单天活动快照（周计划中每天的内容）"""
    date_str: str = ""              # YYYY-MM-DD
    day_of_week: str = ""           # 周一 ~ 周五
    is_holiday: bool = False        # 是否放假

    # 晨间谈话
    morning_talk_topic: str = ""
    morning_talk_questions: str = ""

    # 集体活动（来自一日计划快照）
    group_activity_theme: str = ""
    group_activity_goal: str = ""
    group_activity_process: str = ""

    # 户外游戏
    outdoor_game_area: str = ""
    outdoor_game_circuit: str = ""  # 体能大循环
    outdoor_game_group: str = ""    # 集体游戏
    outdoor_game_free: str = ""     # 自主游戏

    # 区域游戏
    area_game_zone: str = ""        # 重点指导区域
    area_game_goal: str = ""        # 活动目标
    area_game_materials: str = ""   # 区域材料
    area_game_guidance: str = ""    # 区域指导

    def to_dict(self) -> dict:
        import dataclasses
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "WeekDayPlan":
        valid_keys = cls.__dataclass_fields__.keys()
        return cls(**{k: d.get(k, v.default) for k, v in cls.__dataclass_fields__.items()})


@dataclass
class WeeklyPlan:
    """周计划完整数据模型"""
    id: Optional[int] = None
    semester_id: Optional[int] = None
    week_number: Optional[int] = None
    week_start_date: Optional[date] = None   # 周一
    week_end_date: Optional[date] = None     # 周五
    grade: str = ""
    class_name: str = ""
    theme: str = ""                          # 本周活动主题
    teacher_name: str = ""                   # 教师姓名（快照）
    carer_name: str = ""                     # 保育员姓名（快照）
    days: list = field(default_factory=list) # list[WeekDayPlan]，5 天
    week_focus: str = ""                     # 本周重点
    env_setup: str = ""                      # 环境创设
    life_habits: str = ""                    # 生活习惯培养
    home_school: str = ""                    # 家园共育
    status: str = "draft"

    # ------------------------------------------------------------------
    # 序列化 / 反序列化
    # ------------------------------------------------------------------

    def to_db_dict(self) -> dict:
        return {
            "semester_id": self.semester_id,
            "week_number": self.week_number,
            "week_start_date": self.week_start_date,
            "week_end_date": self.week_end_date,
            "grade": self.grade,
            "class_name": self.class_name,
            "theme": self.theme,
            "teacher_name": self.teacher_name,
            "carer_name": self.carer_name,
            "days_json": json_encode([d.to_dict() for d in self.days]),
            "week_focus": self.week_focus,
            "env_setup": self.env_setup,
            "life_habits": self.life_habits,
            "home_school": self.home_school,
            "status": self.status,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "WeeklyPlan":
        days_data = json_decode(row.get("days_json")) or []
        days = [WeekDayPlan.from_dict(d) for d in days_data]
        return cls(
            id=row.get("id"),
            semester_id=row.get("semester_id"),
            week_number=row.get("week_number"),
            week_start_date=row.get("week_start_date"),
            week_end_date=row.get("week_end_date"),
            grade=row.get("grade", ""),
            class_name=row.get("class_name", ""),
            theme=row.get("theme", ""),
            teacher_name=row.get("teacher_name", ""),
            carer_name=row.get("carer_name", ""),
            days=days,
            week_focus=row.get("week_focus", ""),
            env_setup=row.get("env_setup", ""),
            life_habits=row.get("life_habits", ""),
            home_school=row.get("home_school", ""),
            status=row.get("status", "draft"),
        )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def save_weekly_plan(plan: WeeklyPlan) -> int:
    """
    保存或更新周计划（upsert by semester_id + week_number + grade + class_name）。
    返回计划 id。
    """
    d = plan.to_db_dict()

    if plan.id:
        execute_update(
            """
            UPDATE weekly_plans SET
                semester_id=%s, week_number=%s, week_start_date=%s, week_end_date=%s,
                grade=%s, class_name=%s, theme=%s, teacher_name=%s, carer_name=%s,
                days_json=%s, week_focus=%s, env_setup=%s, life_habits=%s, home_school=%s,
                status=%s
            WHERE id=%s
            """,
            (
                d["semester_id"], d["week_number"], d["week_start_date"], d["week_end_date"],
                d["grade"], d["class_name"], d["theme"], d["teacher_name"], d["carer_name"],
                d["days_json"], d["week_focus"], d["env_setup"], d["life_habits"], d["home_school"],
                d["status"], plan.id,
            ),
        )
        return plan.id

    # 先查是否存在（按唯一键）
    existing = execute_one(
        "SELECT id FROM weekly_plans WHERE semester_id=%s AND week_number=%s "
        "AND grade=%s AND class_name=%s",
        (d["semester_id"], d["week_number"], d["grade"], d["class_name"]),
    )
    if existing:
        plan_id = existing["id"]
        execute_update(
            """
            UPDATE weekly_plans SET
                week_start_date=%s, week_end_date=%s, theme=%s, teacher_name=%s, carer_name=%s,
                days_json=%s, week_focus=%s, env_setup=%s, life_habits=%s, home_school=%s,
                status=%s
            WHERE id=%s
            """,
            (
                d["week_start_date"], d["week_end_date"], d["theme"], d["teacher_name"], d["carer_name"],
                d["days_json"], d["week_focus"], d["env_setup"], d["life_habits"], d["home_school"],
                d["status"], plan_id,
            ),
        )
        return plan_id

    return execute_insert(
        """
        INSERT INTO weekly_plans
            (semester_id, week_number, week_start_date, week_end_date,
             grade, class_name, theme, teacher_name, carer_name,
             days_json, week_focus, env_setup, life_habits, home_school, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            d["semester_id"], d["week_number"], d["week_start_date"], d["week_end_date"],
            d["grade"], d["class_name"], d["theme"], d["teacher_name"], d["carer_name"],
            d["days_json"], d["week_focus"], d["env_setup"], d["life_habits"], d["home_school"],
            d["status"],
        ),
    )


def get_weekly_plan(semester_id: int, week_number: int, grade: str, class_name: str) -> Optional[WeeklyPlan]:
    """按学期周+年级班级查询周计划"""
    row = execute_one(
        "SELECT * FROM weekly_plans WHERE semester_id=%s AND week_number=%s "
        "AND grade=%s AND class_name=%s",
        (semester_id, week_number, grade, class_name),
    )
    return WeeklyPlan.from_db_row(row) if row else None


def get_weekly_plan_by_id(plan_id: int) -> Optional[WeeklyPlan]:
    row = execute_one("SELECT * FROM weekly_plans WHERE id=%s", (plan_id,))
    return WeeklyPlan.from_db_row(row) if row else None
