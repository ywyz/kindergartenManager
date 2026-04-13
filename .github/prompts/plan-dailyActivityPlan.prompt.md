# Plan: 教学管理-每日活动计划系统

## TL;DR
基于 NiceGUI + Python 3.14 构建幼儿园每日活动计划撰写与收集系统。分5个阶段迭代开发：基础架构 → 教案AI拆分 → 一日计划AI生成 → Word导出 → 提示词管理。使用 pymysql 存储数据，python-docx 生成 Word，openai 库连接AI。

## 项目上下文
- **UV环境**: teacherplan（已创建，已安装 nicegui, pymysql, openai, requests, python-docx, openpyxl）
- **MySQL**: aliyun.ywyz.tech，root用户，需新建数据库和表
- **年级班级**: 小班1-4班、中班1-4班、大班1-4班
- **Word模板**: templates/teacherplan.docx（单表格）
- **用户认证**: 先做单用户版本，后续集成登录系统
- **AI API**: 全局配置 + 用户可覆盖
- **导出格式**: python-docx 生成 Word

## Word模板表格结构
单个表格，结构如下：
1. 第( )周（整行）
2. 月 日 周()（整行）
3. **晨间活动** → 体能大循环/集体游戏/自选游戏 + 重点指导/活动目标/指导要点
4. **晨间谈话** → 谈话主题 + 问题设计
5. **集体活动** → 活动主题/活动目标/活动重点/活动难点/活动过程
6. **室内区域活动** → 游戏区域 + 重点指导/活动目标/指导要点 + 支持策略
7. **户外游戏活动** → 游戏区域 + 重点指导/活动目标/指导要点 + 支持策略
8. **一日活动反思** → 空白

---

## Phase 1: 项目基础架构（所有后续阶段依赖）

### Step 1.1 项目目录结构
创建以下目录结构：
```
kindergartenManager/
├── app/
│   ├── __init__.py
│   ├── main.py              # NiceGUI 入口，启动应用
│   ├── config.py             # 配置管理（MySQL连接、AI API默认配置）
│   ├── db.py                 # PyMySQL 数据库连接池和通用操作
│   ├── models/
│   │   ├── __init__.py
│   │   └── daily_plan.py     # 每日活动计划数据模型
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── settings.py       # 设置页面（学期时间、年级班级、AI配置）
│   │   ├── lesson_split.py   # 教案AI拆分页面
│   │   ├── daily_plan.py     # 一日活动计划AI生成页面
│   │   ├── prompt_mgmt.py    # 提示词管理页面
│   │   └── plan_history.py   # 历史计划查看页面
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py     # AI API 调用封装
│   │   ├── word_export.py    # Word 导出服务
│   │   ├── date_utils.py     # 日期计算（第几周、周几、是否工作日、节假日临近）
│   │   └── plan_service.py   # 计划的CRUD业务逻辑
│   └── static/               # 静态资源（如果需要）
├── templates/
│   └── teacherplan.docx      # Word模板（已有）
├── .env                      # 环境变量（MySQL密码、默认AI Key等，gitignore）
├── .gitignore
└── pyproject.toml            # UV项目配置（已有）
```

### Step 1.2 数据库设计
在 MySQL 创建数据库 `kindergarten` 及以下表：

**semester_settings** - 学期设置
- id, semester_name, start_date, end_date, grade, class_name, created_at, updated_at

**ai_config** - AI配置
- id, api_url, api_key（加密存储）, model_name, is_global, user_id(nullable), created_at

**daily_plans** - 每日活动计划
- id, plan_date, week_number, day_of_week, grade, class_name, semester_id(FK)
- morning_activity_json (晨间活动所有字段的JSON)
- morning_talk_json (晨间谈话所有字段的JSON)
- group_activity_json (集体活动所有字段的JSON)
- indoor_area_json (室内区域活动所有字段的JSON)
- outdoor_game_json (户外游戏活动所有字段的JSON)
- daily_reflection (一日活动反思)
- original_lesson_text (原始教案文本)
- ai_modified_parts_json (AI修改部分的JSON，用于红色标记)
- status (draft/completed)
- created_at, updated_at

**prompts** - 提示词管理
- id, prompt_name, prompt_category (lesson_split/daily_plan/morning_activity等), prompt_content, is_active, created_at, updated_at

### Step 1.3 配置管理
- `config.py`: 从 `.env` 文件读取 MySQL 连接信息和默认AI API配置
- `.env` 文件包含: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DEFAULT_AI_URL, DEFAULT_AI_KEY, DEFAULT_AI_MODEL
- `.gitignore` 排除 .env

### Step 1.4 数据库连接层
- `db.py`: 封装 pymysql 连接，提供 `get_connection()`, `execute_query()`, `execute_many()` 等基础方法
- 启动时自动检查并创建所需表（如果不存在）

### Step 1.5 NiceGUI 应用骨架
- `main.py`: 创建 NiceGUI 应用，配置路由和导航
- 左侧导航栏：设置 / 教案拆分 / 一日计划 / 提示词管理 / 历史记录
- 页面路由：`/settings`, `/lesson-split`, `/daily-plan`, `/prompts`, `/history`

### Step 1.6 日期工具
- `date_utils.py`:
  - `calc_week_number(semester_start, target_date)` → 第几周
  - `get_day_of_week(date)` → 周几（中文）
  - `is_workday(date)` → 是否工作日（基于周一至周五）
  - `is_near_holiday(date)` → 是否临近节假日（前后3天内有法定节假日）

---

## Phase 2: 教案AI拆分功能（依赖 Phase 1）

### Step 2.1 设置页面 (`pages/settings.py`)
- 学期开始/结束日期选择器
- 年级下拉（小班/中班/大班）+ 班级下拉（1-4班）
- 区域游戏内容文本框（可保存多条）
- 户外游戏内容文本框（可保存多条）
- AI API 配置区域：API地址、API Key（密码输入框）、模型名称
  - 显示全局默认值，用户可覆盖
  - API Key 在页面上用密码掩码显示
- 保存按钮 → 写入 MySQL

### Step 2.2 AI服务封装 (`services/ai_service.py`)
- 使用 openai 库，支持自定义 base_url
- `split_lesson_plan(text, grade)` → 调用AI拆分教案为JSON：{活动主题, 活动目标, 活动准备, 活动重点, 活动难点, 活动过程}
- `modify_activity_process(original_process, grade)` → 根据年龄段修改活动过程，返回修改后文本
- 统一的错误处理和重试机制
- 提示词从 prompts 表读取（如果有），否则使用内置默认提示词

### Step 2.3 教案拆分页面 (`pages/lesson_split.py`)
- 顶部：选择日期 → 自动显示第几周、周几、是否工作日（非工作日弹出警告）
- 大文本区域：粘贴完整教案
- 「AI拆分」按钮：
  1. 调用 `split_lesson_plan()` 拆分教案
  2. 将拆分结果填充到下方表单字段中
  3. 调用 `modify_activity_process()` 修改活动过程
  4. 显示原始 vs 修改后的对比视图（diff 高亮）
  5. 用户选择采用修改版还是原始版
- 表单字段（可编辑）：活动主题、活动目标、活动准备、活动重点、活动难点、活动过程
- 「保存」按钮 → 存入 daily_plans 表

---

## Phase 3: 一日活动计划AI生成（依赖 Phase 1，可与 Phase 2 并行开发）

### Step 3.1 计划生成AI服务扩展 (`services/ai_service.py`)
- `generate_morning_activity(week, day, grade, outdoor_content)` → 生成晨间活动内容
- `generate_morning_talk(week, day, grade, near_holiday)` → 生成晨间谈话
- `generate_indoor_area(grade, area_content)` → 生成室内区域活动
- `generate_outdoor_game(grade, outdoor_content)` → 生成户外游戏活动
- 每个方法从 prompts 表读取对应类别的提示词

### Step 3.2 一日活动计划页面 (`pages/daily_plan.py`)
- 顶部同教案拆分页面：日期选择 → 周次、星期、工作日判断
- 完整表单对应模板8个大项的所有子字段
- 「AI生成」按钮：根据设置中的年级、班级、区域内容、户外内容，调用AI生成以下内容：
  - 晨间活动（体能大循环、集体游戏、自选游戏、重点指导、活动目标、指导要点）
  - 晨间谈话（谈话主题、问题设计）
  - 室内区域活动（游戏区域、重点指导、活动目标、指导要点、支持策略）
  - 户外游戏活动（游戏区域、重点指导、活动目标、指导要点、支持策略）
- 集体活动部分从教案拆分结果中读取（如果已保存当天的教案）
- 一日活动反思：手动填写
- 「保存」和「导出Word」按钮

---

## Phase 4: Word导出（依赖 Phase 2 和 Phase 3）

### Step 4.1 Word导出服务 (`services/word_export.py`)
- 读取 templates/teacherplan.docx 作为模板
- 使用 python-docx 定位表格中的各个单元格
- 按模板结构将表单数据填充进对应位置
- **红色字体处理**：对比 `original_lesson_text` 和 `ai_modified_parts_json`，AI修改过的部分使用红色字体（`RGBColor(0xFF, 0x00, 0x00)`）
- 填写周次、日期等头部信息
- 生成的 Word 文件通过 NiceGUI 的下载功能提供给用户

### Step 4.2 集成到页面
- 在教案拆分页面和一日计划页面都添加「导出Word」按钮
- 点击后调用 `word_export.py` 中的导出函数，触发浏览器下载

---

## Phase 5: 提示词管理（依赖 Phase 1，可与 Phase 2/3 并行）

### Step 5.1 提示词管理页面 (`pages/prompt_mgmt.py`)
- 提示词分类：教案拆分(lesson_split)、活动过程修改(process_modify)、晨间活动(morning_activity)、晨间谈话(morning_talk)、室内区域(indoor_area)、户外游戏(outdoor_game)
- 每个分类可创建/编辑/删除提示词
- 标记当前激活的提示词（is_active）
- 提示词中支持占位符变量：{grade}、{week}、{day}、{content} 等
- 提供内置默认提示词，用户可修改

### Step 5.2 AI服务与提示词集成
- `ai_service.py` 中的所有方法优先从 prompts 表读取 is_active=True 的提示词
- 如果没有自定义提示词，使用代码中的默认提示词
- 在提示词管理页面提供「测试」按钮，发送测试内容验证提示词效果

---

## Relevant Files

| 文件 | 作用 |
|---|---|
| `app/main.py` | NiceGUI 入口，路由和导航布局 |
| `app/config.py` | 环境变量读取，MySQL/AI默认配置 |
| `app/db.py` | PyMySQL 连接封装，自动建表 |
| `app/models/daily_plan.py` | 数据模型与 CRUD |
| `app/services/ai_service.py` | AI调用：教案拆分、内容生成 |
| `app/services/word_export.py` | Word模板填充、红色差异标记 |
| `app/services/date_utils.py` | 周次/工作日/节假日计算 |
| `app/services/plan_service.py` | 计划保存/读取业务逻辑 |
| `app/pages/settings.py` | 设置页面 |
| `app/pages/lesson_split.py` | 教案AI拆分页面 |
| `app/pages/daily_plan.py` | 一日活动计划页面 |
| `app/pages/prompt_mgmt.py` | 提示词管理页面 |
| `app/pages/plan_history.py` | 历史计划查看 |
| `templates/teacherplan.docx` | Word模板（已有） |
| `.env` | 敏感配置（不入Git） |

---

## Verification

1. 运行 `uv run python app/main.py` → NiceGUI 启动无报错，所有页面可访问
2. MySQL 连接成功，4张表自动创建
3. 设置页保存数据 → 刷新后数据仍在
4. 粘贴教案 → AI拆分返回正确JSON → 表单填充 → 活动过程对比显示
5. 日期选择显示正确周次和星期 → AI生成各项内容
6. 导出Word → 表格结构与模板一致、位置正确、AI修改部分红色字体
7. 自定义提示词 → AI使用新提示词生效
8. 在 `feature/daily-plan` 分支开发，完成后合并 main

---

## Decisions

- **单用户优先**: 不实现登录系统，user_id 字段预留，后续集成账号管理系统时启用
- **AI API 安全**: API Key 在数据库中加密存储，.env 中的全局 Key 不入 Git
- **节假日判断**: 初版按周一至周五判断工作日，不接入外部节假日API（可扩展）
- **Git分支**: 使用 `feature/daily-plan` 分支开发，完成后合并到 main
- **排除范围**: 不含登录系统、备课笔记、周/月计划等其他教学管理功能
