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
| F009 | 零持久化全矩阵、Linux 浏览器 mock 与安全配置真实模型验收 | F008 固定 GREEN + Review/CI/Issue | 已授权；公共验收 seam 冻结，下一门禁为稳定 RED |

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

F009 内部依赖顺序冻结为：

1. 在 `test_f009_zero_persistence_matrix_red.py` 固定统一 `EffectSnapshot` 和所有终态矩阵：初始化/seed 后动态
   反射实际数据库全部表（不限于 `Base.metadata`），并覆盖
   受保护配置/exports（排除 SQLite/WAL/journal 与 pytest cache 等运行时物理文件）、调用方 UI 正文、独立 audit
   logger 捕获与 seed 后 DML/DDL attempts；覆盖文本、READ、两个 DRAFT、配置缺失/解密失败、Context/plan/
   Provider/Tool 失败、装配期/Provider/Tool/host 取消、Provider/Tool/总 timeout、TTL/current-context/scope/
   fingerprint stale、未知/WRITE、prompt injection、跨 tenant/user、busy、same-controller reentry、mutation
   发布窗口、discard、disconnect/reconnect、close/restart，且无 Agent schema 或可恢复记忆。
2. 在 `tests/test_config_secrets.py` 固定 POSIX `.kindergarten_secrets` 从创建时即为 `0600`；已有普通文件在
   首次读取前纠权（包括环境变量覆盖 Key），内容摘要/显式配置/复用语义不变；拒绝 symlink/非普通文件，
   纠权或安全写入失败须 fail-closed。只有这两组测试 collection clean、旧测试保持 GREEN、连续两次失败
   node ID 完全相同后，才提交并推送 F009 RED、回写 Issue。
3. RED 后的最小 GREEN 只允许 coordinator 公开可选 `RuntimeLimits` 透传和 secrets 文件最小权限创建/纠权；
   默认生产时限不变，不增加表、migration、Tool、WRITE、记忆或产品多 Agent。
4. 自动矩阵 GREEN 后执行双轴 Review；每个 finding 先建立 Review RED 再修正。随后固定 `tested_code_sha`，不再改
   产品代码，再执行 Linux 浏览器 mock：临时 SQLite、虚构加密 Key、仓库内仅测试辅助 mock server；迁移、
   seed、Key 保存与 Settings 权限收敛完成后、首次 Agent operation 前取得 baseline；可见验证
   文本/DRAFT/丢弃、cancel、A→B→A、断开重连、无 Agent WRITE 控件及 DB/exports/Git/UI 正文零变化。
5. 同一 `tested_code_sha` 的隔离临时 worktree/SQLite 中 seed 合成计划，再由用户在临时应用 `/settings` 正常
   保存真实 active `text` 配置；脚本和浏览器自动化不得读取、复制或键入 Key/endpoint/密文。配置与权限收敛
   后、首次 Agent operation 前取 baseline，只通过 controller→coordinator→repository 解密链执行；禁止
   环境变量临时注入真实 Key、直接构造 Provider、`/models`
   探测、切换凭据或重试。缺配置/权限不安全时 `network_requests=0` 且 F009 保持未完成。
6. 两份脱敏证据与最终状态文档完成后，按 repo skill 更新 codebase-memory 与 Graphify，验证 changed-source
   coverage、标签、结构诊断和无异常图缩小；图谱是辅助证据，不替代验收。然后把证据分别写入/保留在
   `specs/agent-foundation/evidence/f009-linux-browser-mock.md` 与
   `f009-real-model.md`，绑定同一 `tested_code_sha`；真实模型必须 `PASS`。提交证据形成独立
   `evidence_closure_sha`（同一 commit 包含最终图谱更新），完成最终 Standards 0 / Spec 0、Foundation/全量/
   静态门禁后推送 closure SHA，等待
   Quality `headSha` 精确匹配且 success，核对远端分支并回写 Issue #48。

当前只允许提交本次 F009 文档冻结并建立稳定 RED；GREEN、人工验收与证据文件必须按上述顺序。全程禁止
migration、WRITE、长期记忆、产品多 Agent、合并 main、关闭 Issue 或发布。
