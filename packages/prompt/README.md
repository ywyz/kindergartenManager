# @kindergarten/prompt

提示词优化系统基础包。

## 当前职责

- 定义提示词发布质量门槛。
- 阻止低于门槛的提示词进入发布状态。

## 验证

```bash
pnpm --filter @kindergarten/prompt typecheck
pnpm test:gate
```
