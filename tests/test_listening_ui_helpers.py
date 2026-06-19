"""P7 — 一对一倾听页面纯函数测试。"""
from datetime import date

from app.ui.pages.one_on_one_listening import (
    build_export_filename,
    default_year_month,
    format_stage_label,
    infer_age_by_grade,
    parse_stage_label,
    validate_image_count,
)


def test_infer_age_by_grade():
    assert infer_age_by_grade("小班") == "4岁"
    assert infer_age_by_grade("中班") == "5岁"
    assert infer_age_by_grade("大班") == "6岁"
    assert infer_age_by_grade("") == ""
    assert infer_age_by_grade(None) == ""
    assert infer_age_by_grade(" 小班 ") == "4岁"


def test_default_year_month():
    assert default_year_month(date(2026, 4, 15)) == (2026, 4)
    assert default_year_month(date(2025, 12, 1)) == (2025, 12)


def test_validate_image_count():
    assert validate_image_count(1) is True
    assert validate_image_count(3) is True
    assert validate_image_count(0) is False
    assert validate_image_count(4) is False


def test_stage_label_roundtrip():
    assert format_stage_label("小班", "下学期") == "小班·下学期"
    assert parse_stage_label("小班·下学期") == ("小班", "下学期")
    assert parse_stage_label("中班·上学期") == ("中班", "上学期")
    # 异常格式不崩溃
    assert parse_stage_label("无分隔")[0] == "无分隔"


def test_build_export_filename():
    fname = build_export_filename(1, 1, "小明", 2026, 4, "合并")
    assert fname == "1_1_小明_2026年4月_一对一倾听_合并.docx"
    # 含斜杠/空格的姓名被清理
    assert "/" not in build_export_filename(1, 1, "小/明 明", 2026, 4, "按领域")
    # 空姓名回退
    assert "幼儿" in build_export_filename(1, 1, "", 2026, 4, "合并")
