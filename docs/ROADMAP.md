# KindergartenManager 产品与工程路线图

> 当前快照：2026-08-23；Agent 安全同步 RED 基线 `5de2e49bee19749f611b50747a31be9464b92d7b`；最近远端产品主线 `main@cfeadefd7dfa056c1b3757876658493110d8cf84`。

## 1. 状态语义

| 状态 | 含义 |
|---|---|
| `规划` | 方向存在，但范围和验收尚未冻结 |
| `设计中` | 正在形成 spec/ADR/任务，不得据此宣称实现 |
| `RED` | 验收测试已建立并按预期失败 |
| `实现中` | 已获授权进行最小 GREEN |
| `自动验证` | 当前 SHA 的自动测试通过，人工门禁仍可能未完成 |
| `人工验收` | 正在目标平台/真实模板/真实流程核对 |
| `完成` | 所有规定门禁都有当前、可回读证据 |
| `历史完成` | 旧 SHA/旧模式曾完成，当前基线需重新确认 |

## 2. 门禁证据

里程碑“完成”至少需要：

- 固定需求/spec 与非目标。
- 与迁移、API、Word、AI 边界一致的实现。
- 当前 SHA 的自动测试结果。
- 需要时的 SQLite/MySQL、Windows/Linux、Word 和真实交互人工证据。
- 文档与代码一致性复核。
- 若已发布：远端 ref、CI `headSha`、Release 资产可回读。

Graphify 和 codebase-memory 是导航/覆盖证据，不单独构成完成证明。

## 3. 当前依赖图

```text
R0 事实基线与图谱
  └─ R1 质量/迁移/安全基线
       ├─ R2 当前五个教学模块复验
       └─ R3 Agent Foundation 规格与分支决策
            └─ R4A 受控 Agent READ/DRAFT
                 ├─ R4B Agent WRITE（独立未来门禁）
                 └─ R5 发布与运维复核
```

## 4. R0：事实基线与图谱

状态：`自动验证`（2026-08-23 本地审查完成；尚未提交/发布，也未执行平台人工验收）。

范围：

- 区分当前维护审查分支与最近产品主线，不把分支状态或未提交改动混写为已发布事实。
- 建立 `CONTEXT.md`、Roadmap、ADR、架构、数据模型和威胁模型。
- 纠正单用户、多用户、微服务、迁移 head 和测试数字的漂移。
- 建立 codebase-memory 与 Graphify 图谱并验证健康。

本地证据（工作树，基于 `dev4.0@0657c3a` 起点）：

- Ruff：`app`/`tests` 0 错误；全量 pytest `535 passed`。
- 依赖与迁移：Python 3.14.7，83 个已安装包兼容；全新 SQLite 升级到 `a6c4d8e2f9b1`。
- Graphify：OpenAI-compatible 完成代码/文档提取；其社区命名返回不可解析空 JSON 后，按固定顺序由 DeepSeek 完成命名。本轮非生成变更源全部覆盖，多重边诊断无缺失/悬空端点、自环或重复边；易随文档变化的节点计数不固化在路线图中。
- codebase-memory：full index 已完成，共享压缩图已写入 `.codebase-memory/graph.db.zst`；易随生成报告变化的节点计数只记录在当次审查报告中。

出口门禁：

- 文档链接与事实检查通过。
- codebase-memory 可查询当前审查基线。
- Graphify 来源覆盖、端点和完整性诊断可回读。
- 工作树改动清单明确，不夹带业务实现。

## 5. R1：质量、迁移与安全基线

状态：`自动验证`（2026-08-23 本地门禁通过；远端 push/PR CI 待固定 SHA 回读）。

目标：把“历史上能运行”提升为“当前 SHA 可重复验证”。

范围：

- 建立锁定或可审计的开发依赖安装方式。
- 已新增常规 push/PR 质量 CI，执行依赖检查、Ruff、全新 SQLite Alembic 迁移和全量 pytest；远端结果必须按 `headSha` 回读。
- 本地全新 SQLite 已升级到 `a6c4d8e2f9b1`，全量 pytest `548 passed`。
- 聚合失败注入 RED 已证明部分提交风险；一对一倾听和游戏观察现由 service/use-case 持有事务，内部 repository `flush()`、最外层 commit/rollback。
- API tenant 投影与 UI tenant + user 投影已显式命名，跨 tenant/user 负向测试覆盖列表、详情和子表。
- 设置页 AI `/models` HTTP 已移至 integration adapter，由 settings service 编排；大型页面的其余用例继续渐进抽离。
- 启动迁移已决策为桌面、开发、服务器统一 fail-closed；迁移失败中止启动，不提供 fail-open 开关。
- 隔离未注册的登录/RBAC 预备代码和单用户产品入口（当前 UI 仍为单用户；多用户优先级低）。
- 修复 Compose 默认凭据和健康检查对环境变量不一致的问题。
- 建立日志、导出、图片和数据库备份/恢复说明。

明确不做：未经过 spec 的新业务模块。

## 6. R2：当前教学模块复验

状态：`规划`。

按风险和未闭环程度建议顺序：

1. 一对一倾听完整 P8/P8d 人工验收（在聚合事务修复后）。
2. 每日活动计划在当前单用户模式下重跑主流程与 Word。
3. 游戏观察图片/视觉 AI/历史/Word 复验。
4. 自制教玩具与课程审议当前 SHA 回归。
5. 对外只读 API 的 HMAC、租户越权和真实调用方验收。

每个模块分别记录自动证据和人工证据，不使用一个模块的结果代替另一个模块。

## 7. R3：Agent Foundation 规格与分支决策

状态：`自动验证`（F005、F006 固定 GREEN 已验证；F007 未授权）。

已确认：[ADR-0005](ADR/ADR-0005-controlled-ai-agent-runtime.md) 和
[Agent Runtime 设计](design/agent-runtime.md) 已经固定首期上限，即每日活动计划的单 Agent、
4 个 READ、2 个 DRAFT、零持久化和零长期记忆。设计接受不代表 spec/Issue、RED 或实现已完成。

当前结果：

- 功能分支固定为 `feat/agent-foundation`；F002 原始 RED SHA 为 `ad13a6aa3e44ff98b2604d4a008649cd66185d80`。
- `main@cfeadefd7dfa056c1b3757876658493110d8cf84` 通过双亲 merge commit 同步到 `5de2e49bee19749f611b50747a31be9464b92d7b`；该远端 SHA 的 Quality 已通过。
- [冻结规格与停止边界](../specs/agent-foundation/spec.md)、[任务顺序](../specs/agent-foundation/tasks.md) 和 [Issue #48](https://github.com/ywyz/kindergartenManager/issues/48) 已建立。
- `specs/agent-foundation/tests/` 的 F005 固定 GREEN 为 `53dd2e8…`，双轴 Review 零发现且远端 Quality `32641923137` 精确匹配成功；F006 稳定 RED 为 `f0ab660…`，Review RED 为 `6b083fa…`、`8831b3f…`、`79e005a…` 与 `51f5e5f…`，最终实现/重构候选 `99167ef…` 为 Standards `0`、Spec `0`，Foundation `73 passed`、全量 `551 passed`；证据 SHA `049b520…` 的远端 Quality `32644290676` 精确匹配成功。
- 当前继续单用户；NiceGUI 多用户/RBAC 代码仅作为低优先级预备资产，不进入 Foundation 范围。
- 是否仍保持模块化单体？服务拆分必须有独立 ADR 和运营理由。
- 聚合事务和 tenant/user 投影修复后，每日计划、班级设置和日历的窄 Service 投影如何建立，使 Agent Tool 不直接调用 Repository？

当前停止边界：F006 Provider port 与有界串行 Runtime 的固定 SHA Review/CI 已闭合。F007 取消/超时/scope-fingerprint 变化/迟到丢弃、Tool 实现、UI 或 migration 仍需新的明确授权。

## 8. R4A：受控 Agent Foundation READ/DRAFT

状态：`自动验证`（F005、F006 固定 GREEN；F007 未授权）。

实现范围严格限定为：

1. 应用层单 `AgentRuntime`、供应商中立 `AgentProviderPort` 和关闭 `ToolRegistry`。
2. 四个 READ Tool：当前计划、计划上下文、日历判定、班级区域。
3. 两个 DRAFT Tool：登记栏目 Patch 和一日反思 Patch。
4. F006 提供有界串行 Tool loop、busy、Tool/消息/响应/ToolResult/request-id 上限和关闭输入输出校验；取消、超时与迟到/过期结果丢弃属于未授权 F007。
5. 只展示 assistant 文本和字段级 `PlanPatch`；无采用、保存、确认 WRITE 或历史恢复。

完成证据必须包含：未知/WRITE Tool、额外参数、prompt injection、跨 tenant/user、取消、超时和
过期结果的负向测试，以及所有路径对业务数据、页面正文、版本、preview、audit 和导出“零变化”的证明。

每个切片按以下顺序独立通过：

```text
文档/spec → Issue/任务 → RED → 最小 GREEN → Review → 当前 SHA 自动验证
→ 目标平台人工验收 → 合并 → 发布（如获授权）
```

不得提前实现后续切片；不得把 Review、合并、推送或发布视为自动授权。

## 9. R4B：Agent WRITE（未来独立里程碑）

状态：`规划`，当前未授权。

R4A 完成不会自动启动 R4B。只有在真实用户故事证明 DRAFT 不足，且已建立可信 actor/session、
`daily_plan` 显式单调 revision、Patch/target/revision/session/turn/expiry/nonce 绑定的逐次确认、短事务、
操作前版本、最小不可变审计和失败全回滚后，才能以新 ADR/spec/Issue/迁移/RED 开始。

## 10. R5：发布与运维复核

状态：`规划`。

范围：

- Windows 安装包/便携包、Debian 包、Docker 镜像分别验证。
- 备份、恢复、升级、卸载和数据目录行为。
- 固定 Word 模板在真实 Office/Word 中保真。
- 真实 MySQL、AI、节假日接口的失败与降级。
- Release SHA、资产、校验值、变更日志和回滚说明。

## 11. Roadmap 更新规则

- 状态变化必须附日期、SHA 和证据位置。
- 历史通过但当前未复跑时写“历史完成”，不写“完成”。
- 分支、身份模式、数据库或部署边界改变时同步 `CONTEXT.md` 与 ADR。
- 不在 Roadmap 中用模糊的“基本完成”“应该可用”代替明确门禁。
