# 幼儿园教学管理系统 — 分步实施计划

> **阅读规则**
> - 每步必须完整完成并通过验证后再进行下一步。
> - 禁止跳步或合并多步同时实现。
> - 每步完成后在旁边标注 `✅`。
> - 数据库 schema 变更必须通过 Alembic 迁移完成，禁止 `create_all()`。
> - 参考：[AGENTS.md](../AGENTS.md) | [PRD.md](PRD.md) | [tech-stack.md](tech-stack.md)

---

## 阶段 0：项目骨架搭建

### Step 0.1 ✅ — 创建标准目录结构

**指令**
按照 AGENTS.md 中"目录结构规范"，在仓库根目录创建以下空目录（每个目录放一个 `.gitkeep` 文件）：
- `app/ui/`
- `app/api/`
- `app/service/`
- `app/repository/`
- `app/integration/ai_client/`
- `app/integration/holiday_client/`
- `app/integration/word_export/`
- `app/auth/`
- `app/core/`
- `app/jobs/`
- `alembic/`
- `tests/`
- `exports/`

每个 Python 包目录同时创建空的 `__init__.py`。

**验证**
- 运行 `find app tests alembic exports -type d | sort`，输出结果与上述目录清单完全一致。
- `python -c "import app.core; import app.service; import app.auth"` 无报错。

---

### Step 0.2 ✅ — 创建依赖清单与虚拟环境

**指令**
在根目录创建 `requirements.txt`，包含以下依赖（只列库名，版本约束宽松 `>=` 即可）：
- `nicegui`
- `fastapi`
- `uvicorn`
- `sqlalchemy[asyncio]`
- `aiomysql`（SQLAlchemy 异步 MySQL 驱动）
- `alembic`
- `pydantic-settings`
- `passlib[argon2]`
- `python-jose[cryptography]`（JWT）
- `httpx`
- `tenacity`
- `python-docx`
- `apscheduler`
- `pytest`
- `pytest-asyncio`
- `cryptography`（用于 AI Key 加密）

使用 `python3.12 -m venv .venv` 创建虚拟环境，激活后执行 `pip install -r requirements.txt`。

**验证**
- `pip list | grep nicegui` 有输出。
- `python -c "import nicegui, sqlalchemy, alembic, passlib, jose, httpx, tenacity, docx, apscheduler"` 无报错。

---

### Step 0.3 ✅ — 配置管理（core/config.py）

**指令**
在 `app/core/config.py` 中使用 `pydantic-settings` 定义 `Settings` 类，包含以下字段（全部从环境变量读取）：
- `DATABASE_URL`：异步 MySQL 连接串（`mysql+aiomysql://...`）
- `ENCRYPTION_KEY`：32 字节字符串，用于 AI Key 加密
- `JWT_SECRET`：JWT 签名密钥
- `JWT_EXPIRE_MINUTES`：整数，默认 60
- `HOLIDAY_API_URL`：节假日接口地址
- `LOG_LEVEL`：默认 `INFO`

在根目录创建 `.env.example`，列出上述所有字段名（值填写占位符），并在 `.gitignore` 中确保 `.env` 和 `.env.prod` 被忽略。

**验证**
- 复制 `.env.example` 为 `.env`，填入测试用假值。
- `python -c "from app.core.config import Settings; s = Settings(); print(s.JWT_EXPIRE_MINUTES)"` 输出 `60`。

---

### Step 0.4 ✅ — 日志初始化（core/logging.py）

**指令**
在 `app/core/logging.py` 中配置结构化 JSON 日志：
- 使用标准库 `logging` + `python-json-logger`（需加入 requirements）。
- 日志格式包含字段：`timestamp`、`level`、`logger`、`message`。
- 提供 `get_logger(name: str)` 函数供其他模块调用。
- `LOG_LEVEL` 从 `Settings` 读取。

**验证**
- `python -c "from app.core.logging import get_logger; l = get_logger('test'); l.info('hello')"` 输出包含 `"message": "hello"` 的 JSON 行。

---

### Step 0.5 ✅ — 数据库连接（core/database.py）

**指令**
在 `app/core/database.py` 中：
- 使用 `sqlalchemy.ext.asyncio` 创建 `AsyncEngine` 和 `AsyncSessionLocal`。
- 定义 `Base`（`DeclarativeBase`）供所有模型继承。
- 提供 `get_async_session()` 异步生成器，用于依赖注入。
- 连接串从 `Settings.DATABASE_URL` 读取。

初始化 Alembic：运行 `alembic init alembic`，修改 `alembic/env.py`，使其读取 `Settings.DATABASE_URL` 并导入 `Base.metadata`。

**验证**
- `alembic current` 不报错（首次为空，输出空行或 `<none>` 均可）。
- `python -c "from app.core.database import Base, AsyncSessionLocal; print('ok')"` 无报错。

---

## 阶段 1：账号与鉴权基础

### Step 1.1 ✅ — 用户数据模型

**指令**
在 `app/core/models/user.py` 中定义 `User` 表，字段包括：
- `id`（主键，BigInteger 自增）
- `tenant_id`（BigInteger，非空，索引）
- `username`（String 64，唯一约束范围：同一 tenant_id 下唯一）
- `hashed_password`（String 256，非空）
- `role`（Enum：`teacher` / `teaching_admin` / `sys_admin`，非空）
- `is_active`（Boolean，默认 True）
- `created_at` / `updated_at`（DateTime，自动时间戳）

生成并执行 Alembic 迁移：`alembic revision --autogenerate -m "add user table"` → `alembic upgrade head`。

**验证**
- `alembic current` 显示刚生成的迁移版本号。
- 用 MySQL 客户端执行 `DESCRIBE user;`，字段与上述定义一致。
- 迁移文件中可以看到 `tenant_id` 字段的 `index=True` 对应索引语句。

---

### Step 1.2 ✅ — 密码工具（auth/password.py）

**指令**
在 `app/auth/password.py` 中封装两个函数：
- `hash_password(plain: str) -> str`：使用 Argon2 哈希密码。
- `verify_password(plain: str, hashed: str) -> bool`：验证密码。
禁止使用 MD5 / SHA1 / bcrypt。

在 `tests/test_password.py` 中编写测试：
- 哈希后的字符串不等于原始密码。
- `verify_password` 对正确密码返回 True，对错误密码返回 False。
- 对同一密码两次哈希结果不同（Argon2 带 salt）。

**验证**
- `pytest tests/test_password.py -v` 全部通过。

---

### Step 1.3 ✅ — JWT 工具（auth/jwt.py）

**指令**
在 `app/auth/jwt.py` 中封装：
- `create_access_token(user_id: int, tenant_id: int, role: str) -> str`：生成 JWT，payload 包含 `sub`（user_id）、`tenant_id`、`role`、`exp`（过期时间）。
- `decode_access_token(token: str) -> dict`：解码并验证 token，过期或无效时抛出 `AuthError`（在 `app/core/exceptions.py` 中定义）。
- `JWT_SECRET` 和 `JWT_EXPIRE_MINUTES` 从 `Settings` 读取。

在 `tests/test_jwt.py` 中编写测试：
- 正常 token 可成功解码并取回 `user_id`、`role`。
- 篡改签名的 token 解码时抛出 `AuthError`。
- 过期 token（将 expire 设为过去时间）解码时抛出 `AuthError`。

**验证**
- `pytest tests/test_jwt.py -v` 全部通过。

---

### Step 1.4 ✅ — 用户仓库层（repository/user_repository.py）

**指令**
在 `app/repository/user_repository.py` 中定义异步函数：
- `create_user(session, tenant_id, username, hashed_password, role) -> User`
- `get_user_by_username(session, tenant_id, username) -> User | None`
- `get_user_by_id(session, tenant_id, user_id) -> User | None`
- `update_password(session, user_id, new_hashed_password) -> None`

所有查询必须携带 `tenant_id` 过滤条件。

在 `tests/test_user_repository.py` 中使用 SQLite 内存库（`aiosqlite`，加入 requirements）做集成测试：
- 创建用户后可通过 username 查询到。
- 不同 tenant_id 下同名用户互不可见。

**验证**
- `pytest tests/test_user_repository.py -v` 全部通过。

---

### Step 1.5 ✅ — 登录服务（service/auth_service.py）

**指令**
在 `app/service/auth_service.py` 中定义：
- `login(session, tenant_id, username, password) -> str`：验证用户名密码，返回 JWT access token；用户不存在或密码错误时统一抛出 `AuthError`（禁止区分两种情况，避免用户枚举攻击）。
- `change_password(session, tenant_id, user_id, old_password, new_password) -> None`：验证旧密码后更新为新哈希值。

在 `tests/test_auth_service.py` 中测试：
- 正确凭证登录返回有效 token。
- 错误密码抛出 `AuthError`。
- 不存在用户名抛出 `AuthError`。
- 改密后旧密码登录失败，新密码登录成功。

**验证**
- `pytest tests/test_auth_service.py -v` 全部通过。

---

### Step 1.6 ✅ — NiceGUI 登录页面（ui/pages/login.py）

**指令**
在 `app/ui/pages/login.py` 中创建登录页面：
- 包含"用户名"输入框、"密码"输入框（masked）、"登录"按钮。
- 点击登录后调用 `auth_service.login()`，成功则将 token 存入 `app.storage.user`（NiceGUI 内置用户 storage），并跳转到主页（暂时跳转到占位页 `/home`）。
- 登录失败显示红色提示文字"用户名或密码错误"，不暴露具体原因。
- 在 `app/main.py` 中注册该页面路由为 `/`，启动 NiceGUI 应用。

**验证**
- 运行 `python -m app.main`，浏览器访问 `http://localhost:8080`，出现登录表单。
- 输入错误密码，出现错误提示，不跳转。
- 输入正确凭证（需先用 repository 手动插入一条测试用户），成功跳转到 `/home`。

---

## 阶段 2：学期配置与日期计算

### Step 2.1 ✅ — 学期配置数据模型

**指令**
在 `app/core/models/semester.py` 中定义 `SemesterConfig` 表，字段：
- `id`（主键）
- `tenant_id` / `user_id`（BigInteger，非空，联合索引）
- `semester_name`（String 64，如"2025-2026学年第一学期"）
- `start_date` / `end_date`（Date 类型）
- `is_active`（Boolean，默认 True；同一用户只允许一条 active）
- `created_at` / `updated_at`

生成并执行迁移：`alembic revision --autogenerate -m "add semester_config table"` → `alembic upgrade head`。

**验证**
- `DESCRIBE semester_config;` 字段与定义一致。
- `alembic current` 显示最新版本。

---

### Step 2.2 ✅ — 班级配置数据模型

**指令**
在 `app/core/models/class_config.py` 中定义 `ClassConfig` 表，字段：
- `id`（主键）
- `tenant_id` / `user_id`
- `grade`（String 16，如"小班"/"中班"/"大班"）
- `class_name`（String 32，如"阳光班"）
- `indoor_areas`（Text，区域内容描述）
- `outdoor_content`（Text，户外内容描述）
- `created_at` / `updated_at`

生成并执行迁移。

**验证**
- `DESCRIBE class_config;` 字段与定义一致。

---

### Step 2.3 ✅ — 日期计算服务（service/date_service.py）

**指令**
在 `app/service/date_service.py` 中实现以下纯函数（无 IO，无数据库依赖）：
- `get_week_number(start_date: date, target_date: date) -> int`：返回 target_date 是开学后第几周（第 1 周起算）。
- `get_weekday_cn(target_date: date) -> str`：返回中文星期（"周一"…"周日"）。
- `is_workday(target_date: date) -> bool`：仅根据是否为周六/周日判断（节假日由独立客户端判断，不耦合到此处）。
- `is_within_semester(start_date: date, end_date: date, target_date: date) -> bool`：判断是否在学期内。

在 `tests/test_date_service.py` 中测试：
- 开学第一天为第 1 周。
- 开学后第 8 天为第 2 周。
- 周六/周日 `is_workday` 返回 False。
- 目标日期在学期外返回 False。

**验证**
- `pytest tests/test_date_service.py -v` 全部通过。

---

### Step 2.4 ✅ — 节假日客户端（integration/holiday_client/client.py）

**指令**
在 `app/integration/holiday_client/client.py` 中实现：
- `is_holiday(target_date: date) -> bool`：调用 `Settings.HOLIDAY_API_URL` 查询指定日期是否为法定节假日。
- 查询结果以 `{date_str: bool}` 格式缓存到内存字典，缓存有效期为当天结束（跨天自动失效）。
- API 调用失败时：记录警告日志，返回 `None`（调用方根据 None 判断"节假日信息不可用"，不抛出异常）。

在 `tests/test_holiday_client.py` 中使用 `httpx` 的 `MockTransport` 模拟 API：
- 正常响应时返回正确的 bool 值。
- API 返回 5xx 时返回 `None`。
- 同一日期第二次调用不发出 HTTP 请求（验证缓存生效）。

**验证**
- `pytest tests/test_holiday_client.py -v` 全部通过。

---

### Step 2.5 ✅ — 配置页面（ui/pages/settings.py）

**指令**
在 `app/ui/pages/settings.py` 中创建配置页面（路由 `/settings`），包含两个区块：

**学期配置区块**
- 学期名称输入框
- 开始日期选择器、结束日期选择器
- "保存"按钮：调用 repository 保存到 `semester_config` 表

**班级配置区块**
- 年级下拉（小班/中班/大班）
- 班级名称输入框
- 区域内容多行文本框
- 户外内容多行文本框
- "保存"按钮

页面加载时从数据库读取当前用户已有配置并回填。

**验证**
- 浏览器访问 `/settings`，两个区块正常显示。
- 填写并保存后，刷新页面数据仍存在（持久化验证）。
- 用 MySQL 客户端查询表数据，`tenant_id` 和 `user_id` 字段值正确。

---

### Step 2.6 ✅ — 日期选择面板（ui/components/date_panel.py）

**指令**
在 `app/ui/components/date_panel.py` 中创建可复用组件：
- 日期选择器（从 NiceGUI `ui.date` 实现）
- 选择日期后自动计算并显示：第几周、周几、是否工作日
- 若节假日客户端返回"是节假日"或"非工作日"，显示橙色提示文字（"今天是节假日/非工作日，可继续填写"）；若节假日信息不可用，显示灰色提示"节假日信息暂不可用"
- 不阻止用户继续操作

**验证**
- 将组件嵌入任意测试页面，选择一个周六，出现橙色提示。
- 选择工作日，提示消失。
- 模拟节假日 API 返回 None，出现灰色提示，其他功能不受影响。

---

## 阶段 3：AI Key 管理

### Step 3.1 ✅ — 加密工具（core/crypto.py）

**指令**
在 `app/core/crypto.py` 中实现：
- `encrypt(plain_text: str) -> str`：使用 `cryptography` 库的 Fernet 对称加密，密钥来自 `Settings.ENCRYPTION_KEY`（需做 base64 padding 处理）。
- `decrypt(cipher_text: str) -> str`：解密，失败时抛出 `CryptoError`。

在 `tests/test_crypto.py` 中测试：
- 加密后字符串不等于原文。
- 解密后还原为原文。
- 密文篡改后解密抛出 `CryptoError`。

**验证**
- `pytest tests/test_crypto.py -v` 全部通过。

---

### Step 3.2 ✅ — AI Key 数据模型与仓库

**指令**
在 `app/core/models/ai_key.py` 中定义 `AiApiKey` 表，字段：
- `id`（主键）
- `tenant_id` / `user_id`
- `api_base_url`（String 256，AI 接口地址）
- `api_key_encrypted`（Text，加密后存储）
- `is_active`（Boolean）
- `created_at` / `updated_at`

在 `app/repository/ai_key_repository.py` 中提供：
- `save_ai_key(session, tenant_id, user_id, api_base_url, plain_api_key) -> AiApiKey`：加密后入库。
- `get_active_ai_key(session, tenant_id, user_id) -> AiApiKey | None`：查询激活 Key。
- `get_decrypted_key(ai_key: AiApiKey) -> str`：解密并返回明文（明文禁止入库、禁止写日志）。

生成并执行迁移。

**验证**
- 写入一条记录后，直接查询数据库，`api_key_encrypted` 字段不是明文。
- 通过 `get_decrypted_key` 可还原原始字符串。
- `pytest tests/test_ai_key_repository.py -v` 全部通过。

---

### Step 3.3 ✅ — AI Key 设置页面

**指令**
在 `/settings` 页面新增"AI 接口配置"区块：
- API 地址输入框
- API Key 输入框（password 类型，展示时脱敏为 `sk-****xxxx`）
- "保存"按钮：保存前加密，入库
- "验证连接"按钮：发送一次最小化测试请求，返回成功/失败提示

**验证**
- 保存后数据库中 `api_key_encrypted` 为密文。
- 页面刷新后 API Key 输入框显示脱敏字符串，不显示明文。
- "验证连接"在 Key 有效时显示"连接成功"。

---

## 阶段 4：教案拆分与年龄适配

### Step 4.1 ✅ — AI 客户端基础（integration/ai_client/base.py）

**指令**
在 `app/integration/ai_client/base.py` 中实现通用 AI 请求函数：
- 接受 `messages: list[dict]`、`api_base_url: str`、`api_key: str`、`response_schema: dict`（JSON schema）参数。
- 使用 `httpx.AsyncClient` 发送请求，超时 60 秒。
- 使用 `tenacity`：最多重试 3 次，指数退避（2s → 4s → 8s）。
- 返回解析后的 dict；解析 JSON 失败时记录完整原始响应（INFO 级别）并抛出 `AiParseError`。
- API 返回 4xx/5xx 时抛出 `AiCallError`（均在 `core/exceptions.py` 定义）。

在 `tests/test_ai_client_base.py` 中使用 `httpx.MockTransport` 测试：
- 正常响应返回解析后 dict。
- 返回无效 JSON 时抛出 `AiParseError`。
- 返回 500 时重试 3 次后抛出 `AiCallError`。

**验证**
- `pytest tests/test_ai_client_base.py -v` 全部通过。

---

### Step 4.2 ✅ — 教案拆分客户端（integration/ai_client/lesson_plan_client.py）

**指令**
在 `app/integration/ai_client/lesson_plan_client.py` 中实现：
- `split_lesson_plan(raw_text: str, api_base_url: str, api_key: str) -> dict`：构造 system prompt + user message，调用 `base.py` 中的通用函数，返回包含以下键的 dict：
  - `activity_goal`（活动目标）
  - `activity_prep`（活动准备）
  - `activity_key`（活动重点）
  - `activity_difficult`（活动难点）
  - `activity_process`（活动过程原文）

system prompt 从 `app/repository/prompt_repository.py` 查询当前激活版本（见 Step 5.1），若无则使用内置默认 prompt。

**验证**
- 使用 Mock 模拟 AI 返回，调用后返回 dict 包含全部 5 个键。
- 缺少任意键时抛出 `AiParseError`。

---

### Step 4.3 ✅ — 年龄适配客户端（integration/ai_client/adapt_client.py）

**指令**
在 `app/integration/ai_client/adapt_client.py` 中实现：
- `adapt_activity_process(original: str, grade: str, api_base_url: str, api_key: str) -> str`：将活动过程按年龄段（小班/中班/大班）改写，返回改写后文本。

**验证**
- Mock 返回正常时，返回字符串非空。
- Mock 返回缺少内容时抛出 `AiParseError`。

---

### Step 4.4 ✅ — 差异比对服务（service/diff_service.py）

**指令**
在 `app/service/diff_service.py` 中实现：
- `compute_diff(original: str, adapted: str) -> list[dict]`：使用 `difflib` 对两段文本按句（以句号/换行分句）比对，返回列表，每项包含：
  - `text`（句子内容）
  - `changed`（bool，True 表示该句在改写文中与原文不同）

在 `tests/test_diff_service.py` 中测试：
- 完全相同的文本，所有 `changed` 为 False。
- 修改一句后，该句 `changed` 为 True，其余不变。
- 空字符串输入返回空列表。

**验证**
- `pytest tests/test_diff_service.py -v` 全部通过。

---

### Step 4.5 ✅ — 教案数据模型

**指令**
在 `app/core/models/daily_plan.py` 中定义 `DailyPlan` 表，字段：
- `id`（主键）
- `tenant_id` / `user_id`
- `plan_date`（Date）
- `week_number`（Integer）
- `weekday_cn`（String 4）
- `grade` / `class_name`（String）
- `activity_goal` / `activity_prep` / `activity_key` / `activity_difficult`（Text）
- `activity_process_original`（Text，AI 拆分原文）
- `activity_process_adapted`（Text，年龄适配改写文）
- `morning_activity` / `indoor_area` / `outdoor_activity`（Text，一日活动生成内容，可为空）
- `morning_talk_topic` / `morning_talk_questions`（Text，可为空）
- `daily_reflection`（Text，可为空）
- `created_at` / `updated_at`

生成并执行迁移。

**验证**
- `DESCRIBE daily_plan;` 字段与定义一致。
- `alembic current` 显示最新版本。

---

### Step 4.6 ✅ — 教案拆分服务（service/lesson_plan_service.py）

**指令**
在 `app/service/lesson_plan_service.py` 中编排完整教案拆分流程：
1. 从数据库获取用户 AI Key（解密）
2. 调用 `split_lesson_plan()`
3. 调用 `adapt_activity_process()` 对活动过程改写
4. 调用 `compute_diff()` 生成差异
5. 将所有结果组合为 `LessonPlanResult` dataclass（定义在 `app/service/` 目录内），包含拆分字段 + 改写文 + 差异列表
6. 不负责入库（入库由 repository 层负责，由 UI 层触发）

在 `tests/test_lesson_plan_service.py` 中使用 Mock 隔离 AI 调用，测试：
- 完整流程返回 `LessonPlanResult`，包含所有字段。
- AI Key 不存在时抛出 `ConfigError`。

**验证**
- `pytest tests/test_lesson_plan_service.py -v` 全部通过。

---

### Step 4.7 ✅ — 教案拆分页面（ui/pages/daily_plan.py）

**指令**
在 `app/ui/pages/daily_plan.py` 中创建每日活动计划页面（路由 `/daily-plan`），包含：

**顶部区域**（引用 Step 2.6 的 `date_panel` 组件，复用不重写）

**教案输入区块**
- 大文本框（粘贴完整教案）
- "连接AI拆分"按钮：点击后调用 `lesson_plan_service`，显示加载动画，完成后回填以下表单字段

**回填表单字段**（每个对应一个 `ui.textarea`）
- 活动目标、活动准备、活动重点、活动难点、活动过程（展示改写后版本；改写前原文以折叠方式可查看）

**操作按钮**
- "保存草稿"：将当前表单内容保存到 `daily_plan` 表
- "导出 Word"（暂时禁用，Stage 5 实现）

**验证**
- 浏览器打开 `/daily-plan`，粘贴教案后点击拆分，5 个字段被回填。
- 点击"保存草稿"，数据库中出现一条 `daily_plan` 记录，`tenant_id`/`user_id` 正确。
- 刷新页面后可通过选择日期重新加载已保存草稿（可从 `plan_date` 查询）。

---

## 阶段 5：提示词管理

### Step 5.1 ✅ — 提示词数据模型

**指令**
在 `app/core/models/prompt_template.py` 中定义 `PromptTemplate` 表，字段：
- `id`（主键）
- `tenant_id` / `user_id`
- `task_type`（Enum：`split`/`adapt`/`morning_exercise`/`morning_talk`/`area_game`/`outdoor_game`/`daily_reflection`，共 7 种；初始建表为 `split`/`adapt`/`generate`，后经迁移 `e2a3f1b8c9d0` 扩展为 7 值）
- `version`（Integer，同一用户同一 task_type 下单调递增）
- `content`（Text，提示词正文）
- `is_active`（Boolean；同一用户同一 task_type 只能有一条 active）
- `created_at` / `updated_at`

生成并执行迁移（初始迁移 `bcd07e51527d`，扩展迁移 `e2a3f1b8c9d0`）。

**验证**
- `DESCRIBE prompt_template;` 字段与定义一致。

---

### Step 5.2 ✅ — 提示词仓库与服务

**指令**
在 `app/repository/prompt_repository.py` 中实现：
- `get_active_prompt(session, tenant_id, user_id, task_type) -> PromptTemplate | None`
- `save_new_version(session, tenant_id, user_id, task_type, content) -> PromptTemplate`：版本号自动递增，新版本设为 active，旧版本 is_active 设为 False。
- `rollback_to_version(session, tenant_id, user_id, task_type, version) -> PromptTemplate`：将指定版本设为 active。
- `list_versions(session, tenant_id, user_id, task_type) -> list[PromptTemplate]`：返回所有版本，按版本号降序。

在 `tests/test_prompt_repository.py` 中测试：
- 保存新版本后，版本号自动递增。
- 新版本保存后旧版本 `is_active` 变为 False。
- 回滚后目标版本变为 active，其他版本变为 inactive。

**验证**
- `pytest tests/test_prompt_repository.py -v` 全部通过（16 passed）。

---

### Step 5.3 ✅ — 提示词管理页面（ui/pages/prompt_mgmt.py）

**指令**
在 `app/ui/pages/prompt_mgmt.py` 中创建提示词管理页面（路由 `/prompts`），对每种 task_type 分别展示：
- 当前激活版本的提示词内容（可编辑文本框）
- "保存为新版本"按钮
- 历史版本列表（版本号、创建时间、是否激活）
- 每条历史版本旁有"回滚"按钮
- 7 个 Tab（教案拆分、年龄适配、晨间活动、晨间谈话、区域游戏、户外游戏、一日反思）

**验证**
- 保存新版本后，版本列表中出现新条目，旧条目"激活"标识消失。
- 点击"回滚"后，对应版本变为激活，验证数据库 `is_active` 字段正确。
- **手工测试待执行**（下次启动第一步）。

---

## 阶段 6：Word 导出

### Step 6.1 — Word 导出服务（integration/word_export/exporter.py）

> **2026-05-30 调整**：经核实 `templates/teacherplan.docx` 为 **19 行 2 列** 结构（左列标题纵向合并，右列内容分子字段单元格），并非早前规划的 8 行。导出主方案改为 **打开模板填充其既有单元格**，将子字段分别写入对应行的右列单元格（晨间活动 R2/R3、晨间谈话 R4/R5、集体活动 R6~R11、室内区域 R12~R14、户外 R15~R17、反思 R18）。`_parse_fields` 将一日活动生成文本解析为子字段后分格填充；模板缺失时降级 `_export_from_scratch`（原 8 行从零建表逻辑保留为兜底）。

**指令**
在 `app/integration/word_export/exporter.py` 中实现 `export_daily_plan(daily_plan: DailyPlan, diff_result: list[dict]) -> bytes`：
- 主方案：`Document(TEMPLATE_PATH)` 打开 `templates/teacherplan.docx`，按模板单元格结构填充各字段（子字段分单元格）。
- 对"活动过程"字段：`diff_result` 中 `changed=True` 的句子用红色字体（`RGBColor(255, 0, 0)`）输出；未改动句子用黑色。
- 中文字体统一指定为"宋体"。
- 模板缺失/填充异常时降级为从零构建简化表格（`_export_from_scratch`，8 行 2 列）。
- 返回文档的 bytes 内容（不写文件，由调用方决定存储）。

在 `tests/test_word_exporter.py` 中测试：
- 返回值为非空 bytes。
- 使用 python-docx 重新解析返回的 bytes，验证表格行数为 8。
- 包含差异标注时，对应 run 的字体颜色为红色。

**验证**
- `pytest tests/test_word_exporter.py -v` 全部通过。

---

### Step 6.2 — 导出记录模型与接入页面

**指令**
在 `app/core/models/export_record.py` 中定义 `ExportRecord` 表：
- `id`、`tenant_id`、`user_id`、`daily_plan_id`（外键）、`file_name`（String）、`file_path`（String）、`created_at`

生成迁移并执行。

在 `/daily-plan` 页面中激活"导出 Word"按钮：
- 点击后调用 `export_daily_plan()`，将返回 bytes 写入 `exports/{tenant_id}_{user_id}_{grade}_{class}_{YYYYMMDD}_日计划.docx`。
- 将文件路径写入 `export_records` 表。
- 通过 NiceGUI 的 `ui.download` 触发浏览器下载。

**验证**
- 点击"导出 Word"，浏览器自动下载文件，文件名格式正确。
- 打开下载文件，表格共 8 行，差异内容字体为红色。
- `export_records` 表中有对应记录。

---

## 阶段 7：一日活动辅助生成

### Step 7.1 — 一日活动生成客户端（integration/ai_client/activity_gen_client.py）

**指令**
在 `app/integration/ai_client/activity_gen_client.py` 中实现：
- `generate_daily_activities(context: dict, api_base_url: str, api_key: str) -> dict`
- `context` 字段：`week_number`、`weekday`、`near_holiday`（bool 或 None）、`indoor_areas`、`outdoor_content`、`grade`、`class_name`
- 返回 dict 包含键：`morning_activity`、`indoor_area`、`outdoor_activity`、`morning_talk_topic`、`morning_talk_questions`

**验证**
- Mock 测试：返回 dict 包含全部 5 个键。
- `near_holiday=True` 时，system prompt 中包含节假日相关提示（通过断言 prompt 字符串实现）。

---

### Step 7.2 — 一日活动生成表单（接入 daily_plan 页面）

> **2026-05-30 调整**：按用户手测反馈改为 **一键生成**。原各小节（晨间活动/晨间谈话/区域游戏/户外游戏）独立「AI 生成」按钮已合并为单个「一键生成一日活动」按钮（`_gen_all_daily`），内部用 `asyncio.gather(..., return_exceptions=True)` 并发调用 4 次生成，单项失败不阻断其余项，并在小节与顶部汇总 label 标注结果。「集体活动」走拆分按钮、「一日活动反思」独立按钮保持不变。

**指令**
在 `/daily-plan` 页面新增"一日活动生成"区块：
- "一键生成一日活动"按钮：根据当前日期面板信息 + 班级配置并发调用生成，回填晨间活动、室内区域活动、户外游戏活动、晨间谈话主题/问题设计。
- 单项失败保留原值并提示，不影响其他项回填。

回填后内容可手动编辑，"保存草稿"已有逻辑自动包含这些字段（无需修改）。

**验证**
- 选定日期和班级配置后，点击"一键生成一日活动"，多个区域并发回填；单项失败有提示。
- 手动修改回填内容后保存，数据库中记录为修改后内容。

---

## 阶段 8：收尾与稳定性

### Step 8.1 — 全局异常处理与日志审计

**指令**
在 `app/core/exceptions.py` 中确认已定义：`AuthError`、`AiCallError`、`AiParseError`、`CryptoError`、`ConfigError`。

在 `app/main.py` 中为 NiceGUI/FastAPI 注册全局异常处理：
- `AuthError` → 重定向到登录页。
- `AiCallError` / `AiParseError` → 显示用户友好提示，记录 ERROR 级别日志（包含 user_id、tenant_id）。
- 未预期异常 → 显示"系统错误，请联系管理员"，记录完整 traceback。

**验证**
- 模拟 AI 调用失败，页面显示友好提示，不暴露堆栈信息。
- 日志文件中出现对应 JSON 格式错误记录。

---

### Step 8.2 — 路由守卫（未登录跳转）

**指令**
在 `app/auth/middleware.py` 中实现路由守卫：
- 所有非 `/`（登录页）路由，检查 `app.storage.user` 中是否存在有效 token。
- 无效或过期时重定向到 `/`，清除 storage。
- 在 `app/main.py` 中注册该守卫。

**验证**
- 未登录直接访问 `/daily-plan`，自动跳转到 `/`。
- 登录后访问 `/daily-plan`，正常显示。
- 手动删除 storage 中的 token 后刷新，自动跳转。

---

### Step 8.3 — 运行全量测试

**指令**
运行 `pytest tests/ -v --tb=short`，所有测试用例必须全部通过，零失败、零错误。

记录最终测试数量与通过率到本文件末尾（追加一行注释即可）。

**验证**
- 命令输出最后一行为 `N passed`（N 为实际数量），无 `failed` 或 `error`。

---

### Step 8.4 — 更新 architecture.md

**指令**
在 `memory-bank/` 目录创建（或更新）`architecture.md`，记录：
- 最终数据库表清单（表名 + 核心字段）
- 模块职责说明（每个 `app/` 子目录一行描述）
- 已实现的 Alembic 迁移版本列表
- 已知限制与后续扩展点

**验证**
- `memory-bank/architecture.md` 文件存在且内容覆盖上述四个部分。

---

## 完成标志

以下所有条件满足时，视为 M2（首期闭环可用）达成：

- [ ] `pytest tests/ -v` 全部通过
- [ ] 可完整执行：登录 → 配置学期/班级 → 选择日期 → 粘贴教案 → AI拆分回填 → AI生成一日活动 → 保存草稿 → 导出 Word
- [ ] Word 文件差异文本标红正确
- [ ] 数据库中 `tenant_id`/`user_id` 在所有表中均正确写入
- [ ] 提示词可保存新版本并回滚
- [ ] `memory-bank/architecture.md` 已更新

---

## Backlog：低优先级待开发需求

### BL-01 — `get_special_day_tags` 在线 API 支持

**背景**：在 Step 2.4 阶段曾实现过在线动态获取特殊节日标签（GET `{SPECIAL_DAY_API_URL}/{YYYY-MM-DD}` → `{"tags":[...]}`），但因收益有限、增加配置依赖而回滚，改回本地硬编码同步实现。

**待实现时的方案**：
- 在 `app/core/config.py` 新增 `SPECIAL_DAY_API_URL: str | None = None`（可选）。
- `get_special_day_tags` 改为 async：配置 API 时优先在线获取，失败或未配置时降级本地硬编码。
- 独立缓存 `_special_day_cache: dict[str, list[str]]`，当天有效，跨天自动清空。
- `DatePanel._update_info` 对应改为 `await get_special_day_tags(target)`。
- 测试：`MockTransport` 覆盖 API 返回标签、5xx 降级硬编码、未配置不发请求、缓存复用。

**触发条件**：有真实在线特殊节日 API 可接入时启用。
