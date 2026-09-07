# Exports and benchmark

Generate only requested formats from the selected graph. Available CLI formats include `html`, `wiki`, `obsidian`, `svg`, `graphml`, `neo4j` and `falkordb`; inspect `graphify --help` for options. Example:

```bash
graphify export html --graph graphify-out/graph.json
```

Large graphs may need aggregated HTML or a node limit. Distinguish a local export file from a push to an external database. Remote writes need authorization for that destination and data; use supported protected credential configuration, never passwords in command arguments or chat. MERGE behavior does not by itself establish that a remote write is harmless.

Run `graphify benchmark` only when a benchmark is requested or directly needed for a measured comparison, not automatically because a corpus crosses a word threshold. Installing an MCP server or changing a client integration is a separate requested workflow.
