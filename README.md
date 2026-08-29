# KindergartenManager 幼儿园教学管理系统

KindergartenManager 是一个 Python 3.14.7 / NiceGUI 教学管理应用。当前主线是模块化单体：默认使用本地 SQLite，也可连接 MySQL；支持文本/视觉 AI、固定 Word 模板导出，以及按租户隔离的只读 REST API。

> 当前身份边界：UI 使用本地账号登录、JWT 与 RBAC，并按 tenant/user 隔离；匿名注册不挂载，空库也不会自动创建默认管理员。PyInstaller 模式只监听本机；源码或 Docker 模式对外提供服务时仍必须配置 TLS、强密码与网络访问控制。

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

当前 WRITE 边界仅允许本地应用在用户逐 Patch 显式确认后，把一个当前页面 Patch 原子应用到现有记录；
Provider WRITE、自动重试、批量/跨页面采用、新 Tool、多 Agent 和长期 Patch 持久化均不在当前能力内。
详见 [ADR-0005](docs/ADR/ADR-0005-controlled-ai-agent-runtime.md) 与
[ADR-0006](docs/ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md)。

## 快速开始

```bash
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.jobs.bootstrap_admin --init
.venv/bin/python -m app.main
```

浏览器访问 `http://localhost:8080`。首次运行会：

1. 解析 `.env` 与环境变量。
2. 在未设置 `DATABASE_URL` 时使用用户数据目录中的 SQLite。
3. 尝试执行 `alembic upgrade head`。
4. 不自动创建默认管理员；管理员由上述受控命令交互初始化。
5. 进入 `/login`，认证成功后再访问业务页面。

统一在 `/settings` 配置学期、班级、教师和 AI 接口。旧 `/setup` 只保留为跳转到 `/settings` 的兼容入口。

当前 Web 框架安全基线为 NiceGUI 3.16.0 + FastAPI 0.141.1 + Starlette 1.6.0。
其他 Dependabot 相关 Python 依赖下限、官方来源和验证方法见
[docs/DEPENDENCIES.md](docs/DEPENDENCIES.md)。

## 自动测试与迁移

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/alembic upgrade head
```

当前工作树 Alembic head：`e5f7a9c2d4b6`。

仓库历史曾记录多次通过结果，但这些数字属于对应旧 SHA。本 README 不把历史数字当作当前验证；交付时应记录本次命令、SHA、平台和结果。

## 配置

| 变量 | 默认/边界 |
|---|---|
| `DATABASE_URL` | 留空使用 SQLite；MySQL 例：`mysql+aiomysql://...` |
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

## 部署方式

### Windows / Linux 打包版

Tag 发布工作流可构建 Windows 安装包/便携包、Debian 包/Linux 便携包。发布资产是否可用必须以对应 tag/SHA 的工作流和目标平台人工验收为准。

### Docker

```bash
cp .env.example .env
# 先填写已解析到本机的 CADDY_DOMAIN，并用密码管理器填写
# MYSQL_ROOT_PASSWORD、MYSQL_PASSWORD，
# 并固定 ENCRYPTION_KEY、JWT_SECRET；MySQL 密码使用十六进制随机值。
docker compose up -d
docker compose exec app python -m app.jobs.bootstrap_admin --init
```

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
3. [docs/ADR/README.md](docs/ADR/README.md) — 架构决策。
4. [docs/design/system-architecture.md](docs/design/system-architecture.md) — 实际系统架构。
5. [docs/design/agent-runtime.md](docs/design/agent-runtime.md) — 受控 AI Agent 契约与实现门禁。
6. [docs/design/data-model.md](docs/design/data-model.md) — 数据模型与迁移不变量。
7. [docs/security/threat-model.md](docs/security/threat-model.md) — 威胁模型。
8. [docs/DEVELOPER.md](docs/DEVELOPER.md) — 开发者指南。
9. [docs/MANUAL_TESTING.md](docs/MANUAL_TESTING.md) — 当前人工验收矩阵。
10. [docs/USER_MANUAL.md](docs/USER_MANUAL.md) — 用户手册。
11. [docs/API.md](docs/API.md) — 对外只读 API。
12. [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md) — Python 依赖安全基线与 Dependabot 处理规则。

`memory-bank/` 保存模块设计和历史进度。若与当前代码或上述事实文档冲突，以当前代码、迁移、测试证据和 `CONTEXT.md` 为准。

## 当前开发门禁

聚合保存的首批原子性修复、tenant/user 投影区分、设置页 AI adapter、启动迁移 fail-closed 和常规质量 CI 已通过本地自动验证。大型页面用例仍需渐进抽离；READ/DRAFT Agent Foundation 必须在独立分支固定 spec/Issue/稳定 RED 后才能开始 GREEN，不能把 ADR、设计文档或保留分支自动视为主线已交付。
