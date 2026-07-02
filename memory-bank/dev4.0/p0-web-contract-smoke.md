# dev4.0 P0 — Web Contract Smoke

## 结果指标

证明 dev4.0 前端可以从共享合同生成基础显示模型，不复制角色和高权限 action 常量。

## 范围

- 在 `apps/web` 建立合同 view model。
- 从 `packages/contracts` 读取角色和 workflow actions。
- 生成角色列表、业务高权限 action、系统高权限 action。
- `App` 使用该 view model。

## 不做

- P0 不实现真实页面布局。
- P0 不接 API。
- P0 不做浏览器 E2E。
- P0 不引入 React Testing Library。

## Gate Tests

```bash
pnpm --filter @kindergarten/web typecheck
pnpm test:gate
pnpm --filter @kindergarten/web build
```

测试覆盖：

- 前端角色列表包含 5 类角色。
- 提示词发布属于业务高权限 action。
- 备份恢复属于系统高权限 action。
- `App` 使用共享合同 view model。
- 前端构建命令通过。

## 失败边界

- 如果前端复制角色常量导致合同不一致，测试失败。
- 如果系统高权限 action 被归到业务 action，测试失败。
