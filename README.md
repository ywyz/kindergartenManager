# 幼儿园教学管理系统

> 「幼儿园信息管理系统」的子系统 —— 首期聚焦**教学管理 · 每日活动计划**的撰写、AI 辅助生成、Word 导出与云端存档。

基于 **Python 3.12+ / NiceGUI** 前后端一体化，**MySQL 8** 云端存储，接入 **OpenAI 兼容**大模型，实现从「教案输入 → AI 拆分 → 表单回填 → 年龄适配 → 差异比对 → 一日活动生成 → Word 导出 → 云端存档」的完整闭环，并对外提供只读 REST API 供主系统集成。

---

## 功能特性

- **账号与权限**：账号密码登录 + JWT + RBAC（教师 / 教研管理员 / 系统管理员）。
- **账号管理（阶段二）**：系统管理员账号初始化脚本、账号创建、启停、重置密码、筛选分页。
- **学期与日期**：学期起止配置，自动计算第几周、周几、工作日 / 法定节假日（带缓存与降级）。
- **教案 AI 拆分**：粘贴整篇教案，一键拆分为活动目标 / 准备 / 重点 / 难点 / 过程并回填表单。
- **年龄适配与差异比对**：按年龄段改写「活动过程」，原文与改写文逐句比对，导出时差异标红。
- **一日活动一键生成**：结合教学周、是否临近节假日、班级区域等上下文，并发生成晨间活动 / 晨间谈话 / 区域游戏 / 户外游戏。
- **提示词管理**：7 类任务的提示词多版本保存、启停与回滚。
- **Word 导出**：严格按模板 `templates/teacherplan.docx` 填充单元格，差异内容红字标注（宋体）。
- **对外只读 REST API**：`/api/v1` 暴露教学计划数据，API Key + 可选 HMAC 签名鉴权（详见 [docs/API.md](docs/API.md)）。
- **安全**：AI Key 应用层加密入库 + 脱敏展示；密码 Argon2；关键操作审计日志；全局异常结构化记录。

## 技术栈

| 层 | 选型 |
|----|------|
| 语言 | Python 3.12+（开发环境 3.14） |
| 前后端 | NiceGUI（底层 FastAPI / Starlette） |
| 数据库 | MySQL 8（async：SQLAlchemy 2 + aiomysql）；迁移：Alembic |
| 鉴权 | JWT（python-jose）+ Argon2（argon2-cffi）+ RBAC |
| 加密 | Fernet（cryptography）—— AI Key 入库加密 |
| AI | OpenAI 兼容 Chat Completions（httpx + tenacity 重试） |
| 文档导出 | python-docx |
| 测试 | pytest + pytest-asyncio（SQLite 内存库隔离） |

## 安装

### Windows（推荐：安装向导）

1. 从 [Releases](https://github.com/ywyz/kindergartenManager/releases) 下载 `KindergartenManager-Setup-*.exe`
2. 双击运行安装向导
3. 从开始菜单或桌面启动，浏览器自动打开 http://localhost:8080
4. 访问 http://localhost:8080/setup 创建管理员账号

**零配置**：首次启动自动使用内嵌 SQLite，无需配置数据库。

### Ubuntu/Debian（推荐：.deb 安装包）

```bash
sudo dpkg -i kindergarten-manager_*.deb
# 服务自动启动，访问 http://localhost:8080/setup
```

配置文件：`/etc/kindergarten-manager/env`（首次安装自动生成随机密钥）

```bash
systemctl status kindergarten-manager   # 查看服务状态
journalctl -u kindergarten-manager -f   # 实时日志
```

### Docker（服务器部署）

```bash
# 克隆仓库后
docker compose up -d
```

或使用镜像：
```bash
docker pull ghcr.io/ywyz/kindergartenmanager:latest
```

### 源码运行（开发/自定义部署）

```bash
# 1. 克隆并进入项目
cd kindergartenManager

# 2. 创建虚拟环境并安装依赖
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. 配置环境变量（可选，留空使用 SQLite 零配置）
cp .env.example .env
# 如需 MySQL：编辑 .env，填写 DATABASE_URL / ENCRYPTION_KEY / JWT_SECRET

# 4. 启动应用（默认 http://0.0.0.0:8080）
.venv/bin/python -m app.main
# 首次启动自动执行数据库迁移，访问 /setup 创建管理员账号

# 5. 运行测试
.venv/bin/pytest tests/ -q
```

> ⚠️ **生产环境**：请在 `.env` 中显式配置 `ENCRYPTION_KEY` 和 `JWT_SECRET`，避免重启后密钥变化导致数据无法解密。

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `DATABASE_URL` | 否 | 留空使用内嵌 SQLite；MySQL：`mysql+aiomysql://user:pass@host:3306/db` |
| `ENCRYPTION_KEY` | 推荐 | AI Key 加密密钥；留空自动生成并持久化到 `.kindergarten_secrets` |
| `JWT_SECRET` | 推荐 | JWT 签名密钥；留空自动生成并持久化 |
| `JWT_EXPIRE_MINUTES` | 否 | access token 有效期，默认 60 |
| `HOLIDAY_API_URL` | 否 | 中国法定节假日 API，默认 timor.tech |
| `LOG_LEVEL` | 否 | 日志级别，默认 INFO |
| `API_KEYS` | 否 | 对外 API 鉴权，`"key:tenant_id"` 逗号分隔；为空则接口关闭 |
| `API_SIGNING_SECRET` | 否 | 对外 API HMAC 签名密钥；非空时强制校验签名 |
| `BOOTSTRAP_ADMIN_ENABLED` | 否 | 允许脚本方式初始化管理员，默认 false |
| `BOOTSTRAP_ADMIN_PASSWORD` | 否 | 脚本方式初始化时的管理员密码 |

## 目录结构

```
app/
  ui/            NiceGUI 页面与组件
  api/           对外只读 REST API（二期）
  service/       业务逻辑（拆分编排、年龄适配、差异、日期、生成、登录）
  repository/    数据访问层（强制 tenant_id 过滤）
  integration/   ai_client / holiday_client / word_export
  auth/          JWT、密码、RBAC、路由守卫中间件
  core/          配置、日志、数据库、异常、加密、审计、ORM 模型
  jobs/          定时任务（预留）
alembic/         数据库迁移
tests/           pytest 测试
templates/       Word 模板（teacherplan.docx）
docs/            开发者文档与 API 参考
memory-bank/     项目文档（PRD、技术栈、计划、架构、进度）
```

## 文档

- 产品需求：[memory-bank/PRD.md](memory-bank/PRD.md)
- 技术选型：[memory-bank/tech-stack.md](memory-bank/tech-stack.md)
- 架构说明：[memory-bank/architecture.md](memory-bank/architecture.md)
- 开发者指南：[docs/DEVELOPER.md](docs/DEVELOPER.md)
- 手动测试文档：[docs/MANUAL_TESTING.md](docs/MANUAL_TESTING.md)
- 对外 API 参考：[docs/API.md](docs/API.md)

## 里程碑

| 里程碑 | 内容 | 状态 |
|--------|------|------|
| M1 | 原型联调（登录 + 日期 + AI 拆分） | ✅ |
| M2 | 首期闭环可用（完整教案流程 + Word 导出 + 云端存档） | ✅ |
| M3 | 稳定性与安全加固（异常处理 / 路由守卫 / 审计） | ✅ |
| M5（二期） | 对外 REST API + 数据库只读视图 | 🚧 API 已落地 |
