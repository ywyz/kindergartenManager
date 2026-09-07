# Media transcription

Use only when the requested graph corpus includes audio/video. Use the installed Graphify transcription API with explicit source paths; do not assume a detection or analysis sidecar already exists. Resolve the interpreter that owns Graphify only when invoking its Python API.

`graphify.transcribe.transcribe_all(paths, initial_prompt=...)` produces transcript paths. `GRAPHIFY_WHISPER_MODEL` selects the Whisper model; preserve a user-specified choice. Supply a short domain hint only when the task's context supports one. Reading graph hubs or making a separate model request for a hint is unnecessary.

Keep diagnostic stdout separate from serialized JSON. Verify which transcripts were actually created, report failures, and feed only successful transcripts into the document extraction workflow in `update.md`. A text transcript does not cover visual evidence in a video; inspect relevant frames separately when the question needs them. Do not label a partially transcribed corpus complete.
