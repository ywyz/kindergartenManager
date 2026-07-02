# @kindergarten/database

数据库边界包。

## 当前职责

- MySQL workflow job 表 SQL 合同。
- 任务领取事务 SQL，使用 `FOR UPDATE SKIP LOCKED`。
- 内存 job queue，用于 gate tests 验证领取互斥、失败重试、状态回写。

## 后续职责

- Prisma schema 和 migration。
- 业务数据表、审计表。
- 备份恢复前后的数据一致性检查。

## 验证

```bash
pnpm --filter @kindergarten/database typecheck
pnpm test:gate
```

## P0 文档

见 `memory-bank/dev4.0/p0-job-spike.md`。
