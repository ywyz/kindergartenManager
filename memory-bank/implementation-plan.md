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


> 阶段 4~8（教案拆分、提示词管理、Word 导出、一日活动生成、收尾加固）的实施计划详见 [daily-plan/design.md](daily-plan/design.md)。

---

## 阶段 M6：Docker Compose AIO + 子系统拆分 + Caddy HTTPS

> v3.0.1 已完成单用户模式重构（取消登录、默认 SQLite、简化 setup）。
> M6 目标：将系统容器化，建立微服务架构基础。

### Step M6.1 ✅ — 主系统容器化 + Caddy 反向代理

**指令**
- 更新 `docker-compose.yml`：AIO 编排（Caddy + app + MySQL）
- 创建 `Caddyfile`：反向代理到主系统（开发用 HTTP，生产切换域名 HTTPS）
- 创建 `docker-compose.dev.yml`：开发覆盖（直接暴露端口、禁用 Caddy）
- 更新 `Dockerfile`：主系统镜像构建

**验证**
- `docker compose up -d` 启动成功
- Caddy 反向代理到主系统 :8080
- `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` 直接暴露端口

---

### Step M6.2 — 子系统骨架创建

**指令**
在 `services/` 下创建三个子系统骨架：

1. `services/ai-service/`：FastAPI 骨架 + `GET /health` + Dockerfile
2. `services/word-service/`：FastAPI 骨架 + `GET /health` + Dockerfile
3. `services/holiday-service/`：FastAPI 骨架 + `GET /health` + Dockerfile

每个子系统包含：
- `app/main.py`（FastAPI 入口）
- `Dockerfile`（基于 python:3.12-slim）
- `requirements.txt`（fastapi, uvicorn, 及各自专属依赖）

**验证**
- 每个子系统可独立启动：`cd services/ai-service && uvicorn app.main:app`
- `GET /health` 返回 `{"status": "ok"}`

---

### Step M6.3 — 子系统加入 Docker Compose 编排

**指令**
- 在 `docker-compose.yml` 中添加 ai-service、word-service、holiday-service 服务定义
- 配置 Docker 内部网络（kindergarten_net），子系统不暴露外部端口
- 主系统通过服务名（如 `http://ai-service:8001`）调用子系统

**验证**
- `docker compose up -d` 启动所有服务
- 主系统容器可通过 `curl http://ai-service:8001/health` 访问子系统

---

### Step M6.4 — holiday-service 功能迁移（首个拆分）

**指令**
- 将 `app/integration/holiday_client/client.py` 的核心逻辑迁移到 `services/holiday-service/`
- 在 holiday-service 中实现 REST API：
  - `GET /api/v1/holiday/{date}` → 法定节假日判定
  - `GET /api/v1/holiday/{date}/near` → 是否临近节假日
  - `GET /api/v1/holiday/{date}/workday` → 调班工作日判定
  - `GET /api/v1/special-days/{date}` → 特殊节日标签
- 修改主系统 `app/integration/holiday_client/client.py`：改为 HTTP 调用 holiday-service

**验证**
- holiday-service 独立运行，API 返回正确结果
- 主系统通过 Docker 网络调用 holiday-service，日期功能正常

---

### Step M6.5 — ai-service 功能迁移

**指令**
- 将 `app/integration/ai_client/` 的核心逻辑迁移到 `services/ai-service/`
- 在 ai-service 中实现 REST API：
  - `POST /api/v1/split` → 教案拆分
  - `POST /api/v1/adapt` → 年龄适配
  - `POST /api/v1/generate` → 一日活动生成
  - `POST /api/v1/observe` → 游戏观察生成（含视觉模型）
- 主系统通过 HTTP 调用 ai-service

**验证**
- 主系统 AI 功能正常（拆分、适配、生成）
- ai-service 容器独立处理 AI 调用

---

### Step M6.6 — word-service 功能迁移

**指令**
- 将 `app/integration/word_export/` 的核心逻辑迁移到 `services/word-service/`
- 在 word-service 中实现 REST API：
  - `POST /api/v1/export/daily-plan` → 导出每日活动计划 Word
  - `POST /api/v1/export/observation` → 导出游戏观察 Word
  - `POST /api/v1/export/batch` → 批量导出
- 主系统通过 HTTP 调用 word-service，接收生成的 Word 文件

**验证**
- Word 导出功能正常（单导出、批量导出）
- word-service 容器独立处理模板填充和文件生成

---

## 阶段 M7：恢复登录与多用户支持

> 待 M6 稳定后启动

### Step M7.1 — 恢复登录页面和 AuthMiddleware
### Step M7.2 — 恢复注册和用户管理页面
### Step M7.3 — 恢复个人资料页面
### Step M7.4 — 多用户数据隔离验证
