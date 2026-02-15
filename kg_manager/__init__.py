"""
幼儿园教案管理系统核心库

该模块提供教案管理的核心功能，包括：
- 教案数据验证
- Word文档生成
- 数据库存取
- AI内容拆分

使用示例：
    from kg_manager import (
        validate_plan_data,
        generate_plan_docx,
        save_plan_data,
        load_plan_data,
        split_collective_activity,
    )
    
    # 验证教案数据
    errors = validate_plan_data(plan_data)
    
    # 生成Word文档
    generate_plan_docx(
        template_path="template.docx",
        plan_data=plan_data,
        week_text="第（1）周",
        date_text="周（一） 2月26日",
        output_path="output.docx"
    )
    
    # 保存到数据库
    save_plan_data("plan.db", "2026-02-26", plan_data)
    
    # 从数据库加载
    data = load_plan_data("plan.db", "2026-02-26")
    
    # AI拆分
    result = split_collective_activity("完整原稿文本")
"""

# Models & Constants
from .models import (
    FIELD_ORDER,
    SUBFIELDS,
    SAMPLE_PLAN_DATA,
    WORD_FONT_NAME,
    WORD_FONT_SIZE,
    WORD_INDENT_FIRST_LINE,
)

# Database
from .db import (
    save_semester,
    load_latest_semester,
    init_plan_db,
    save_plan_data,
    load_plan_data,
    list_plan_dates,
    delete_plan_data,
    get_plan_data_info,
)

# Word Operations
from .word import (
    generate_plan_docx,
    fill_teacher_plan,
    fill_doc_by_labels,
    set_cell_text,
    append_by_labels,
)

# Validation & Utils
from .validate import (
    validate_plan_data,
    export_schema_json,
    calculate_week_number,
    weekday_cn,
    build_week_text,
    build_date_text,
)

# AI
from .ai import (
    split_collective_activity,
    parse_ai_json,
    set_custom_system_prompt,
    AI_SYSTEM_PROMPT,
)

__version__ = "0.1.0"

__all__ = [
    # Models
    "FIELD_ORDER",
    "SUBFIELDS",
    "SAMPLE_PLAN_DATA",
    "WORD_FONT_NAME",
    "WORD_FONT_SIZE",
    "WORD_INDENT_FIRST_LINE",
    # Database
    "save_semester",
    "load_latest_semester",
    "init_plan_db",
    "save_plan_data",
    "load_plan_data",
    "list_plan_dates",
    "delete_plan_data",
    "get_plan_data_info",
    # Word
    "generate_plan_docx",
    "fill_teacher_plan",
    "fill_doc_by_labels",
    "set_cell_text",
    "append_by_labels",
    # Validation
    "validate_plan_data",
    "export_schema_json",
    "calculate_week_number",
    "weekday_cn",
    "build_week_text",
    "build_date_text",
    # AI
    "split_collective_activity",
    "parse_ai_json",
    "set_custom_system_prompt",
    "AI_SYSTEM_PROMPT",
]
