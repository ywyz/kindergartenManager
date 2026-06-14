# 游戏观察子系统 — 设计文档

> 本文档为「游戏观察记录」子系统的需求与技术设计说明。配套文档：
> - 开发计划：[dev-plan.md](dev-plan.md)
> - 测试计划：[test-plan.md](test-plan.md)
>
> 阅读前置：[../PRD.md](../PRD.md)、[../architecture.md](../architecture.md)、[../tech-stack.md](../tech-stack.md) 与
> `.github/instructions/*.instructions.md`（数据库 / AI / Word 导出约定）。

## 1. 目标与范围

教师对幼儿游戏过程进行观察记录：录入元数据 + 上传 1~3 张游戏照片，调用**视觉 AI** 自动生成
「观察目标 / 观察记录 / 评价分析 / 支持策略」四段内容，填充进 Word 模板
`templates/ObservationRecord.docx` 并导出，同时全部数据（含图片）持久化到云端 MySQL，支持历史查询与重新导出。

本子系统附带两项**账号体系增强**（因「观察者」字段衍生）：
1. 自助注册（邀请码 + 管理员审核）。
2. 个人资料页（显示名/真实姓名管理）。

### 1.1 不在本期范围
- 云对象存储（S3 / WebDAV）落地：仅预留可插拔存储接口，本期只实现 MySQL BLOB 后端。
- 观察记录的批量导出（首期单条导出；如需批量可后续比照教案批量导出实现）。

## 2. 已确认的关键决策

| # | 主题 | 决策 |
|---|------|------|
| 1 | AI 生成方式 | 多模态视觉：1~3 张图片 + 元数据 → 视觉模型 → 返回 4 段文本（结构化 JSON 一次返回） |
| 2 | 视觉模型配置 | 独立配置：单独 `api_base_url` + `api_key` + `model`，与文本模型分离 |
| 3 | 图片存储 | 初期 MySQL BLOB；设计可插拔存储层，后期接入 S3 / WebDAV |
| 4 | 图片处理 | 入库前用 Pillow 压缩，单图 ≤ 1MB，超限自动缩小 |
| 5 | 提示词 | 新增 `task_type=game_observation`，接入提示词管理（多版本 + 回滚） |
| 6 | 持久化 | 新建 `game_observation` + `game_observation_image` 表 |
| 7 | 观察者 | 自动填当前登录用户的显示名，允许手动修改 |
| 8 | 显示名 | `user` 表新增 `display_name`；新增个人资料页可编辑 |
| 9 | 自助注册 | 邀请码绑定 `tenant_id`，默认角色 `teacher`，`is_active=False` 待审核 |
| 10 | 邀请码 | 新建 `invite_code` 表，由 `sys_admin` 在账号管理页生成 / 启用 / 停用 |
| 11 | 图片数量 | 1~3 张灵活（至少 1 张才能生成） |
| 12 | 图片排版 | 第 6 行「观察记录」右侧单元格内、文字下方横向并排，无标题文字 |
| 13 | 大环境 | 户外 / 室内 / 公共 → 仅填标题占位符 `（xx）` |
| 14 | 游戏区域 | 具体区域（如「建构区」）→ 填「观察环境」单元格 |
| 15 | 班级/年龄段 | 取自当前用户的班级配置（`class_config`），年龄段作为 AI 上下文 |

## 3. Word 模板字段映射

模板：`templates/ObservationRecord.docx`
- 标题段落：`南通市崇川区樾府幼儿园游戏观察记录（xx）`，其中 `xx`（第 2 个 run）替换为大环境（户外/室内/公共）。
- 单表格：8 行 × 8 列（逻辑列），左列为固定标题，右列为内容（部分跨列合并）。

| 行(0基) | 左列标题 | 内容单元格(逻辑列) | 数据来源 |
|--------|---------|------------------|---------|
| R0 | 班级 / 日期 / 起止时间 | 班级=C1、日期=C3、起止时间=C7 | 班级=班级配置；日期/起止时间=教师输入 |
| R1 | 成人数目 / 儿童数目 / 观察者 | 成人=C1、儿童=C3、观察者=C7 | 成人/儿童数目=教师输入；观察者=显示名(可改) |
| R2 | 幼儿姓名 / 幼儿年龄 | 姓名=C1、年龄=C6 | 教师输入 |
| R3 | 观察环境 | C1 | 具体游戏区域（教师输入） |
| R4 | 观察目标 | C1 | AI 生成 |
| R5 | 观察记录 | C1 | AI 生成（文字）+ 图片（文字下方横向并排） |
| R6 | 评价分析 | C1 | AI 生成 |
| R7 | 支持策略 | C1 | AI 生成 |

> 注意：模板示例单元格里残留示例文本（如「王鹤宁、侯舒妍」「\n\n」），写入前必须清空原有段落再写入。
> 合并单元格通过 `row.cells[idx]` 访问逻辑列，写入一次即可。

### 3.1 图片写入规则
- 位置：R5「观察记录」右侧合并单元格（`row.cells[1]`）内。
- 顺序：先写观察记录文字段落，再追加一个段落容纳图片。
- 排版：1~3 张图片在**同一段落**内以多个 inline run 横向并排（run 间以空格分隔），不跨单元格、无标题文字。
- 尺寸：按可用宽度等分（约每张宽度 4.5cm，3 张并排），保持比例。
- 中文字体：所有文字 run 显式设置宋体 + `w:eastAsia`，避免乱码（沿用既有 `_set_font`）。

## 4. 数据模型

遵循 `.github/instructions/database.instructions.md`：所有业务表含 `tenant_id / user_id / created_at / updated_at`，
查询强制携带 `tenant_id`，schema 变更走 Alembic，禁止 `create_all()`。

### 4.1 新表 `game_observation`
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | |
| tenant_id / user_id | BIGINT | 隔离字段 |
| obs_date | DATE | 游戏日期 |
| time_range | VARCHAR(64) | 起止时间（自由文本，如 9:00-9:40） |
| big_env | VARCHAR(8) | 大环境：户外 / 室内 / 公共 |
| game_area | VARCHAR(64) | 具体游戏区域（观察环境） |
| grade | VARCHAR(16) | 年龄段（冗余，取自班级配置） |
| class_name | VARCHAR(32) | 班级（冗余，取自班级配置） |
| adult_count | INT | 成人数目 |
| child_count | INT | 儿童数目 |
| child_names | VARCHAR(255) | 幼儿姓名 |
| child_age | VARCHAR(64) | 幼儿年龄 |
| observer | VARCHAR(64) | 观察者（默认显示名，可改） |
| observation_goal | TEXT | AI：观察目标 |
| observation_record | TEXT | AI：观察记录 |
| evaluation_analysis | TEXT | AI：评价分析 |
| support_strategy | TEXT | AI：支持策略 |
| created_at / updated_at | DATETIME | |

> `big_env` 取值约束在应用层校验（户外/室内/公共）。同一用户同日期允许多条观察记录（与教案 upsert 不同），按 id 区分。

### 4.2 新表 `game_observation_image`（可插拔存储）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | |
| tenant_id / user_id | BIGINT | 隔离字段 |
| observation_id | BIGINT | 逻辑外键 → game_observation.id |
| image_index | INT | 1~3，控制排序 |
| storage_backend | VARCHAR(16) | 默认 `mysql_blob`；预留 `s3` / `webdav` |
| blob_content | LONGBLOB / LargeBinary | BLOB 后端存压缩后二进制；其他后端为 NULL |
| object_key | VARCHAR(512) NULL | 远端后端的对象键（本期为 NULL） |
| mime_type | VARCHAR(32) | 如 image/jpeg |
| file_size | INT | 压缩后字节数（≤ 1MB） |
| width / height | INT | 压缩后尺寸（可选） |
| created_at / updated_at | DATETIME | |

> SQLite 测试用 `LargeBinary`，MySQL 生产用 `LONGBLOB` variant。

### 4.3 `ai_api_key` 增列
- 新增 `key_type` ENUM(`text`,`vision`)，`server_default='text'`（存量数据回填 text）。
- 仓库层按 `key_type` 查询激活记录：`get_active_ai_key(..., key_type='text'|'vision')`。
- 设置页拆分为「文本模型配置」与「视觉模型配置」两块；各自独立 active 记录。

### 4.4 `user` 增列
- 新增 `display_name` VARCHAR(64) NULL。观察者默认取 `display_name`，为空时回退 `username`。

### 4.5 新表 `invite_code`
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | |
| tenant_id | BIGINT | 邀请码绑定的机构 |
| code | VARCHAR(64) UNIQUE | 邀请码（随机生成） |
| note | VARCHAR(128) NULL | 备注 |
| is_active | BOOL | 是否可用 |
| created_by | BIGINT NULL | 生成者 user_id |
| created_at / updated_at | DATETIME | |

> `invite_code` 为配置类表但仍保留 `tenant_id`/时间戳；`user_id` 用 `created_by` 表达生成者。

## 5. AI 视觉集成设计

遵循 `.github/instructions/ai-integration.instructions.md`：统一入口、超时 60s、tenacity 重试 3 次、强约束 JSON、Key 解密后仅内存使用、不写日志。

- **新增 `app/integration/ai_client/vision_base.py`**：`call_ai_vision(messages, ...)`，
  支持 OpenAI 兼容多模态消息体：
  ```json
  {"role":"user","content":[
    {"type":"text","text":"..."},
    {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,...."}}
  ]}
  ```
  复用 base 的重试/超时/错误提取逻辑（抽取公共部分，避免重复）。
- **新增 `app/integration/ai_client/observation_client.py`**：`generate_observation(images, context, ...) -> dict`，
  输出严格 JSON：
  ```json
  {
    "observation_goal": "string",
    "observation_record": "string",
    "evaluation_analysis": "string",
    "support_strategy": "string"
  }
  ```
  内置默认提示词 `DEFAULT_OBSERVATION_PROMPT`（含格式约束：纯文本、禁 Markdown）。缺字段时按既有模式降级/抛 `AiParseError`。
- **提示词管理**：`task_type=game_observation` 接入；服务层优先查 DB 激活版本，否则用内置默认。
- **上下文**：传给 AI 的 `context` 含 `grade`（年龄段）、`big_env`、`game_area`、`child_age`、`child_count` 等，辅助生成贴合年龄/场景的内容。

## 6. 图片处理与存储抽象

- **`app/integration/image_processing.py`**：`compress_image(data, max_bytes=1MB) -> (bytes, mime, w, h)`。
  用 Pillow：超过阈值时按比例缩放 + 逐步降低 JPEG 质量直至 ≤ 1MB；统一转 JPEG（保留必要透明度时转 PNG，初期统一 JPEG）。
- **`app/integration/image_storage/`**：
  - `base.py`：`ImageStorageBackend` 抽象（`put(data, meta) -> StoredRef` / `get(ref) -> bytes`）。
  - `blob_backend.py`：MySQL BLOB 后端（二进制写入 `game_observation_image.blob_content`）。
  - 预留 `s3_backend.py` / `webdav_backend.py`（本期不实现，仅占位说明）。
  - 后端选择由 `settings.IMAGE_STORAGE_BACKEND`（默认 `mysql_blob`）决定。

## 7. 账号体系增强

### 7.1 自助注册
- 新增公开页 `/register`（加入中间件白名单 `UNRESTRICTED_PAGE_ROUTES`）。
- 表单：邀请码、用户名、密码、确认密码、显示名（可选）。
- 流程：校验邀请码有效 → 取得 `tenant_id` → 校验同租户用户名唯一 → Argon2 哈希 →
  创建 `role=teacher, is_active=False` 用户 → 提示「等待管理员审核」。
- 审核：复用账号管理页启用/停用（`is_active`）。新增「待审核」筛选（`is_active=False`）。

### 7.2 个人资料页
- 新增页 `/profile`（需登录）：展示用户名/角色（只读），可编辑 `display_name`，可修改密码（复用既有 `change_password`）。

### 7.3 邀请码管理
- 账号管理页 `/user-admin`（仅 `sys_admin`）新增「邀请码」区块：列表、生成（随机串）、启用/停用。

## 7.5 界面重构（共享布局外壳）

> 现状问题：各页面（settings/daily_plan/prompt_mgmt/user_admin/date_test）各自手写 `ui.header()` 与导航按钮，
> 重复 5 处；`/home` 为占位页；`/date-test` 为开发测试页应删除。整体是扁平路由，缺统一导航。

### 7.5.1 布局方案（已确认）
- **左侧边栏 + 右侧内容区**（后台管理常见布局）。
- 新增共享布局组件 `app/ui/components/app_shell.py`：
  - `with app_shell(user, active="daily_plan"):` 上下文管理器，渲染左侧 `ui.left_drawer` 菜单 + 顶栏（标题、当前用户显示名、退出），内部 `yield` 给页面填充内容区。
  - 菜单项按角色显示（管理员才显示账号管理/邀请码）。
  - `active` 参数高亮当前菜单。
- 所有业务页面改为 `with app_shell(...)` 包裹内容，删除各自的 `ui.header()` 重复代码。

### 7.5.2 侧边栏菜单分组（已确认）
| 分组 | 菜单项 | 路由 | 可见角色 |
|------|--------|------|---------|
| 教学管理 | 每日活动计划 | /daily-plan | 全部 |
| 教学管理 | 游戏观察记录 | /game-observation | 全部 |
| 配置中心 | 基础配置（学期/班级） | /settings | 全部 |
| 配置中心 | AI 模型配置 | /settings#ai 或同页区块 | 全部 |
| 配置中心 | 提示词管理 | /prompts | 全部 |
| 账号中心 | 个人资料 | /profile | 全部 |
| 账号中心 | 账号管理 | /user-admin | sys_admin |
| 账号中心 | 邀请码 | /user-admin#invite 或同页区块 | sys_admin |

> AI 模型配置与基础配置可同页分区块（settings），菜单可锚点跳转或拆分独立页，实现时二选一（推荐同页分区块，减少页面数）。

### 7.5.3 首页仪表盘（已确认）
- `/home` 重构为仪表盘：欢迎信息（显示名）+ 快捷入口卡片（每日活动计划 / 游戏观察记录）+ 当前班级信息（年级/班级，取自 class_config）。
- 删除"功能模块开发中"占位文案。

### 7.5.4 清理项
- 删除 `app/ui/pages/date_test.py` 及 `main.py` 的导入、`home.py` 中 `/date-test` 按钮。
- 删除各页面重复的 header 导航代码（迁移到 app_shell）。

### 7.5.5 执行顺序（已确认）
**先重构布局，后开发观察子系统**：先把现有页面迁到 app_shell（含清理 date-test 与首页仪表盘），全量回归通过后，再按阶段 A~I 开发游戏观察。观察页面从一开始就用新布局。

## 8. 路由与导航变更
| 路由 | 鉴权 | 变更 |
|------|------|------|
| `/home` | 登录 | 重构为仪表盘（欢迎+快捷卡片+班级信息） |
| `/date-test` | — | **删除**（开发测试页） |
| 共享布局 | — | 新增 `app/ui/components/app_shell.py`，所有业务页套用 |
| `/register` | 公开 | 新增（白名单） |
| `/profile` | 登录 | 新增 |
| `/game-observation` | 登录 | 新增 |
| `/prompts` | 登录 | 新增 game_observation Tab |
| `/settings` | 登录 | 新增视觉模型配置区块 |
| `/user-admin` | sys_admin | 新增邀请码管理 + 待审核筛选 |
| `/`（登录页） | 公开 | 新增「注册账号」入口 |

## 9. 安全与隔离
- 所有新查询强制 `tenant_id` 过滤；观察记录与图片均按 `(tenant_id, user_id)` 隔离。
- 视觉模型 API Key 与文本 Key 一样 Fernet 加密入库，脱敏展示，禁止写日志。
- 图片为隐私数据：仅本人/同租户可访问；下载/读取接口校验 `tenant_id`。
- 审计：`ai_observation`（视觉生成）、`export_observation`（导出）、`register`（注册）、`approve_user`、`invite_code_create` 接入 `log_audit`。
- 注册防滥用：邀请码停用即失效；可后续加频率限制（本期不做）。

## 10. 依赖变更
- 新增 `Pillow>=10.0.0`（图片压缩）。
- `requirements.txt` 追加并 `pip install`。

## 11. 验收标准
1. 教师上传 1~3 张图片 + 元数据，点击生成 → AI 返回 4 段内容并回填。
2. 导出 Word：标题大环境正确、各字段就位、图片在「观察记录」格文字下方横向并排、中文不乱码。
3. 观察记录（含图片）持久化，可在历史中查看并重新导出。
4. 图片入库前压缩到 ≤ 1MB。
5. 视觉模型独立配置可用；未配置时给出友好提示。
6. 注册：邀请码无效被拒；有效则创建待审核用户；管理员审核后可登录。
7. 个人资料页可改显示名，观察者默认取显示名。
8. 提示词管理可维护 game_observation 多版本并回滚。
