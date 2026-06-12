# 一日活动计划子系统 — 开发进度

> 本文档记录从阶段 4（教案拆分与年龄适配）起的一日活动计划子系统开发进度。
>
> 系统级进度（阶段 0~3：项目骨架、账号鉴权、学期配置、AI Key 管理）详见 [../progress.md](../progress.md)。

---

## 2026-05-17（阶段 4）

### 已完成（阶段 4：教案拆分与年龄适配）

- **Step 4.1 ✅**：`app/integration/ai_client/base.py` — 通用 AI 请求函数 `call_ai()`；`httpx.AsyncClient` 超时 60s；`tenacity` 重试 3 次（指数退避 2s→4s→8s）；HTTP 4xx/5xx 提取错误描述写入 `AiCallError.message`；解析失败抛 `AiParseError`；`app/core/exceptions.py` 新增 `AiCallError`、`AiParseError`。
  - `tests/test_ai_client_base.py` — **6 passed**（正常响应、无效 JSON content、非 JSON body、HTTP 500 重试3次、HTTP 400、缺少 choices 字段）。

- **Step 4.2 ✅**：`app/integration/ai_client/lesson_plan_client.py` — `split_lesson_plan()`；内置默认 system prompt（英文 key 约束）；必填字段验证（5 个 key）；多余字段过滤。
  - `tests/test_lesson_plan_client.py` — **5 passed**（正常返回、自定义 prompt、缺字段报错、空 dict 报错、多余字段过滤）。

- **Step 4.3 ✅**：`app/integration/ai_client/adapt_client.py` — `adapt_activity_process()`；内置年龄适配 prompt（小班/中班/大班三套策略）；空原文前置校验不发请求；输出字段 `adapted_process` 验证。
  - `tests/test_adapt_client.py` — **5 passed**（正常返回、三个年龄段、缺字段报错、空原文报错、自定义 prompt）。

- **Step 4.4 ✅**：`app/service/diff_service.py` — `compute_diff()`；按 `。？！\n` 分句；`difflib.SequenceMatcher` 逐句比对；返回改写文视角结果（`{"text": str, "changed": bool}`）。
  - `tests/test_diff_service.py` — **8 passed**（完全相同、一句改变、空输入、空改写文、全部改变、新增句、原文删除句不出现、多行文本）。

- **Step 4.5 ✅**：`app/core/models/daily_plan.py` — `DailyPlan` 表（20 个字段）；Alembic 迁移 `f6d79ac6bf21`；`app/core/models/__init__.py` 注册 `DailyPlan`；`app/repository/daily_plan_repository.py` — `save_daily_plan`（同日期 upsert）、`get_daily_plan_by_date`。
  - `alembic upgrade head` 执行成功，迁移版本：`f6d79ac6bf21 (head)`。

- **Step 4.6 ✅**：`app/service/lesson_plan_service.py` — `process_lesson_plan()` 编排完整流程（AI Key 获取→拆分→适配→差异比对）；`LessonPlanResult` dataclass 包含全部字段；AI Key 缺失抛 `ConfigError`。
  - `tests/test_lesson_plan_service.py` — **3 passed**（完整流程返回 LessonPlanResult、差异正确标注、无 Key 抛 ConfigError）。

- **Step 4.7 ✅**：`app/ui/pages/daily_plan.py` — 每日活动计划页面（路由 `/daily-plan`）；顶部复用 `DatePanel` 组件；教案输入区 + "连接 AI 拆分"按钮；5 个字段自动回填 + 改写原文折叠展示；"保存草稿"（upsert daily_plan 表）；`app/main.py` 注册路由；`app/ui/pages/home.py` 添加导航入口。
  - 手工验收通过：选择日期 → 粘贴教案 → AI 拆分 → 字段回填 → 保存草稿 → 刷新页面后草稿回填。

### Bug 修复记录（阶段 4 手工测试期间）

| 编号 | 现象 | 根因 | 修复 |
|------|------|------|------|
| BL-03 | 选择日期后点击"连接 AI 拆分"提示"⚠ 请先选择日期" | `DatePanel.on_date_change` 回调若为 async 函数，`_update_info` 中调用未加 `await`，协程创建后被丢弃，`state["selected_date"]` 永远为 None | `date_panel.py._update_info` 结尾用 `asyncio.iscoroutine()` 检测回调返回值，若为协程则 await；空日期早返回分支同样修复 |
| BL-04 | AI 调用失败时仅显示通用提示"请检查网络或 API Key 是否有效"，无法定位具体原因 | `daily_plan.py` 中 `except AiCallError` 丢弃了 `e.message`；`base.py` 中 HTTP 错误未提取响应体 | `base.py` 提取响应体中的 `error.message / message / detail` 字段写入 `AiCallError.message`；`daily_plan.py` 将 `e.message` 展示到页面 |

### 已知问题（待 Step 5 修复）

| 编号 | 问题 | 影响 | 修复计划 |
|------|------|------|---------|
| KI-01 | AI 返回的教案拆分/年龄适配内容格式不稳定，存在字段包含 markdown 标记（如 `**重点：**`）、多余换行、数字列表格式不一致等情况 | 拆分结果回填后需人工清理格式；差异比对精度受分句格式影响 | Step 5 提示词管理实现后，在拆分/适配 system prompt 中明确输出格式约束 |

### 全量测试结果

- 自动化测试：**119 passed, 0 failed, 0 warnings**（Python 3.14.4）
- Alembic 当前版本：`f6d79ac6bf21 (head)`，含 5 张业务表（users / semester_config / class_config / ai_api_key / daily_plan）

---

## 2026-05-17（阶段 5：提示词管理）

### 已完成

- **Step 5.1 ✅**：`app/core/models/prompt_template.py` — `PromptTemplate` ORM 模型；Alembic 迁移 `bcd07e51527d`（add prompt_template table）；`app/core/models/__init__.py` 注册 `PromptTemplate`。
  - task_type Enum 初始值：`split` / `adapt` / `generate`（后续在 5.x 扩展）。
  - 联合索引：`(tenant_id, user_id, task_type)`；同一用户同一任务类型只能有一条 `is_active=True` 记录。

- **Step 5.2 ✅**：`app/repository/prompt_repository.py` — 4 个异步函数。
  - `get_active_prompt` / `save_new_version` / `rollback_to_version` / `list_versions`
  - `tests/test_prompt_repository.py` — **16 passed**（TestSaveNewVersion ×5 / TestGetActivePrompt ×3 / TestRollbackToVersion ×3 / TestListVersions ×3 / TestTenantIsolation ×2）。

- **Step 5.2b ✅**：`app/service/lesson_plan_service.py` 接入 `prompt_repository`。
  - `process_lesson_plan()` 在 `split_system_prompt` / `adapt_system_prompt` 为 `None` 时，先查 DB 激活版本，有则覆盖；否则继续使用 AI 客户端内置默认。
  - **KI-01 修复**：`DEFAULT_SPLIT_PROMPT` 与 `DEFAULT_ADAPT_PROMPT` 均追加明确格式约束（禁 Markdown 标记、步骤间句号自然衔接、无数字编号换行、无多余空行）。

- **Step 5.3 ✅**：`app/ui/pages/prompt_mgmt.py` — 提示词管理页面（路由 `/prompts`）；7 Tab；每 Tab 含编辑区 + 保存 + 历史版本 + 回滚。

- **Step 5.x ✅**：将 `task_type` Enum 从 3 值扩展为 7 值。
  - **变更**：`generate` → `morning_exercise` / `morning_talk` / `area_game` / `outdoor_game` / `daily_reflection`。
  - **数据库**：新建 Alembic 迁移 `e2a3f1b8c9d0`（expand prompt_task_type enum）；已应用到 MySQL。
  - **新文件**：`app/integration/ai_client/generate_client.py` — 5 种活动类型内置默认提示词（含输出格式约束）；模块级 `GENERATE_DEFAULTS: dict[str, str]` 供服务层查取。

### Bug 修复记录（阶段 5）

| 编号 | 现象 | 根因 | 修复 |
|------|------|------|------|
| BL-05 | Step 5.2b 合入后，`test_process_lesson_plan_success` 等旧测试失败 | 测试未 mock `get_active_prompt`，service 实际调用时 `AsyncMock` session 返回协程对象而非模型实例，导致 `.content` 属性报错 | 两个受影响的旧测试补加 `patch("app.service.lesson_plan_service.get_active_prompt", new=AsyncMock(return_value=None))` |

### 全量测试结果

- 自动化测试：**137 passed, 0 failed, 0 warnings**（Python 3.14.4）
- Alembic 当前版本：`e2a3f1b8c9d0 (head)`，含 6 张业务表

---

## 2026-05-30（Step 5 手测反馈修复：按钮一键生成 + 导出分单元格）

### 背景

用户在 Step 5 手动测试 `/daily-plan` 页面后反馈两个问题：

1. **按钮冗余**：一日活动各小节（晨间活动/晨间谈话/区域游戏/户外游戏）各有独立「AI 生成」按钮，需逐个点击。要求：除「集体活动」（走拆分按钮）与「一日活动反思」外，其余应一键生成。
2. **导出未分单元格**：Word 导出时同一项目内容全部塞进一个单元格，需按 `templates/teacherplan.docx` 模板结构分单元格存放。

### 已完成

- **问题一（按钮一键生成）** — `app/ui/pages/daily_plan.py`：
  - 删除晨间活动/晨间谈话/区域游戏/户外游戏 4 个独立「AI 生成」按钮。
  - 新增「一键生成一日活动」按钮 `_gen_all_daily`：用 `asyncio.gather(..., return_exceptions=True)` 并发调用 4 次 `generate_activity_content`，各用独立 `AsyncSessionLocal`；成功项回填，失败项保留原值并标注。

- **问题二（导出分单元格）** — `app/integration/word_export/exporter.py` 重写：
  - 主方案改为 `Document(templates/teacherplan.docx)` 打开模板填充既有单元格，子字段分落到对应行。
  - 新增 `_parse_fields(text)`：将生成文本解析为 `{标签: 内容}` 字典，落到各子单元格。
  - 「活动过程」差异标红逻辑保留（`_fill_process_cell`，红字 `RGBColor(255,0,0)`）。

- **支持策略对齐** — `app/integration/ai_client/generate_client.py`：区域游戏 / 户外游戏 prompt 增加「支持策略」段输出。

### 全量测试结果

- **152 passed, 0 failed, 0 warnings**（Python 3.14.4）

---

## 2026-05-31（阶段 7 收尾：near_holiday 接入 + 补单元测试）

### 背景

Step 6 Word 导出手测通过。阶段 7「一键生成一日活动」核心已实现，但存在两个收尾缺口：
1. `near_holiday`（临近节假日）上下文未接入生成流程。
2. `generate_client` / `generate_service` / `export_repository` 三个模块缺单元测试。

### 已完成

- **near_holiday 上下文接入** — `app/integration/ai_client/generate_client.py`：
  - 抽出 `_build_prefix(context)`：拼接「班级：年级班名」+「教学周：第N周 周X」。
  - 新增 `_holiday_hint(context)`：`near_holiday is True` 时返回节日提示，`daily_reflection` 不注入。
  - `_build_user_content` 改为消费 `week_number`/`weekday`/`near_holiday`。

- **页面接入** — `app/ui/pages/daily_plan.py`：
  - `_gen_all_daily` 在并发 `asyncio.gather` 前 `await is_near_holiday(selected_date)` 取一次；API 失败时返回 `None` 静默忽略，不阻断生成。
  - `base_ctx` 新增 `week_number`、`weekday`、`near_holiday` 三字段。

- **补单元测试**：
  - `tests/test_generate_client.py`（新，22 项）
  - `tests/test_generate_service.py`（新，3 项）
  - `tests/test_export_repository.py`（新，3 项）

### 全量测试结果

- **192 passed, 0 failed, 0 warnings**（Python 3.14.4）
- Alembic head 不变：`d60766786069`

---

## 2026-05-31（阶段 8 收尾：全局异常处理 + 路由守卫 + 审计日志）

### 已完成

- **Step 8.1 全局异常处理与审计日志**：
  - `app/core/audit.py`（新）：`log_audit(action, *, tenant_id=None, user_id=None, **detail)` 结构化审计日志；内部 `try/except` 包裹，绝不影响主流程。
  - `app/main.py`：`app.on_exception(_on_global_exception)` 记录未捕获异常。
  - 审计接入点：login_success / change_password（auth_service）、ai_split（lesson_plan_service）、ai_generate（generate_service）、export_word（daily_plan 页面）。

- **Step 8.2 路由守卫中间件**：
  - `app/auth/middleware.py`（新）：`AuthMiddleware(BaseHTTPMiddleware)` — 受限页面校验 JWT token，无效则清空 storage 并重定向 `/`；白名单 `UNRESTRICTED_PAGE_ROUTES = {"/", "/register"}`。

### 补单元测试

- `tests/test_audit.py`（新，3 项）
- `tests/test_middleware.py`（新，5 项）

### 全量测试结果

- **200 passed, 0 failed, 0 warnings**（Python 3.14.4）

### 手工验收进度（2026-05-31）

1. ✅ 未登录直接访问 `/daily-plan`、`/settings`、`/prompts` → 自动重定向回 `/`。
2. ✅ 登录后正常访问受限页面；退出登录后再访问 → 重定向回 `/`。
3. ⏳ 审计日志落盘验收。
4. ⏳ 全局异常 traceback 验收。

---

## 2026-05-31（二期前置：对外只读 REST API + 项目文档）

### 已完成

- **新增 `app/api/` 模块**：`__init__.py`（`create_api_router`）、`auth.py`（API Key + HMAC 签名鉴权）、`deps.py`（`get_db`）、`schemas.py`（Pydantic 只读响应模型）、`routes.py`（v1 路由）。
- **配置**：`app/core/config.py` 新增 `API_KEYS` / `API_SIGNING_SECRET` / `API_SIGNATURE_MAX_SKEW`。
- **仓库层只读查询**：`daily_plan_repository.list_daily_plans` / `get_daily_plan_by_id`、`semester_repository.list_semesters`、`class_repository.list_class_configs`，均强制 `tenant_id` 过滤。
- **入口注册**：`app/main.py` 在 `main()` 中 `app.include_router(create_api_router())`。
- **文档**：新增 `README.md`、`docs/DEVELOPER.md`、`docs/API.md`。

### 测试

- 新增 `tests/test_api_auth.py`（12 项）、`tests/test_api_routes.py`（16 项）。
- 全量：**228 passed, 0 warnings**。

---

## 2026-06-11（dev3.0 验收 Bug 修复）

### 背景

dev3.0（游戏观察子系统）进入 E~I 阶段验收，发现 3 个 Bug 及 1 项功能缺失，已修复。

### Bug 修复

| 编号 | 现象 | 根因 | 修复 |
|------|------|------|------|
| BL-GO-01 | 上传照片后计数不更新，`AttributeError: 'UploadEventArguments' object has no attribute 'content'` | NiceGUI 新版将上传事件 `content` 改为 `file: FileUpload`，`read()` 变为 async | `handle_upload` 改 async，`e.content.read()` → `await e.file.read()` |
| BL-GO-02 | 历史区块加载 `ValueError: not enough values to unpack (expected 2, got 0)` | `list_observations()` 返回 `list`，代码用 `records, _ =` 解包 | `records = await list_observations(...)` |
| BL-GO-03 | 「观察者」字段为空，未自动填入登录用户姓名 | JWT payload 不含 `username`/`display_name`，`get_display_name()` 始终返回 `""` | `create_access_token()` 新增可选参数写入 payload；`login()` 传入用户信息 |

### 功能补全

- `app/ui/pages/prompt_mgmt.py`：提示词管理增加「游戏观察」标签页，支持查看/编辑/版本管理游戏观察提示词。

### 待实现（Backlog）

| 编号 | 功能 | 优先级 |
|------|------|--------|
| FEAT-GO-01 | 生成观察记录时显示进度提示 | 中 |
| FEAT-GO-02 | 游戏观察历史记录增加删除功能 | 高 |
| FEAT-GO-03 | 每日活动计划增加删除功能 | 高 |

### 全量测试

- **342 passed, 0 failed**（dev3.0 交付基准）
