# Agent Foundation 任务冻结

权威范围见 [spec.md](spec.md)。下列任务有严格依赖关系；F005、F006 已固定 GREEN，F007-F009 已获连续授权，
但只能在前置切片的 Review、精确 SHA Quality 与 Issue 证据闭合后依序进入。

| ID | 任务 | 前置 | 当前状态 |
|---|---|---|---|
| F000 | 固定 `feat/agent-foundation` 与 R1 基线 SHA | R1 本地 GREEN | 完成 |
| F001 | 固定 spec、非目标、顺序和停止边界 | F000 | 完成 |
| F002 | 建立契约/关闭 registry 稳定 RED | F001 | 完成（原始 `ad13a6aa…`；安全同步 `5de2e49…`） |
| F003 | 最小实现 contracts 与关闭 registry | F002 + 明确 GREEN 授权 | GREEN |
| F004 | 建立 tenant+user 窄 READ service 投影 | F003 + 明确授权 | GREEN（`729f446…`，Review/CI 通过） |
| F005 | 实现规范 PlanPatch | F004 | GREEN（`53dd2e8…`，双轴 Review/CI 通过） |
| F006 | 实现 Provider port 与有界 Runtime | F005 | GREEN（RED `f0ab660…`；Review RED `6b083fa…`、`8831b3f…`、`79e005a…`、`51f5e5f…`；实现/重构 `99167ef…`；证据 `049b520…`；Review 0/0；本地 `73 + 551 passed`；CI `32644290676`） |
| F007 | 实现取消/超时/context current-state/迟到丢弃 | F006 | RED（`97 collected / 73 passed / 24 failed`） |
| F008 | OpenAI-compatible Provider adapter、六个关闭 Tool executor、组合装配与每日计划 Agent UI | F007 固定 GREEN + Review/CI/Issue | 已授权，等待 F007 |
| F009 | 零持久化全矩阵、Linux 浏览器 mock 与安全配置真实模型验收 | F008 固定 GREEN + Review/CI/Issue | 已授权，等待 F008 |

当前只激活 F007。F008/F009 不得提前实现；全程禁止 migration、WRITE、长期记忆、产品多 Agent、合并 main、
关闭 Issue 或发布。
