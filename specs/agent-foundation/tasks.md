# Agent Foundation 任务冻结

权威范围见 [spec.md](spec.md)。下列任务有严格依赖关系；当前仅 F003 已进入 GREEN，F004 及以后未授权。

| ID | 任务 | 前置 | 当前状态 |
|---|---|---|---|
| F000 | 固定 `feat/agent-foundation` 与 R1 基线 SHA | R1 本地 GREEN | 完成 |
| F001 | 固定 spec、非目标、顺序和停止边界 | F000 | 完成 |
| F002 | 建立契约/关闭 registry 稳定 RED | F001 | 完成（原始 `ad13a6aa…`；安全同步 `5de2e49…`） |
| F003 | 最小实现 contracts 与关闭 registry | F002 + 明确 GREEN 授权 | GREEN |
| F004 | 建立 tenant+user 窄 READ service 投影 | F003 | 未授权 |
| F005 | 实现规范 PlanPatch | F004 | 未授权 |
| F006 | 实现 Provider port 与有界 Runtime | F005 | 未授权 |
| F007 | 实现取消/超时/迟到丢弃 | F006 | 未授权 |
| F008 | 接入每日计划页只读/草案 UI | F007 | 未授权 |
| F009 | 零持久化全矩阵、Review 与人工验收 | F008 | 未授权 |

当前停在 F003。禁止在未获授权前预建 F004-F009 的目录、类、migration、UI 控件或占位实现。
