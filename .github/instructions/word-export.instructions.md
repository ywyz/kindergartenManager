---
description: "Use when modifying Word export logic, changing docx template filling, fixing font colors, or adding export functions in word_export.py."
applyTo: "app/services/word_export.py"
---
# Word Export Conventions

## Template structure
The Word template (`templates/teacherplan.docx`) contains a single table. Rows are accessed by fixed index (`t.rows[N].cells[1]`). See `export_daily_plan_word()` for the row-to-field mapping (Row 0 = week, Row 1 = date, Row 2-3 = morning activity, etc.).

## Filling helpers
| Helper | Use case |
|---|---|
| `_fill_labeled_para(para, content, is_red)` | Single-label paragraph (finds colon, fills after it) |
| `_fill_multiline_cell(cell, fields)` | Multi-label cell (matches label keywords across paragraphs) |
| `_fill_process_cell(cell, text, use_ai_color)` | Activity process only — section-based AI tag coloring |
| `_set_cell_text(cell, text)` | Simple full-cell replacement |

## Red text coloring
- AI-modified fields are tracked in `plan.ai_modified_parts["fields"]`.
- `_fill_process_cell` colors entire sections red when the section header contains `【AI修改】` or `【AI新增】` tags.
- **Known limitation**: python-docx run-level coloring may not render correctly in all Word versions. The logic is correct at the XML level but visual results can be inconsistent. Do not attempt to fix this with paragraph-level or cell-level formatting — it makes things worse.

## File naming
- Single export: `{grade}{class}_{YYYY-MM-DD}_{第N周周X}.docx`
- Merged batch: `{author}备课笔记.docx`

## Merged export
`export_merged_plans(plans, author_name)` uses `copy.deepcopy` of each sub-document's table XML, joined by page breaks. Do not use `docxcompose` or similar libraries — the current approach avoids style conflicts.

## Adding new export functions
1. Generate content via `export_daily_plan_word(plan)` → bytes.
2. Write to `AppConfig.EXPORT_DIR` (create with `mkdir(parents=True, exist_ok=True)`).
3. Return a `Path` object — the caller handles `ui.download()`.
