# 进度记录

## 2026-05-10

### 已完成

- 完成 memory-bank 文档全量阅读与一致性检查。
- 收敛 9 项需求澄清并写入实施计划。
- 已将关键规则固化到 architecture.md 初始化版本。
- 已确认模板文件存在：`templates/teacherplan.docx`。
- 已最终确认 `is_holiday` 返回语义：法定节假日 True、工作日 False；周末独立额外判定。
- **Step 0.1 ✅**：创建标准目录结构与 Python 包初始化文件，创建 `.gitignore`。
  - 目录：`app/ui`, `app/api`, `app/service`, `app/repository`, `app/integration/{ai_client,holiday_client,word_export}`, `app/auth`, `app/core`, `app/jobs`, `alembic`, `tests`, `exports`
  - 每目录含 `.gitkeep`，所有 Python 包目录含空 `__init__.py`（共 13 个）
  - 验证：`find app tests alembic exports -type d | sort` 输出完整；`python3 -c "import app.core; import app.service; import app.auth"` 无报错
- **Step 0.2 ✅**：创建 `requirements.txt`，建立 `.venv`（Python 3.12），安装全部依赖。
  - 依赖包含：nicegui, fastapi, uvicorn, sqlalchemy[asyncio], aiomysql, pymysql, alembic, pydantic-settings, passlib[argon2], python-jose, cryptography, httpx, tenacity, python-docx, apscheduler, python-json-logger, pytest, pytest-asyncio, aiosqlite
  - 创建 `.env.example` 列出所有配置占位符
- **Step 0.3 ✅**：`app/core/config.py` — `pydantic-settings` Settings 类，读取 DATABASE_URL/ENCRYPTION_KEY/JWT_SECRET/JWT_EXPIRE_MINUTES/HOLIDAY_API_URL/LOG_LEVEL；`.env` 复制自 `.env.example`
- **Step 0.4 ✅**：`app/core/logging.py` — JSON 结构化日志，`get_logger(name)` 函数，字段含 timestamp/level/logger/message
- **Step 0.5 ✅**：`app/core/database.py` — `AsyncEngine`、`AsyncSessionLocal`、`Base`、`get_async_session()`；Alembic 初始化并配置 `env.py` 读取 Settings.DATABASE_URL（迁移用 pymysql 同步驱动）

### 当前状态

- 阶段状态：阶段 0（Step 0.1~0.5）全部完成，阶段 1（Step 1.1 账号数据模型）待开始。
- 文档状态：PRD、implementation-plan、architecture 已具备可执行基线。

### 下一步

- Step 1.1：定义 User 数据模型，生成并执行 Alembic 迁移（需真实 MySQL 连接）。

### 风险与备注

- Word 导出必须严格按模板结构实现，禁止自行重排结构。
- 节假日逻辑包含“法定节假日前一天”和“不放假节日标签”两个维度，需提前设计接口返回模型。
- 权限可见性含“同班可见、跨班不可见”，后续数据查询层要预留班级维度过滤。

## 2026-05-11

### 已完成

- 新增 Step 0 自动化测试文件：`tests/conftest.py`、`tests/step0/test_bootstrap.py`、`tests/step0/test_config.py`、`tests/step0/test_logging.py`、`tests/step0/test_database.py`。
- 保留人工验收清单：`tests/step0/pytest_checklist.md`。
- 已执行 Step 0 窄范围测试：`.venv/bin/pytest tests/step0 -q`。
- 测试结果：`18 passed, 1 warning in 2.06s`。
- 新增 `memory-bank/testing.md`，记录测试说明、覆盖范围、执行命令与最近一次测试情况。

### 当前状态

- 阶段状态不变：阶段 0 已完成并具备自动化回归基线；阶段 1（Step 1.1 账号数据模型）待开始。

### 风险与备注

- 当前 warning 来自第三方库 `python-json-logger` 的弃用提示，不影响 Step 0 结论。
- Step 0 的数据库测试暂不依赖真实 MySQL，仅验证结构与迁移接线；后续阶段需增加真实迁移与仓库层集成测试。

## 2026-05-14

### 已完成

- 用户按顺序完成 Step 0 手工验收：Step 0.1~0.5 全部通过。
- 处理并修复 Alembic 在 `DATABASE_URL` 包含 URL 编码字符（如 `%40`）时的插值报错：
  - 报错现象：`ValueError: invalid interpolation syntax ...`
  - 根因：Alembic 底层 `configparser` 将 `%` 解释为插值占位符。
  - 修复方式：在 `alembic/env.py` 写入 `sqlalchemy.url` 前将 `%` 转义为 `%%`。
- 修复后复测：`alembic current` 正常执行；当前 `alembic/versions/` 为空时不显示迁移版本属预期行为。

### 当前状态

- 阶段状态：阶段 0 完整通过并可复现；阶段 1 仍未开始（按用户要求等待进一步指令）。

### 风险与备注

- 连接串中若包含 `@`、`%` 等特殊字符，需做 URL 编码；并保留 Alembic `% -> %%` 转义逻辑。

