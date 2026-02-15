"""
向后兼容模块：重新导出 kg_manager 的所有函数

此模块保留用于兼容旧代码，新代码应直接导入 kg_manager。

使用建议：
  from kg_manager import validate_plan_data, save_plan_data
  # 而非
  from minimal_fill import validate_plan_data, save_plan_data
"""

from pathlib import Path

# 重新导出所有 kg_manager 函数和常量
from kg_manager import (  # noqa: F401
    # Models
    FIELD_ORDER,
    SUBFIELDS,
    SAMPLE_PLAN_DATA,
    WORD_FONT_NAME,
    WORD_FONT_SIZE,
    WORD_INDENT_FIRST_LINE,
    # Database
    save_semester,
    load_latest_semester,
    init_plan_db,
    save_plan_data,
    load_plan_data,
    list_plan_dates,
    delete_plan_data,
    get_plan_data_info,
    # Word
    generate_plan_docx,
    fill_teacher_plan,
    fill_doc_by_labels,
    set_cell_text,
    append_by_labels,
    # Validation
    validate_plan_data,
    export_schema_json,
    calculate_week_number,
    weekday_cn,
    build_week_text,
    build_date_text,
    # AI
    split_collective_activity,
    parse_ai_json,
    set_custom_system_prompt,
)

# 保留以下函数用于向后兼容
from docx import Document
from datetime import date


def main():
    """
    测试示例（使用kg_manager核心库）
    
    此示例演示如何使用kg_manager库生成教案。
    """
    src = Path("examples/teacherplan.docx")
    dst = Path("examples/teacherplan_filled.docx")
    db_path = Path("examples/semester.db")
    schema_path = Path("examples/plan_schema.json")

    semester_start = date.fromisoformat("2026-02-23")
    semester_end = date.fromisoformat("2026-07-10")
    target_date = date.fromisoformat("2026-02-26")

    if not (semester_start <= target_date <= semester_end):
        raise ValueError("target_date is out of semester range")

    save_semester(db_path, semester_start, semester_end)

    week_no = calculate_week_number(semester_start, target_date)
    week_text = f"第（{week_no}）周"
    date_text = (
        f"周（{weekday_cn(target_date)}） "
        f"{target_date.month}月{target_date.day}日"
    )

    doc = Document(src)

    if not is_workday(target_date):
        print("Warning: target_date is not a workday in Chinese calendar.")

    plan_data = SAMPLE_PLAN_DATA
    errors = validate_plan_data(plan_data)
    if errors:
        raise ValueError("; ".join(errors))
    fill_teacher_plan(doc, plan_data, week_text, date_text)

    export_schema_json(schema_path)
    print(f"Saved schema: {schema_path}")

    doc.save(dst)
    print(f"Saved: {dst}")


if __name__ == "__main__":
    main()
