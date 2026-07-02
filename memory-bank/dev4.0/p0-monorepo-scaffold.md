# dev4.0 P0 — Monorepo Scaffold 说明

## 结果指标

P0 scaffold 的可见结果是后续 dev4.0 子系统可以在独立目录中开发、测试和审查，不再把新业务继续堆到旧 NiceGUI 目录。

## 范围

- `apps/api`：线上 API 服务入口，当前只保留 health check。
- `apps/web`：React/Vite 前端入口，当前只验证角色合同可被前端使用。
- `apps/worker`：异步任务入口，后续承载 AI、导出、备份等后台任务。
- `packages/contracts`：跨服务共享的类型、角色、权限动作。
- `packages/workflow`：子系统 workflow 定义合同。
- `packages/prompt`：提示词优化发布门槛。
- `packages/backup`：备份 manifest 和 hash 校验。
- `packages/storage`：对象存储 key 生成，禁止用户输入直接拼路径。

## 不做

- 不迁移旧业务子系统。
- 不删除旧文档、模板、迁移和测试。
- 不接入真实数据库、AI、S3 或 WebDAV。

## Gate Tests

```bash
pnpm test:gate
```

覆盖 API health check、角色权限合同、workflow 定义、提示词发布门槛、备份 manifest、对象存储 key。

## Periodic Eval

```bash
pnpm eval:periodic
```

覆盖 P0 架构约束：文档、gate tests、eval 入口必须接入根工作流，核心角色和高权限动作必须保留。

## CI

`.github/workflows/dev4-ci.yml` 在 `dev4.0` 分支 push 和 pull request 上执行：

- `pnpm install --frozen-lockfile`
- `pnpm lint`
- `pnpm typecheck`
- `pnpm test:gate`
- `pnpm eval:periodic`
- `pytest tests/test_dev4_planning_contract.py -q`
- `pnpm audit:deps`
- `pnpm run sbom:generate`

## 失败边界

- 如果 `packages/contracts` 中角色顺序或中文名称变化，eval 会失败。
- 如果 `prompt:release` 或 `backup:restore` 被放宽权限，eval 会失败。
- 如果根工作流不再执行 `eval:periodic`，eval 会失败。
- 如果 CI 不再执行 P0 验收命令，eval 会失败。
