# dev4.0 P0 — MySQL Job Spike

## 结果指标

证明 dev4.0 后台任务可以通过 MySQL 8 任务表实现原子领取、失败重试和状态回写，避免同一任务被多个 worker 同时执行。

## 范围

- 在 `packages/database` 建立 workflow job 合同。
- 固化 MySQL 8 任务表 DDL 和事务领取 SQL。
- 任务领取 SQL 必须使用 `FOR UPDATE SKIP LOCKED`。
- 建立内存 job queue，用 gate tests 验证并发领取互斥、失败重试、最终失败和成功回写。

## 不做

- P0 不启动真实 MySQL 容器。
- P0 不引入 Prisma。
- P0 不实现 worker 进程循环。
- P0 不执行真实 AI 或导出任务。

## MySQL 领取策略

worker 领取任务必须在同一个事务内执行：

1. `START TRANSACTION`
2. 按 `status='queued'`、`run_at <= NOW(3)`、`attempts < max_attempts` 查询最早任务。
3. `SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1` 锁定单行。
4. 更新为 `running`，写入 `locked_by`、`locked_at`，`attempts = attempts + 1`。
5. 重新读取该任务并 `COMMIT`。

## Gate Tests

```bash
pnpm --filter @kindergarten/database typecheck
pnpm test:gate
```

测试覆盖：

- 多 worker 并发领取同一队列时，同一任务只会被领取一次。
- 任务失败后在未达到 `maxAttempts` 前重新入队。
- 达到最大重试次数后状态变为 `failed`。
- 只有持有锁的 worker 可以成功回写。
- MySQL SQL 合同包含 `FOR UPDATE SKIP LOCKED`。

## 失败边界

- 如果缺少 `FOR UPDATE SKIP LOCKED`，测试失败。
- 如果并发领取出现重复 job id，测试失败。
- 如果非锁持有者能回写任务，测试失败。
