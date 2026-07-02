# dev4.0 线上系统重构计划

## 1. 决策与目标

### 1.1 已确认决策

- 交付形态：**线上唯一**。dev4.0 不再以 Windows 单机版、PyInstaller、Inno Setup、桌面本地 SQLite 为交付目标。
- 架构方式：先比对三种方案，默认执行**全栈重写**。移除 NiceGUI 前后端一体模式，前端、后端、后台任务、导出能力重新设计。
- AI 配置：**用户各自 Key**。每位用户独立配置 text / vision 模型地址、模型名与 API Key，继续支持 OpenAI 兼容接口。
- 角色体系：教师、年级组长、业务园长、园长、系统管理员。
- 数据安全：备份与恢复是 dev4.0 一级功能，备份目标必须支持 S3 兼容存储或 WebDAV。

### 1.2 目标用户规模

- 线上 50 人左右并发使用，主要用户为教师、年级组长、业务园长、园长、系统管理员。
- 系统必须支持多用户登录、个人数据隔离、用户级 AI Key、历史记录、图片上传、Word 导出与批量导出。
- 支持后续大量新增子系统。多数子系统属于同一类工作流：用户填表和上传资料 → 调 AI → 用户编辑结果 → 保存历史 → 导出 Word。

### 1.3 可量化结果

- 现有 5 个教学子系统功能全部保留：每日活动计划、游戏观察、一对一倾听、自制教玩具、课程审议。
- 首屏业务页面接口 P95 < 800ms，不含 AI 与导出任务。
- AI 与 Word 导出改为任务化执行，前端可查看进度和失败原因。
- 建立提示词优化系统：提示词版本、样例集、eval、对比、发布、回滚形成闭环。
- dev4.0 依赖扫描在发布门禁中无 Critical / High 漏洞；Medium 必须有说明或升级计划。
- 迁移后现有 dev3.4 数据可在 dev4.0 中查询、编辑、重新导出。
- Word 导出支持运行时选择样式配置：表头、标题、正文的字体、字号、段落间距、行距、对齐、页边距。

## 2. 架构比对与技术栈

### 2.1 三种架构比对

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| FastAPI + React/Vite 前后端分离 | 可最大复用现有 Python 业务代码、AI 客户端、Word 导出逻辑和 pytest 资产；迁移风险最低；前端摆脱 NiceGUI | 后端仍在 Python 生态，依赖治理要继续处理 FastAPI / Starlette / multipart 组合；未来若大量平台化表单和任务系统仍要重构后端模型 | 备选方案。适合先快迁 UI，但不满足本次“全栈重写”的决策 |
| Python 服务端渲染 | 技术栈最少；前端构建复杂度最低；适合简单后台页面 | 复杂表单、图片批量上传、任务进度、样式配置器、未来大量子系统会越来越难维护；交互体验容易回到 NiceGUI 类问题 | 不采用。它解决依赖面的一部分，但不解决长期扩展问题 |
| 全栈重写 | 可从数据模型、权限、任务、备份、模板样式、子系统 manifest 重新建平台；统一 TypeScript 合同；前端交互能力最好；依赖治理可重新建立 | 初期工作量最大；dev3.4 业务逻辑需要迁移和重测；数据迁移必须严格做 dry-run 和回归 | 采用。dev4.0 目标是线上长期系统，不是只替换 NiceGUI |

### 2.2 技术栈

- 语言：TypeScript。
- 前端：React + Vite，面向后台业务系统，不使用营销页结构。
- 后端 API：Node.js + Fastify。
- 数据库：MySQL 8，保留现有线上数据迁移路径。
- ORM / 迁移：Prisma。所有 schema 变更走迁移文件。
- 校验：Zod，前后端共享请求、响应与子系统 manifest schema。
- 鉴权：HTTP-only Session Cookie + CSRF Token；密码使用 Argon2id。
- 文件存储：S3 兼容存储或 WebDAV 为正式目标；本地持久卷只允许开发和应急恢复演练使用。
- 后台任务：MySQL job 表 + worker 进程，不引入 Redis。使用 MySQL 8 行锁领取任务。
- Word 导出：TypeScript OpenXML 导出引擎，基于模板包、字段映射和样式配置生成 `.docx`。
- 备份：MySQL 逻辑备份 + 文件存储清单 + 配置快照，自动上传到 S3 或 WebDAV。
- 部署：Docker Compose，Caddy 反向代理，MySQL，API，worker，frontend 静态资源。
- 测试：Vitest、Playwright、Prisma 测试库、OSV / npm audit / SBOM 门禁。

### 2.3 目录结构

```text
apps/
  web/                 React + Vite 前端
  api/                 Fastify API
  worker/              AI / Word / 批量任务 worker
packages/
  contracts/           Zod schema、DTO、枚举、错误码
  database/            Prisma schema、迁移、seed、测试 fixture
  auth/                密码、session、RBAC、CSRF
  ai/                  OpenAI 兼容 text / vision 客户端
  prompt/              提示词版本、优化、eval、发布、回滚
  document/            Word 模板、样式、OpenXML 导出引擎
  workflow/            子系统 manifest、表单、任务、记录装配
  storage/             本地文件 / S3 兼容存储接口
  backup/              备份、恢复、校验、S3/WebDAV 目标
  observability/       日志、审计、指标
legacy/
  python-dev3/         只读保留 dev3.4 迁移参考代码，不进入运行镜像
memory-bank/
  dev4.0-plan.md
```

### 2.4 依赖治理

- 新增 lockfile，CI 只允许 lockfile 安装。
- CI 生成 CycloneDX SBOM。
- CI 执行 OSV Scan、npm audit、容器镜像扫描。
- 发布门禁：Critical / High 漏洞直接失败；Medium 需在 `security/accepted-risks.md` 写明影响面、缓解和到期日。
- 当前 dev3.4 基线已确认：`pytest tests/ -q` 为 `543 passed`。该结果作为迁移功能基线。

## 3. 平台能力设计

### 3.1 用户、权限与 AI Key

- 角色固定为 5 类：
  - `teacher`：教师。
  - `grade_lead`：年级组长。
  - `academic_director`：业务园长。
  - `principal`：园长。
  - `sys_admin`：系统管理员。
- 角色采用多角色授权模型：一个用户可拥有多个角色；`grade_lead` 必须绑定可管理年级范围，如小班、中班、大班。
- 权限边界：
  - 教师：维护本人业务记录、个人 AI Key、个人资料、导出本人记录。
  - 年级组长：查看和导出本年级记录，可做业务批注，不管理系统配置。
  - 业务园长：查看全园教学业务记录，管理提示词、Word 模板和样式配置。
  - 园长：查看全园数据、统计、导出和审计摘要，不默认维护技术配置。
  - 系统管理员：账号、角色、系统配置、备份恢复、安全配置；默认不作为业务审核角色，需业务查看时叠加授权。
- 功能权限矩阵：
  - 个人业务记录创建、编辑、导出：`teacher` 及以上，数据范围默认本人。
  - 年级记录查看、批注、导出：`grade_lead`，数据范围限定绑定年级。
  - 全园业务记录查看、批注、导出：`academic_director`、`principal`。
  - 提示词优化、eval、发布、回滚：`academic_director`。
  - Word 模板、全局导出样式配置：`academic_director`。
  - 全园统计和审计摘要：`principal`、`academic_director`。
  - 用户、角色、年级范围配置：`sys_admin`。
  - 备份、恢复、系统安全配置：`sys_admin`。
  - 用户个人 AI Key：仅本人可维护；`sys_admin` 只能停用或清除，不可查看明文。
- 每个 workflow action 必须显式声明 `required_roles`、`scope` 和 `audit_action`，不能只靠前端隐藏按钮控制权限。
- 用户登录改为服务端 session，session 存数据库并支持强制下线。
- 用户自行配置两类 AI Key：
  - `text`：文本生成、教案拆分、课程审议、自制教玩具。
  - `vision`：游戏观察、一对一倾听。
- AI Key 用主密钥派生后 AES-256-GCM 加密，密文、nonce、key version 入库。
- 密钥轮换支持双读单写：新写入用最新 key version，旧密文在用户下次保存或后台任务中迁移。
- 明文 Key 永不写日志、审计、任务 payload 或错误消息。

### 3.2 子系统工作流平台

新增通用工作流模型，解决未来大量同构子系统扩展问题。

核心概念：

- `workflow_definition`：子系统定义，包含 slug、名称、版本、权限、表单 schema、AI 任务、导出模板。
- `workflow_record`：一次业务记录，包含 tenant、user、workflow slug、状态、表单输入、AI 输出、用户编辑结果、设置快照。
- `workflow_asset`：图片、Excel、附件等文件元数据。
- `workflow_job`：AI 生成、Word 导出、批量导出、Excel 解析等后台任务。
- `workflow_export`：导出记录，关联 record、模板、样式配置、文件路径、生成状态。

策略：

- 同构子系统优先用 workflow 平台定义，不再为每个子系统复制一套 UI、service、repository、exporter。
- 已有复杂子系统可有专用扩展表，但 API、任务、审计、导出记录仍接入统一 workflow。
- 每个子系统 manifest 必须包含：表单字段、AI 输入装配、AI 输出 schema、可编辑字段、导出字段映射、测试 fixture。

### 3.3 AI 调用

- `packages/ai` 提供统一 OpenAI 兼容客户端。
- 所有 AI 调用必须有：超时、重试、结构化输出校验、错误分类、脱敏日志。
- text / vision 共用任务表，任务状态为 `queued / running / succeeded / failed / canceled`。
- 失败结果写入可展示的中文错误，不暴露 API Key、完整请求头和隐私图片内容。
- 保存 AI 原始 JSON 的脱敏版本，用于问题追踪和 eval。

### 3.4 提示词优化系统

提示词优化系统独立于普通提示词编辑，不只是保存版本。目标是让业务园长能用固定样例证明新提示词更好，再发布到生产。

核心对象：

- `prompt_template`：提示词草稿、版本、适用 workflow、任务类型、状态。
- `prompt_dataset`：样例集，包含输入、期望结构、必填字段、规则断言。
- `prompt_eval_run`：一次评测运行，记录模型、用户 Key、样例、输出、评分、失败原因。
- `prompt_comparison`：候选版本和当前生产版本的对比报告。
- `prompt_release`：发布记录，支持一键回滚到上一生产版本。

能力要求：

- 支持按子系统和任务类型维护提示词，如教案拆分、年龄适配、游戏观察、一对一倾听。
- 支持从真实历史记录复制一份脱敏样例进入样例集。
- eval 至少检查 JSON 结构通过率、必填字段完整率、字数范围、禁 Markdown、可导出性。
- 新提示词发布前必须跑完指定样例集；未达到阈值不能发布，除非业务园长填写风险说明。
- 支持 champion / challenger：小流量试用候选提示词，失败自动退回生产版本。
- 所有提示词发布、回滚、风险放行都写审计。

权限：

- `teacher` 可查看当前生产提示词说明，但不能编辑。
- `grade_lead` 可提交提示词问题反馈和样例建议。
- `academic_director` 可创建、评测、发布和回滚提示词。
- `principal` 可查看提示词效果报告。
- `sys_admin` 只维护系统配置，不默认编辑业务提示词。

### 3.5 Word 模板与样式引擎

现有导出器硬编码模板路径、单元格坐标、宋体和字号。dev4.0 改为模板包。

模板包包含：

- 原始 `.docx` 模板。
- `mapping.json`：字段到段落、表格、单元格、重复块、图片区域的映射。
- `style-schema.json`：允许用户调整的样式项。
- `defaults.json`：每个模板默认样式。
- `fixtures/`：输入样例和期望文档断言。

样式配置项：

- 页面：纸张、页边距。
- 标题：字体、字号、加粗、居中、段前段后。
- 表头：字体、字号、加粗、背景色、水平/垂直对齐。
- 正文：字体、字号、行距、段前段后、首行缩进。
- 图片：最大宽高、对齐、间距。
- 差异文本：颜色、是否加粗。

导出行为：

- 用户导出时选择模板版本和样式配置。
- 业务园长可创建全局样式；教师可复制为个人样式。
- 样式修改不改变历史记录，只影响新导出。
- 导出的 docx 必须可被 Office / WPS / LibreOffice 打开。

### 3.6 文件与图片

- 图片和导出文件不再存 MySQL BLOB，迁移到文件存储。
- 数据库只保存文件元数据、hash、mime、大小、宽高、存储 key。
- 上传限制：
  - 图片默认单张 10MB，服务端压缩后用于 AI 和导出。
  - Word 模板只允许 `.docx`。
  - Excel 只允许 `.xlsx`。
- 所有文件名服务端生成，禁止使用用户上传文件名拼接路径。

### 3.7 Excel 与人脸识别预留

- Excel 作为 workflow asset 类型接入，第一期只做 `.xlsx` 解析和字段映射，不做宏文件。
- 人脸识别不进 dev4.0 首发功能，但预留 `vision_provider` 接口、图片资产权限、特征数据禁入普通业务表。
- 若后续做人脸识别，必须单独设计隐私、授权、删除和审计流程。

## 4. 现有子系统迁移

### 4.1 每日活动计划

保留能力：

- 教案拆分：活动目标、准备、重点、难点、过程。
- 年龄适配与差异标红。
- 晨间活动、晨间谈话、区域游戏、户外游戏、一日反思生成。
- 提示词版本管理。
- Word 导出和批量导出。

dev4.0 实现：

- 作为内置 workflow `daily_plan`。
- `plan_date`、周次、周几、节假日提示保留。
- 导出模板从 `templates/teacherplan.docx` 转为模板包。
- 差异计算迁移为 TypeScript 纯函数并保留回归样例。

### 4.2 游戏观察

保留能力：

- 1 到 3 张图片上传。
- 视觉模型生成观察目标、观察记录、评价分析、支持策略。
- 历史查询、重新导出。
- Word 中图片位于观察记录文字下方横向排列。

dev4.0 实现：

- 作为内置 workflow `game_observation`。
- 图片走统一文件存储和压缩管线。
- 视觉 AI 任务异步执行，页面轮询或 SSE 接收状态。
- 导出模板从 `ObservationRecord.docx` 转为模板包。

### 4.3 一对一倾听

保留能力：

- 单个幼儿、五大领域、每领域独立年月和 3 个工作日。
- 每领域 3 张绘画，五领域共 15 张。
- 视觉模型生成目标、图片描述、指标星级、综合评价、支持策略。
- 星级可编辑，未涉及指标默认 3 星。
- 合并导出、按领域导出、批量按领域导出。
- 指标目录按年级、学期、领域扩展。

dev4.0 实现：

- 作为专用 workflow `one_on_one_listening`，保留指标目录扩展表。
- 批量导出用后台任务生成 zip。
- 指标模板行序写入 `mapping.json`，不再散落在导出代码中。

### 4.4 自制教玩具

保留能力：

- 读取年级、班级、教师姓名。
- 文本 AI 生成教玩具名称、所用材料、玩法。
- 历史查询、重新导出、删除。
- Word 模板导出。

dev4.0 实现：

- 作为标准 workflow `homemade_teaching`。
- 该模块作为新增子系统模板样例，用于验证未来同构子系统的最低开发成本。

### 4.5 课程审议

保留能力：

- 读取年龄段、班级、教师姓名。
- 用户输入活动名称、幼儿人数、活动时间、原始教案。
- AI 拆分原稿并生成审议调整、二次修改稿。
- Word 导出时移除示例内容，字段落到正确位置。
- 历史重新导出和删除。

dev4.0 实现：

- 作为标准 workflow `course_review_activity`。
- AI 输出 schema 保留布尔校验和活动过程必须调整规则。

## 5. 数据迁移

### 5.1 迁移原则

- dev3.4 数据库只读抽取，不在原库上做破坏性迁移。
- 迁移脚本支持 dry-run、快照、校验、回滚。
- 每张旧业务表迁移到新模型后生成计数和抽样比对报告。
- 导出文件与图片迁移到文件存储，并记录 hash。

### 5.2 迁移映射

- `users` → `users`、`sessions` 初始化为空。
- 旧角色迁移：
  - `teacher` → `teacher`。
  - `teaching_admin` → 默认迁为 `academic_director`，迁移报告列出名单，由系统管理员上线前人工确认是否改为 `grade_lead` 并补年级范围。
  - `sys_admin` → `sys_admin`。
- `ai_api_key` → `ai_credentials`，保留 `key_type`、base url、model、active 状态。
- `prompt_template` → `prompt_templates`，保留 task type、版本、active 状态。
- `daily_plan` → `workflow_record(daily_plan)`。
- `game_observation` + `game_observation_image` → `workflow_record(game_observation)` + `workflow_asset`。
- `listening_*` + `indicator_catalog` → `workflow_record(one_on_one_listening)` + 专用指标表 + `workflow_asset`。
- `homemade_teaching_toy` → `workflow_record(homemade_teaching)`。
- `course_review_activity` → `workflow_record(course_review_activity)`。
- `export_records` → `workflow_export`。

### 5.3 验收

- 迁移后每类记录数量与 dev3.4 一致。
- 用户角色迁移报告必须列出旧角色、新角色、是否需要人工确认、年级组长范围是否已配置。
- 每类记录抽样 20 条进行字段级比对；不足 20 条则全量比对。
- 每个模板至少抽样 3 份重新导出并验证 docx 可打开。
- 图片文件 hash、mime、大小与迁移报告一致。

## 6. 安全、备份、审计与运维

### 6.1 Web 安全

- 所有写操作要求 CSRF Token。
- Cookie 设置 `HttpOnly`、`Secure`、`SameSite=Lax`。
- 统一请求体大小限制，上传走专用 endpoint。
- 所有富文本、Markdown、模板变量默认按纯文本处理。
- 所有下载 endpoint 校验 tenant、user、role。
- 路径、文件名、模板名只使用服务端 id，不使用用户原始输入拼路径。

### 6.2 审计

保留并扩展审计动作：

- 登录、退出、改密、用户启停、管理员重置密码。
- AI 生成、AI 失败、Word 导出、批量导出。
- AI Key 创建、替换、停用。
- 模板上传、样式创建、样式修改。
- 备份任务创建、开始、完成、失败、恢复演练、真实恢复。
- 数据迁移任务开始、完成、失败。

### 6.3 观测

- API 结构化 JSON 日志。
- 请求 id 贯穿 API、worker、导出任务。
- 指标：请求延迟、AI 成功率、AI 失败分类、导出耗时、任务队列长度、文件存储错误。
- 健康检查：
  - `/health/live`
  - `/health/ready`
  - `/health/dependencies`

### 6.4 备份与恢复

数据安全优先级高于功能扩展。dev4.0 必须内置备份、校验和恢复演练。

备份目标：

- 支持 S3 兼容存储：AWS S3、MinIO、阿里云 OSS S3 兼容层等。
- 支持 WebDAV：群晖、坚果云、自建 WebDAV 等。
- 生产环境必须至少配置一个远端备份目标；允许同时配置 S3 和 WebDAV 双写。
- S3 目标优先开启 bucket versioning / object lock；WebDAV 目标使用按日期分目录的只追加写入策略，禁止覆盖同名备份。

备份内容：

- MySQL 逻辑备份：schema、业务数据、用户、权限、AI Key 密文、审计表。
- 文件资产：上传图片、Word 模板、导出文档、Excel 附件。
- 配置快照：非密钥运行配置、模板包版本、样式配置、workflow definition。
- 密钥材料不直接写入普通备份包；主密钥以单独的加密密钥备份文件保存，并要求系统管理员离线保管恢复口令。

备份策略：

- 每日全量备份，保留 30 天。
- 每 6 小时增量备份文件资产清单和新增对象，保留 14 天。
- 每次正式发布和数据迁移前自动创建一次发布前快照。
- 所有备份包生成 SHA-256 校验文件和 manifest。
- 备份包上传前进行应用层加密，恢复时必须提供恢复口令或密钥文件。
- 备份上传失败必须在系统管理员首页显示红色告警，并写审计。

恢复策略：

- 提供只读恢复演练命令：拉取指定备份到临时库和临时文件目录，校验记录数、文件 hash、模板包 hash。
- 提供真实恢复命令，执行前必须要求二次确认并自动生成当前状态快照。
- 每月自动运行一次恢复演练任务，只验证到临时环境，不覆盖生产。

验收标准：

- 任意一天全量备份可恢复出完整 MySQL 数据、文件资产、模板与样式。
- 抽样恢复 20 条业务记录，图片和导出文件 hash 与备份 manifest 一致。
- 备份目标断网、认证失败、空间不足均能产生明确告警。

### 6.5 部署

Docker Compose 服务：

- `caddy`
- `web`
- `api`
- `worker`
- `backup-worker`
- `mysql`

生产配置：

- `.env.production` 不入库。
- 必须配置 S3 或 WebDAV 备份目标。
- MySQL 每日全量备份。
- 文件资产每 6 小时增量备份。
- 每月恢复演练。
- 发布前执行迁移 dry-run 和依赖扫描。

## 7. 实施阶段

### P0：基线与技术验证

阶段文档：

- [P0 开发计划](dev4.0/p0-dev-plan.md)
- [P0 测试计划](dev4.0/p0-test-plan.md)

执行规则：

- 每个 P 阶段开始前必须先补齐对应开发计划、测试计划和 gate tests。
- 阶段实现提交必须引用对应计划条目和测试命令。

- 创建 dev4.0 monorepo 结构。
- 建立 TypeScript、lint、format、test、lockfile、CI。
- 建立安全扫描和 SBOM。
- 完成 Word 技术验证：读取一个现有模板、写入中文、图片、表格、样式配置，生成可打开 docx。
- 完成 MySQL job 表领取任务验证。
- 完成 S3 和 WebDAV 备份目标连接验证。

验收：

- CI 可运行。
- 安全扫描接入。
- Word spike 输出样例文档并通过打开校验。
- S3 / WebDAV 至少一个目标可上传、下载、校验 hash。

### P1：基础平台

- 用户、角色、session、CSRF、RBAC。
- 用户 AI Key 配置，text / vision 分离。
- 文件存储、上传、下载、图片压缩。
- 备份配置、手动备份、备份状态页。
- workflow definition / record / job / export 基础表。
- 审计日志。

验收：

- 用户可登录、配置 AI Key、上传图片、触发测试任务。
- API 权限与 tenant/user 隔离测试通过。
- 系统管理员可配置 S3 或 WebDAV 并成功执行一次手动备份。

### P2：AI、任务与提示词优化系统

- text / vision AI 客户端。
- 结构化输出校验。
- 后台 worker。
- 任务进度 API。
- 失败重试、取消、错误展示。
- 提示词样例集、eval run、版本对比、发布、回滚。

验收：

- Mock AI 和真实测试 Key 两条通道可运行。
- 常见错误有中文提示。
- 业务园长可用样例集评测候选提示词，达标后发布，失败时回滚。

### P3：Word 模板与样式系统

- 模板包导入。
- 样式配置 UI。
- 导出任务。
- docx 打开校验。
- 批量 zip 导出。

验收：

- 标题、表头、正文、段落、行距可在导出时切换。
- 每个模板有 fixture 和导出测试。

### P4：迁移每日活动计划与提示词

- `daily_plan` workflow。
- 教案拆分、年龄适配、活动生成。
- 差异标红。
- 单份与批量导出。
- 提示词版本管理。
- 接入提示词优化系统的样例集、eval 和发布流程。

验收：

- dev3.4 每日活动主流程功能对齐。
- 旧数据迁移后可重新导出。

### P5：迁移游戏观察和一对一倾听

- `game_observation` workflow。
- `one_on_one_listening` workflow。
- 指标目录迁移。
- 图片资产迁移。
- 三种倾听导出模式。

验收：

- 视觉 AI 生成、图片预览、历史查询、批量导出均通过。

### P6：迁移自制教玩具和课程审议

- `homemade_teaching` workflow。
- `course_review_activity` workflow。
- 历史、删除、重新导出。
- 两套模板包。

验收：

- 两个子系统可作为新增 workflow 样板。

### P7：线上试运行

- 线上备份目标配置和恢复演练。
- dev3.4 数据迁移 dry-run。
- 真实数据预发布环境导入。
- 50 用户容量压测。
- 管理员手动验收。
- 正式迁移与发布。

验收：

- 迁移报告通过。
- 备份和恢复演练报告通过。
- 线上关键路径通过。
- 发布门禁通过。

## 8. 测试与 eval

### 8.1 Gate tests

- contracts schema 测试。
- auth、RBAC、CSRF、session 测试。
- workflow record CRUD 与隔离测试。
- AI 客户端 mock 测试。
- 提示词优化系统的样例集、eval 阈值、发布、回滚、风险放行权限测试。
- Word 模板 fixture 测试。
- 文件上传与路径安全测试。
- 数据迁移 dry-run 测试。
- S3 / WebDAV 备份上传、下载、hash 校验、失败告警测试。
- 恢复演练测试。

### 8.2 E2E

Playwright 覆盖：

- 登录、用户 AI Key 配置。
- 业务园长运行提示词 eval、发布候选提示词、回滚生产提示词。
- 每个子系统的创建、AI 生成、编辑、保存、导出、历史重导。
- 一对一倾听批量按领域导出。
- 管理员用户管理。
- 系统管理员备份配置、手动备份、查看备份告警。
- 样式配置切换导出。

### 8.3 Periodic evals

- 每个 AI workflow 保留 5 到 10 个固定输入样例。
- 使用用户配置的测试 Key 或预发布测试 Key 生成结果。
- 评估项：JSON 结构通过率、必填字段完整率、字数范围、禁 Markdown、模板字段可导出。
- 提示词优化系统的发布阈值默认要求结构通过率 100%、必填字段完整率 100%、可导出性 100%。
- eval 不以主观好坏为唯一标准，先保证结构和业务规则稳定。

## 9. 清理与归档策略

dev4.0 是重构，但旧系统不能在计划阶段直接清空。dev3.4 的代码、模板、迁移、测试和 memory-bank 文档是迁移依据、功能对照和回归基线。

立即清理：

- Office / WPS / LibreOffice 临时锁文件，如 `.~lock.*#`。
- Python 缓存、测试缓存、构建产物、导出产物、运行期 session 状态。
- 明确误提交的本机环境文件和日志文件。

暂时保留：

- `app/`、`alembic/`、`templates/`、`tests/`、旧 `memory-bank/` 子系统文档。
- PyInstaller、Windows installer、Docker 等旧交付文件，直到 dev4.0 对应部署流水线完成并通过发布演练。
- dev3.4 迁移脚本和数据库模型，直到 dev4.0 数据迁移 dry-run 与正式迁移均通过。

删除条件：

- 某个旧子系统只有在 dev4.0 对应 workflow 完成、旧数据迁移通过、Playwright 主流程通过、Word 导出 fixture 通过后，才能从运行路径移除。
- 删除旧代码前必须保留可追溯归档：迁移说明、字段映射、测试证据、旧模板 hash。
- 删除提交必须独立，不与新功能混在同一提交，方便回滚。

归档方式：

- dev4.0 新实现完成前，旧代码继续留在当前路径作为参考。
- dev4.0 新实现完成后，必要的旧代码复制到 `legacy/python-dev3/` 只读归档；运行镜像和新测试不依赖该目录。
- 旧文档不批量删除，合并为迁移附录后再逐步移除重复内容。

## 10. 不做事项

- dev4.0 不交付 Windows 单机版。
- dev4.0 不继续维护 NiceGUI 页面。
- dev4.0 不把图片继续存为 MySQL BLOB。
- dev4.0 首发不做人脸识别。
- dev4.0 不引入 Kubernetes。
- dev4.0 不做邮箱/短信找回密码，仍由管理员重置。
- dev4.0 不允许生产环境只依赖服务器本地磁盘备份。

## 11. 当前证据

- 当前重构分支：`dev4.0`。
- 当前旧系统自动化测试基线：`.venv/bin/pytest tests/ -q` 为 `547 passed`。
- P0 scaffold 已推送：`dae8ced chore: scaffold dev4 monorepo`。
- Word export spike 已推送：`73e1955 feat: add dev4 word export spike`。
- Backup target spike 已推送：`b7f25d5 feat: add dev4 backup target spike`。
- MySQL job spike 已推送：`6f1eb7f feat: add dev4 workflow job spike`。
- Storage upload spike 已完成完整验证：PNG/JPEG/DOCX/XLSX 上传校验、hash 元数据、tenant-scoped 对象 key、禁止用户文件名拼路径。
- 当前 `services/` 只有 README，没有已拆出的微服务。
- 当前运行依赖实际解析包含 `nicegui==3.12.0`。
- 当前 OSV 命中漏洞的包包括 `starlette==1.0.0`、`aiohttp==3.13.5`、`python-multipart==0.0.28`、`cryptography==48.0.0`。
