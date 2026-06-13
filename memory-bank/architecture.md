# 幼儿园教学管理系统架构文档（初始化）

## 1. 当前阶段

- 项目阶段：M2/M3 已完成（阶段 0~8 全部完成）；二期对外只读 REST API 已落地。
- 开发策略：先架构后编码；每完成一个步骤同步更新本文件与 progress.md

## 2. 业务与权限边界（已确认）

- 教师：创建、编辑、导出、查看同班计划；不可跨班查看。
- 教研管理员：可查看、编辑、批注教学计划；可管理提示词。
- 系统管理员：独立后台管理界面（低优先级，后续实现）。
- 多设备登录：token 独立；设备管理和强制下线功能为低优先级需求。

> 一日活动计划子系统（教案拆分 / 年龄适配 / 提示词管理 / Word 导出 / 一日活动生成）的核心流程约束、日历规则与导出规则详见 [daily-plan/design.md](daily-plan/design.md)。

## 3. 目录结构与模块职责（Step 0.1 完成后）

以下目录已创建，每个目录的职责如下：

| 目录 | 职责 |
|------|------|
| `app/` | 应用根包，所有业务代码入口 |
| `app/ui/` | NiceGUI 页面与组件，每个页面独立文件（如 `pages/login.py`、`pages/setup.py`、`components/date_panel.py`）；禁止在此层做权限逻辑 |
| `app/api/` | 对外只读 REST API（二期）：`/api/v1` 路由、API Key + 可选 HMAC 签名鉴权；供子系统（幼儿园信息管理主系统）读取教学计划数据 |
| `app/service/` | 业务逻辑层：教案拆分协调、年龄适配、差异比对、日期计算、登录逻辑等；不直接发 HTTP 请求 |
| `app/repository/` | 数据访问层：封装所有 SQL 查询，返回模型对象；所有查询必须携带 `tenant_id` 过滤条件 |
| `app/integration/ai_client/` | OpenAI 兼容接口封装：`httpx` + `tenacity` 重试，强约束 JSON schema，解析失败抛出 `AiParseError` |
| `app/integration/holiday_client/` | 中国法定节假日 API 调用：带内存缓存（当天有效），API 失败时返回 `None` 降级，不阻断主流程 |
| `app/integration/word_export/` | Word 导出：`python-docx` 主方案，严格依照 `templates/teacherplan.docx` 结构，差异段落标红 |
| `app/auth/` | JWT 生成/验证、RBAC 权限校验、密码哈希（Argon2）、路由守卫中间件（`middleware.py`）；权限逻辑统一在此层，不下沉到 UI |
| `app/core/` | 配置（`pydantic-settings`）、日志（JSON 结构化）、审计日志（`audit.py`）、数据库连接（`AsyncEngine`）、异常定义、常量、加密工具 |
| `app/jobs/` | 管理脚本：`bootstrap_admin.py`（系统管理员初始化 / 密码重置，支持 `--init` / `--reset-password` 交互式 CLI）；APScheduler 定时任务预留位 |
| `alembic/` | 数据库迁移脚本（Alembic），所有 schema 变更必须通过此处，禁止应用启动时 `create_all()` |
| `tests/` | pytest 测试，每个 service 函数必须有单元测试；AI/Word/数据库操作用 mock/fixture 隔离 |
| `exports/` | 导出的 Word 文件（运行时生成，不入仓，已在 `.gitignore` 中排除） |
| `templates/` | Word 模板文件，`teacherplan.docx` 为唯一导出结构依据 |
| `memory-bank/` | 项目文档（PRD、技术栈、实施计划、架构、进度），供开发者参考 |

### 关键约束速查
- **数据隔离**：所有业务表必须包含 `tenant_id`、`user_id`、`created_at`、`updated_at`
- **禁止**：`app/api/` 首期不实现；应用启动时不得 `create_all()`；service 层不直接发 HTTP 请求
- **Python 包**：`alembic/`、`exports/`、`templates/`、`memory-bank/` 均非 Python 包（无 `__init__.py`）

## 4. 阶段 0 已实现文件清单

| 文件 | 职责 |
|------|------|
| `requirements.txt` | 项目全量依赖，含运行时与测试依赖 |
| `.env.example` | 环境变量占位模板，真实 `.env` 不入仓 |
| `.gitignore` | 忽略 `.env`、`.env.prod`、`.venv/`、`exports/`、`__pycache__/` 等 |
| `app/core/config.py` | `Settings` 类（pydantic-settings），统一读取所有环境变量；单例 `settings` 供全局使用 |
| `app/core/logging.py` | `get_logger(name)` — JSON 结构化日志，字段固定为 timestamp/level/logger/message；LOG_LEVEL 由 Settings 控制 |
| `app/core/database.py` | `AsyncEngine`、`AsyncSessionLocal`（async_sessionmaker）、`Base`（DeclarativeBase）、`get_async_session()` 依赖注入生成器 |
| `alembic/env.py` | 已配置读取 `Settings.DATABASE_URL`（迁移用 pymysql 同步驱动）并绑定 `Base.metadata` 支持 autogenerate |
| `alembic.ini` | Alembic 默认配置，连接串由 env.py 覆盖 |

### 核心约定提示
- Alembic 迁移使用 `pymysql`（同步）；运行时使用 `aiomysql`（异步）
- `Base` 必须在所有 model 文件中被导入后，`alembic revision --autogenerate` 才能检测到新表
- 当 `DATABASE_URL` 含 URL 编码字符（如 `%40`）时，`alembic/env.py` 写入 `sqlalchemy.url` 前必须将 `%` 转义为 `%%`，避免 `configparser` 插值异常

## 5. 阶段 1 & 2 已实现文件清单

### 数据库表（Alembic 当前 head：最新迁移版本，含 ai_api_key 表）

| 表名 | 迁移版本 | 主要字段 |
|------|---------|----------|
| `users` | `5e03413fdeca` | id, tenant_id, username, hashed_password, role, is_active |
| `semester_config` | `fd6d29f921b4` | id, tenant_id, user_id, semester_name, start_date, end_date, is_active |
| `class_config` | `67b4aef28796` | id, tenant_id, user_id, grade, class_name, indoor_areas, outdoor_content |
| `ai_api_key` | 阶段3迁移 | id, tenant_id, user_id, api_base_url, model_name, api_key_encrypted, is_active |

所有表均含 `created_at`、`updated_at`，并建立 `(tenant_id, user_id)` 联合索引。

**安全约束**：`ai_api_key.api_key_encrypted` 仅存 Fernet 密文，明文禁止入库、禁止写日志。

### 核心模块

| 文件 | 职责 |
|------|------|
| `app/core/models/user.py` | User ORM 模型 |
| `app/core/models/semester.py` | SemesterConfig ORM 模型 |
| `app/core/models/class_config.py` | ClassConfig ORM 模型 |
| `app/auth/password.py` | Argon2 密码哈希与验证（passlib） |
| `app/auth/jwt.py` | JWT 生成/验证（python-jose HS256），payload 含 sub/tenant_id/role/exp |
| `app/service/auth_service.py` | 登录逻辑（查用户→验密码→签 JWT）；修改密码 |
| `app/service/date_service.py` | 纯函数：`get_week_number`、`get_weekday_cn`、`is_workday`、`is_within_semester` |
| `app/repository/user_repository.py` | 按用户名/ID 查询用户；更新密码 |
| `app/repository/semester_repository.py` | `get_active_semester`、`upsert_active_semester` |
| `app/repository/class_repository.py` | `get_class_config`、`upsert_class_config` |
| `app/integration/holiday_client/client.py` | 法定节假日判定；法定节假日缓存 `dict[str, tuple[bool, str\|None, int]]`（含 day_type）；特殊节日缓存 `dict[str, list[str]]`；`is_holiday`、`is_near_holiday`、`get_holiday_name`、`get_special_day_tags`（sync，本地硬编码）、`is_adjusted_workday` |
| `app/ui/pages/login.py` | 登录页（路由 `/`），token 写入 `app.storage.user` |
| `app/ui/pages/home.py` | 首页（路由 `/home`），快捷导航按钮 |
| `app/ui/pages/settings.py` | 配置页（路由 `/settings`），学期配置、班级配置、AI 接口配置（含脱敏展示与验证连接） |
| `app/ui/pages/date_test.py` | 日期测试页（路由 `/date-test`），嵌入 DatePanel |

## 6. 阶段 3 已实现文件清单

### 核心模块

| 文件 | 职责 |
|------|------|
| `app/core/exceptions.py` | 新增 `CryptoError`（加解密失败）、`ConfigError`（业务配置缺失，如未配置 AI Key） |
| `app/core/crypto.py` | Fernet 对称加密：`encrypt(plain_text) -> str` / `decrypt(cipher_text) -> str`；密钥来自 `ENCRYPTION_KEY`（UTF-8→取前32字节→base64）；解密失败抛 `CryptoError` |
| `app/core/models/ai_key.py` | `AiApiKey` ORM 模型；`api_key_encrypted` 仅存密文 |
| `app/repository/ai_key_repository.py` | `save_ai_key`（加密入库，自动 deactivate 旧记录）/ `get_active_ai_key` / `get_decrypted_key` |

### 基础设施变更

| 文件 | 变更内容 |
|------|----------|
| `app/core/database.py` | `pool_pre_ping=False`（避免远程 DB 额外往返）；新增 `pool_recycle=1800` |
| `.env` | `DATABASE_URL` 主机改为 IPv4 直连（`47.116.40.89`），规避双栈服务器 IPv6 超时问题 |

### 已知问题与决策记录

| 编号 | 问题 | 决策 |
|------|------|------|
| BL-02 | `aliyun.ywyz.tech` 同时有 A/AAAA 记录，aiomysql 优先尝试 IPv6 导致连接超时 2+ 分钟 | `.env` 改用 IPv4 直连；根治方案：删除 DNS AAAA 记录 |
| BL-01 | `get_special_day_tags` 曾计划在线 API，代价大于收益 | 回滚为本地硬编码同步实现 |

### Holiday Client 接口说明

```python
# 判定法定节假日（True=法定节假日, False=非法定节假日, None=API不可用）
is_holiday(target_date, *, _transport=None) -> bool | None

# 判定明天是否为法定节假日（True=是, False=否, None=API不可用）
is_near_holiday(target_date, *, _transport=None) -> bool | None

# 获取具体节日名称（如"国庆节"），非法定节假日或API不可用返回 None
# 与 is_holiday 共享法定节假日缓存，同一日期不发额外 HTTP 请求
get_holiday_name(target_date, *, _transport=None) -> str | None

# 返回不放假节日标签列表（如["教师节"]）
# 纯本地硬编码字典（不依赖外部 API），返回副本
# 独立缓存（当天有效）
get_special_day_tags(target_date) -> list[str]  # sync

# 判定调班工作日：调休补班的周末（type=3），需正常上班
# 复用 is_holiday 法定节假日缓存（同日期不重复发 HTTP 请求）
# True=调班工作日, False=非调班工作日, None=API不可用
is_adjusted_workday(target_date, *, _transport=None) -> bool | None
```

API 响应格式（timor.tech 兼容）：
```json
{
  "code": 0,
  "type": {"type": 0|1|2|3, "name": "工作日|周末|法定节假日|调班工作日"},
  "holiday": {"name": "国庆节", "holiday": true, "wage": 3} | null
}
```
type 值：0=工作日，1=周末，2=法定节假日，3=调班工作日。

### DatePanel 组件

`app/ui/components/date_panel.py` — 可复用日期面板，嵌入任意页面即可获得：
- 日期选择器（`ui.date`）
- 自动计算并展示：第几周、周几
- 状态提示（颜色区分）：法定节假日（含节日名称）/ 调班工作日 / 临近节假日 / 特殊节日标签 / 节假日信息不可用
- 不阻止用户继续操作

> 一日活动计划子系统（Stage 4~7）已实现文件清单详见 [daily-plan/design.md](daily-plan/design.md)。

## 7. 阶段 8：收尾与稳定性

| 文件 | 职责 |
|------|------|
| `app/auth/middleware.py` | `AuthMiddleware`（`BaseHTTPMiddleware`）路由守卫：受限页面校验 `app.storage.user` 中 JWT token，无效则清空 storage 重定向 `/`；非页面路由（静态资源/`_nicegui`）放行；白名单 `UNRESTRICTED_PAGE_ROUTES = {"/", "/register", "/setup"}` |
| `app/core/audit.py` | `log_audit(action, *, tenant_id, user_id, **detail)` 结构化审计日志（logger 名 `audit`）；接入点：login_success / change_password（auth_service）、ai_split（lesson_plan_service）、ai_generate（generate_service）、export_word（daily_plan 页面）、setup_init_admin / setup_reset_password（setup 页面）；审计调用绝不抛异常 |
| `app/main.py` | `app.on_exception(_on_global_exception)` 记录未捕获异常（ERROR + traceback）；`app.add_middleware(AuthMiddleware)` 注册路由守卫 |
| `app/ui/pages/setup.py` | 系统初始化向导（路由 `/setup`，白名单免登录）；双层保护：网络层（仅 localhost 或 `BOOTSTRAP_ADMIN_ALLOW_REMOTE=true`）+ 应用层（Reset 模式需旧密码验证）；自动运行 Alembic 迁移；无 sys_admin 时显示 Init 表单，已有时显示 Reset 表单 |
| `app/jobs/bootstrap_admin.py` | 系统管理员初始化 CLI：`--init` 模式创建 sys_admin，`--reset-password` 模式重置密码（需旧密码验证）；env 变量缺失时交互式提示 |

**异常体系**（`app/core/exceptions.py`）：`AuthError`、`CryptoError`、`ConfigError`、`AiCallError`、`AiParseError`（均带 `message` 属性）。页面层捕获业务异常展示友好提示（`e.message`），不暴露堆栈；未预期异常由 `app.on_exception` 记录完整 traceback。

## 8. 对外只读 REST API

作为「幼儿园信息管理主系统」的子系统，本模块对外提供教学计划数据的**只读** REST API（路由前缀 `/api/v1`）。

| 文件 | 职责 |
|------|------|
| `app/api/__init__.py` | `create_api_router()` 组装并返回对外路由，由 `app/main.py` 的 `app.include_router()` 注册 |
| `app/api/auth.py` | `ApiPrincipal`、`get_api_principal`（FastAPI 依赖）、`parse_api_keys`、`verify_signature`；API Key 必填（映射 key→tenant_id）+ 可选 HMAC-SHA256 签名（配置 `API_SIGNING_SECRET` 时强制） |
| `app/api/deps.py` | `get_db` 异步会话依赖（可被测试 `dependency_overrides` 覆盖） |
| `app/api/schemas.py` | Pydantic 响应模型（`DailyPlanOut`/`DailyPlanListOut`/`SemesterOut`/`ClassConfigOut`/`HealthOut`/`PageMeta`），**不暴露密钥/密码** |
| `app/api/routes.py` | v1 路由：`GET /health`（免鉴权）、`GET /daily-plans`（分页+过滤）、`GET /daily-plans/{id}`、`GET /semesters`、`GET /classes` |

**租户隔离**：每个 API Key 绑定唯一 `tenant_id`，所有业务查询以鉴权得到的 `tenant_id` 为强制过滤条件，调用方无法越权读取其他租户数据。**未配置** `API_KEYS` 时对外接口默认关闭（返回 401）。详见 [docs/API.md](../docs/API.md)。

仓库层新增只读查询：`daily_plan_repository.list_daily_plans` / `get_daily_plan_by_id`、`semester_repository.list_semesters`、`class_repository.list_class_configs`——均强制携带 `tenant_id` 过滤。


## 9. SQLite 兼容性与 Windows EXE 首次运行支持（2026-06-13）

### SQLite 迁移链修复

Windows EXE 打包使用内嵌 SQLite，迁移链存在 3 处 MySQL 专属语法，已全部修复：

| 迁移文件 | 原问题 | 修复方案 |
|----------|--------|----------|
| `54c20d37a461` | `server_default='text'` → SQL `DEFAULT text`（无引号），SQLite 语法错误 | 改为 `server_default=sa.text("'text'")` |
| `46b9fd5613c3` | 全新 SQLite 无 `model_name` 列时直接 UPDATE/ALTER 失败 | `sa.inspect()` 检测列存在性，不存在则 `op.add_column` |
| `f6d79ac6bf21` | 全新 SQLite 无 `daily_plan` 表时直接 ALTER 失败 | `inspector.get_table_names()` 检测，不存在则 `op.create_table` |

`alembic/env.py` 同步修复：
- 新增 `render_as_batch=True`（支持 SQLite 的 `op.alter_column`）
- PyInstaller 路径一致性：`sys.frozen` 检测 + `os.path.dirname(sys.executable)` 绝对路径

### 首次运行配置向导

#### 新增模块

| 模块 | 路径 | 职责 |
|------|------|------|
| `SetupState` | `app/core/setup_state.py` | `is_setup_complete()` / `mark_setup_complete()`；标记文件 `.kindergarten_setup_complete`；纯文件检查，无 DB 查询；路径适配 PyInstaller |
| `EnvWriter` | `app/core/env_writer.py` | `read_dot_env()` / `write_dot_env()`；原子更新 `.env` 文件；路径适配 PyInstaller |

#### 新增配置字段

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `8080` | 应用监听端口，可通过 `.env` 覆盖，`ui.run(port=settings.PORT)` |

#### 首次运行触发机制

```
frozen exe 启动
  └─ ui.run(show=True)  →  浏览器打开 /
     /  login_page()  →  is_setup_complete()==False  →  navigate.to('/setup')
     /setup  →  is_setup_complete()==False  →  渲染 4 步向导

向导完成
  └─ mark_setup_complete()  →  写 .kindergarten_setup_complete

后续启动
  └─ /  →  is_setup_complete()==True  →  正常渲染登录表单
     /setup  →  is_setup_complete()==True  →  渲染密码重置表单
```

#### 向导 4 步结构（`app/ui/pages/setup.py`）

| 步骤 | 内容 | 可跳过 | 后端调用 |
|------|------|--------|----------|
| Step 1：数据库 & 端口 | 数据库模式（SQLite/MySQL）+ 端口；有变更时写 `.env` + 自动重启 | ✅ | `write_dot_env()` |
| Step 2：创建管理员账号 | 用户名 / 姓名 / 密码 | ❌ | `register_user()` |
| Step 3：AI 接口配置 | API URL / Key / 模型名称 | ✅ | `save_ai_key()` |
| Step 4：完成 | 配置摘要 + 前往登录 | — | `mark_setup_complete()` |

自动重启机制：`subprocess.Popen([sys.executable] + sys.argv[1:])` → 等待 0.8s 确认子进程存活 → `os._exit(0)`；失败降级为"请手动关闭并重新启动"提示。
