# Build and maintain Graphify

Use this reference for an authorized build, extraction, update, labeling or clustering task. Ordinary document/code edits do not require graph maintenance. Scope the corpus to the task; preserve configured exclusions for secrets, runtime data and generated artifacts.

## Select a command

Use the installed CLI, checking its help if needed:

```bash
# Code-only structural extraction; no semantic provider calls.
graphify extract . --code-only --no-cluster
# Semantic extraction; uses the existing manifest/cache unless forced.
graphify extract . --backend openai
# Recluster an existing graph without rebuilding extraction.
graphify cluster-only . --backend openai --no-viz
# Name only missing communities.
graphify label . --backend openai --missing-only
```

`graphify update` is code-only in the current CLI. For changed governance/architecture documents use `extract` with a semantic backend; do not claim an AST refresh covers documents. Keep the original root and directedness. For separate subfolder graphs, use separate output directories before merging.

Prefer incremental work and existing semantic caches. Use `--mode deep` only for requested broader inferred relationships. Do not use `--force` merely to bypass a shrink guard; investigate whether the intended corpus/deletions explain the difference first. Avoid full-corpus extraction for a local lookup.

## Backend policy

Use an explicit repository policy when present. In KindergartenManager the fixed order for semantic extraction and LLM-backed labeling/clustering is:

1. Configured OpenAI-compatible backend (`--backend openai`).
2. On failure or invalid semantic output, configured DeepSeek (`--backend deepseek`) for the same scope.
3. Only if both fail, the installed `luna_worker` for the same bounded semantic task, using `references/extraction-spec.md` and supported cache/build mechanisms. Do not substitute another agent or skip DeepSeek.

Stop at the first semantically valid result. Do not loop on failing backends, inject product credentials, print endpoints/keys/raw provider errors, or replace the configured backend based on which unrelated environment variable is present. If all paths fail or the required fallback is unavailable, report semantic maintenance unavailable and use current sources for the application task. An unavailable graph does not require pausing unrelated work.

Agent fallback uses tools actually available in the current host, not a hard-coded `Task`/`close_agent` API. Give each writer non-overlapping output ownership, source paths and extraction schema. Do not require recursive fan-out or a fixed number of files per agent. Validate fallback output before supported ingestion; do not hand-edit `graph.json`.

## Integrity and completion

Before mutation, retain a recoverable snapshot of the existing graph artifacts. A zero exit status is insufficient: check parseability, changed-source and target-concept coverage, node/edge count changes, and integrity diagnostics (`graphify diagnose multigraph`, plus extraction diagnostics where applicable). Do not overwrite a useful graph with an empty or unexplained smaller result.

Preserve deterministic IDs, edge direction, source attribution and hyperedges. Changed-source replacement differs from deletion pruning. Failed semantic sources must remain pending, not stamped as completed. Report missing chunks and limitations; partial extraction is not completion.

Use the CLI's manifest/cache/report management rather than duplicating the pipeline with ad-hoc Python recipes. Raw extraction with `--no-cluster` does not prove that labels, reports or HTML were refreshed. `cluster-only` is self-contained; do not repeat cleanup/rebuild stages afterward. Generate only requested outputs; no automatic benchmark or follow-up exploration.

After a tool upgrade, verify `graphify --version`, align `.graphify_version`, reconcile local skill customizations with upstream, and validate affected skills. This is not an instruction to upgrade during ordinary use.
