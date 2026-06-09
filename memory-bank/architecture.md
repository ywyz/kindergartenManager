# 幼儿园教学管理系统架构文档（初始化）

## 1. 当前阶段

- 项目阶段：M2/M3 已完成（阶段 0~8 全部完成）；二期对外只读 REST API 已落地。
- 账号体系补充：已完成第二阶段（管理员初始化脚本、账号创建/启停/重置密码、筛选分页），首期不开放公开自助注册。
- 开发策略：先架构后编码；每完成一个步骤同步更新本文件与 progress.md

## 2. 业务与权限边界（已确认）

- 教师：创建、编辑、导出、查看同班计划；不可跨班查看。
- 教研管理员：可查看、编辑、批注教学计划；可管理提示词。
- 系统管理员：独立后台管理界面（低优先级，后续实现）。
- 多设备登录：token 独立；设备管理和强制下线功能为低优先级需求。

## 3. 核心流程约束（已确认）

- 教案改写：覆盖多个活动字段，核心优先活动过程。
- 差异标红：导出时以活动过程差异为主进行红字标注。
- 提示词：共 7 种任务类型，分别独立配置与版本管理：`split`（教案拆分）/ `adapt`（年龄适配）/ `morning_exercise`（晨间活动）/ `morning_talk`（晨间谈话）/ `area_game`（区域游戏）/ `outdoor_game`（户外游戏）/ `daily_reflection`（一日活动反思）。
- 提示词回滚：仅影响后续生成，不回溯重算已保存草稿。

## 4. 日历与节假日规则（已确认）

- `is_holiday`：基于中国法定节假日接口判定，返回语义固定为法定节假日 True、工作日 False。
- 周末判定：独立于 `is_holiday`，由额外规则处理（例如 date_service 或 UI 提示层）。
- `near_holiday`：仅法定节假日前一天为 True，不包含周末前一天。
- 额外节日标签：支持不放假节日（首批包含 5 月 12 日全国防灾减灾日）。
- 节假日信息异常时不阻断主流程，UI 给出“信息暂不可用”提示。

## 5. Word 导出结构（已确认）

- 唯一模板来源：`templates/teacherplan.docx`。
- 表格结构：2 列多行，左列固定 8 行标题，右列为内容并包含部分子分割。
- 晨间活动固定字段：体能大循环 / 集体游戏 / 自选游戏。
- 其中“集体游戏”“自选游戏”后需拼接具体生成内容。

## 6. 导出与存档规则（已确认）

- 同一日期允许多次导出，生成多条导出记录。
- `file_path` 存储相对路径（相对仓库或导出根目录）。
- 浏览器下载由 `ui.download` 触发，与 `file_path` 字段存储形式解耦。
- 需要导出历史页面，支持查看与重新下载。

## 7. 目录结构与模块职责（Step 0.1 完成后）

以下目录已创建，每个目录的职责如下：

| 目录 | 职责 |
|------|------|
| `app/` | 应用根包，所有业务代码入口 |
| `app/ui/` | NiceGUI 页面与组件，每个页面独立文件（如 `pages/login.py`、`components/date_panel.py`）；禁止在此层做权限逻辑 |
| `app/api/` | 对外只读 REST API（二期）：`/api/v1` 路由、API Key + 可选 HMAC 签名鉴权；供子系统（幼儿园信息管理主系统）读取教学计划数据 |
| `app/service/` | 业务逻辑层：教案拆分协调、年龄适配、差异比对、日期计算、登录逻辑等；不直接发 HTTP 请求 |
| `app/repository/` | 数据访问层：封装所有 SQL 查询，返回模型对象；所有查询必须携带 `tenant_id` 过滤条件 |
| `app/integration/ai_client/` | OpenAI 兼容接口封装：`httpx` + `tenacity` 重试，强约束 JSON schema，解析失败抛出 `AiParseError` |
| `app/integration/holiday_client/` | 中国法定节假日 API 调用：带内存缓存（当天有效），API 失败时返回 `None` 降级，不阻断主流程 |
| `app/integration/word_export/` | Word 导出：`python-docx` 主方案，严格依照 `templates/teacherplan.docx` 结构，差异段落标红 |
| `app/auth/` | JWT 生成/验证、RBAC 权限校验、密码哈希（Argon2）、路由守卫中间件（`middleware.py`）；权限逻辑统一在此层，不下沉到 UI |
| `app/core/` | 配置（`pydantic-settings`）、日志（JSON 结构化）、审计日志（`audit.py`）、数据库连接（`AsyncEngine`）、异常定义、常量、加密工具 |
| `app/jobs/` | APScheduler 定时任务（如缓存清理、审计归档等） |
| `alembic/` | 数据库迁移脚本（Alembic），所有 schema 变更必须通过此处，禁止应用启动时 `create_all()` |
| `tests/` | pytest 测试，每个 service 函数必须有单元测试；AI/Word/数据库操作用 mock/fixture 隔离 |
| `exports/` | 导出的 Word 文件（运行时生成，不入仓，已在 `.gitignore` 中排除） |
| `templates/` | Word 模板文件，`teacherplan.docx` 为唯一导出结构依据 |
| `memory-bank/` | 项目文档（PRD、技术栈、实施计划、架构、进度），供开发者参考 |

### 关键约束速查
- **数据隔离**：所有业务表必须包含 `tenant_id`、`user_id`、`created_at`、`updated_at`
- **禁止**：`app/api/` 首期不实现；应用启动时不得 `create_all()`；service 层不直接发 HTTP 请求
- **Python 包**：`alembic/`、`exports/`、`templates/`、`memory-bank/` 均非 Python 包（无 `__init__.py`）

## 8. 阶段 0 已实现文件清单

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

## 9. 阶段 1 & 2 已实现文件清单

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
| `app/service/auth_service.py` | 登录逻辑（查用户→验密码→签 JWT）；修改密码；管理员账号创建、筛选分页、启停与重置密码（仅 `sys_admin`） |
| `app/service/date_service.py` | 纯函数：`get_week_number`、`get_weekday_cn`、`is_workday`、`is_within_semester` |
| `app/repository/user_repository.py` | 按用户名/ID 查询用户；更新密码；启停状态更新；用户筛选分页查询 |
| `app/repository/semester_repository.py` | `get_active_semester`、`upsert_active_semester` |
| `app/repository/class_repository.py` | `get_class_config`、`upsert_class_config` |
| `app/integration/holiday_client/client.py` | 法定节假日判定；法定节假日缓存 `dict[str, tuple[bool, str\|None, int]]`（含 day_type）；特殊节日缓存 `dict[str, list[str]]`；`is_holiday`、`is_near_holiday`、`get_holiday_name`、`get_special_day_tags`（sync，本地硬编码）、`is_adjusted_workday` |
| `app/ui/pages/login.py` | 登录页（路由 `/`），token 写入 `app.storage.user` |
| `app/ui/pages/home.py` | 首页（路由 `/home`），快捷导航按钮 |
| `app/ui/pages/settings.py` | 配置页（路由 `/settings`），学期配置、班级配置、AI 接口配置（含脱敏展示与验证连接） |
| `app/ui/pages/user_admin.py` | 账号管理页（路由 `/user-admin`），系统管理员创建账号、筛选分页、启停账号、重置密码 |
| `app/jobs/bootstrap_admin.py` | 系统管理员初始化脚本（环境变量控制、幂等创建） |
| `app/ui/pages/date_test.py` | 日期测试页（路由 `/date-test`），嵌入 DatePanel |

## 10. 阶段 3 已实现文件清单

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

## 11. 当前状态（截至 2026-06-09）

**所有首期阶段（0~8）及二期对外只读 REST API 均已完成。**

- 阶段 0~3：骨架、鉴权、配置、AI Key ✅
- 阶段 4：教案拆分 + 年龄适配 + 差异比对 ✅
- 阶段 5：提示词管理 ✅
- 阶段 6：Word 单条导出 + 导出记录 ✅（详见第 12、13 节）
- 阶段 7：一日活动辅助生成（晨间活动/晨间谈话/区域/户外/反思）✅
- 阶段 8：全局异常处理、审计日志、路由守卫 ✅
- 二期：对外只读 REST API（`/api/v1`）✅
- 附加功能：日期批量导出 Word ✅（详见第 14 节）

**低优先级待办：**
- 数据库 ERD 完整图（随模型实现逐步补齐，当前共 6 张业务表）

---

## 12. 阶段 4 已实现文件清单

### 核心模块

| 文件 | 职责 |
|------|------|
| `app/core/exceptions.py` | 新增 `AiCallError`（AI 接口调用失败）、`AiParseError`（AI 返回内容解析失败） |
| `app/core/models/daily_plan.py` | `DailyPlan` ORM 模型；含教案拆分字段、改写文、一日活动、晨间谈话、反思共 20 列 |
| `app/integration/ai_client/base.py` | 通用 `call_ai()` — httpx 超时 60s + tenacity 重试 3次（指数退避）；HTTP 错误提取响应体写入 `AiCallError.message` |
| `app/integration/ai_client/lesson_plan_client.py` | `split_lesson_plan()` — 教案拆分，输出 5 个结构化字段；内置默认 system prompt；prompt_repository 查询优先（Step 5 接入后生效） |
| `app/integration/ai_client/adapt_client.py` | `adapt_activity_process()` — 年龄适配改写；内置三段式 prompt（小班/中班/大班策略）；输出 `adapted_process` 字符串 |
| `app/service/diff_service.py` | `compute_diff()` — 按标点/换行分句；`difflib.SequenceMatcher` 逐句比对；返回改写文视角 `[{text, changed}]` |
| `app/service/lesson_plan_service.py` | `process_lesson_plan()` — 编排全流程（AI Key → 拆分 → 适配 → 差异）；`LessonPlanResult` dataclass |
| `app/repository/daily_plan_repository.py` | `save_daily_plan`（同日期 upsert）、`get_daily_plan_by_date` |
| `app/ui/pages/daily_plan.py` | 每日活动计划页（路由 `/daily-plan`）；DatePanel 复用；AI 拆分 + 回填 + 保存草稿；刷新后草稿自动加载。**一日活动各小节（晨间活动/晨间谈话/区域游戏/户外游戏）合并为单个「一键生成一日活动」按钮**，内部 `asyncio.gather(..., return_exceptions=True)` 并发生成、单项失败不阻断；「集体活动」拆分按钮与「一日活动反思」按钮保持独立 |
| `app/integration/word_export/exporter.py` | `export_daily_plan(daily_plan, diff_result)` — 主方案打开 `templates/teacherplan.docx`（19 行 2 列）按既有单元格结构分子字段填充；`_parse_fields` 解析生成文本为子字段分格写入；活动过程差异标红（`RGBColor(255,0,0)`）、宋体；模板缺失/异常时降级 `_export_from_scratch`（8 行从零建表） |

### 数据库表（新增）

| 表名 | 迁移版本 | 主要字段 |
|------|---------|----------|
| `daily_plan` | `f6d79ac6bf21` | id, tenant_id, user_id, plan_date, week_number, weekday_cn, grade, class_name, activity_goal, activity_prep, activity_key, activity_difficult, activity_process_original, activity_process_adapted, morning_activity, indoor_area, outdoor_activity, morning_talk_topic, morning_talk_questions, daily_reflection |

---

## 13. 阶段 5 已实现文件清单

### 数据库表（新增）

| 表名 | 迁移版本 | 主要字段 |
|------|---------|----------|
| `prompt_template` | `bcd07e51527d` → `e2a3f1b8c9d0` | id, tenant_id, user_id, task_type(Enum×7), version, content, is_active, created_at, updated_at |

**Alembic 当前 head**：`e2a3f1b8c9d0`（含全部 6 张业务表）

**task_type Enum 枚举值**：`split` / `adapt` / `morning_exercise` / `morning_talk` / `area_game` / `outdoor_game` / `daily_reflection`

### 核心模块（新增 / 修改）

| 文件 | 职责 |
|------|------|
| `app/core/models/prompt_template.py` | `PromptTemplate` ORM 模型；联合索引 `(tenant_id, user_id, task_type)` |
| `app/repository/prompt_repository.py` | `get_active_prompt` / `save_new_version` / `rollback_to_version` / `list_versions` 四个异步函数 |
| `app/integration/ai_client/generate_client.py` | 5 种一日活动类型的内置默认提示词；`GENERATE_DEFAULTS: dict[str, str]` 供服务层查取；`_build_prefix`（班级 + 教学周）/`_holiday_hint`（near_holiday=True 注入临近节假日提示，daily_reflection 不注入）；`_build_user_content` 消费 `week_number`/`weekday`/`near_holiday` |
| `app/integration/ai_client/lesson_plan_client.py` | `DEFAULT_SPLIT_PROMPT` 追加格式约束（禁 Markdown / 无数字编号换行 / 无多余空行）；KI-01 修复 |
| `app/integration/ai_client/adapt_client.py` | `DEFAULT_ADAPT_PROMPT` 追加格式约束（禁 Markdown / 纯文本 / 标点约束）；KI-01 修复 |
| `app/service/lesson_plan_service.py` | `process_lesson_plan()` 新增：`split_system_prompt` / `adapt_system_prompt` 为 None 时先查 DB 激活版本，有则覆盖 |
| `app/ui/pages/prompt_mgmt.py` | 提示词管理页（路由 `/prompts`）；7 Tab；每 Tab 含编辑区 + 保存 + 历史版本 + 回滚 |
| `app/ui/pages/home.py` | 新增"提示词管理"导航按钮（紫色，跳转 `/prompts`） |

### 一日活动提示词格式规范（已确认）

| 活动类型 | 格式要点 |
|---------|---------|
| 晨间活动 `morning_exercise` | 体能大循环（集体游戏/自主游戏/重点指导）+ 活动目标3条 + 指导要点3条 |
| 晨间谈话 `morning_talk` | 谈话主题 + 问题设计3条 |
| 区域游戏 `area_game` | 游戏区域（选2个，用" 、 "分隔）+ 重点指导（选1个）+ 活动目标3条 + 指导要点3条 |
| 户外游戏 `outdoor_game` | 游戏区域（选2个，用" 、 "分隔）+ 重点指导（选1个）+ 活动目标3条 + 指导要点3条 |
| 一日活动反思 `daily_reflection` | 自然段落（无编号），100~200字，含亮点/问题/调整策略 |

### 已知问题与决策记录（阶段 4）

| 编号 | 问题 | 决策 |
|------|------|------|
| BL-03 | `DatePanel.on_date_change` 为 async 函数时，`_update_info` 未 await 导致 state 不更新 | `_update_info` 末尾使用 `asyncio.iscoroutine()` 判断后 await；已修复 |
| BL-04 | AI 调用失败时 UI 显示通用提示，无法定位原因 | `base.py` 提取 HTTP 错误响应体；`daily_plan.py` 显示 `e.message`；已修复 |
| KI-01 | AI 返回字段含 markdown 标记（`**重点：**`）、格式不一致 | **待修复**：Step 5 提示词管理时强化 prompt 格式约束 |

### AI 客户端接口说明

```python
# 通用 AI 调用（httpx + tenacity）
call_ai(messages, api_base_url, api_key, model_name, response_schema, *, _client) -> dict

# 教案拆分（返回 5 字段 dict）
split_lesson_plan(raw_text, api_base_url, api_key, model_name, system_prompt, *, _client) -> dict
# 返回键：activity_goal / activity_prep / activity_key / activity_difficult / activity_process

# 年龄适配（返回改写后文本字符串）
adapt_activity_process(original, grade, api_base_url, api_key, model_name, system_prompt, *, _client) -> str

# 差异比对（纯本地，无 AI 调用）
compute_diff(original, adapted) -> list[{"text": str, "changed": bool}]

# 教案拆分服务（编排入口）
process_lesson_plan(session, tenant_id, user_id, raw_text, grade, *, split_system_prompt, adapt_system_prompt, _ai_client) -> LessonPlanResult
```

### 阶段 8：收尾与稳定性

| 文件 | 职责 |
|------|------|
| `app/auth/middleware.py` | `AuthMiddleware`（`BaseHTTPMiddleware`）路由守卫：受限页面校验 `app.storage.user` 中 JWT token，无效则清空 storage 重定向 `/`；非页面路由（静态资源/`_nicegui`）放行；白名单 `UNRESTRICTED_PAGE_ROUTES = {"/"}` |
| `app/core/audit.py` | `log_audit(action, *, tenant_id, user_id, **detail)` 结构化审计日志（logger 名 `audit`）；接入点：login_success / change_password（auth_service）、ai_split（lesson_plan_service）、ai_generate（generate_service）、export_word（daily_plan 页面）；审计调用绝不抛异常 |
| `app/main.py` | `app.on_exception(_on_global_exception)` 记录未捕获异常（ERROR + traceback）；`app.add_middleware(AuthMiddleware)` 注册路由守卫 |

**异常体系**（`app/core/exceptions.py`）：`AuthError`、`CryptoError`、`ConfigError`、`AiCallError`、`AiParseError`（均带 `message` 属性）。页面层捕获业务异常展示友好提示（`e.message`），不暴露堆栈；未预期异常由 `app.on_exception` 记录完整 traceback。

### 二期：对外只读 REST API

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

---

## 14. 日期批量导出（2026-06-08）

### 新增功能

用户可在「每日计划」页面底部选择开始~结束日期范围，将区间内所有已保存计划合并导出为单个 Word 文档（表格按日期升序排列，相邻表格间留一空行）。

### 核心变更

| 文件 | 变更内容 |
|------|----------|
| `app/integration/word_export/exporter.py` | 新增 `export_batch_daily_plans(plans_with_diffs)` — 按 `plan_date` 升序排列；首个 plan 作为主文档，后续 plan 用 `copy.deepcopy` 追加表格 XML；相邻表格间插入空段落；空列表返回合法空文档；模板缺失时降级兼容 |
| `app/ui/pages/daily_plan.py` | 新增「批量导出」卡片：日期范围选择器（`bind_value` 直读 `.value`）、输入校验（start≤end）、调用 `list_daily_plans(..., limit=200)` 范围查询、循环 `compute_diff` + `export_batch_daily_plans`、写入 `export_record`（`daily_plan_id=None`）、`log_audit("batch_export_word")`、`ui.download` 触发下载 |
| `tests/test_word_exporter.py` | 新增 `TestBatchExport`：`test_batch_empty_list_returns_valid_bytes` / `test_batch_single_plan_has_one_table` / `test_batch_multiple_plans_sorted_by_date` |

### Bug 修复（BL-05）

| 编号 | 问题 | 决策 |
|------|------|------|
| BL-05 | 批量导出按钮点击后 `TypeError: strptime() argument 1 must be str, not list`；根因：`ui.date(...).on("update:model-value", lambda e: ..., e.args)` 中 `e.args` 为 NiceGUI 事件参数 list | 删除 `batch_state` dict 及 `on(...)` 监听器，改为在 `_batch_export()` 中直接读 `batch_start_input.value` / `batch_end_input.value`（已由 `bind_value` 双向绑定） |

### 测试基准

全量回归：**251 passed**（新增 9 个测试用例：`TestBatchExport` × 3 + `TestExportDailyPlan` 新增用例 × 3 + 其他 × 3）。

