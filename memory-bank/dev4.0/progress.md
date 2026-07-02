# dev4.0 进度记录

## 2026-07-02（P0 工程底座与技术验证）

### 已完成并推送

- 创建并推送 `dev4.0` 分支。
- 完成 dev4.0 总计划：线上唯一、全栈重写、用户各自 AI Key、5 类角色、S3/WebDAV 备份、提示词优化系统、权限矩阵、清理归档策略。
- 完成 P0 开发计划和测试计划：
  - `memory-bank/dev4.0/p0-dev-plan.md`
  - `memory-bank/dev4.0/p0-test-plan.md`
- 完成 P0 monorepo scaffold：
  - `apps/api`：Fastify health check。
  - `apps/web`：React/Vite 前端入口。
  - `apps/worker`：后台任务入口。
  - `packages/contracts`：角色和 workflow action 合同。
  - `packages/workflow`：workflow 定义合同。
  - `packages/prompt`：提示词发布阈值。
  - `packages/document`：Word 导出边界。
  - `packages/backup`：备份 manifest 和目标边界。
  - `packages/storage`：对象 key 安全生成。
- 完成 dev4 CI：lockfile 安装、lint、typecheck、gate tests、periodic evals、Python planning contract、依赖审计、SBOM。
- 完成 Word export spike：
  - `generateStyledWordDocument` 可生成包含中文、正文、表格、图片的 `.docx`。
  - 支持标题、表头、正文的字体、字号、段前段后和行距配置。
  - 测试解包 OpenXML，直接验证 `w:eastAsia`、字号、行距、表格和图片。

### Backup target spike 已完成本地验证

- 新增 `memory-bank/dev4.0/p0-backup-target-spike.md`。
- 新增 `BackupObjectTarget` 统一目标合同。
- 新增 WebDAV 目标实现，使用 Node 24 内置 `fetch`。
- 新增上传后读回 SHA-256 校验。
- 新增认证失败和完整性失败错误类型。
- S3 暂保留同一目标合同，P0 不接真实 S3 账号。

### MySQL job spike 已完成本地验证

- 新增 `memory-bank/dev4.0/p0-job-spike.md`。
- 新增 `packages/database` 的 workflow job 合同和 MySQL 8 SQL 合同。
- 领取 SQL 明确使用 `FOR UPDATE SKIP LOCKED`。
- 新增内存 job queue gate tests，验证并发领取互斥、失败重试、达到最大次数后失败、非锁持有者不能回写。

### Storage upload spike 已完成完整验证

- 新增 `memory-bank/dev4.0/p0-storage-upload-spike.md`。
- 新增 `createStoredObjectMetadata` 上传入口合同。
- 支持 PNG、JPEG、DOCX、XLSX 的扩展名、MIME、文件头和大小校验。
- 生成不含用户上传文件名的 tenant-scoped 对象 key。
- 返回 `key`、`bytes`、`sha256`、`mimeType`、`extension`、`assetKind` 元数据。
- 收紧 object id，禁止路径分隔符和 `..` 进入对象 key。

### 自动验证记录

- P0 scaffold 提交 `dae8ced`：
  - `pnpm check` 通过。
  - `pnpm --filter @kindergarten/web build` 通过。
  - `.venv/bin/pytest tests/ -q`：`547 passed`。
  - `pnpm audit:deps`：No known vulnerabilities found。
  - `pnpm run sbom:generate` 通过。
- Word export spike 提交 `73e1955`：
  - `pnpm check` 通过。
  - `.venv/bin/pytest tests/test_dev4_planning_contract.py -q`：`4 passed`。
  - `pnpm audit:deps`：No known vulnerabilities found。
  - `pnpm run sbom:generate` 通过。
- Backup target spike：
  - `pnpm check` 通过。
  - `.venv/bin/pytest tests/ -q`：`547 passed`。
  - `pnpm audit:deps`：No known vulnerabilities found。
  - `pnpm run sbom:generate` 通过。
- MySQL job spike：
  - `pnpm check` 通过。
  - `.venv/bin/pytest tests/ -q`：`547 passed`。
  - `pnpm audit:deps`：No known vulnerabilities found。
  - `pnpm run sbom:generate` 通过。
- Storage upload spike：
  - `pnpm check` 通过。
  - `.venv/bin/pytest tests/ -q`：`547 passed`。
  - `pnpm audit:deps`：No known vulnerabilities found。
  - `pnpm run sbom:generate` 通过。

### 需要 Julien 后续手工测试

- 当前不需要手工测试。
- 到 P1 备份配置 UI 完成后，需要 Julien 提供一个真实 WebDAV 或 S3 测试目标，做一次上传、下载、hash 校验和认证失败测试。

### 下一步

- 推送 Storage upload spike。
- 继续 P0 Auth/RBAC 合同 spike。
