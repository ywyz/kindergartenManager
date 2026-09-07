# Hooks and agent integration

Use only for a requested installation, removal or review of Graphify integration. Check the installed CLI and existing hooks/configuration before changes; preserve unrelated hook logic.

```bash
graphify hook status
graphify hook install
graphify hook uninstall
```

Hooks/watchers can update code graphs after changes; they do not prove semantic document coverage. Do not install them during ordinary queries or edits. For Codex integration use the command supported by the installed CLI (`graphify codex install`), then inspect the resulting AGENTS.md diff. Preserve the project's scoped graph routing rather than introducing an always-on graph/rebuild requirement.

After an authorized change, verify the intended hook/configuration and summarize when it runs and what it writes. Do not start an unrequested background process or replace user hooks.
