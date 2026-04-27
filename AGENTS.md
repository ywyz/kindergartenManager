
# Kindergarten Manager Agent Guide

## Scope
These instructions apply to the whole repository.

## First Read
- Product scope and current status: [PROJECT.md](PROJECT.md)
- Daily plan requirements: [docs/daily-plan.md](docs/daily-plan.md)
- Weekly plan requirements: [docs/week-plan.md](docs/week-plan.md)
- Prompt assets: [.github/prompts/](.github/prompts/)

## Environment And Run
- Python ≥ 3.12, package manager: **uv**
- Install deps: `uv sync`
- Run app: `uv run python -m app.main`
- No test suite exists yet; validate changes with `python3 -m py_compile <files...>`

## Architecture Map
- Entry, routing, nav layout: [app/main.py](app/main.py)
- DB connection + DDL bootstrap: [app/db.py](app/db.py)
- Data models and CRUD: [app/models/daily_plan.py](app/models/daily_plan.py)
- Pages (NiceGUI): [app/pages/](app/pages/) — each module exports a `xxx_page()` function called from main.py
- Services: [app/services/](app/services/) (AI / date / export / crypto / plan)
- Word template: [templates/teacherplan.docx](templates/teacherplan.docx)
- Config from `.env`: [app/config.py](app/config.py)

## Key Patterns

### Page structure
Each page module exports one function (e.g. `daily_plan_page()`) that builds UI using NiceGUI components. Routes are registered in `main.py` via `@ui.page` decorators that call `create_layout()` + the page function.

### Async and IO
All blocking DB/IO calls in page handlers **must** use `await run.io_bound(fn, ...)`. Direct synchronous calls inside NiceGUI async handlers will freeze the UI.

### DB access
Use the `db_cursor()` context manager from `app.db`. It auto-commits on success and rolls back on exception.

### AI service
`get_ai_service()` returns a configured `AIService` instance or `None`. JSON generation goes through `_call_json()` with built-in retry; plain text uses `_chat()`. AI generation parameters (temperature, top_p, frequency_penalty) are stored in `app_settings` table.

## Project Conventions
- Keep business details in [docs/daily-plan.md](docs/daily-plan.md) and [docs/week-plan.md](docs/week-plan.md); do not introduce parallel requirement docs.
- Preserve current data model fields and JSON keys unless explicitly migrating.
- Keep changes small and local; avoid unrelated refactors.

## Data And Persistence Rules
- `daily_plans` is keyed by `(plan_date, grade, class_name)` with a unique index; one logical plan per class/day.
- Save flow uses upsert behavior; always return a valid plan id after save.
- If `APP_SECRET_KEY` changes, encrypted AI keys must be re-saved in settings.

## AI And Prompt Rules
- AI JSON generation is centralized in [app/services/ai_service.py](app/services/ai_service.py).
- 6 prompt categories: `lesson_split`, `process_modify`, `morning_activity`, `morning_talk`, `indoor_area`, `outdoor_game`.
- For process modification output, keep plain text semantics and preserve non-edited sections.

## Export Rules
- Word export logic is centralized in [app/services/word_export.py](app/services/word_export.py).
- Filename convention: `{grade}{class}_{date}_{weekN weekday}.docx`.
- Merged batch export: `export_merged_plans()` produces a single `.docx` with page breaks.

## Validation Before Finish
- Syntax check: `python3 -m py_compile <files...>`
- If behavior changes in save/export/history flows, validate from UI:
  1. save daily plan → 2. open history detail → 3. export word

## Out Of Scope By Default
- Authentication system
- Weekly/monthly planning modules
- Non-teaching subsystems from the parent platform
