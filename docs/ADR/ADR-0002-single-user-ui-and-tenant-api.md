# ADR-0002：单用户 UI 与租户只读 API 是两个身份边界

- 状态：部分取代（UI 身份边界由 ADR-0006 更新；API tenant 边界仍有效）
- 日期：2026-08-22

## 背景

本 ADR 的原始基线是固定身份单用户 UI 与独立的 tenant 只读 API。当前代码已恢复本地账号/JWT/RBAC、受保护
页面和 active 用户重读；可信 UI 会话、`jti`/`auth_epoch`、每日计划 revision 与逐次确认写入改由
[ADR-0006](ADR-0006-trusted-ui-session-and-confirmed-agent-write.md) 约束。`/api/v1` 仍使用映射到 tenant 的 API Key。

## 决策

- 旧固定身份单用户 UI 只作为历史状态保留，不再描述当前登录行为；当前 UI 必须使用 ADR-0006 的可信会话。
- 外部 API 采用独立服务主体：API Key → tenant_id；可通过 HMAC 加固。
- API 的租户能力不推导出 UI 的多用户能力。
- 若扩大角色、跨教师可见性或 API 写入范围，仍必须作为完整功能切片设计和验收，不能只打开路由或中间件。

## 后果

- frozen 应用只监听回环；源码/Docker 对外监听时必须额外配置 TLS、强密码和网络控制。
- UI 登录与会话已恢复，但生产管理员轮换、普通业务旧标签页、完整浏览器矩阵仍须按当前 SHA 分别验收。
- API 仍是独立的服务主体；API Key/HMAC 不得与 UI JWT、session 或角色语义混用。
