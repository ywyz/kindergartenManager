---
description: "Use when modifying AI generation logic, adding new AI methods, or changing prompt handling in ai_service.py."
applyTo: "app/services/ai_service.py"
---
# AI Service Conventions

## Adding a new generation method
1. Use `_call_json()` for structured JSON output, `_chat()` for plain text.
2. Always pass `**self._params` (temperature, top_p, frequency_penalty) from cached settings.
3. Load the active prompt from DB via `_get_prompt(category)` — the 6 categories are: `lesson_split`, `process_modify`, `morning_activity`, `morning_talk`, `indoor_area`, `outdoor_game`.

## JSON safety
`_call_json()` enables `response_format={"type":"json_object"}` with automatic fallback, appends `_JSON_FORMAT_RULES`, and retries parse failures up to 2 times with self-correction.

## Plain text safety
`_strip_to_process_text()` extracts plain text even if the model returns JSON — always use it as a fallback for `process_modify` output.

## AI parameters
User-configurable via `app_settings` table (keys: `ai_temperature`, `ai_top_p`, `ai_frequency_penalty`). Cached in `self._params` at `__init__` time via `_get_ai_params()`.
