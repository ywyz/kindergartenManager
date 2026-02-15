# Kindergarten Lesson Plan Management System - AI Instructions

## Big Picture
- **Architecture**: 3-layer system where `app.py` (NiceGUI UI) → `kg_manager/` (core library) → data layer (SQLite/MySQL)
- **Core library**: `kg_manager/` exports 27+ reusable functions from 5 modules (`word.py`, `validate.py`, `db.py`, `ai.py`, `models.py`)
- **Compatibility layer**: `minimal_fill.py` redirects to `kg_manager` for backward compatibility
- **Data flow**: schema (`FIELD_ORDER`/`SUBFIELDS` in `models.py`) → JSON schema (`plan_schema.json`) → form → validation → DB/Word export

## Word Template + Formatting (Critical)
- Template: `examples/teacherplan.docx` has a 19-row × 2-column table (row 0 = 周次, row 1 = 日期)
- **MUST use** `apply_run_style(run)` for ALL text inserts — sets FangSong 12pt; do NOT bypass
- **Multi-line content**: Use `cell.add_paragraph()` for each line, NOT `\n` in a single run
- **Indentation rules**:
  - Content paragraphs: `paragraph_format.first_line_indent = Pt(24)` (2 Chinese chars)
  - Labels (field names): No indent
- **Example**:
  ```python
  p = cell.add_paragraph()
  p.paragraph_format.first_line_indent = Pt(WORD_INDENT_FIRST_LINE)
  run = p.add_run("content text")
  apply_run_style(run)
  ```

## Schema + Validation Rules
- `周次` and `日期` are auto-calculated; skip them in form UI and validation
- **Always call** `validate_plan_data(plan_data)` before save/export — returns list of error strings
- Grouped fields (e.g., "集体活动") must contain all subfields defined in `SUBFIELDS`
- Label matching: normalize by stripping whitespace/trailing colons, then case-sensitive match
- **Example**:
  ```python
  errors = kg.validate_plan_data(plan_data)
  if errors:
      ui.notify("\n".join(errors), type="negative")
      return
  ```

## Date + Calendar Logic
- Week number: `calculate_week_number(semester_start_date, target_date)` counts from semester start
- Chinese weekday: `weekday_cn(date_obj)` returns "一", "二", ..., "日"
- Semester data stored in `examples/semester.db` (load with `load_latest_semester()`)

## Developer Workflows
- **Run UI**: `python app.py` → http://localhost:8080
- **Regenerate schema**: `python minimal_fill.py` → writes `examples/plan_schema.json`
- **Test core library**: `python examples_usage.py` → runs 4 example scenarios
- **Install as package**: `pip install -e .` → use `import kg_manager as kg` anywhere
- **Output location**: Word files written to `output/` (gitignored)

## NiceGUI Patterns (UI Framework)
### Date Pickers
Pattern: `ui.date()` inside `ui.menu()`, bind to `ui.input()` via `bind_value()`:
```python
with ui.input("Date Label") as date_input:
    with date_input.add_slot("append"):
        ui.icon("event").on("click", lambda: date_menu.open())
    with ui.menu() as date_menu:
        ui.date(value="2026-02-26").bind_value(date_input)
```

### Async JavaScript Calls
**Critical**: `ui.run_javascript()` returns a coroutine; MUST await it:
```python
async def get_storage():
    value = await ui.run_javascript("localStorage.getItem('key')")
    return value
```

### Deferred Initialization with Timer
Use `ui.timer(delay, callback, once=True)` to run async setup after page loads:
```python
async def load_config():
    config = await ConfigManager.get_config_from_storage()
    input_field.value = config.get("key", "")

ui.timer(0.1, load_config, once=True)  # Runs once after 100ms
```

### Form Data Collection
Keep `collect_plan_data()` and `apply_plan_data()` in sync when schema changes:
- `collect_plan_data()`: UI fields → Python dict
- `apply_plan_data(dict)`: Python dict → UI fields

## Configuration Management (ConfigManager Pattern)
- **Storage**: Browser `localStorage` for persistence across sessions
- **Keys**: Namespaced with `kg_manager_` prefix (see `ConfigManager.STORAGE_PREFIX`)
- **Save**: `ConfigManager.save_to_storage(key, value)` — synchronous, no await needed
- **Load**: `ConfigManager.get_config_from_storage()` — async, returns dict with all configs
- **Auto-restore**: Use `ui.timer(0.1, load_func, once=True)` in `build_config_panel()` to restore on page load
- **Supported configs**: AI (api_key, model, base_url), DB (type, MySQL connection params)

## Integration Points
### AI Integration
- **Function**: `split_collective_activity(draft_text, api_key, base_url, model, system_prompt)` in `kg_manager/ai.py`
- **Parameters**: Accepts explicit parameters (api_key, base_url, model) to avoid global state pollution
- **Backward compatibility**: Falls back to `os.environ` if parameters not provided (for migration)
- **UI flow**: User pastes draft → clicks "AI 拆分" → passes stored config as params → calls async function → parses JSON → fills 6 subfields
- **Security**: Thread-safe, no env var pollution, prevents cross-user config leakage in concurrent scenarios
- **Customization**: Pass `system_prompt` parameter to override default AI behavior

### Database Layer
- **Default**: SQLite at `examples/plan.db` and `examples/semester.db`
- **MySQL**: Optional, configured via UI; connection params stored in localStorage
- **Key functions**:
  - `save_plan_data(db_path, date_str, plan_dict)` — upsert plan
  - `load_plan_data(db_path, date_str)` → plan dict or None
  - `list_plan_dates(db_path)` → list of ISO date strings

## Error Handling Conventions
- **Validation errors**: Return list of strings, display with `ui.notify("\n".join(errors), type="negative")`
- **File not found**: Check `Path.exists()` before operations, notify user with helpful message
- **Date parsing**: Wrap `date.fromisoformat()` in try/except, catch `ValueError`
- **Database**: Use `try/except` around all DB calls; rollback and notify on failure
- **AI failures**: Catch exceptions, show "AI 处理失败：{error}" message

## Critical "Don'ts"
- ❌ Don't use `\n` for multi-line Word content — use `add_paragraph()` per line
- ❌ Don't skip `apply_run_style(run)` when adding text to Word cells
- ❌ Don't forget to `await` `ui.run_javascript()` calls (they're coroutines)
- ❌ Don't validate `周次` or `日期` fields (they're auto-calculated)
- ❌ Don't modify `kg_manager/models.py` constants without updating schema generation
- ❌ Don't call `ui.run_javascript("localStorage.setItem()")` directly — use `ConfigManager.save_to_storage()`

## File Structure Reference
```
kg_manager/          # Core library (import with `import kg_manager as kg`)
├─ models.py         # FIELD_ORDER, SUBFIELDS, constants (no dependencies)
├─ db.py             # SQLite operations (8 functions)
├─ word.py           # Word generation (5 functions, depends on models)
├─ validate.py       # Validation + utils (6 functions, depends on models)
├─ ai.py             # OpenAI integration (3 functions)
└─ __init__.py       # Public API (exports 27+ symbols)
app.py               # NiceGUI UI (uses kg_manager)
minimal_fill.py      # Legacy compatibility layer (redirects to kg_manager)
examples/
├─ teacherplan.docx  # Word template (19x2 table)
├─ plan_schema.json  # Auto-generated from FIELD_ORDER/SUBFIELDS
├─ semester.db       # Semester date ranges
└─ plan.db           # Saved lesson plans
```

## Quick Reference: Common Tasks
**Add a new field**: Edit `FIELD_ORDER` in `models.py` → run `minimal_fill.py` → update `build_form()` in `app.py`  
**Change Word font**: Edit `WORD_FONT_NAME`/`WORD_FONT_SIZE` in `models.py`  
**Add DB support**: Extend `db.py`, maintain same function signatures  
**Customize AI prompt**: Call `kg.set_custom_system_prompt("...")` before `split_collective_activity()`  
**Batch export**: Use `export_range_plans(start_date, days)` — loads from DB, generates multiple Word files
