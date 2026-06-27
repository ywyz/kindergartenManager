# 一对一倾听观察子系统 — 设计文档

> 本文档为「一对一倾听观察记录」子系统（dev3.1）的需求与技术设计说明。配套文档：
> - 开发计划：[dev-plan.md](dev-plan.md)
> - 测试计划：[test-plan.md](test-plan.md)
>
> 阅读前置：[../PRD.md](../PRD.md)、[../architecture.md](../architecture.md)、[../tech-stack.md](../tech-stack.md)、
> [游戏观察设计](../game-observation/design.md)（本子系统大量复用其模式）与
> `.github/instructions/*.instructions.md`（数据库 / AI / Word 导出约定）。

## 1. 目标与范围

教师对**单个幼儿**进行「一对一倾听」观察：录入元数据（观察年月、姓名、成人数、年龄）+ 选择年级学期 →
针对**健康、语言、社会、艺术、科学五大领域**，每个领域：
1. AI 生成该领域观察目标（1~2 点）；
2. 系统自动从观察月份的前三周各取一个工作日（排除法定节假日，可手动改）；
3. 上传 3 张幼儿绘画照片（每张配一个日期）；
4. 照片存入 MySQL，并送视觉 AI：图上**有字识别文字、无字以幼教专家身份描述绘画内容**；
5. 依据绘画内容对该领域的**二级指标**评定达成星级（1~3 星，AI 生成、用户可改、未涉及默认 3 星）；
6. AI 生成约 200 字的**综合评价**与**支持策略**。

全部数据持久化到 MySQL，支持历史查询、重新导出，并能导出为 Word（多种拆分模式）。

### 1.1 本期范围（小班下学期）
- 仅内置「小班下学期」一套指标（模板 `templates/OneOnOneListeningSmallSecond.docx`）。
- 五大领域指标目录预置入库，UI/AI/导出均以入库目录为准。

### 1.2 后期扩展（不在本期，但架构需预留）
- 小班上学期、中班上下学期、大班上下学期：指标不同、逻辑相同。
- 通过 `indicator_catalog` 表按 `(grade, term, domain)` 扩展，无需改代码结构。

## 2. 已确认的关键决策

| # | 主题 | 决策 |
|---|------|------|
| 1 | 数据粒度 | 一条 `listening_record` = 一个幼儿全部 5 领域内容；导出时按领域拆分 |
| 2 | 年月与日期 | **领域级独立**：每个领域各自的观察年月 + 3 个工作日（表单选默认年月→预填 5 领域→各领域可独立改） |
| 3 | 绘画照片 | 每领域 3 张（5 领域共 15 张/幼儿），每张配一个日期 |
| 4 | 年级/学期来源 | 年级取 `class_config`、学期取 `semester_config`，并提供表单下拉（当前仅「小班下学期」），下拉为权威值 |
| 5 | 指标目录 | DB 表 `indicator_catalog`，按 `(grade, term, domain)` 组织，迁移预置小班下学期，含 `tenant_id`（seed 默认租户 1），后期可扩展/编辑 |
| 6 | 工作日选取 | 自动从当月第 1/2/3 周各取 1 个工作日（排除法定节假日），用户可改 |
| 7 | AI 调用粒度 | **每领域 1 次视觉调用**，返回结构化 JSON（目标 + 3 图描述 + 各二级指标星级 + 综合评价 + 支持策略），共 5 次/记录 |
| 8 | 图片文字识别 | 由视觉模型在该领域调用内完成：有字→返回文字；无字/无法识别→以幼教专家身份描述绘画内容 |
| 9 | 星级默认值 | AI 生成 1~3 星；绘画未涉及的指标默认 3 星；用户可在 UI 修改 |
| 10 | 视觉模型配置 | 复用既有「视觉模型」独立配置（`ai_api_key.key_type='vision'`） |
| 11 | 图片存储 | 复用 MySQL BLOB 可插拔存储（`image_storage`），入库前 Pillow 压缩 ≤ 1MB |

## 3. Word 模板字段映射

模板：`templates/OneOnOneListeningSmallSecond.docx`，含 **5 个表格**，每个表格前有一个标题段落。

### 3.1 整体结构

| 表序 | 领域 | 行数 | 标题段落文本 |
|------|------|------|--------------|
| TABLE 0 | 健康 | 31 | `“一对一倾听”观察记录中，小班幼儿    健康领域    的发展评价` |
| TABLE 1 | 语言 | 28 | `…语言领域…` |
| TABLE 2 | 社会 | 31 | `…社会领域…` |
| TABLE 3 | 科学 | 28 | `…科学领域…` |
| TABLE 4 | 艺术 | 22 | `…艺术领域…` |

> 行数差异源于各领域二级指标数量不同（每指标占 3 行）。

### 3.2 单领域表格布局（6 列；行号以健康领域 31 行为例）

| 行(0基) | 列(逻辑) | 内容 | 数据来源 |
|--------|---------|------|---------|
| R0 | C0–C5 合并 | 元数据块：`观察日期：`/`幼儿姓名：`/`成人数目：`/`幼儿年龄：`/`目标：`（5 行，需在冒号后填值） | 表单 + AI（目标=该领域目标 1~2 点） |
| R1 | C0–C3 合并 / C4–C5 合并 | `幼儿绘画表征（  月  日）` / `一对一倾听记录` | 日期 1（填月日） |
| R2 | C0–C3 合并 / C4–C5 合并 | 绘画图片 1 / 倾听记录 1（图片描述） | 上传图片 + AI 描述 |
| R3–R4 | 同上 | 绘画 2 + 倾听记录 2 | 日期 2 + 图片 + AI |
| R5–R6 | 同上 | 绘画 3 + 倾听记录 3 | 日期 3 + 图片 + AI |
| R7 | C0..C5 | 指标表头：`一级指标` `二级指标` `评价要求` `评价指标` `具体标准` `评价` | 模板固定 |
| R8..R(末-2) | C0 竖排领域名（跨所有指标行合并）；C1 一级指标；C2 二级指标；C3 `★`/`★★`/`★★★`；C4 具体标准；C5 评价 | 每个二级指标占 3 行（★/★★/★★★） | C0–C4 模板固定；**C5 由系统打勾** |
| R(末-1) | C0 竖排`综合评价`；C1–C5 合并 | 综合评价内容 | AI 约 200 字 |
| R(末) | C0 竖排`支持策略`；C1–C5 合并 | 支持策略内容 | AI 约 200 字 |

各领域指标数与末两行位置：

| 领域 | 二级指标数 | 指标行范围 | 综合评价行 | 支持策略行 |
|------|-----------|-----------|-----------|-----------|
| 健康 | 7 | R8–R28 | R29 | R30 |
| 语言 | 6 | R8–R25 | R26 | R27 |
| 社会 | 7 | R8–R28 | R29 | R30 |
| 科学 | 6 | R8–R25 | R26 | R27 |
| 艺术 | 4 | R8–R19 | R20 | R21 |

### 3.3 写入规则

- **元数据 R0**：清空原占位文本，按行写入 `观察日期：{年}年{月}月`、`幼儿姓名：{name}`、`成人数目：{n}`、`幼儿年龄：{age}`、`目标：{AI 目标}`。
- **绘画表头 R1/R3/R5**：将 `幼儿绘画表征（  月  日）` 中的月、日替换为该领域 date_1/2/3 的月、日。
- **绘画图片 R2/R4/R6 左格（C0–C3）**：清空后插入压缩图片（按可用宽度等比缩放）。
- **倾听记录 R2/R4/R6 右格（C4–C5）**：写入该图的 AI 描述（图上文字或绘画内容描述）。
- **指标打勾 C5**：第 `i` 个二级指标（0 基，按 `sort_order`）的 3 档分别在 `R8+3i`、`+1`、`+2`；评定星级 `s`（1~3）时在 `R8+3i+(s-1)` 行的 **C5** 写入 `√`。
- **综合评价 / 支持策略**：写入末两行的 C1（合并区）。
- 所有文字 run 显式设置宋体 + `w:eastAsia`，避免中文乱码（复用 `_set_font`）。
- 写入前必须清空模板示例文本（复用 `_clear_cell`）。

## 4. 数据模型

遵循 `.github/instructions/database.instructions.md`：所有业务表含 `tenant_id / user_id / created_at / updated_at`，
查询强制携带 `tenant_id`，schema 变更走 Alembic，禁止 `create_all()`。

五大领域常量：`["健康", "语言", "社会", "艺术", "科学"]`（应用层定义）。

### 4.1 新表 `listening_record`（主表 / 一个幼儿一次记录）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | |
| tenant_id / user_id | BIGINT | 隔离字段 |
| obs_year | INT | 主观察年（历史筛选用；领域可各自覆盖） |
| obs_month | INT | 主观察月（1~12） |
| child_name | VARCHAR(64) | 幼儿姓名（单个幼儿） |
| adult_count | INT | 成人数目（默认 1） |
| child_age | VARCHAR(16) | 幼儿年龄（如「4岁」，由年级推断） |
| grade | VARCHAR(16) | 年级（小/中/大班，冗余自 class_config） |
| term | VARCHAR(16) | 学期（上学期/下学期） |
| class_name | VARCHAR(32) | 班级（冗余） |
| observer | VARCHAR(64) | 观察者（默认显示名，可改） |
| created_at / updated_at | DATETIME | |

### 4.2 新表 `listening_domain`（每记录 5 条，每领域一条）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | |
| tenant_id / user_id | BIGINT | 隔离字段 |
| record_id | BIGINT | 逻辑外键 → listening_record.id |
| domain | VARCHAR(8) | 健康/语言/社会/艺术/科学 |
| obs_year | INT | **领域级独立**观察年 |
| obs_month | INT | **领域级独立**观察月 |
| date_1 / date_2 / date_3 | DATE NULL | 三个工作日（对应 3 张绘画） |
| goals | TEXT | AI：该领域目标 1~2 点 |
| evaluation | TEXT | AI：综合评价（约 200 字） |
| support_strategy | TEXT | AI：支持策略（约 200 字） |
| created_at / updated_at | DATETIME | |

### 4.3 新表 `listening_image`（每领域 3 张，共 15 张/记录）
结构复用 `game_observation_image`，新增 `domain` 与 `image_description`。
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | |
| tenant_id / user_id | BIGINT | 隔离字段 |
| record_id | BIGINT | 逻辑外键 → listening_record.id |
| domain | VARCHAR(8) | 所属领域 |
| image_index | INT | 1~3（控制顺序，对应 date_1/2/3） |
| storage_backend | VARCHAR(16) | 默认 `mysql_blob` |
| blob_content | LONGBLOB / LargeBinary | 压缩后二进制 |
| object_key | TEXT NULL | 远端后端对象键（本期 NULL） |
| mime_type | VARCHAR(32) | 如 image/jpeg |
| file_size / width / height | INT NULL | 压缩后尺寸 |
| image_description | TEXT NULL | AI：图上文字或绘画内容描述 |
| created_at / updated_at | DATETIME | |

### 4.4 新表 `listening_indicator_result`（每记录每领域每二级指标一条）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | |
| tenant_id / user_id | BIGINT | 隔离字段 |
| record_id | BIGINT | 逻辑外键 → listening_record.id |
| domain | VARCHAR(8) | 所属领域 |
| catalog_id | BIGINT | 逻辑外键 → indicator_catalog.id |
| stars | INT | 达成星级 1~3（默认 3） |
| created_at / updated_at | DATETIME | |

### 4.5 新表 `indicator_catalog`（参考数据，迁移预置）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | |
| tenant_id | BIGINT | 隔离（seed 默认租户 1；后期可按园所定制） |
| grade | VARCHAR(16) | 小/中/大班 |
| term | VARCHAR(16) | 上学期/下学期 |
| domain | VARCHAR(8) | 五大领域 |
| level1_name | VARCHAR(64) | 一级指标（如「身心状况」） |
| level2_name | VARCHAR(512) | 二级指标 / 评价要求 |
| sort_order | INT | 同领域内排序（**必须与模板行序一致**，用于导出定位） |
| standard_star1 / 2 / 3 | TEXT | ★/★★/★★★ 三档具体标准 |
| max_stars | INT | 默认 3 |
| created_at / updated_at | DATETIME | |

> 唯一性建议索引：`(tenant_id, grade, term, domain, sort_order)`。
> 种子数据已从模板提取：`alembic/seed_data/listening_indicators_xiaoban_xia.json`（30 个二级指标，每个 3 档标准，校验通过）。

### 4.6 既有表增列
- `prompt_template.task_type` Enum 增加值 `one_on_one_listening`。
- `export_records` 增加 `listening_record_id BIGINT NULL`（导出历史关联）。

## 5. AI 视觉集成设计

遵循 `.github/instructions/ai-integration.instructions.md`：统一入口、超时、tenacity 重试、强约束 JSON、Key 解密后仅内存使用、不写日志。

- **复用 `vision_base.call_ai_vision`** 与视觉 Key（`get_active_ai_key(key_type='vision')`）。
- **新增 `app/integration/ai_client/listening_client.py`**：`generate_listening_domain(images, context, indicators, ...) -> dict`，
  **每领域一次调用**，输入：3 张该领域绘画 + 上下文（年级、学期、领域、幼儿年龄）+ 该领域二级指标清单（含 3 档标准），
  输出严格 JSON：
  ```json
  {
    "goals": "该领域观察目标 1~2 点（纯文本）",
    "image_descriptions": ["图1描述", "图2描述", "图3描述"],
    "indicators": [
      {"sort_order": 0, "stars": 2},
      {"sort_order": 1, "stars": 3}
    ],
    "evaluation": "综合评价约200字",
    "support_strategy": "支持策略约200字"
  }
  ```
  - 提示词要求：对每张图先判断有无文字，有字识别并返回文字，无字以幼教专家身份描述绘画内容；
    依据绘画对每个二级指标评定 1~3 星，**未涉及默认 3 星**；评价/策略各约 200 字；纯文本、禁 Markdown。
  - `image_descriptions` 必须与上传图片数量一致；`indicators` 必须覆盖该领域全部二级指标（按 `sort_order`）。
  - 缺字段或数量不符 → 记录日志并抛 `AiParseError`；缺失的指标星级在服务层降级为默认 3 星。
- **提示词管理**：`task_type=one_on_one_listening` 接入提示词管理（多版本 + 回滚）；服务层优先 DB 激活版本，否则用内置默认。

## 6. 图片处理与存储

- 复用 `app/integration/image_processing.py::compress_image`（≤ 1MB）。
- 复用 `app/integration/image_storage/blob_backend.py::BlobImageStorage`（MySQL BLOB）。
- 每领域至少 1 张才能生成；导出时按 image_index 顺序填入 R2/R4/R6。

## 7. 工作日选取

- **新增 `app/service/date_service.py::pick_three_workdays(year, month, is_holiday=None) -> list[date]`**（纯函数，节假日判定可注入）：
  - 将当月按自然周（周一为周首）划分，取前三个「包含工作日」的周，各取该周第一个工作日（周一~周五且非法定节假日）。
  - `is_holiday` 为可选回调 `(date) -> bool | None`；返回 `True` 跳过该日，`None`（API 不可用）视为非节假日不阻断（降级原则）。
  - 不足 3 个时返回已找到的（UI 提示用户手动补全）。
- 服务层用 `holiday_client.is_holiday` 包装为同步回调注入；单测用桩函数。
- UI 提供「自动选取」按钮 + 3 个可编辑日期框（每领域一组）。

## 8. Word 导出设计

遵循 `.github/instructions/word-export.instructions.md`：`python-docx` 主方案，复用 `observation_exporter` 的
`_set_font` / `_clear_cell` / `_write_cell` / `_add_images_to_cell` 等辅助。

- **新增 `app/integration/word_export/listening_exporter.py`**，提供三种导出模式：
  1. **合并导出（单幼儿 5 领域 → 1 个 docx）**：打开模板，按 5 表填充该幼儿全部领域内容。
  2. **按领域拆分（单幼儿 5 领域 → 5 个 docx）**：每个领域单独成档（仅保留该领域 1 个表 + 标题），返回 `{领域: bytes}`，UI 打包为 zip。
  3. **批量按领域（多/选定幼儿 → 5 个 docx，每档一个领域含所有选定幼儿）**：对每个领域，复制该领域表格为每个幼儿各一份（`copy.deepcopy(table._tbl)` 追加），返回 `{领域: bytes}`，打包 zip。
- **拆分实现**：以「标题段落 + 紧随表格」为一个领域单元。删除其它领域的标题与表格元素（操作 `document.element.body`），或在空白文档中追加目标领域的标题与表格副本。
- **领域顺序**：模板为 健康/语言/社会/科学/艺术；批量导出文件命名/顺序可按用户偏好（语言/艺术/社会/科学/健康）配置，默认按模板顺序。
- 模板缺失时降级 `_build_from_scratch`（简化表格）。

## 9. 指标目录与种子

- 种子 JSON：`alembic/seed_data/listening_indicators_xiaoban_xia.json`，结构：
  ```json
  {"grade":"小班","term":"下学期","domains":{"健康":[{"level1","level2","sort_order","standards":{"1","2","3"}}, ...], ...}}
  ```
- 数据迁移读取该 JSON，`bulk_insert` 到 `indicator_catalog`（tenant_id=1）。
- `indicator_repository.list_indicators(grade, term, domain)` 供 UI/AI 读取（按 `sort_order` 升序）。

## 10. 路由与导航

| 路由 | 鉴权 | 变更 |
|------|------|------|
| `/one-on-one-listening` | 单用户 | 新增主页面（表单 + 5 领域分区 + 生成/保存/导出 + 历史） |
| 共享布局 `app_shell` | — | 「教学管理」分组新增菜单项「一对一倾听」 |
| `/prompts` | 单用户 | 新增 `one_on_one_listening` 提示词 Tab |

## 11. 安全与隔离

- 所有新查询强制 `tenant_id` 过滤；记录/领域/图片/指标结果均按 `(tenant_id, user_id)` 隔离。
- 视觉模型 API Key Fernet 加密入库、脱敏展示、禁止写日志。
- 图片为隐私数据：读取接口校验 `tenant_id`。
- 审计：`ai_listening`（视觉生成）、`export_listening`（导出）接入 `log_audit`。

## 12. 验收标准

1. 录入元数据 + 选择年级学期，5 个领域各上传 3 张绘画，点「生成」→ 每领域 AI 返回目标、3 图描述、各指标星级、综合评价、支持策略并回填，全部可编辑。
2. 自动选取的 3 个工作日正确（前三周各一个、排除法定节假日），可手动修改；各领域独立。
3. 指标星级 AI 生成、用户可改、未涉及默认 3 星。
4. 保存后数据（含图片）持久化，可在历史中查看并重新导出。
5. 图片入库前压缩 ≤ 1MB。
6. 导出三种模式正确：单幼儿合并（1 档）、单幼儿按领域（5 档）、批量按领域（5 档含多幼儿）；中文不乱码、指标打勾 `√` 在正确星级行、图片/日期/目标/评价/策略就位。
7. 视觉模型独立配置可用；未配置时友好提示。
8. 提示词管理可维护 `one_on_one_listening` 多版本并回滚。
9. 架构预留后期年级/学期扩展（仅需在 `indicator_catalog` 增数据）。
