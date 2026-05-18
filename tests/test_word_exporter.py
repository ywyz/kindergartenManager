"""Word 导出服务单元测试。

使用 python-docx 解析导出的 bytes，验证：
- 返回非空 bytes
- 表格共 8 行
- 周次/日期文本正确写入
- diff 差异中 changed=True 的句子字体为红色
- 无 diff 时直接输出改写文
- 空字段也能生成合法文档
"""
from datetime import date
from io import BytesIO

import pytest
from docx import Document
from docx.shared import RGBColor

from app.core.models.daily_plan import DailyPlan
from app.integration.word_export.exporter import export_daily_plan


def _make_plan(**kwargs) -> DailyPlan:
    """构造测试用 DailyPlan 实例（不依赖数据库，通过 SQLAlchemy __init__）。"""
    defaults: dict = {
        "tenant_id": 1,
        "user_id": 1,
        "plan_date": date(2026, 5, 18),
        "week_number": 3,
        "weekday_cn": "周一",
        "grade": "中班",
        "class_name": "阳光班",
        "activity_goal": "培养幼儿合作能力。",
        "activity_prep": "彩色积木若干。",
        "activity_key": "学会分工合作。",
        "activity_difficult": "协调动作一致。",
        "activity_process_original": "幼儿观察。老师示范。幼儿练习。",
        "activity_process_adapted": "幼儿仔细观察。老师耐心示范。幼儿反复练习。",
        "morning_activity": "体能大循环：跳绳、爬梯。",
        "indoor_area": "美工区：拼贴画。",
        "outdoor_activity": "追逐跑游戏。",
        "morning_talk_topic": "春天的花朵",
        "morning_talk_questions": "你最喜欢哪种花？为什么？",
        "daily_reflection": None,
    }
    defaults.update(kwargs)
    return DailyPlan(**defaults)


def _parse(doc_bytes: bytes) -> Document:
    return Document(BytesIO(doc_bytes))


class TestExportDailyPlan:
    def test_returns_nonempty_bytes(self):
        plan = _make_plan()
        result = export_daily_plan(plan, [])
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_table_has_8_rows(self):
        plan = _make_plan()
        result = export_daily_plan(plan, [])
        doc = _parse(result)
        assert len(doc.tables) == 1
        assert len(doc.tables[0].rows) == 8

    def test_week_number_in_first_row(self):
        plan = _make_plan(week_number=5)
        result = export_daily_plan(plan, [])
        doc = _parse(result)
        row0_text = doc.tables[0].rows[0].cells[0].text
        assert "5" in row0_text

    def test_date_in_second_row(self):
        plan = _make_plan(plan_date=date(2026, 5, 18), weekday_cn="周一")
        result = export_daily_plan(plan, [])
        doc = _parse(result)
        row1_text = doc.tables[0].rows[1].cells[0].text
        assert "5" in row1_text
        assert "18" in row1_text
        assert "周一" in row1_text

    def test_diff_changed_run_is_red(self):
        diff_result = [
            {"text": "幼儿仔细观察。", "changed": True},
            {"text": "老师耐心示范。", "changed": False},
            {"text": "幼儿反复练习。", "changed": True},
        ]
        plan = _make_plan()
        result = export_daily_plan(plan, diff_result)
        doc = _parse(result)

        content_cell = doc.tables[0].rows[4].cells[1]
        red_found = any(
            run.font.color.rgb == RGBColor(0xFF, 0x00, 0x00)
            for para in content_cell.paragraphs
            for run in para.runs
        )
        assert red_found, "应有 changed=True 的 run 使用红色字体"

    def test_unchanged_run_is_not_red(self):
        diff_result = [
            {"text": "幼儿仔细观察。", "changed": True},
            {"text": "老师耐心示范。", "changed": False},
        ]
        plan = _make_plan()
        result = export_daily_plan(plan, diff_result)
        doc = _parse(result)

        content_cell = doc.tables[0].rows[4].cells[1]
        for para in content_cell.paragraphs:
            for run in para.runs:
                if "老师耐心示范" in run.text:
                    assert run.font.color.rgb != RGBColor(0xFF, 0x00, 0x00), (
                        "changed=False 的 run 不应为红色"
                    )

    def test_no_diff_shows_adapted_text(self):
        plan = _make_plan(activity_process_adapted="改写后的过程文本。")
        result = export_daily_plan(plan, [])
        doc = _parse(result)
        cell_text = " ".join(
            p.text for p in doc.tables[0].rows[4].cells[1].paragraphs
        )
        assert "改写后的过程文本" in cell_text

    def test_morning_talk_written(self):
        plan = _make_plan(
            morning_talk_topic="今天的天气",
            morning_talk_questions="今天是晴天还是阴天？",
        )
        result = export_daily_plan(plan, [])
        doc = _parse(result)
        talk_text = " ".join(
            p.text for p in doc.tables[0].rows[3].cells[1].paragraphs
        )
        assert "今天的天气" in talk_text
        assert "晴天" in talk_text

    def test_empty_optional_fields_produce_valid_doc(self):
        plan = _make_plan(
            activity_goal=None,
            activity_prep=None,
            activity_key=None,
            activity_difficult=None,
            activity_process_original=None,
            activity_process_adapted=None,
            morning_activity=None,
            indoor_area=None,
            outdoor_activity=None,
            morning_talk_topic=None,
            morning_talk_questions=None,
        )
        result = export_daily_plan(plan, [])
        doc = _parse(result)
        assert len(doc.tables[0].rows) == 8
