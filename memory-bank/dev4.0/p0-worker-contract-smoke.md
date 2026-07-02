# dev4.0 P0 — Worker Contract Smoke

## 结果指标

证明 dev4.0 worker 可以按 `jobType` 分发任务，并对未知任务和 handler 失败返回可回写的结构化结果。

## 范围

- 在 `apps/worker` 建立任务分发纯函数。
- 使用 `packages/database` 的 `WorkflowJob` 合同。
- 支持按 `jobType` 注册 handler。
- 返回 succeeded / failed、result、error、retryable。

## 不做

- P0 不启动常驻 worker 进程。
- P0 不连接数据库领取任务。
- P0 不调用真实 AI。
- P0 不生成真实 Word。

## Gate Tests

```bash
pnpm --filter @kindergarten/worker typecheck
pnpm test:gate
```

测试覆盖：

- 已注册 jobType 调用对应 handler。
- 未注册 jobType 返回 failed 且 retryable=false。
- handler 抛错返回 failed 且 retryable=true。

## 失败边界

- 如果未知 jobType 被当作成功，测试失败。
- 如果 handler 抛错导致 worker 崩溃而不是结构化失败，测试失败。
