# dev4.0 P0 — API Contract Smoke

## 结果指标

证明 dev4.0 API 层可以暴露共享合同，前端无需复制角色和 workflow action 常量。

## 范围

- 在 `apps/api` 增加只读合同端点。
- 保留 health check。
- 暴露角色列表和核心 workflow actions。
- 合同端点设置 `Cache-Control: no-store`，避免发布后旧权限合同被浏览器缓存。

## 不做

- P0 不实现登录。
- P0 不实现业务 CRUD。
- P0 不连接数据库。
- P0 不实现 OpenAPI 文档。

## Endpoints

- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1/contracts/roles`
- `GET /api/v1/contracts/workflow-actions`

## Gate Tests

```bash
pnpm --filter @kindergarten/api typecheck
pnpm test:gate
```

测试覆盖：

- health checks 返回 `200`。
- roles 端点返回 5 类角色和中文名称。
- workflow actions 端点返回权限动作、scope 和 auditAction。
- 合同端点带 `Cache-Control: no-store`。

## 失败边界

- 如果角色中文名和共享合同不一致，测试失败。
- 如果 workflow actions 未暴露 auditAction，测试失败。
- 如果合同端点可被缓存，测试失败。
