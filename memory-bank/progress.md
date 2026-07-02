# 进度记录

## 2026-07-02（dev4.0 P0 线上重构）

### 已完成

- 新建并推送 `dev4.0` 分支。
- 完成 dev4.0 总计划、P0 开发计划、P0 测试计划。
- 完成 P0 monorepo scaffold 并推送：`dae8ced chore: scaffold dev4 monorepo`。
- 完成 Word export spike 并推送：`73e1955 feat: add dev4 word export spike`。
- 完成 Backup target spike 本地验证：WebDAV 目标、统一备份目标合同、上传后读回 SHA-256 校验、认证失败与完整性失败错误分类。
- 完成 MySQL job spike 本地验证：MySQL 8 领取 SQL 合同、`FOR UPDATE SKIP LOCKED`、并发领取互斥、失败重试、状态回写。
- 完成 Storage upload spike 完整验证：PNG/JPEG/DOCX/XLSX 上传校验、hash 元数据、tenant-scoped 对象 key、禁止用户文件名拼路径。
- 完成 Auth/RBAC spike 完整验证：角色、workflow action、self/grade/tenant/system scope、审计动作授权判断。

### 验证

- P0 scaffold：`pnpm check` 通过，`.venv/bin/pytest tests/ -q` 为 `547 passed`，`pnpm audit:deps` 无已知漏洞，SBOM 生成通过。
- Word export spike：`pnpm check` 通过，`pnpm audit:deps` 无已知漏洞，SBOM 生成通过。
- Backup target spike 本地：`pnpm check` 通过，`.venv/bin/pytest tests/ -q` 为 `547 passed`，`pnpm audit:deps` 无已知漏洞，SBOM 生成通过。
- MySQL job spike 本地：`pnpm check` 通过，`.venv/bin/pytest tests/ -q` 为 `547 passed`，`pnpm audit:deps` 无已知漏洞，SBOM 生成通过。
- Storage upload spike：`pnpm check` 通过，`.venv/bin/pytest tests/ -q` 为 `547 passed`，`pnpm audit:deps` 无已知漏洞，SBOM 生成通过。
- Auth/RBAC spike：`pnpm check` 通过，`.venv/bin/pytest tests/ -q` 为 `547 passed`，`pnpm audit:deps` 无已知漏洞，SBOM 生成通过。

### 下一步

- 推送 Auth/RBAC spike。
- 继续 P0 AI Key 加密合同 spike。

## 2026-06-30（dev3.4 登录系统恢复）

### 已完成

- 从 `main` 新建 `dev3.4` 分支。
- 新增 `memory-bank/login/`：设计、开发计划、测试计划、进度。
- 恢复登录系统核心能力：登录页、首次管理员初始化、注册待审核、管理员用户管理、管理员重置密码、个人资料与改密。
- 页面用户上下文从固定单用户切换为 JWT + 数据库刷新校验；业务页面按当前登录用户 `tenant_id/user_id` 运行。
- `/setup` 调整为登录用户个人 AI 配置页，支持 text/vision Key；`/settings` 限系统管理员；`/prompts` 限教研管理员与系统管理员。
- 停用启动时默认 `admin` 自动创建；初始化 CLI 支持 password-file/stdin；Windows/Linux 安装包增加管理员初始化入口，首次启动页兜底。

### 自动测试

- 认证与 UI 权限相关回归：`75 passed`。
- 全量回归：`543 passed`。

## 2026-06-28（课程审议记录子系统）

### 已完成

- 新增课程审议记录模块：数据模型、仓库、AI 客户端、服务层、Word 导出器、NiceGUI 页面、菜单/首页入口、提示词管理入口。
- 新增 Alembic 迁移 `a6c4d8e2f9b1`：创建 `course_review_activity` 表，扩展 `prompt_task_type`，为 `export_records` 增加 `course_review_activity_id`。
- 新增 `memory-bank/coursereviewactivity/` 文档：设计、开发计划、测试计划、进度。
- 分阶段自动测试：P1 `26 passed`，P2 `12 passed`，P3 `6 passed`，P4 `16 passed`。
- 课程审议相关回归：`60 passed`；全量回归：`529 passed`。

### 当前状态

- 用户手动测试通过，课程审议记录子系统主流程完成。
- 手测已覆盖：设置读取、AI 生成、编辑保存、导出 Word、历史重新导出、删除。

## 2026-06-21（跨电脑复测交接）

### 已完成

- 处理一对一倾听第 1 轮测试反馈并推送 `dev3.1`：提交 `57fd14d`。
- 修复 3 项问题：
  - 自动选工作日节假日误判：改为按年拉取法定节假日并缓存，避免并发逐日请求触发 429。
  - 一键导入图片：由“必须 15 张”调整为“至少 15 张，按文件名取前 15 张”。
  - 工作日自动分配：由“固定前三周”调整为“全月随机 3 个工作日（排除周末与法定节假日）”。
- 完成自动化验证：全量测试 `466 passed`。
- 已创建并推送复测标签：`v3.1.0-beta2`（指向 `57fd14d`）。

### 跨电脑复测建议

- 若用安装包复测：直接下载 `v3.1.0-beta2` 对应构建产物（Actions/release 资产）。
- 若用源码复测：拉取 `dev3.1` 最新后启动 `.venv/bin/python -m app.main`。
- 进入「一对一倾听」优先复测 3 个回归点：
  - 节假日日期不应被自动选为工作日（如 2026-05-01）。
  - 上传超过 15 张时应自动取前 15 张并提示。
  - 自动日期应分布在整月，不再集中在月初前三周。

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

## 2026-05-17

### 开发环境升级

- **Python 升级**：`.venv` 由 Python 3.12.3 升级至 **Python 3.14.4**（`/home/admin/.local/bin/python3.14`）。
- **依赖重装**：删除旧 `.venv`，用 `python3.14 -m venv .venv` 重建，`pip install -r requirements.txt` 全量安装。
- **验证**：`pytest tests/ -q` 全部通过（**89 passed, 0 warnings**），相比 3.12 环境消除了 passlib/json-logger DeprecationWarning（已知问题，代码层已提前切换至 argon2-cffi + pythonjsonlogger.json）。

### 当前状态

- Python：3.14.4
- 依赖与旧环境版本一致（nicegui 3.12.0、SQLAlchemy 2.0.49、alembic 1.18.4 等）
- 测试：89 passed, 0 warnings

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

## 2026-05-17

### 已完成（阶段 3）

- **Step 3.1 ✅**：加密工具 `app/core/crypto.py` — `encrypt` / `decrypt`（Fernet 对称加密）；`app/core/exceptions.py` 新增 `CryptoError`、`ConfigError`。
  - `ENCRYPTION_KEY` 字符串 → UTF-8 编码取前 32 字节补零 → `base64.urlsafe_b64encode` → 合法 Fernet Key；Fernet 实例模块级初始化一次。
  - `tests/test_crypto.py` — **8 passed**（加密结果异于原文、往返还原、Unicode 往返、Fernet 随机 IV、篡改密文报错、非法字符串报错、空字符串报错）。
  - 手工验收：自动化测试全部通过，无需额外手工操作。

- **Step 3.2 ✅**：`app/core/models/ai_key.py` — `AiApiKey` 数据模型；Alembic 迁移（add ai_api_key table）；`app/repository/ai_key_repository.py` — `save_ai_key` / `get_active_ai_key` / `get_decrypted_key`。
  - `app/core/models/__init__.py` 更新：新增 `AiApiKey` 导入，确保 Alembic autogenerate 可发现。
  - `tests/test_ai_key_repository.py` — **11 passed**（密文存储、active 记录可取、解密还原、Key 轮换旧记录 inactive、租户隔离）。
  - Alembic 迁移执行成功；`DESCRIBE ai_api_key;` 字段与定义一致。

- **Step 3.3 ✅**：`app/ui/pages/settings.py` 新增 AI 接口配置区块。
  - 新增辅助函数 `_mask_api_key`：明文末4位可见，其余替换为 `sk-****` 前缀。
  - "保存"按钮：判断 Key 是否修改（与脱敏字符串对比），复用或更新 Key 后加密入库。
  - "验证连接"按钮：内联 `httpx.AsyncClient` 调用 `{api_base_url}/models`，超时 10 秒，显示成功/失败提示。
  - 页面加载回填：AI 地址正常回填；Key 以脱敏形式展示，解密失败时提示重新配置。
  - **手工验收通过**（2026-05-17）：密文存储 ✅ / 脱敏显示 ✅ / 验证连接 ✅。

- **Bug 修复 — 登录响应极慢（IPv6 超时）**：
  - 现象：点击登录等待 2+ 分钟才响应。
  - 根因：`aliyun.ywyz.tech` 同时有 A 和 AAAA 记录；`aiomysql` 优先尝试 IPv6（`2408:4002:...`），该地址在 13306 端口不通，等待 TCP 超时（约 2 分 15 秒）后才降级 IPv4。
  - 修复：`.env` 中 `DATABASE_URL` 将主机名改为 IPv4 地址（`47.116.40.89`），绕过 DNS 双栈解析。
  - 同步修改：`app/core/database.py` 将 `pool_pre_ping=True` 改为 `False`（避免每次取连接前额外发 `SELECT 1` 增加往返延迟），新增 `pool_recycle=1800` 防止服务端主动断连后复用报错。
  - **验证通过**：登录响应恢复正常。
  - 后续建议：在 DNS 管理面板删除 `aliyun.ywyz.tech` 的 AAAA 记录（根治），届时可将 `DATABASE_URL` 改回域名。

### 当前状态

- **阶段 3（Step 3.1~3.3）全部完成并通过手工验收。**
- 自动化测试（Step 3 范围）：`test_crypto.py` 8 passed / `test_ai_key_repository.py` 11 passed。
- 待执行：Step 3 全量回归测试 + 文档更新 + 推送 GitHub。

### 全量测试与推送（已完成）

- `pytest tests/ -v` — 约 90 passed，0 warnings（含 8 test_crypto + 11 test_ai_key_repository）。
- 文档更新：`memory-bank/architecture.md` 阶段 3 内容补全。
- GitHub 推送：`git push origin dev2.0` 成功。

### 当前状态（文档整理完成后）

- 阶段 0~3 全部完成，已推送 `dev2.0` 分支。
- `memory-bank/` 文档已同步：tech-stack.md（Python 3.14/argon2-cffi）、implementation-plan.md（✅ 标注）、architecture.md（Section 10 编号修正、DatePanel 归位）。
- 下一步：**阶段 4 Step 4.1** — AI 客户端基础 `app/integration/ai_client/base.py`。

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

## 2026-05-17（续）

### 已完成：为 AI 配置新增 model_name 字段

- **背景**：AI API Key 表缺少模型名称字段，导致后续 ai_client 层无法知道应使用哪个模型。
- **数据库**：`app/core/models/ai_key.py` 新增 `model_name: String(128), NOT NULL, server_default='gpt-4o-mini'`；Alembic 迁移 `46b9fd5613c3` 已应用（含回填现有 NULL 值 → 'gpt-4o-mini'）。
- **附注（数据库状态修复）**：另一台机器曾用 `38441cbdef11` 迁移将 `model_name` 列以 nullable 形式加入 DB，但迁移文件未推送到仓库；本次将 DB alembic_version 重置为 `1a0d0e46f700` 后编写 `46b9fd5613c3` 完成对齐。
- **仓库层**：`save_ai_key` 新增 `model_name: str = "gpt-4o-mini"` 参数，写入新记录时赋值。
- **Settings UI**：AI 配置区块新增"模型名称"自由文本输入框（placeholder 提供常用示例）；加载时自动回填；保存前校验非空。
- **测试**：原有 `save_ai_key` 调用全部补充 `model_name` 参数；新增 `TestModelName` 测试类（3 个用例）；全量测试 **92 passed, 0 warnings**。

### 当前状态

- Alembic 当前版本：`46b9fd5613c3 (head)`
- 全量测试：92 passed, 0 warnings（Python 3.14.4）
- 下一步：阶段 3（Step 3.1）加密工具 `app/core/crypto.py`（已在之前阶段完成），或 ai_client 层实现（Step 4.1）

---


> Stage 4（教案拆分/年龄适配）及后续阶段的开发进度详见 [daily-plan/progress.md](daily-plan/progress.md)。

---

## 2026-06-13（Windows EXE SQLite 兼容性修复 + 首次运行配置向导）

### 背景

v3.0.0-beta.2 Windows EXE 打包后在全新 Windows 机器上首次运行出现两类问题：
1. `/setup` 页面返回 500 错误：`OperationalError: no such column: user.display_name`
2. 首次运行时没有任何引导页面，用户不知道需要访问 `/setup`

### 1. SQLite 迁移链兼容性修复

**根本原因链：**
- 迁移 `54c20d37a461` 中 `server_default='text'`（Python 字符串）被 SQLAlchemy 渲染为 SQL `DEFAULT text`（无引号），SQLite 将 `text` 视为标识符而非字符串字面量 → `op.add_column` 失败 → 整个事务回滚 → `user.display_name` 列永远无法创建
- MySQL 不受影响（MySQL 对 ENUM 列 DEFAULT 有特殊宽松处理）

**修复文件：**

| 文件 | 修复内容 |
|------|----------|
| `alembic/versions/54c20d37a461_dev3_0_phase_b_new_tables_and_columns.py` | `server_default='text'` → `server_default=sa.text("'text'")` |
| `alembic/versions/46b9fd5613c3_add_model_name_to_ai_api_key.py` | 用 `sa.inspect()` 检查 `model_name` 列是否存在：不存在时 `op.add_column`，存在时走 MySQL 的 UPDATE+ALTER 路径 |
| `alembic/versions/f6d79ac6bf21_add_daily_plan_table.py` | 检查 `daily_plan` 表是否存在：不存在时直接 `op.create_table`（全新 SQLite），存在时走 MySQL 的 ALTER 路径 |
| `alembic/env.py` | ① 添加 PyInstaller 路径一致性（`sys.frozen` 检测 + `os.path.dirname(sys.executable)`）；② 两个 `context.configure()` 均添加 `render_as_batch=True` |

**验证：**
- SQLite 迁移链从空库完整运行到 HEAD（`4e2e0e079e56`）✅
- `user.display_name`、`ai_api_key.key_type` 等关键列均正确创建 ✅
- MySQL 生产用户已迁移版本不受影响（alembic_version 不重置）✅

### 2. 首次运行环境配置向导（First-Run Setup Wizard）

**新增文件：**

| 文件 | 职责 |
|------|------|
| `app/core/setup_state.py` | `is_setup_complete()` / `mark_setup_complete()`：纯文件检查（`.kindergarten_setup_complete` 标记文件），无 DB 查询，路径适配 PyInstaller |
| `app/core/env_writer.py` | `read_dot_env()` / `write_dot_env()`：原子更新 `.env` 文件，路径适配 PyInstaller |
| `tests/test_setup_state.py` | 6 个单元测试 |
| `tests/test_env_writer.py` | 10 个单元测试 |

**修改文件：**

| 文件 | 变更 |
|------|------|
| `app/core/config.py` | 新增 `PORT: int = 8080` 字段（通过 `.env` 持久化，修改后需重启） |
| `app/main.py` | `ui.run(port=settings.PORT, ...)` 替换硬编码 `8080` |
| `app/ui/pages/login.py` | 登录页顶部同步检测 `is_setup_complete()`：未完成 → `navigate.to('/setup')` |
| `app/ui/pages/setup.py` | **完整重写**为 4 步向导（未完成时），已完成时退化为原有密码重置表单 |

**向导 4 步设计：**

| 步骤 | 内容 | 可跳过 |
|------|------|--------|
| Step 1：数据库 & 端口 | 数据库模式（SQLite/MySQL）+ 端口号；有变更时写 `.env` 并尝试自动重启 | ✅（"使用默认配置"按钮） |
| Step 2：创建管理员账号 | 用户名 / 姓名 / 密码 / 确认密码；调用 `register_user()` | ❌（必填）|
| Step 3：AI 接口配置 | API URL / API Key / 模型名称；调用 `save_ai_key()` | ✅（"跳过，稍后配置"）|
| Step 4：完成 | 显示配置摘要；调用 `mark_setup_complete()`；跳转登录 | — |

**自动触发机制：**
- `main.py`：`show=True`（frozen 模式）→ 浏览器自动打开 `/`
- `login.py`：`is_setup_complete() == False` → 重定向到 `/setup`
- 标记文件写入后：`/` 正常渲染登录表单，`/setup` 显示密码重置表单

**重启机制：** Step 1 有配置变更时，先尝试 `subprocess.Popen([sys.executable] + sys.argv[1:])`（等待 0.8s 确认子进程存活），成功则 `os._exit(0)`；失败降级为"请手动关闭并重新启动应用"提示。

### 测试统计

| 时间节点 | 测试数 |
|---------|--------|
| 本次修复前（dev3.0 交付基准） | 342 passed |
| SQLite 迁移修复后 | 367 passed（+25：迁移 smoke test 重验）|
| 首次运行向导实现后 | **383 passed** |

### Alembic 当前 HEAD

- `4e2e0e079e56`（drop_invite_code_table）

### 全量测试

```
383 passed, 0 failed, 0 warnings（Python 3.14.4）
```

## 2026-06-20（dev3.1：一对一倾听 P8/P8d/P9）

### 已完成

- **P8a 后端**：`export_repository.save_export_record(listening_record_id=...)`；`listening_repository.delete_domains_by_record`；`indicator_repository.list_indicators_by_ids`；`listening_service.load_record_detail` / `to_export_payload`（纯函数）/ `update_record_with_all`（覆盖保存，与 `save_record_with_all` 共用 `_persist_domains`）。
- **P8b 历史 UI**：`/one-on-one-listening` 底部历史区（年月/姓名筛选、只读详情弹窗、单条「导出合并」「导出按领域 zip」、多选「批量按领域 zip」、删除含图片+确认弹窗）；写 `export_records(listening_record_id)` + 审计 `export_listening`；表单内既有导出同步补审计与关联。
- **P8c 编辑**：历史「编辑」载入记录到表单（DB blob 重建 `CompressedImage`）→ 覆盖保存；顶部「编辑中」横幅 +「取消编辑/新建」。
- **P8d 体验增强**：① 领域时间方案 C（每领域独立年月 + 各自/一键自动选取工作日）；② 提示词页新增 `one_on_one_listening` Tab；③ 五领域改 `ui.tabs` 布局；④ 图片统一横版 `normalize_to_landscape`（上传即归一）；⑤ 一键导入 15 张按文件名分配五领域 +「生成全部领域」串行。
- **P9 文档**：更新 `architecture.md`（§10 一对一倾听子系统）、`one-on-one-listening/{progress,dev-plan,test-plan}.md`、本文件。

### 测试 / 冒烟

- 全量回归 **461 passed**（基线 444 +17 新增）；一对一倾听相关 107 passed。
- 本地 sqlite 启动冒烟：`NiceGUI ready`；`/one-on-one-listening`、`/prompts`、`/game-observation` 均 `HTTP 200`。

### Alembic 当前 HEAD

- `9ec29bdc3822`（dev3.1 seed indicator catalog）。

### 待办

- 🧑 用户手动验收一对一倾听全功能（见 `one-on-one-listening/progress.md` 验收清单）。

## 2026-06-28（dev3.2：自制教玩具子系统启动）

### 已完成

- 完成项目文件与 `memory-bank` 阅读，确认复用一日活动计划、游戏观察、一对一倾听的分层模式。
- 确认模板 `templates/homemadeteaching.docx`：标题 + 5 行 2 列表格，字段为班级、姓名、教玩具名称、所用材料、玩法。
- 新建 `memory-bank/homemadeteaching/`：
  - `design.md`
  - `dev-plan.md`
  - `test-plan.md`
  - `progress.md`
- 更新 `overview.md` 与 `architecture.md`，登记自制教玩具子系统设计入口与规划中的架构变更。

### 当前计划

- P1~P5 已实现：设置页教师姓名、`homemade_teaching_toy` 模型与仓库、AI JSON 客户端与服务层、Word 导出、NiceGUI 页面/菜单/首页入口/提示词 Tab。
- 相关自动测试：54 passed；临时 SQLite `alembic upgrade head` 通过。
- 全量回归：`pytest tests/ -q` → **497 passed**。
- 用户手动验收：测试通过，能够运行（见 `homemadeteaching/progress.md`）。
