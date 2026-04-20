---
description: "Use when creating or modifying NiceGUI page modules in app/pages/. Covers async patterns, UI layout, and io_bound requirements."
applyTo: "app/pages/**/*.py"
---
# NiceGUI Page Conventions

## Module structure
Export one public function `xxx_page()` that builds the UI. Register the route in `app/main.py` with `@ui.page` calling `create_layout()` then the page function.

## Async / IO rule
Every DB or network call inside a NiceGUI event handler **must** use:
```python
result = await run.io_bound(sync_function, arg1, arg2)
```
Calling synchronous IO directly freezes the event loop and produces "JavaScript did not respond" errors.

## DB access
```python
from app.db import db_cursor
with db_cursor() as cursor:
    cursor.execute(sql, args)
    rows = cursor.fetchall()
```

## AI calls
```python
from app.services.ai_service import get_ai_service
ai = get_ai_service()        # returns AIService | None
if not ai:
    # show error to user
    return
result = await run.io_bound(ai.some_method, ...)
```

## Status feedback pattern
Use a `ui.label("")` for operation status, update via `.set_text("⏳ ...")` / `.set_text("✅ ...")` / `.set_text("❌ ...")`.

## File downloads
```python
ui.download(str(file_path), filename=file_path.name)
```
