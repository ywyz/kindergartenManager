# @kindergarten/observability

观测与审计边界包。

## 当前职责

- 结构化审计事件合同。
- 高风险动作审计字段。
- metadata 递归脱敏，避免 API Key、密码、Token、Authorization header 进入日志。

## 后续职责

- 结构化日志、指标和追踪。
- 备份、恢复、提示词发布、权限变更等高风险动作写入审计表。
- 线上 50 人规模的错误定位和安全审计。

## 验证

```bash
pnpm --filter @kindergarten/observability typecheck
pnpm test:gate
```

## P0 文档

见 `memory-bank/dev4.0/p0-observability-audit-spike.md`。
