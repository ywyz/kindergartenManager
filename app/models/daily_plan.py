"""每日活动计划数据模型与 CRUD 操作"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from app.db import execute_query, execute_one, execute_insert, execute_update, json_encode, json_decode


@dataclass
class MorningActivity:
    """晨间活动"""
    group_activity_name: str = ""    # 集体活动名称
    self_selected_name: str = ""     # 自选活动名称
    key_guidance: str = ""           # 重点指导（通常是某个活动名称）
    activity_goal: str = ""          # 活动目标
    guidance_points: str = ""        # 指导要点


@dataclass
class MorningTalk:
    """晨间谈话"""
    topic: str = ""                  # 谈话主题
    questions: str = ""              # 问题设计


@dataclass
class GroupActivity:
    """集体活动（来自教案拆分）"""
    theme: str = ""                  # 活动主题
    goal: str = ""                   # 活动目标
    preparation: str = ""            # 活动准备
    key_point: str = ""              # 活动重点
    difficulty: str = ""             # 活动难点
    process: str = ""                # 活动过程
    process_original: str = ""       # 活动过程（原始，用于对比）


@dataclass
class AreaActivity:
    """区域活动（室内/户外通用）"""
    game_area: str = ""              # 游戏区域
    key_guidance: str = ""           # 重点指导
    activity_goal: str = ""          # 活动目标
    guidance_points: str = ""        # 指导要点
    support_strategy: str = ""       # 支持策略


@dataclass
class DailyPlan:
    """每日活动计划完整数据模型"""
    id: Optional[int] = None
    plan_date: Optional[date] = None
    week_number: Optional[int] = None
    day_of_week: str = ""
    grade: str = ""
    class_name: str = ""
    semester_id: Optional[int] = None
    morning_activity: MorningActivity = field(default_factory=MorningActivity)
    morning_talk: MorningTalk = field(default_factory=MorningTalk)
    group_activity: GroupActivity = field(default_factory=GroupActivity)
    indoor_area: AreaActivity = field(default_factory=AreaActivity)
    outdoor_game: AreaActivity = field(default_factory=AreaActivity)
    daily_reflection: str = ""
    original_lesson_text: str = ""
    ai_modified_parts: dict = field(default_factory=dict)
    status: str = "draft"

    # ------------------------------------------------------------------
    # 序列化 / 反序列化
    # ------------------------------------------------------------------

    def to_db_dict(self) -> dict:
        import dataclasses
        return {
            "plan_date": self.plan_date,
            "week_number": self.week_number,
            "day_of_week": self.day_of_week,
            "grade": self.grade,
            "class_name": self.class_name,
            "semester_id": self.semester_id,
            "morning_activity_json": json_encode(dataclasses.asdict(self.morning_activity)),
            "morning_talk_json": json_encode(dataclasses.asdict(self.morning_talk)),
            "group_activity_json": json_encode(dataclasses.asdict(self.group_activity)),
            "indoor_area_json": json_encode(dataclasses.asdict(self.indoor_area)),
            "outdoor_game_json": json_encode(dataclasses.asdict(self.outdoor_game)),
            "daily_reflection": self.daily_reflection,
            "original_lesson_text": self.original_lesson_text,
            "ai_modified_parts_json": json_encode(self.ai_modified_parts),
            "status": self.status,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "DailyPlan":
        ma_data = json_decode(row.get("morning_activity_json")) or {}
        mt_data = json_decode(row.get("morning_talk_json")) or {}
        ga_data = json_decode(row.get("group_activity_json")) or {}
        ia_data = json_decode(row.get("indoor_area_json")) or {}
        og_data = json_decode(row.get("outdoor_game_json")) or {}

        return cls(
            id=row.get("id"),
            plan_date=row.get("plan_date"),
            week_number=row.get("week_number"),
            day_of_week=row.get("day_of_week", ""),
            grade=row.get("grade", ""),
            class_name=row.get("class_name", ""),
            semester_id=row.get("semester_id"),
            morning_activity=MorningActivity(**{
                k: ma_data.get(k, "") for k in MorningActivity.__dataclass_fields__
            }),
            morning_talk=MorningTalk(**{
                k: mt_data.get(k, "") for k in MorningTalk.__dataclass_fields__
            }),
            group_activity=GroupActivity(**{
                k: ga_data.get(k, "") for k in GroupActivity.__dataclass_fields__
            }),
            indoor_area=AreaActivity(**{
                k: ia_data.get(k, "") for k in AreaActivity.__dataclass_fields__
            }),
            outdoor_game=AreaActivity(**{
                k: og_data.get(k, "") for k in AreaActivity.__dataclass_fields__
            }),
            daily_reflection=row.get("daily_reflection", ""),
            original_lesson_text=row.get("original_lesson_text", ""),
            ai_modified_parts=json_decode(row.get("ai_modified_parts_json")) or {},
            status=row.get("status", "draft"),
        )


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------

def get_plan_by_date(plan_date: date, grade: str = "", class_name: str = "") -> Optional[DailyPlan]:
    """按日期（及可选年级/班级）获取计划"""
    sql = "SELECT * FROM daily_plans WHERE plan_date = %s"
    args: list = [plan_date]
    if grade:
        sql += " AND grade = %s"
        args.append(grade)
    if class_name:
        sql += " AND class_name = %s"
        args.append(class_name)
    sql += " LIMIT 1"
    row = execute_one(sql, args)
    return DailyPlan.from_db_row(row) if row else None


def get_plans(limit: int = 50, offset: int = 0) -> list[DailyPlan]:
    """获取计划列表"""
    rows = execute_query(
        "SELECT * FROM daily_plans ORDER BY plan_date DESC LIMIT %s OFFSET %s",
        (limit, offset),
    )
    return [DailyPlan.from_db_row(r) for r in rows]


def save_plan(plan: DailyPlan) -> int:
    """保存或更新计划，返回 ID"""
    data = plan.to_db_dict()
    if plan.id:
        sets = ", ".join(f"{k} = %s" for k in data)
        sql = f"UPDATE daily_plans SET {sets} WHERE id = %s"
        execute_update(sql, list(data.values()) + [plan.id])
        return plan.id
    else:
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO daily_plans ({cols}) VALUES ({placeholders})"
        return execute_insert(sql, list(data.values()))


def delete_plan(plan_id: int) -> None:
    """删除计划"""
    execute_update("DELETE FROM daily_plans WHERE id = %s", (plan_id,))
