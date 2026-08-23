# Agent Foundation 任务冻结

权威范围见 [spec.md](spec.md)。下列任务有严格依赖关系；F005、F006 已固定 GREEN，F007 及以后未授权。

| ID | 任务 | 前置 | 当前状态 |
|---|---|---|---|
| F000 | 固定 `feat/agent-foundation` 与 R1 基线 SHA | R1 本地 GREEN | 完成 |
| F001 | 固定 spec、非目标、顺序和停止边界 | F000 | 完成 |
| F002 | 建立契约/关闭 registry 稳定 RED | F001 | 完成（原始 `ad13a6aa…`；安全同步 `5de2e49…`） |
| F003 | 最小实现 contracts 与关闭 registry | F002 + 明确 GREEN 授权 | GREEN |
| F004 | 建立 tenant+user 窄 READ service 投影 | F003 + 明确授权 | GREEN（`729f446…`，Review/CI 通过） |
| F005 | 实现规范 PlanPatch | F004 | GREEN（`53dd2e8…`，双轴 Review/CI 通过） |
| F006 | 实现 Provider port 与有界 Runtime | F005 | GREEN（RED `f0ab660…`；Review RED `6b083fa…`、`8831b3f…`、`79e005a…`、`51f5e5f…`；实现/重构 `99167ef…`；证据 `049b520…`；Review 0/0；本地 `73 + 551 passed`；CI `32644290676`） |
| F007 | 实现取消/超时/迟到丢弃 | F006 | 未授权 |
| F008 | 接入每日计划页只读/草案 UI | F007 | 未授权 |
| F009 | 零持久化全矩阵、Review 与人工验收 | F008 | 未授权 |

当前停在已闭合的 F006 门禁。F007-F009 的目录、类、migration、UI 控件或占位实现仍禁止。
