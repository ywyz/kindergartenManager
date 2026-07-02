# @kindergarten/api

dev4.0 线上 API 服务入口。

## 当前职责

- 提供 `/health/live` 和 `/health/ready`。
- 提供 `/api/v1/contracts/roles` 和 `/api/v1/contracts/workflow-actions`。
- 后续承载认证、workflow API、导出任务 API 和备份管理 API。

## 验证

```bash
pnpm --filter @kindergarten/api typecheck
pnpm test:gate
```

## P0 文档

见 `memory-bank/dev4.0/p0-api-contract-smoke.md`。
