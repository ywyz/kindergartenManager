# dev4.0 P0 — Auth/RBAC Contract Spike

## 结果指标

证明 dev4.0 的权限判断不依赖前端隐藏按钮，而是由共享合同中的 workflow action、角色和 scope 统一计算。

## 范围

- 在 `packages/auth` 建立 RBAC 合同。
- 使用 `packages/contracts` 中的角色和 workflow action。
- 支持 `self`、`grade`、`tenant`、`system` 四类 scope。
- 返回可审计的授权结果：allowed、reason、auditAction。

## 不做

- P0 不实现登录。
- P0 不实现 session cookie、CSRF、密码哈希。
- P0 不连接数据库读取用户角色。
- P0 不实现 API middleware。

## 权限规则

- `self`：只允许访问本人资源。
- `grade`：只允许年级组长访问自己管理的年级。
- `tenant`：只允许访问当前园所租户资源。
- `system`：只允许系统管理员访问系统级动作。
- workflow action 的 `requiredRoles` 是第一层门禁；scope 是第二层门禁。

## Gate Tests

```bash
pnpm --filter @kindergarten/auth typecheck
pnpm test:gate
```

测试覆盖：

- 教师只能创建/维护本人记录。
- 年级组长只能审核自己管理年级的记录。
- 业务园长可以发布提示词，园长和系统管理员默认不能发布业务提示词。
- 系统管理员可以执行备份恢复，园长不能。
- 跨 tenant 资源访问被拒绝。

## 失败边界

- 如果前端可见性绕过 RBAC 函数，后续 API middleware 测试必须失败。
- 如果系统管理员默认获得业务提示词发布权限，测试失败。
- 如果年级组长能访问未绑定年级，测试失败。
