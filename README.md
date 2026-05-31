# 幼儿园教学管理系统

> 「幼儿园信息管理系统」的子系统 —— 首期聚焦**教学管理 · 每日活动计划**的撰写、AI 辅助生成、Word 导出与云端存档。

基于 **Python 3.12+ / NiceGUI** 前后端一体化，**MySQL 8** 云端存储，接入 **OpenAI 兼容**大模型，实现从「教案输入 → AI 拆分 → 表单回填 → 年龄适配 → 差异比对 → 一日活动生成 → Word 导出 → 云端存档」的完整闭环，并对外提供只读 REST API 供主系统集成。

---

## 功能特性

- **账号与权限**：账号密码登录 + JWT + RBAC（教师 / 教研管理员 / 系统管理员）。
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

## 快速开始

```bash
# 1. 克隆并进入项目
cd kindergartenManager

# 2. 创建虚拟环境并安装依赖
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填写 DATABASE_URL / ENCRYPTION_KEY / JWT_SECRET / HOLIDAY_API_URL 等

# 4. 执行数据库迁移
.venv/bin/alembic upgrade head

# 5. 启动应用（默认 http://0.0.0.0:8080）
.venv/bin/python -m app.main

# 6. 运行测试
.venv/bin/pytest tests/ -q
```

> ⚠️ `ENCRYPTION_KEY` 与 `JWT_SECRET` 必须与生产环境保持一致，否则已加密的 AI Key 无法解密、已签发的 JWT 失效。

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `DATABASE_URL` | 是 | `mysql+aiomysql://user:pass@host:3306/db` |
| `ENCRYPTION_KEY` | 是 | AI Key 加密密钥（取前 32 字节构造 Fernet Key） |
| `JWT_SECRET` | 是 | JWT 签名密钥，同时用于 `app.storage.user` 加密 |
| `JWT_EXPIRE_MINUTES` | 否 | access token 有效期，默认 60 |
| `HOLIDAY_API_URL` | 是 | 中国法定节假日 API 地址 |
| `LOG_LEVEL` | 否 | 日志级别，默认 INFO |
| `API_KEYS` | 否 | 对外 API 鉴权，`"key:tenant_id"` 逗号分隔；为空则对外 API 关闭 |
| `API_SIGNING_SECRET` | 否 | 对外 API HMAC 签名密钥；非空时强制校验签名 |
| `API_SIGNATURE_MAX_SKEW` | 否 | 签名时间戳允许偏移秒数，默认 300 |

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
- 对外 API 参考：[docs/API.md](docs/API.md)

## 里程碑

| 里程碑 | 内容 | 状态 |
|--------|------|------|
| M1 | 原型联调（登录 + 日期 + AI 拆分） | ✅ |
| M2 | 首期闭环可用（完整教案流程 + Word 导出 + 云端存档） | ✅ |
| M3 | 稳定性与安全加固（异常处理 / 路由守卫 / 审计） | ✅ |
| M5（二期） | 对外 REST API + 数据库只读视图 | 🚧 API 已落地 |
