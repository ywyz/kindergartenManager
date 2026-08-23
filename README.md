# KindergartenManager 幼儿园教学管理系统

KindergartenManager 是一个 Python 3.14.7 / NiceGUI 教学管理应用。当前主线是模块化单体：默认使用本地 SQLite，也可连接 MySQL；支持文本/视觉 AI、固定 Word 模板导出，以及按租户隔离的只读 REST API。

> 当前身份边界：UI 为固定身份的单用户模式，没有有效登录保护。PyInstaller 模式只监听本机；源码或 Docker 模式若暴露到网络，必须先增加可信网络边界或恢复认证。

## 当前能力

- 每日活动计划：学期/日期、教案拆分、年龄适配、活动生成、差异比对、Word 导出。
- 游戏观察：图片上传、视觉 AI、可编辑观察记录、历史和 Word 导出。
- 一对一倾听：五领域、指标、图片、历史、编辑、合并/分领域/批量导出。
- 自制教玩具：AI 生成、编辑、保存、历史和 Word 导出。
- 课程审议：教案拆分、审议调整、修订稿、历史、删除和 Word 导出。
- 配置中心：学期、班级、教师、文本/视觉 AI Key、提示词版本。
- 只读 API：`/api/v1`，API Key 必填，HMAC 可选，业务查询强制 `tenant_id`。

当前并未完成微服务拆分；`services/` 只是未来规划。实际运行单元为一个 NiceGUI 应用进程，外加可选 Caddy/MySQL。

## 已确认的下一能力：受控 AI Agent（尚未实现）

项目已接受 [ADR-0005](docs/ADR/ADR-0005-controlled-ai-agent-runtime.md)，下一功能方向是在每日活动
计划页面增加一个受控单 Agent。首阶段只有 4 个 READ Tool 和 2 个 DRAFT Tool：它可以读取当前计划、
班级/学期/日历的最小投影并生成字段级 `PlanPatch`，但不会修改表单正文、写数据库、保存对话或调用
文件、URL、SQL、MCP/插件。

这仍是设计状态，不属于上方“当前能力”。实现前必须先确认分支基线、补齐 Service 读取投影，并建立
稳定 RED。未来 Agent WRITE、多 Agent、长期记忆和无人值守 Workflow 均未获授权。

## 快速开始

```bash
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.main
```

浏览器访问 `http://localhost:8080`。首次运行会：

1. 解析 `.env` 与环境变量。
2. 在未设置 `DATABASE_URL` 时使用用户数据目录中的 SQLite。
3. 尝试执行 `alembic upgrade head`。
4. 创建固定的默认管理员记录。
5. 直接进入 `/home`。

建议先打开 `/settings` 配置学期、班级和教师，再打开 `/setup` 配置 AI 接口。

当前 Web 框架安全基线为 NiceGUI 3.16.0 + FastAPI 0.141.1 + Starlette 1.6.0。
其他 Dependabot 相关 Python 依赖下限、官方来源和验证方法见
[docs/DEPENDENCIES.md](docs/DEPENDENCIES.md)。

## 自动测试与迁移

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/alembic upgrade head
```

当前 Alembic head：`a6c4d8e2f9b1`。

仓库历史曾记录多次通过结果，但这些数字属于对应旧 SHA。本 README 不把历史数字当作当前验证；交付时应记录本次命令、SHA、平台和结果。

## 配置

| 变量 | 默认/边界 |
|---|---|
| `DATABASE_URL` | 留空使用 SQLite；MySQL 例：`mysql+aiomysql://...` |
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
docker compose up -d
```

当前 Compose 包含 Caddy、主应用和 MySQL。示例默认密码只适合本地试验；部署前必须在 `.env` 中覆盖，并限制 UI 网络访问。

开发 override：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## 架构速览

```text
NiceGUI UI / FastAPI-style API
            │
         service
        ├─ planned controlled Agent ── Agent Provider
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

`origin/dev3.4` 保留了 6 个尚未进入 `main` 的提交。开始 Agent 实现前，需先确认以 `main` 还是经审查后的 `dev3.4` 为基线，并为 READ/DRAFT Agent Foundation 建立 spec/Issue/稳定 RED；不要把 ADR、设计文档或保留分支自动视为主线已交付。
