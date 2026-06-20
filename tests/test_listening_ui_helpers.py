"""P7 — 一对一倾听页面纯函数测试。"""
from datetime import date

from app.ui.pages.one_on_one_listening import (
    build_batch_export_filename,
    build_export_filename,
    default_year_month,
    distribute_images_by_filename,
    format_record_summary,
    format_stage_label,
    infer_age_by_grade,
    pack_domain_files_to_zip,
    parse_stage_label,
    validate_bulk_import_count,
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


def test_build_batch_export_filename():
    fname = build_batch_export_filename(1, 2, 2026, 4, 3)
    assert fname == "1_2_2026年4月_一对一倾听_批量按领域_3人.zip"


def test_validate_bulk_import_count():
    assert validate_bulk_import_count(15) is True
    assert validate_bulk_import_count(14) is False
    assert validate_bulk_import_count(16) is False
    assert validate_bulk_import_count(0) is False


def test_distribute_images_by_filename():
    import random

    domains = ["健康", "语言", "社会", "艺术", "科学"]
    files = [(f"{i:02d}.jpg", bytes([i])) for i in range(15)]
    shuffled = files[:]
    random.shuffle(shuffled)
    dist = distribute_images_by_filename(shuffled, domains, per_domain=3)
    assert list(dist.keys()) == domains
    assert all(len(v) == 3 for v in dist.values())
    # 按文件名排序：健康取前3，科学取后3
    assert dist["健康"] == [bytes([0]), bytes([1]), bytes([2])]
    assert dist["科学"] == [bytes([12]), bytes([13]), bytes([14])]


def test_pack_domain_files_to_zip():
    import io
    import zipfile

    files = {"健康": b"health-docx", "语言": b"lang-docx"}
    data = pack_domain_files_to_zip(files)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert set(zf.namelist()) == {"健康.docx", "语言.docx"}
        assert zf.read("健康.docx") == b"health-docx"


def test_format_record_summary():
    s = format_record_summary("小明", 2026, 4, "小班", "下学期", "王老师")
    assert "2026年4月" in s
    assert "小明" in s
    assert "小班·下学期" in s
    assert "王老师" in s
    # 缺失字段不崩溃
    assert "未命名" in format_record_summary("", None, None, None, None, None)
