# Kindergarten Manager Agent Guide

## Scope
These instructions apply to the whole repository.

## First Read
- Source of truth for product scope and current status: [PROJECT.md](PROJECT.md)
- Existing prompt assets: [.github/prompts/](.github/prompts/)

## Environment And Run
- Python environment: use uv
- Install deps: `uv sync`
- Run app: `uv run python -m app.main`
- Alternate run: `uv run python app/main.py`

## Architecture Map
- Entry and routing: [app/main.py](app/main.py)
- DB and schema init: [app/db.py](app/db.py)
- Domain model and CRUD: [app/models/daily_plan.py](app/models/daily_plan.py)
- Pages (NiceGUI): [app/pages/](app/pages/)
- Services (AI/date/export/crypto): [app/services/](app/services/)
- Word template: [templates/teacherplan.docx](templates/teacherplan.docx)

## Project Conventions
- Keep business details aligned with [PROJECT.md](PROJECT.md); do not introduce parallel requirement docs.
- For NiceGUI page handlers, run blocking DB/IO work with `run.io_bound`.
- Preserve current data model fields and JSON keys unless explicitly migrating.
- Keep changes small and local; avoid unrelated refactors.

## Data And Persistence Rules
- `daily_plans` is keyed by `(plan_date, grade, class_name)`; treat it as one logical plan per class/day.
- Save flow uses upsert behavior in model layer; always return a valid plan id after save.
- If `APP_SECRET_KEY` changes, encrypted AI keys must be re-saved in settings.

## AI And Prompt Rules
- AI JSON generation is centralized in [app/services/ai_service.py](app/services/ai_service.py).
- Prompt categories should stay consistent with prompt management page and DB records.
- For process modification output, keep plain text semantics and preserve non-edited sections.

## Export Rules
- Word export logic is centralized in [app/services/word_export.py](app/services/word_export.py).
- For activity process coloring, only AI-tagged changed/new segments should be highlighted.

## Validation Before Finish
- Syntax check changed Python files with `python3 -m py_compile <files...>`.
- If behavior changes in save/export/history flows, validate from UI path:
  - save daily plan
  - open history detail
  - export word

## Out Of Scope By Default
- Authentication system
- Weekly/monthly planning modules
- Non-teaching subsystems from the parent platform
