# Graph Report - KindergartenManager  (2026-08-25)

## Corpus Check
- label refresh on the existing 3192-node graph; corpus statistics unchanged

## Summary
- 3192 nodes · 7337 edges · 204 communities (152 shown, 52 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 472 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Application Pages
- Zero Persistence Matrix
- Holiday Calendar Integration
- Browser Mock Helpers
- Runtime Lifecycle Safety
- Agent Runtime Controls
- Secrets Configuration
- Listening Document Export
- Error Logging and AI Keys
- AI Lesson Planning
- Daily Plan Word Export
- Plan Draft Projection
- Agent Composition UI
- User Authentication
- Workday Calendar Service
- Provider Runtime Verification
- Listening Record Services
- Closed Tool Executor Verification
- OpenAI Provider Adapter
- Graph Knowledge Pipeline
- Listening Content Services
- Database Model Layer
- Activity Generation Client
- Observation Data Repository
- Prompt Version Management
- Closed Agent Tool Registry
- Provider Adapter Verification
- Listening Activity Page
- Observation Word Export
- User Data Repository
- Encryption Services
- Migration Integration Verification
- Signed API Routes
- Content Generation Errors
- Agent Context Projection
- Composition UI Verification
- Course Review Word Export
- Image Processing Errors
- Image Storage Backend
- Provider Lifecycle Composition
- Agent Contracts
- AI Key Persistence
- Secret Initialization Verification
- Export Record Repository
- Tenant User Model
- Observation Image Repository
- Indicator Catalog Repository
- JWT Authentication
- Listening Image Repository
- Agent Foundation Specification
- Core Model Registry
- Admin Bootstrap
- Plan Patch Verification
- Environment File Handling
- Prompt Record Updates
- Vision AI Integration
- Homemade Teaching Export
- Listening AI Verification
- Daily Plan Repository
- Diff Calculation
- Course Review Schema
- Application Architecture Overview
- Course Review Data Model
- Lesson Plan Processing
- Startup Migration Flow
- Daily Plan Agent Panel
- Secret Failure Handling
- Secret File Security
- Readonly API Routes
- Authentication Middleware
- Homemade Teaching Repository
- Setup State Management
- Observation AI Client
- Date Selection Panel
- Application Data Paths
- Homemade Teaching Feature
- Listening Data Models
- Activity Adaptation Client
- Observation Page Validation
- Password Security
- Manual Acceptance Verification
- Database Configuration Verification
- AI Connection Verification
- Course Review AI Client
- Read Projection Verification
- Listening Migration Verification
- User Registration Service
- Semester Data Repository
- Selection Generation Safety
- Course Review UI Validation
- API Router Setup
- Audit Logging
- Secrets Configuration Verification
- Listening AI Integration
- Prompt Management UI
- Secret Write Failure Verification
- Dependency Security Verification
- AI Endpoint Validation
- Game Observation Design
- Image Configuration Verification
- Application Entry Point
- API Key Masking
- Root Page Layout
- Setup Wizard
- Changelog History
- Async Session Management
- AI Key Migration
- Invitation Removal Migration
- Course Review Migration
- Homemade Teaching Plan
- Python Runtime Verification
- Class Configuration Migration
- Homemade Teaching Migration
- Export Record Migration
- Prompt Task Migration
- Observation Image Encoding
- Listening Development Progress
- Product Requirements
- Closed Registry Verification
- Foundation Contract Verification
- Dependency Baseline Verification
- Release Build Workflow
- Contribution Guidelines
- AI Word Boundary Decision
- Architecture Decisions
- Security Threat Model
- Future Services Architecture
- Daily Plan Prompt Design
- Homemade Teaching Design
- AI Integration Boundary
- Database Migration Policy
- Word Export Policy
- Agent Foundation Package
- Production Container Topology
- Modular Monolith Decision
- Debian Package Build
- Package Install Hook
- Package Removal Hook
- Package Cleanup Hook
- Controlled Agent Runtime
- Web Server Routing
- Container Platform
- Main Application Architecture
- MySQL Database
- SQLite Database
- Tenant Isolation
- Controlled Agent Governance
- Knowledge Graph Navigation
- Graph Navigation Entry Points
- Risk Classification Rules
- Session Management
- Type Validation Utilities
- Document Color Formatting
- Exception Handling
- Page Rendering
- Development Container Topology
- Single User Tenant API
- User Manual
- SQLite MySQL Decision
- Dependency Security Baseline
- Developer Agent Workflow
- Image Storage Interface
- Homemade Teaching Stages
- Homemade Teaching Progress
- Homemade Teaching Roadmap
- Historical Implementation Plan
- Architecture History
- Course Review Manual Acceptance
- Daily Plan Lesson Pipeline
- Homemade Teaching Development
- Project Identity
- Word Document Library
- Architecture Overview
- Python Dependencies
- Provider Response Contract
- Async HTTP Client

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
- `ToolLoopProvider` --uses--> `Permission`  [INFERRED]
  specs/agent-foundation/tests/test_f009_zero_persistence_matrix_red.py → app/service/agent/contracts.py
- `CalendarEvaluationProjection` --uses--> `test_each_read_tool_returns_one_closed_projection_from_one_short_session()`  [INFERRED]
  app/service/agent/contracts.py → specs/agent-foundation/tests/test_f008_tool_executor_red.py
- `DailyPlanProjection` --uses--> `_projection()`  [INFERRED]
  app/service/agent/contracts.py → specs/agent-foundation/tests/test_f009_zero_persistence_matrix_red.py
- `DailyPlanProjection` --uses--> `test_controller_builds_fresh_actor_scoped_context_and_short_lived_credentials()`  [INFERRED]
  app/service/agent/contracts.py → specs/agent-foundation/tests/test_f008_composition_ui_red.py
- `DailyPlanProjection` --uses--> `test_each_read_tool_returns_one_closed_projection_from_one_short_session()`  [INFERRED]
  app/service/agent/contracts.py → specs/agent-foundation/tests/test_f008_tool_executor_red.py

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

## Communities (204 total, 52 thin omitted)

### Community 0 - "Application Pages"
Cohesion: 0.04
Nodes (73): NiceGUI - Python Web Framework, get_current_user(), 单用户模式：提供固定的默认用户上下文。  取消登录功能后，所有页面通过此模块获取当前用户信息， 而非从 JWT token 中解析。, 返回当前用户信息字典（单用户模式下始终返回默认管理员）。, 应用入口。 运行方式： python -m app.main 页面路由： / — 重定向到 /home /home — 主页 /setup —…, get_class_config(), list_class_configs_for_tenant(), AsyncSession (+65 more)

### Community 1 - "Zero Persistence Matrix"
Cohesion: 0.07
Nodes (69): AgentPanelStatus, Enum, str, Closed UI-facing states for the non-writing Agent panel., ProviderFinishReason, ProviderTurnResult, Normalized result returned by a provider adapter., Local ceilings that bound a serial provider/tool loop. (+61 more)

### Community 2 - "Holiday Calendar Integration"
Cohesion: 0.05
Nodes (47): _ensure_cache_fresh(), get_holiday_name(), get_legal_holidays_in_year(), get_special_day_tags(), is_adjusted_workday(), is_holiday(), is_near_holiday(), date (+39 more)

### Community 3 - "Browser Mock Helpers"
Cohesion: 0.08
Nodes (65): 创建或更新每日活动计划（同一用户同一日期 upsert）。 若当天已存在记录，则更新；否则新建。 Args: session: 异步数据库会话。…, save_daily_plan(), ArgumentParser, BaseHTTPRequestHandler, HTTPStatus, Namespace, _arguments(), _completed() (+57 more)

### Community 4 - "Runtime Lifecycle Safety"
Cohesion: 0.10
Nodes (56): ClassAreasProjection, Allowlisted class-area facts; teacher identity is intentionally omitted., _agent(), BlockingThenSuccessProvider, CancellationDefyingExecutor, CancellationDefyingProvider, CancelledClock, _context() (+48 more)

### Community 5 - "Agent Runtime Controls"
Cohesion: 0.05
Nodes (49): DailyPlanScope, Exactly one current-plan locator; actor identity is deliberately absent., plan_patch_matches_expected(), PlanPatch, Verify every canonical PlanPatch field except its intentionally random id., Immutable, discardable suggestion bound to one frozen Agent turn., AgentContextStamp, AgentCurrentContextPort (+41 more)

### Community 6 - "Secrets Configuration"
Cohesion: 0.06
Nodes (51): Alembic - Database Migration Tool, Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online(), ApiPrincipal, _build_signing_string(), get_api_principal() (+43 more)

### Community 7 - "Listening Document Export"
Cohesion: 0.06
Nodes (64): _build_domain_doc(), _build_from_scratch(), _clear_cell(), _domain_of_title(), export_batch_by_domain(), export_combined(), export_split_by_domain(), _extract_block() (+56 more)

### Community 8 - "Error Logging and AI Keys"
Cohesion: 0.07
Nodes (41): 审计日志：记录关键操作（登录、改密、AI 调用、Word 导出等）。  审计日志通过结构化 JSON logger 输出，统一携带 audit_action 与, get_logger(), AiApiKey, 年龄适配 AI 客户端。  将活动过程原文按年龄段（小班/中班/大班）改写，返回改写后文本。  输出 Schema：     {"adapted_process, 一日活动生成客户端 — 包含 5 种活动类型的内置默认提示词。  任务类型对应关系： - morning_exercise  →  晨间活动 - morning, 游戏观察生成 AI 客户端。  调用 OpenAI 兼容多模态接口，输入 1~3 张游戏照片 + 元数据， 输出「观察目标 / 观察记录 / 评价分析 / 支持, AI 视觉客户端基础模块 — 多模态 Chat Completions 调用。  所有视觉 AI 调用必须通过此模块，禁止在 service 层直接发 HTTP, get_active_ai_key() (+33 more)

### Community 9 - "AI Lesson Planning"
Cohesion: 0.07
Nodes (52): AiCallError, AiParseError, Exception, AI 接口调用失败时抛出：HTTP 4xx/5xx、网络超时、超过重试次数等。, AI 返回内容解析失败时抛出：JSON 格式非法、缺少必要字段等。, call_ai(), call_ai_text(), _make_retry_decorator() (+44 more)

### Community 10 - "Daily Plan Word Export"
Cohesion: 0.08
Nodes (36): _build_collective_cell(), export_batch_daily_plans(), export_daily_plan(), _export_from_scratch(), _fill_fields_cell(), _fill_plain_cell(), _fill_process_cell(), _fill_template() (+28 more)

### Community 11 - "Plan Draft Projection"
Cohesion: 0.07
Nodes (48): get_daily_plan_by_date(), 按日期查询每日计划（同一用户同一天只有一条）。, canonical_sha256(), Hash supported DTO values using stable UTF-8 JSON encoding., CalendarEvaluationProjection, DailyPlanProjection, PlanSection, One allowlisted, bounded daily-plan section. (+40 more)

### Community 12 - "Agent Composition UI"
Cohesion: 0.06
Nodes (39): _ActiveOperation, AgentPanelSnapshot, AgentPatchOperationSnapshot, AgentPatchSnapshot, _cancelled(), create_daily_plan_agent_controller(), DailyPlanAgentController, DailyPlanAgentCoordinator (+31 more)

### Community 13 - "User Authentication"
Cohesion: 0.09
Nodes (51): AuthError, 鉴权失败：token 无效、已过期、签名错误或用户名密码错误时抛出。          故意不区分"用户不存在"和"密码错误"，防止用户枚举攻击。, approve_user(), change_password(), create_user_by_admin(), list_users_for_admin(), login(), AsyncSession (+43 more)

### Community 14 - "Workday Calendar Service"
Cohesion: 0.08
Nodes (22): get_week_number(), get_weekday_cn(), is_within_semester(), is_workday(), pick_three_workdays(), date, 日期计算服务 — 纯函数，无 IO，无数据库依赖。, 返回 target_date 是开学后第几周（第 1 周起算）。      例：start_date=周一，target_date=同一天 → 第 1 周； (+14 more)

### Community 15 - "Provider Runtime Verification"
Cohesion: 0.17
Nodes (46): _agent_runtime(), BlockingProvider, _context(), _draft_arguments(), MutableExecutorPayload, MutableText, MutableTuple, _plan_patch() (+38 more)

### Community 16 - "Listening Record Services"
Cohesion: 0.09
Nodes (47): delete_domains_by_record(), delete_indicator_results_by_record(), delete_record(), get_record_by_id(), list_domains_by_record(), list_indicator_results(), list_records(), Any (+39 more)

### Community 17 - "Closed Tool Executor Verification"
Cohesion: 0.12
Nodes (40): Permission, Permissions reserved by the Agent contract., Closed local tool-execution outcomes., ToolExecutionStatus, async_sessionmaker, _assert_envelope(), _call(), _context() (+32 more)

### Community 18 - "OpenAI Provider Adapter"
Cohesion: 0.08
Nodes (40): AgentProviderAdapterError, _build_payload(), _classify_transport_failure(), _descriptor_for_call(), _input_json_schema(), _InvalidWire, OpenAICompatibleAgentProvider, _parse_request_id() (+32 more)

### Community 19 - "Graph Knowledge Pipeline"
Cohesion: 0.04
Nodes (47): Cypher Query Language, detect_changes, Edge Types, get_architecture, get_code_snippet, query_graph, search_graph, codebase-memory 14 MCP Tools (+39 more)

### Community 20 - "Listening Content Services"
Cohesion: 0.07
Nodes (42): CompressedImage, 图片压缩处理模块（游戏观察子系统）。  `compress_image` 将任意图片字节压缩至指定大小上限： - 超限时等比缩放 + 逐步降低 JPEG 质量直, list_images_by_record(), 查询某记录下的图片（可选按领域过滤），按领域 + image_index 升序。, _clamp_star(), generate_domain_content(), load_record_detail(), 从 DB 装配整条记录详情（主表 + 各领域 + 图片 + 指标结果）。 指标的 sort_order 经 indicator_catalog… (+34 more)

### Community 21 - "Database Model Layer"
Cohesion: 0.06
Nodes (31): Base, _build_engine(), _resolve_database_url(), AiApiKey — AI 接口 Key 数据模型。  安全约束： - `api_key_encrypted` 字段仅存密文，明文禁止入库、禁止写入日志。 -, GameObservationImage — 游戏观察图片数据模型。  可插拔存储：本期实现 MySQL BLOB 后端（blob_content 存压缩后二进, GameObservation — 游戏观察记录数据模型。  每条记录对应教师的一次游戏观察，包含元数据（日期/环境/人员） 和 AI 生成的四段内容（观察目标, IndicatorCatalog — 一对一倾听指标目录（参考数据，迁移预置）。  按 (grade, term, domain) 组织一级/二级指标及三档（★, ListeningDomain — 一对一倾听单领域内容。  每条 listening_record 对应 5 条本表（健康/语言/社会/艺术/科学各一）。 年 (+23 more)

### Community 22 - "Activity Generation Client"
Cohesion: 0.07
Nodes (43): _build_prefix(), _build_user_content(), generate_activity(), _holiday_hint(), 构建消息开头的班级与教学周信息。      context 支持 grade、class_name、week_number、weekday 字段；     we, 当 near_holiday 为 True 时返回临近节假日提示行，否则返回空字符串。      near_holiday 取值：True 表示明日为法定节假日, 根据任务类型和上下文构建发送给 AI 的用户消息。      context 支持以下字段：         grade, class_name, activi, 生成单项一日活动内容（纯文本输出）。      Args:         task_type: 任务类型（morning_exercise / morning (+35 more)

### Community 23 - "Observation Data Repository"
Cohesion: 0.08
Nodes (38): delete_observation(), get_observation_by_id(), list_observations(), Any, AsyncSession, date, observation_repository — 游戏观察记录数据访问层。 所有查询强制携带 tenant_id 过滤，确保多租户数据隔离。, 更新指定观察记录的字段（传入任意关键字参数），返回是否成功。 (+30 more)

### Community 24 - "Prompt Version Management"
Cohesion: 0.08
Nodes (23): list_versions(), AsyncSession, 将指定版本设为激活，其余版本设为 inactive。      Args:         session: 异步数据库会话。         tenant_i, 返回指定任务类型的所有版本，按版本号降序排列。      Args:         session: 异步数据库会话。         tenant_id:, 保存新版本提示词，自动递增版本号并将旧激活记录设为 inactive。      Args:         session: 异步数据库会话。, rollback_to_version(), save_new_version(), 提示词仓库层集成测试。  使用 SQLite 内存库 fixture（来自 conftest.py），与真实 MySQL 完全隔离。 (+15 more)

### Community 25 - "Closed Agent Tool Registry"
Cohesion: 0.09
Nodes (25): AgentContext, Short-lived, frozen facts for one operation and turn., AgentToolRegistry, AgentToolRejected, ValueError, Closed registry for the first Agent Foundation slice., Raised with a stable code when registry resolution is rejected., Exact, immutable Foundation tool surface. (+17 more)

### Community 26 - "Provider Adapter Verification"
Cohesion: 0.17
Nodes (39): build_foundation_registry(), Build the closed registry; callers cannot add or replace descriptors., _adapter_module(), _arguments_for(), _assert_no_sensitive_text(), _assert_tool_parameters_are_closed(), _choice(), _context() (+31 more)

### Community 27 - "Listening Activity Page"
Cohesion: 0.09
Nodes (36): _auto_pick_workdays(), build_batch_export_filename(), build_export_filename(), default_year_month(), distribute_images_by_filename(), format_record_summary(), format_stage_label(), infer_age_by_grade() (+28 more)

### Community 28 - "Observation Word Export"
Cohesion: 0.11
Nodes (35): _add_images_to_cell(), _build_from_scratch(), _clear_cell(), export_observation(), _fill_template(), Document, Path, 游戏观察记录 Word 导出器。 主方案：打开模板 `templates/ObservationRecord.docx`， 替换标题中的 'xx'… (+27 more)

### Community 29 - "User Data Repository"
Cohesion: 0.16
Nodes (19): create_user(), get_user_by_id(), 创建用户并持久化到数据库，返回已持久化的 User 对象。, 在指定租户下按 ID 查询用户，不存在时返回 None。, 用户仓库层集成测试（SQLite 内存库）。, 支持用户名关键字筛选和分页，且总数统计正确。, 不同 tenant_id 下同名用户互不可见。, 不同 tenant_id 下通过 ID 查询返回 None。 (+11 more)

### Community 30 - "Encryption Services"
Cohesion: 0.09
Nodes (19): _build_fernet(), decrypt(), encrypt(), 应用层对称加密工具（Fernet）。  密钥来源：Settings.ENCRYPTION_KEY（原始字符串，UTF-8 编码后取前 32 字节， 再经 bas, 将环境变量中的原始字符串密钥转换为 Fernet 实例。      Fernet 要求 32 字节的 URL-safe base64 编码密钥（共 44 个字符, 加密明文字符串，返回 URL-safe base64 密文字符串。      Args:         plain_text: 待加密的明文（禁止在调用方写入, 解密密文字符串，还原为原始明文。      Args:         cipher_text: 由 `encrypt()` 生成的密文字符串。      Re, CryptoError (+11 more)

### Community 31 - "Migration Integration Verification"
Cohesion: 0.09
Nodes (32): GameObservation, GameObservationImage, PromptTemplate, Phase P1: Migration & Seed, asyncio, Phase B — 数据模型冒烟测试（ORM + SQLite in-memory）。 测试策略： - 用 async_session…, GameObservation 可插入并按 id 查询。, GameObservation.tenant_id 非空约束生效。 (+24 more)

### Community 32 - "Signed API Routes"
Cohesion: 0.09
Nodes (11): get_db(), AsyncSession, 对外 REST API 的 FastAPI 依赖。, 提供独立的异步数据库会话（只读查询，无需提交）。      测试可通过 ``app.dependency_overrides[get_db]`` 注入内存库会话, 对外 REST API 路由集成测试（httpx ASGITransport + SQLite 内存库）。, API Key 代表 tenant；不传 user 过滤时可读本 tenant 内多个教师。, _seed(), TestAuth (+3 more)

### Community 33 - "Content Generation Errors"
Cohesion: 0.11
Nodes (28): ConfigError, 业务配置缺失时抛出：如用户尚未配置 AI Key。, generate_course_review_activity_content(), AsyncSession, generate_activity_content(), AsyncSession, 生成单项活动内容。      Args:         session: 异步数据库会话（查询 AI Key 与自定义提示词）。         tenant, generate_homemade_teaching_content() (+20 more)

### Community 34 - "Agent Context Projection"
Cohesion: 0.09
Nodes (24): AgentContextBuilder, _fingerprint(), datetime, UUID, Build short-lived, frozen Agent contexts from the F004 READ seam., Assemble one ordered context without exposing repository or ORM objects., Read and freeze facts in the contract-defined order., _utc_now() (+16 more)

### Community 35 - "Composition UI Verification"
Cohesion: 0.17
Nodes (24): agent_session_factory(), BlockingProvider, _composition(), _controller(), ImmediateProvider, Any, asyncio, fixture (+16 more)

### Community 36 - "Course Review Word Export"
Cohesion: 0.18
Nodes (27): Any, _build_from_scratch(), _clear_cell(), _clear_paragraph(), export_course_review_activity(), _fill_template(), _get_bool(), _get_value() (+19 more)

### Community 37 - "Image Processing Errors"
Cohesion: 0.12
Nodes (28): AppError, 通用业务异常：输入非法、文件格式错误等非 AI / 非鉴权类业务错误。, compress_image(), normalize_to_landscape(), 将图片统一为横版（宽 ≥ 高）。      处理步骤：       1. 按 EXIF 方向校正（手机照片常见）。       2. 透明通道转白底 RGB。, 将图片字节压缩至 max_bytes 以内。      Args:         data: 原始图片字节（JPEG / PNG / WebP 等 Pillo, Phase P8d: Image Processing, _make_jpeg_bytes() (+20 more)

### Community 38 - "Image Storage Backend"
Cohesion: 0.11
Nodes (20): ABC, ImageStorageBackend, 存储图片字节，返回存储引用 dict。          Returns:             dict，键因后端而异（blob_backend 含 blo, 从存储引用还原图片字节。          Args:             stored: 与 put 返回格式相同的 dict。          Ret, 可插拔图片存储后端抽象。      put / get 与数据库 session 解耦：     - put 返回 stored_ref dict，由 repo, BlobImageStorage, MySQL BLOB 图片存储后端。  put/get 只操作内存 dict，实际 DB 写入由 repository 层完成。, MySQL BLOB 后端：图片二进制存入 game_observation_image.blob_content。 (+12 more)

### Community 39 - "Provider Lifecycle Composition"
Cohesion: 0.08
Nodes (16): AgentProviderConfig, _BoundProvider, _CurrentContextState, _default_provider_factory(), ProviderFactory, datetime, Protocol, SessionFactory (+8 more)

### Community 40 - "Agent Contracts"
Cohesion: 0.11
Nodes (21): CalendarDayType, ClosedToolInputSchema, ClosedToolOutputSchema, Enum, str, Closed contracts for the authorized Agent Foundation slices., Exact application DTO kind accepted back from a local executor., Return whether every field is a closed, deeply immutable DTO value. (+13 more)

### Community 41 - "AI Key Persistence"
Cohesion: 0.10
Nodes (17): AsyncSession, tests/test_ai_key_repository.py — ai_key_repository 集成测试。 使用 SQLite…, 查询从未保存过 Key 的租户应返回 None。, 入库后 api_key_encrypted 不能与明文相同。, 新保存的记录 is_active 应为 True。, api_base_url 字段应与传入值一致。, 保存后 get_active_ai_key 可取回该记录。, model_name 字段应与传入值一致。 (+9 more)

### Community 42 - "Secret Initialization Verification"
Cohesion: 0.14
Nodes (14): _make_settings(), 在受控环境下构造 Settings 实例，不读取磁盘 .env 文件。, 无任何配置时，Settings() 应成功实例化（修复必填字段导致的启动崩溃）。, ENCRYPTION_KEY 为空时应自动生成非空值。, JWT_SECRET 为空时应自动生成非空值。, 已设置的 ENCRYPTION_KEY 不应被自动生成逻辑覆盖。, 首次生成的密钥写入持久化文件，第二次实例化时读回相同值。, 自动生成的 ENCRYPTION_KEY 应能被 app.core.crypto 正常使用。 (+6 more)

### Community 43 - "Export Record Repository"
Cohesion: 0.12
Nodes (23): ExportRecord, 导出记录数据模型。  对应数据库表：export_records 记录每次 Word 导出操作的元信息（文件名、路径、关联教案）。 导出记录为只增不改（immu, AsyncSession, 写入一条导出记录。      Args:         session: 异步数据库会话（调用方负责事务管理）。         tenant_id: 机构, save_export_record(), tests/test_export_repository.py — 导出记录仓库层测试。  使用 SQLite 内存库（async_session fixtur, 写入倾听导出记录时，listening_record_id 字段正确持久化。, 未传 listening_record_id 时，字段默认为 None（向后兼容）。 (+15 more)

### Community 44 - "Tenant User Model"
Cohesion: 0.09
Nodes (36): ensure_default_user(), AsyncSession, 应用启动引导：确保默认用户存在。  单用户模式下，系统启动时自动在 user 表中创建默认管理员账号。 如果已存在则跳过（幂等）。, 确保默认用户存在，不存在则创建。已存在则跳过。, run_bootstrap(), User, UserRole, create_pending_user() (+28 more)

### Community 45 - "Observation Image Repository"
Cohesion: 0.16
Nodes (22): SQLAlchemy - ORM, add_image(), delete_images_by_observation(), get_image(), list_images_by_observation(), AsyncSession, observation_image_repository — 游戏观察图片数据访问层。, 新增一张观察图片并 flush，提交由最外层 use-case 负责。 (+14 more)

### Community 46 - "Indicator Catalog Repository"
Cohesion: 0.17
Nodes (22): IndicatorCatalog, get_indicator_by_id(), list_available_stages(), list_indicators(), list_indicators_by_ids(), AsyncSession, indicator_repository — 指标目录数据访问层。  只读参考数据查询（指标目录按 tenant_id + grade + term + dom, 查询某 (年级, 学期, 领域) 的全部二级指标，按 sort_order 升序。 (+14 more)

### Community 47 - "JWT Authentication"
Cohesion: 0.15
Nodes (20): create_access_token(), decode_access_token(), JWT access token 生成与解码工具。, 生成 JWT access token。 payload 字段： - sub: str(user_id) - tenant_id: int - role:…, 解码并验证 JWT token，返回 payload 字典。 token 过期、签名无效等情况统一抛出 AuthError。, _get_current_user(), 系统管理员账号管理页面（路由：/user-admin）。  阶段二能力： - 系统管理员创建账号 - 列表筛选与分页 - 账号启停 - 管理员重置密码, user_admin_page() (+12 more)

### Community 48 - "Listening Image Repository"
Cohesion: 0.14
Nodes (21): add_image(), delete_images_by_record(), get_image(), AsyncSession, listening_image_repository — 一对一倾听图片数据访问层。, 新增一张倾听图片并 flush，提交由最外层 use-case 负责。, 按 id 查询单张图片，强制 tenant_id 过滤。, 删除某记录下的所有图片（tenant 隔离）。 (+13 more)

### Community 49 - "Agent Foundation Specification"
Cohesion: 0.16
Nodes (22): Current Agent Foundation status, Controlled AI Agent Runtime decision, Agent Runtime design, Agent data persistence boundary, Agent application composition, F009 manual acceptance guide, Agent Foundation roadmap snapshot 2026-08-25, F009 acceptance status (+14 more)

### Community 50 - "Core Model Registry"
Cohesion: 0.26
Nodes (13): ClassConfigOut, DailyPlanListOut, DailyPlanOut, HealthOut, PageMeta, 对外 REST API 响应模型（Pydantic）。  仅暴露教学计划相关的只读字段；不包含密钥、密码等敏感信息。, SemesterOut, ClassConfig (+5 more)

### Community 51 - "Admin Bootstrap"
Cohesion: 0.17
Nodes (17): bootstrap_admin(), _main(), _prompt_password(), _prompt_str(), 系统管理员初始化脚本。  模式：   --init           创建 sys_admin 账号（默认模式）   --reset-password 重置, --init 模式：创建 sys_admin 账号。, --reset-password 模式：重置 sys_admin 密码。, 重置 sys_admin 密码（需旧密码验证），返回执行结果说明。 (+9 more)

### Community 52 - "Plan Patch Verification"
Cohesion: 0.25
Nodes (20): _assert_rejected(), _context(), _patch_module(), _proposal(), asyncio, AsyncSession, DailyPlan, parametrize (+12 more)

### Community 53 - "Environment File Handling"
Cohesion: 0.21
Nodes (9): 解析 .env 文件，返回 key-value 字典。      忽略空行与 # 开头的注释行。文件不存在时返回空字典。, 将 updates 中的 key-value 原子写入 .env，保留其余行不动。      若 .env 不存在则自动创建。写入失败时抛出 RuntimeEr, read_dot_env(), write_dot_env(), Path, 测试 app.core.env_writer 模块。  覆盖： - read_dot_env()：文件不存在返回 {}；解析 key=value；忽略注释和空行, 值中包含 = 时，仅在第一个 = 处分割。, TestReadDotEnv (+1 more)

### Community 54 - "Prompt Record Updates"
Cohesion: 0.13
Nodes (16): AsyncSessionUnitOfWork, AsyncSession, SQLAlchemy 异步会话的最外层 Unit of Work。, 在一个 use-case 结束时统一提交，任一步失败时统一回滚。, _persist_domains(), AsyncSession, ImageStorageBackend, 写入某记录下的各领域内容（领域 + 图片 + 指标结果）。 save_record_with_all（新建）与… (+8 more)

### Community 55 - "Vision AI Integration"
Cohesion: 0.15
Nodes (19): call_ai_vision(), _make_retry_decorator(), AsyncClient, 构造 tenacity 重试装饰器：最多 3 次，指数退避 2s → 4s → 8s。, 发送多模态 Chat Completions 请求，返回解析后的 dict。      Args:         messages: 消息列表，content, _make_error_response(), _make_openai_response(), Response (+11 more)

### Community 56 - "Homemade Teaching Export"
Cohesion: 0.24
Nodes (18): _build_from_scratch(), _clear_cell(), export_homemade_teaching(), _fill_template(), _get_value(), Any, Document, Path (+10 more)

### Community 57 - "Listening AI Verification"
Cohesion: 0.19
Nodes (18): generate_listening_domain(), 调用视觉 AI 生成某领域的一对一倾听结构化内容。      Args:         images: 该领域绘画图片字节列表（经压缩后的 bytes，至少, Phase P4: AI Client, _full_result(), _make_response(), Response, P4 — 一对一倾听 AI 客户端测试（generate_listening_domain）。, 传入 system_prompt 时覆盖默认（校验请求 payload）。 (+10 more)

### Community 58 - "Daily Plan Repository"
Cohesion: 0.20
Nodes (17): delete_daily_plan(), get_daily_plan_by_id_for_tenant(), get_daily_plan_by_id_for_user(), _list_daily_plans(), list_daily_plans_for_tenant(), list_daily_plans_for_user(), AsyncSession, DailyPlan (+9 more)

### Community 59 - "Diff Calculation"
Cohesion: 0.15
Nodes (18): compute_diff(), 将文本按标点符号或换行符拆分为句子列表，过滤空串。, 对原文与改写文按句比对，返回带 changed 标记的句子列表。      Args:         original: 活动过程原文。         ad, _split_sentences(), tests/test_diff_service.py — 差异比对服务测试。, 完全相同的文本，所有句子 changed 为 False。, 修改一句后，该句 changed 为 True，其余句子不变。, 原文与改写文完全不同时，所有句子 changed 为 True。 (+10 more)

### Community 60 - "Course Review Schema"
Cohesion: 0.11
Nodes (19): 课程审议 AI 结构化 JSON 合约, 课程审议持久化与历史导出, 课程审议 Word 模板映射, 课程审议 AI 客户端与服务层, 课程审议分阶段交付, 课程审议 Word 导出阶段, 课程审议完整实现, 课程审议自动测试证据 (+11 more)

### Community 61 - "Application Architecture Overview"
Cohesion: 0.12
Nodes (18): AI Integration Layer, Authentication System (JWT + RBAC), Course Review Activity Subsystem, Daily Plan Subsystem, Database Layer (MySQL/SQLite), Game Observation Subsystem, Homemade Teaching Toy Subsystem, Kindergarten Management System (+10 more)

### Community 62 - "Course Review Data Model"
Cohesion: 0.26
Nodes (15): CourseReviewActivity, 课程审议记录。      每条记录保存一次课程审议生成与教师编辑后的结果。班级、年龄段与教师姓名     采用冗余快照，避免后续系统设置变更影响历史导出。, create_course_review_activity(), delete_course_review_activity(), get_course_review_activity(), list_course_review_activities(), AsyncSession, 删除课程审议记录，强制 tenant_id + user_id 双重过滤。 (+7 more)

### Community 63 - "Lesson Plan Processing"
Cohesion: 0.20
Nodes (17): process_lesson_plan(), AsyncSession, 完整教案拆分与年龄适配流程。      Args:         session: 异步数据库会话（用于查询 AI Key）。         tenant_, _make_mock_ai_client(), _make_mock_ai_key(), asyncio, tests/test_lesson_plan_service.py — 教案拆分服务测试。 使用 Mock 隔离 AI 调用和数据库访问。, 用户未配置 AI Key 时，抛出 ConfigError。 (+9 more)

### Community 64 - "Startup Migration Flow"
Cohesion: 0.15
Nodes (13): build_sync_url(), _get_alembic_ini_path(), _get_alembic_script_location(), 应用启动模块：自动执行 Alembic 数据库迁移。 支持三种运行模式： - 开发模式（python -m…, 将异步驱动 URL 转换为 Alembic 所需的同步驱动 URL。…, 在应用启动时自动执行 alembic upgrade head。 桌面、开发与服务器模式统一 fail-closed：迁移失败时记录异常并重新抛出，…, run_startup_migrations(), 显式配置 MySQL 异步 URL 时，迁移侧应转换为同步 pymysql 驱动且库名不变。 (+5 more)

### Community 65 - "Daily Plan Agent Panel"
Cohesion: 0.18
Nodes (7): DailyPlanAgentPanel, date, Invalidate suggestions based on an authoritative plan before mutation., Cancel connection-local work while keeping the controller reusable., Release page-local state and cancel its exact in-flight operation., NiceGUI rendering facade around one page-local Agent controller., Synchronously invalidate old work before date-side awaits begin.

### Community 66 - "Secret Failure Handling"
Cohesion: 0.15
Nodes (17): _assert_failure_is_sanitized(), _capture_settings_error(), _install_after_open_write_failure(), parametrize, 允许安全打开，再在 Settings 期间的第一笔正文写入处失败。, FIFO 必须以 non-blocking 方式打开并在任何正文读取前拒绝。, 目录等非普通文件不得被当作缺失配置后继续启动。, 生成的两个密钥写入失败时必须向上传播、清理并保持脱敏。 (+9 more)

### Community 67 - "Secret File Security"
Cohesion: 0.20
Nodes (17): _assert_non_posix_regular_file_contract(), _file_digest(), _install_content_read_probe(), _mode(), Path, 只验证跨平台功能，不把 POSIX mode 当作 Windows DACL 证据。, POSIX 新文件即使在 umask=0 下也不得短暂暴露为 group/other 可读。, 既有 0664 普通文件必须先纠权再读，且不得重写其正文。 (+9 more)

### Community 68 - "Readonly API Routes"
Cohesion: 0.18
Nodes (15): FastAPI - Web Framework, ApiPrincipal, get_daily_plan(), health(), date, query_classes(), query_daily_plans(), query_semesters() (+7 more)

### Community 69 - "Authentication Middleware"
Cohesion: 0.16
Nodes (11): AuthMiddleware, Request, 路由守卫中间件（已禁用 — 单用户模式无需登录）。  保留模块以便后续恢复登录功能。当前为直通中间件，不做任何鉴权检查。 根路径 (/) 重定向到 /home。, 单用户模式：仅将根路径重定向到 /home，其余请求直接放行。, BaseHTTPMiddleware, asyncio, tests/test_middleware.py — 单用户模式路由中间件测试。 验证： - 根路径 (/) 重定向到 /home -…, 中间件可被实例化（接收 ASGI app 参数）。 (+3 more)

### Community 70 - "Homemade Teaching Repository"
Cohesion: 0.28
Nodes (13): HomemadeTeachingToy, 教师自制教玩具记录。      每条记录保存一次 AI 生成或教师编辑后的教玩具方案。班级与教师姓名     采用冗余快照，避免后续设置变更影响历史导出。, create_homemade_teaching_toy(), delete_homemade_teaching_toy(), get_homemade_teaching_toy(), list_homemade_teaching_toys(), AsyncSession, 按 id 查询记录，强制 tenant_id 过滤。 (+5 more)

### Community 71 - "Setup State Management"
Cohesion: 0.21
Nodes (9): is_setup_complete(), mark_setup_complete(), 检查系统是否已完成初始化配置（同步调用，纯文件检查，无 DB 查询）。, 写入 setup 完成标记文件。写入失败时静默忽略（不阻断正常流程）。, Path, 测试 app.core.setup_state 模块。 注意：setup_state 标记文件机制在单用户模式重构中已弃用。…, TestIsSetupComplete, TestMarkSetupComplete (+1 more)

### Community 72 - "Observation AI Client"
Cohesion: 0.18
Nodes (15): _build_context_text(), generate_observation(), 将上下文 dict 转为给 AI 的说明文本。, 调用视觉 AI 生成游戏观察记录四段内容。      Args:         images: 图片字节列表（1~3 张，经压缩后的 bytes）。, _make_openai_response(), Response, tests/test_observation_client.py — 游戏观察生成客户端测试。  测试覆盖：   1. mock 返回 4 字段 JSON →, 空图片列表时，抛出 AppError（至少需要 1 张图片）。 (+7 more)

### Community 73 - "Date Selection Panel"
Cohesion: 0.21
Nodes (8): DatePanel, 渲染面板并返回外层 card 元素，可嵌入父容器。, Synchronously invalidate older work before starting async lookups., 外部或内部直接设置日期值，触发联动更新（同步入口）。, 日期选择器选值回调（同步，启动异步联动）。, 日期选择面板，可嵌入任意 NiceGUI 页面。 参数： semester_start: 学期开始日期，用于计算第几周；传 None 时不显示周次信息。…, card, date_type

### Community 74 - "Application Data Paths"
Cohesion: 0.17
Nodes (12): get_env_path(), Path, 运行时 .env 文件读写工具。  路径策略： - PyInstaller 打包模式：可执行文件同级目录 - 开发 / Docker 模式：当前工作目录  这与, 返回 .env 文件的绝对路径（位于用户可写数据目录）。, app_data_dir(), Path, 跨平台可写数据目录解析。  打包（PyInstaller frozen）模式下，可执行文件常被安装到只读目录 （如 Windows 的 ``Program Fi, 返回应用可写数据目录，用于 SQLite、密钥、.env、状态标记等运行期文件。      - 打包模式：定位到操作系统的「用户数据目录」并确保其存在。 (+4 more)

### Community 75 - "Homemade Teaching Feature"
Cohesion: 0.15
Nodes (11): build_homemade_teaching_filename(), P0 - Documentation & Template Analysis, P1 - Teacher Name Setting, P2 - Data Model & Repository, P3 - AI Client & Service, P4 - Word Export, P5 - UI Page & Navigation, P6 - Documentation & Regression (+3 more)

### Community 76 - "Listening Data Models"
Cohesion: 0.16
Nodes (15): ListeningDomain, ListeningImage, ListeningIndicatorResult, ListeningRecord, P1 — 一对一倾听数据模型冒烟测试（ORM + SQLite in-memory）。  用 async_session fixture（create_all）, IndicatorCatalog 可创建并保存三档标准。, ListeningRecord 可创建；adult_count 默认 1。, ListeningDomain 支持领域级年月与 3 个日期。 (+7 more)

### Community 77 - "Activity Adaptation Client"
Cohesion: 0.25
Nodes (13): adapt_activity_process(), 将活动过程按年龄段改写。      Args:         original: 活动过程原文。         grade: 年龄段，如"小班"、"中班"、, _make_client(), AsyncClient, tests/test_adapt_client.py — 年龄适配客户端测试。, AI 返回缺少 adapted_process 字段时，抛出 AiParseError。, 原文为空字符串时，不发请求直接抛出 AiParseError。, 传入自定义 system prompt 时，正常调用不报错。 (+5 more)

### Community 78 - "Observation Page Validation"
Cohesion: 0.18
Nodes (10): build_export_filename(), 构造导出文件名。 格式：{tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx, 校验大环境值是否合法（仅允许 户外/室内/公共）。, validate_big_env(), tests/test_observation_ui_helpers.py — 游戏观察 UI 工具函数测试。  测试覆盖（3 项纯函数）：   1. 导出文件名, 文件名格式为 {tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx。, 非法大环境值校验失败（返回 False 或抛异常）。, test_build_export_filename_format() (+2 more)

### Community 79 - "Password Security"
Cohesion: 0.27
Nodes (11): hash_password(), 将明文密码哈希为 Argon2 格式字符串。, verify_password(), `verify_password` 对正确密码返回 True。, `verify_password` 对错误密码返回 False。, 同一密码两次哈希结果不同（Argon2 带 salt）。, test_empty_password(), test_hash_not_equal_to_plain() (+3 more)

### Community 80 - "Manual Acceptance Verification"
Cohesion: 0.24
Nodes (12): _load_mock_helper(), _load_seed_helper(), _mock_payload(), parametrize, RuntimeError, F009 Review RED: verified worktree imports must precede app imports., Sentinel proving the test did not cross into application imports., _StopBeforeApplicationImport (+4 more)

### Community 81 - "Database Configuration Verification"
Cohesion: 0.21
Nodes (7): Path, tests/test_settings_database.py — 数据库配置区域功能测试。 验证： - write_dot_env 正确写入…, MySQL 独立字段应被组装为 mysql+aiomysql:// 格式写入 .env。, 切换到 SQLite 时，DATABASE_URL 应为空（触发 config.py 的 fallback）。, 端口配置写入 .env 的 PORT 字段。, 更新 DATABASE_URL 时不丢失已有的其他配置项。, TestDatabaseConfigSave

### Community 82 - "AI Connection Verification"
Cohesion: 0.26
Nodes (9): AiEndpointVerifier, AiEndpointCheck, OpenAI-compatible model catalog connection adapter., Sanitized endpoint check result with no response body or credential data., AsyncSession, 验证当前用户已保存的 AI 配置，不把明文 Key 返回给 UI。, verify_saved_ai_connection(), test_verify_saved_ai_connection_passes_decrypted_key_to_adapter() (+1 more)

### Community 83 - "Course Review AI Client"
Cohesion: 0.41
Nodes (10): _build_user_content(), generate_course_review_activity(), _make_client(), AsyncClient, test_generate_course_review_activity_filters_extra_keys(), test_generate_course_review_activity_invalid_string_payload_raises(), test_generate_course_review_activity_requires_boolean_fields(), test_generate_course_review_activity_success() (+2 more)

### Community 84 - "Read Projection Verification"
Cohesion: 0.36
Nodes (10): _field_names(), asyncio, AsyncSession, DailyPlan, F004 public RED tests for frozen, actor-scoped READ projections., _seed_actor_data(), test_calendar_projection_distinguishes_known_and_degraded_results(), test_context_and_class_area_projections_are_frozen_and_cropped() (+2 more)

### Community 85 - "Listening Migration Verification"
Cohesion: 0.17
Nodes (9): migrated_db(), P1 — 一对一倾听迁移与种子集成测试。  在临时 sqlite 文件库上实际执行 `alembic upgrade head`，验证： - 5 个新表创建成功, export_records 含 listening_record_id 列。, 种子 JSON：5 领域共 30 个二级指标，每个含 3 档标准、sort_order 连续。, 在临时 sqlite 文件库上执行 alembic upgrade head，返回库路径。, 每条种子三档标准非空，tenant_id=1，max_stars=3。, test_export_records_has_listening_col(), test_indicator_seed_integrity() (+1 more)

### Community 86 - "User Registration Service"
Cohesion: 0.18
Nodes (11): 自助注册： - 若系统（tenant_id=1）尚无任何用户，注册者自动成为 sys_admin（is_active=True，可立即登录）。 - 否则创建…, register_user(), 空库第一个注册用户自动成为 sys_admin（is_active=True），可立即登录。, 已有用户后，第二个注册者成为 teacher（is_active=False），需管理员审核。, 同用户名注册两次时抛出 ValueError。, 注册时传入显示名，返回的用户对象应包含该显示名。, test_first_user_becomes_sys_admin_and_active(), test_register_duplicate_username_raises() (+3 more)

### Community 87 - "Semester Data Repository"
Cohesion: 0.31
Nodes (9): get_active_semester(), list_semesters_for_tenant(), AsyncSession, date, 查询当前用户的激活学期配置，若不存在返回 None。, 保存学期配置：若已存在激活记录则更新，否则新建。 同一用户只保留一条 is_active=True 的记录。, API tenant 投影；可在当前 tenant 内按 user_id 进一步筛选。, upsert_active_semester() (+1 more)

### Community 88 - "Selection Generation Safety"
Cohesion: 0.20
Nodes (6): DateSelection, DateSelectionGuard, One immutable date selection, ordered by a local generation., Issue selections and reject work belonging to an older generation., Return the latest immutable selection, if one has been issued., Return whether ``token`` is the exact current generation and date.

### Community 89 - "Course Review UI Validation"
Cohesion: 0.29
Nodes (6): build_course_review_activity_filename(), validate_course_review_form(), test_build_course_review_activity_filename(), test_build_course_review_activity_filename_sanitizes_values(), test_validate_course_review_form_base_fields_only(), test_validate_course_review_form_requires_generated_fields()

### Community 90 - "API Router Setup"
Cohesion: 0.28
Nodes (7): APIRouter, create_api_router(), 对外只读 REST API（二期）。  通过 :func:`create_api_router` 暴露 ``/api/v1`` 路由，由 ``app/main., 返回组装好的对外 API 路由（当前仅 v1）。, AsyncClient, fixture, api_client()

### Community 91 - "Audit Logging"
Cohesion: 0.31
Nodes (8): log_audit(), 记录一条审计日志。      Args:         action: 操作标识（如 login_success / change_password / ai, tests/test_audit.py — 审计日志测试。, 审计日志携带 audit_action / tenant_id / user_id 及附加字段。, 未提供 tenant_id / user_id 时默认为 None。, test_log_audit_defaults_none_ids(), test_log_audit_emits_structured_fields(), test_log_audit_never_raises()

### Community 92 - "Secrets Configuration Verification"
Cohesion: 0.11
Nodes (19): Settings, BaseSettings, 回归测试：config.py 中密钥自动生成与 BOOTSTRAP_ADMIN_* 字段。 核心目标： 1. Settings…, 并发启动都只能返回同一组已持久化密钥，不能各自成功后丢失一组。, BOOTSTRAP_ADMIN_ENABLED 默认 False。, BOOTSTRAP_ADMIN_TENANT_ID 默认 1。, BOOTSTRAP_ADMIN_USERNAME 默认 'sysadmin'。, BOOTSTRAP_ADMIN_PASSWORD 默认空字符串。 (+11 more)

### Community 93 - "Listening AI Integration"
Cohesion: 0.29
Nodes (7): _build_context_text(), _detect_mime(), _image_to_data_url(), 一对一倾听单领域生成 AI 客户端。  针对某一领域（健康/语言/社会/艺术/科学），输入该领域 3 张幼儿绘画照片 + 班级信息 + 该领域二级指标清单，一次, 根据文件头检测图片 MIME 类型，无法识别时默认 image/jpeg。, 将图片字节转为 base64 data-url 字符串。, 构造给 AI 的说明文本（上下文 + 二级指标清单）。

### Community 94 - "Prompt Management UI"
Cohesion: 0.25
Nodes (8): _build_task_panel(), prompt_mgmt_page(), page, 构建单个任务类型的提示词编辑区块（含历史版本列表）。, _render_history(), column, label, textarea

### Community 96 - "Dependency Security Verification"
Cohesion: 0.32
Nodes (7): _minimum_versions(), Regression guard for the dependency floors frozen in GitHub Issue #49., Vulnerable families must resolve no lower than their patched release., The exact runtime graph must not contain the unpatched python-ecdsa chain., test_lock_excludes_unpatched_python_ecdsa_runtime_dependency(), test_requirements_cover_frozen_dependabot_security_floors(), _version_tuple()

### Community 97 - "AI Endpoint Validation"
Cohesion: 0.43
Nodes (6): check_ai_endpoint(), Call the provider's ``/models`` endpoint and return a sanitized result., 设置页 AI 模型端点连接 adapter 测试。, test_check_ai_endpoint_returns_sanitized_http_failure(), test_check_ai_endpoint_returns_sanitized_timeout(), test_check_ai_endpoint_uses_models_path_and_bearer_header()

### Community 98 - "Game Observation Design"
Cohesion: 0.38
Nodes (7): Game Observation Design Document, Call AI Vision Function, Game Observation Table, Game Observation Image Table, Generate Observation Function, Invite Code Table, Game Observation Progress Document

### Community 99 - "Image Configuration Verification"
Cohesion: 0.29
Nodes (5): 测试图片相关配置项（Phase A）。  验证新增的 IMAGE_STORAGE_BACKEND 和 IMAGE_MAX_BYTES 配置项存在且默认值正确，, IMAGE_MAX_BYTES 默认值为 1048576（1MB）。, IMAGE_STORAGE_BACKEND 默认值为 mysql_blob。, test_image_max_bytes_default(), test_image_storage_backend_default()

### Community 100 - "Application Entry Point"
Cohesion: 0.33
Nodes (5): main(), _on_global_exception(), 全局未捕获异常处理：记录结构化 ERROR 日志（含 traceback）。 用户友好提示由各页面自行处理（如 AI 调用失败展示 e.message）；…, Exception, PyInstaller 入口脚本。  此文件作为 kindergartenManager.spec 的 Analysis 入口， 不能用 `python -m

### Community 101 - "API Key Masking"
Cohesion: 0.53
Nodes (5): mask_api_key(), 脱敏 API Key，仅对较长密钥保留末四位。, test_mask_api_key_hides_short_key(), test_mask_api_key_shows_last_four_at_threshold(), test_mask_api_key_shows_last_four_for_long_key()

### Community 102 - "Root Page Layout"
Cohesion: 0.47
Nodes (4): page, root_page(), asyncio, test_root_redirects_to_home()

### Community 103 - "Setup Wizard"
Cohesion: 0.40
Nodes (5): page, setup_page(), asyncio, 旧 /setup 路由只保留为 /settings 兼容入口。, test_setup_redirects_to_settings()

### Community 104 - "Changelog History"
Cohesion: 0.33
Nodes (6): Six Dependabot security lower-bound upgrades, Changelog, ecdsa 0.19.2 residual risk remains outside this upgrade, Local dependency tests do not prove GitHub alert closure, Python 3.14.7 runtime unification, NiceGUI 3.16.0/FastAPI 0.141.1/Starlette compatibility baseline

### Community 105 - "Async Session Management"
Cohesion: 0.33
Nodes (5): async_session(), AsyncSession, fixture, F004 integration fixtures for the Agent Foundation public service seam., Give each Foundation integration test an isolated in-memory database.

### Community 106 - "AI Key Migration"
Cohesion: 0.40
Nodes (4): downgrade(), Upgrade schema.      列 model_name 可能已存在（来自另一台机器的未提交迁移）。     若不存在则新增；若已存在则修改为 NOT, Downgrade schema: 恢复为可空、无默认值。, upgrade()

### Community 107 - "Invitation Removal Migration"
Cohesion: 0.40
Nodes (4): downgrade(), 删除 invite_code 表（邀请码功能已移除）。, 重建 invite_code 表（回滚用）。, upgrade()

### Community 108 - "Course Review Migration"
Cohesion: 0.80
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 109 - "Homemade Teaching Plan"
Cohesion: 0.40
Nodes (5): Homemade Teaching Toy Test Plan, Test Stage P1, Test Stage P2, Test Class Repository File, Upsert Class Config Function

### Community 111 - "Class Configuration Migration"
Cohesion: 0.83
Nodes (3): downgrade(), _has_column(), upgrade()

### Community 112 - "Homemade Teaching Migration"
Cohesion: 0.83
Nodes (3): downgrade(), _has_table(), upgrade()

### Community 113 - "Export Record Migration"
Cohesion: 0.83
Nodes (3): downgrade(), _has_column(), upgrade()

### Community 115 - "Observation Image Encoding"
Cohesion: 0.50
Nodes (4): _detect_mime(), _image_to_data_url(), 根据文件头检测图片 MIME 类型，无法识别时默认 image/jpeg。, 将图片字节转为 base64 data-url 字符串。

### Community 116 - "Listening Development Progress"
Cohesion: 0.50
Nodes (4): One-on-One Listening Progress Record, Development Phase P0, Development Phase P1, Pick Three Workdays Function

### Community 117 - "Product Requirements"
Cohesion: 0.67
Nodes (4): AI 拆分、年龄适配、Word 导出与存档, 首期每日活动计划闭环, 首期产品需求文档, 角色权限与数据安全

### Community 120 - "Dependency Baseline Verification"
Cohesion: 0.67
Nodes (3): Regression guard for dependency versions raised by Dependabot., _requirements_by_name(), test_dependabot_security_floors_are_not_downgraded()

### Community 121 - "Release Build Workflow"
Cohesion: 0.67
Nodes (3): Release build workflow, Python 3.14.7 release build runtime, Windows/Linux/Docker release artifacts

### Community 136 - "Contribution Guidelines"
Cohesion: 0.67
Nodes (3): Agent rejection and zero-change verification, Agent implementation rules: closed registry, no WRITE or persistence, Contributing guide

### Community 137 - "AI Word Boundary Decision"
Cohesion: 0.67
Nodes (3): Existing AI adapter and teacher-adoption boundaries apply to future Agent, ADR-0004 AI and fixed Word boundaries, Existing one-shot AI functions cannot be exposed as arbitrary Agent Tools

### Community 138 - "Architecture Decisions"
Cohesion: 0.67
Nodes (3): Accepted ADR-0005 Agent registry entry, Agent Tool, permission, memory, or write changes require a new ADR, ADR index

### Community 139 - "Security Threat Model"
Cohesion: 1.00
Nodes (3): Security lower bounds and dependency audit are production gates, Dependency and release supply-chain threat, Security threat model

### Community 140 - "Future Services Architecture"
Cohesion: 1.00
Nodes (3): Future Microservice Decomposition, Main Application (app/integration/), Services Directory Status README

### Community 141 - "Daily Plan Prompt Design"
Cohesion: 0.67
Nodes (3): 一日活动节假日语义, 一日活动提示词版本管理, 一日活动提示词与一键生成

### Community 142 - "Homemade Teaching Design"
Cohesion: 1.00
Nodes (3): Homemade Teaching Design Document, Generate Homemade Teaching Function, Homemade Teaching Toy Table

## Knowledge Gaps
- **142 isolated node(s):** `一日活动节假日语义`, `一日活动提示词版本管理`, `课程审议手动流程验收`, `一日活动教案处理流水线`, `课程审议持久化与历史导出` (+137 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **52 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TrustedActor` connect `Agent Composition UI` to `Application Pages`, `Zero Persistence Matrix`, `Agent Context Projection`, `Composition UI Verification`, `Runtime Lifecycle Safety`, `Agent Runtime Controls`, `Agent Contracts`, `Plan Draft Projection`, `Provider Runtime Verification`, `Closed Tool Executor Verification`, `Plan Patch Verification`, `Provider Adapter Verification`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Why does `save_daily_plan()` connect `Browser Mock Helpers` to `Application Pages`, `Daily Plan Repository`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `One-on-One Listening Subsystem` connect `Listening Image Repository` to `Image Processing Errors`, `Listening Document Export`, `Export Record Repository`, `Indicator Catalog Repository`, `Workday Calendar Service`, `Listening Record Services`, `Listening Content Services`, `Listening AI Verification`, `Listening Activity Page`, `Application Architecture Overview`, `Migration Integration Verification`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `AgentContext` (e.g. with `build_plan_patch()` and `build_plan_patch_from_arguments()`) actually correct?**
  _`AgentContext` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `TrustedActor` (e.g. with `create_daily_plan_agent_controller()` and `_context()`) actually correct?**
  _`TrustedActor` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 34 inferred relationships involving `Permission` (e.g. with `_call()` and `test_rejected_calls_fail_before_opening_a_session()`) actually correct?**
  _`Permission` has 34 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `AiParseError` (e.g. with `test_adapt_empty_original_raises_parse_error()` and `test_adapt_missing_adapted_process_raises_parse_error()`) actually correct?**
  _`AiParseError` has 12 INFERRED edges - model-reasoned connections that need verification._