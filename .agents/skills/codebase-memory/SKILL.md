---
name: codebase-memory
description: Find indexed symbols, trace call paths, or assess structural change impact with Codebase Memory.
---

# Codebase Memory

Use the graph when structural relationships are the question. Read known files directly; use scoped text search for literals, configuration, instructions, or insufficient graph results. Do not repeat an answer already established by another graph.

## Query selection

Confirm the project/root and index generation on first use, or when freshness is uncertain; reuse that context while it remains valid.

- `search_graph`: discover symbols and exact qualified names; follow relevant `has_more` pages.
- `trace_path`: inbound for callers, outbound for callees; both only when the question needs both.
- `get_code_snippet`: inspect source behind a material claim.
- `query_graph`: complex relationships; inspect the schema only if needed to formulate a query.
- `get_architecture`: broad architecture questions, not routine edits.
- `detect_changes`: change-impact questions.

Use the callable tool schema rather than guessing arguments. `search_graph(relationship=...)` filters node degree; use `query_graph` for actual edge details.

## Evidence

Before relying on graph findings, batch `check_index_coverage` for the evidence paths and any scope supporting negative/exhaustive claims. Read current source for stale, partial, skipped, excluded or unknown coverage. A clean coverage report is a best-effort signal, not proof of completeness.

A quick positive lookup may be reported as provisional. Absence, dead-code and complete-impact claims need a defined scope, relevant pagination and source checks, including dynamic entry points. Stop when the evidence answers the task; do not expand to a repository-wide audit by default.

If delegating graph-derived work, pass relevant symbols, paths, freshness, limitations and unresolved questions already gathered. A child without graph access uses those sources and must not claim fresh graph verification. Delegation itself does not require extra graph queries.

Index/rebuild only when requested or necessary for an authorized graph maintenance task; a missing index does not block source-based work.
