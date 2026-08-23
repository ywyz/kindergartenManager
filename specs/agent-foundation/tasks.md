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
| F007 | 实现取消/超时/context current-state/迟到丢弃 | F006 | GREEN（RED `55b8702…`；Review RED `08ada78…`、`ddca78d…`；候选 `51443a3…`；证据 `2fb4e6f…`；Review 0/0；本地 `110 + 551 passed`；CI `32648599591`） |
| F008 | OpenAI-compatible Provider adapter、六个关闭 Tool executor、组合装配与每日计划 Agent UI | F007 固定 GREEN + Review/CI/Issue | GREEN（RED `b3cad08…`；Review RED `b3c45d2…`、`b0647a9…`；候选 `f1f5e63…`；Review 0/0；本地 `180 + 551 passed`；CI `32651221452`） |
| F009 | 零持久化全矩阵、Linux 浏览器 mock 与安全配置真实模型验收 | F008 固定 GREEN + Review/CI/Issue | 已授权；当前只固定文档与稳定 RED |

F008 内部依赖顺序冻结为：

1. `test_f008_provider_adapter_red.py` 固定 Chat Completions adapter、显式 canonical/wire 双射、固定关闭 system
   JSON、operation namespace UUID5/历史 ID 自洽、关闭净化、无 `store`/`parallel_tool_calls`、400 不降级重试。
2. `test_f008_tool_executor_red.py` 固定六路静态 executor、每 READ 独立短 session、DRAFT 零 session、
   actor/scope/permission/绑定关闭拒绝和零业务/UI 变化。
3. `test_f008_composition_ui_red.py` 固定应用级单 `DailyPlanAgentCoordinator`、短命凭据、
   `DailyPlanAgentController`/`AgentPanelSnapshot`、DatePanel selection generation + exact stamp，以及只展示
   运行/取消/失败/assistant/PlanPatch/丢弃且无正文回填/adopt/save/confirm。
4. 三个 RED 文件 collection clean 且连续两次 collected/passed/failed 完全一致、旧 Foundation 测试继续 GREEN
   后提交 RED；此 commit 前不得实施 F008 GREEN。
5. RED 后才依次执行最小 GREEN、双轴 Review、findings RED/修正、固定 SHA 本地验证、push、精确 Quality
   `headSha` 回读与 Issue #48 证据回写。只有这些门禁全闭合才把 F008 标为 GREEN 并进入 F009。

当前只激活 F009 文档/spec/tasks 与稳定 RED；验收实现必须等待 RED 固定。全程禁止 migration、WRITE、长期记忆、产品多 Agent、合并 main、
关闭 Issue 或发布。
