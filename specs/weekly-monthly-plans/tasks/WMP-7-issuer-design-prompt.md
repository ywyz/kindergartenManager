# WMP-7 issuer 设计缺口下一步提示词

> 状态：已于 2026-09-06 执行并进入交付闭合；下一道提示词见 `WMP-8-formal-exporter-prompt.md`。

从已完整验证、发布并部署的精确 SHA
`6bbff57f0c410459bcdb3bdd86980013d4b6c80e` 开始，只处理 WMP-7/T011-E 的 receipt issuer
设计缺口，不实施 WMP-8。

先只读核对 CodeGraph/Codebase Memory、CONTEXT.md、ROADMAP、ADR-0008、模板中心设计、weekly-monthly spec、
WMP-6 receipt 与现有 32 节点稳定 RED。威胁模型必须明确回答：不受信任的同进程 Python 模块是否属于攻击面。

若属于攻击面，冻结一个可验证且不可由同进程反射/monkeypatch 伪造的 issuer/signature 契约，并明确密钥托管、轮换、
进程重启、并发、过期、重放、失败关闭和测试策略。不得把 module private、closure、WeakSet/weakref、对象 identity
或命名约定描述为安全边界。若方案需要数据库字段、Alembic、外部 signer/HSM/KMS 或新的 evidence store，只提交
ADR/spec/稳定 RED 与迁移提案，等待明确授权，不实现。

若不属于攻击面，必须在 ADR/spec 中明确受信任进程内 capability 边界及理由，并把 RED 调整为该威胁模型可证明的
完整性、当前 profile/contract 漂移和 replay 规则；不得声称对恶意同进程模块不可伪造。

reviewer 必须只读；每个 finding 先由 Main 补稳定 RED，再修复。只有 Review 0/0/0、WMP-7 GREEN、连续两次
节点集合一致、全库/模板中心/WMP/Agent Foundation/Ruff/format/diff 通过、提交推送及 exact-SHA Quality/CodeQL
成功并回写 Issue #56/#57 后才停止。届时明确下一道独立门为 WMP-8 formal exporter；不得在本任务实现 WMP-8、
WMP-9、审核流、统一文档中心、远程对象存储或 Agent 能力扩展。
