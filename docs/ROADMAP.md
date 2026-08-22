# KindergartenManager 产品与工程路线图

> 当前快照：2026-08-22，基线 `main@225fe139`。

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

状态：`自动验证`（文档和图谱在当前任务中生成，尚未提交/发布）。

范围：

- 删除废弃的 dev4.0 及之后远端版本分支。
- 建立 `CONTEXT.md`、Roadmap、ADR、架构、数据模型和威胁模型。
- 纠正单用户、多用户、微服务、迁移 head 和测试数字的漂移。
- 建立 codebase-memory 与 Graphify 图谱并验证健康。

出口门禁：

- 文档链接与事实检查通过。
- codebase-memory 可查询当前 `main`。
- Graphify 来源覆盖、端点和完整性诊断可回读。
- 工作树改动清单明确，不夹带业务实现。

## 5. R1：质量、迁移与安全基线

状态：`规划`。

目标：把“历史上能运行”提升为“当前 SHA 可重复验证”。

范围：

- 建立锁定或可审计的开发依赖安装方式。
- 新增常规 push/PR 质量 CI，而不仅是 tag 发布工作流。
- 在全新 SQLite 上执行 `alembic upgrade head`，运行全量 pytest。
- 评审启动迁移 fail-open 行为，确定桌面与服务器模式的失败策略。
- 清理或隔离未注册的登录/RBAC 页面和单用户残留 UI。
- 修复 Compose 默认凭据和健康检查对环境变量不一致的问题。
- 建立日志、导出、图片和数据库备份/恢复说明。

明确不做：未经过 spec 的新业务模块。

## 6. R2：当前教学模块复验

状态：`规划`。

按风险和未闭环程度建议顺序：

1. 一对一倾听完整 P8/P8d 人工验收。
2. 每日活动计划在当前单用户模式下重跑主流程与 Word。
3. 游戏观察图片/视觉 AI/历史/Word 复验。
4. 自制教玩具与课程审议当前 SHA 回归。
5. 对外只读 API 的 HMAC、租户越权和真实调用方验收。

每个模块分别记录自动证据和人工证据，不使用一个模块的结果代替另一个模块。

## 7. R3：Agent Foundation 规格与分支决策

状态：`设计中`。

已确认：[ADR-0005](ADR/ADR-0005-controlled-ai-agent-runtime.md) 和
[Agent Runtime 设计](design/agent-runtime.md) 已经固定首期上限，即每日活动计划的单 Agent、
4 个 READ、2 个 DRAFT、零持久化和零长期记忆。设计接受不代表 spec/Issue、RED 或实现已完成。

开始前必须回答：

- 新工作以 `main` 还是经审查后的 `origin/dev3.4` 为基线？
- `dev3.4` 的 6 个未合并提交哪些保留、重写或放弃？
- Agent Foundation 的 spec/Issue、任务顺序、稳定 RED 和停止边界是什么？
- 是否继续单用户，还是正式恢复认证/多用户？两者不能隐式混合。
- 是否仍保持模块化单体？服务拆分必须有独立 ADR 和运营理由。
- 每日计划、班级设置和日历的窄 Service 投影如何建立，使 Agent Tool 不直接调用 Repository？

出口门禁：固定 spec、任务顺序、分支、Issue 和第一组稳定 RED。

## 8. R4A：受控 Agent Foundation READ/DRAFT

状态：`规划`。

实现范围严格限定为：

1. 应用层单 `AgentRuntime`、供应商中立 `AgentProviderPort` 和关闭 `ToolRegistry`。
2. 四个 READ Tool：当前计划、计划上下文、日历判定、班级区域。
3. 两个 DRAFT Tool：登记栏目 Patch 和一日反思 Patch。
4. 有界的串行 Tool loop、取消、超时、busy 和迟到/过期结果丢弃。
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
