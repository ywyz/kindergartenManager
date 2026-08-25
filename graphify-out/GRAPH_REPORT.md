# Graph Report - KindergartenManager  (2026-08-25)

## Corpus Check
- 54 files · ~143,464 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3191 nodes · 7334 edges · 209 communities (157 shown, 52 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 472 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- F009 Persistence Matrix
- F008 Provider Adapter
- Daily Plan Export
- F007 Runtime Safety
- F009 Browser Mock
- External REST API
- Codebase Memory MCP
- Observation Repository
- Daily Activity AI Client
- F008 Daily Plan UI
- F008 Tool Executors
- Authentication Service
- Export Record Repository
- Listening Service Layer
- Observation Word Export
- Encryption Utilities
- User Bootstrap
- Database Models
- Migration Smoke Tests
- Export Filename Helpers
- Config Secrets Tests
- App Entry and UI
- Course Review Export
- API Key Auth
- Image Storage Backend
- AI Key Repository Tests
- REST API Tests
- Observation Image Repository
- Auth and User Admin
- Indicator Repository
- Vision AI Client
- AI Key Repository
- F008 Daily Plan UI
- AI Client Base
- Admin Bootstrap Script
- User Registration
- App Shell UI
- Env File Utilities
- Observation AI Client
- Homemade Teaching Export
- User Repository
- Project Documentation
- AI Endpoint Verification
- Daily Plan Repository
- Course Review Activity
- System Architecture
- API Response Schemas
- Audit and User Admin
- Course Review Repository
- Startup Migrations
- Holiday API Client
- Class Config Settings
- Auth Middleware
- Listening Data Models
- Setup State Management
- REST API Routes
- Password Hashing
- Runtime Path Utilities
- Homemade Teaching Repository
- F007 F008 F009 Foundation
- Prompt Repository
- CI Quality Workflow
- Listening Subsystem Plan
- Age Adaptation Client
- Holiday Client
- Observation UI Helpers
- Application Config
- Adjusted Workday Check
- Menu Items Logic
- Course Review UI Helpers
- Database Config Tests
- Daily Activity Service
- Date Panel Component
- Listening Migration Tests
- Course Review Service
- Course Review AI Client
- Special Day Tags
- Near Holiday Check
- Prompt Version Save
- Prompt Version Rollback
- Semester Repository
- Homemade Teaching AI Client
- Observation Generation Service
- UI Helper Functions
- Prompt Version Listing
- Agent Runtime Tools
- Listening Service Tests
- Homemade Teaching Service
- Dependency Security Audit
- Game Observation Docs
- Image Config Tests
- Prompt Editor UI
- Root Redirect Page
- Dependency Upgrade Notes
- Listening Image Repo Tests
- Alembic Migration Env
- AI Key Model Migration
- Drop Invite Code Migration
- Course Review Migration
- API Database Dependency
- Workday Date Utilities
- Homemade Teaching Toy Tests
- Async Test Fixtures
- Runtime Pin Tests
- Add Teacher Name Migration
- Homemade Teaching Toy Migration
- Prompt Task Enum Migration
- Application Architecture Layers
- Listening Progress Development
- Product Requirements Documents
- Agent Registry Boundary Tests
- Agent Contract Tests
- Dependency Security Tests
- Release Build Workflow
- AI API Key Migration
- Phase B Schema Migration
- Smoke Test Migration
- Add User Table Migration
- Export Observation Migration
- Add Class Config Migration
- Seed Indicator Catalog Migration
- Prompt Template Migration
- Teaching Prompt Task Migration
- Export Record Table Migration
- Listening Schema Migration
- Daily Plan Table Migration
- Production Docker Topology
- Modular Monolith Decision
- Deb Build Script
- Post-Install Script
- Post-Remove Script
- Pre-Remove Script
- Database Migration Tool
- Web Server
- Containerization Platform
- MySQL Database Engine
- SQLite Database Engine
- Multi-tenant Isolation
- Codebase Memory Skill
- Application Entry Points
- Risk Label Definitions
- Auth Package Init
- Async SQLAlchemy Session
- Core Package Init
- App Package Init
- AI Client Package Init
- Holiday Client Package
- Integration Package Init
- Python Any Type
- Word Export Package Init
- RGB Color Type
- Jobs Package Init
- Exception Base Class
- Repository Package Init
- Components Package Init
- Dependency Security Baseline
- Image Storage Backend
- Test Stage P4
- Word Document Library
- Response Type
- Async HTTP Client
- Prompt Template Task Types
- ADR 0003
- Dependency security baseline
- Developer Agent workflow
- Image Storage Backend
- Test Stage P3
- Test Stage P4
- Test Stage P5
- memory bank implementation plan
- Architecture history pointer
- Supporting Concepts
- General Components
- Homemade Teaching Development Plan
- kindergarten manager
- python docx Word Document
- Kindergarten Manager architecture overview
- Python dependency baseline
- Response Module
- Async Client

## God Nodes (most connected - your core abstractions)
1. `AgentContext` - 63 edges
2. `TrustedActor` - 47 edges
3. `Permission` - 46 edges
4. `AiParseError` - 43 edges
5. `DailyPlanScope` - 37 edges
6. `Base` - 36 edges
7. `_runtime_module()` - 36 edges
8. `_context()` - 34 edges
9. `MockTransport` - 31 edges
10. `_agent()` - 30 edges

## Surprising Connections (you probably didn't know these)
- `test_ai_key_default_key_type()` --calls--> `AiApiKey`  [INFERRED]
  tests/test_migrations_smoke.py → app/core/models/ai_key.py
- `test_ai_key_vision_type()` --calls--> `AiApiKey`  [INFERRED]
  tests/test_migrations_smoke.py → app/core/models/ai_key.py
- `test_class_config_teacher_name_column()` --calls--> `ClassConfig`  [INFERRED]
  tests/test_migrations_smoke.py → app/core/models/class_config.py
- `test_course_review_activity_insertable()` --calls--> `CourseReviewActivity`  [INFERRED]
  tests/test_migrations_smoke.py → app/core/models/course_review_activity.py
- `test_user_display_name_nullable()` --calls--> `User`  [INFERRED]
  tests/test_migrations_smoke.py → app/core/models/user.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Course Review Activity Documentation Set** — memory-bank_coursereviewactivity_design, memory-bank_coursereviewactivity_dev-plan, memory-bank_coursereviewactivity_progress, memory-bank_coursereviewactivity_test-plan [EXTRACTED 0.75]
- **Daily Plan Documentation Set** — memory-bank_daily-plan_design, memory-bank_daily-plan_progress [EXTRACTED 0.75]
- **System Architecture Components** — kindergarten_manager_system, nicegui_framework, ai_integration_layer, word_export_system, database_layer, authentication_system [EXTRACTED 0.75]
- **Current vs Future Service Architecture** — services_readme, integration_app, future_microservice [EXTRACTED 0.85]
- **Tested Layers of One-on-One Listening Subsystem** — tests_test_migrations_smoke, tests_test_indicator_repository, tests_test_listening_repository, tests_test_listening_image_repository, tests_test_date_service, tests_test_listening_client, tests_test_listening_service, tests_test_listening_exporter, tests_test_listening_ui_helpers, tests_test_export_repository, tests_test_image_processing [EXTRACTED 0.90]
- **Development Phases Covered by Listening Test Plan** — phase_p1, phase_p2, phase_p3, phase_p4, phase_p5, phase_p6, phase_p7, phase_p8a, phase_p8b, phase_p8d [EXTRACTED 0.95]
- **Architecture Decision Records** — docs_ADR_ADR-0002-single-user-ui-and-tenant-api [EXTRACTED 1.00]
- **F007 F008 F009 Agent Foundation acceptance** — specs_agent_foundation_spec_f007_cancellation_timeout_stale, specs_agent_foundation_spec_f008_openai_compatible_provider_adapter, specs_agent_foundation_spec_f008_six_closed_tool_executors, specs_agent_foundation_spec_f008_composition_daily_plan_ui, specs_agent_foundation_spec_f009_zero_persistence_matrix, specs_agent_foundation_spec_f009_linux_browser_mock, specs_agent_foundation_spec_f009_secure_real_model_acceptance [EXTRACTED 1.00]
- **Current Agent design documents** — docs_design_agent_runtime_f007_runtime, docs_design_data_model_f009_zero_persistence, docs_design_system_architecture_agent_composition [EXTRACTED 1.00]
- **Current architecture decision records** — docs_ADR_ADR-0002-single-user-ui-and-tenant-api, docs_adr_adr_0005_controlled_ai_agent_runtime_frozen_boundary [EXTRACTED 1.00]
- **Graphify Extraction Pipeline** — agents_skills_graphify_skill_md_ast_extraction, agents_skills_graphify_skill_md_semantic_extraction, agents_skills_graphify_skill_md_gemini_backend, agents_skills_graphify_skill_md_community_detection, agents_skills_graphify_skill_md_graph_json, agents_skills_graphify_skill_md_graph_report [EXTRACTED 1.00]
- **Graphify Reference Documentation** — agents_skills_graphify_references_extraction_spec_md, agents_skills_graphify_references_query_md, agents_skills_graphify_references_update_md, agents_skills_graphify_references_exports_md, agents_skills_graphify_references_add_watch_md, agents_skills_graphify_references_github_and_merge_md, agents_skills_graphify_references_hooks_md, agents_skills_graphify_references_transcribe_md [EXTRACTED 1.00]
- **Memory Bank Historical Documents** — memory-bank_api-integration, memory-bank_implementation-plan, memory-bank_overview [EXTRACTED 1.00]
- **One-on-One Listening Development Phases** — memory-bank_one-on-one-listening_progress_p0, memory-bank_one-on-one-listening_progress_p1 [INFERRED 0.75]
- **Homemade Teaching Toy Test Suite** — tests_test_class_repository, tests_test_homemade_teaching_repository, tests_test_homemade_teaching_client, tests_test_homemade_teaching_service, tests_test_homemade_teaching_exporter, tests_test_homemade_teaching_ui_helpers, tests_test_app_shell_menu, tests_test_export_repository [INFERRED 0.75]
- **Homemade Teaching Toy Test Stages** — memory-bank_homemadeteaching_test-plan_p1, memory-bank_homemadeteaching_test-plan_p2, memory-bank_homemadeteaching_test-plan_p3, memory-bank_homemadeteaching_test-plan_p4, memory-bank_homemadeteaching_test-plan_p5 [INFERRED 0.75]
- **Game Observation Subsystem Components** — memory_bank_game_observation_design, memory_bank_game_observation_progress, memory_bank_game_observation_design_game_observation, memory_bank_game_observation_design_game_observation_image, memory_bank_game_observation_design_invite_code, memory_bank_game_observation_design_call_ai_vision, memory_bank_game_observation_design_generate_observation [INFERRED 0.80]
- **Homemade Teaching Subsystem Components** — memory_bank_homemadeteaching_design, memory_bank_homemadeteaching_dev_plan, memory_bank_homemadeteaching_design_homemade_teaching_toy, memory_bank_homemadeteaching_design_generate_homemade_teaching [INFERRED 0.80]

## Communities (209 total, 52 thin omitted)

### Community 0 - "F009 Persistence Matrix"
Cohesion: 0.07
Nodes (69): AgentPanelStatus, Enum, str, Closed UI-facing states for the non-writing Agent panel., ProviderFinishReason, ProviderTurnResult, Normalized result returned by a provider adapter., Local ceilings that bound a serial provider/tool loop. (+61 more)

### Community 1 - "F008 Provider Adapter"
Cohesion: 0.06
Nodes (74): AgentProviderAdapterError, _build_payload(), _classify_transport_failure(), _descriptor_for_call(), _input_json_schema(), _InvalidWire, OpenAICompatibleAgentProvider, _parse_request_id() (+66 more)

### Community 2 - "Daily Plan Export"
Cohesion: 0.05
Nodes (47): _ensure_cache_fresh(), get_holiday_name(), get_legal_holidays_in_year(), get_special_day_tags(), is_adjusted_workday(), is_holiday(), is_near_holiday(), date (+39 more)

### Community 3 - "F007 Runtime Safety"
Cohesion: 0.10
Nodes (56): ClassAreasProjection, Allowlisted class-area facts; teacher identity is intentionally omitted., _agent(), BlockingThenSuccessProvider, CancellationDefyingExecutor, CancellationDefyingProvider, CancelledClock, _context() (+48 more)

### Community 4 - "F009 Browser Mock"
Cohesion: 0.08
Nodes (63): ArgumentParser, BaseHTTPRequestHandler, HTTPStatus, Namespace, _arguments(), _completed(), _draft(), _Handler (+55 more)

### Community 5 - "External REST API"
Cohesion: 0.06
Nodes (64): _build_domain_doc(), _build_from_scratch(), _clear_cell(), _domain_of_title(), export_batch_by_domain(), export_combined(), export_split_by_domain(), _extract_block() (+56 more)

### Community 6 - "Codebase Memory MCP"
Cohesion: 0.06
Nodes (37): get_env_path(), Path, 运行时 .env 文件读写工具。  路径策略： - PyInstaller 打包模式：可执行文件同级目录 - 开发 / Docker 模式：当前工作目录  这与, 返回 .env 文件的绝对路径（位于用户可写数据目录）。, 解析 .env 文件，返回 key-value 字典。      忽略空行与 # 开头的注释行。文件不存在时返回空字典。, 将 updates 中的 key-value 原子写入 .env，保留其余行不动。      若 .env 不存在则自动创建。写入失败时抛出 RuntimeEr, read_dot_env(), write_dot_env() (+29 more)

### Community 7 - "Observation Repository"
Cohesion: 0.07
Nodes (48): 审计日志：记录关键操作（登录、改密、AI 调用、Word 导出等）。  审计日志通过结构化 JSON logger 输出，统一携带 audit_action 与, ConfigError, 业务配置缺失时抛出：如用户尚未配置 AI Key。, AiApiKey, get_active_ai_key(), get_decrypted_key(), AsyncSession, ai_key_repository — AI API Key 数据访问层。  所有函数均携带 tenant_id + user_id 过滤，确保数据隔离。  安 (+40 more)

### Community 8 - "Daily Activity AI Client"
Cohesion: 0.08
Nodes (36): _build_collective_cell(), export_batch_daily_plans(), export_daily_plan(), _export_from_scratch(), _fill_fields_cell(), _fill_plain_cell(), _fill_process_cell(), _fill_template() (+28 more)

### Community 9 - "F008 Daily Plan UI"
Cohesion: 0.06
Nodes (41): _ActiveOperation, AgentPanelSnapshot, AgentPatchOperationSnapshot, AgentPatchSnapshot, _cancelled(), create_daily_plan_agent_controller(), DailyPlanAgentController, DailyPlanAgentCoordinator (+33 more)

### Community 10 - "F008 Tool Executors"
Cohesion: 0.11
Nodes (43): Permission, Permissions reserved by the Agent contract., plan_patch_matches_expected(), Verify every canonical PlanPatch field except its intentionally random id., Closed local tool-execution outcomes., ToolExecutionStatus, async_sessionmaker, _assert_envelope() (+35 more)

### Community 11 - "Authentication Service"
Cohesion: 0.08
Nodes (22): get_week_number(), get_weekday_cn(), is_within_semester(), is_workday(), pick_three_workdays(), date, 日期计算服务 — 纯函数，无 IO，无数据库依赖。, 返回 target_date 是开学后第几周（第 1 周起算）。      例：start_date=周一，target_date=同一天 → 第 1 周； (+14 more)

### Community 12 - "Export Record Repository"
Cohesion: 0.17
Nodes (46): _agent_runtime(), BlockingProvider, _context(), _draft_arguments(), MutableExecutorPayload, MutableText, MutableTuple, _plan_patch() (+38 more)

### Community 13 - "Listening Service Layer"
Cohesion: 0.10
Nodes (49): AuthError, 鉴权失败：token 无效、已过期、签名错误或用户名密码错误时抛出。          故意不区分"用户不存在"和"密码错误"，防止用户枚举攻击。, approve_user(), change_password(), create_user_by_admin(), list_users_for_admin(), login(), AsyncSession (+41 more)

### Community 14 - "Observation Word Export"
Cohesion: 0.06
Nodes (39): _fingerprint(), datetime, UUID, Build short-lived, frozen Agent contexts from the F004 READ seam., Read and freeze facts in the contract-defined order., _utc_now(), CalendarEvaluationProjection, DailyPlanContextProjection (+31 more)

### Community 15 - "Encryption Utilities"
Cohesion: 0.06
Nodes (47): call_ai_text(), AsyncClient, 发送 Chat Completions 请求，返回纯文本 content 字符串。      与 call_ai() 的区别：不强制 json_object 格, _build_prefix(), _build_user_content(), generate_activity(), _holiday_hint(), 一日活动生成客户端 — 包含 5 种活动类型的内置默认提示词。  任务类型对应关系： - morning_exercise  →  晨间活动 - morning (+39 more)

### Community 16 - "User Bootstrap"
Cohesion: 0.04
Nodes (47): Cypher Query Language, detect_changes, Edge Types, get_architecture, get_code_snippet, query_graph, search_graph, codebase-memory 14 MCP Tools (+39 more)

### Community 17 - "Database Models"
Cohesion: 0.10
Nodes (44): delete_indicator_results_by_record(), delete_record(), get_record_by_id(), list_domains_by_record(), list_indicator_results(), list_records(), Any, AsyncSession (+36 more)

### Community 18 - "Migration Smoke Tests"
Cohesion: 0.08
Nodes (25): _CurrentContextState, Application-owned current stamp plus a live page-scope predicate., AgentContextStamp, AgentRuntime, _failure(), _host_task_is_cancelling(), _log_provider_rejection(), Any (+17 more)

### Community 19 - "Export Filename Helpers"
Cohesion: 0.06
Nodes (31): Base, _build_engine(), _resolve_database_url(), AiApiKey — AI 接口 Key 数据模型。  安全约束： - `api_key_encrypted` 字段仅存密文，明文禁止入库、禁止写入日志。 -, GameObservationImage — 游戏观察图片数据模型。  可插拔存储：本期实现 MySQL BLOB 后端（blob_content 存压缩后二进, GameObservation — 游戏观察记录数据模型。  每条记录对应教师的一次游戏观察，包含元数据（日期/环境/人员） 和 AI 生成的四段内容（观察目标, IndicatorCatalog — 一对一倾听指标目录（参考数据，迁移预置）。  按 (grade, term, domain) 组织一级/二级指标及三档（★, ListeningDomain — 一对一倾听单领域内容。  每条 listening_record 对应 5 条本表（健康/语言/社会/艺术/科学各一）。 年 (+23 more)

### Community 20 - "Config Secrets Tests"
Cohesion: 0.10
Nodes (25): AgentContext, Name, permission, and closed input/output shapes exposed by the registry., Short-lived, frozen facts for one operation and turn., ToolDescriptor, AgentToolRegistry, AgentToolRejected, ValueError, Closed registry for the first Agent Foundation slice. (+17 more)

### Community 21 - "App Entry and UI"
Cohesion: 0.08
Nodes (23): list_versions(), AsyncSession, 将指定版本设为激活，其余版本设为 inactive。      Args:         session: 异步数据库会话。         tenant_i, 返回指定任务类型的所有版本，按版本号降序排列。      Args:         session: 异步数据库会话。         tenant_id:, 保存新版本提示词，自动递增版本号并将旧激活记录设为 inactive。      Args:         session: 异步数据库会话。, rollback_to_version(), save_new_version(), 提示词仓库层集成测试。  使用 SQLite 内存库 fixture（来自 conftest.py），与真实 MySQL 完全隔离。 (+15 more)

### Community 22 - "Course Review Export"
Cohesion: 0.08
Nodes (35): CompressedImage, _clamp_star(), generate_domain_content(), 将星级归一化为 1~3 的整数，非法值回退默认。, 调用视觉 AI 生成某领域的一对一倾听内容，返回结构化结果。 Args: session: 异步数据库会话。 tenant_id / user_id:…, Phase P5: Service Layer, Phase P8a: Backend Assembly, _ai_return() (+27 more)

### Community 23 - "API Key Auth"
Cohesion: 0.09
Nodes (22): NiceGUI - Python Web Framework, Read-only daily-plan Agent panel. The panel renders detached suggestions only.…, Render and return the non-writing daily-plan Agent panel., render_daily_plan_agent_panel(), DatePanel, DateSelection, DateSelectionGuard, 日期选择面板组件（可复用）。 功能： - 日期选择器（NiceGUI ui.date） - 选择日期后自动计算并显示：第几周、周几、是否工作日 -… (+14 more)

### Community 24 - "Image Storage Backend"
Cohesion: 0.09
Nodes (30): AsyncSessionUnitOfWork, AsyncSession, SQLAlchemy 异步会话的最外层 Unit of Work。, 在一个 use-case 结束时统一提交，任一步失败时统一回滚。, delete_images_by_record(), listening_image_repository — 一对一倾听图片数据访问层。, 删除某记录下的所有图片（tenant 隔离）。, delete_domains_by_record() (+22 more)

### Community 25 - "AI Key Repository Tests"
Cohesion: 0.11
Nodes (35): _add_images_to_cell(), _build_from_scratch(), _clear_cell(), export_observation(), _fill_template(), Document, Path, 游戏观察记录 Word 导出器。 主方案：打开模板 `templates/ObservationRecord.docx`， 替换标题中的 'xx'… (+27 more)

### Community 26 - "REST API Tests"
Cohesion: 0.11
Nodes (29): hash_password(), 将明文密码哈希为 Argon2 格式字符串。, verify_password(), ensure_default_user(), AsyncSession, 应用启动引导：确保默认用户存在。  单用户模式下，系统启动时自动在 user 表中创建默认管理员账号。 如果已存在则跳过（幂等）。, 确保默认用户存在，不存在则创建。已存在则跳过。, run_bootstrap() (+21 more)

### Community 27 - "Observation Image Repository"
Cohesion: 0.09
Nodes (32): GameObservation, GameObservationImage, PromptTemplate, Phase P1: Migration & Seed, asyncio, Phase B — 数据模型冒烟测试（ORM + SQLite in-memory）。 测试策略： - 用 async_session…, GameObservation 可插入并按 id 查询。, GameObservation.tenant_id 非空约束生效。 (+24 more)

### Community 28 - "Auth and User Admin"
Cohesion: 0.12
Nodes (29): canonical_sha256(), Canonical hashing shared by F004 projection and context fingerprints., Hash supported DTO values using stable UTF-8 JSON encoding., build_plan_patch(), build_plan_patch_from_arguments(), DraftPatchOperation, DraftPatchProposal, _normalize_operations() (+21 more)

### Community 29 - "Indicator Repository"
Cohesion: 0.09
Nodes (30): build_batch_export_filename(), build_export_filename(), default_year_month(), distribute_images_by_filename(), format_record_summary(), format_stage_label(), infer_age_by_grade(), one_on_one_listening_page() (+22 more)

### Community 30 - "Vision AI Client"
Cohesion: 0.11
Nodes (24): log_audit(), 记录一条审计日志。      Args:         action: 操作标识（如 login_success / change_password / ai, bootstrap_admin(), _main(), _prompt_password(), _prompt_str(), 系统管理员初始化脚本。  模式：   --init           创建 sys_admin 账号（默认模式）   --reset-password 重置, --init 模式：创建 sys_admin 账号。 (+16 more)

### Community 31 - "AI Key Repository"
Cohesion: 0.08
Nodes (25): AgentTurnStatus, _freeze_dataclass_field(), _freeze_dataclass_value(), _freeze_json(), _freeze_tool_value(), _InvalidToolPayload, _OperationStopped, _PortFailure (+17 more)

### Community 32 - "F008 Daily Plan UI"
Cohesion: 0.17
Nodes (24): agent_session_factory(), BlockingProvider, _composition(), _controller(), ImmediateProvider, Any, asyncio, fixture (+16 more)

### Community 33 - "AI Client Base"
Cohesion: 0.18
Nodes (27): Any, _build_from_scratch(), _clear_cell(), _clear_paragraph(), export_course_review_activity(), _fill_template(), _get_bool(), _get_value() (+19 more)

### Community 34 - "Admin Bootstrap Script"
Cohesion: 0.13
Nodes (14): ApiPrincipal, _build_signing_string(), get_api_principal(), parse_api_keys(), Request, 对外 REST API 鉴权：API Key + 可选 HMAC 签名。  鉴权模型（服务间调用）： 1. **API Key**（必填）：调用方在 `X-Ap, 解析 `API_KEYS` 配置为 {api_key: tenant_id} 映射。      格式："key1:1,key2:2"；忽略空段与格式非法段（te, 校验 HMAC-SHA256 请求签名与时间戳新鲜度。 (+6 more)

### Community 35 - "User Registration"
Cohesion: 0.12
Nodes (19): _build_fernet(), decrypt(), encrypt(), 应用层对称加密工具（Fernet）。  密钥来源：Settings.ENCRYPTION_KEY（原始字符串，UTF-8 编码后取前 32 字节， 再经 bas, 将环境变量中的原始字符串密钥转换为 Fernet 实例。      Fernet 要求 32 字节的 URL-safe base64 编码密钥（共 44 个字符, 加密明文字符串，返回 URL-safe base64 密文字符串。      Args:         plain_text: 待加密的明文（禁止在调用方写入, 解密密文字符串，还原为原始明文。      Args:         cipher_text: 由 `encrypt()` 生成的密文字符串。      Re, CryptoError (+11 more)

### Community 36 - "App Shell UI"
Cohesion: 0.11
Nodes (27): compress_image(), normalize_to_landscape(), 图片压缩处理模块（游戏观察子系统）。  `compress_image` 将任意图片字节压缩至指定大小上限： - 超限时等比缩放 + 逐步降低 JPEG 质量直, 将图片统一为横版（宽 ≥ 高）。      处理步骤：       1. 按 EXIF 方向校正（手机照片常见）。       2. 透明通道转白底 RGB。, 将图片字节压缩至 max_bytes 以内。      Args:         data: 原始图片字节（JPEG / PNG / WebP 等 Pillo, Phase P8d: Image Processing, _make_jpeg_bytes(), _make_large_jpeg_bytes() (+19 more)

### Community 37 - "Env File Utilities"
Cohesion: 0.13
Nodes (27): delete_observation(), get_observation_by_id(), list_observations(), Any, AsyncSession, date, observation_repository — 游戏观察记录数据访问层。 所有查询强制携带 tenant_id 过滤，确保多租户数据隔离。, 更新指定观察记录的字段（传入任意关键字参数），返回是否成功。 (+19 more)

### Community 38 - "Observation AI Client"
Cohesion: 0.11
Nodes (20): ABC, ImageStorageBackend, 存储图片字节，返回存储引用 dict。          Returns:             dict，键因后端而异（blob_backend 含 blo, 从存储引用还原图片字节。          Args:             stored: 与 put 返回格式相同的 dict。          Ret, 可插拔图片存储后端抽象。      put / get 与数据库 session 解耦：     - put 返回 stored_ref dict，由 repo, BlobImageStorage, MySQL BLOB 图片存储后端。  put/get 只操作内存 dict，实际 DB 写入由 repository 层完成。, MySQL BLOB 后端：图片二进制存入 game_observation_image.blob_content。 (+12 more)

### Community 39 - "Homemade Teaching Export"
Cohesion: 0.10
Nodes (17): AsyncSession, tests/test_ai_key_repository.py — ai_key_repository 集成测试。 使用 SQLite…, 查询从未保存过 Key 的租户应返回 None。, 入库后 api_key_encrypted 不能与明文相同。, 新保存的记录 is_active 应为 True。, api_base_url 字段应与传入值一致。, 保存后 get_active_ai_key 可取回该记录。, model_name 字段应与传入值一致。 (+9 more)

### Community 40 - "User Repository"
Cohesion: 0.22
Nodes (26): _cleanup_temp_artifact(), _create_posix_file(), _harden_regular_fd(), _parse_kv_text(), _path_entry_exists(), _path_matches_identity(), _posix_lifecycle_file_lock(), _posix_open_flags() (+18 more)

### Community 41 - "Project Documentation"
Cohesion: 0.14
Nodes (23): SQLAlchemy - ORM, add_image(), delete_images_by_observation(), get_image(), list_images_by_observation(), AsyncSession, observation_image_repository — 游戏观察图片数据访问层。, 新增一张观察图片并 flush，提交由最外层 use-case 负责。 (+15 more)

### Community 42 - "AI Endpoint Verification"
Cohesion: 0.17
Nodes (15): get_logger(), 年龄适配 AI 客户端。  将活动过程原文按年龄段（小班/中班/大班）改写，返回改写后文本。  输出 Schema：     {"adapted_process, _make_retry_decorator(), AI 客户端基础模块 — 通用 Chat Completions 调用。  所有 AI 调用必须通过此模块，禁止在 service 层直接发 HTTP 请求。, 构造 tenacity 重试装饰器：最多 3 次，指数退避 2s → 4s → 8s。, 教案拆分 AI 客户端。  调用 OpenAI 兼容接口，将完整教案文本拆分为结构化字段。  输出 Schema（5 个必填键）：     activity_g, _detect_mime(), _image_to_data_url() (+7 more)

### Community 43 - "Daily Plan Repository"
Cohesion: 0.12
Nodes (23): ExportRecord, 导出记录数据模型。  对应数据库表：export_records 记录每次 Word 导出操作的元信息（文件名、路径、关联教案）。 导出记录为只增不改（immu, AsyncSession, 写入一条导出记录。      Args:         session: 异步数据库会话（调用方负责事务管理）。         tenant_id: 机构, save_export_record(), tests/test_export_repository.py — 导出记录仓库层测试。  使用 SQLite 内存库（async_session fixtur, 写入倾听导出记录时，listening_record_id 字段正确持久化。, 未传 listening_record_id 时，字段默认为 None（向后兼容）。 (+15 more)

### Community 44 - "Course Review Activity"
Cohesion: 0.16
Nodes (24): IndicatorCatalog, get_indicator_by_id(), list_available_stages(), list_indicators(), list_indicators_by_ids(), AsyncSession, indicator_repository — 指标目录数据访问层。  只读参考数据查询（指标目录按 tenant_id + grade + term + dom, 查询某 (年级, 学期, 领域) 的全部二级指标，按 sort_order 升序。 (+16 more)

### Community 45 - "System Architecture"
Cohesion: 0.11
Nodes (7): 对外 REST API 路由集成测试（httpx ASGITransport + SQLite 内存库）。, API Key 代表 tenant；不传 user 过滤时可读本 tenant 内多个教师。, _seed(), TestAuth, TestConfigEndpoints, TestDailyPlans, TestSignature

### Community 46 - "API Response Schemas"
Cohesion: 0.12
Nodes (23): create_user(), list_users_by_tenant(), 在指定租户中更新用户启停状态，返回是否更新成功。, 创建用户并持久化到数据库，返回已持久化的 User 对象。, 在指定租户中更新用户哈希密码，返回是否更新成功。, 返回指定租户下的用户列表（按创建时间倒序）。, update_password(), update_user_active() (+15 more)

### Community 47 - "Audit and User Admin"
Cohesion: 0.15
Nodes (20): create_access_token(), decode_access_token(), JWT access token 生成与解码工具。, 生成 JWT access token。 payload 字段： - sub: str(user_id) - tenant_id: int - role:…, 解码并验证 JWT token，返回 payload 字典。 token 过期、签名无效等情况统一抛出 AuthError。, _get_current_user(), 系统管理员账号管理页面（路由：/user-admin）。  阶段二能力： - 系统管理员创建账号 - 列表筛选与分页 - 账号启停 - 管理员重置密码, user_admin_page() (+12 more)

### Community 48 - "Course Review Repository"
Cohesion: 0.13
Nodes (22): AiCallError, Exception, AI 接口调用失败时抛出：HTTP 4xx/5xx、网络超时、超过重试次数等。, call_ai_vision(), _make_retry_decorator(), AsyncClient, 构造 tenacity 重试装饰器：最多 3 次，指数退避 2s → 4s → 8s。, 发送多模态 Chat Completions 请求，返回解析后的 dict。      Args:         messages: 消息列表，content (+14 more)

### Community 49 - "Startup Migrations"
Cohesion: 0.15
Nodes (22): AppError, 通用业务异常：输入非法、文件格式错误等非 AI / 非鉴权类业务错误。, _build_context_text(), generate_listening_domain(), 调用视觉 AI 生成某领域的一对一倾听结构化内容。      Args:         images: 该领域绘画图片字节列表（经压缩后的 bytes，至少, 构造给 AI 的说明文本（上下文 + 二级指标清单）。, Phase P4: AI Client, _full_result() (+14 more)

### Community 50 - "Holiday API Client"
Cohesion: 0.18
Nodes (21): delete_daily_plan(), get_daily_plan_by_date(), get_daily_plan_by_id_for_tenant(), get_daily_plan_by_id_for_user(), _list_daily_plans(), list_daily_plans_for_tenant(), list_daily_plans_for_user(), AsyncSession (+13 more)

### Community 51 - "Class Config Settings"
Cohesion: 0.10
Nodes (16): AgentProviderConfig, _BoundProvider, _default_provider_factory(), ProviderFactory, datetime, Protocol, SessionFactory, Delegate through the one runtime without retaining credentials after a run. (+8 more)

### Community 52 - "Auth Middleware"
Cohesion: 0.22
Nodes (22): PlanSection, One allowlisted, bounded daily-plan section., _assert_rejected(), _context(), _patch_module(), _proposal(), asyncio, AsyncSession (+14 more)

### Community 53 - "Listening Data Models"
Cohesion: 0.13
Nodes (19): FastAPI - Web Framework, ApiPrincipal, get_db(), AsyncSession, 对外 REST API 的 FastAPI 依赖。, 提供独立的异步数据库会话（只读查询，无需提交）。      测试可通过 ``app.dependency_overrides[get_db]`` 注入内存库会话, get_daily_plan(), health() (+11 more)

### Community 54 - "Setup State Management"
Cohesion: 0.26
Nodes (13): ClassConfigOut, DailyPlanListOut, DailyPlanOut, HealthOut, PageMeta, 对外 REST API 响应模型（Pydantic）。  仅暴露教学计划相关的只读字段；不包含密钥、密码等敏感信息。, SemesterOut, ClassConfig (+5 more)

### Community 55 - "REST API Routes"
Cohesion: 0.11
Nodes (19): Settings, BaseSettings, 回归测试：config.py 中密钥自动生成与 BOOTSTRAP_ADMIN_* 字段。 核心目标： 1. Settings…, 并发启动都只能返回同一组已持久化密钥，不能各自成功后丢失一组。, BOOTSTRAP_ADMIN_ENABLED 默认 False。, BOOTSTRAP_ADMIN_TENANT_ID 默认 1。, BOOTSTRAP_ADMIN_USERNAME 默认 'sysadmin'。, BOOTSTRAP_ADMIN_PASSWORD 默认空字符串。 (+11 more)

### Community 56 - "Password Hashing"
Cohesion: 0.16
Nodes (20): add_image(), get_image(), list_images_by_record(), AsyncSession, 新增一张倾听图片并 flush，提交由最外层 use-case 负责。, 查询某记录下的图片（可选按领域过滤），按领域 + image_index 升序。, 按 id 查询单张图片，强制 tenant_id 过滤。, aiosqlite In-Memory Database Fixture (+12 more)

### Community 57 - "Runtime Path Utilities"
Cohesion: 0.16
Nodes (18): CalendarDayType, ClosedToolOutputSchema, Enum, str, Closed contracts for the authorized Agent Foundation slices., Exact application DTO kind accepted back from a local executor., Return whether every field is a closed, deeply immutable DTO value., Locally normalized calendar result for the closed READ surface. (+10 more)

### Community 58 - "Homemade Teaching Repository"
Cohesion: 0.14
Nodes (19): compute_diff(), 差异比对服务 — 使用 difflib 对原文与改写文进行逐句比对。  分句规则：以句号（。）、问号（？）、感叹号（！）、换行符为分隔符， 保留分隔符到句子末尾, 将文本按标点符号或换行符拆分为句子列表，过滤空串。, 对原文与改写文按句比对，返回带 changed 标记的句子列表。      Args:         original: 活动过程原文。         ad, _split_sentences(), tests/test_diff_service.py — 差异比对服务测试。, 完全相同的文本，所有句子 changed 为 False。, 修改一句后，该句 changed 为 True，其余句子不变。 (+11 more)

### Community 59 - "F007 F008 F009 Foundation"
Cohesion: 0.16
Nodes (21): Current Agent Foundation status, Controlled AI Agent Runtime decision, Agent Runtime design, Agent data persistence boundary, Agent application composition, F009 manual acceptance guide, Agent Foundation roadmap milestone, Quality workflow gate (+13 more)

### Community 60 - "Prompt Repository"
Cohesion: 0.17
Nodes (19): call_ai(), 发送 Chat Completions 请求，返回解析后的 dict。      Args:         messages: 消息列表，格式为 [{"rol, Response, _make_error_response(), _make_openai_response(), asyncio, tests/test_ai_client_base.py — AI 客户端基础模块测试。 使用 httpx.MockTransport 隔离真实 HTTP…, HTTP 500 时重试后抛出 AiCallError。 (+11 more)

### Community 61 - "CI Quality Workflow"
Cohesion: 0.14
Nodes (19): _build_context_text(), _detect_mime(), generate_observation(), _image_to_data_url(), 将上下文 dict 转为给 AI 的说明文本。, 根据文件头检测图片 MIME 类型，无法识别时默认 image/jpeg。, 将图片字节转为 base64 data-url 字符串。, 调用视觉 AI 生成游戏观察记录四段内容。      Args:         images: 图片字节列表（1~3 张，经压缩后的 bytes）。 (+11 more)

### Community 62 - "Listening Subsystem Plan"
Cohesion: 0.24
Nodes (18): _build_from_scratch(), _clear_cell(), export_homemade_teaching(), _fill_template(), _get_value(), Any, Document, Path (+10 more)

### Community 63 - "Age Adaptation Client"
Cohesion: 0.15
Nodes (18): create_pending_user(), get_user_by_id(), AsyncSession, 创建待审核用户（is_active=False，role=teacher），用于自助注册流程。      Args:         session: 异步数据, 在指定租户下按 ID 查询用户，不存在时返回 None。, update_display_name(), 更新用户个人资料的显示名。 Args: session: 异步数据库会话。 tenant_id: 租户 ID。 user_id: 用户 ID。…, update_profile_display_name() (+10 more)

### Community 64 - "Holiday Client"
Cohesion: 0.17
Nodes (15): AiEndpointVerifier, AiEndpointCheck, check_ai_endpoint(), OpenAI-compatible model catalog connection adapter., Sanitized endpoint check result with no response body or credential data., Call the provider's ``/models`` endpoint and return a sanitized result., AsyncSession, 验证当前用户已保存的 AI 配置，不把明文 Key 返回给 UI。 (+7 more)

### Community 65 - "Observation UI Helpers"
Cohesion: 0.12
Nodes (16): AsyncSession, ImageStorageBackend, 事务写入观察记录 + 图片，返回 observation_id。 Args: session: 异步数据库会话。 obs_data: 观察记录字段…, save_observation_with_images(), CompressedImage, _FailOnSecondPutStorage, tests/test_observation_service.py — 游戏观察服务层测试。 测试覆盖： 1. 未配置视觉 Key → ConfigError…, 保存观察记录 + 图片，取回记录和有序图片均一致。 (+8 more)

### Community 66 - "Application Config"
Cohesion: 0.14
Nodes (14): app_shell(), get_display_name(), 返回顶栏显示名：优先 display_name，回退 username。 Args: user: 包含用户信息的字典，通常来自…, 统一布局：左侧分组菜单 + 顶栏。 用法:: async with app_shell(user, active="daily-plan"): #…, game_observation_page(), page, home_page(), page (+6 more)

### Community 67 - "Adjusted Workday Check"
Cohesion: 0.11
Nodes (19): 课程审议 AI 结构化 JSON 合约, 课程审议持久化与历史导出, 课程审议 Word 模板映射, 课程审议 AI 客户端与服务层, 课程审议分阶段交付, 课程审议 Word 导出阶段, 课程审议完整实现, 课程审议自动测试证据 (+11 more)

### Community 68 - "Menu Items Logic"
Cohesion: 0.12
Nodes (18): AI Integration Layer, Authentication System (JWT + RBAC), Course Review Activity Subsystem, Daily Plan Subsystem, Database Layer (MySQL/SQLite), Game Observation Subsystem, Homemade Teaching Toy Subsystem, Kindergarten Management System (+10 more)

### Community 69 - "Course Review UI Helpers"
Cohesion: 0.26
Nodes (15): CourseReviewActivity, 课程审议记录。      每条记录保存一次课程审议生成与教师编辑后的结果。班级、年龄段与教师姓名     采用冗余快照，避免后续系统设置变更影响历史导出。, create_course_review_activity(), delete_course_review_activity(), get_course_review_activity(), list_course_review_activities(), AsyncSession, 删除课程审议记录，强制 tenant_id + user_id 双重过滤。 (+7 more)

### Community 70 - "Database Config Tests"
Cohesion: 0.21
Nodes (14): 共享布局组件 app_shell。 提供统一的左侧导航菜单 + 顶栏，供所有页面复用。 纯函数（可在 NiceGUI 渲染外调用，支持单测）： -…, 渲染顶栏和左侧抽屉（无 context manager 版本）。 供已有页面调用：在页面函数开头调用一次，内容随后在同一层级放置。 Args: user:…, render_shell(), clean_filename_part(), format_setting_summary(), 校验单次或单领域图片数量是否在 1 至 3 张。, validate_generation_context(), validate_image_count() (+6 more)

### Community 71 - "Daily Activity Service"
Cohesion: 0.15
Nodes (13): build_sync_url(), _get_alembic_ini_path(), _get_alembic_script_location(), 应用启动模块：自动执行 Alembic 数据库迁移。 支持三种运行模式： - 开发模式（python -m…, 将异步驱动 URL 转换为 Alembic 所需的同步驱动 URL。…, 在应用启动时自动执行 alembic upgrade head。 桌面、开发与服务器模式统一 fail-closed：迁移失败时记录异常并重新抛出，…, run_startup_migrations(), 显式配置 MySQL 异步 URL 时，迁移侧应转换为同步 pymysql 驱动且库名不变。 (+5 more)

### Community 72 - "Date Panel Component"
Cohesion: 0.18
Nodes (7): DailyPlanAgentPanel, date, Invalidate suggestions based on an authoritative plan before mutation., Cancel connection-local work while keeping the controller reusable., Release page-local state and cancel its exact in-flight operation., NiceGUI rendering facade around one page-local Agent controller., Synchronously invalidate old work before date-side awaits begin.

### Community 73 - "Listening Migration Tests"
Cohesion: 0.15
Nodes (17): _assert_failure_is_sanitized(), _capture_settings_error(), _install_after_open_write_failure(), parametrize, 允许安全打开，再在 Settings 期间的第一笔正文写入处失败。, FIFO 必须以 non-blocking 方式打开并在任何正文读取前拒绝。, 目录等非普通文件不得被当作缺失配置后继续启动。, 生成的两个密钥写入失败时必须向上传播、清理并保持脱敏。 (+9 more)

### Community 74 - "Course Review Service"
Cohesion: 0.20
Nodes (17): _assert_non_posix_regular_file_contract(), _file_digest(), _install_content_read_probe(), _mode(), Path, 只验证跨平台功能，不把 POSIX mode 当作 Windows DACL 证据。, POSIX 新文件即使在 umask=0 下也不得短暂暴露为 group/other 可读。, 既有 0664 普通文件必须先纠权再读，且不得重写其正文。 (+9 more)

### Community 75 - "Course Review AI Client"
Cohesion: 0.16
Nodes (11): AuthMiddleware, Request, 路由守卫中间件（已禁用 — 单用户模式无需登录）。  保留模块以便后续恢复登录功能。当前为直通中间件，不做任何鉴权检查。 根路径 (/) 重定向到 /home。, 单用户模式：仅将根路径重定向到 /home，其余请求直接放行。, BaseHTTPMiddleware, asyncio, tests/test_middleware.py — 单用户模式路由中间件测试。 验证： - 根路径 (/) 重定向到 /home -…, 中间件可被实例化（接收 ASGI app 参数）。 (+3 more)

### Community 76 - "Special Day Tags"
Cohesion: 0.28
Nodes (13): HomemadeTeachingToy, 教师自制教玩具记录。      每条记录保存一次 AI 生成或教师编辑后的教玩具方案。班级与教师姓名     采用冗余快照，避免后续设置变更影响历史导出。, create_homemade_teaching_toy(), delete_homemade_teaching_toy(), get_homemade_teaching_toy(), list_homemade_teaching_toys(), AsyncSession, 按 id 查询记录，强制 tenant_id 过滤。 (+5 more)

### Community 77 - "Near Holiday Check"
Cohesion: 0.16
Nodes (15): ListeningDomain, ListeningImage, ListeningIndicatorResult, ListeningRecord, P1 — 一对一倾听数据模型冒烟测试（ORM + SQLite in-memory）。  用 async_session fixture（create_all）, IndicatorCatalog 可创建并保存三档标准。, ListeningRecord 可创建；adult_count 默认 1。, ListeningDomain 支持领域级年月与 3 个日期。 (+7 more)

### Community 78 - "Prompt Version Save"
Cohesion: 0.21
Nodes (15): 将完整教案文本拆分为结构化字段。      Args:         raw_text: 用户粘贴的完整教案文本。         api_base_url:, split_lesson_plan(), _make_client(), AsyncClient, tests/test_lesson_plan_client.py — 教案拆分客户端测试。  使用 httpx.MockTransport 隔离真实 HTTP, AI 返回空 dict 时，抛出 AiParseError。, AI 返回额外字段时，只保留 5 个必要键。, 正常响应时，返回包含全部 5 个键的 dict。 (+7 more)

### Community 79 - "Prompt Version Rollback"
Cohesion: 0.12
Nodes (14): has_any_user(), 检查指定租户是否已有任意用户，用于判断注册者是否是第一个用户。, 自助注册： - 若系统（tenant_id=1）尚无任何用户，注册者自动成为 sys_admin（is_active=True，可立即登录）。 - 否则创建…, register_user(), 注册页面（路由：/register）。  功能：   - 用户自助注册（无需邀请码，无需登录即可访问）   - 若系统尚无用户，第一个注册者自动成为 sys_a, 空库第一个注册用户自动成为 sys_admin（is_active=True），可立即登录。, 已有用户后，第二个注册者成为 teacher（is_active=False），需管理员审核。, 同用户名注册两次时抛出 ValueError。 (+6 more)

### Community 80 - "Semester Repository"
Cohesion: 0.26
Nodes (12): get_class_config(), list_class_configs_for_tenant(), AsyncSession, 查询当前用户的班级配置，若不存在返回 None。, 保存班级配置：若已存在则更新，否则新建。 每个用户只保留一条班级配置记录（最新）。, API tenant 投影；可在当前 tenant 内按 user_id 进一步筛选。, upsert_class_config(), 配置页面（路由：/settings）。 包含配置区块： 1. 学期配置：学期名称、开始日期、结束日期 2. 班级配置：年级、班级名称、区域内容、户外内容 3.… (+4 more)

### Community 81 - "Homemade Teaching AI Client"
Cohesion: 0.18
Nodes (9): get_menu_items(), 根据角色返回可见菜单项列表，每项含 selected 标记。 Args: role: 用户角色，如 'teacher' / 'teaching_admin'…, 测试 app_shell 纯函数逻辑。 测试策略：将菜单项生成和显示名逻辑抽为纯函数，脱离 NiceGUI 渲染独立测试。, role=teacher 时，菜单包含核心项，不含已移除项。, 单用户模式下 sys_admin 与 teacher 看到相同菜单。, 所有角色均可见核心菜单项：每日活动计划、设置、提示词管理。, 传入 active='daily-plan' 时，该菜单项 selected=True，其他项 selected=False。, 不传 active 时，所有菜单项 selected=False。 (+1 more)

### Community 82 - "Observation Generation Service"
Cohesion: 0.15
Nodes (11): build_homemade_teaching_filename(), P0 - Documentation & Template Analysis, P1 - Teacher Name Setting, P2 - Data Model & Repository, P3 - AI Client & Service, P4 - Word Export, P5 - UI Page & Navigation, P6 - Documentation & Regression (+3 more)

### Community 83 - "UI Helper Functions"
Cohesion: 0.23
Nodes (14): _make_mock_ai_client(), _make_mock_ai_key(), asyncio, tests/test_lesson_plan_service.py — 教案拆分服务测试。 使用 Mock 隔离 AI 调用和数据库访问。, 用户未配置 AI Key 时，抛出 ConfigError。, 构造返回预设响应的 Mock httpx 客户端。 客户端根据请求 URL 或请求体内容区分拆分/适配调用。 实际上两次调用会轮流使用 responses…, DB 中存在激活提示词时，服务层应使用 DB 中的内容，而非内置默认。, DB 中无激活提示词时，服务层应传 None 给客户端（客户端自行使用内置默认）。 (+6 more)

### Community 84 - "Prompt Version Listing"
Cohesion: 0.25
Nodes (13): adapt_activity_process(), 将活动过程按年龄段改写。      Args:         original: 活动过程原文。         grade: 年龄段，如"小班"、"中班"、, _make_client(), AsyncClient, tests/test_adapt_client.py — 年龄适配客户端测试。, AI 返回缺少 adapted_process 字段时，抛出 AiParseError。, 原文为空字符串时，不发请求直接抛出 AiParseError。, 传入自定义 system prompt 时，正常调用不报错。 (+5 more)

### Community 85 - "Agent Runtime Tools"
Cohesion: 0.18
Nodes (10): build_export_filename(), 构造导出文件名。 格式：{tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx, 校验大环境值是否合法（仅允许 户外/室内/公共）。, validate_big_env(), tests/test_observation_ui_helpers.py — 游戏观察 UI 工具函数测试。  测试覆盖（3 项纯函数）：   1. 导出文件名, 文件名格式为 {tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx。, 非法大环境值校验失败（返回 False 或抛异常）。, test_build_export_filename_format() (+2 more)

### Community 86 - "Listening Service Tests"
Cohesion: 0.14
Nodes (14): _make_settings(), 在受控环境下构造 Settings 实例，不读取磁盘 .env 文件。, 无任何配置时，Settings() 应成功实例化（修复必填字段导致的启动崩溃）。, ENCRYPTION_KEY 为空时应自动生成非空值。, JWT_SECRET 为空时应自动生成非空值。, 已设置的 ENCRYPTION_KEY 不应被自动生成逻辑覆盖。, 首次生成的密钥写入持久化文件，第二次实例化时读回相同值。, 自动生成的 ENCRYPTION_KEY 应能被 app.core.crypto 正常使用。 (+6 more)

### Community 87 - "Homemade Teaching Service"
Cohesion: 0.24
Nodes (12): _load_mock_helper(), _load_seed_helper(), _mock_payload(), parametrize, RuntimeError, F009 Review RED: verified worktree imports must precede app imports., Sentinel proving the test did not cross into application imports., _StopBeforeApplicationImport (+4 more)

### Community 88 - "Dependency Security Audit"
Cohesion: 0.36
Nodes (10): _field_names(), asyncio, AsyncSession, DailyPlan, F004 public RED tests for frozen, actor-scoped READ projections., _seed_actor_data(), test_calendar_projection_distinguishes_known_and_degraded_results(), test_context_and_class_area_projections_are_frozen_and_cropped() (+2 more)

### Community 89 - "Game Observation Docs"
Cohesion: 0.17
Nodes (9): migrated_db(), P1 — 一对一倾听迁移与种子集成测试。  在临时 sqlite 文件库上实际执行 `alembic upgrade head`，验证： - 5 个新表创建成功, export_records 含 listening_record_id 列。, 种子 JSON：5 领域共 30 个二级指标，每个含 3 档标准、sort_order 连续。, 在临时 sqlite 文件库上执行 alembic upgrade head，返回库路径。, 每条种子三档标准非空，tenant_id=1，max_stars=3。, test_export_records_has_listening_col(), test_indicator_seed_integrity() (+1 more)

### Community 90 - "Image Config Tests"
Cohesion: 0.36
Nodes (10): AiParseError, AI 返回内容解析失败时抛出：JSON 格式非法、缺少必要字段等。, _build_user_content(), generate_homemade_teaching(), _make_client(), AsyncClient, test_generate_homemade_teaching_filters_extra_keys(), test_generate_homemade_teaching_invalid_payload_raises() (+2 more)

### Community 91 - "Prompt Editor UI"
Cohesion: 0.24
Nodes (9): get_current_user(), 单用户模式：提供固定的默认用户上下文。  取消登录功能后，所有页面通过此模块获取当前用户信息， 而非从 JWT token 中解析。, 返回当前用户信息字典（单用户模式下始终返回默认管理员）。, prompt_mgmt_page(), page, tests/test_user_context.py — 单用户上下文测试。  覆盖： - get_current_user 返回正确的默认用户字典 - 返回值, 每次调用返回独立副本，修改不影响后续调用。, test_returns_copy_each_call() (+1 more)

### Community 92 - "Root Redirect Page"
Cohesion: 0.44
Nodes (10): _build_user_content(), generate_course_review_activity(), _make_client(), AsyncClient, test_generate_course_review_activity_filters_extra_keys(), test_generate_course_review_activity_invalid_string_payload_raises(), test_generate_course_review_activity_requires_boolean_fields(), test_generate_course_review_activity_success() (+2 more)

### Community 93 - "Dependency Upgrade Notes"
Cohesion: 0.31
Nodes (9): get_active_semester(), list_semesters_for_tenant(), AsyncSession, date, 查询当前用户的激活学期配置，若不存在返回 None。, 保存学期配置：若已存在激活记录则更新，否则新建。 同一用户只保留一条 is_active=True 的记录。, API tenant 投影；可在当前 tenant 内按 user_id 进一步筛选。, upsert_active_semester() (+1 more)

### Community 94 - "Listening Image Repo Tests"
Cohesion: 0.29
Nodes (6): build_course_review_activity_filename(), validate_course_review_form(), test_build_course_review_activity_filename(), test_build_course_review_activity_filename_sanitizes_values(), test_validate_course_review_form_base_fields_only(), test_validate_course_review_form_requires_generated_fields()

### Community 95 - "Alembic Migration Env"
Cohesion: 0.28
Nodes (7): APIRouter, create_api_router(), 对外只读 REST API（二期）。  通过 :func:`create_api_router` 暴露 ``/api/v1`` 路由，由 ``app/main., 返回组装好的对外 API 路由（当前仅 v1）。, AsyncClient, fixture, api_client()

### Community 96 - "AI Key Model Migration"
Cohesion: 0.32
Nodes (6): main(), _on_global_exception(), 应用入口。 运行方式： python -m app.main 页面路由： / — 重定向到 /home /home — 主页 /setup —…, 全局未捕获异常处理：记录结构化 ERROR 日志（含 traceback）。 用户友好提示由各页面自行处理（如 AI 调用失败展示 e.message）；…, Exception, PyInstaller 入口脚本。  此文件作为 kindergartenManager.spec 的 Analysis 入口， 不能用 `python -m

### Community 97 - "Drop Invite Code Migration"
Cohesion: 0.50
Nodes (7): generate_course_review_activity_content(), AsyncSession, _make_mock_ai_key(), _result(), test_generate_course_review_activity_content_no_ai_key_raises(), test_generate_course_review_activity_content_success_with_default_prompt(), test_generate_course_review_activity_content_uses_db_prompt()

### Community 98 - "Course Review Migration"
Cohesion: 0.32
Nodes (6): page, 历史配置入口（路由 /setup）。 当前配置入口统一为 /settings；保留本路由只为兼容旧书签和旧链接。, setup_page(), asyncio, 旧 /setup 路由只保留为 /settings 兼容入口。, test_setup_redirects_to_settings()

### Community 100 - "Workday Date Utilities"
Cohesion: 0.32
Nodes (7): _minimum_versions(), Regression guard for the dependency floors frozen in GitHub Issue #49., Vulnerable families must resolve no lower than their patched release., The exact runtime graph must not contain the unpatched python-ecdsa chain., test_lock_excludes_unpatched_python_ecdsa_runtime_dependency(), test_requirements_cover_frozen_dependabot_security_floors(), _version_tuple()

### Community 101 - "Homemade Teaching Toy Tests"
Cohesion: 0.29
Nodes (6): 串行化完整 read→generate→persist；非 POSIX 仅承诺进程内互斥。, 返回自动生成密钥的持久化文件路径（位于用户可写数据目录）。, 自动生成缺失的密钥并持久化，保证重启后可还原。, _secrets_file_path(), _secrets_lifecycle_lock(), model_validator

### Community 102 - "Async Test Fixtures"
Cohesion: 0.52
Nodes (6): generate_homemade_teaching_content(), AsyncSession, _make_mock_ai_key(), test_generate_homemade_teaching_content_no_ai_key_raises(), test_generate_homemade_teaching_content_success_with_default_prompt(), test_generate_homemade_teaching_content_uses_db_prompt()

### Community 103 - "Runtime Pin Tests"
Cohesion: 0.38
Nodes (7): Game Observation Design Document, Call AI Vision Function, Game Observation Table, Game Observation Image Table, Generate Observation Function, Invite Code Table, Game Observation Progress Document

### Community 104 - "Add Teacher Name Migration"
Cohesion: 0.29
Nodes (5): 测试图片相关配置项（Phase A）。  验证新增的 IMAGE_STORAGE_BACKEND 和 IMAGE_MAX_BYTES 配置项存在且默认值正确，, IMAGE_MAX_BYTES 默认值为 1048576（1MB）。, IMAGE_STORAGE_BACKEND 默认值为 mysql_blob。, test_image_max_bytes_default(), test_image_storage_backend_default()

### Community 105 - "Homemade Teaching Toy Migration"
Cohesion: 0.33
Nodes (5): Alembic - Database Migration Tool, Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 107 - "Prompt Task Enum Migration"
Cohesion: 0.53
Nodes (5): mask_api_key(), 脱敏 API Key，仅对较长密钥保留末四位。, test_mask_api_key_hides_short_key(), test_mask_api_key_shows_last_four_at_threshold(), test_mask_api_key_shows_last_four_for_long_key()

### Community 108 - "Application Architecture Layers"
Cohesion: 0.33
Nodes (6): _build_task_panel(), 构建单个任务类型的提示词编辑区块（含历史版本列表）。, _render_history(), column, label, textarea

### Community 109 - "Listening Progress Development"
Cohesion: 0.47
Nodes (4): page, root_page(), asyncio, test_root_redirects_to_home()

### Community 110 - "Product Requirements Documents"
Cohesion: 0.33
Nodes (6): Six Dependabot security lower-bound upgrades, Changelog, ecdsa 0.19.2 residual risk remains outside this upgrade, Local dependency tests do not prove GitHub alert closure, Python 3.14.7 runtime unification, NiceGUI 3.16.0/FastAPI 0.141.1/Starlette compatibility baseline

### Community 111 - "Agent Registry Boundary Tests"
Cohesion: 0.33
Nodes (5): async_session(), AsyncSession, fixture, F004 integration fixtures for the Agent Foundation public service seam., Give each Foundation integration test an isolated in-memory database.

### Community 112 - "Agent Contract Tests"
Cohesion: 0.40
Nodes (4): downgrade(), Upgrade schema.      列 model_name 可能已存在（来自另一台机器的未提交迁移）。     若不存在则新增；若已存在则修改为 NOT, Downgrade schema: 恢复为可空、无默认值。, upgrade()

### Community 113 - "Dependency Security Tests"
Cohesion: 0.40
Nodes (4): downgrade(), 删除 invite_code 表（邀请码功能已移除）。, 重建 invite_code 表（回滚用）。, upgrade()

### Community 114 - "Release Build Workflow"
Cohesion: 0.80
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 115 - "AI API Key Migration"
Cohesion: 0.40
Nodes (5): Homemade Teaching Toy Test Plan, Test Stage P1, Test Stage P2, Test Class Repository File, Upsert Class Config Function

### Community 117 - "Smoke Test Migration"
Cohesion: 0.83
Nodes (3): downgrade(), _has_column(), upgrade()

### Community 118 - "Add User Table Migration"
Cohesion: 0.83
Nodes (3): downgrade(), _has_table(), upgrade()

### Community 119 - "Export Observation Migration"
Cohesion: 0.83
Nodes (3): downgrade(), _has_column(), upgrade()

### Community 121 - "Seed Indicator Catalog Migration"
Cohesion: 0.50
Nodes (4): One-on-One Listening Progress Record, Development Phase P0, Development Phase P1, Pick Three Workdays Function

### Community 122 - "Prompt Template Migration"
Cohesion: 0.67
Nodes (4): AI 拆分、年龄适配、Word 导出与存档, 首期每日活动计划闭环, 首期产品需求文档, 角色权限与数据安全

### Community 125 - "Listening Schema Migration"
Cohesion: 0.67
Nodes (3): Regression guard for dependency versions raised by Dependabot., _requirements_by_name(), test_dependabot_security_floors_are_not_downgraded()

### Community 126 - "Daily Plan Table Migration"
Cohesion: 0.67
Nodes (3): Release build workflow, Python 3.14.7 release build runtime, Windows/Linux/Docker release artifacts

### Community 141 - "Production Docker Topology"
Cohesion: 0.67
Nodes (3): Agent rejection and zero-change verification, Agent implementation rules: closed registry, no WRITE or persistence, Contributing guide

### Community 142 - "Modular Monolith Decision"
Cohesion: 0.67
Nodes (3): Existing AI adapter and teacher-adoption boundaries apply to future Agent, ADR-0004 AI and fixed Word boundaries, Existing one-shot AI functions cannot be exposed as arbitrary Agent Tools

### Community 143 - "Deb Build Script"
Cohesion: 0.67
Nodes (3): Accepted ADR-0005 Agent registry entry, Agent Tool, permission, memory, or write changes require a new ADR, ADR index

### Community 144 - "Post-Install Script"
Cohesion: 1.00
Nodes (3): Security lower bounds and dependency audit are production gates, Dependency and release supply-chain threat, Security threat model

### Community 145 - "Post-Remove Script"
Cohesion: 1.00
Nodes (3): Future Microservice Decomposition, Main Application (app/integration/), Services Directory Status README

### Community 146 - "Pre-Remove Script"
Cohesion: 0.67
Nodes (3): 一日活动节假日语义, 一日活动提示词版本管理, 一日活动提示词与一键生成

### Community 147 - "Database Migration Tool"
Cohesion: 1.00
Nodes (3): Homemade Teaching Design Document, Generate Homemade Teaching Function, Homemade Teaching Toy Table

## Knowledge Gaps
- **142 isolated node(s):** `一日活动节假日语义`, `一日活动提示词版本管理`, `课程审议手动流程验收`, `一日活动教案处理流水线`, `课程审议持久化与历史导出` (+137 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **52 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `save_daily_plan()` connect `Holiday API Client` to `F009 Browser Mock`, `API Key Auth`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `TrustedActor` connect `F008 Daily Plan UI` to `F008 Daily Plan UI`, `F008 Provider Adapter`, `F009 Persistence Matrix`, `F007 Runtime Safety`, `F008 Tool Executors`, `Export Record Repository`, `Observation Word Export`, `Migration Smoke Tests`, `Auth Middleware`, `API Key Auth`, `Runtime Path Utilities`, `AI Key Repository`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `AgentContext` (e.g. with `AgentContextBuilder` and `build_plan_patch()`) actually correct?**
  _`AgentContext` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `TrustedActor` (e.g. with `_ActiveOperation` and `create_daily_plan_agent_controller()`) actually correct?**
  _`TrustedActor` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 34 inferred relationships involving `Permission` (e.g. with `_validate_tool()` and `AgentToolRegistry`) actually correct?**
  _`Permission` has 34 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `AiParseError` (e.g. with `test_adapt_empty_original_raises_parse_error()` and `test_adapt_missing_adapted_process_raises_parse_error()`) actually correct?**
  _`AiParseError` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `DailyPlanScope` (e.g. with `_ActiveOperation` and `DailyPlanAgentController`) actually correct?**
  _`DailyPlanScope` has 10 INFERRED edges - model-reasoned connections that need verification._