# Kindergarten Lesson Plan Management System - AI Instructions

## System Architecture

**Two-Layer Design:**
- `minimal_fill.py`: Core logic (Word manipulation, validation, date calculations)
- `app.py`: NiceGUI web interface (form generation, user interaction)

**Data Flow:**
```
FIELD_ORDER/SUBFIELDS → export_schema_json() → examples/plan_schema.json
                                                    ↓
User Input (app.py) → collect_plan_data() → validate_plan_data() → fill_teacher_plan() → Word document
```

## Critical Word Formatting Rules

**All text MUST use FangSong font 12pt:**
```python
# Always use apply_run_style(run) for ANY text insertion
run.font.name = "FangSong"
run.font.size = Pt(12)
run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "仿宋")
```

**Multi-line content handling:**
- Use `cell.add_paragraph()` to create separate paragraphs (NOT `\n` in single run)
- New content paragraphs: `paragraph_format.first_line_indent = Pt(24)` (2 Chinese chars)
- Template labels: no indent, apply FangSong to existing runs

## Template Structure (examples/teacherplan.docx)

**19-row table (rows 0-18), 2 columns:**
- Row 0: 周次 (auto-calculated)
- Row 1: 日期 (auto-calculated)
- Rows 2-18: Various lesson plan fields

**Cell filling pattern:**
```python
# Simple text (周次, 日期, 一日活动反思)
set_cell_text(cell, text)

# Labeled content with multi-line support
append_by_labels(cell, {"标签名": "内容"})  # Splits on \n, creates paragraphs
```

## Field Schema System

**Two-level structure:**
1. `FIELD_ORDER`: List of `(field_name, required)` tuples (defines order & validation)
2. `SUBFIELDS`: Dict mapping parent fields to lists of child field names

**Critical pattern:** 周次 and 日期 are:
- NOT shown in web form (auto-calculated)
- Excluded from validation (`validate_plan_data` skips them)
- Calculated via `calculate_week_number()` and `weekday_cn()`

## Date & Calendar Logic

**Semester management:**
```python
# Chinese calendar integration (chinesecalendar library)
is_workday(date)  # Checks against Chinese holidays/working days

# Week calculation from semester start
calculate_week_number(semester_start, target_date)  # Returns 1-based week number
```

**Date storage:** `examples/semester.db` (SQLite) stores semester ranges

## Development Workflow

**Testing core logic:**
```bash
python minimal_fill.py  # Generates test document + schema JSON
```

**Running web UI:**
```bash
python app.py  # Starts NiceGUI on http://localhost:8080
```

**Output:** All generated Word files go to `output/` (gitignored)

## Code Conventions

**Label normalization:**
- Strip whitespace and trailing colons: `normalize_label("标签：")`
- Match template labels case-sensitively after normalization

**Field validation:**
- Required fields must exist and be non-empty
- Grouped fields must be dicts with all subfields present
- Use `validate_plan_data()` before Word generation

**Data structure for form:**
```python
plan_data = {
    "field_name": "value",  # Simple field
    "grouped_field": {      # Grouped field
        "subfield1": "value1",
        "subfield2": "value2"
    }
}
```

## Key Gotchas

1. **Never use `run.text +=` or string concatenation** for multiline content - always create new paragraphs
2. **Template content formatting:** When reconstructing cells in `append_by_labels()`, apply `apply_run_style()` to preserve FangSong
3. **Date pickers in NiceGUI:** Use `ui.date()` in `ui.menu()` pattern, bind to `ui.input()` value
4. **Schema regeneration:** Run `export_schema_json()` after modifying `FIELD_ORDER`/`SUBFIELDS`

## External Dependencies

- `python-docx`: Word manipulation (table cells, runs, paragraphs)
- `nicegui`: Web UI framework (reactive components)
- `chinesecalendar`: Mainland China holiday/workday detection
- `sqlite3`: Local semester data storage

## Future Extension Points

- MySQL cloud storage (pymysql installed, not yet implemented)
- AI content generation (openai library available)
- Batch export functionality
- Lesson plan history/search features
