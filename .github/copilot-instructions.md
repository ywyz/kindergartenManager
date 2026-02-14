# Kindergarten Lesson Plan Management System - AI Instructions

## Big Picture
- UI entry: `app.py` builds the NiceGUI web form and wires user actions to the core library in `kg_manager/`.
- Core library: `kg_manager/` holds reusable logic (`word.py`, `validate.py`, `db.py`, `ai.py`, `models.py`). `minimal_fill.py` is a compatibility layer.
- Data flow: schema → form → validation → Word export. Form schema is `examples/plan_schema.json` and is derived from `FIELD_ORDER`/`SUBFIELDS`.

## Word Template + Formatting (Critical)
- Template is `examples/teacherplan.docx` with a 19x2 table; row 0 is 周次, row 1 is 日期.
- All inserted text must use FangSong 12pt via `apply_run_style(run)`; do not bypass it.
- For multi-line content, create new paragraphs with `cell.add_paragraph()`, not `\n` in a single run.
- New content paragraphs must have a first-line indent of 24pt (2 Chinese chars). Labels keep no indent.

## Schema + Validation Rules
- `周次` and `日期` are auto-calculated, not shown in the form, and skipped by validation.
- Use `validate_plan_data()` before any save/export; grouped fields must include all subfields.
- Label matching uses normalization (strip whitespace and trailing colons) and is case-sensitive after normalization.

## Date + Calendar Logic
- Week number is from semester start (`calculate_week_number`), weekday label uses `weekday_cn`.
- Semester ranges are stored in SQLite at `examples/semester.db`.

## Developer Workflows
- Run UI: `python app.py` (NiceGUI on http://localhost:8080).
- Regenerate schema/test core: `python minimal_fill.py` (writes `examples/plan_schema.json`).
- Output Word files are written to `output/` (gitignored).

## Integration Points
- AI split for “集体活动” uses OpenAI-compatible API in `kg_manager/ai.py`; app config is saved in browser localStorage.
- DB layer supports SQLite by default, optional MySQL config in UI (see `kg_manager/db.py`).

## UI Patterns (NiceGUI)
- Date pickers use `ui.date()` inside `ui.menu()` and bind to `ui.input()` values.
- When changing schema or UI fields, keep `collect_plan_data()` and `apply_plan_data()` in sync.
