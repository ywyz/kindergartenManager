# @kindergarten/workflow

子系统 workflow 定义合同。

## 当前职责

- 约束 workflow `slug`、名称、版本和动作列表。
- 要求每个子系统动作显式声明允许角色和审计要求。

## 验证

```bash
pnpm --filter @kindergarten/workflow typecheck
pnpm test:gate
```
