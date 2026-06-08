# 开发者指南

面向参与本系统开发与维护的工程师。阅读顺序建议：本文 → [memory-bank/PRD.md](../memory-bank/PRD.md) → [memory-bank/architecture.md](../memory-bank/architecture.md) → [memory-bank/progress.md](../memory-bank/progress.md)。

---

## 1. 环境搭建

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # 填写连接串与密钥
.venv/bin/alembic upgrade head
.venv/bin/python -m app.main  # http://0.0.0.0:8080
```

- 开发环境 Python 3.14（最低 3.12）。密码哈希使用 `argon2-cffi`（已替换 passlib，兼容 3.13+）。
- VS Code 调试：使用「运行应用 (python -m app.main)」配置（`module: app.main` + `cwd: ${workspaceFolder}`），不要以文件路径方式启动，否则 `ModuleNotFoundError: No module named 'app'`。

## 2. 分层架构与约定

```
ui  →  service  →  repository  →  models(ORM)
            ↘ integration（ai_client / holiday_client / word_export）
auth / core 为横切支撑
```

- **UI 层**：仅交互与展示，**不写权限逻辑**（统一在 `app/auth/`）。
- **Service 层**：业务编排；**禁止直接发 HTTP 请求**（AI 调用一律走 `app/integration/ai_client/`）。
- **Repository 层**：封装 SQL；**所有查询强制携带 `tenant_id` 过滤**；分页用 `limit`/`offset`，禁止全量加载后切片。
- **Integration 层**：外部依赖封装，含超时、重试、降级。

### 数据隔离（强制）

所有业务表必须包含：`tenant_id`、`user_id`、`created_at`、`updated_at`。查询必须按 `tenant_id` 过滤，避免跨租户泄露。

### 鉴权与角色

- 账号密码 + JWT（HS256，`app/auth/jwt.py`）+ RBAC：`teacher` / `teaching_admin` / `sys_admin`。
- 页面访问由 `app/auth/middleware.py` 的 `AuthMiddleware` 统一守卫：未登录访问受限页面重定向到 `/`；白名单 `UNRESTRICTED_PAGE_ROUTES = {"/"}`。`/api/*` 等非页面路由放行（由 API Key 鉴权）。
- 用户注册策略（首期）：不开放公开自助注册，仅 `sys_admin` 可在 `/user-admin` 页面创建账号。
- 账号管理第二阶段：支持系统管理员初始化脚本、账号启停、重置密码、列表筛选与分页。
- 页面内仍保留 `_get_current_user()` 作为纵深防御。

### 管理员初始化脚本

- 入口：`python -m app.jobs.bootstrap_admin`
- 默认关闭：仅当 `BOOTSTRAP_ADMIN_ENABLED=true` 且 `BOOTSTRAP_ADMIN_PASSWORD` 非空时才执行。
- 幂等：同租户下若已存在同名 `sys_admin`，脚本输出跳过信息并退出 0。
- 安全：脚本仅记录账号标识，不记录明文密码。

### 敏感信息

- AI API Key：`app/core/crypto.py`（Fernet）加密入库，页面脱敏展示（`sk-****` + 末 4 位）。
- 密码：Argon2，禁止 MD5/SHA1。
- 明文密钥、密码禁止写入任何日志。

### 异常体系

`app/core/exceptions.py`：`AuthError` / `CryptoError` / `ConfigError` / `AiCallError` / `AiParseError`（均带 `.message`）。页面捕获业务异常展示 `e.message`，不暴露堆栈；未预期异常由 `app/main.py` 的 `app.on_exception(_on_global_exception)` 记录完整 traceback。

### 审计日志

`app/core/audit.py` 的 `log_audit(action, *, tenant_id, user_id, **detail)`，结构化记录。已接入审计点：`login_success` / `change_password` / `ai_split` / `ai_generate` / `export_word`。审计调用内部包裹 try/except，**绝不影响主流程**。

## 3. 数据库与迁移

- ORM：SQLAlchemy 2（`Mapped` / `mapped_column`），`AsyncSession`。
- 主键在 SQLite 测试下需 `BigInteger().with_variant(Integer, "sqlite")` 以支持自增。
- **禁止**应用启动时 `create_all()`；所有 schema 变更走 Alembic：

```bash
.venv/bin/alembic revision --autogenerate -m "描述"
# 人工检查生成的迁移（autogenerate 不能识别全部约束）
.venv/bin/alembic upgrade head
```

- 当前 head：`d60766786069`。表清单：`users` / `semester_config` / `class_config` / `ai_api_key` / `daily_plan` / `prompt_template` / `export_records`。
- 连接串含 `@`、`%` 等特殊字符需 URL 编码；`alembic/env.py` 已对 `%` 做 `%%` 转义。

## 4. AI 集成约定

- 统一入口 `app/integration/ai_client/base.py::call_ai`（httpx 超时 60s + tenacity 指数退避重试 3 次）。
- 返回值强约束 JSON schema，解析失败抛 `AiParseError` 并记录日志。
- 拆分 / 适配 / 一日活动生成分别封装在 `lesson_plan_client.py` / `adapt_client.py` / `generate_client.py`，各自内置默认 system prompt；数据库激活的提示词优先覆盖默认。

## 5. Word 导出约定

- 主方案 `python-docx`，打开 `templates/teacherplan.docx`（19 行 2 列单表）按单元格填充，禁止自行重排结构。
- 差异段落字体设为红色 `RGBColor(255, 0, 0)`；中文需显式指定字体（宋体），否则乱码。
- 模板缺失时降级 `_export_from_scratch` 从零建表。

## 6. 测试规范

```bash
.venv/bin/pytest tests/ -q            # 全量
.venv/bin/pytest tests/test_xxx.py -v # 单文件
```

- `pytest.ini` 设 `asyncio_mode = auto`，异步测试无需逐个标注。
- `tests/conftest.py` 提供 `async_session` fixture（SQLite 内存库，每测试函数建表/拆表）。
- AI / Word / DB 调用使用 mock / fixture 隔离；每个 service 函数必须有单元测试。
- API 路由测试用 `httpx.ASGITransport` 构建独立 FastAPI app，`dependency_overrides[get_db]` 注入内存库会话，`monkeypatch` 覆盖 `settings.API_KEYS`。
- 当前基线：**242 passed, 0 warnings**。

## 7. 对外 REST API 开发

- 路由集中在 `app/api/routes.py`，鉴权依赖 `app/api/auth.py::get_api_principal`，响应模型在 `app/api/schemas.py`（不暴露密钥/密码）。
- 鉴权返回 `ApiPrincipal(tenant_id=...)`，端点以该 `tenant_id` 作为查询隔离条件。新增端点务必沿用此模式，禁止从查询参数直接取 `tenant_id`。
- 详见 [API.md](API.md)。

## 8. 部署（生产）

- 云服务器直装 + systemd 托管 `python -m app.main`，前置 Nginx 反向代理（TLS、限流、来源限制）。
- 启用对外 API：在 `.env` 配置 `API_KEYS`（建议同时配置 `API_SIGNING_SECRET`），并在反向代理层限制 `/api/` 来源 IP。
- 备份：定期备份 MySQL 与 `exports/` 导出文件。

## 9. 常见陷阱

1. NiceGUI 底层 async，UI 状态更新需正确传递；`DatePanel` 回调若为 async 须 `await`。
2. SQLite 测试与 MySQL 类型差异：主键用 `with_variant`。
3. python-docx 中文字体须显式指定，否则乱码。
4. Alembic autogenerate 不识别全部约束，迁移后人工核对 SQL。
5. 远程 MySQL 域名若有 AAAA 记录可能导致 IPv6 连接超时；必要时连接串直接用 IPv4。

## 10. 手动验证步骤（账号管理第二阶段）

完整测试清单见 [MANUAL_TESTING.md](MANUAL_TESTING.md)。

1. 初始化系统管理员
    - 设置环境变量：`BOOTSTRAP_ADMIN_ENABLED=true`、`BOOTSTRAP_ADMIN_PASSWORD=<强密码>`，可选设置 tenant 和用户名。
    - 执行：`.venv/bin/python -m app.jobs.bootstrap_admin`
    - 预期：首次创建成功；重复执行提示已存在并跳过。
2. 登录与入口可见性
    - 使用系统管理员登录，主页可见“账号管理”。
    - 使用教师账号登录，主页不可见“账号管理”；直接访问 `/user-admin` 显示无权限。
3. 创建账号
    - 在 `/user-admin` 创建 teacher / teaching_admin 账号。
    - 预期：创建成功后列表刷新可见；重复用户名提示失败。
4. 启停账号
    - 在账号列表对某教师执行停用。
    - 预期：该账号登录失败；重新启用后可再次登录。
5. 重置密码
    - 在账号列表对某账号执行重置密码。
    - 预期：旧密码登录失败，新密码登录成功。
6. 筛选与分页
    - 输入用户名关键字筛选，并切换页码。
    - 预期：结果总数、当前页数据与分页按钮状态正确。
