---
description: "Add a new field to the Word export pipeline: data model → word_export.py → page UI. Use when the Word template adds a row or a new piece of data needs to appear in the exported docx."
agent: "agent"
argument-hint: "field name, which section it belongs to, and the template row number"
---
# Add Word Export Field

Add a new field to the Word export pipeline. This requires coordinated changes across three files.

## Input
The user will provide:
- **Field name** (e.g. `activity_summary`)
- **Section** it belongs to (e.g. morning_activity, group_activity, indoor_area, outdoor_game, or a new section)
- **Template row index** in the Word table (e.g. Row 19)

## Steps

### 1. Data model — [app/models/daily_plan.py](app/models/daily_plan.py)
- Add the field to the appropriate `@dataclass` (`MorningActivity`, `MorningTalk`, `GroupActivity`, `AreaActivity`, or `DailyPlan`).
- If the field belongs to a JSON-serialized nested object, it is automatically included via `dataclasses.asdict()` — no extra serialization code needed.

### 2. Word export — [app/services/word_export.py](app/services/word_export.py)
- In `export_daily_plan_word()`, add a new `# Row N` block at the correct position.
- Choose the right helper based on cell structure:
  - Single label paragraph → `_fill_labeled_para(para, content, is_red)`
  - Multiple labels in one cell → `_fill_multiline_cell(cell, fields_list)`
  - Activity process with AI tags → `_fill_process_cell(cell, text, use_ai_color)`
  - Plain text replacement → `_set_cell_text(cell, text)`
- Wire `is_red()` with the matching key from `plan.ai_modified_parts["fields"]` if AI can modify this field.

### 3. Page UI — [app/pages/daily_plan.py](app/pages/daily_plan.py)
- Add the corresponding `ui.input()` or `ui.textarea()` in the appropriate card section.
- Wire it into the `do_save()` handler so the value is stored in the `DailyPlan` object.
- If AI can generate this field, also wire it into `do_generate()`.

### 4. Validate
```bash
python3 -m py_compile app/models/daily_plan.py app/services/word_export.py app/pages/daily_plan.py
```

Follow conventions in [.github/instructions/word-export.instructions.md](.github/instructions/word-export.instructions.md).
