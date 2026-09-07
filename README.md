# KindergartenManager 幼儿园教学管理系统

KindergartenManager 是一个部署在云服务器上的在线幼儿园教学管理系统，用户通过浏览器访问。当前主线是
Python 3.14.7 / NiceGUI 模块化单体，生产参考拓扑使用 Caddy、主应用和 MySQL 8；系统支持文本/视觉 AI、
固定 Word 模板导出，以及按租户隔离的只读 REST API。

> 当前产品交付边界：只提供云端在线 Web 系统，不再把 Windows/Linux 安装包或便携包作为独立产品。
> UI 使用系统账号、JWT 与 RBAC，并按 tenant/user 隔离；匿名注册不挂载，空库不会自动创建默认管理员。
> 生产必须使用 HTTPS、强密码、网络访问控制、MySQL、备份恢复和不可变镜像门禁。

## 当前能力

- 每日活动计划：学期/日期、教案拆分、年龄适配、活动生成、差异比对、Word 导出。
- 游戏观察：图片上传、视觉 AI、可编辑观察记录、历史和 Word 导出。
- 一对一倾听：五领域、指标、图片、历史、编辑、合并/分领域/批量导出。
- 自制教玩具：AI 生成、编辑、保存、历史和 Word 导出。
- 课程审议：教案拆分、审议调整、修订稿、历史、删除和 Word 导出。
- 配置中心：学期、班级、教师、文本/视觉 AI Key、提示词版本。
- 只读 API：`/api/v1`，用于未来与其他系统集成；API Key 必填，HMAC 可选，业务查询强制 `tenant_id`。

当前并未完成微服务拆分；`services/` 只是未来规划。实际运行单元为一个 NiceGUI 应用进程，外加可选 Caddy/MySQL。

## 技术栈

| 层 | 选型 |
|----|------|
| 语言 | Python 3.12+（开发环境 3.14） |
| 前后端 | NiceGUI（底层 FastAPI / Starlette） |
| 数据库 | MySQL 8（async：SQLAlchemy 2 + aiomysql）；迁移：Alembic |
| 鉴权 | JWT（PyJWT）+ Argon2（argon2-cffi）+ RBAC |
| 加密 | Fernet（cryptography）—— AI Key 入库加密 |
| AI | OpenAI 兼容 Chat Completions（httpx + tenacity 重试） |
| 文档导出 | python-docx |
| 测试 | pytest + pytest-asyncio（SQLite 内存库隔离） |

## 受控 AI Agent

每日活动计划页已接入受控单 Agent。Provider/Tool 能力面固定为 4 个 READ Tool、2 个 DRAFT Tool、
0 个 Provider WRITE；每轮上下文按可信 tenant/user 与当前页面重建并在轮后丢弃，不保存对话、线程、
embedding、工具结果或长期记忆。DRAFT 只返回内存 `PlanPatch`。

当前 WRITE 边界仅允许应用服务层在用户逐 Patch 显式确认后，把一个当前页面 Patch 原子应用到现有记录；
Provider WRITE、自动重试、批量/跨页面采用、新 Tool、多 Agent 和长期 Patch 持久化均不在当前能力内。
详见 [ADR-0005](docs/ADR/ADR-0005-controlled-ai-agent-runtime.md) 与
[ADR-0006](docs/ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md)。

## 本地开发与测试

以下命令只用于开发、自动测试或隔离验收，不是面向用户的本地应用安装方式。正式用户应访问由园所提供的
HTTPS 在线地址。

```bash
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
# 仅用于 schema 已在当前 Alembic head 时的幂等校验；revision 变化必须改用部署指南的完整 Release + receipt 流程
.venv/bin/python -m app.jobs.migrate_database \
  --backup-evidence /absolute/path/backup-evidence.json \
  --protected-image no-running-image
.venv/bin/python -m app.jobs.bootstrap_admin --init
.venv/bin/python -m app.main
```

revision 变化时不得直接使用上述简化命令；完整的 draft Release、OCI/source revision、migration receipt 与
post-migration acceptance 参数见 [部署指南](docs/DEPLOYMENT.md)。

开发浏览器访问 `http://localhost:8080`。首次运行会：

1. 解析 `.env` 与环境变量。
2. 在未设置 `DATABASE_URL` 时，开发/测试模式使用当前工作目录中的 SQLite；生产必须显式连接 MySQL 8。
3. 应用启动不执行迁移；迁移只由已验证备份门保护的显式命令执行。
4. 不自动创建默认管理员；管理员由上述受控命令交互初始化。
5. 进入 `/login`，认证成功后再访问业务页面。

统一在 `/settings` 配置学期、班级、教师和 AI 接口。旧 `/setup` 只保留为跳转到 `/settings` 的兼容入口。

当前 Web 框架安全基线为 NiceGUI 3.16.0 + FastAPI 0.141.1 + Starlette 1.6.0。
其他 Dependabot 相关 Python 依赖下限、官方来源和验证方法见
[docs/DEPENDENCIES.md](docs/DEPENDENCIES.md)。

## 自动测试与迁移

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m app.jobs.migrate_database \
  --backup-evidence /absolute/path/backup-evidence.json \
  --protected-image no-running-image
```

当前工作树 Alembic head：`3c9f4b2a7d1e`。前序 `2b7f3d5e9c8a` 为用户增加正整数
`auth_epoch`；当前 head 增加 WMP-9 production prerequisites 的六张表及其约束。改密或管理员重置会原子
递增 `auth_epoch`，从而使此前签发的 UI token 失效。

仓库历史曾记录多次通过结果，但这些数字属于对应旧 SHA。本 README 不把历史数字当作当前验证；交付时应记录本次命令、SHA、平台和结果。

## 配置

| 变量 | 默认/边界 |
|---|---|
| `DATABASE_URL` | 开发/测试留空使用 SQLite；云端生产必须显式配置 MySQL 8 |
| `KINDERGARTEN_DATA_DIR` | 可选绝对路径；显式部署时统一承载 SQLite、密钥和运行期 `.env` |
| `ENCRYPTION_KEY` | 留空自动生成并持久化；服务器应显式提供 |
| `JWT_SECRET` | 留空自动生成；当前主要用于 NiceGUI storage secret |
| `PORT` | `8080` |
| `HOLIDAY_API_URL` | timor.tech；失败允许提示后降级 |
| `API_KEYS` | `key:tenant_id` 列表；留空时业务 API 关闭 |
| `API_SIGNING_SECRET` | 非空时业务 API 强制 HMAC |
| `API_SIGNATURE_MAX_SKEW` | 默认 300 秒 |
| `IMAGE_STORAGE_BACKEND` | 默认 `mysql_blob` |
| `IMAGE_MAX_BYTES` | 默认 1 MiB |

不要提交 `.env`、`.kindergarten_secrets`、数据库、真实照片、导出文件或密钥。

## 云端部署

唯一产品交付目标是云服务器上的在线 Web 系统。Windows/Linux 桌面安装包、便携包和 Debian 本地应用已退出
产品路线；仓库中仍存在的打包脚本或历史 Release 资产不代表当前受支持交付。源码和 SQLite 仅用于开发、
测试与隔离验收。

Docker 发布与生产部署已改为收敛到不可变镜像引用；`docker-image.json` 会随 release 附件上传，并在 release body 中写入
`tag`、`source SHA`、`OCI index digest`、`repository@sha256`。`/api/v1/health` 仍只表示进程存活；
`/api/v1/readiness` 独立检查数据库连接与 schema revision。Issue #54 的真实 MySQL 故障/恢复验收仍未由本地实现替代。生产密码文件、轮换门禁、
部署状态与回滚边界见 [生产部署指南](docs/DEPLOYMENT.md)。

### Docker/Compose 参考拓扑

```bash
cp .env.example .env
# 先填写已解析到本机的 CADDY_DOMAIN，并用密码管理器填写
# MYSQL_ROOT_PASSWORD、MYSQL_PASSWORD，
# 并固定 ENCRYPTION_KEY、JWT_SECRET；MySQL 密码使用十六进制随机值。
docker compose up -d
# 下列简化迁移只允许数据库已经在当前 Alembic head 时作幂等复核；新库/升级请按部署指南先建完整候选/Release 绑定
docker compose exec app python -m app.jobs.migrate_database \
  --backup-evidence /absolute/container/path/backup-evidence.json \
  --protected-image no-running-image
docker compose exec -e BOOTSTRAP_ADMIN_ALLOW_REMOTE=true app python -m app.jobs.bootstrap_admin --init
```

部署脚本使用不可变镜像、串行锁、owner-only 状态、失败自动回滚和 dry-run；稳定部署状态目录应独立于按版本切换的 Compose 目录：

```bash
python -m scripts.deploy --service app --state-dir /var/lib/kindergarten-manager/deploy-state \
  --backup-evidence /secure/path/backup-evidence.json --protected-image <当前不可变镜像ref> \
  --acceptance-runner /secure/path/r5-acceptance-runner \
  --health-url https://manager.ywyz.tech/api/v1/health \
  --readiness-url https://manager.ywyz.tech/api/v1/readiness \
  deploy ghcr.io/ywyz/kindergartenmanager@sha256:<64位digest>
python -m scripts.deploy --service app --state-dir /var/lib/kindergarten-manager/deploy-state \
  --backup-evidence /secure/path/backup-evidence.json --protected-image <当前不可变镜像ref> \
  --acceptance-runner /secure/path/r5-acceptance-runner \
  --health-url https://manager.ywyz.tech/api/v1/health \
  --readiness-url https://manager.ywyz.tech/api/v1/readiness rollback
```

该 `BOOTSTRAP_ADMIN_ALLOW_REMOTE` 只作用于这一次交互初始化命令；常驻 app 容器不得设置它，MySQL root
凭据仍只属于 db 容器。

当前 Compose 包含 Caddy、主应用和 MySQL；缺少生产域名或数据库密码时会失败关闭。域名必须先通过
DNS 解析到部署主机，并允许 Caddy 使用 80/443 端口自动申请和续期 HTTPS 证书。应用数据使用独立
`app_data` 卷，不覆盖镜像内 `/app` 代码；部署与升级时必须同时保留 `app_data`、`db_data`、`exports`
卷（以及 Caddy 证书状态卷），并限制 UI 网络访问。

开发 override：

```bash
CADDY_DOMAIN=localhost docker compose \
  -f docker-compose.yml -f docker-compose.dev.yml up
```

## 架构速览

```text
NiceGUI UI / FastAPI-style API
            │
         service
        ├─ controlled Agent ── Agent Provider
        └───┬─────────┘
            │
        ┌───┴─────────┐
   repository     integration
        │        AI / Holiday / Image / Word
   SQLite/MySQL
```

目录职责：

- `app/ui/`：页面与组件。
- `app/api/`：只读 API 契约与鉴权。
- `app/service/`：业务编排。
- `app/repository/`：数据库访问和租户过滤。
- `app/integration/`：AI、节假日、图片和 Word 适配器。
- `app/core/`：配置、数据库、模型、迁移启动、日志、审计和加密。
- `alembic/`：唯一 schema 演进路径。
- `templates/`：固定 Word 模板。
- `tests/`：pytest 自动测试。

## 文档导航

建议按顺序阅读：

1. [CONTEXT.md](CONTEXT.md) — 当前事实、边界、分支与风险。
2. [docs/ROADMAP.md](docs/ROADMAP.md) — 里程碑与门禁。
3. [docs/PRODUCT_MANAGER_GUIDE.md](docs/PRODUCT_MANAGER_GUIDE.md) — 当前产品能力、用户旅程与验收规划。
4. [docs/PRODUCT_DIRECTION.md](docs/PRODUCT_DIRECTION.md) — 业务功能与系统能力方向、阶段依赖和非目标。
5. [docs/ADR/README.md](docs/ADR/README.md) — 架构决策。
6. [docs/design/system-architecture.md](docs/design/system-architecture.md) — 实际系统架构。
7. [docs/design/agent-runtime.md](docs/design/agent-runtime.md) — 受控 AI Agent 契约与实现门禁。
8. [docs/design/data-model.md](docs/design/data-model.md) — 数据模型与迁移不变量。
9. [docs/security/threat-model.md](docs/security/threat-model.md) — 威胁模型。
10. [docs/DEVELOPER.md](docs/DEVELOPER.md) — 开发者指南。
11. [docs/DEVELOPMENT_WORKSTATION.md](docs/DEVELOPMENT_WORKSTATION.md) — 开发电脑依赖、Skills 与安全换机清单。
12. [docs/MANUAL_TESTING.md](docs/MANUAL_TESTING.md) — 当前人工验收矩阵。
13. [docs/USER_MANUAL.md](docs/USER_MANUAL.md) — 用户手册。
14. [docs/API.md](docs/API.md) — 对外只读 API。
15. [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md) — Python 依赖安全基线与 Dependabot 处理规则。

`memory-bank/` 保存模块设计和历史进度。若与当前代码或上述事实文档冲突，以当前代码、迁移、测试证据和 `CONTEXT.md` 为准。

## 当前开发门禁

聚合保存的首批原子性修复、tenant/user 投影区分、设置页 AI adapter、启动迁移 fail-closed 和常规质量 CI 已通过本地自动验证。READ/DRAFT Agent Foundation 已进入主线，其当前能力、测试 SHA 与独立证据以 [`specs/agent-write/tests/README.md`](specs/agent-write/tests/README.md) 为准；后续 Agent 能力扩展仍必须先固定新的 spec/Issue 和稳定 RED，再按对应门禁实现，不能把 ADR 或设计文档自动视为授权。
