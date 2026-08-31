# 开发电脑迁移与环境清单

> 盘点日期：2026-08-31。本文把“官方最新版”“本机已安装”和“仍被阻塞”分开记录，避免把
> 一个版本号同时当成项目锁定版本、CI 版本或本机状态。版本以本日期能够从官方发布渠道回读的结果为准。
> Git 只承载项目源码、文档和仓库级 Skills；认证、密钥、浏览器会话和运行数据必须走独立安全流程。

## 1. 可复现项目基线

| 类别 | 项目基线 | 权威来源 |
|---|---|---|
| Python | `3.14.7`；`.venv` 由 uv 管理 | `.python-version`、Dockerfile、GitHub workflows |
| Python 依赖 | `uv.lock` revision 3，当前锁定 80 个包 | `pyproject.toml`、`uv.lock` |
| 兼容安装 | `requirements.txt` 记录安全下限，不是精确锁 | `requirements.txt`、`docs/DEPENDENCIES.md` |
| 数据库 | 本地默认 SQLite；Compose/生产使用 MySQL 8 | Alembic、`docker-compose.yml` |
| Web/UI | NiceGUI、FastAPI、Uvicorn | 锁文件与 requirements |
| 文档/图片 | python-docx、Pillow、lxml | 锁文件与 requirements |
| 质量 | pytest、pytest-asyncio；本机 Ruff `0.16.5`、pip-audit `2.10.1` | `pyproject.toml`、`quality.yml` |
| 容器发布 | Docker、Compose v2、Buildx；CI 构建 `linux/amd64` 与 `linux/arm64` | `release.yml` |
| 桌面发布 | PyInstaller；Windows 另需 Inno Setup 6，Linux 另需 gcc、dpkg-dev | Release workflow、打包脚本 |

CI 当前仍显式安装 Ruff `0.15.22`，而本机已更新到官方最新版 `0.16.5`；这两个版本不要混写。
若要让 CI 也跟随最新版，需要单独修改 workflow 并回读精确 SHA 结果。CI、Docker 和 Release 仍通过
`requirements.txt` 安装，未直接消费 `uv.lock`；这也是待单独收敛的可复现性差异。

### 1.1 2026-08-31 官方最新版、本机状态与阻塞项

| 工具/能力 | 官方最新版 | 本机已安装/状态 | 结论 |
|---|---:|---|---|
| Python | `3.14.7` | uv 管理的项目解释器与 `.venv` 为 `3.14.7` | 已满足 |
| uv / uvx | `0.12.7` | `0.12.7` | 已满足 |
| Node.js | `v26.8.1` | NVM 已安装 `v26.8.1`（随附 npm `11.19.0`），官方 SHA-256 校验通过；`default -> 26` 当前解析到该版本 | 已满足；本次使用官方预编译包，未编译 |
| Git | `2.53.0` | `2.53.0` | 已满足 |
| GitHub CLI | `2.98.0` | `2.98.0` | 已满足 |
| ripgrep | `15.2.0` | `15.2.0` | 已满足 |
| fd | `10.5.0` | `10.5.0` | 已满足 |
| ast-grep | `0.45.3` | `0.45.3` | 已满足 |
| Ruff | `0.16.5` | `0.16.5` | 已满足（CI 另有旧 pin） |
| pip-audit | `2.10.1` | `2.10.1` | 已满足 |
| PyInstaller | `6.22.2` | `6.22.2` | 已满足 |
| Docker Engine | `29.7.2` | `29.7.2` | 已满足 |
| Docker Compose | `5.5.0` | `5.5.0` | 已满足 |
| Docker Buildx | `0.36.1` | `0.36.1` | 已满足 |
| Graphify | `0.9.53` | 全局与仓库 Skill 均已同步 `0.9.53` | 已满足；需按当前 checkout 重提取 |
| codebase-memory-mcp | `0.10.8` | `0.10.8`；Codex MCP 配置已更新 | 已满足；当前仓库已重建索引 |
| CodeGraph | `1.6.0` | `1.6.0`；当前仓库已初始化 | 已满足；本地数据库不入 Git |
| Codex CLI | `0.151.0` | npm PATH 为 `0.151.0` | 已满足；VS Code 内置 alpha 副本不在 PATH 首位 |
| QEMU/binfmt | CI 通过 `setup-qemu-action` 配置 | `tonistiigi/binfmt` 已注册 arm64，并以 Alpine aarch64 容器验证 | 已满足本地跨架构运行；仍需按目标镜像单独验收 |
| 浏览器控制 | Chrome/Edge 浏览器插件 | 可导航；Chrome 扩展与 Native Host 诊断通过，但 DOM 状态通道超时 | 阻塞语义控制；按官方指引从 ChatGPT 插件 UI 重装 Browser 插件 |

浏览器仍是阻塞项；Node 与 QEMU/binfmt 已满足。浏览器 Native Host 不应由本机
脚本自行改写；重装插件后再用浏览器工具验证导航、DOM 读取、点击、输入和截图。生产密码、真实 AI Key
和浏览器会话不属于这份清单。

关键依赖文件：

- `.python-version`：审查运行时版本。
- `pyproject.toml`：直接依赖集合和 Python 兼容下限。
- `uv.lock`：唯一精确 Python 锁定快照。
- `requirements.txt`：现有 CI、Docker 和 Release 使用的安全下限安装入口。
- `docs/DEPENDENCIES.md`：安全基线、升级策略和本次锁刷新记录。
- `Dockerfile`、`docker-compose*.yml`：容器构建与运行拓扑。
- `.github/workflows/quality.yml`、`release.yml`：质量与发布工具链。

## 2. 仓库级 Skills、图谱与规则

以下内容已被 Git 跟踪，克隆仓库即可恢复：

- `.agents/skills/codebase-memory/`：结构、调用链和影响分析；优先使用 MCP 图谱查询。
- `.agents/skills/graphify/`：代码与文档语义图谱工作流；仓库版本为 `0.9.53`。
- `AGENTS.md`：本仓库开发、安全、验证、多 Agent 与生产交付约束；本次审计未发现需要修改之处。
- `.github/instructions/`：AI integration、数据库和 Word 导出路径规则。
- `.codebase-memory/`：当前 checkout 的结构图快照；换机后应重建，不能把旧图当作当前事实。
- `.codegraph/.gitignore`：CodeGraph 本地数据库忽略规则；数据库本体不应提交。

本次已更新并验证 Graphify `0.9.53`、codebase-memory-mcp `0.10.8` 和 CodeGraph `1.6.0`。Graphify
与 codebase-memory 的输出会随源码和文档变化；先检查来源覆盖、端点和完整性诊断，再把结果用于导航，
不能用生成图谱替代实际代码、迁移、测试或人工验收。仓库 Skills 以 `.agents/skills/` 为唯一副本，
不要再复制到项目内 `.codex/skills/`。

## 3. Codex、用户 Skills 与 Agent 配置

### 3.1 Codex 系统与插件能力

- Codex CLI 当前为 `0.151.0`；npm 安装位于 PATH 首位。VS Code 的内置 alpha 版本只作为编辑器集成，
  不作为 shell 的 CLI 来源；当前没有活动的 `CODEX_CLI_PATH` 覆盖，因此没有 PATH 冲突。
- `~/.codex/skills/` 只保留 Codex 系统目录及已安装的项目相关 Skill；仓库 Skill 仍以 `.agents/skills/`
  为准。插件缓存不是安装证明，不应复制或提交。
- `~/.codex/agents/` 中的 `luna_worker`、`reviewer`、`spark-explorer`、`spark-worker` 以及
  codebase-memory 辅助 Agent 配置按需使用；Agent 配置和认证文件均不进入 Git。
- 浏览器控制能力属于 Browser/Chrome 插件。当前“可导航但 DOM 通道超时”的状态必须在插件 UI 重装后
  重新验收，不能通过手工修改 Native Host 绕过。

### 3.2 迁移原则

不要硬编码其他机器（例如 `/home/admin`）的路径或 Skills 数量。迁移时以当前用户的 `~/.codex/`、
仓库 `.agents/skills/` 和本节的工具版本表为准；旧缓存、旧绝对路径、旧会话和旧 Agent 分支都不是安装证明。

## 4. 新电脑恢复步骤

1. 安装 Git、GitHub CLI、Python `3.14.7`、uv、Docker Engine/Compose v2 和 Codex CLI；按表格核对官方最新版。
2. 安装 Graphify `0.9.53`、codebase-memory-mcp `0.10.8`、CodeGraph `1.6.0`，再安装 `rg`、`fd`、
   `ast-grep`。Linux 上 `sg` 可能是切换用户组命令，结构搜索应明确使用 `ast-grep`。
3. 重新认证 GitHub、Codex 和所需浏览器/插件；不要复制旧会话文件。
4. 克隆并恢复默认分支或经审查的开发分支：

   ```bash
   git clone https://github.com/ywyz/kindergartenManager.git
   cd kindergartenManager
   git fetch --all --prune --tags
   git switch main
   git pull --ff-only
   ```

5. 创建精确依赖环境并检查：

   ```bash
   uv python install 3.14.7
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

7. 按新 checkout 刷新 codebase-memory、Graphify 和 CodeGraph；Graphify 语义提取遵循仓库规定的
   `openai → deepseek → luna_worker` 顺序，并验证版本、来源覆盖和完整性，不以退出码 `0` 单独判定成功。
8. 需要本地业务数据或真实集成时，再从加密备份恢复非生产配置，并重新完成登录、AI、Word、MySQL 和浏览器验收。
9. 若要本地构建双架构镜像，先安装与 Docker Buildx 匹配的 QEMU/binfmt；否则仅使用 CI 的 QEMU action。

## 5. 不得进入 Git 的迁移物

- `.env`、`.kindergarten_secrets`、API Key、Token、`auth.json`、浏览器 Cookie/会话。
- 生产 Bootstrap 管理员密码及其备份；生产密码继续只保留在受控服务器 owner-only 文件中。
- `.venv`、Codex plugin cache、本地 Graphify/CodeGraph/CBM 数据库、临时数据库、测试输出。
- 未经授权的真实 SQLite/MySQL 数据、幼儿照片、Word 导出和日志。

如确需迁移非生产数据库与 AI 配置，数据库密文必须与原 `ENCRYPTION_KEY` 成对、加密传输并在新电脑
恢复 owner-only 权限；不得经 Issue、聊天、提交或普通剪贴板传递。

## 6. 换机前后验收清单

换机前：

- [ ] `git fetch --all --prune --tags` 已执行。
- [ ] 当前分支所有可交付修改已提交并推送，远端分支 SHA 已回读。
- [ ] 未把 Graphify/CBM/CodeGraph 缓存、密钥、认证或运行数据混入提交。
- [ ] Codex Agent 配置、项目 Skills 和经审查的配置骨架已有加密备份或重装清单。

换机后：

- [ ] 当前分支与远端 SHA 一致，`git log --branches --not --remotes` 无输出。
- [ ] Python、uv、Graphify、codebase-memory-mcp、CodeGraph 和仓库 Skill 版本符合本文基线。
- [ ] `uv lock --check`、`uv pip check`、全新 SQLite 迁移和 pytest 通过。
- [ ] MCP、Graphify 和 CodeGraph 均针对当前 checkout 查询/刷新并通过完整性检查。
- [ ] `nvm use 26.8.1` 后 `node --version` 显示 `v26.8.1`、`npm --version` 显示随附的 `11.19.0`；本次使用官方预编译包且 SHA-256 匹配，未编译。
- [ ] QEMU/binfmt 已注册并用目标架构容器验证；正式发布仍须运行对应镜像验收。
- [ ] 浏览器能导航、读取 DOM、点击、输入和截图；若只可导航且 DOM 超时，先从 ChatGPT 插件 UI 重装 Browser 插件。
- [ ] 真实浏览器、Word/Office、MySQL 和发布工具按本次开发范围另行验收。
