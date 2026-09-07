---
name: graphify
description: Build or maintain Graphify graphs, or explore relationships across documents and code in an existing graph.
---

# Graphify

Use Graphify for cross-document/concept relationships or requested graph operations. Ordinary edits, known-file reads and symbol/caller lookups do not require it. An existing `graphify-out/` directory alone is not a trigger.

## Choose the relevant workflow

- Existing graph query, path or explanation: [references/query.md](references/query.md).
- Build, semantic extraction, update, labeling or clustering: [references/update.md](references/update.md).
- Clone/merge repositories: [references/github-and-merge.md](references/github-and-merge.md).
- URL ingestion or watcher: [references/add-watch.md](references/add-watch.md).
- Export or benchmark: [references/exports.md](references/exports.md).
- Install/remove hooks or agent integration: [references/hooks.md](references/hooks.md).
- Media transcription: [references/transcribe.md](references/transcribe.md), only for media in the requested corpus.
- Agent semantic fallback: [references/extraction-spec.md](references/extraction-spec.md), only when that fallback is needed.

Read only the relevant reference. Prefer installed CLI commands over reconstructing the pipeline in Python; consult `graphify --help` for version-specific options. Help requests need no indexing or setup. Do not install/upgrade tools or change integrations just to answer a graph question.

## Boundaries

Keep query work separate from maintenance. Do not automatically rebuild, export HTML, benchmark, save Q&A, reflect on history, or start watchers after a lookup. Follow the user's requested scope and stop when the question is answered.

Graph results are navigation evidence. Verify material code/spec claims against current sources; disclose stale/missing coverage, truncation and inferred edges. Never invent relationships or present incomplete extraction as complete.

Maintenance must preserve source attribution, direction, the existing graph on failure, and integrity diagnostics. Do not hand-edit generated graph files. Use configured credentials safely; never print keys, authenticated URLs or raw provider errors. Follow any repository-specific backend policy and authorization for external data transmission.

Report the requested result and material limits concisely. Report measured costs when available for extraction; do not invent token counts or append promotional text and unrelated follow-up tasks.
