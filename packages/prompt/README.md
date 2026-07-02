# @kindergarten/prompt

提示词优化系统基础包。

## 当前职责

- 定义提示词发布质量门槛。
- 阻止低于门槛的提示词进入发布状态。
- 汇总提示词 eval 样例结果。
- 仅允许业务园长进行风险放行。

## 验证

```bash
pnpm --filter @kindergarten/prompt typecheck
pnpm test:gate
```

## P0 文档

见 `memory-bank/dev4.0/p0-prompt-eval-spike.md`。
