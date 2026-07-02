# dev4.0 P0 — 测试计划

## 测试目标

P0 测试用于证明 dev4.0 的工程底座可继续安全推进。测试重点不是业务功能，而是计划约束、工具链、Word 技术验证、任务领取和备份目标。

## Gate Tests

- `tests/test_dev4_planning_contract.py`
  - 验证 dev4.0 主计划存在。
  - 验证 P0 开发计划和测试计划存在。
  - 验证提示词优化系统、功能权限矩阵、S3/WebDAV 备份、清理归档策略已写入主计划。
  - 验证 P0 文档明确禁止在迁移完成前删除旧业务代码。

- TypeScript unit tests（P0 工具链建立后新增）
  - Word spike：中文字体、表格、图片、标题/表头/正文样式配置写入。
  - Job spike：MySQL 领取 SQL、任务领取互斥、失败重试、状态流转。
  - Backup spike：WebDAV 客户端上传、下载、hash 校验和失败错误分类；S3 保留同一目标合同。
  - Storage spike：图片、Word、Excel 上传类型、大小、hash、对象 key 安全。

## E2E / Integration

- P0 不做浏览器业务 E2E。
- CI smoke 必须执行安装、lint、typecheck、gate tests、periodic evals、Python planning contract、依赖扫描、SBOM。

## 安全测试

- lockfile 安装测试。
- OSV / npm audit / SBOM 生成命令测试。
- 备份目标认证失败测试。
- 文件名不使用用户输入拼路径的单元测试在 storage 包建立后补齐。

## 验收命令

```bash
.venv/bin/pytest tests/test_dev4_planning_contract.py -q
```

P0 工具链建立后追加：

```bash
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test:gate
pnpm eval:periodic
pnpm audit:deps
pnpm run sbom:generate
```

## 通过标准

- 所有 gate tests 通过。
- P0 spike 测试全部通过。
- 若安全扫描存在 Medium 以上问题，必须写入 `security/accepted-risks.md` 并标明到期处理日期。
