# WMP-8 formal exporter 下一步提示词

从 Issue #56/#57 最终回写且 exact-SHA Quality/CodeQL 均成功的 WMP-7 closure SHA 开始，只实施
WMP-8 formal exporter，不实施 WMP-9。开始前必须回读两个 Issue，确认 `headSha`、Quality、CodeQL、
Review 0/0/0 与本地证据指向同一精确 SHA；任一不一致即停止。

先只读核对 CodeGraph/Codebase Memory、CONTEXT.md、ROADMAP、ADR-0008、模板中心 spec/design、
weekly-monthly spec、WMP-5 export contracts、WMP-6 receipt、WMP-7 active binding gate 及全部相关测试。
冻结稳定 RED 后再实现 GREEN；reviewer 必须只读，每个 finding 先由 Main 增加独立稳定 RED，再修复。

formal exporter 只能消费 WMP-7 已验证的当前 ACTIVE opaque binding，并严格执行关闭链：
`resolve_active → render → parse`。输入必须是已授权、不可变的 weekly/monthly ExportSnapshot；输出只包含
冻结的 ExportResult 与脱敏 metadata。tenant、document type、plan id/version、binding version/hash、contract、
rendered 与 parse report 任一不匹配、缺失、过期或在调用期间漂移均 fail closed。不得读取或返回模板路径、
blob、URL、bucket、storage handle、registry/descriptor、candidate evidence、provider DTO 或原始异常正文。

不得接受 requested historical version，不重生历史版本，不 fallback、不从零构建、不自动重试、不动态发现，
不实现模板 CRUD、上传、激活、回滚、下载或 active pointer/version 创建。不得新增数据库字段或 Alembic；若冻结
ExportRecord/持久化设计不足，停在 spec/稳定 RED 与迁移提案，等待明确授权。不得实施 WMP-9 正式业务验收、
审核流、统一文档中心、远程对象存储或任何 Agent 能力扩展。

验证必须包含：weekly/monthly 正向结果、授权前零模板调用、无 active/错误类型/跨 tenant/跨 document/version、
binding 漂移、render/parse 证据错配、未解析 token、安全检查失败、异常脱敏、无隐式业务/审计/preview/export
持久化变化，以及 WMP-7 capability 面未扩大。连续运行两次并记录 collected/passed/failed、完整节点集合与
node-only hash；运行模板中心已实施门、完整 WMP、全库、Agent Foundation、Ruff/format/diff。

只有最终 Review High/Medium/Low 0/0/0、所有规定 GREEN、提交并推送、exact-SHA Quality/CodeQL 成功且回写
Issue #56/#57 后才停止。完成时明确下一道独立门为 WMP-9 正式业务验收；不得在本任务提前执行 WMP-9。
