# 开发电脑迁移与环境清单

> 盘点日期：2026-08-31。本文用于在新电脑恢复 KindergartenManager 的开发能力。
> Git 只承载项目源码、文档和仓库级 Skills；认证、密钥、浏览器会话和运行数据必须走独立安全流程。

## 1. 可复现项目基线

| 类别 | 当前基线 | 权威来源 |
|---|---|---|
| Python | 开发、CI、Docker、Release 均使用 `3.14.7` | `.python-version`、Dockerfile、GitHub workflows |
| Python 依赖 | `uv.lock` revision 3，当前锁定 80 个包 | `pyproject.toml`、`uv.lock` |
| 兼容安装 | `requirements.txt` 记录安全下限，不是精确锁 | `requirements.txt`、`docs/DEPENDENCIES.md` |
| 数据库 | 本地默认 SQLite；Compose/生产使用 MySQL 8 | Alembic、`docker-compose.yml` |
| Web/UI | NiceGUI、FastAPI、Uvicorn | 锁文件与 requirements |
| 文档/图片 | python-docx、Pillow、lxml | 锁文件与 requirements |
| 质量 | pytest、pytest-asyncio；CI 另装 Ruff `0.15.22`、pip-audit `2.10.1` | `quality.yml` |
| 容器发布 | Docker、Compose v2、Buildx、QEMU；双平台 `amd64/arm64` | `release.yml` |
| 桌面发布 | PyInstaller；Windows 另需 Inno Setup 6，Linux 另需 gcc、dpkg-dev | Release workflow、打包脚本 |

本机盘点时的辅助工具版本为：uv `0.11.30`、Docker `29.7.2`、Compose `5.5.0`、
Git `2.43.0`、GitHub CLI `2.98.0`、Graphify `0.9.48`、codebase-memory-mcp `0.9.0`、
CodeGraph `1.2.0`、ripgrep `14.1.0`、fd `9.0.0`、ast-grep `0.45.1`、Node.js `26.5.0`
和 Codex CLI `0.149.0`。这些是迁移参考，不应误写成应用运行时依赖。

关键依赖文件：

- `.python-version`：审查运行时版本。
- `pyproject.toml`：直接依赖集合和 Python 兼容下限。
- `uv.lock`：唯一精确 Python 锁定快照。
- `requirements.txt`：现有 CI、Docker 和 Release 使用的安全下限安装入口。
- `docs/DEPENDENCIES.md`：安全基线、升级策略和历史验证记录。
- `Dockerfile`、`docker-compose*.yml`：容器构建与运行拓扑。
- `.github/workflows/quality.yml`、`release.yml`：质量与发布工具链。

当前尚未完全收敛的依赖风险：CI、Docker 和 Release 仍通过 `requirements.txt` 安装，未直接消费
`uv.lock`；Caddy/MySQL 镜像、PyInstaller、Inno Setup 和部分 GitHub Actions 仍使用浮动版本；
`kindergartenManager.spec` 还需单独核查已从依赖中移除的 `jose` hidden imports。应分别建 Issue
处理，不在换机时顺手改变发布行为。

## 2. 仓库级 Skills 与规则

以下内容已被 Git 跟踪，克隆仓库即可恢复：

- `.agents/skills/codebase-memory/`：结构、调用链和影响分析；优先使用 MCP 图谱查询。
- `.agents/skills/graphify/`：代码与文档语义图谱工作流，仓库版本为 `0.9.48`。
- `AGENTS.md`：本仓库开发、安全、验证、多 Agent 与生产交付约束。
- `.github/instructions/ai-integration.instructions.md`：AI integration/service 路径规则。
- `.github/instructions/database.instructions.md`：数据库、Repository、Alembic 和租户隔离规则。
- `.github/instructions/word-export.instructions.md`：Word 模板与导出规则。
- `.codebase-memory/`：已提交的结构图快照；换机后仍应按当前 checkout 刷新索引。

`graphify-out/` 同时可能含有经过审查并被 Git 跟踪的图谱产物，以及未审查的缓存、旧电脑绝对路径和
运行期记忆。前者随 clone 恢复；不要手工搬运整个旧目录，也不要把后者新增到 Git。在新电脑安装相同
Graphify 版本后，从当前源码重新提取、诊断和验证。仓库 Skills 以 `.agents/skills/` 为唯一副本，
不要再复制到项目内 `.codex/skills/`。

## 3. 用户级与系统级 Skills

这些能力不在项目 Git 中，需在新电脑通过可信安装源重新安装，或通过加密备份恢复自有配置。

### 3.1 用户级工程 Skills

当前 `/home/admin/.agents/skills/` 共 34 项：

```text
ask-matt                 claude-handoff              code-review
codebase-design          codebase-memory              diagnosing-bugs
domain-modeling          find-skills                  git-guardrails-claude-code
graphify                 grill-me                     grill-with-docs
grilling                 handoff                      implement
improve-codebase-architecture  loop-me                migrate-to-shoehorn
prototype                research                     resolving-merge-conflicts
scaffold-exercises       setup-matt-pocock-skills     setup-pre-commit
setup-ts-deep-modules    tdd                          teach
to-spec                  to-tickets                   triage
wayfinder                writing-beats                writing-fragments
writing-shape
```

本项目最相关的是 `codebase-memory`、`graphify`、`code-review`、`diagnosing-bugs`、
`domain-modeling`、`tdd`、`research`、`to-spec`、`to-tickets`、`implement` 和
`resolving-merge-conflicts`。`~/.codex/skills` 中多数只是指向这些目录的符号链接，不要重复备份两份。

### 3.2 Codex 系统、插件与自定义 Agent

- Codex 系统 Skills：`imagegen`、`openai-docs`、`plugin-creator`、`review-agent`、
  `skill-creator`、`skill-installer`；应随 Codex 安装恢复。
- 本项目常用插件能力：browser、Chrome、documents、template-creator、visualize；站点、PDF、
  presentations、spreadsheets 等按需重装。
- 自定义 Agent 配置位于 `~/.codex/agents/`：`luna-worker.toml`、`reviewer.toml`、
  `spark_explorer.toml`、`spark_worker.toml`。
- `~/.codex/config.toml` 还包含多 Agent、MCP 和插件启用状态。只迁移人工审查后的配置骨架，
  到新电脑后重新认证并逐项验证。

不要复制 Codex/plugin cache 或市场快照来代替安装；缓存体积大、可能含旧路径，而且不能证明插件仍可用。

## 4. 新电脑恢复步骤

1. 安装 Git、GitHub CLI、Python `3.14.7`、uv、Docker Engine/Compose v2、Codex CLI。
2. 安装 Graphify `0.9.48`、codebase-memory MCP，并安装 `rg`、`fd`、`ast-grep`。
   Linux 上 `sg` 可能是切换用户组命令，结构搜索应明确使用 `ast-grep`。
3. 重新认证 GitHub、Codex 和所需浏览器/插件；不要复制旧会话文件。
4. 克隆并恢复当前开发分支：

   ```bash
   git clone https://github.com/ywyz/kindergartenManager.git
   cd KindergartenManager
   git fetch --all --prune --tags
   git switch feat/agent-write
   git pull --ff-only
   ```

5. 创建精确依赖环境并检查：

   ```bash
   uv sync --locked --all-groups
   uv lock --check
   uv pip check
   ```

6. 在 Linux/WSL/macOS 使用一次性 SQLite 验证迁移，避免误读 `.env` 后连接生产或旧开发库：

   ```bash
   workstation_db_dir="$(mktemp -d)"
   trap 'rm -rf -- "$workstation_db_dir"' EXIT
   workstation_database_url="sqlite+aiosqlite:///$workstation_db_dir/workstation.sqlite3"
   DATABASE_URL="$workstation_database_url" .venv/bin/python -m alembic upgrade head
   DATABASE_URL="$workstation_database_url" .venv/bin/python -m alembic current
   .venv/bin/python -m pytest tests/ -q
   ```

   Windows PowerShell 应使用系统临时目录创建等价的独立数据库路径，不要直接照抄上述 POSIX
   `mktemp`/`trap`。验证命令和 `DATABASE_URL` 隔离要求保持相同。

7. 按新 checkout 刷新 codebase-memory 与 Graphify；验证版本、来源覆盖和完整性，不以退出码 `0`
   单独判定成功。
8. 需要本地业务数据或真实集成时，再从加密备份恢复非生产配置，并重新完成登录、AI、Word 和浏览器验收。

## 5. 不得进入 Git 的迁移物

- `.env`、`.kindergarten_secrets`、API Key、Token、`auth.json`、浏览器 Cookie/会话。
- 生产 Bootstrap 管理员密码及其备份；生产密码继续只保留在受控服务器 owner-only 文件中。
- `.venv`、Codex plugin cache、未审查的 Graphify cache、临时数据库、测试输出。
- 未经授权的真实 SQLite/MySQL 数据、幼儿照片、Word 导出和日志。

如确需迁移非生产数据库与 AI 配置，数据库密文必须与原 `ENCRYPTION_KEY` 成对、加密传输并在新电脑
恢复 owner-only 权限；不得经 Issue、聊天、提交或普通剪贴板传递。

## 6. 换机前后验收清单

换机前：

- [ ] `git fetch --all --prune --tags` 已执行。
- [ ] 当前分支所有可交付修改已提交并推送，远端分支 SHA 已回读。
- [ ] 未把 Graphify 缓存、密钥、认证或运行数据混入提交。
- [ ] 用户级 Skills、自定义 Agent 和经审查的配置骨架已有加密备份或重装清单。

换机后：

- [ ] 当前分支与远端 SHA 一致，`git log --branches --not --remotes` 无输出。
- [ ] Python、uv、Graphify 和仓库 Skill 版本符合本文基线。
- [ ] `uv lock --check`、`uv pip check`、全新 SQLite 迁移和 pytest 通过。
- [ ] MCP、Graphify、luna/reviewer/spark 路由均经过实际调用验证。
- [ ] 真实浏览器、Word/Office、MySQL 和发布工具按本次开发范围另行验收。
