# @kindergarten/contracts

跨服务共享合同包。

## 当前职责

- 维护 dev4.0 角色代码和中文名称。
- 维护核心 workflow 动作和权限边界。

## 验证

```bash
pnpm --filter @kindergarten/contracts typecheck
pnpm test:gate
pnpm eval:periodic
```
