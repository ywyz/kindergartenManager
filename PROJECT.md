# 幼儿园每日活动计划系统

> 教学管理子系统 · `feature/week-plan` 分支
> 最后更新:2026-04-27

本文档由历史待办文档与提示词草案汇总而成,作为项目的**唯一入口文档**。后续仅维护本文件。

---

## 1. 项目背景

幼儿园整体信息化管理系统的子模块。完整母系统覆盖账号管理、学生信息、教职工信息、食堂、后勤、教学、数据备份等;本仓库当前实现"教学管理 → 每日活动计划撰写与收集"。

- **运行环境**:UV Python ≥ 3.12 (目标 3.14)
- **界面框架**:NiceGUI ≥ 2.0
- **数据库**:MySQL (aliyun.ywyz.tech)
- **AI 接入**:OpenAI 兼容接口 (openai SDK)
- **导出**:python-docx 填充 `templates/teacherplan.docx`
- **加密**:Fernet (cryptography),用于 AI Key 落库前加密
- **节假日**:`chinesecalendar`(支持 2004–2026,含调休)

依赖见 [pyproject.toml](pyproject.toml)。

---

## 2. 总体目标

围绕一份"每日活动计划 Word"完成全流程:

1. **学期 / 班级 / 区域户外内容设置**(数据库持久化)
2. **AI 配置**(URL / Key / Model,加密保存)
3. **教案粘贴 → AI 拆分**(JSON 化为活动主题/目标/准备/重点/难点/过程)
4. **活动过程 AI 修改**(按年龄段最小化优化,差异部分红字标识)
5. **一日活动 AI 一键生成**(晨间活动 / 晨间谈话 / 室内区域 / 户外游戏)
6. **导出 Word**(填充模板,AI 修改部分红字)
7. **历史记录**(可重新查看与导出旧计划)
8. **提示词管理**(6 大分类增删改激活,支持测试)

---

## 3. 系统架构

```
kindergartenManager/
├── app/
│   ├── main.py                    # NiceGUI 入口 + 路由 + 左侧导航
│   ├── config.py                  # 环境变量与默认配置
│   ├── db.py                      # PyMySQL 封装 + 自动建表
│   ├── models/
│   │   └── daily_plan.py          # DailyPlan / MorningActivity / GroupActivity 等
│   ├── pages/
│   │   ├── settings.py            # 学期/班级/区域内容/AI 配置
│   │   ├── daily_plan.py          # 一日计划主页(已合并教案拆分)
│   │   ├── lesson_split.py        # 旧独立教案拆分页(已从导航移除,路由保留)
│   │   ├── prompt_mgmt.py         # 提示词管理
│   │   └── plan_history.py        # 历史记录
│   └── services/
│       ├── ai_service.py          # AI 调用封装 + JSON 强约束 + 修复重试
│       ├── crypto.py              # Fernet 加解密
│       ├── date_utils.py          # 周次/星期/工作日/节假日临近
│       ├── plan_service.py        # 学期/设置/计划读写
│       └── word_export.py         # docx 模板填充 + 红字差异
├── templates/teacherplan.docx     # 单表格 Word 模板
├── exports/                       # 导出文件落地目录
└── .env                           # 敏感配置 (不入 Git)
```

### 数据库 5 张表

| 表                    | 用途                               |
| --------------------- | ---------------------------------- |
| `semester_settings` | 学期开始/结束日期 + 年级班级       |
| `ai_config`         | AI URL / Key(加密) / Model         |
| `daily_plans`       | 每日计划主表(各模块以 JSON 列存储) |
| `prompts`           | 6 类提示词 + is_active             |
| `app_settings`      | 区域内容 / 户外内容等 KV 配置      |

---

## 4. 关键页面与字段

### 4.1 一日计划页面 `/daily-plan`(主页)

| 卡片                             | 字段                                                                                                                |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| 日期区                           | 日期选择 → 自动显示第几周 / 周几 / 工作日 / 临近节假日                                                             |
| 晨间活动                         | 集体活动名 / 自选活动名 / 重点指导 / 活动目标 / 指导要点                                                            |
| 晨间谈话                         | 谈话主题 / 问题设计                                                                                                 |
| **集体活动(内嵌教案拆分)** | 教案粘贴框 +`🤖 AI 拆分教案` + 采用 AI 修改版复选框 + 活动主题/目标/准备/重点/难点 + 活动过程双 Tab(原始/AI 修改) |
| 室内区域                         | 游戏区域 / 重点指导 / 活动目标 / 指导要点 / 支持策略                                                                |
| 户外游戏                         | 游戏区域 / 重点指导 / 活动目标 / 指导要点 / 支持策略                                                                |
| 一日活动反思                     | 自由文本                                                                                                            |

操作按钮:`🤖 AI 生成活动内容` / `💾 保存` / `📄 导出 Word`。

### 4.2 设置 `/settings`

学期 / 年级 / 班级 / 区域内容 / 户外内容 / AI URL / AI Key / Model。

### 4.3 提示词管理 `/prompts`

6 类:`lesson_split` / `process_modify` / `morning_activity` / `morning_talk` / `indoor_area` / `outdoor_game`。每类支持新增 / 编辑 / 删除 / 激活 / 测试。

### 4.4 历史记录 `/history`

按日期翻看历史计划,支持重新导出 Word。

---

## 5. AI 调用约定

所有 JSON 生成走统一入口 `_call_json()`,内置三层防护:

1. **强制 JSON 模式**:启用 OpenAI `response_format={"type":"json_object"}`,网关不支持时自动回退。
2. **格式硬约束**:在用户提示词末尾追加 `_JSON_FORMAT_RULES`,显式禁止裸字符串并列、Markdown 围栏、注释、多余键等常见错误。
3. **失败自我修正**:JSON 解析失败时,把错误信息 + 上次输出回灌给模型,要求修正,最多 2 次。

文本类调用(`process_modify`)使用 `_strip_to_process_text()` 兜底:即使模型违规返回 JSON,也会自动剥离仅保留 process 字段文本。

`process_modify` 提示词强制要求"二选一":只允许**修改一个环节**或**新增一个环节**,其余环节一字不动;改动末尾追加 `【AI修改】` 标记。

---

## 6. 当前进度

### ✅ 已完成

- **Phase 1**:项目骨架、5 表自动建库、NiceGUI 路由与导航、日期工具、Fernet 加密
- **Phase 2**:教案 AI 拆分页面、AI 服务封装、活动过程 diff 高亮、保存与导出
- **Phase 3**:一日活动 4 块 AI 生成(晨间活动/晨间谈话/室内区域/户外游戏)
- **Phase 4**:Word 导出与历史记录页(基础流程跑通)
- **Phase 5**:提示词管理 CRUD + 测试 + 激活
- **关键 Bug 修复**:Key 解密、JSON 容错、日期事件绑定、晨间活动字段拆分、JSON key 中文别名、教案目标丢失、`process_modify` 不再返回 JSON
- **性能修复**:阻塞 IO 全部走 `nicegui.run.io_bound`,消除"JavaScript did not respond"
- **结构重构**:教案拆分内嵌一日计划页,导航移除独立入口,日期统一

### ⚠️ 已识别的代码缺口与风险

| #  | 位置                                     | 问题                                                                                                                                    | 状态                          |
| -- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| 1  | `app/pages/daily_plan.py`              | 集体活动栏不会自动从当天教案拆分继承(已部分通过内嵌缓解,跨次访问仍需依赖保存)                                                           | TODO                          |
| 2  | `app/services/date_utils.py`           | 接入 `chinesecalendar` 取代硬编码节假日,含调休;`is_near_holiday` 已禁用(节假日本身被工作日判断覆盖,业务内容不含节假日,无需额外提示) | ✅ 已完成                     |
| 3  | DB schema `daily_plans`                | 缺 `(plan_date, grade, class_name)` 唯一索引                                                                                          | ✅ 已完成（DDL + ALTER 兜底） |
| 4  | `ai_service.py`                        | JSON 解析失败重试                                                                                                                       | ✅ 已完成                     |
| 5  | `settings.py`                          | `area_content`/`outdoor_content` 仅单文本框,需支持多候选                                                                            | TODO                          |
| 6  | 学期设置                                 | 仅最近一条生效,无法切换历史学期                                                                                                         | TODO                          |
| 7  | `.env` `APP_SECRET_KEY`              | 占位符,**必须替换为强随机值**(替换后需重新保存 AI Key)                                                                            | ✅ 已完成                     |
| 8  | `lesson_split.py`                      | 与一日计划日期共用                                                                                                                      | ✅ 已完成                     |
| 9  | `lesson_split.py` → `daily_plan.py` | 教案拆分内嵌一日计划                                                                                                                    | ✅ 已完成                     |
| 10 | `_DEFAULT_PROMPTS["process_modify"]`   | 禁止 JSON 输出 + 兜底剥离                                                                                                               | ✅ 已完成                     |
| 11 | lesson_split key 归一化                  | 教案目标键被错误映射到 activity_goal                                                                                                    | ✅ 已完成                     |
| 12 | `word_export.py` Row 11                | 导出后活动过程整段全红 → 改为**每行独立段落 + 单 run 显式 `<w:color>`**,按"环节"聚合 AI 标记决定红/黑                          | ✅ 已完成                     |
| 13 | `word_export.py` Row 11                | 【AI新增】等新增环节标记红字未生效 → 标题正则扩展为强(中文数字/`第N步`)+ 弱(阿拉伯数字)两级,AI 标记正则覆盖 `【】/[]/()` 三种括号  | ✅ 已完成                     |
| 14 | `app/pages/plan_history.py`            | 查看历史详情时报错：`'MorningActivity' object has no attribute 'activity_type'`，导致"查看"无响应                                     | ✅ 已完成                     |
| 15 | `app/pages/plan_history.py`            | 历史记录中草稿计划点击"查看"无法打开（需与异常处理联动排查）                                                                            | ✅ 已完成                     |

### 🚀 待开发功能

- [X] **多 AI 并发批量生成**:4 个 AI 请求改 `asyncio.gather` 并发,显著降低等待时间
- [X] **多 AI 负载均衡**:`ai_config` 支持多条激活记录,按轮询/随机/权重分发,失败自动切换
- [X] `templates/MAPPING.md`:docx 单元格 ↔ Python 字段映射文档
- [X] 导出文件命名规范:`{年级}{班级}_{YYYY-MM-DD}_{第N周周X}.docx`
- [X] 启动自检页:DB / AI 配置 / Word 模板三项检查
- [X] AI 调用日志:每次 prompt/响应落库,便于优化
- [X] 导出按钮文案区分:`保存并导出` vs 单独 `导出`
- [X] 连续导出多日一日活动计划（按日期范围批量导出）
- [X] 历史记录页新增"AI生成一日活动反思"按钮（打开历史计划后可一键生成并保存反思）
- [X] **日期加载已有计划**：在一日计划页面选择日期后，自动从数据库加载该日期已保存的计划内容并填充到表单

---

## 7. 开发与启动

```bash
# 进入 UV 项目环境
cd /home/admin/code/kindergartenManager
uv sync                    # 安装依赖

# 配置 .env(参考 .env.example)
#   DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME
#   APP_SECRET_KEY            ← 必须强随机
#   DEFAULT_AI_URL / DEFAULT_AI_KEY / DEFAULT_AI_MODEL(可选)

# 启动
uv run python -m app.main
# 或
uv run python app/main.py
```

启动后访问 `http://localhost:8080`,左侧导航包含 4 项:`系统设置` / `一日计划` / `提示词管理` / `历史记录`。

---

## 8. 关键决策

- **单用户优先**:不实现登录系统,`user_id` 字段预留。
- **AI Key 安全**:数据库中 Fernet 加密;`.env` 中默认 Key 不入 Git。
- **节假日判断**:接入 `chinesecalendar` 库(2004–2026,含调休);因业务内容不含节假日,`is_near_holiday` 已禁用以避免噪声提示。
- **Word 红字**:不在段落/单元格层级染色;采用"每行独立 `<w:p>` + 显式 `<w:color>`"避免 run 颜色越界,环节按强标题(中文数字/`第N步`)与 AI 标记联合判定。
- **Git 流**:在 `feature/daily-plan` 开发,完成后合并 `main`。
- **不做范围**:登录系统、备课笔记、其他教学管理功能。
- **周计划与一日计划关系**:周计划保存为独立快照；提供"从一日计划重新同步"入口，同步后快照更新。
- **周计划周次定义**:按学期周理解，节假日/调休导致一周有效天数可在 4–6 天之间；展示层固定 5 列（周一–周五），节假日仅标注，不删除列。
- **教师/保育员设置**:存入 `app_settings`，全局生效，不按班级隔离。
- **周计划初版范围**:支持生成、保存、导出；不做周计划历史列表页（数据已存库，后续可扩展）。

---

## 10. 周计划子系统

### 10.1 目标

依附于一日计划子系统，新增独立的"周计划"生成与导出功能：

1. 选择学期周，自动推导周次、本周各天日期与工作日/放假日状态
2. 从已保存的一日计划中同步本周集体活动内容（含教案拆分结果）
3. AI 批量生成晨间谈话、户外游戏、区域游戏及周级内容（本周重点/环境创设/生活习惯/家园共育）
4. 支持人工补录缺失内容
5. 保存为独立周计划快照；提供"重新同步一日计划"入口
6. 导出为 Word（填充 `templates/weekplan.docx`）

### 10.2 模板结构 `templates/weekplan.docx`

9 行 × 7 列，单表格：

| 行  | Col0（大类）  | Col1（小类标签）    | Col2（周一） | Col3（周二） | Col4（周三） | Col5（周四） | Col6（周五） |
| --- | ------------- | ------------------- | ------------ | ------------ | ------------ | ------------ | ------------ |
| 0   | 周次/日期信息 | ← 周一 (Col1+2合并) | ↑            | 周二         | 周三         | 周四         | 周五         |
| 1   | 学习活动      | 晨间谈话            | 内容         | 内容         | 内容         | 内容         | 内容         |
| 2   | 学习活动      | 集体活动            | 内容         | 内容         | 内容         | 内容         | 内容         |
| 3   | 游戏活动      | 户外游戏            | 内容         | 内容         | 内容         | 内容         | 内容         |
| 4   | 游戏活动      | 区域游戏            | 内容         | 内容         | 内容         | 内容         | 内容         |
| 5   | 本周重点      | ← Col1-6 合并 →     | ←            | ←            | ←            | ←            | 内容         |
| 6   | 环境创设      | ← Col1-6 合并 →     |              |              |              |              |              |
| 7   | 生活习惯培养  | ← Col1-6 合并 →     |              |              |              |              |              |
| 8   | 家园共育      | ← Col1-6 合并 →     |              |              |              |              |              |

字段映射见 `templates/weekplan_mapping.md`。

### 10.3 数据模型 `weekly_plans` 表

| 字段                 | 类型     | 说明                               |
| -------------------- | -------- | ---------------------------------- |
| `id`               | INT PK   | 自增                               |
| `semester_id`      | INT FK   | 关联学期                           |
| `week_number`      | INT      | 学期第几周                         |
| `week_start_date`  | DATE     | 本周周一日期                       |
| `week_end_date`    | DATE     | 本周周五日期                       |
| `grade`            | VARCHAR  | 年级                               |
| `class_name`       | VARCHAR  | 班级                               |
| `theme`            | VARCHAR  | 本周活动主题                       |
| `teacher_name`     | VARCHAR  | 教师姓名（快照）                   |
| `carer_name`       | VARCHAR  | 保育员姓名（快照）                 |
| `days_json`        | JSON     | 每日计划快照（WeekDayPlan 列表）   |
| `week_focus`       | TEXT     | 本周重点                           |
| `env_setup`        | TEXT     | 环境创设                           |
| `life_habits`      | TEXT     | 生活习惯培养                       |
| `home_school`      | TEXT     | 家园共育                           |
| `status`           | ENUM     | draft / completed                  |
| `created_at`       | DATETIME | 创建时间                           |
| `updated_at`       | DATETIME | 更新时间                           |

唯一键：`(semester_id, week_number, grade, class_name)`。

### 10.4 AI 提示词分类

新增 3 类，沿用现有提示词管理页：

| 分类                   | 用途                       |
| ---------------------- | -------------------------- |
| `weekly_morning_talk`  | 批量生成 5 天晨间谈话      |
| `weekly_outdoor_game`  | 批量生成 5 天户外游戏      |
| `weekly_area_game`     | 批量生成 5 天区域游戏      |
| `weekly_summary`       | 生成本周重点/环境/生活/家园 |

### 10.5 新增文件

| 文件                              | 作用                                     |
| --------------------------------- | ---------------------------------------- |
| `app/models/weekly_plan.py`       | WeekDayPlan / WeeklyPlan dataclass + CRUD |
| `app/pages/weekly_plan.py`        | 周计划页面（NiceGUI）                    |
| `templates/weekplan_mapping.md`   | 模板字段映射文档                         |

### 10.6 修改文件

| 文件                          | 改动                                   |
| ----------------------------- | -------------------------------------- |
| `app/db.py`                   | 新增 `weekly_plans` DDL + 迁移         |
| `app/services/date_utils.py`  | 新增 `get_week_info()` 等周级工具函数  |
| `app/services/ai_service.py`  | 新增 4 类周计划 AI 生成方法            |
| `app/services/word_export.py` | 新增 `export_weekly_plan_word()`        |
| `app/pages/settings.py`       | 新增教师姓名、保育员姓名设置项         |
| `app/pages/prompt_mgmt.py`    | 扩展周计划提示词分类                   |
| `app/main.py`                 | 新增 `/weekly-plan` 路由与导航项       |

### 10.7 周计划验收清单

1. 选择日期后自动推导本周周次、各天日期、工作日/放假日标记
2. 点击"从一日计划同步"后，已有一日计划的集体活动填入对应天格；缺失天保留空白
3. AI 生成整周晨间谈话、户外游戏、区域游戏、本周重点等内容
4. 节假日当天晨间谈话显示空，集体活动显示"放假"
5. 保存后刷新页面仍能恢复快照内容
6. 导出 Word：表格内容与 weekplan.docx 模板位置一致，教师/保育员/周次/日期正确填充

---

## 11. 一日计划验收清单

1. `uv run python -m app.main` 启动无报错,4 页面均可访问
2. MySQL 连接成功,5 张表自动创建
3. 设置页保存数据,刷新仍在
4. 粘贴教案 → AI 拆分 5 字段全部填充,活动过程双 Tab 可见 diff
5. 日期选择显示正确周次和星期
6. AI 生成 4 块活动内容
7. 导出 Word:表格结构与模板一致,AI 修改环节红字
8. 自定义提示词激活后实际生效
9. 历史记录可重新导出旧计划
