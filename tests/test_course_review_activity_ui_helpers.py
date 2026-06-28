from app.ui.pages.course_review_activity import (
    build_course_review_activity_filename,
    format_setting_summary,
    validate_course_review_form,
    validate_generation_context,
)


def test_build_course_review_activity_filename():
    filename = build_course_review_activity_filename(
        tenant_id=1,
        user_id=2,
        record_id=33,
        grade="小班",
        class_name="阳光班",
    )

    assert filename == "1_2_小班_阳光班_33_课程审议.docx"


def test_build_course_review_activity_filename_sanitizes_values():
    filename = build_course_review_activity_filename(
        tenant_id=1,
        user_id=2,
        record_id=None,
        grade="小/班",
        class_name="阳 光班",
    )

    assert "/" not in filename
    assert "小班" in filename
    assert "阳光班" in filename
    assert "新记录" in filename


def test_validate_generation_context_success():
    errors = validate_generation_context(
        {"grade": "小班", "class_name": "阳光班", "teacher_name": "张老师"}
    )
    assert errors == []


def test_validate_generation_context_missing_fields():
    errors = validate_generation_context(
        {"grade": "", "class_name": "", "teacher_name": ""}
    )

    assert "请先在设置页选择年级" in errors
    assert "请先在设置页填写班级名称" in errors
    assert "请先在设置页填写教师姓名" in errors


def test_validate_course_review_form_base_fields_only():
    errors = validate_course_review_form(
        {
            "activity_name": "圆形灯笼",
            "child_count": "30",
            "activity_time": "2026.06.28",
            "lesson_plan_original": "完整教案",
        },
        require_generated=False,
    )

    assert errors == []


def test_validate_course_review_form_requires_generated_fields():
    errors = validate_course_review_form(
        {
            "activity_name": "圆形灯笼",
            "child_count": "30",
            "activity_time": "2026.06.28",
            "lesson_plan_original": "完整教案",
        }
    )

    assert "请填写活动目标" in errors
    assert "请填写活动过程调整内容" in errors
    assert "请填写二次修改稿" in errors


def test_format_setting_summary():
    summary = format_setting_summary(
        {"grade": "大班", "class_name": "彩虹班", "teacher_name": "李老师"}
    )

    assert summary == "当前设置：大班 彩虹班 / 李老师"
    assert "未配置" in format_setting_summary({})
