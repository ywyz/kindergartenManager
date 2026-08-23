# Graph Report - KindergartenManager  (2026-08-23)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2264 nodes · 4534 edges · 181 communities (137 shown, 44 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 210 edges (avg confidence: 0.77)
- Token cost: 13,338 input · 8,447 output

## Graph Freshness
- Built from commit: `1a72c2d4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AI Key Management
- Listening Record Export
- Observation Image Management
- Homemade Teaching Toy
- Date Calculation Service
- Authentication Service
- Codebase Graph Query
- Listening Record Repository
- Application Bootstrap
- External REST API
- Environment Config Management
- AI Message Builder
- Observation Word Export
- Audit and AI Client
- Record Detail Loader
- Export Filename Builder
- Semester Configuration
- App Startup Migration
- Export Record Model
- Config Secrets Test
- Database Migration
- External API Auth
- Symmetric Encryption
- AI Vision Call
- Listening AI Client
- Daily Plan Word Export
- Image Storage Backend
- Indicator Catalog
- Unit of Work Pattern
- App Entry and Migration
- REST API Tests
- Data Model Smoke Test
- Image Processing
- UI Menu Display
- AI Text Call
- Listening Image Repository
- JWT Token Management
- Batch Plan Export
- Game Observation Models
- Admin Bootstrap
- Diff Comparison Service
- API Response Schemas
- Listening Data Models
- Observation Generation Client
- Homemade Teaching Export
- User Repository Test
- Documentation and ADRs
- Setup State Management
- Daily Plan Repository
- Course Review Subsystem
- System Architecture Components
- Course Review Models
- Listening and Observation Design
- User Context and UI
- Holiday Check Client
- Route Guard Middleware
- Activity Generation Service
- Lesson Plan Splitter
- Prompt Version Manager
- Age Adaptation Client
- Legal Holiday Client
- Observation Export Helpers
- Password Hashing
- Audit Log Test
- Adjusted Workday Check
- Activity Content Generation
- Date Selection Panel
- Listening Migration Test
- Course Review Generation
- Special Day Tags
- Near Holiday Check
- User Registration
- Prompt Repository Test
- Version Listing
- Course Review Service Test
- Legacy Setup Page
- Agent Runtime Tools
- Prompt Template Model
- Security Audit
- Game Observation Design
- Image Config Test
- AI Return Parser
- UI Helper Functions
- Prompt Edit Panel
- Dependency Upgrades
- Listening Generation Test
- Database Migration Script
- Drop Invite Code Migration
- Add Course Review Migration
- Observation Image Model
- Homemade Teaching Test Plan
- Test Fixture Setup
- Python Runtime Test
- Add Teacher Name Migration
- Add Homemade Teaching Migration
- Add Teaching ID Migration
- Expand Task Type Migration
- Database Migration Script
- Database Migration Script
- Database Migration Script
- Application Layers
- Feature Development Phases
- AI and Product Features
- Registry Boundary Tests
- Public Contract Tests
- Dependency Security Tests
- Release Build Workflow
- Contributing guide
- ADR-0004 AI and fixed Word boundaries
- ADR index
- Future Microservice Decomposition
- 一日活动提示词与一键生成
- Homemade Teaching Design Document
- .handle_async_request
- AgentRuntime - Controlled AI Agent Runtime
- AI client integration boundary
- Alembic-only schema changes
- Word export instructions
- Production Docker Compose
- ADR-0001 modular monolith baseline
- build-deb.sh
- postinst
- postrm
- prerm
- Alembic - Database Migration Tool
- Caddy - Web Server
- Docker - Containerization Platform
- MySQL - Database Engine
- SQLite - Database Engine
- Tenant - Multi-tenant Isolation Concept
- codebase-memory skill
- Entry Points
- Risk Labels
- AsyncSession
- Any
- RGBColor
- Exception
- Agent Foundation Concept
- KindergartenManager Project
- Development Compose override
- docs/DEPENDENCIES.md - Python Dependency Security Baseline
- docs/USER_MANUAL.md - User Manual
- Quality CI Workflow
- ImageStorageBackend
- Test Stage P3
- Test Stage P4
- Test Stage P5
- 课程审议手动流程验收
- 一日活动教案处理流水线
- Homemade Teaching Development Plan
- python-docx - Word Document Library
- Response
- AsyncClient

## God Nodes (most connected - your core abstractions)
1. `AiParseError` - 43 edges
2. `Base` - 37 edges
3. `MockTransport` - 31 edges
4. `AuthError` - 30 edges
5. `get_active_ai_key()` - 27 edges
6. `save_ai_key()` - 27 edges
7. `log_audit()` - 27 edges
8. `make_response()` - 25 edges
9. `get_logger()` - 23 edges
10. `User` - 23 edges

## Surprising Connections (you probably didn't know these)
- `_seed_catalog_multi()` --calls--> `IndicatorCatalog`  [INFERRED]
  tests/test_listening_service.py → app/core/models/indicator_catalog.py
- `_seed_catalog_multi()` --calls--> `list_indicators()`  [INFERRED]
  tests/test_listening_service.py → app/repository/indicator_repository.py
- `test_save_observation_with_images()` --calls--> `BlobImageStorage`  [INFERRED]
  tests/test_observation_service.py → app/integration/image_storage/blob_backend.py
- `test_ai_key_default_key_type()` --calls--> `AiApiKey`  [INFERRED]
  tests/test_migrations_smoke.py → app/core/models/ai_key.py
- `test_ai_key_vision_type()` --calls--> `AiApiKey`  [INFERRED]
  tests/test_migrations_smoke.py → app/core/models/ai_key.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Course Review Activity Documentation Set** — memory-bank_coursereviewactivity_design, memory-bank_coursereviewactivity_dev-plan, memory-bank_coursereviewactivity_progress, memory-bank_coursereviewactivity_test-plan [EXTRACTED 0.75]
- **Daily Plan Documentation Set** — memory-bank_daily-plan_design, memory-bank_daily-plan_progress [EXTRACTED 0.75]
- **System Architecture Components** — kindergarten_manager_system, nicegui_framework, ai_integration_layer, word_export_system, database_layer, authentication_system [EXTRACTED 0.75]
- **Current vs Future Service Architecture** — services_readme, integration_app, future_microservice [EXTRACTED 0.85]
- **Tested Layers of One-on-One Listening Subsystem** — tests_test_migrations_smoke, tests_test_indicator_repository, tests_test_listening_repository, tests_test_listening_image_repository, tests_test_date_service, tests_test_listening_client, tests_test_listening_service, tests_test_listening_exporter, tests_test_listening_ui_helpers, tests_test_export_repository, tests_test_image_processing [EXTRACTED 0.90]
- **Development Phases Covered by Listening Test Plan** — phase_p1, phase_p2, phase_p3, phase_p4, phase_p5, phase_p6, phase_p7, phase_p8a, phase_p8b, phase_p8d [EXTRACTED 0.95]
- **Architecture Decision Records** — docs_ADR_ADR-0002-single-user-ui-and-tenant-api, docs_ADR_ADR-0005-controlled-ai-agent-runtime [EXTRACTED 1.00]
- **Agent Foundation Tool Set** — specs_agent_foundation_spec_tool_registry, specs_agent_foundation_spec_daily_plan_read_current, specs_agent_foundation_spec_daily_plan_read_context, specs_agent_foundation_spec_calendar_read_evaluation, specs_agent_foundation_spec_settings_read_class_areas, specs_agent_foundation_spec_daily_plan_draft_section_patch, specs_agent_foundation_spec_daily_plan_draft_reflection_patch [EXTRACTED 1.00]
- **Graphify Extraction Pipeline** — agents_skills_graphify_skill_md_ast_extraction, agents_skills_graphify_skill_md_semantic_extraction, agents_skills_graphify_skill_md_gemini_backend, agents_skills_graphify_skill_md_community_detection, agents_skills_graphify_skill_md_graph_json, agents_skills_graphify_skill_md_graph_report [EXTRACTED 1.00]
- **Graphify Reference Documentation** — agents_skills_graphify_references_extraction_spec_md, agents_skills_graphify_references_query_md, agents_skills_graphify_references_update_md, agents_skills_graphify_references_exports_md, agents_skills_graphify_references_add_watch_md, agents_skills_graphify_references_github_and_merge_md, agents_skills_graphify_references_hooks_md, agents_skills_graphify_references_transcribe_md [EXTRACTED 1.00]
- **Memory Bank Historical Documents** — memory-bank_api-integration, memory-bank_architecture, memory-bank_implementation-plan, memory-bank_overview [EXTRACTED 1.00]
- **Design Documents for KindergartenManager** — docs_design_agent-runtime, docs_design_data_model, docs_design_system_architecture [INFERRED 0.75]
- **One-on-One Listening Development Phases** — memory-bank_one-on-one-listening_progress_p0, memory-bank_one-on-one-listening_progress_p1 [INFERRED 0.75]
- **Homemade Teaching Toy Test Suite** — tests_test_class_repository, tests_test_homemade_teaching_repository, tests_test_homemade_teaching_client, tests_test_homemade_teaching_service, tests_test_homemade_teaching_exporter, tests_test_homemade_teaching_ui_helpers, tests_test_app_shell_menu, tests_test_export_repository [INFERRED 0.75]
- **Homemade Teaching Toy Test Stages** — memory-bank_homemadeteaching_test-plan_p1, memory-bank_homemadeteaching_test-plan_p2, memory-bank_homemadeteaching_test-plan_p3, memory-bank_homemadeteaching_test-plan_p4, memory-bank_homemadeteaching_test-plan_p5 [INFERRED 0.75]
- **Game Observation Subsystem Components** — memory_bank_game_observation_design, memory_bank_game_observation_progress, memory_bank_game_observation_design_game_observation, memory_bank_game_observation_design_game_observation_image, memory_bank_game_observation_design_invite_code, memory_bank_game_observation_design_call_ai_vision, memory_bank_game_observation_design_generate_observation [INFERRED 0.80]
- **Homemade Teaching Subsystem Components** — memory_bank_homemadeteaching_design, memory_bank_homemadeteaching_dev_plan, memory_bank_homemadeteaching_design_homemade_teaching_toy, memory_bank_homemadeteaching_design_generate_homemade_teaching [INFERRED 0.80]

## Communities (181 total, 44 thin omitted)

### Community 0 - "AI Key Management"
Cohesion: 0.05
Nodes (58): ConfigError, 业务配置缺失时抛出：如用户尚未配置 AI Key。, AiApiKey, AiApiKey — AI 接口 Key 数据模型。  安全约束： - `api_key_encrypted` 字段仅存密文，明文禁止入库、禁止写入日志。 -, get_active_ai_key(), get_decrypted_key(), AsyncSession, ai_key_repository — AI API Key 数据访问层。  所有函数均携带 tenant_id + user_id 过滤，确保数据隔离。  安 (+50 more)

### Community 1 - "Listening Record Export"
Cohesion: 0.06
Nodes (64): _build_domain_doc(), _build_from_scratch(), _clear_cell(), _domain_of_title(), export_batch_by_domain(), export_combined(), export_split_by_domain(), _extract_block() (+56 more)

### Community 2 - "Observation Image Management"
Cohesion: 0.05
Nodes (57): add_image(), delete_images_by_observation(), get_image(), list_images_by_observation(), AsyncSession, 新增一张观察图片并 flush，提交由最外层 use-case 负责。, 查询某观察记录下的所有图片，按 image_index 升序排列。, 按 id 查询单张图片，强制 tenant_id 过滤。 (+49 more)

### Community 3 - "Homemade Teaching Toy"
Cohesion: 0.06
Nodes (46): HomemadeTeachingToy, 教师自制教玩具记录。      每条记录保存一次 AI 生成或教师编辑后的教玩具方案。班级与教师姓名     采用冗余快照，避免后续设置变更影响历史导出。, AsyncSession, 写入一条导出记录。      Args:         session: 异步数据库会话（调用方负责事务管理）。         tenant_id: 机构, save_export_record(), create_homemade_teaching_toy(), delete_homemade_teaching_toy(), get_homemade_teaching_toy() (+38 more)

### Community 4 - "Date Calculation Service"
Cohesion: 0.08
Nodes (22): get_week_number(), get_weekday_cn(), is_within_semester(), is_workday(), pick_three_workdays(), date, 日期计算服务 — 纯函数，无 IO，无数据库依赖。, 返回 target_date 是开学后第几周（第 1 周起算）。      例：start_date=周一，target_date=同一天 → 第 1 周； (+14 more)

### Community 5 - "Authentication Service"
Cohesion: 0.10
Nodes (48): AuthError, 鉴权失败：token 无效、已过期、签名错误或用户名密码错误时抛出。          故意不区分"用户不存在"和"密码错误"，防止用户枚举攻击。, approve_user(), change_password(), create_user_by_admin(), list_users_for_admin(), login(), AsyncSession (+40 more)

### Community 6 - "Codebase Graph Query"
Cohesion: 0.04
Nodes (47): Cypher Query Language, detect_changes, Edge Types, get_architecture, get_code_snippet, query_graph, search_graph, codebase-memory 14 MCP Tools (+39 more)

### Community 7 - "Listening Record Repository"
Cohesion: 0.10
Nodes (42): delete_domains_by_record(), delete_indicator_results_by_record(), delete_record(), get_record_by_id(), list_indicator_results(), list_records(), Any, AsyncSession (+34 more)

### Community 8 - "Application Bootstrap"
Cohesion: 0.09
Nodes (38): ensure_default_user(), AsyncSession, 应用启动引导：确保默认用户存在。  单用户模式下，系统启动时自动在 user 表中创建默认管理员账号。 如果已存在则跳过（幂等）。, 确保默认用户存在，不存在则创建。已存在则跳过。, run_bootstrap(), Base, User, UserRole (+30 more)

### Community 9 - "External REST API"
Cohesion: 0.07
Nodes (36): AiEndpointVerifier, APIRouter, create_api_router(), 对外只读 REST API（二期）。  通过 :func:`create_api_router` 暴露 ``/api/v1`` 路由，由 ``app/main., 返回组装好的对外 API 路由（当前仅 v1）。, AiEndpointCheck, check_ai_endpoint(), OpenAI-compatible model catalog connection adapter. (+28 more)

### Community 10 - "Environment Config Management"
Cohesion: 0.09
Nodes (22): get_env_path(), Path, 返回 .env 文件的绝对路径（位于用户可写数据目录）。, 解析 .env 文件，返回 key-value 字典。      忽略空行与 # 开头的注释行。文件不存在时返回空字典。, 将 updates 中的 key-value 原子写入 .env，保留其余行不动。      若 .env 不存在则自动创建。写入失败时抛出 RuntimeEr, read_dot_env(), write_dot_env(), Path (+14 more)

### Community 11 - "AI Message Builder"
Cohesion: 0.07
Nodes (39): _build_prefix(), _build_user_content(), _holiday_hint(), 构建消息开头的班级与教学周信息。      context 支持 grade、class_name、week_number、weekday 字段；     we, 当 near_holiday 为 True 时返回临近节假日提示行，否则返回空字符串。      near_holiday 取值：True 表示明日为法定节假日, 根据任务类型和上下文构建发送给 AI 的用户消息。      context 支持以下字段：         grade, class_name, activi, _make_text_client(), AsyncClient (+31 more)

### Community 12 - "Observation Word Export"
Cohesion: 0.11
Nodes (35): _add_images_to_cell(), _build_from_scratch(), _clear_cell(), export_observation(), _fill_template(), Document, Path, 游戏观察记录 Word 导出器。 主方案：打开模板 `templates/ObservationRecord.docx`， 替换标题中的 'xx'… (+27 more)

### Community 13 - "Audit and AI Client"
Cohesion: 0.12
Nodes (15): 审计日志：记录关键操作（登录、改密、AI 调用、Word 导出等）。  审计日志通过结构化 JSON logger 输出，统一携带 audit_action 与, get_logger(), 年龄适配 AI 客户端。  将活动过程原文按年龄段（小班/中班/大班）改写，返回改写后文本。  输出 Schema：     {"adapted_process, AI 客户端基础模块 — 通用 Chat Completions 调用。  所有 AI 调用必须通过此模块，禁止在 service 层直接发 HTTP 请求。, 一日活动生成客户端 — 包含 5 种活动类型的内置默认提示词。  任务类型对应关系： - morning_exercise  →  晨间活动 - morning, 教案拆分 AI 客户端。  调用 OpenAI 兼容接口，将完整教案文本拆分为结构化字段。  输出 Schema（5 个必填键）：     activity_g, 游戏观察生成 AI 客户端。  调用 OpenAI 兼容多模态接口，输入 1~3 张游戏照片 + 元数据， 输出「观察目标 / 观察记录 / 评价分析 / 支持, AI 视觉客户端基础模块 — 多模态 Chat Completions 调用。  所有视觉 AI 调用必须通过此模块，禁止在 service 层直接发 HTTP (+7 more)

### Community 14 - "Record Detail Loader"
Cohesion: 0.11
Nodes (28): CompressedImage, list_domains_by_record(), UI 领域投影，强制 tenant_id + user_id 过滤。, load_record_detail(), 从 DB 装配整条记录详情（主表 + 各领域 + 图片 + 指标结果）。 指标的 sort_order 经 indicator_catalog…, 将 load_record_detail 结果转为 exporter 入参 (record, domains)（纯函数）。 images → [(data,…, to_export_payload(), Phase P5: Service Layer (+20 more)

### Community 15 - "Export Filename Builder"
Cohesion: 0.09
Nodes (30): build_batch_export_filename(), build_export_filename(), default_year_month(), distribute_images_by_filename(), format_record_summary(), format_stage_label(), infer_age_by_grade(), one_on_one_listening_page() (+22 more)

### Community 16 - "Semester Configuration"
Cohesion: 0.11
Nodes (24): NiceGUI - Python Web Framework, get_active_semester(), list_semesters_for_tenant(), AsyncSession, date, 查询当前用户的激活学期配置，若不存在返回 None。, 保存学期配置：若已存在激活记录则更新，否则新建。 同一用户只保留一条 is_active=True 的记录。, API tenant 投影；可在当前 tenant 内按 user_id 进一步筛选。 (+16 more)

### Community 17 - "App Startup Migration"
Cohesion: 0.10
Nodes (20): build_sync_url(), _get_alembic_ini_path(), _get_alembic_script_location(), 应用启动模块：自动执行 Alembic 数据库迁移。 支持三种运行模式： - 开发模式（python -m…, 将异步驱动 URL 转换为 Alembic 所需的同步驱动 URL。…, 在应用启动时自动执行 alembic upgrade head。 桌面、开发与服务器模式统一 fail-closed：迁移失败时记录异常并重新抛出，…, run_startup_migrations(), main() (+12 more)

### Community 18 - "Export Record Model"
Cohesion: 0.12
Nodes (21): ExportRecord, 导出记录数据模型。  对应数据库表：export_records 记录每次 Word 导出操作的元信息（文件名、路径、关联教案）。 导出记录为只增不改（immu, 渲染顶栏和左侧抽屉（无 context manager 版本）。 供已有页面调用：在页面函数开头调用一次，内容随后在同一层级放置。 Args: user:…, render_shell(), clean_filename_part(), format_setting_summary(), 校验单次或单领域图片数量是否在 1 至 3 张。, validate_generation_context() (+13 more)

### Community 19 - "Config Secrets Test"
Cohesion: 0.08
Nodes (29): _make_settings(), 回归测试：config.py 中密钥自动生成与 BOOTSTRAP_ADMIN_* 字段。 核心目标： 1. Settings…, 自动生成的 ENCRYPTION_KEY 应能被 app.core.crypto 正常使用。, BOOTSTRAP_ADMIN_ENABLED 默认 False。, BOOTSTRAP_ADMIN_TENANT_ID 默认 1。, BOOTSTRAP_ADMIN_USERNAME 默认 'sysadmin'。, BOOTSTRAP_ADMIN_PASSWORD 默认空字符串。, BOOTSTRAP_ADMIN_ALLOW_REMOTE 默认 False。 (+21 more)

### Community 20 - "Database Migration"
Cohesion: 0.18
Nodes (27): Any, _build_from_scratch(), _clear_cell(), _clear_paragraph(), export_course_review_activity(), _fill_template(), _get_bool(), _get_value() (+19 more)

### Community 21 - "External API Auth"
Cohesion: 0.13
Nodes (14): ApiPrincipal, _build_signing_string(), get_api_principal(), parse_api_keys(), Request, 对外 REST API 鉴权：API Key + 可选 HMAC 签名。  鉴权模型（服务间调用）： 1. **API Key**（必填）：调用方在 `X-Ap, 解析 `API_KEYS` 配置为 {api_key: tenant_id} 映射。      格式："key1:1,key2:2"；忽略空段与格式非法段（te, 校验 HMAC-SHA256 请求签名与时间戳新鲜度。 (+6 more)

### Community 22 - "Symmetric Encryption"
Cohesion: 0.10
Nodes (23): Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online(), Path, 应用配置：通过 pydantic-settings 从 .env 文件和环境变量加载。  首次部署（无 .env 文件）时的行为： - DATABASE_URL, 返回自动生成密钥的持久化文件路径（位于用户可写数据目录）。, 解析 key=value 文件，忽略空行与注释行。 (+15 more)

### Community 23 - "AI Vision Call"
Cohesion: 0.12
Nodes (19): _build_fernet(), decrypt(), encrypt(), 应用层对称加密工具（Fernet）。  密钥来源：Settings.ENCRYPTION_KEY（原始字符串，UTF-8 编码后取前 32 字节， 再经 bas, 将环境变量中的原始字符串密钥转换为 Fernet 实例。      Fernet 要求 32 字节的 URL-safe base64 编码密钥（共 44 个字符, 加密明文字符串，返回 URL-safe base64 密文字符串。      Args:         plain_text: 待加密的明文（禁止在调用方写入, 解密密文字符串，还原为原始明文。      Args:         cipher_text: 由 `encrypt()` 生成的密文字符串。      Re, CryptoError (+11 more)

### Community 24 - "Listening AI Client"
Cohesion: 0.10
Nodes (22): AiCallError, Exception, AI 接口调用失败时抛出：HTTP 4xx/5xx、网络超时、超过重试次数等。, call_ai_vision(), _make_retry_decorator(), AsyncClient, 构造 tenacity 重试装饰器：最多 3 次，指数退避 2s → 4s → 8s。, 发送多模态 Chat Completions 请求，返回解析后的 dict。      Args:         messages: 消息列表，content (+14 more)

### Community 25 - "Daily Plan Word Export"
Cohesion: 0.12
Nodes (27): AppError, 通用业务异常：输入非法、文件格式错误等非 AI / 非鉴权类业务错误。, _build_context_text(), _detect_mime(), generate_listening_domain(), _image_to_data_url(), 一对一倾听单领域生成 AI 客户端。  针对某一领域（健康/语言/社会/艺术/科学），输入该领域 3 张幼儿绘画照片 + 班级信息 + 该领域二级指标清单，一次, 调用视觉 AI 生成某领域的一对一倾听结构化内容。      Args:         images: 该领域绘画图片字节列表（经压缩后的 bytes，至少 (+19 more)

### Community 26 - "Image Storage Backend"
Cohesion: 0.18
Nodes (11): export_daily_plan(), 生成每日活动计划 Word 文档，返回文档字节流。      优先使用模板 `templates/teacherplan.docx` 填充其既有单元格；模板缺失, RGBColor, _make_plan(), _parse(), Document, Word 导出服务单元测试。 使用 python-docx 解析导出的 bytes，验证： - 返回非空 bytes - 使用模板时表格共 19…, 构造测试用 DailyPlan 实例（不依赖数据库，通过 SQLAlchemy __init__）。 (+3 more)

### Community 27 - "Indicator Catalog"
Cohesion: 0.11
Nodes (20): ABC, ImageStorageBackend, 存储图片字节，返回存储引用 dict。          Returns:             dict，键因后端而异（blob_backend 含 blo, 从存储引用还原图片字节。          Args:             stored: 与 put 返回格式相同的 dict。          Ret, 可插拔图片存储后端抽象。      put / get 与数据库 session 解耦：     - put 返回 stored_ref dict，由 repo, BlobImageStorage, MySQL BLOB 图片存储后端。  put/get 只操作内存 dict，实际 DB 写入由 repository 层完成。, MySQL BLOB 后端：图片二进制存入 game_observation_image.blob_content。 (+12 more)

### Community 28 - "Unit of Work Pattern"
Cohesion: 0.14
Nodes (25): IndicatorCatalog, IndicatorCatalog — 一对一倾听指标目录（参考数据，迁移预置）。  按 (grade, term, domain) 组织一级/二级指标及三档（★, get_indicator_by_id(), list_available_stages(), list_indicators(), list_indicators_by_ids(), AsyncSession, indicator_repository — 指标目录数据访问层。  只读参考数据查询（指标目录按 tenant_id + grade + term + dom (+17 more)

### Community 29 - "App Entry and Migration"
Cohesion: 0.10
Nodes (23): AsyncSessionUnitOfWork, AsyncSession, SQLAlchemy 异步会话的最外层 Unit of Work。, 在一个 use-case 结束时统一提交，任一步失败时统一回滚。, _clamp_star(), generate_domain_content(), _persist_domains(), AsyncSession (+15 more)

### Community 30 - "REST API Tests"
Cohesion: 0.11
Nodes (8): FastAPI - Web Framework, 对外 REST API 路由集成测试（httpx ASGITransport + SQLite 内存库）。, API Key 代表 tenant；不传 user 过滤时可读本 tenant 内多个教师。, _seed(), TestAuth, TestConfigEndpoints, TestDailyPlans, TestSignature

### Community 31 - "Data Model Smoke Test"
Cohesion: 0.11
Nodes (26): GameObservation, Phase P1: Migration & Seed, asyncio, Phase B — 数据模型冒烟测试（ORM + SQLite in-memory）。 测试策略： - 用 async_session…, GameObservation 可插入并按 id 查询。, GameObservation.tenant_id 非空约束生效。, AiApiKey 不传 key_type 时默认为 'text'。, invite_code 表已通过迁移删除，ORM 模型已不存在。 (+18 more)

### Community 32 - "Image Processing"
Cohesion: 0.12
Nodes (26): compress_image(), normalize_to_landscape(), 将图片统一为横版（宽 ≥ 高）。      处理步骤：       1. 按 EXIF 方向校正（手机照片常见）。       2. 透明通道转白底 RGB。, 将图片字节压缩至 max_bytes 以内。      Args:         data: 原始图片字节（JPEG / PNG / WebP 等 Pillo, Phase P8d: Image Processing, _make_jpeg_bytes(), _make_large_jpeg_bytes(), _make_png_with_alpha() (+18 more)

### Community 33 - "UI Menu Display"
Cohesion: 0.10
Nodes (16): get_display_name(), get_menu_items(), 返回顶栏显示名：优先 display_name，回退 username。 Args: user: 包含用户信息的字典，通常来自…, 根据角色返回可见菜单项列表，每项含 selected 标记。 Args: role: 用户角色，如 'teacher' / 'teaching_admin'…, 测试 app_shell 纯函数逻辑。 测试策略：将菜单项生成和显示名逻辑抽为纯函数，脱离 NiceGUI 渲染独立测试。, role=teacher 时，菜单包含核心项，不含已移除项。, 单用户模式下 sys_admin 与 teacher 看到相同菜单。, 所有角色均可见核心菜单项：每日活动计划、设置、提示词管理。 (+8 more)

### Community 34 - "AI Text Call"
Cohesion: 0.13
Nodes (24): call_ai(), call_ai_text(), _make_retry_decorator(), AsyncClient, 发送 Chat Completions 请求，返回纯文本 content 字符串。      与 call_ai() 的区别：不强制 json_object 格, 构造 tenacity 重试装饰器：最多 3 次，指数退避 2s → 4s → 8s。, 发送 Chat Completions 请求，返回解析后的 dict。      Args:         messages: 消息列表，格式为 [{"rol, Response (+16 more)

### Community 35 - "Listening Image Repository"
Cohesion: 0.14
Nodes (23): add_image(), delete_images_by_record(), get_image(), list_images_by_record(), AsyncSession, listening_image_repository — 一对一倾听图片数据访问层。, 新增一张倾听图片并 flush，提交由最外层 use-case 负责。, 查询某记录下的图片（可选按领域过滤），按领域 + image_index 升序。 (+15 more)

### Community 36 - "JWT Token Management"
Cohesion: 0.15
Nodes (19): create_access_token(), decode_access_token(), JWT access token 生成与解码工具。, 生成 JWT access token。      payload 字段：     - sub: str(user_id)     - tenant_id: i, 解码并验证 JWT token，返回 payload 字典。      token 过期、签名无效等情况统一抛出 AuthError。, _get_current_user(), profile_page(), 个人资料页面（路由：/profile）。  功能：   - 查看并修改显示名（真实姓名）   - 修改密码 (+11 more)

### Community 37 - "Batch Plan Export"
Cohesion: 0.16
Nodes (21): _build_collective_cell(), export_batch_daily_plans(), _export_from_scratch(), _fill_fields_cell(), _fill_plain_cell(), _fill_process_cell(), _fill_template(), _merge_row() (+13 more)

### Community 38 - "Game Observation Models"
Cohesion: 0.13
Nodes (18): ApiPrincipal, get_db(), AsyncSession, 对外 REST API 的 FastAPI 依赖。, 提供独立的异步数据库会话（只读查询，无需提交）。      测试可通过 ``app.dependency_overrides[get_db]`` 注入内存库会话, get_daily_plan(), health(), date (+10 more)

### Community 39 - "Admin Bootstrap"
Cohesion: 0.17
Nodes (17): bootstrap_admin(), _main(), _prompt_password(), _prompt_str(), 系统管理员初始化脚本。  模式：   --init           创建 sys_admin 账号（默认模式）   --reset-password 重置, --init 模式：创建 sys_admin 账号。, --reset-password 模式：重置 sys_admin 密码。, 重置 sys_admin 密码（需旧密码验证），返回执行结果说明。 (+9 more)

### Community 40 - "Diff Comparison Service"
Cohesion: 0.14
Nodes (19): compute_diff(), 差异比对服务 — 使用 difflib 对原文与改写文进行逐句比对。  分句规则：以句号（。）、问号（？）、感叹号（！）、换行符为分隔符， 保留分隔符到句子末尾, 将文本按标点符号或换行符拆分为句子列表，过滤空串。, 对原文与改写文按句比对，返回带 changed 标记的句子列表。      Args:         original: 活动过程原文。         ad, _split_sentences(), tests/test_diff_service.py — 差异比对服务测试。, 完全相同的文本，所有句子 changed 为 False。, 修改一句后，该句 changed 为 True，其余句子不变。 (+11 more)

### Community 41 - "API Response Schemas"
Cohesion: 0.15
Nodes (17): SQLAlchemy - ORM, GameObservation — 游戏观察记录数据模型。  每条记录对应教师的一次游戏观察，包含元数据（日期/环境/人员） 和 AI 生成的四段内容（观察目标, get_class_config(), list_class_configs_for_tenant(), AsyncSession, 查询当前用户的班级配置，若不存在返回 None。, 保存班级配置：若已存在则更新，否则新建。 每个用户只保留一条班级配置记录（最新）。, API tenant 投影；可在当前 tenant 内按 user_id 进一步筛选。 (+9 more)

### Community 42 - "Listening Data Models"
Cohesion: 0.27
Nodes (13): ClassConfigOut, DailyPlanListOut, DailyPlanOut, HealthOut, PageMeta, 对外 REST API 响应模型（Pydantic）。  仅暴露教学计划相关的只读字段；不包含密钥、密码等敏感信息。, SemesterOut, ClassConfig (+5 more)

### Community 43 - "Observation Generation Client"
Cohesion: 0.12
Nodes (17): ListeningDomain, ListeningImage, ListeningImage — 一对一倾听绘画图片数据模型。  每个领域 3 张（共 15 张/记录）。复用游戏观察图片的可插拔 BLOB 存储， 新增 do, ListeningIndicatorResult, ListeningIndicatorResult — 一对一倾听二级指标达成结果。  每条 listening_record 的每个领域每个二级指标一条，记录达, ListeningRecord, P1 — 一对一倾听数据模型冒烟测试（ORM + SQLite in-memory）。  用 async_session fixture（create_all）, IndicatorCatalog 可创建并保存三档标准。 (+9 more)

### Community 44 - "Homemade Teaching Export"
Cohesion: 0.14
Nodes (19): _build_context_text(), _detect_mime(), generate_observation(), _image_to_data_url(), 将上下文 dict 转为给 AI 的说明文本。, 根据文件头检测图片 MIME 类型，无法识别时默认 image/jpeg。, 将图片字节转为 base64 data-url 字符串。, 调用视觉 AI 生成游戏观察记录四段内容。      Args:         images: 图片字节列表（1~3 张，经压缩后的 bytes）。 (+11 more)

### Community 45 - "User Repository Test"
Cohesion: 0.24
Nodes (18): _build_from_scratch(), _clear_cell(), export_homemade_teaching(), _fill_template(), _get_value(), Any, Document, Path (+10 more)

### Community 46 - "Documentation and ADRs"
Cohesion: 0.16
Nodes (19): create_user(), get_user_by_id(), 创建用户并持久化到数据库，返回已持久化的 User 对象。, 在指定租户下按 ID 查询用户，不存在时返回 None。, 用户仓库层集成测试（SQLite 内存库）。, 支持用户名关键字筛选和分页，且总数统计正确。, 不同 tenant_id 下同名用户互不可见。, 不同 tenant_id 下通过 ID 查询返回 None。 (+11 more)

### Community 47 - "Setup State Management"
Cohesion: 0.23
Nodes (16): AGENTS.md - Repository Guidelines, docs/ADR/ADR-0002 - Single User UI and Tenant API, docs/ADR/ADR-0005 - Controlled AI Agent Runtime, docs/API.md - External REST API Reference, docs/DEVELOPER.md - Developer Guide, docs/MANUAL_TESTING.md - Manual Testing Matrix, ADR-0003, docs/design/agent-runtime.md - Controlled AI Agent Runtime Design (+8 more)

### Community 48 - "Daily Plan Repository"
Cohesion: 0.17
Nodes (12): _get_state_path(), is_setup_complete(), mark_setup_complete(), Path, 返回 setup 完成标记文件的路径（位于用户可写数据目录）。, 检查系统是否已完成初始化配置（同步调用，纯文件检查，无 DB 查询）。, 写入 setup 完成标记文件。写入失败时静默忽略（不阻断正常流程）。, Path (+4 more)

### Community 49 - "Course Review Subsystem"
Cohesion: 0.21
Nodes (18): delete_daily_plan(), get_daily_plan_by_date(), get_daily_plan_by_id_for_tenant(), _list_daily_plans(), list_daily_plans_for_tenant(), list_daily_plans_for_user(), AsyncSession, date (+10 more)

### Community 50 - "System Architecture Components"
Cohesion: 0.11
Nodes (19): 课程审议 AI 结构化 JSON 合约, 课程审议持久化与历史导出, 课程审议 Word 模板映射, 课程审议 AI 客户端与服务层, 课程审议分阶段交付, 课程审议 Word 导出阶段, 课程审议完整实现, 课程审议自动测试证据 (+11 more)

### Community 51 - "Course Review Models"
Cohesion: 0.12
Nodes (18): AI Integration Layer, Authentication System (JWT + RBAC), Course Review Activity Subsystem, Daily Plan Subsystem, Database Layer (MySQL/SQLite), Game Observation Subsystem, Homemade Teaching Toy Subsystem, Kindergarten Management System (+10 more)

### Community 52 - "Listening and Observation Design"
Cohesion: 0.26
Nodes (15): CourseReviewActivity, 课程审议记录。      每条记录保存一次课程审议生成与教师编辑后的结果。班级、年龄段与教师姓名     采用冗余快照，避免后续系统设置变更影响历史导出。, create_course_review_activity(), delete_course_review_activity(), get_course_review_activity(), list_course_review_activities(), AsyncSession, 删除课程审议记录，强制 tenant_id + user_id 双重过滤。 (+7 more)

### Community 53 - "User Context and UI"
Cohesion: 0.11
Nodes (16): ListeningDomain — 一对一倾听单领域内容。  每条 listening_record 对应 5 条本表（健康/语言/社会/艺术/科学各一）。 年, Listening Indicator Result Model, ListeningRecord — 一对一倾听观察记录主表。  一条记录对应一个幼儿的一次「一对一倾听」观察，覆盖五大领域。 领域级内容（目标/日期/图片/指标, Game Observation Design, One-on-One Listening Observation Subsystem, P0 - Branch & Template Analysis, P1 - Data Model & Migration, P2 - Repository Layer (+8 more)

### Community 54 - "Holiday Check Client"
Cohesion: 0.15
Nodes (14): get_current_user(), 单用户模式：提供固定的默认用户上下文。  取消登录功能后，所有页面通过此模块获取当前用户信息， 而非从 JWT token 中解析。, 返回当前用户信息字典（单用户模式下始终返回默认管理员）。, app_shell(), 统一布局：左侧分组菜单 + 顶栏。 用法:: async with app_shell(user, active="daily-plan"): #…, home_page(), page, 主页仪表盘（路由：/home）。 显示欢迎信息、当前班级信息和快捷入口卡片。 (+6 more)

### Community 55 - "Route Guard Middleware"
Cohesion: 0.21
Nodes (9): is_holiday(), 查询指定日期是否为法定节假日。      返回语义（固定）：     - True  ：法定节假日（API type == 2）     - False ：工作, MockTransport, 普通周末（type=1）返回 False（与法定节假日语义严格区分）, 调班工作日（type=3）返回 False, API 返回 5xx 时降级，返回 None, 同一日期第二次调用命中缓存，不发出 HTTP 请求, 可编程异步 HTTP 传输层，用于拦截 httpx 请求。 (+1 more)

### Community 56 - "Activity Generation Service"
Cohesion: 0.16
Nodes (11): AuthMiddleware, Request, 路由守卫中间件（已禁用 — 单用户模式无需登录）。  保留模块以便后续恢复登录功能。当前为直通中间件，不做任何鉴权检查。 根路径 (/) 重定向到 /home。, 单用户模式：仅将根路径重定向到 /home，其余请求直接放行。, BaseHTTPMiddleware, asyncio, tests/test_middleware.py — 单用户模式路由中间件测试。 验证： - 根路径 (/) 重定向到 /home -…, 中间件可被实例化（接收 ASGI app 参数）。 (+3 more)

### Community 57 - "Lesson Plan Splitter"
Cohesion: 0.24
Nodes (14): AiParseError, AI 返回内容解析失败时抛出：JSON 格式非法、缺少必要字段等。, generate_activity(), 生成单项一日活动内容（纯文本输出）。      Args:         task_type: 任务类型（morning_exercise / morning, _build_user_content(), generate_homemade_teaching(), 不支持的任务类型且无自定义 prompt 时抛出 AiParseError。, test_generate_activity_unsupported_task_type_raises() (+6 more)

### Community 58 - "Prompt Version Manager"
Cohesion: 0.21
Nodes (15): 将完整教案文本拆分为结构化字段。      Args:         raw_text: 用户粘贴的完整教案文本。         api_base_url:, split_lesson_plan(), _make_client(), AsyncClient, tests/test_lesson_plan_client.py — 教案拆分客户端测试。  使用 httpx.MockTransport 隔离真实 HTTP, AI 返回空 dict 时，抛出 AiParseError。, AI 返回额外字段时，只保留 5 个必要键。, 正常响应时，返回包含全部 5 个键的 dict。 (+7 more)

### Community 59 - "Age Adaptation Client"
Cohesion: 0.24
Nodes (8): get_holiday_name(), 返回法定节假日名称，如"国庆节"、"春节"。      返回语义：     - str  ：该日期是法定节假日，返回节日名称（如"国庆节"）     - Non, make_response(), 法定节假日且 API 返回 holiday 对象时，取其 name 字段, 法定节假日但 holiday 字段为 null 时，从 type.name 取名称, 先调用 is_holiday，再调用 get_holiday_name，不发出额外 HTTP 请求, 构造节假日 API 响应。      holiday_name：当 day_type=2 时，传入节日名称（如"国庆节"），, TestGetHolidayName

### Community 60 - "Legal Holiday Client"
Cohesion: 0.18
Nodes (8): 保存新版本提示词，自动递增版本号并将旧激活记录设为 inactive。      Args:         session: 异步数据库会话。, save_new_version(), 不同 tenant_id 的提示词互不可见。, save_new_version — 保存新版本提示词, 保存新版本后，旧版本 is_active 变为 False。, 不同 task_type 的版本号独立计数。, TestSaveNewVersion, TestTenantIsolation

### Community 61 - "Observation Export Helpers"
Cohesion: 0.25
Nodes (13): adapt_activity_process(), 将活动过程按年龄段改写。      Args:         original: 活动过程原文。         grade: 年龄段，如"小班"、"中班"、, _make_client(), AsyncClient, tests/test_adapt_client.py — 年龄适配客户端测试。, AI 返回缺少 adapted_process 字段时，抛出 AiParseError。, 原文为空字符串时，不发请求直接抛出 AiParseError。, 传入自定义 system prompt 时，正常调用不报错。 (+5 more)

### Community 62 - "Password Hashing"
Cohesion: 0.18
Nodes (10): _ensure_cache_fresh(), get_legal_holidays_in_year(), date, 中国法定节假日客户端。  特性： - 查询指定日期是否为法定节假日（True / False / None） - 查询是否为法定节假日前一天（near_holi, 一次性查询整年的法定节假日集合（单请求，避免逐日并发触发限流）。      用于「一对一倾听」批量选取工作日时排除节假日。复用 timor.tech 的「年」接, 若缓存日期不是今天，清空缓存（单日缓存 + 年节假日缓存）。, 同年第二次查询命中缓存，不再发起 HTTP。, API 5xx → 返回 None（降级）。 (+2 more)

### Community 63 - "Audit Log Test"
Cohesion: 0.18
Nodes (10): build_export_filename(), 构造导出文件名。 格式：{tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx, 校验大环境值是否合法（仅允许 户外/室内/公共）。, validate_big_env(), tests/test_observation_ui_helpers.py — 游戏观察 UI 工具函数测试。  测试覆盖（3 项纯函数）：   1. 导出文件名, 文件名格式为 {tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx。, 非法大环境值校验失败（返回 False 或抛异常）。, test_build_export_filename_format() (+2 more)

### Community 64 - "Adjusted Workday Check"
Cohesion: 0.27
Nodes (11): hash_password(), 将明文密码哈希为 Argon2 格式字符串。, verify_password(), `verify_password` 对正确密码返回 True。, `verify_password` 对错误密码返回 False。, 同一密码两次哈希结果不同（Argon2 带 salt）。, test_empty_password(), test_hash_not_equal_to_plain() (+3 more)

### Community 65 - "Activity Content Generation"
Cohesion: 0.19
Nodes (12): log_audit(), 记录一条审计日志。      Args:         action: 操作标识（如 login_success / change_password / ai, 更新用户个人资料的显示名。 Args: session: 异步数据库会话。 tenant_id: 租户 ID。 user_id: 用户 ID。…, update_profile_display_name(), tests/test_audit.py — 审计日志测试。, 审计日志携带 audit_action / tenant_id / user_id 及附加字段。, 未提供 tenant_id / user_id 时默认为 None。, test_log_audit_defaults_none_ids() (+4 more)

### Community 66 - "Date Selection Panel"
Cohesion: 0.22
Nodes (7): is_adjusted_workday(), 判断指定日期是否为调班工作日（节假日调休补班的周末）。      返回语义：     - True  ：调班工作日（API type == 3），周末需正常上班, 普通工作日（type=0）返回 False, 调班工作日（type=3）返回 True，例如 2026-05-09, 法定节假日（type=2）返回 False, 先调用 is_holiday，再调用 is_adjusted_workday，共享缓存不发额外请求, TestIsAdjustedWorkday

### Community 67 - "Listening Migration Test"
Cohesion: 0.24
Nodes (11): generate_activity_content(), AsyncSession, 生成单项活动内容。      Args:         session: 异步数据库会话（查询 AI Key 与自定义提示词）。         tenant, _make_mock_ai_key(), tests/test_generate_service.py — 一日活动生成服务测试。  使用 Mock 隔离 AI 调用、AI Key 仓库与提示词仓库。, 用户未配置 AI Key 时抛出 ConfigError。, 无自定义提示词时，使用内置默认（system_prompt=None）并返回生成文本。, 存在激活的自定义提示词时，将其传给 generate_activity。 (+3 more)

### Community 68 - "Course Review Generation"
Cohesion: 0.23
Nodes (7): DatePanel, 外部或内部直接设置日期值，触发联动更新（同步入口）。, 日期选择器选值回调（同步，启动异步联动）。, 日期选择面板，可嵌入任意 NiceGUI 页面。 参数： semester_start: 学期开始日期，用于计算第几周；传 None 时不显示周次信息。…, 渲染面板并返回外层 card 元素，可嵌入父容器。, card, date_type

### Community 69 - "Special Day Tags"
Cohesion: 0.17
Nodes (9): migrated_db(), P1 — 一对一倾听迁移与种子集成测试。  在临时 sqlite 文件库上实际执行 `alembic upgrade head`，验证： - 5 个新表创建成功, export_records 含 listening_record_id 列。, 种子 JSON：5 领域共 30 个二级指标，每个含 3 档标准、sort_order 连续。, 在临时 sqlite 文件库上执行 alembic upgrade head，返回库路径。, 每条种子三档标准非空，tenant_id=1，max_stars=3。, test_export_records_has_listening_col(), test_indicator_seed_integrity() (+1 more)

### Community 70 - "Near Holiday Check"
Cohesion: 0.44
Nodes (10): _build_user_content(), generate_course_review_activity(), _make_client(), AsyncClient, test_generate_course_review_activity_filters_extra_keys(), test_generate_course_review_activity_invalid_string_payload_raises(), test_generate_course_review_activity_requires_boolean_fields(), test_generate_course_review_activity_success() (+2 more)

### Community 71 - "User Registration"
Cohesion: 0.27
Nodes (4): get_special_day_tags(), 返回不放假节日标签列表（本地硬编码）。     空列表表示该日期无特殊节日标注。     返回值为副本，修改不影响内部数据。, Step 2.4 — 节假日客户端测试  使用自定义 httpx.AsyncBaseTransport 模拟 API，测试： - 正常响应的 bool 返回值（, TestGetSpecialDayTags

### Community 72 - "Prompt Repository Test"
Cohesion: 0.24
Nodes (7): is_near_holiday(), 判断 target_date 是否为法定节假日前一天。      返回语义：     - True  ：明天是法定节假日     - False ：明天不是法定, AsyncBaseTransport, 法定节假日前一天（9月30日，10月1日为法定节假日）返回 True, 周五（普通周末前一天）返回 False，不视为 near_holiday, 普通工作日的前一天，次日也是工作日，返回 False, TestIsNearHoliday

### Community 73 - "Version Listing"
Cohesion: 0.18
Nodes (11): 自助注册： - 若系统（tenant_id=1）尚无任何用户，注册者自动成为 sys_admin（is_active=True，可立即登录）。 - 否则创建…, register_user(), 空库第一个注册用户自动成为 sys_admin（is_active=True），可立即登录。, 已有用户后，第二个注册者成为 teacher（is_active=False），需管理员审核。, 同用户名注册两次时抛出 ValueError。, 注册时传入显示名，返回的用户对象应包含该显示名。, test_first_user_becomes_sys_admin_and_active(), test_register_duplicate_username_raises() (+3 more)

### Community 74 - "Course Review Service Test"
Cohesion: 0.24
Nodes (7): AsyncSession, 将指定版本设为激活，其余版本设为 inactive。      Args:         session: 异步数据库会话。         tenant_i, rollback_to_version(), 回滚不存在的版本应抛出 ValueError。, rollback_to_version — 回滚到指定版本, 回滚后非目标版本应变为 inactive。, TestRollbackToVersion

### Community 75 - "Legacy Setup Page"
Cohesion: 0.31
Nodes (5): get_active_prompt(), 查询该用户指定任务类型的当前激活提示词。      Args:         session: 异步数据库会话。         tenant_id: 租户, 提示词仓库层集成测试。  使用 SQLite 内存库 fixture（来自 conftest.py），与真实 MySQL 完全隔离。, get_active_prompt — 查询激活提示词, TestGetActivePrompt

### Community 76 - "Agent Runtime Tools"
Cohesion: 0.32
Nodes (5): list_versions(), 返回指定任务类型的所有版本，按版本号降序排列。      Args:         session: 异步数据库会话。         tenant_id:, list_versions — 列出所有版本, 只返回指定 task_type 的版本，不混入其他类型。, TestListVersions

### Community 77 - "Prompt Template Model"
Cohesion: 0.50
Nodes (7): generate_course_review_activity_content(), AsyncSession, _make_mock_ai_key(), _result(), test_generate_course_review_activity_content_no_ai_key_raises(), test_generate_course_review_activity_content_success_with_default_prompt(), test_generate_course_review_activity_content_uses_db_prompt()

### Community 78 - "Security Audit"
Cohesion: 0.32
Nodes (6): page, 历史配置入口（路由 /setup）。 当前配置入口统一为 /settings；保留本路由只为兼容旧书签和旧链接。, setup_page(), asyncio, 旧 /setup 路由只保留为 /settings 兼容入口。, test_setup_redirects_to_settings()

### Community 79 - "Game Observation Design"
Cohesion: 0.25
Nodes (8): AgentRuntime, Tool: calendar.read_evaluation, Tool: daily_plan.draft_reflection_patch, Tool: daily_plan.draft_section_patch, Tool: daily_plan.read_context, Tool: daily_plan.read_current, Tool: settings.read_class_areas, ToolRegistry

### Community 80 - "Image Config Test"
Cohesion: 0.33
Nodes (5): PromptTemplate, PromptTemplate — 提示词模板数据模型。  支持以下任务类型，每种类型独立维护版本历史，同一用户同一类型只能有一条 is_active=True, prompt_repository — 提示词模板数据访问层。  支持提示词多版本管理：保存新版本、回滚、查询激活版本、列出所有版本。  约束： - 同一用户同, PromptTemplate 可保存 task_type='game_observation'。, test_prompt_template_game_observation_task_type()

### Community 81 - "AI Return Parser"
Cohesion: 0.33
Nodes (7): Security lower bounds and dependency audit are production gates, Dependency and release supply-chain threat, Security threat model, Requirements encode six Dependabot lower-bound classes plus related transitive security floors, Python dependency requirements, python-jose remains the transitive source of ecdsa 0.19.2 residual risk, Requirements enforce NiceGUI 3.16.0 and FastAPI 0.141.1 with Starlette 1.6.0

### Community 82 - "UI Helper Functions"
Cohesion: 0.38
Nodes (7): Game Observation Design Document, Call AI Vision Function, Game Observation Table, Game Observation Image Table, Generate Observation Function, Invite Code Table, Game Observation Progress Document

### Community 83 - "Prompt Edit Panel"
Cohesion: 0.29
Nodes (5): 测试图片相关配置项（Phase A）。  验证新增的 IMAGE_STORAGE_BACKEND 和 IMAGE_MAX_BYTES 配置项存在且默认值正确，, IMAGE_MAX_BYTES 默认值为 1048576（1MB）。, IMAGE_STORAGE_BACKEND 默认值为 mysql_blob。, test_image_max_bytes_default(), test_image_storage_backend_default()

### Community 84 - "Dependency Upgrades"
Cohesion: 0.47
Nodes (3): _parse_fields(), 将 AI 生成的行结构文本解析为 {标签: 内容} 字典。      识别形如 "标签：内容" 的行；其后不含标签的行（如编号 1./2./3.）     归属, TestParseFields

### Community 85 - "Listening Generation Test"
Cohesion: 0.53
Nodes (5): mask_api_key(), 脱敏 API Key，仅对较长密钥保留末四位。, test_mask_api_key_hides_short_key(), test_mask_api_key_shows_last_four_at_threshold(), test_mask_api_key_shows_last_four_for_long_key()

### Community 86 - "Database Migration Script"
Cohesion: 0.33
Nodes (6): _build_task_panel(), 构建单个任务类型的提示词编辑区块（含历史版本列表）。, _render_history(), column, label, textarea

### Community 87 - "Drop Invite Code Migration"
Cohesion: 0.33
Nodes (6): Six Dependabot security lower-bound upgrades, Changelog, ecdsa 0.19.2 residual risk remains outside this upgrade, Local dependency tests do not prove GitHub alert closure, Python 3.14.7 runtime unification, NiceGUI 3.16.0/FastAPI 0.141.1/Starlette compatibility baseline

### Community 88 - "Add Course Review Migration"
Cohesion: 0.33
Nodes (6): _ai_return(), DB 有激活 one_on_one_listening 提示词 → 作为 system_prompt 传给 AI。, 正常生成：返回五段内容 + 指标结果 + 压缩图片，触发审计。, test_default_three_stars(), test_generate_domain_ok(), test_prompt_from_db_overrides_default()

### Community 89 - "Observation Image Model"
Cohesion: 0.40
Nodes (4): downgrade(), Upgrade schema.      列 model_name 可能已存在（来自另一台机器的未提交迁移）。     若不存在则新增；若已存在则修改为 NOT, Downgrade schema: 恢复为可空、无默认值。, upgrade()

### Community 90 - "Homemade Teaching Test Plan"
Cohesion: 0.40
Nodes (4): downgrade(), 删除 invite_code 表（邀请码功能已移除）。, 重建 invite_code 表（回滚用）。, upgrade()

### Community 91 - "Test Fixture Setup"
Cohesion: 0.80
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 92 - "Python Runtime Test"
Cohesion: 0.40
Nodes (4): GameObservationImage, GameObservationImage — 游戏观察图片数据模型。  可插拔存储：本期实现 MySQL BLOB 后端（blob_content 存压缩后二进, GameObservationImage.blob_content 可存取二进制字节，值完全相同。, test_game_observation_image_blob_roundtrip()

### Community 93 - "Add Teacher Name Migration"
Cohesion: 0.40
Nodes (5): Homemade Teaching Toy Test Plan, Test Stage P1, Test Stage P2, Test Class Repository File, Upsert Class Config Function

### Community 94 - "Add Homemade Teaching Migration"
Cohesion: 0.40
Nodes (4): async_session(), AsyncSession, 公共测试 fixture。  提供基于 SQLite 内存库的异步 session，用于仓库层集成测试， 与真实 MySQL 连接完全隔离。, 每个测试函数获得独立的 SQLite 内存库 + 全新表结构。

### Community 96 - "Expand Task Type Migration"
Cohesion: 0.83
Nodes (3): downgrade(), _has_column(), upgrade()

### Community 97 - "Database Migration Script"
Cohesion: 0.83
Nodes (3): downgrade(), _has_table(), upgrade()

### Community 98 - "Database Migration Script"
Cohesion: 0.83
Nodes (3): downgrade(), _has_column(), upgrade()

### Community 100 - "Application Layers"
Cohesion: 0.50
Nodes (4): Integration, NiceGUI UI, Repository, Service Layer

### Community 101 - "Feature Development Phases"
Cohesion: 0.50
Nodes (4): One-on-One Listening Progress Record, Development Phase P0, Development Phase P1, Pick Three Workdays Function

### Community 102 - "AI and Product Features"
Cohesion: 0.67
Nodes (4): AI 拆分、年龄适配、Word 导出与存档, 首期每日活动计划闭环, 首期产品需求文档, 角色权限与数据安全

### Community 105 - "Dependency Security Tests"
Cohesion: 0.67
Nodes (3): Regression guard for dependency versions raised by Dependabot., _requirements_by_name(), test_dependabot_security_floors_are_not_downgraded()

### Community 106 - "Release Build Workflow"
Cohesion: 0.67
Nodes (3): Release build workflow, Python 3.14.7 release build runtime, Windows/Linux/Docker release artifacts

### Community 121 - "Contributing guide"
Cohesion: 0.67
Nodes (3): Agent rejection and zero-change verification, Agent implementation rules: closed registry, no WRITE or persistence, Contributing guide

### Community 122 - "ADR-0004 AI and fixed Word boundaries"
Cohesion: 0.67
Nodes (3): Existing AI adapter and teacher-adoption boundaries apply to future Agent, ADR-0004 AI and fixed Word boundaries, Existing one-shot AI functions cannot be exposed as arbitrary Agent Tools

### Community 123 - "ADR index"
Cohesion: 0.67
Nodes (3): Accepted ADR-0005 Agent registry entry, Agent Tool, permission, memory, or write changes require a new ADR, ADR index

### Community 124 - "Future Microservice Decomposition"
Cohesion: 1.00
Nodes (3): Future Microservice Decomposition, Main Application (app/integration/), Services Directory Status README

### Community 125 - "一日活动提示词与一键生成"
Cohesion: 0.67
Nodes (3): 一日活动节假日语义, 一日活动提示词版本管理, 一日活动提示词与一键生成

### Community 126 - "Homemade Teaching Design Document"
Cohesion: 1.00
Nodes (3): Homemade Teaching Design Document, Generate Homemade Teaching Function, Homemade Teaching Toy Table

## Knowledge Gaps
- **144 isolated node(s):** `一日活动节假日语义`, `一日活动提示词版本管理`, `课程审议手动流程验收`, `一日活动教案处理流水线`, `课程审议持久化与历史导出` (+139 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **44 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Base` connect `Application Bootstrap` to `AI Key Management`, `Homemade Teaching Toy`, `API Response Schemas`, `Listening Data Models`, `Observation Generation Client`, `Unit of Work Pattern`, `Image Config Test`, `Export Record Model`, `Listening and Observation Design`, `User Context and UI`, `Symmetric Encryption`, `Python Runtime Test`, `Add Homemade Teaching Migration`, `Data Model Smoke Test`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `read_dot_env()` connect `Environment Config Management` to `Semester Configuration`, `Symmetric Encryption`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Why does `get_logger()` connect `Audit and AI Client` to `AI Key Management`, `Listening Record Export`, `JWT Token Management`, `Batch Plan Export`, `Application Bootstrap`, `User Repository Test`, `Password Hashing`, `Lesson Plan Splitter`, `Daily Plan Word Export`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `AiParseError` (e.g. with `test_adapt_empty_original_raises_parse_error()` and `test_adapt_missing_adapted_process_raises_parse_error()`) actually correct?**
  _`AiParseError` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Base` (e.g. with `AiApiKey` and `ClassConfig`) actually correct?**
  _`Base` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `AuthError` (e.g. with `test_approve_user_allows_login()` and `test_change_password_success()`) actually correct?**
  _`AuthError` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `一日活动节假日语义`, `一日活动提示词版本管理`, `课程审议手动流程验收` to the rest of the system?**
  _144 weakly-connected nodes found - possible documentation gaps or missing edges._