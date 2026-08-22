# Graph Report - /home/admin/code/KindergartenManager  (2026-08-22)

## Corpus Check
- 15 files · ~89,802 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2071 nodes · 4605 edges · 131 communities (117 shown, 14 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 217 edges (avg confidence: 0.74)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Listening Word Export
- Export Audit Persistence
- Listening AI Pipeline
- Prompt Version Management
- Project Governance Docs
- Authentication Service
- Listening Analysis Service
- Application Configuration
- Course Review Persistence
- Activity Generation AI
- Audit Logging Context
- Listening Record Persistence
- Read Only API Routes
- Text Difference Analysis
- Observation Word Export
- Game Observation Persistence
- Holiday Lookup Client
- Historical Architecture Docs
- Course Review History
- Alembic Runtime Database
- Default User Bootstrap
- Course Review Export
- Daily Plan Export
- Date Calculation Service
- Homemade Teaching History
- API Key Authentication
- Data Encryption
- Listening Indicator Catalog
- API Database Dependencies
- JWT Token Handling
- Vision AI Base Client
- User Repository
- Observation Image Persistence
- AI Key Persistence
- Listening Image Persistence
- Admin Bootstrap Job
- User Registration Flow
- Environment File Writer
- Text AI Base Client
- Observation Vision Client
- Daily Plan Export Internals
- Homemade Teaching Export
- Content Generation Services
- Game Observation UI
- Holiday Year Cache
- Blob Image Storage
- Image Storage Abstraction
- Activity Adaptation AI
- Setup State Marker
- Lesson Plan Parsing
- Application Shell Navigation
- Disabled Auth Middleware
- Password Security
- Runtime Path Management
- Encrypted AI Keys
- Agent Security and Persistence
- Agent Runtime Integration
- Course Review UI
- Class Configuration Persistence
- Listening Model Tests
- Startup Migration Flow
- Course Review AI Client
- Agent Architecture Decisions
- Semester Configuration
- Workday Sampling
- Activity Generation Service
- Date Picker Component
- Setup Configuration Page
- API Route Tests
- Listening Migration Tests
- Audit Action Tests
- Near Holiday Detection
- Semester Week Calculation
- Homemade Teaching UI
- Agent Roadmap and Status
- Settings Database Tests
- Database URL Migration
- Homemade Teaching AI
- Display Name Tests
- Special Day Tags
- Fixed User Context
- Homemade Teaching Service
- Image Settings Tests
- Domain Exception Constructors
- Word Field Parser
- AI Model Migration
- Invite Code Removal
- Course Review Migration
- Teacher Name Migration
- Homemade Teaching Migration
- Semester Config Migration
- Observation Prompt Migration
- Single User Entry
- Debian Build Script
- Debian Install Hook
- Debian Removal Hook
- Debian Pre Removal Hook
- Authentication Package
- Core Package
- Application Package
- AI Client Package
- Development Compose

## God Nodes (most connected - your core abstractions)
1. `AiParseError` - 54 edges
2. `Base` - 37 edges
3. `DailyPlan` - 37 edges
4. `log_audit()` - 35 edges
5. `ConfigError` - 35 edges
6. `get_active_ai_key()` - 35 edges
7. `AuthError` - 31 edges
8. `get_logger()` - 31 edges
9. `save_ai_key()` - 31 edges
10. `MockTransport` - 31 edges

## Surprising Connections (you probably didn't know these)
- `Controlled Agent boundary (planned, not implemented)` --conceptually_related_to--> `Four READ plus two DRAFT tools with zero persistence`  [INFERRED]
  AGENTS.md → docs/ADR/ADR-0005-controlled-ai-agent-runtime.md
- `test_expired_token_raises_auth_error()` --indirect_call--> `AuthError`  [INFERRED]
  tests/test_jwt.py → app/core/exceptions.py
- `test_tampered_signature_raises_auth_error()` --indirect_call--> `AuthError`  [INFERRED]
  tests/test_jwt.py → app/core/exceptions.py
- `test_wrong_secret_raises_auth_error()` --indirect_call--> `AuthError`  [INFERRED]
  tests/test_jwt.py → app/core/exceptions.py
- `test_generate_activity_content_no_ai_key_raises_config_error()` --indirect_call--> `ConfigError`  [INFERRED]
  tests/test_generate_service.py → app/core/exceptions.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Agent Foundation scope and application boundaries** — docs_adr_adr_0005_controlled_ai_agent_runtime_single_agent_provider_boundary, docs_adr_adr_0005_controlled_ai_agent_runtime_read_draft_zero_persistence, docs_design_agent_runtime_closed_registry_service_projection, docs_design_system_architecture_agent_layer_boundary, docs_roadmap_r4a_read_draft_scope [INFERRED 0.85]
- **Agent zero-persistence boundary and future WRITE gate** — docs_design_agent_runtime_short_context_planpatch, docs_design_data_model_agent_no_persistence, docs_security_threat_model_agent_stale_zero_write, docs_roadmap_r4b_write_independent, docs_design_data_model_agent_write_revision_gate [INFERRED 0.85]
- **计划中的服务拆分及其门禁** — memory_bank_implementation_plan_m6_service_split, memory_bank_overview_microservice_topology, services_readme_current_in_process, services_readme_split_gates [INFERRED 0.85]
- **Homemade teaching design, delivery, and verification** — memory_bank_homemadeteaching_design_generation_contract, memory_bank_homemadeteaching_dev_plan_phased_delivery, memory_bank_homemadeteaching_progress_completion_evidence, memory_bank_homemadeteaching_test_plan_test_matrix [INFERRED 0.85]
- **Listening design, implementation, and acceptance** — memory_bank_one_on_one_listening_design_five_domain_observation, memory_bank_one_on_one_listening_dev_plan_staged_delivery, memory_bank_one_on_one_listening_progress_manual_acceptance_pending, memory_bank_one_on_one_listening_test_plan_manual_acceptance [INFERRED 0.85]

## Communities (131 total, 14 thin omitted)

### Community 0 - "Listening Word Export"
Cohesion: 0.06
Nodes (63): _build_domain_doc(), _build_from_scratch(), _clear_cell(), _domain_of_title(), export_batch_by_domain(), export_combined(), export_split_by_domain(), _extract_block() (+55 more)

### Community 1 - "Export Audit Persistence"
Cohesion: 0.06
Nodes (56): CourseReviewActivity, 课程审议记录。      每条记录保存一次课程审议生成与教师编辑后的结果。班级、年龄段与教师姓名     采用冗余快照，避免后续系统设置变更影响历史导出。, create_course_review_activity(), delete_course_review_activity(), get_course_review_activity(), list_course_review_activities(), AsyncSession, 删除课程审议记录，强制 tenant_id + user_id 双重过滤。 (+48 more)

### Community 2 - "Listening AI Pipeline"
Cohesion: 0.08
Nodes (54): ListeningIndicatorResult, ListeningRecord, delete_domains_by_record(), delete_indicator_results_by_record(), delete_record(), get_record_by_id(), list_domains_by_record(), list_indicator_results() (+46 more)

### Community 3 - "Prompt Version Management"
Cohesion: 0.09
Nodes (34): _build_collective_cell(), export_batch_daily_plans(), export_daily_plan(), _export_from_scratch(), _fill_fields_cell(), _fill_plain_cell(), _fill_process_cell(), _fill_template() (+26 more)

### Community 4 - "Project Governance Docs"
Cohesion: 0.07
Nodes (47): ExportRecord, 导出记录数据模型。  对应数据库表：export_records 记录每次 Word 导出操作的元信息（文件名、路径、关联教案）。 导出记录为只增不改（immu, HomemadeTeachingToy, 教师自制教玩具记录。      每条记录保存一次 AI 生成或教师编辑后的教玩具方案。班级与教师姓名     采用冗余快照，避免后续设置变更影响历史导出。, AsyncSession, 写入一条导出记录。      Args:         session: 异步数据库会话（调用方负责事务管理）。         tenant_id: 机构, save_export_record(), create_homemade_teaching_toy() (+39 more)

### Community 5 - "Authentication Service"
Cohesion: 0.08
Nodes (35): AiApiKey, get_active_ai_key(), get_decrypted_key(), AsyncSession, ai_key_repository — AI API Key 数据访问层。  所有函数均携带 tenant_id + user_id 过滤，确保数据隔离。  安, 解密并返回明文 API Key。      Args:         ai_key: 由 `get_active_ai_key` 取得的模型对象。, 加密 API Key 后入库，同时将该用户同类型旧记录标记为 inactive。      Args:         session: 异步数据库会话。, 查询该用户当前激活的 AI Key 记录。      Args:         session: 异步数据库会话。         tenant_id: 租户 (+27 more)

### Community 6 - "Listening Analysis Service"
Cohesion: 0.10
Nodes (48): AuthError, 鉴权失败：token 无效、已过期、签名错误或用户名密码错误时抛出。          故意不区分"用户不存在"和"密码错误"，防止用户枚举攻击。, approve_user(), create_user_by_admin(), list_users_for_admin(), login(), AsyncSession, 审核通过：将指定用户的 is_active 设为 True。      Args:         session: 异步数据库会话。         tena (+40 more)

### Community 7 - "Application Configuration"
Cohesion: 0.07
Nodes (30): list_versions(), AsyncSession, 将指定版本设为激活，其余版本设为 inactive。      Args:         session: 异步数据库会话。         tenant_i, 返回指定任务类型的所有版本，按版本号降序排列。      Args:         session: 异步数据库会话。         tenant_id:, 保存新版本提示词，自动递增版本号并将旧激活记录设为 inactive。      Args:         session: 异步数据库会话。, rollback_to_version(), save_new_version(), _build_task_panel() (+22 more)

### Community 8 - "Course Review Persistence"
Cohesion: 0.07
Nodes (39): _build_prefix(), _build_user_content(), _holiday_hint(), 构建消息开头的班级与教学周信息。      context 支持 grade、class_name、week_number、weekday 字段；     we, 当 near_holiday 为 True 时返回临近节假日提示行，否则返回空字符串。      near_holiday 取值：True 表示明日为法定节假日, 根据任务类型和上下文构建发送给 AI 的用户消息。      context 支持以下字段：         grade, class_name, activi, _make_text_client(), AsyncClient (+31 more)

### Community 9 - "Activity Generation AI"
Cohesion: 0.12
Nodes (32): ApiPrincipal, get_daily_plan(), health(), date, query_classes(), query_daily_plans(), query_semesters(), 对外 REST API v1 路由（只读）。  所有业务端点强制经过 API Key 鉴权，并以鉴权得到的 tenant_id 作为查询隔离条件， 调用方无法越 (+24 more)

### Community 10 - "Audit Logging Context"
Cohesion: 0.11
Nodes (20): get_env_path(), Path, 运行时 .env 文件读写工具。  路径策略： - PyInstaller 打包模式：可执行文件同级目录 - 开发 / Docker 模式：当前工作目录  这与, 返回 .env 文件的绝对路径（位于用户可写数据目录）。, 解析 .env 文件，返回 key-value 字典。      忽略空行与 # 开头的注释行。文件不存在时返回空字典。, 将 updates 中的 key-value 原子写入 .env，保留其余行不动。      若 .env 不存在则自动创建。写入失败时抛出 RuntimeEr, read_dot_env(), write_dot_env() (+12 more)

### Community 11 - "Listening Record Persistence"
Cohesion: 0.11
Nodes (36): _add_images_to_cell(), _build_from_scratch(), _clear_cell(), export_observation(), _fill_template(), Document, Path, RGBColor (+28 more)

### Community 12 - "Read Only API Routes"
Cohesion: 0.12
Nodes (34): create_user(), get_user_by_id(), get_user_by_username(), has_any_user(), list_users_by_tenant(), AsyncSession, query_users_by_tenant(), 用户数据访问层。  所有查询必须携带 tenant_id 过滤条件，确保多租户数据隔离。 (+26 more)

### Community 13 - "Text Difference Analysis"
Cohesion: 0.10
Nodes (35): _auto_pick_workdays(), build_batch_export_filename(), build_export_filename(), default_year_month(), distribute_images_by_filename(), format_record_summary(), format_stage_label(), infer_age_by_grade() (+27 more)

### Community 14 - "Observation Word Export"
Cohesion: 0.09
Nodes (24): app_shell(), get_display_name(), get_menu_items(), 共享布局组件 app_shell。  提供统一的左侧导航菜单 + 顶栏，供所有页面复用。  纯函数（可在 NiceGUI 渲染外调用，支持单测）： - get_, 返回顶栏显示名：优先 display_name，回退 username。      Args:         user: 包含用户信息的字典，通常来自 dec, 统一布局：左侧分组菜单 + 顶栏。      用法::          async with app_shell(user, active="daily-pl, 渲染顶栏和左侧抽屉（无 context manager 版本）。      供已有页面调用：在页面函数开头调用一次，内容随后在同一层级放置。      Args, 根据角色返回可见菜单项列表，每项含 selected 标记。      Args:         role: 用户角色，如 'teacher' / 'teac (+16 more)

### Community 15 - "Game Observation Persistence"
Cohesion: 0.12
Nodes (18): get_holiday_name(), is_adjusted_workday(), 返回法定节假日名称，如"国庆节"、"春节"。      返回语义：     - str  ：该日期是法定节假日，返回节日名称（如"国庆节"）     - Non, 判断指定日期是否为调班工作日（节假日调休补班的周末）。      返回语义：     - True  ：调班工作日（API type == 3），周末需正常上班, make_response(), MockTransport, Request, Response (+10 more)

### Community 16 - "Holiday Lookup Client"
Cohesion: 0.12
Nodes (26): hash_password(), 将明文密码哈希为 Argon2 格式字符串。, verify_password(), bootstrap_admin(), _main(), _prompt_password(), _prompt_str(), 系统管理员初始化脚本。  模式：   --init           创建 sys_admin 账号（默认模式）   --reset-password 重置 (+18 more)

### Community 17 - "Historical Architecture Docs"
Cohesion: 0.11
Nodes (32): 课程审议 AI 结构化 JSON 合约, 课程审议记录子系统设计文档, 课程审议持久化与历史导出, 课程审议 Word 模板映射, 课程审议 AI 客户端与服务层, 课程审议记录子系统开发计划, 课程审议分阶段交付, 课程审议 Word 导出阶段 (+24 more)

### Community 18 - "Course Review History"
Cohesion: 0.12
Nodes (12): get_weekday_cn(), is_workday(), pick_three_workdays(), date, 日期计算服务 — 纯函数，无 IO，无数据库依赖。, 仅根据是否为周六/周日判断工作日（节假日由独立客户端判断，不耦合此处）。, 从指定年月的全部工作日中随机选取 3 个不同日期，按时间升序返回。      用于「一对一倾听」自动选取 3 个观察工作日（分布于全月，避免总是月初、1 号）。, Random (+4 more)

### Community 19 - "Alembic Runtime Database"
Cohesion: 0.11
Nodes (18): Base, _build_engine(), get_async_session(), AsyncSession, _resolve_database_url(), AiApiKey — AI 接口 Key 数据模型。  安全约束： - `api_key_encrypted` 字段仅存密文，明文禁止入库、禁止写入日志。 -, GameObservationImage — 游戏观察图片数据模型。  可插拔存储：本期实现 MySQL BLOB 后端（blob_content 存压缩后二进, GameObservation — 游戏观察记录数据模型。  每条记录对应教师的一次游戏观察，包含元数据（日期/环境/人员） 和 AI 生成的四段内容（观察目标 (+10 more)

### Community 20 - "Default User Bootstrap"
Cohesion: 0.18
Nodes (28): _build_from_scratch(), _clear_cell(), _clear_paragraph(), export_course_review_activity(), _fill_template(), _get_bool(), _get_value(), _iter_body_blocks() (+20 more)

### Community 21 - "Course Review Export"
Cohesion: 0.09
Nodes (26): Path, 应用配置：通过 pydantic-settings 从 .env 文件和环境变量加载。  首次部署（无 .env 文件）时的行为： - DATABASE_URL, 返回自动生成密钥的持久化文件路径（位于用户可写数据目录）。, 解析 key=value 文件，忽略空行与注释行。, 将新键值追加/覆盖到持久化文件（已有键保留）。, 自动生成缺失的密钥并持久化，保证重启后可还原。, _read_kv_file(), _secrets_file_path() (+18 more)

### Community 22 - "Daily Plan Export"
Cohesion: 0.12
Nodes (19): _build_fernet(), decrypt(), encrypt(), 应用层对称加密工具（Fernet）。  密钥来源：Settings.ENCRYPTION_KEY（原始字符串，UTF-8 编码后取前 32 字节， 再经 bas, 将环境变量中的原始字符串密钥转换为 Fernet 实例。      Fernet 要求 32 字节的 URL-safe base64 编码密钥（共 44 个字符, 加密明文字符串，返回 URL-safe base64 密文字符串。      Args:         plain_text: 待加密的明文（禁止在调用方写入, 解密密文字符串，还原为原始明文。      Args:         cipher_text: 由 `encrypt()` 生成的密文字符串。      Re, CryptoError (+11 more)

### Community 23 - "Date Calculation Service"
Cohesion: 0.11
Nodes (20): get_current_user(), 单用户模式：提供固定的默认用户上下文。  取消登录功能后，所有页面通过此模块获取当前用户信息， 而非从 JWT token 中解析。, 返回当前用户信息字典（单用户模式下始终返回默认管理员）。, daily_plan_page(), 每日活动计划页面（路由：/daily-plan）。  功能： 1. 顶部：日期选择面板（复用 DatePanel 组件） 2. 教案输入区块：粘贴完整教案 →, _mask_api_key(), 配置页面（路由：/settings）。  包含配置区块： 1. 学期配置：学期名称、开始日期、结束日期 2. 班级配置：年级、班级名称、区域内容、户外内容 3., 将明文 API Key 脱敏，仅保留末 4 位，其余替换为 sk-**** 前缀。 (+12 more)

### Community 24 - "Homemade Teaching History"
Cohesion: 0.12
Nodes (29): Homemade teaching toy design, Structured homemade-toy AI generation contract, Teacher/class snapshot and tenant-isolated persistence, Fixed homemade-teaching Word template mapping, Homemade teaching toy development plan, P0-P6 phased implementation plan, Test-first implementation and manual handoff, Homemade teaching completion evidence (+21 more)

### Community 25 - "API Key Authentication"
Cohesion: 0.11
Nodes (20): ABC, ImageStorageBackend, 存储图片字节，返回存储引用 dict。          Returns:             dict，键因后端而异（blob_backend 含 blo, 从存储引用还原图片字节。          Args:             stored: 与 put 返回格式相同的 dict。          Ret, 可插拔图片存储后端抽象。      put / get 与数据库 session 解耦：     - put 返回 stored_ref dict，由 repo, BlobImageStorage, MySQL BLOB 图片存储后端。  put/get 只操作内存 dict，实际 DB 写入由 repository 层完成。, MySQL BLOB 后端：图片二进制存入 game_observation_image.blob_content。 (+12 more)

### Community 26 - "Data Encryption"
Cohesion: 0.13
Nodes (13): _build_signing_string(), get_api_principal(), parse_api_keys(), Request, 对外 REST API 鉴权：API Key + 可选 HMAC 签名。  鉴权模型（服务间调用）： 1. **API Key**（必填）：调用方在 `X-Ap, 解析 `API_KEYS` 配置为 {api_key: tenant_id} 映射。      格式："key1:1,key2:2"；忽略空段与格式非法段（te, 校验 HMAC-SHA256 请求签名与时间戳新鲜度。, FastAPI 依赖：校验 API Key（必填）与签名（按配置可选），返回调用方主体。 (+5 more)

### Community 27 - "Listening Indicator Catalog"
Cohesion: 0.13
Nodes (26): AppError, 通用业务异常：输入非法、文件格式错误等非 AI / 非鉴权类业务错误。, _build_context_text(), _detect_mime(), generate_listening_domain(), _image_to_data_url(), 一对一倾听单领域生成 AI 客户端。  针对某一领域（健康/语言/社会/艺术/科学），输入该领域 3 张幼儿绘画照片 + 班级信息 + 该领域二级指标清单，一次, 调用视觉 AI 生成某领域的一对一倾听结构化内容。      Args:         images: 该领域绘画图片字节列表（经压缩后的 bytes，至少 (+18 more)

### Community 28 - "API Database Dependencies"
Cohesion: 0.13
Nodes (25): GameObservationImage, add_image(), delete_images_by_observation(), get_image(), list_images_by_observation(), AsyncSession, observation_image_repository — 游戏观察图片数据访问层。, 新增一张观察图片记录，返回带 id 的对象。 (+17 more)

### Community 29 - "JWT Token Handling"
Cohesion: 0.14
Nodes (25): IndicatorCatalog, IndicatorCatalog — 一对一倾听指标目录（参考数据，迁移预置）。  按 (grade, term, domain) 组织一级/二级指标及三档（★, get_indicator_by_id(), list_available_stages(), list_indicators(), list_indicators_by_ids(), AsyncSession, indicator_repository — 指标目录数据访问层。  只读参考数据查询（指标目录按 tenant_id + grade + term + dom (+17 more)

### Community 30 - "Vision AI Base Client"
Cohesion: 0.11
Nodes (25): CompressedImage, 图片压缩处理模块（游戏观察子系统）。  `compress_image` 将任意图片字节压缩至指定大小上限： - 超限时等比缩放 + 逐步降低 JPEG 质量直, load_record_detail(), 从 DB 装配整条记录详情（主表 + 各领域 + 图片 + 指标结果）。      指标的 sort_order 经 indicator_catalog 映射，, 将 load_record_detail 结果转为 exporter 入参 (record, domains)（纯函数）。      images → [(da, to_export_payload(), _ai_return(), P5 — 一对一倾听服务层测试。  覆盖：未配置视觉 Key、正常生成、指标缺失补默认 3 星、DB 提示词覆盖、整记录持久化。 (+17 more)

### Community 31 - "User Repository"
Cohesion: 0.15
Nodes (22): ConfigError, 业务配置缺失时抛出：如用户尚未配置 AI Key。, get_active_prompt(), prompt_repository — 提示词模板数据访问层。  支持提示词多版本管理：保存新版本、回滚、查询激活版本、列出所有版本。  约束： - 同一用户同, 查询该用户指定任务类型的当前激活提示词。      Args:         session: 异步数据库会话。         tenant_id: 租户, generate_course_review_activity_content(), AsyncSession, generate_homemade_teaching_content() (+14 more)

### Community 32 - "Observation Image Persistence"
Cohesion: 0.17
Nodes (14): get_logger(), 年龄适配 AI 客户端。  将活动过程原文按年龄段（小班/中班/大班）改写，返回改写后文本。  输出 Schema：     {"adapted_process, call_ai_text(), _make_retry_decorator(), AsyncClient, AI 客户端基础模块 — 通用 Chat Completions 调用。  所有 AI 调用必须通过此模块，禁止在 service 层直接发 HTTP 请求。, 发送 Chat Completions 请求，返回纯文本 content 字符串。      与 call_ai() 的区别：不强制 json_object 格, 构造 tenacity 重试装饰器：最多 3 次，指数退避 2s → 4s → 8s。 (+6 more)

### Community 33 - "AI Key Persistence"
Cohesion: 0.14
Nodes (24): GameObservation, delete_observation(), get_observation_by_id(), list_observations(), Any, AsyncSession, date, observation_repository — 游戏观察记录数据访问层。  所有查询强制携带 tenant_id 过滤，确保多租户数据隔离。 (+16 more)

### Community 34 - "Listening Image Persistence"
Cohesion: 0.13
Nodes (25): compress_image(), normalize_to_landscape(), 将图片统一为横版（宽 ≥ 高）。      处理步骤：       1. 按 EXIF 方向校正（手机照片常见）。       2. 透明通道转白底 RGB。, 将图片字节压缩至 max_bytes 以内。      Args:         data: 原始图片字节（JPEG / PNG / WebP 等 Pillo, _make_jpeg_bytes(), _make_large_jpeg_bytes(), _make_png_with_alpha(), Phase C — 图片处理单测。  测试 compress_image 纯函数：压缩大图、小图透传、异常输入处理。 所有测试用 Pillow 在内存中生成合成 (+17 more)

### Community 35 - "Admin Bootstrap Job"
Cohesion: 0.12
Nodes (9): get_db(), AsyncSession, 对外 REST API 的 FastAPI 依赖。, 提供独立的异步数据库会话（只读查询，无需提交）。      测试可通过 ``app.dependency_overrides[get_db]`` 注入内存库会话, 对外 REST API 路由集成测试（httpx ASGITransport + SQLite 内存库）。, _seed(), TestConfigEndpoints, TestDailyPlans (+1 more)

### Community 36 - "User Registration Flow"
Cohesion: 0.13
Nodes (23): AiCallError, Exception, AI 接口调用失败时抛出：HTTP 4xx/5xx、网络超时、超过重试次数等。, call_ai_vision(), _make_retry_decorator(), AsyncClient, AI 视觉客户端基础模块 — 多模态 Chat Completions 调用。  所有视觉 AI 调用必须通过此模块，禁止在 service 层直接发 HTTP, 构造 tenacity 重试装饰器：最多 3 次，指数退避 2s → 4s → 8s。 (+15 more)

### Community 37 - "Environment File Writer"
Cohesion: 0.14
Nodes (20): create_access_token(), decode_access_token(), JWT access token 生成与解码工具。, 生成 JWT access token。      payload 字段：     - sub: str(user_id)     - tenant_id: i, 解码并验证 JWT token，返回 payload 字典。      token 过期、签名无效等情况统一抛出 AuthError。, _get_current_user(), profile_page(), 个人资料页面（路由：/profile）。  功能：   - 查看并修改显示名（真实姓名）   - 修改密码 (+12 more)

### Community 38 - "Text AI Base Client"
Cohesion: 0.12
Nodes (19): app_data_dir(), Path, 跨平台可写数据目录解析。  打包（PyInstaller frozen）模式下，可执行文件常被安装到只读目录 （如 Windows 的 ``Program Fi, 返回应用可写数据目录，用于 SQLite、密钥、.env、状态标记等运行期文件。      - 打包模式：定位到操作系统的「用户数据目录」并确保其存在。, _get_state_path(), Path, 首次运行状态管理：通过标记文件判断系统是否已完成初始化配置。  标记文件路径： - PyInstaller 打包模式：可执行文件同级目录 .kindergart, 返回 setup 完成标记文件的路径（位于用户可写数据目录）。 (+11 more)

### Community 39 - "Observation Vision Client"
Cohesion: 0.13
Nodes (18): log_audit(), 审计日志：记录关键操作（登录、改密、AI 调用、Word 导出等）。  审计日志通过结构化 JSON logger 输出，统一携带 audit_action 与, 记录一条审计日志。      Args:         action: 操作标识（如 login_success / change_password / ai, generate_observation_content(), AsyncSession, 游戏观察服务层 — 生成与持久化。  职责：   - generate_observation_content：取 vision Key → 查提示词 → 压缩, 调用视觉 AI 生成游戏观察四段内容，返回结果 dict（含 compressed_images）。      Args:         session: 异, 游戏观察记录页面（路由：/game-observation）。  功能：   - 表单输入观察元数据（日期、大环境、游戏区域、人数、幼儿、观察者）   - 图片 (+10 more)

### Community 40 - "Daily Plan Export Internals"
Cohesion: 0.16
Nodes (19): LessonPlanResult, process_lesson_plan(), AsyncSession, 教案拆分与年龄适配的完整结果。      Attributes:         activity_goal: 活动目标（AI 拆分原文）。         a, 完整教案拆分与年龄适配流程。      Args:         session: 异步数据库会话（用于查询 AI Key）。         tenant_, _make_mock_ai_client(), _make_mock_ai_key(), AsyncClient (+11 more)

### Community 41 - "Homemade Teaching Export"
Cohesion: 0.18
Nodes (18): ListeningImage, ListeningImage — 一对一倾听绘画图片数据模型。  每个领域 3 张（共 15 张/记录）。复用游戏观察图片的可插拔 BLOB 存储， 新增 do, add_image(), delete_images_by_record(), get_image(), list_images_by_record(), AsyncSession, listening_image_repository — 一对一倾听图片数据访问层。 (+10 more)

### Community 42 - "Content Generation Services"
Cohesion: 0.14
Nodes (19): compute_diff(), 差异比对服务 — 使用 difflib 对原文与改写文进行逐句比对。  分句规则：以句号（。）、问号（？）、感叹号（！）、换行符为分隔符， 保留分隔符到句子末尾, 将文本按标点符号或换行符拆分为句子列表，过滤空串。, 对原文与改写文按句比对，返回带 changed 标记的句子列表。      Args:         original: 活动过程原文。         ad, _split_sentences(), tests/test_diff_service.py — 差异比对服务测试。, 完全相同的文本，所有句子 changed 为 False。, 修改一句后，该句 changed 为 True，其余句子不变。 (+11 more)

### Community 43 - "Game Observation UI"
Cohesion: 0.14
Nodes (19): _build_context_text(), _detect_mime(), generate_observation(), _image_to_data_url(), 将上下文 dict 转为给 AI 的说明文本。, 根据文件头检测图片 MIME 类型，无法识别时默认 image/jpeg。, 将图片字节转为 base64 data-url 字符串。, 调用视觉 AI 生成游戏观察记录四段内容。      Args:         images: 图片字节列表（1~3 张，经压缩后的 bytes）。 (+11 more)

### Community 44 - "Holiday Year Cache"
Cohesion: 0.24
Nodes (18): _build_from_scratch(), _clear_cell(), export_homemade_teaching(), _fill_template(), _get_value(), Any, Document, Path (+10 more)

### Community 45 - "Blob Image Storage"
Cohesion: 0.16
Nodes (18): call_ai(), 发送 Chat Completions 请求，返回解析后的 dict。      Args:         messages: 消息列表，格式为 [{"rol, _make_error_response(), _make_openai_response(), Response, tests/test_ai_client_base.py — AI 客户端基础模块测试。  使用 httpx.MockTransport 隔离真实 HTTP 请, HTTP 500 时重试后抛出 AiCallError。, HTTP 400 时抛出 AiCallError（不重试，因为是客户端错误）。 (+10 more)

### Community 46 - "Image Storage Abstraction"
Cohesion: 0.14
Nodes (13): APIRouter, create_api_router(), 对外只读 REST API（二期）。  通过 :func:`create_api_router` 暴露 ``/api/v1`` 路由，由 ``app/main., 返回组装好的对外 API 路由（当前仅 v1）。, run_bootstrap(), main(), _on_global_exception(), Exception (+5 more)

### Community 47 - "Activity Adaptation AI"
Cohesion: 0.21
Nodes (15): ensure_default_user(), AsyncSession, 应用启动引导：确保默认用户存在。  单用户模式下，系统启动时自动在 user 表中创建默认管理员账号。 如果已存在则跳过（幂等）。, 确保默认用户存在，不存在则创建。已存在则跳过。, User, UserRole, str, tests/test_single_user_bootstrap.py — 默认用户自动创建逻辑测试。  覆盖： - 数据库为空时自动创建默认用户 - 默认用户 (+7 more)

### Community 48 - "Setup State Marker"
Cohesion: 0.25
Nodes (16): AiParseError, AI 返回内容解析失败时抛出：JSON 格式非法、缺少必要字段等。, _build_user_content(), generate_course_review_activity(), generate_activity(), 生成单项一日活动内容（纯文本输出）。      Args:         task_type: 任务类型（morning_exercise / morning, _make_client(), AsyncClient (+8 more)

### Community 49 - "Lesson Plan Parsing"
Cohesion: 0.23
Nodes (9): is_setup_complete(), mark_setup_complete(), 检查系统是否已完成初始化配置（同步调用，纯文件检查，无 DB 查询）。, 写入 setup 完成标记文件。写入失败时静默忽略（不阻断正常流程）。, Path, 测试 app.core.setup_state 模块。  注意：setup_state 标记文件机制在单用户模式重构中已弃用。 这些测试保留以确保模块本身未被破, TestIsSetupComplete, TestMarkSetupComplete (+1 more)

### Community 50 - "Application Shell Navigation"
Cohesion: 0.21
Nodes (15): 将完整教案文本拆分为结构化字段。      Args:         raw_text: 用户粘贴的完整教案文本。         api_base_url:, split_lesson_plan(), _make_client(), AsyncClient, tests/test_lesson_plan_client.py — 教案拆分客户端测试。  使用 httpx.MockTransport 隔离真实 HTTP, AI 返回空 dict 时，抛出 AiParseError。, AI 返回额外字段时，只保留 5 个必要键。, 正常响应时，返回包含全部 5 个键的 dict。 (+7 more)

### Community 51 - "Disabled Auth Middleware"
Cohesion: 0.17
Nodes (15): build_export_filename(), 构造导出文件名。      格式：{tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx, 校验大环境值是否合法（仅允许 户外/室内/公共）。, 校验图片数量是否在合法范围（1~3 张）。, validate_big_env(), validate_image_count(), tests/test_observation_ui_helpers.py — 游戏观察 UI 工具函数测试。  测试覆盖（3 项纯函数）：   1. 导出文件名, 文件名格式为 {tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx。 (+7 more)

### Community 52 - "Password Security"
Cohesion: 0.17
Nodes (10): AuthMiddleware, Request, 路由守卫中间件（已禁用 — 单用户模式无需登录）。  保留模块以便后续恢复登录功能。当前为直通中间件，不做任何鉴权检查。 根路径 (/) 重定向到 /home。, 单用户模式：仅将根路径重定向到 /home，其余请求直接放行。, BaseHTTPMiddleware, tests/test_middleware.py — 单用户模式路由中间件测试。  验证： - 根路径 (/) 重定向到 /home - 其他路由直接放行，无认, 中间件可被实例化（接收 ASGI app 参数）。, test_middleware_instantiable() (+2 more)

### Community 53 - "Runtime Path Management"
Cohesion: 0.20
Nodes (6): get_special_day_tags(), 中国法定节假日客户端。  特性： - 查询指定日期是否为法定节假日（True / False / None） - 查询是否为法定节假日前一天（near_holi, 返回不放假节日标签列表（本地硬编码）。     空列表表示该日期无特殊节日标注。     返回值为副本，修改不影响内部数据。, 日期选择面板组件（可复用）。  功能： - 日期选择器（NiceGUI ui.date） - 选择日期后自动计算并显示：第几周、周几、是否工作日 - 节假日状态, Step 2.4 — 节假日客户端测试  使用自定义 httpx.AsyncBaseTransport 模拟 API，测试： - 正常响应的 bool 返回值（, TestGetSpecialDayTags

### Community 54 - "Encrypted AI Keys"
Cohesion: 0.19
Nodes (8): is_holiday(), 查询指定日期是否为法定节假日。      返回语义（固定）：     - True  ：法定节假日（API type == 2）     - False ：工作, 普通工作日（type=0）返回 False, 普通周末（type=1）返回 False（与法定节假日语义严格区分）, 调班工作日（type=3）返回 False, API 返回 5xx 时降级，返回 None, 同一日期第二次调用命中缓存，不发出 HTTP 请求, TestIsHoliday

### Community 55 - "Agent Security and Persistence"
Cohesion: 0.18
Nodes (15): Agent rejection and zero-change verification, Agent implementation rules: closed registry, no WRITE or persistence, Contributing guide, Four READ plus two DRAFT tools with zero persistence, Turn-scoped Context and discardable PlanPatch, AgentContext, ToolResult, and PlanPatch are memory-only; no Agent tables or migration, Future WRITE requires explicit daily_plan revision and minimal immutable audit, Data model design (+7 more)

### Community 56 - "Agent Runtime Integration"
Cohesion: 0.20
Nodes (14): Closed 4-READ/2-DRAFT tools and narrow Service projections, Controlled Agent boundary (planned, not implemented), Repository guidelines, Agent Foundation accepted design, absent from current code, Project context, Closed registry, narrow daily-plan Service projections, and non-executing Provider port, Agent Runtime design, Confirmed Agent Runtime contract, not implementation (+6 more)

### Community 57 - "Course Review UI"
Cohesion: 0.29
Nodes (11): ClassConfig, get_class_config(), list_class_configs(), AsyncSession, 查询当前用户的班级配置，若不存在返回 None。, 保存班级配置：若已存在则更新，否则新建。     每个用户只保留一条班级配置记录（最新）。, 按租户（可选用户）查询班级配置列表，按更新时间降序。, upsert_class_config() (+3 more)

### Community 58 - "Class Configuration Persistence"
Cohesion: 0.25
Nodes (13): adapt_activity_process(), 将活动过程按年龄段改写。      Args:         original: 活动过程原文。         grade: 年龄段，如"小班"、"中班"、, _make_client(), AsyncClient, tests/test_adapt_client.py — 年龄适配客户端测试。, AI 返回缺少 adapted_process 字段时，抛出 AiParseError。, 原文为空字符串时，不发请求直接抛出 AiParseError。, 传入自定义 system prompt 时，正常调用不报错。 (+5 more)

### Community 59 - "Listening Model Tests"
Cohesion: 0.21
Nodes (12): generate_activity_content(), AsyncSession, 一日活动内容生成服务。  编排 AI 调用与提示词版本查询，供 UI 层调用。 支持：晨间活动、晨间谈话、区域游戏、户外游戏、一日活动反思。, 生成单项活动内容。      Args:         session: 异步数据库会话（查询 AI Key 与自定义提示词）。         tenant, _make_mock_ai_key(), tests/test_generate_service.py — 一日活动生成服务测试。  使用 Mock 隔离 AI 调用、AI Key 仓库与提示词仓库。, 用户未配置 AI Key 时抛出 ConfigError。, 无自定义提示词时，使用内置默认（system_prompt=None）并返回生成文本。 (+4 more)

### Community 60 - "Startup Migration Flow"
Cohesion: 0.14
Nodes (14): _make_settings(), 自动生成的 ENCRYPTION_KEY 应能被 app.core.crypto 正常使用。, 在受控环境下构造 Settings 实例，不读取磁盘 .env 文件。, 无任何配置时，Settings() 应成功实例化（修复必填字段导致的启动崩溃）。, ENCRYPTION_KEY 为空时应自动生成非空值。, JWT_SECRET 为空时应自动生成非空值。, 已设置的 ENCRYPTION_KEY 不应被自动生成逻辑覆盖。, 首次生成的密钥写入持久化文件，第二次实例化时读回相同值。 (+6 more)

### Community 61 - "Course Review AI Client"
Cohesion: 0.17
Nodes (12): ListeningDomain, P1 — 一对一倾听数据模型冒烟测试（ORM + SQLite in-memory）。  用 async_session fixture（create_all）, IndicatorCatalog 可创建并保存三档标准。, ListeningRecord 可创建；adult_count 默认 1。, ListeningDomain 支持领域级年月与 3 个日期。, ListeningImage 存储 blob + domain + image_index + 描述。, ListeningIndicatorResult 不传 stars 时默认 3。, test_indicator_catalog_create() (+4 more)

### Community 62 - "Agent Architecture Decisions"
Cohesion: 0.23
Nodes (13): Existing AI adapter and teacher-adoption boundaries apply to future Agent, ADR-0004 AI and fixed Word boundaries, Existing one-shot AI functions cannot be exposed as arbitrary Agent Tools, ADR-0005 controlled AI Agent runtime, Future WRITE as an independent milestone, Single application-layer Agent and non-executing Provider boundary, Accepted ADR-0005 Agent registry entry, Agent Tool, permission, memory, or write changes require a new ADR (+5 more)

### Community 63 - "Semester Configuration"
Cohesion: 0.20
Nodes (9): _ensure_cache_fresh(), get_legal_holidays_in_year(), 一次性查询整年的法定节假日集合（单请求，避免逐日并发触发限流）。      用于「一对一倾听」批量选取工作日时排除节假日。复用 timor.tech 的「年」接, 若缓存日期不是今天，清空缓存（单日缓存 + 年节假日缓存）。, AsyncBaseTransport, 同年第二次查询命中缓存，不再发起 HTTP。, API 5xx → 返回 None（降级）。, 仅 holiday==True 计入；调班工作日（holiday==False）排除；单次请求。 (+1 more)

### Community 64 - "Workday Sampling"
Cohesion: 0.23
Nodes (7): DatePanel, 外部或内部直接设置日期值，触发联动更新（同步入口）。, 日期选择器选值回调（同步，启动异步联动）。, 日期选择面板，可嵌入任意 NiceGUI 页面。      参数：         semester_start: 学期开始日期，用于计算第几周；传 None, 渲染面板并返回外层 card 元素，可嵌入父容器。, card, date_type

### Community 65 - "Activity Generation Service"
Cohesion: 0.20
Nodes (12): API Key 租户绑定与隔离, 对外 REST API 集成说明, HMAC-SHA256 签名鉴权, 教学计划只读 REST API, M6 子系统拆分规划, 系统顶层总览, NiceGUI 主系统与功能地图, 历史渐进式微服务拓扑 (+4 more)

### Community 66 - "Date Picker Component"
Cohesion: 0.17
Nodes (9): migrated_db(), P1 — 一对一倾听迁移与种子集成测试。  在临时 sqlite 文件库上实际执行 `alembic upgrade head`，验证： - 5 个新表创建成功, export_records 含 listening_record_id 列。, 种子 JSON：5 领域共 30 个二级指标，每个含 3 档标准、sort_order 连续。, 在临时 sqlite 文件库上执行 alembic upgrade head，返回库路径。, 每条种子三档标准非空，tenant_id=1，max_stars=3。, test_export_records_has_listening_col(), test_indicator_seed_integrity() (+1 more)

### Community 67 - "Setup Configuration Page"
Cohesion: 0.31
Nodes (9): SemesterConfig, get_active_semester(), list_semesters(), AsyncSession, date, 查询当前用户的激活学期配置，若不存在返回 None。, 保存学期配置：若已存在激活记录则更新，否则新建。     同一用户只保留一条 is_active=True 的记录。, 按租户（可选用户）查询学期配置列表，按更新时间降序。 (+1 more)

### Community 68 - "API Route Tests"
Cohesion: 0.24
Nodes (7): is_near_holiday(), date, 判断 target_date 是否为法定节假日前一天。      返回语义：     - True  ：明天是法定节假日     - False ：明天不是法定, 法定节假日前一天（9月30日，10月1日为法定节假日）返回 True, 周五（普通周末前一天）返回 False，不视为 near_holiday, 普通工作日的前一天，次日也是工作日，返回 False, TestIsNearHoliday

### Community 69 - "Listening Migration Tests"
Cohesion: 0.25
Nodes (10): create_pending_user(), 创建待审核用户（is_active=False，role=teacher），用于自助注册流程。      Args:         session: 异步数据, update_display_name(), Phase D — user_repository display_name / create_pending_user 扩充测试。, 同 tenant 重复用户名创建 pending user 应抛出唯一性异常。, update_display_name 可将显示名更新为新值。, create_pending_user 创建的用户 is_active=False，role=teacher。, test_create_pending_user_duplicate_username_raises() (+2 more)

### Community 70 - "Audit Action Tests"
Cohesion: 0.18
Nodes (11): 自助注册：      - 若系统（tenant_id=1）尚无任何用户，注册者自动成为 sys_admin（is_active=True，可立即登录）。, register_user(), 空库第一个注册用户自动成为 sys_admin（is_active=True），可立即登录。, 已有用户后，第二个注册者成为 teacher（is_active=False），需管理员审核。, 同用户名注册两次时抛出 ValueError。, 注册时传入显示名，返回的用户对象应包含该显示名。, test_first_user_becomes_sys_admin_and_active(), test_register_duplicate_username_raises() (+3 more)

### Community 71 - "Near Holiday Detection"
Cohesion: 0.27
Nodes (5): get_week_number(), 返回 target_date 是开学后第几周（第 1 周起算）。      例：start_date=周一，target_date=同一天 → 第 1 周；, start_date 为周三时，目标日期在同一自然周内仍为第 1 周, 目标日期早于开学日，返回 ≤ 0（允许调用方自行处理，不抛异常）, TestGetWeekNumber

### Community 72 - "Semester Week Calculation"
Cohesion: 0.44
Nodes (8): _build_user_content(), generate_homemade_teaching(), _make_client(), AsyncClient, test_generate_homemade_teaching_filters_extra_keys(), test_generate_homemade_teaching_invalid_payload_raises(), test_generate_homemade_teaching_success(), test_generate_homemade_teaching_uses_custom_prompt()

### Community 73 - "Homemade Teaching UI"
Cohesion: 0.33
Nodes (3): is_within_semester(), 判断 target_date 是否在学期范围内（含首尾两天）。, TestIsWithinSemester

### Community 74 - "Agent Roadmap and Status"
Cohesion: 0.39
Nodes (8): Agent spec/Issue/RED and narrow Service projection gate, Product and engineering roadmap, R3 Agent Foundation specification and branch gate, R4A controlled Agent READ/DRAFT scope, R4B Agent WRITE independent future milestone, Planned daily-plan single Agent with four READ and two DRAFT tools, Unimplemented Agent WRITE, multi-agent, memory, and external tools, Project README

### Community 75 - "Settings Database Tests"
Cohesion: 0.33
Nodes (7): 分步实施计划, M7 恢复登录与多用户, 逐步完成与验证门禁, AI 拆分、年龄适配、Word 导出与存档, 首期每日活动计划闭环, 首期产品需求文档, 角色权限与数据安全

### Community 76 - "Database URL Migration"
Cohesion: 0.29
Nodes (7): AI、Word 与安全技术栈, Docker Compose 与 Caddy 部署, 技术栈选型文档, Python 单体技术路线, Python 依赖清单, 运行时与测试依赖, 依赖安全下限

### Community 77 - "Homemade Teaching AI"
Cohesion: 0.29
Nodes (5): 测试图片相关配置项（Phase A）。  验证新增的 IMAGE_STORAGE_BACKEND 和 IMAGE_MAX_BYTES 配置项存在且默认值正确，, IMAGE_MAX_BYTES 默认值为 1048576（1MB）。, IMAGE_STORAGE_BACKEND 默认值为 mysql_blob。, test_image_max_bytes_default(), test_image_storage_backend_default()

### Community 79 - "Display Name Tests"
Cohesion: 0.40
Nodes (4): Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online()

### Community 80 - "Special Day Tags"
Cohesion: 0.40
Nodes (4): downgrade(), Upgrade schema.      列 model_name 可能已存在（来自另一台机器的未提交迁移）。     若不存在则新增；若已存在则修改为 NOT, Downgrade schema: 恢复为可空、无默认值。, upgrade()

### Community 81 - "Fixed User Context"
Cohesion: 0.40
Nodes (4): downgrade(), 删除 invite_code 表（邀请码功能已移除）。, 重建 invite_code 表（回滚用）。, upgrade()

### Community 82 - "Homemade Teaching Service"
Cohesion: 0.80
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 84 - "Domain Exception Constructors"
Cohesion: 0.50
Nodes (4): Alembic-only schema changes, Database and ORM instructions, ADR-0003 SQLite MySQL Alembic, SQLite default and Alembic authority

### Community 85 - "Word Field Parser"
Cohesion: 0.83
Nodes (3): downgrade(), _has_column(), upgrade()

### Community 86 - "AI Model Migration"
Cohesion: 0.83
Nodes (3): downgrade(), _has_table(), upgrade()

### Community 87 - "Invite Code Removal"
Cohesion: 0.83
Nodes (3): downgrade(), _has_column(), upgrade()

### Community 89 - "Teacher Name Migration"
Cohesion: 0.50
Nodes (4): ADR-0002 single-user UI and tenant API, Single-user UI decision, REST API reference, Read-only REST API v1

### Community 90 - "Homemade Teaching Migration"
Cohesion: 0.50
Nodes (4): 项目进度记录, 历史进度证据不等于当前基线, 一对一倾听反馈修复与复测标签, 自制教玩具与课程审议交付记录

## Ambiguous Edges - Review These
- `历史渐进式微服务拓扑` → `当前能力仍在主应用进程内`  [AMBIGUOUS]
  services/README.md · relation: conceptually_related_to

## Knowledge Gaps
- **31 isolated node(s):** `build-deb.sh script`, `AI integration instructions`, `Database and ORM instructions`, `Word export instructions`, `Release build workflow` (+26 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `历史渐进式微服务拓扑` and `当前能力仍在主应用进程内`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `AiParseError` connect `Setup State Marker` to `Observation Image Persistence`, `Export Audit Persistence`, `User Registration Flow`, `Project Governance Docs`, `Observation Vision Client`, `Semester Week Calculation`, `Course Review Persistence`, `Daily Plan Export Internals`, `Game Observation UI`, `Blob Image Storage`, `Settings Key Management`, `Text Difference Analysis`, `Application Shell Navigation`, `Date Calculation Service`, `Class Configuration Persistence`, `Listening Indicator Catalog`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `get_logger()` connect `Observation Image Persistence` to `Listening Word Export`, `Export Audit Persistence`, `Prompt Version Management`, `User Registration Flow`, `Project Governance Docs`, `Environment File Writer`, `Observation Vision Client`, `Daily Plan Export Internals`, `Listening Model Tests`, `Listening Record Persistence`, `Holiday Year Cache`, `Text Difference Analysis`, `Image Storage Abstraction`, `Activity Adaptation AI`, `Default User Bootstrap`, `Runtime Path Management`, `Listening Indicator Catalog`, `User Repository`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `log_audit()` connect `Observation Vision Client` to `Export Audit Persistence`, `Listening AI Pipeline`, `Project Governance Docs`, `Audit Action Tests`, `Listening Analysis Service`, `Daily Plan Export Internals`, `Read Only API Routes`, `Text Difference Analysis`, `Holiday Lookup Client`, `Date Calculation Service`, `Listening Model Tests`, `User Repository`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `AiParseError` (e.g. with `test_adapt_empty_original_raises_parse_error()` and `test_adapt_missing_adapted_process_raises_parse_error()`) actually correct?**
  _`AiParseError` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Base` (e.g. with `AiApiKey` and `ClassConfig`) actually correct?**
  _`Base` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `DailyPlan` (e.g. with `ClassConfigOut` and `DailyPlanListOut`) actually correct?**
  _`DailyPlan` has 17 INFERRED edges - model-reasoned connections that need verification._