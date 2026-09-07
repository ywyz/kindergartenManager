# Query an existing graph

Use `graphify-out/graph.json` at the requested project root, or an explicit `--graph` path. If missing or stale for the question, use current source and disclose the limitation; do not rebuild automatically.

```bash
graphify query "relevant symbol or concept" --budget 1500
graphify query "relevant symbol or concept" --dfs --budget 1500
```

The matcher uses graph labels, not semantic synonym expansion. Start with known labels; if wording/language yields no useful hit, inspect relevant node labels and retry with their vocabulary. There is no need to export a vocabulary file or scan all labels before every query.

Use `--context` to narrow edge types when useful. Increase the budget or inspect exact nodes only when truncation hides evidence needed for the question. Do not enumerate unrelated neighbors merely for completeness.

For path/explanation requests, use the available graph tool or read-only traversal of the existing graph; verify supported CLI commands before use. Preserve edge direction and confidence labels. Cite source locations and verify current code/spec content for material claims. No match is not proof of absence.

If CLI lookup is unavailable, a bounded read-only traversal of the JSON is sufficient; do not install dependencies just to perform a lookup. Stop once the task is answered.

Saving a result with `save-result`, generating reflections, or refreshing the graph are maintenance actions, not automatic parts of answering. Run them only when requested or required by an applicable maintenance workflow. The CLI may write its own query cache; do not infer that this authorizes persistent Q&A or graph mutation.
