# KindergartenManager 架构决策记录

ADR 记录会长期影响多个模块、难以通过普通代码注释表达的决策。

## 状态

- `提议`：尚未确认，不得作为实现授权。
- `接受`：当前有效。
- `取代`：由新的 ADR 替代，保留历史。
- `废弃`：不再适用，且没有直接替代。

## 索引

| ADR | 决策 | 状态 |
|---|---|---|
| [ADR-0001](ADR-0001-modular-monolith-current-baseline.md) | 当前以 NiceGUI 模块化单体为事实基线 | 接受 |
| [ADR-0002](ADR-0002-single-user-ui-and-tenant-api.md) | 单用户 UI 与租户只读 API 是两个身份边界 | 部分取代（UI 身份见 ADR-0006） |
| [ADR-0003](ADR-0003-sqlite-default-mysql-optional-alembic.md) | SQLite 默认、MySQL 可选、Alembic 唯一 schema 路径 | 接受 |
| [ADR-0004](ADR-0004-ai-and-fixed-word-boundaries.md) | AI 适配器、教师采用与固定 Word 模板边界 | 接受 |
| [ADR-0005](ADR-0005-controlled-ai-agent-runtime.md) | 受控单 AI Agent、关闭 READ/DRAFT Tool 与零持久化 | 接受 |
| [ADR-0006](ADR-0006-trusted-ui-session-and-confirmed-agent-write.md) | 可信 UI 会话、每日计划 revision 与逐次确认 Agent WRITE | 接受（W005/W006 已实现；W007 尚未进入） |

## 何时新增 ADR

以下变化应新增或取代 ADR：身份模式、数据权威来源、服务拆分、部署拓扑、AI 供应商/数据边界、
Agent Tool/权限/记忆/写入边界、图片存储、Word 模板契约、备份恢复或启动失败策略。

修复局部 bug、增加普通字段或不改变跨模块边界的重构通常不需要 ADR。
