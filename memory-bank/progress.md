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

- 阶段 1（Step 1.1~1.6）全部完成，待用户手工验收 Step 1.6 登录页面后，开始阶段 2（Step 2.1 学期配置数据模型）。

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

## 2026-05-16

### 已完成

- **Step 1.1 ✅**：定义 `User` 数据模型 (`app/core/models/user.py`)，包含 id/tenant_id/username/hashed_password/role/is_active/created_at/updated_at 字段；生成并执行 Alembic 迁移 `5e03413fdeca`（add user table）。
  - 创建 `app/core/models/__init__.py` 导入所有 model，确保 alembic autogenerate 可发现。
  - 更新 `alembic/env.py` 导入 `app.core.models`。
  - `alembic current` 显示 `5e03413fdeca (head)`。
- **Step 1.2 ✅**：`app/auth/password.py` — `hash_password` / `verify_password`，使用 Argon2（passlib）。
  - `tests/test_password.py` — 5 passed。
  - ⚠️ **DeprecationWarning 备注（Python 升级预警）**：
    - `passlib/utils/__init__.py`：`import crypt` 在 Python 3.12 弃用，Python 3.13 将移除 `crypt` 标准库模块。届时需升级 passlib 至支持 Python 3.13 的版本，或直接改用 `argon2-cffi`。
    - `passlib/handlers/argon2.py`：`argon2.__version__` 已弃用，建议改用 `importlib.metadata`，升级 passlib 后可消除。
    - **当前影响**：无功能影响；待 Python 3.13 升级前跟进。
- **Step 1.3 ✅**：`app/core/exceptions.py` — 定义 `AuthError`；`app/auth/jwt.py` — `create_access_token` / `decode_access_token`，使用 `python-jose`（HS256），从 `Settings` 读取密钥与过期时间。
  - `tests/test_jwt.py` — 5 passed（正常解码字段、篡改签名报错、错误密钥报错、过期 token 报错、三种角色均可编解码）。
- **Step 1.4 ✅**：`app/repository/user_repository.py` — `create_user` / `get_user_by_username` / `get_user_by_id` / `update_password`，所有查询携带 `tenant_id` 隔离。
  - `tests/conftest.py` — 提供 `async_session` fixture（SQLite 内存库，每测试函数独立）。
  - `pytest.ini` — 设置 `asyncio_mode = auto`，支持异步测试无需逐函数标注。
  - 修复：`User.id` 使用 `BigInteger().with_variant(Integer, "sqlite")` 解决 SQLite 自增兼容问题。
  - 修复：`created_at` / `updated_at` 改用 `datetime.now(timezone.utc)` 替代已弃用的 `utcnow()`。
  - `tests/test_user_repository.py` — 6 passed，0 warnings（创建查询、租户隔离、ID 查询、跨租户隔离、不存在返回 None、更新密码）。
- **Step 1.5 ✅**：`app/service/auth_service.py` — `login` / `change_password`，调用仓库层与密码/JWT 工具。
  - 安全约定：`login` 对"用户不存在"与"密码错误"统一抛出 `AuthError`，防止用户枚举攻击。
  - `tests/test_auth_service.py` — 7 passed（正确凭证返回 token、错误密码报错、不存在用户报错、禁用账号报错、跨租户报错、改密后旧密码失效/新密码有效、旧密码错误不修改）。
  - ⚠️ **DeprecationWarning**（同 Step 1.2，passlib 已知问题，无功能影响）。
- **Step 1.6 ✅**：NiceGUI 登录页面与应用入口。
  - `app/ui/pages/login.py` — 路由 `/`，用户名/密码输入框（支持回车触发）、错误提示（红字）、登录成功存 token 并跳转 `/home`；首期 `tenant_id=1` 固定。
  - `app/ui/pages/home.py` — 路由 `/home`，占位主页，未登录自动跳回 `/`，含退出登录按钮。
  - `app/main.py` — 入口，注册页面路由，`ui.run()` 绑定 `storage_secret=JWT_SECRET`，`show=False` 适配服务器环境。

### 当前状态

- **阶段 1（Step 1.1~1.6）全部完成并通过手工验收。**
- 自动化测试：`23 passed`（test_password ×5、test_jwt ×5、test_user_repository ×6、test_auth_service ×7），2 个已知 passlib DeprecationWarning（无功能影响）。
- 登录页面手工验收通过：空输入提示、错误密码提示、正确登录跳转、未登录保护、退出登录均符合预期。

### 下一步

- 阶段 2（Step 2.1）：学期配置数据模型 `SemesterConfig`，生成并执行 Alembic 迁移。

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

