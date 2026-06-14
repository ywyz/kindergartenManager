# 一日活动计划子系统 — 设计文档

> 本文档为「一日活动计划」子系统（教案拆分 / 年龄适配 / 提示词管理 / Word 导出 / 一日活动生成）的架构设计说明。
>
> 阅读前置：[../PRD.md](../PRD.md)、[../architecture.md](../architecture.md)、[../tech-stack.md](../tech-stack.md)
> 与 `.github/instructions/*.instructions.md`（数据库 / AI / Word 导出约定）。
>
> 开发进度：[progress.md](progress.md)

## 1. 核心流程约束（已确认）

- 教案改写：覆盖多个活动字段，核心优先活动过程。
- 差异标红：导出时以活动过程差异为主进行红字标注。
- 提示词：共 7 种任务类型，分别独立配置与版本管理：`split`（教案拆分）/ `adapt`（年龄适配）/ `morning_exercise`（晨间活动）/ `morning_talk`（晨间谈话）/ `area_game`（区域游戏）/ `outdoor_game`（户外游戏）/ `daily_reflection`（一日活动反思）。
- 提示词回滚：仅影响后续生成，不回溯重算已保存草稿。

## 2. 日历与节假日规则（已确认）

- `is_holiday`：基于中国法定节假日接口判定，返回语义固定为法定节假日 True、工作日 False。
- 周末判定：独立于 `is_holiday`，由额外规则处理（例如 date_service 或 UI 提示层）。
- `near_holiday`：仅法定节假日前一天为 True，不包含周末前一天。
- 额外节日标签：支持不放假节日（首批包含 5 月 12 日全国防灾减灾日）。
- 节假日信息异常时不阻断主流程，UI 给出"信息暂不可用"提示。

### Holiday Client 接口说明

```python
# 判定法定节假日（True=法定节假日, False=非法定节假日, None=API不可用）
is_holiday(target_date, *, _transport=None) -> bool | None

# 判定明天是否为法定节假日（True=是, False=否, None=API不可用）
is_near_holiday(target_date, *, _transport=None) -> bool | None

# 获取具体节日名称（如"国庆节"），非法定节假日或API不可用返回 None
get_holiday_name(target_date, *, _transport=None) -> str | None

# 返回不放假节日标签列表（如["教师节"]），纯本地硬编码
get_special_day_tags(target_date) -> list[str]  # sync

# 判定调班工作日（type=3），复用法定节假日缓存
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

## 3. Word 导出结构（已确认）

- 唯一模板来源：`templates/teacherplan.docx`。
- 表格结构：2 列多行，左列固定标题（纵向合并），右列内容分子字段单元格。
- 晨间活动固定字段：体能大循环 / 集体游戏 / 自选游戏。

### 模板行映射（19 行 2 列）

| 行 | 左列标题 | 右列子字段 |
|----|---------|-----------|
| R0 | 第N周 | （整行合并）|
| R1 | 月 日 周X | （整行合并）|
| R2 | 晨间活动 | 体能大循环 / 集体游戏 / 自主游戏 |
| R3 |  | 重点指导 / 活动目标 / 指导要点 |
| R4 | 晨间谈话 | 话题 |
| R5 |  | 问题设计 |
| R6 | 集体活动 | 活动主题 |
| R7~R10 |  | 活动目标 / 活动准备 / 活动重点 / 活动难点 |
| R11 |  | 活动过程（差异标红）|
| R12 | 室内区域游戏 | 游戏区域 |
| R13 |  | 重点指导 / 活动目标 / 指导要点 |
| R14 |  | 支持策略 |
| R15 | 下午：户外游戏 | 游戏区域 |
| R16 |  | 重点观察 / 活动目标 / 指导要点 |
| R17 |  | 支持策略 |
| R18 | 一日活动反思 | （内容）|

## 4. 导出与存档规则（已确认）

- 同一日期允许多次导出，生成多条导出记录。
- `file_path` 存储相对路径（相对仓库或导出根目录）。
- 浏览器下载由 `ui.download` 触发，与 `file_path` 字段存储形式解耦。
- 需要导出历史页面，支持查看与重新下载。

## 5. 阶段 4 已实现文件清单

### 核心模块

| 文件 | 职责 |
|------|------|
| `app/core/exceptions.py` | 新增 `AiCallError`（AI 接口调用失败）、`AiParseError`（AI 返回内容解析失败） |
| `app/core/models/daily_plan.py` | `DailyPlan` ORM 模型；含教案拆分字段、改写文、一日活动、晨间谈话、反思共 20 列 |
| `app/integration/ai_client/base.py` | 通用 `call_ai()` — httpx 超时 60s + tenacity 重试 3次（指数退避）；HTTP 错误提取响应体写入 `AiCallError.message` |
| `app/integration/ai_client/lesson_plan_client.py` | `split_lesson_plan()` — 教案拆分，输出 5 个结构化字段；内置默认 system prompt；prompt_repository 查询优先 |
| `app/integration/ai_client/adapt_client.py` | `adapt_activity_process()` — 年龄适配改写；内置三段式 prompt（小班/中班/大班策略）；输出 `adapted_process` 字符串 |
| `app/service/diff_service.py` | `compute_diff()` — 按标点/换行分句；`difflib.SequenceMatcher` 逐句比对；返回改写文视角 `[{text, changed}]` |
| `app/service/lesson_plan_service.py` | `process_lesson_plan()` — 编排全流程（AI Key → 拆分 → 适配 → 差异）；`LessonPlanResult` dataclass |
| `app/repository/daily_plan_repository.py` | `save_daily_plan`（同日期 upsert）、`get_daily_plan_by_date` |
| `app/ui/pages/daily_plan.py` | 每日活动计划页（路由 `/daily-plan`）；DatePanel 复用；AI 拆分 + 回填 + 保存草稿；**一键生成一日活动**（`asyncio.gather` 并发4项，失败不阻断）；集体活动拆分与一日反思独立按钮 |
| `app/integration/word_export/exporter.py` | `export_daily_plan(daily_plan, diff_result)` — 打开 `templates/teacherplan.docx`（19 行 2 列）分子字段填充；差异标红（`RGBColor(255,0,0)`）宋体；模板缺失时降级 `_export_from_scratch` |

### 数据库表（新增）

| 表名 | 迁移版本 | 主要字段 |
|------|---------|----------|
| `daily_plan` | `f6d79ac6bf21` | id, tenant_id, user_id, plan_date, week_number, weekday_cn, grade, class_name, activity_goal, activity_prep, activity_key, activity_difficult, activity_process_original, activity_process_adapted, morning_activity, indoor_area, outdoor_activity, morning_talk_topic, morning_talk_questions, daily_reflection |
| `export_record` | `d60766786069` | id, tenant_id, user_id, daily_plan_id, observation_id, file_name, file_path, created_at |

## 6. 阶段 5 已实现文件清单（提示词管理）

### 数据库表（新增）

| 表名 | 迁移版本 | 主要字段 |
|------|---------|----------|
| `prompt_template` | `bcd07e51527d` → `e2a3f1b8c9d0` | id, tenant_id, user_id, task_type(Enum×7+game_observation), version, content, is_active, created_at, updated_at |

**task_type Enum 枚举值**：`split` / `adapt` / `morning_exercise` / `morning_talk` / `area_game` / `outdoor_game` / `daily_reflection` / `game_observation`

### 核心模块（新增 / 修改）

| 文件 | 职责 |
|------|------|
| `app/core/models/prompt_template.py` | `PromptTemplate` ORM 模型；联合索引 `(tenant_id, user_id, task_type)` |
| `app/repository/prompt_repository.py` | `get_active_prompt` / `save_new_version` / `rollback_to_version` / `list_versions` 四个异步函数 |
| `app/integration/ai_client/generate_client.py` | 5 种一日活动类型的内置默认提示词；`GENERATE_DEFAULTS: dict[str, str]`；`_build_prefix`（班级+教学周）/ `_holiday_hint`（near_holiday=True 注入节日提示，daily_reflection 不注入）；`_build_user_content` 消费 `week_number`/`weekday`/`near_holiday` |
| `app/integration/ai_client/lesson_plan_client.py` | `DEFAULT_SPLIT_PROMPT` 追加格式约束（禁 Markdown / 无数字编号换行 / 无多余空行）；KI-01 修复 |
| `app/integration/ai_client/adapt_client.py` | `DEFAULT_ADAPT_PROMPT` 追加格式约束（禁 Markdown / 纯文本 / 标点约束）；KI-01 修复 |
| `app/service/lesson_plan_service.py` | `process_lesson_plan()` 新增：`split_system_prompt` / `adapt_system_prompt` 为 None 时先查 DB 激活版本 |
| `app/ui/pages/prompt_mgmt.py` | 提示词管理页（路由 `/prompts`）；8 Tab（日活 7 种 + 游戏观察）；编辑 + 保存 + 历史版本 + 回滚 |

### 一日活动提示词格式规范（已确认）

| 活动类型 | 格式要点 |
|---------|---------|
| 晨间活动 `morning_exercise` | 体能大循环（集体游戏/自主游戏/重点指导）+ 活动目标3条 + 指导要点3条 |
| 晨间谈话 `morning_talk` | 谈话主题 + 问题设计3条 |
| 区域游戏 `area_game` | 游戏区域（选2个，用" 、 "分隔）+ 重点指导（选1个）+ 活动目标3条 + 指导要点3条 |
| 户外游戏 `outdoor_game` | 游戏区域（选2个，用" 、 "分隔）+ 重点指导（选1个）+ 活动目标3条 + 指导要点3条 |
| 一日活动反思 `daily_reflection` | 自然段落（无编号），100~200字，含亮点/问题/调整策略 |

## 7. AI 客户端接口速查

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

# 一日活动生成（near_holiday=True 时注入节日提示）
generate_activity(context, task_type, api_base_url, api_key, model_name, system_prompt, *, _client) -> str
```

## 8. 已知问题与决策记录

| 编号 | 问题 | 决策 |
|------|------|------|
| BL-03 | `DatePanel.on_date_change` 为 async 函数时，`_update_info` 未 await 导致 state 不更新 | `_update_info` 末尾用 `asyncio.iscoroutine()` 判断后 await；已修复 |
| BL-04 | AI 调用失败时 UI 显示通用提示，无法定位原因 | `base.py` 提取 HTTP 错误响应体；`daily_plan.py` 显示 `e.message`；已修复 |
| KI-01 | AI 返回字段含 markdown 标记（`**重点：**`）、格式不一致 | Step 5 提示词管理时在 prompt 中强化格式约束；已修复 |
| BL-05 | Step 5.2b 合入后，旧测试未 mock `get_active_prompt` 导致失败 | 受影响旧测试补加 `patch(..., new=AsyncMock(return_value=None))`；已修复 |
