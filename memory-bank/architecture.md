# 幼儿园教学管理系统架构文档（初始化）

## 1. 当前阶段

- 项目阶段：M1 进行中（阶段 0/1/2/3 已完成）
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
| `app/api/` | 预留：首期不实现，二期对外 REST API 放此处 |
| `app/service/` | 业务逻辑层：教案拆分协调、年龄适配、差异比对、日期计算、登录逻辑等；不直接发 HTTP 请求 |
| `app/repository/` | 数据访问层：封装所有 SQL 查询，返回模型对象；所有查询必须携带 `tenant_id` 过滤条件 |
| `app/integration/ai_client/` | OpenAI 兼容接口封装：`httpx` + `tenacity` 重试，强约束 JSON schema，解析失败抛出 `AiParseError` |
| `app/integration/holiday_client/` | 中国法定节假日 API 调用：带内存缓存（当天有效），API 失败时返回 `None` 降级，不阻断主流程 |
| `app/integration/word_export/` | Word 导出：`python-docx` 主方案，严格依照 `templates/teacherplan.docx` 结构，差异段落标红 |
| `app/auth/` | JWT 生成/验证、RBAC 权限校验、密码哈希（Argon2）；权限逻辑统一在此层，不下沉到 UI |
| `app/core/` | 配置（`pydantic-settings`）、日志（JSON 结构化）、数据库连接（`AsyncEngine`）、异常定义、常量、加密工具 |
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

## 11. 待后续实现

- 数据库 ERD 完整图（随模型实现逐步补齐）。
- 阶段 6（Word 导出、导出历史）。
- 阶段 7（一日活动辅助生成）。

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
| `app/ui/pages/daily_plan.py` | 每日活动计划页（路由 `/daily-plan`）；DatePanel 复用；AI 拆分 + 回填 + 保存草稿；刷新后草稿自动加载 |

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
| `app/integration/ai_client/generate_client.py` | 5 种一日活动类型的内置默认提示词；`GENERATE_DEFAULTS: dict[str, str]` 供服务层查取 |
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

