# URL ingestion and watch

Use only for requested URL ingestion or a watcher. Prefer the installed CLI:

```bash
graphify add <url>
graphify watch <path>
```

For ingestion, verify that the saved source is complete enough for the task; an oEmbed snippet is not a full article. Do not claim inaccessible content was read. Update the intended corpus according to `update.md`, preserving its root/output and semantic backend policy.

A watcher is a persistent process; start it only for the requested scope and explain how to stop it. Code updates do not prove that changed documents have been semantically extracted. Stop watchers created for a bounded task when finished unless the user requested continued operation.
