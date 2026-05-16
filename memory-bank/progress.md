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

- 阶段 2（Step 2.1 学期配置数据模型）。

## 2026-05-16（续）

### 已完成（阶段 2）

- **Step 2.1 ✅**：`app/core/models/semester.py` — `SemesterConfig` 模型；Alembic 迁移 `fd6d29f921b4`；手工验收通过（DESCRIBE semester_config 字段与定义一致）。
- **Step 2.2 ✅**：`app/core/models/class_config.py` — `ClassConfig` 模型；Alembic 迁移 `67b4aef28796`；手工验收通过。
- **Step 2.3 ✅**：`app/service/date_service.py` — 纯函数：`get_week_number`、`get_weekday_cn`、`is_workday`、`is_within_semester`；`tests/test_date_service.py` 19 passed，0 warnings。
- **Step 2.4 ✅**：`app/integration/holiday_client/client.py` — `is_holiday`、`is_near_holiday`、`get_holiday_name`、`get_special_day_tags`、`is_adjusted_workday`；缓存结构最终为 `tuple[bool, str | None, int]`（bool=法定节假日, str=节日名称, int=day_type）；`tests/test_holiday_client.py` 29 passed。
- **Step 2.5 ✅**：`app/repository/semester_repository.py`、`app/repository/class_repository.py`、`app/ui/pages/settings.py`（路由 `/settings`）；手工验收通过（数据持久化、刷新回填正常；tenant_id/user_id 字段正确；MySQL 中文存储正确，CLI 显示 `?` 属终端字符集问题，非数据问题）。
- **Step 2.6 ✅**：`app/ui/components/date_panel.py` — 可复用日期面板组件；`app/ui/pages/date_test.py`（路由 `/date-test`）；手工验收通过。

### 新增需求记录（2026-05-16）

- **需求 1**：节假日客户端在返回 `is_holiday=True` 时，额外返回具体节日名称（如"国庆节"、"春节"）。
- **实现 1**：
  - 内存缓存结构从 `dict[str, bool]` 升级为 `dict[str, tuple[bool, str | None, int]]`（后续需求3追加存储 day_type），`is_holiday` 在填充缓存时同时存储节日名称与 day_type。
  - 名称解析优先级：`holiday.name`（API 返回的 holiday 对象）→ `type.name`（API 返回的 type 对象）。
  - 新增 `get_holiday_name(target_date, *, _transport) -> str | None` 函数，复用缓存，同一日期不发额外 HTTP 请求。
  - `DatePanel` 组件更新：法定节假日提示文字从"今天是法定节假日"变为"今天是法定节假日（国庆节）"。
- **测试 1**：`TestGetHolidayName` 7 项测试全部通过（节日对象名称、type 名称降级、工作日/周末返回 None、API 失败 None、缓存复用、多节日名称正确）。

- **需求 2**（已回滚，记入 BL-01）：`get_special_day_tags` 曾计划支持在线 API 动态获取，但评估后代价大于收益，已回滚至本地硬编码同步实现。`get_special_day_tags` 保持 sync，不依赖外部 API，不需要 `SPECIAL_DAY_API_URL` 配置项。

- **Bug 修复 — 调班工作日（type=3）显示错误**：
  - 现象：2026-05-09（周六，调班补班）选择后显示"今天是周末（非工作日）"，未能识别调班工作日。
  - 根因：`is_workday()` 是纯日历函数（周一～周五判断），不知道调班信息；`is_holiday()` 对 type=3 返回 False（正确），但无函数能检测 type=3。
  - 修复：
    - 缓存三元组追加 day_type（第3位 int）：`dict[str, tuple[bool, str | None, int]]`。
    - 新增 `is_adjusted_workday(target_date, *, _transport=None) -> bool | None`：type=3 返回 True，复用法定节假日缓存，同日期不重复发 HTTP 请求。
    - `DatePanel._update_info` 在"非工作日"分支优先检查是否调班：调班工作日显示蓝色"今天是调班工作日，需正常上班"；普通周末保持橙色提示。
  - 测试：新增 `TestIsAdjustedWorkday` 6 项，全部通过。

### DeprecationWarning 记录（Python 升级预警）

| 来源 | 警告内容 | 影响 | 建议 |
|------|---------|------|------|
| `passlib/utils/__init__.py` | `import crypt` 在 Python 3.12 弃用，3.13 移除 | 无功能影响 | 升级 3.13 前改用 `argon2-cffi` |
| `passlib/handlers/argon2.py` | `argon2.__version__` 已弃用 | 无功能影响 | 升级 passlib 可消除 |
| `pythonjsonlogger/jsonlogger.py` | 模块路径变更为 `pythonjsonlogger.json` | 无功能影响 | 更新 `app/core/logging.py` 导入路径 |

### 当前状态

- **阶段 2（Step 2.1~2.6）+ 附加需求全部完成并通过手工验收。**
- 全量自动化测试：`71 passed, 0 failed, 3 warnings`（全部为已知 DeprecationWarning，无功能影响）。
- Alembic 迁移版本：`67b4aef28796 (head)`，含 user / semester_config / class_config 三张表。

### 下一步

- 阶段 3（Step 3.1）：加密工具 `app/core/crypto.py`，实现 Fernet 对称加密/解密。

### 风险与备注

- Word 导出必须严格按模板结构实现，禁止自行重排结构。
- 节假日逻辑包含“法定节假日前一天”和“不放假节日标签”两个维度，需提前设计接口返回模型。
- 权限可见性含“同班可见、跨班不可见”，后续数据查询层要预留班级维度过滤。

## 2026-05-16（开发环境迁移 Python 3.12 → 3.14）

### 背景

切换开发电脑，新机器仅有 Python 3.14.4，无 Python 3.12。完成兼容性迁移并验证全量测试通过。

### 变更内容

#### 1. `passlib[argon2]` → `argon2-cffi`（必须修复）

- **原因**：Python 3.13 起标准库移除 `crypt` 模块，`passlib` 内部依赖 `crypt` 导入失败，在 3.14 下运行时直接崩溃。
- **修复**：
  - `requirements.txt`：移除 `passlib[argon2]>=1.7.4`，改为 `argon2-cffi>=23.1.0`。
  - `app/auth/password.py`：从 `passlib.context.CryptContext` 改为直接使用 `argon2.PasswordHasher`；`verify_password` 捕获 `VerifyMismatchError / VerificationError / InvalidHashError` 返回 `False`，接口签名保持不变。
  - 外部接口（`hash_password` / `verify_password`）签名完全不变，上层代码无需修改。
- **验证**：`pytest tests/test_password.py tests/test_auth_service.py -v` 全部通过。

#### 2. `pythonjsonlogger` 导入路径修复（DeprecationWarning）

- **原因**：`python-json-logger` 新版将模块从 `pythonjsonlogger.jsonlogger` 移至 `pythonjsonlogger.json`。
- **修复**：`app/core/logging.py` 中将 `from pythonjsonlogger import jsonlogger` 改为 `from pythonjsonlogger import json as jsonlogger`。
- **效果**：测试警告从 2 条降至 0 条。

#### 3. 登录页异常捕获增强

- **原因**：原代码只捕获 `AuthError`，数据库连接失败等其他异常被 NiceGUI 静默吞掉，导致按钮点击无任何反应。
- **修复**：`app/ui/pages/login.py` 新增 `except Exception` 兜底，将错误类型展示到页面，同时记录结构化日志。

#### 4. VS Code 调试配置修复

- **原因**：旧 `launch.json` 以文件路径方式启动（`python app/main.py`），导致 `ModuleNotFoundError: No module named 'app'`。
- **修复**：`.vscode/launch.json` 新增「运行应用 (python -m app.main)」配置，使用 `module: app.main` + `cwd: ${workspaceFolder}`。

### 测试结果

```
71 passed, 0 warnings   （Python 3.14.4，修复后）
```

### 新电脑环境搭建步骤（备忘）

```bash
# 1. 克隆仓库后进入项目目录
cd /home/ywyz/code/kindergartenManager

# 2. 创建虚拟环境
python3 -m venv .venv

# 3. 安装依赖（zsh 下 >= 需引号）
.venv/bin/pip install -r requirements.txt

# 4. 复制并填写环境变量（DATABASE_URL / ENCRYPTION_KEY / JWT_SECRET 必须与线上一致）
cp .env.example .env

# 5. 运行应用
.venv/bin/python -m app.main

# 6. 跑测试
.venv/bin/pytest tests/ -v
```

> ⚠️ `ENCRYPTION_KEY` 和 `JWT_SECRET` 必须与生产/云端保持一致，否则已加密的 AI Key 无法解密，已颁发的 JWT token 失效。

### 当前状态

- 全量测试：71 passed，0 warnings（Python 3.14.4）。
- Alembic head：`67b4aef28796`（未变化）。
- 下一步：**阶段 3 Step 3.1** — 加密工具 `app/core/crypto.py`（Fernet 对称加密）。

---

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

