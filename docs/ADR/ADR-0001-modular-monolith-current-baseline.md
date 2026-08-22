# ADR-0001：当前以 NiceGUI 模块化单体为事实基线

- 状态：接受
- 日期：2026-08-22

## 背景

旧文档把 ai-service、word-service、holiday-service 描述为现有微服务，但当前仓库 `services/` 只有 README，Compose 只运行 Caddy、主应用和 MySQL。代码中的 AI、节假日、图片和 Word 仍位于 `app/integration/`。

## 决策

当前架构事实定义为单进程 NiceGUI/FastAPI 模块化单体：UI/API → service → repository/integration → core/infrastructure。`services/` 仅表示未来选项，不属于当前部署。

## 后果

- 文档、测试和故障边界以单体为准。
- 不创建假微服务契约或宣称 Compose 已包含它们。
- 未来拆分必须证明独立部署、容量、故障隔离或组织所有权收益，并新增 ADR、契约、鉴权和运维方案。
