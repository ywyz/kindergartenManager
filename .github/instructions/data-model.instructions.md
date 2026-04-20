---
description: "Use when modifying data model classes, adding fields, or accessing nested dataclass attributes in daily_plan.py. Prevents field naming errors."
applyTo: "app/models/daily_plan.py"
---
# Data Model Conventions

## Dataclass field names are the API contract
The field names on `MorningActivity`, `MorningTalk`, `GroupActivity`, `AreaActivity`, and `DailyPlan` are serialized to JSON via `dataclasses.asdict()` and stored in the DB. **Renaming a field breaks deserialization of existing records.** To rename safely, handle both old and new keys in `from_db_row()`.

## Field name quick reference
When accessing nested object attributes in pages or export code, use **only** these exact names:

| Class | Fields |
|---|---|
| `MorningActivity` | `group_activity_name`, `self_selected_name`, `key_guidance`, `activity_goal`, `guidance_points` |
| `MorningTalk` | `topic`, `questions` |
| `GroupActivity` | `theme`, `goal`, `preparation`, `key_point`, `difficulty`, `process`, `process_original` |
| `AreaActivity` | `game_area`, `key_guidance`, `activity_goal`, `guidance_points`, `support_strategy` |
| `DailyPlan` | `morning_activity`, `morning_talk`, `group_activity`, `indoor_area`, `outdoor_game`, `daily_reflection`, `ai_modified_parts`, ... |

Common mistake: `MorningActivity` has `group_activity_name`, NOT `activity_type` or `activity_name`.

## `AreaActivity` is shared
`indoor_area` and `outdoor_game` both use the same `AreaActivity` class. Do not create separate indoor/outdoor dataclasses.

## Adding a new field
1. Add to the dataclass with a default value (e.g. `new_field: str = ""`).
2. No changes needed in `to_db_dict()` or `from_db_row()` — `dataclasses.asdict()` and the `__dataclass_fields__` loop handle it automatically.
3. Old DB rows missing the new key will get the default value via `ma_data.get(k, "")`.

## JSON keys in AI prompts
AI service output JSON keys must match these dataclass field names exactly. If the AI returns different keys, map them in the AI service method, not in the model.
