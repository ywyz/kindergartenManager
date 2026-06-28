from app.ui.pages.homemade_teaching import (
    build_homemade_teaching_filename,
    format_setting_summary,
    validate_generation_context,
)


def test_build_homemade_teaching_filename():
    filename = build_homemade_teaching_filename(
        tenant_id=1,
        user_id=2,
        record_id=33,
        class_name="阳光班",
        teacher_name="张老师",
    )

    assert filename == "1_2_阳光班_张老师_33_自制教玩具.docx"


def test_build_homemade_teaching_filename_sanitizes_values():
    filename = build_homemade_teaching_filename(
        tenant_id=1,
        user_id=2,
        record_id=None,
        class_name="阳/光 班",
        teacher_name="",
    )

    assert "/" not in filename
    assert "阳光班" in filename
    assert "教师" in filename
    assert "新记录" in filename


def test_validate_generation_context_success():
    errors = validate_generation_context(
        {"grade": "中班", "class_name": "阳光班", "teacher_name": "张老师"}
    )
    assert errors == []


def test_validate_generation_context_missing_fields():
    errors = validate_generation_context(
        {"grade": "", "class_name": "", "teacher_name": ""}
    )

    assert "请先在设置页选择年级" in errors
    assert "请先在设置页填写班级名称" in errors
    assert "请先在设置页填写教师姓名" in errors


def test_format_setting_summary():
    summary = format_setting_summary(
        {"grade": "大班", "class_name": "彩虹班", "teacher_name": "李老师"}
    )

    assert summary == "当前设置：大班 彩虹班 / 李老师"
    assert "未配置" in format_setting_summary({})
