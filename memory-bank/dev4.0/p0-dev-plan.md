# dev4.0 P0 — 基线与技术验证开发计划

## 目标

P0 不交付业务功能。P0 的目标是为 dev4.0 后续实现建立可运行、可测试、可审计的工程底座，并验证三件高风险能力：Word 模板生成、MySQL 任务领取、S3/WebDAV 备份目标。

## 前置规则

- 每个 P 阶段开始前必须先有 `dev-plan.md`、`test-plan.md` 和对应自动测试。
- 每个实现提交必须说明关联的计划条目和测试命令。
- 不删除 dev3.4 业务代码、迁移、模板和测试，直到对应 dev4.0 workflow 完成迁移和回归。
- 清理只允许覆盖临时锁文件、缓存、构建产物、导出产物和运行期状态。

## 实施范围

- 建立 dev4.0 monorepo 骨架：`apps/web`、`apps/api`、`apps/worker`、`packages/*`。
- 建立 TypeScript 工具链：package manager、lockfile、lint、format、test。
- 建立 gate tests 与 periodic evals：根工作流必须同时执行确定性单元测试和架构约束 eval。
- 建立 CI 门禁：安装、测试、lint、依赖扫描、SBOM。
- 完成 Word 技术验证：中文、图片、表格、样式配置写入 `.docx`。
- 完成 MySQL job 表技术验证：worker 原子领取任务、失败重试、状态回写。
- 完成 S3 和 WebDAV 技术验证：上传、下载、hash 校验、认证失败告警。
- 建立 dev4.0 文档目录和每阶段测试记录格式。

## 不在 P0 范围

- 不迁移任何业务子系统。
- 不实现登录、RBAC、AI Key 管理。
- 不接入真实 AI。
- 不替换线上系统。
- 不删除旧 NiceGUI 运行代码。

## 输出物

- dev4.0 monorepo 初始目录与 package 配置。
- `memory-bank/dev4.0/p0-monorepo-scaffold.md`。
- `memory-bank/dev4.0/p0-word-spike.md`。
- `memory-bank/dev4.0/p0-backup-target-spike.md`。
- `memory-bank/dev4.0/p0-job-spike.md`。
- `memory-bank/dev4.0/p0-storage-upload-spike.md`。
- `memory-bank/dev4.0/p0-auth-rbac-spike.md`。
- `memory-bank/dev4.0/p0-ai-key-crypto-spike.md`。
- `memory-bank/dev4.0/p0-observability-audit-spike.md`。
- `memory-bank/dev4.0/p0-prompt-eval-spike.md`。
- `memory-bank/dev4.0/p0-api-contract-smoke.md`。
- P0 spike 代码和测试。
- P0 scaffold periodic eval。
- CI 配置。
- CI 必须覆盖 lockfile 安装、lint、typecheck、gate tests、periodic evals、Python planning contract、依赖扫描和 SBOM。
- SBOM 与依赖扫描报告生成命令。
- P0 测试报告。
- 清理报告：列出实际删除的临时文件和未删除旧资产的理由。

## 验收标准

- `tests/test_dev4_planning_contract.py` 通过。
- 新 TypeScript 测试命令通过。
- P0 scaffold periodic eval 通过。
- Word spike 生成的 `.docx` 能被解析并包含中文、图片、表格和样式配置结果。
- MySQL job spike 能证明同一任务不会被两个 worker 同时领取。
- S3/WebDAV 至少一个目标通过上传、下载和 SHA-256 校验；另一个目标允许 mock，但接口测试必须存在。
- CI 在 GitHub Actions 上可运行。
