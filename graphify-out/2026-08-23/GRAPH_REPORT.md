# Graph Report - KindergartenManager  (2026-08-23)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2180 nodes · 4725 edges · 136 communities (121 shown, 15 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 241 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a4d91439`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- listening_exporter.py
- get_active_ai_key
- listening_service.py
- BlobImageStorage
- export_daily_plan
- Dependency security baseline
- ADR-0005 controlled AI Agent runtime
- AiCallError
- database.py
- save_new_version
- test_generate_client.py
- test_auth_service.py
- test_migrations_smoke.py
- pages/game_observation.py
- export_observation
- _seed
- auth_service.py
- one_on_one_listening.py
- exceptions.py
- MockTransport
- app_shell.py
- AppError
- 课程审议记录子系统设计文档
- pick_three_workdays
- course_review_activity_exporter.py
- DailyPlan
- list_images_by_record
- Homemade teaching toy design
- verify_signature
- list_indicators
- config.py
- CryptoError
- AiParseError
- save_export_record
- generate_listening_domain
- test_listening_service.py
- bootstrap_admin.py
- compute_diff
- user_admin.py
- User
- read_dot_env
- export_homemade_teaching
- process_lesson_plan
- CourseReviewActivity
- ConfigError
- generate_observation
- mark_setup_complete
- startup.py
- split_lesson_plan
- test_observation_ui_helpers.py
- AuthMiddleware
- app_data_dir
- HomemadeTeachingToy
- test_holiday_client.py
- make_response
- Project Structure
- graphify skill
- Graphify Pipeline
- adapt_activity_process
- pages/course_review_activity.py
- hash_password
- add_image
- pages/homemade_teaching.py
- Repository Guidelines
- main.py
- get_legal_holidays_in_year
- generate_activity_content
- ._update_info
- test_listening_migration.py
- codebase-memory 14 MCP Tools
- generate_course_review_activity
- is_near_holiday
- create_pending_user
- register_user
- get_week_number
- profile.py
- test_observation_service.py
- Extraction Spec
- log_audit
- is_within_semester
- test_config_image_settings.py
- Controlled AI Agent Boundary
- 46b9fd5613c3_add_model_name_to_ai_api_key.py
- 4e2e0e079e56_drop_invite_code_table.py
- a6c4d8e2f9b1_add_course_review_activity.py
- _make_settings
- test_python_runtime_baseline.py
- Alembic-only schema changes
- 2f7a9c1d4e8b_add_teacher_name_to_class_config.py
- 7c1e2a9b5d4f_add_homemade_teaching_toy.py
- d5e4f3a2b1c0_add_homemade_teaching_id_to_export_records.py
- e2a3f1b8c9d0_expand_prompt_task_type_enum.py
- Single-user UI decision
- 项目进度记录
- test_dependency_security_baseline.py
- AI client integration boundary
- Word export instructions
- Production Docker Compose
- ADR-0001 modular monolith baseline
- Data locations and backup guidance
- build-deb.sh
- postinst
- postrm
- prerm
- AI Client Integration
- Entry Points
- Risk Labels
- Development Compose override

## God Nodes (most connected - your core abstractions)
1. `AiParseError` - 54 edges
2. `DailyPlan` - 37 edges
3. `Base` - 37 edges
4. `get_active_ai_key()` - 35 edges
5. `ConfigError` - 35 edges
6. `log_audit()` - 35 edges
7. `save_ai_key()` - 31 edges
8. `AuthError` - 31 edges
9. `get_logger()` - 31 edges
10. `MockTransport` - 31 edges

## Surprising Connections (you probably didn't know these)
- `Python 3.14.7 release build runtime` --semantically_similar_to--> `Python 3.14.7 cross-environment runtime`  [INFERRED] [semantically similar]
  .github/workflows/release.yml → memory-bank/tech-stack.md
- `requirements.txt >= safety floors without a hash lock` --semantically_similar_to--> `Six Dependabot security lower-bound upgrades`  [INFERRED] [semantically similar]
  docs/DEPENDENCIES.md → CHANGELOG.md
- `NiceGUI 3.16.0/FastAPI 0.141.1/Starlette compatibility baseline` --semantically_similar_to--> `Joint Web baseline: NiceGUI 3.16.0 + FastAPI 0.141.1 + Starlette 1.6.0`  [INFERRED] [semantically similar]
  CHANGELOG.md → docs/DEPENDENCIES.md
- `NiceGUI 3.16.0, FastAPI 0.141.1, and Starlette 1.6.0 baseline` --semantically_similar_to--> `Joint Web baseline: NiceGUI 3.16.0 + FastAPI 0.141.1 + Starlette 1.6.0`  [INFERRED] [semantically similar]
  README.md → docs/DEPENDENCIES.md
- `ecdsa 0.19.2 residual risk remains outside this upgrade` --semantically_similar_to--> `python-jose transitive ecdsa 0.19.2 residual risk with no upstream fix`  [INFERRED] [semantically similar]
  CHANGELOG.md → docs/DEPENDENCIES.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Foundation Agent Controlled Runtime** — agents_md_foundation_agent, agents_md_plan_patch, docs_adr_adr_0005_controlled_ai_agent_runtime_md, docs_design_agent_runtime_md, agents_md_controlled_ai_agent_boundary [EXTRACTED 1.00]
- **Graphify Extraction Pipeline** — agents_skills_graphify_skill_md_ast_extraction, agents_skills_graphify_skill_md_semantic_extraction, agents_skills_graphify_skill_md_gemini_backend, agents_skills_graphify_skill_md_community_detection, agents_skills_graphify_skill_md_graph_json, agents_skills_graphify_skill_md_graph_report [EXTRACTED 1.00]
- **Graphify Reference Documentation** — agents_skills_graphify_references_extraction_spec_md, agents_skills_graphify_references_query_md, agents_skills_graphify_references_update_md, agents_skills_graphify_references_exports_md, agents_skills_graphify_references_add_watch_md, agents_skills_graphify_references_github_and_merge_md, agents_skills_graphify_references_hooks_md, agents_skills_graphify_references_transcribe_md [EXTRACTED 1.00]
- **Agent Foundation scope and application boundaries** — docs_adr_adr_0005_controlled_ai_agent_runtime_single_agent_provider_boundary, docs_adr_adr_0005_controlled_ai_agent_runtime_read_draft_zero_persistence, docs_design_agent_runtime_closed_registry_service_projection, docs_design_system_architecture_agent_layer_boundary, docs_roadmap_r4a_read_draft_scope [INFERRED 0.85]
- **Agent zero-persistence boundary and future WRITE gate** — docs_design_agent_runtime_short_context_planpatch, docs_design_data_model_agent_no_persistence, docs_roadmap_r4b_write_independent, docs_design_data_model_agent_write_revision_gate [INFERRED 0.85]
- **Homemade teaching design, delivery, and verification** — memory_bank_homemadeteaching_design_generation_contract, memory_bank_homemadeteaching_dev_plan_phased_delivery, memory_bank_homemadeteaching_progress_completion_evidence, memory_bank_homemadeteaching_test_plan_test_matrix [INFERRED 0.85]
- **Joint NiceGUI/FastAPI/Starlette compatibility baseline** — docs_dependencies_joint_framework_baseline, changelog_web_framework_security_baseline, readme_web_framework_baseline, memory_bank_tech_stack_python_monolith [INFERRED 0.85]
- **Listening design, implementation, and acceptance** — memory_bank_one_on_one_listening_design_five_domain_observation, memory_bank_one_on_one_listening_dev_plan_staged_delivery, memory_bank_one_on_one_listening_progress_manual_acceptance_pending, memory_bank_one_on_one_listening_test_plan_manual_acceptance [INFERRED 0.85]
- **计划中的服务拆分及其门禁** — memory_bank_overview_microservice_topology, services_readme_current_in_process, services_readme_split_gates [INFERRED 0.85]
- **Python runtime, test, packaging, and Docker verification evidence** — docs_dependencies_python_3147_official_source, docs_dependencies_local_validation_533_passed, docs_dependencies_pyinstaller_6222_smoke_success, docs_dependencies_docker_3147_slim_tag_available, docs_dependencies_docker_build_unverified [INFERRED 0.85]

## Communities (136 total, 15 thin omitted)

### Community 0 - "listening_exporter.py"
Cohesion: 0.06
Nodes (63): _build_domain_doc(), _build_from_scratch(), _clear_cell(), _domain_of_title(), export_batch_by_domain(), export_combined(), export_split_by_domain(), _extract_block() (+55 more)

### Community 1 - "get_active_ai_key"
Cohesion: 0.06
Nodes (43): AiApiKey, get_active_ai_key(), AsyncSession, 加密 API Key 后入库，同时将该用户同类型旧记录标记为 inactive。      Args:         session: 异步数据库会话。, 查询该用户当前激活的 AI Key 记录。      Args:         session: 异步数据库会话。         tenant_id: 租户, save_ai_key(), _mask_api_key(), AI 接口配置页面（路由 /setup）。  简化后的单页面：仅配置 AI 文本模型接口信息（Base URL、API Key、模型名称）。 系统默认使用 SQ (+35 more)

### Community 2 - "listening_service.py"
Cohesion: 0.08
Nodes (57): ListeningDomain, ListeningIndicatorResult, ListeningRecord, delete_domains_by_record(), delete_indicator_results_by_record(), delete_record(), get_record_by_id(), list_domains_by_record() (+49 more)

### Community 3 - "BlobImageStorage"
Cohesion: 0.05
Nodes (49): ABC, ImageStorageBackend, 存储图片字节，返回存储引用 dict。          Returns:             dict，键因后端而异（blob_backend 含 blo, 从存储引用还原图片字节。          Args:             stored: 与 put 返回格式相同的 dict。          Ret, 可插拔图片存储后端抽象。      put / get 与数据库 session 解耦：     - put 返回 stored_ref dict，由 repo, BlobImageStorage, MySQL BLOB 图片存储后端。  put/get 只操作内存 dict，实际 DB 写入由 repository 层完成。, MySQL BLOB 后端：图片二进制存入 game_observation_image.blob_content。 (+41 more)

### Community 4 - "export_daily_plan"
Cohesion: 0.09
Nodes (34): _build_collective_cell(), export_batch_daily_plans(), export_daily_plan(), _export_from_scratch(), _fill_fields_cell(), _fill_plain_cell(), _fill_process_cell(), _fill_template() (+26 more)

### Community 5 - "Dependency security baseline"
Cohesion: 0.06
Nodes (49): Release build workflow, Python 3.14.7 release build runtime, Windows/Linux/Docker release artifacts, Six Dependabot security lower-bound upgrades, Changelog, ecdsa 0.19.2 residual risk remains outside this upgrade, Local dependency tests do not prove GitHub alert closure, Python 3.14.7 runtime unification (+41 more)

### Community 6 - "ADR-0005 controlled AI Agent runtime"
Cohesion: 0.07
Nodes (49): Agent rejection and zero-change verification, Agent implementation rules: closed registry, no WRITE or persistence, Contributing guide, Existing AI adapter and teacher-adoption boundaries apply to future Agent, ADR-0004 AI and fixed Word boundaries, Existing one-shot AI functions cannot be exposed as arbitrary Agent Tools, ADR-0005 controlled AI Agent runtime, Future WRITE as an independent milestone (+41 more)

### Community 7 - "AiCallError"
Cohesion: 0.14
Nodes (21): AiCallError, AI 接口调用失败时抛出：HTTP 4xx/5xx、网络超时、超过重试次数等。, call_ai_vision(), _make_retry_decorator(), AsyncClient, 构造 tenacity 重试装饰器：最多 3 次，指数退避 2s → 4s → 8s。, 发送多模态 Chat Completions 请求，返回解析后的 dict。      Args:         messages: 消息列表，content, _make_error_response() (+13 more)

### Community 8 - "database.py"
Cohesion: 0.08
Nodes (27): Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online(), Base, _build_engine(), get_async_session(), AsyncSession (+19 more)

### Community 9 - "save_new_version"
Cohesion: 0.07
Nodes (30): list_versions(), AsyncSession, 将指定版本设为激活，其余版本设为 inactive。      Args:         session: 异步数据库会话。         tenant_i, 返回指定任务类型的所有版本，按版本号降序排列。      Args:         session: 异步数据库会话。         tenant_id:, 保存新版本提示词，自动递增版本号并将旧激活记录设为 inactive。      Args:         session: 异步数据库会话。, rollback_to_version(), save_new_version(), _build_task_panel() (+22 more)

### Community 10 - "test_generate_client.py"
Cohesion: 0.07
Nodes (44): _build_prefix(), _build_user_content(), generate_activity(), _holiday_hint(), 一日活动生成客户端 — 包含 5 种活动类型的内置默认提示词。  任务类型对应关系： - morning_exercise  →  晨间活动 - morning, 构建消息开头的班级与教学周信息。      context 支持 grade、class_name、week_number、weekday 字段；     we, 当 near_holiday 为 True 时返回临近节假日提示行，否则返回空字符串。      near_holiday 取值：True 表示明日为法定节假日, 根据任务类型和上下文构建发送给 AI 的用户消息。      context 支持以下字段：         grade, class_name, activi (+36 more)

### Community 11 - "test_auth_service.py"
Cohesion: 0.11
Nodes (43): AuthError, 鉴权失败：token 无效、已过期、签名错误或用户名密码错误时抛出。          故意不区分"用户不存在"和"密码错误"，防止用户枚举攻击。, approve_user(), create_user_by_admin(), login(), AsyncSession, 审核通过：将指定用户的 is_active 设为 True。      Args:         session: 异步数据库会话。         tena, 验证用户名和密码，成功则返回 JWT access token。      用户不存在或密码错误时统一抛出 AuthError，不区分具体原因。     账号被 (+35 more)

### Community 12 - "test_migrations_smoke.py"
Cohesion: 0.10
Nodes (23): GameObservation, GameObservation — 游戏观察记录数据模型。  每条记录对应教师的一次游戏观察，包含元数据（日期/环境/人员） 和 AI 生成的四段内容（观察目标, PromptTemplate, observation_repository — 游戏观察记录数据访问层。  所有查询强制携带 tenant_id 过滤，确保多租户数据隔离。, Phase B — 数据模型冒烟测试（ORM + SQLite in-memory）。  测试策略： - 用 async_session fixture（SQL, GameObservation 可插入并按 id 查询。, GameObservation.tenant_id 非空约束生效。, GameObservationImage.blob_content 可存取二进制字节，值完全相同。 (+15 more)

### Community 13 - "pages/game_observation.py"
Cohesion: 0.11
Nodes (32): get_current_user(), 单用户模式：提供固定的默认用户上下文。  取消登录功能后，所有页面通过此模块获取当前用户信息， 而非从 JWT token 中解析。, 返回当前用户信息字典（单用户模式下始终返回默认管理员）。, get_class_config(), AsyncSession, 查询当前用户的班级配置，若不存在返回 None。, 保存班级配置：若已存在则更新，否则新建。     每个用户只保留一条班级配置记录（最新）。, upsert_class_config() (+24 more)

### Community 14 - "export_observation"
Cohesion: 0.11
Nodes (36): _add_images_to_cell(), _build_from_scratch(), _clear_cell(), export_observation(), _fill_template(), Document, Path, RGBColor (+28 more)

### Community 15 - "_seed"
Cohesion: 0.17
Nodes (3): _seed(), TestDailyPlans, TestSignature

### Community 16 - "auth_service.py"
Cohesion: 0.12
Nodes (33): UserRole, create_user(), get_user_by_id(), has_any_user(), list_users_by_tenant(), AsyncSession, query_users_by_tenant(), 用户数据访问层。  所有查询必须携带 tenant_id 过滤条件，确保多租户数据隔离。 (+25 more)

### Community 17 - "one_on_one_listening.py"
Cohesion: 0.10
Nodes (34): _auto_pick_workdays(), build_batch_export_filename(), build_export_filename(), default_year_month(), distribute_images_by_filename(), format_record_summary(), format_stage_label(), infer_age_by_grade() (+26 more)

### Community 18 - "exceptions.py"
Cohesion: 0.14
Nodes (19): 审计日志：记录关键操作（登录、改密、AI 调用、Word 导出等）。  审计日志通过结构化 JSON logger 输出，统一携带 audit_action 与, get_logger(), 年龄适配 AI 客户端。  将活动过程原文按年龄段（小班/中班/大班）改写，返回改写后文本。  输出 Schema：     {"adapted_process, AI 客户端基础模块 — 通用 Chat Completions 调用。  所有 AI 调用必须通过此模块，禁止在 service 层直接发 HTTP 请求。, 教案拆分 AI 客户端。  调用 OpenAI 兼容接口，将完整教案文本拆分为结构化字段。  输出 Schema（5 个必填键）：     activity_g, 一对一倾听单领域生成 AI 客户端。  针对某一领域（健康/语言/社会/艺术/科学），输入该领域 3 张幼儿绘画照片 + 班级信息 + 该领域二级指标清单，一次, 游戏观察生成 AI 客户端。  调用 OpenAI 兼容多模态接口，输入 1~3 张游戏照片 + 元数据， 输出「观察目标 / 观察记录 / 评价分析 / 支持, AI 视觉客户端基础模块 — 多模态 Chat Completions 调用。  所有视觉 AI 调用必须通过此模块，禁止在 service 层直接发 HTTP (+11 more)

### Community 19 - "MockTransport"
Cohesion: 0.18
Nodes (10): get_holiday_name(), 返回法定节假日名称，如"国庆节"、"春节"。      返回语义：     - str  ：该日期是法定节假日，返回节日名称（如"国庆节"）     - Non, MockTransport, Request, Response, 法定节假日且 API 返回 holiday 对象时，取其 name 字段, 法定节假日但 holiday 字段为 null 时，从 type.name 取名称, 先调用 is_holiday，再调用 get_holiday_name，不发出额外 HTTP 请求 (+2 more)

### Community 20 - "app_shell.py"
Cohesion: 0.09
Nodes (21): app_shell(), get_display_name(), get_menu_items(), 共享布局组件 app_shell。  提供统一的左侧导航菜单 + 顶栏，供所有页面复用。  纯函数（可在 NiceGUI 渲染外调用，支持单测）： - get_, 返回顶栏显示名：优先 display_name，回退 username。      Args:         user: 包含用户信息的字典，通常来自 dec, 统一布局：左侧分组菜单 + 顶栏。      用法::          async with app_shell(user, active="daily-pl, 根据角色返回可见菜单项列表，每项含 selected 标记。      Args:         role: 用户角色，如 'teacher' / 'teac, home_page() (+13 more)

### Community 21 - "AppError"
Cohesion: 0.11
Nodes (29): AppError, 通用业务异常：输入非法、文件格式错误等非 AI / 非鉴权类业务错误。, compress_image(), CompressedImage, normalize_to_landscape(), 图片压缩处理模块（游戏观察子系统）。  `compress_image` 将任意图片字节压缩至指定大小上限： - 超限时等比缩放 + 逐步降低 JPEG 质量直, 将图片统一为横版（宽 ≥ 高）。      处理步骤：       1. 按 EXIF 方向校正（手机照片常见）。       2. 透明通道转白底 RGB。, 将图片字节压缩至 max_bytes 以内。      Args:         data: 原始图片字节（JPEG / PNG / WebP 等 Pillo (+21 more)

### Community 22 - "课程审议记录子系统设计文档"
Cohesion: 0.11
Nodes (32): 课程审议 AI 结构化 JSON 合约, 课程审议记录子系统设计文档, 课程审议持久化与历史导出, 课程审议 Word 模板映射, 课程审议 AI 客户端与服务层, 课程审议记录子系统开发计划, 课程审议分阶段交付, 课程审议 Word 导出阶段 (+24 more)

### Community 23 - "pick_three_workdays"
Cohesion: 0.12
Nodes (12): get_weekday_cn(), is_workday(), pick_three_workdays(), date, 日期计算服务 — 纯函数，无 IO，无数据库依赖。, 仅根据是否为周六/周日判断工作日（节假日由独立客户端判断，不耦合此处）。, 从指定年月的全部工作日中随机选取 3 个不同日期，按时间升序返回。      用于「一对一倾听」自动选取 3 个观察工作日（分布于全月，避免总是月初、1 号）。, Random (+4 more)

### Community 24 - "course_review_activity_exporter.py"
Cohesion: 0.18
Nodes (28): _build_from_scratch(), _clear_cell(), _clear_paragraph(), export_course_review_activity(), _fill_template(), _get_bool(), _get_value(), _iter_body_blocks() (+20 more)

### Community 25 - "DailyPlan"
Cohesion: 0.08
Nodes (45): ApiPrincipal, get_db(), AsyncSession, 对外 REST API 的 FastAPI 依赖。, 提供独立的异步数据库会话（只读查询，无需提交）。      测试可通过 ``app.dependency_overrides[get_db]`` 注入内存库会话, get_daily_plan(), health(), date (+37 more)

### Community 26 - "list_images_by_record"
Cohesion: 0.11
Nodes (26): ListeningImage, add_image(), delete_images_by_record(), get_image(), list_images_by_record(), AsyncSession, listening_image_repository — 一对一倾听图片数据访问层。, 新增一张倾听绘画图片记录，返回带 id 的对象。 (+18 more)

### Community 27 - "Homemade teaching toy design"
Cohesion: 0.12
Nodes (29): Homemade teaching toy design, Structured homemade-toy AI generation contract, Teacher/class snapshot and tenant-isolated persistence, Fixed homemade-teaching Word template mapping, Homemade teaching toy development plan, P0-P6 phased implementation plan, Test-first implementation and manual handoff, Homemade teaching completion evidence (+21 more)

### Community 28 - "verify_signature"
Cohesion: 0.13
Nodes (13): _build_signing_string(), get_api_principal(), parse_api_keys(), Request, 对外 REST API 鉴权：API Key + 可选 HMAC 签名。  鉴权模型（服务间调用）： 1. **API Key**（必填）：调用方在 `X-Ap, 解析 `API_KEYS` 配置为 {api_key: tenant_id} 映射。      格式："key1:1,key2:2"；忽略空段与格式非法段（te, 校验 HMAC-SHA256 请求签名与时间戳新鲜度。, FastAPI 依赖：校验 API Key（必填）与签名（按配置可选），返回调用方主体。 (+5 more)

### Community 29 - "list_indicators"
Cohesion: 0.14
Nodes (26): IndicatorCatalog, get_indicator_by_id(), list_available_stages(), list_indicators(), list_indicators_by_ids(), AsyncSession, indicator_repository — 指标目录数据访问层。  只读参考数据查询（指标目录按 tenant_id + grade + term + dom, 查询某 (年级, 学期, 领域) 的全部二级指标，按 sort_order 升序。 (+18 more)

### Community 30 - "config.py"
Cohesion: 0.09
Nodes (26): Path, 应用配置：通过 pydantic-settings 从 .env 文件和环境变量加载。  首次部署（无 .env 文件）时的行为： - DATABASE_URL, 返回自动生成密钥的持久化文件路径（位于用户可写数据目录）。, 解析 key=value 文件，忽略空行与注释行。, 将新键值追加/覆盖到持久化文件（已有键保留）。, 自动生成缺失的密钥并持久化，保证重启后可还原。, _read_kv_file(), _secrets_file_path() (+18 more)

### Community 31 - "CryptoError"
Cohesion: 0.10
Nodes (16): decrypt(), encrypt(), 应用层对称加密工具（Fernet）。  密钥来源：Settings.ENCRYPTION_KEY（原始字符串，UTF-8 编码后取前 32 字节， 再经 bas, 加密明文字符串，返回 URL-safe base64 密文字符串。      Args:         plain_text: 待加密的明文（禁止在调用方写入, 解密密文字符串，还原为原始明文。      Args:         cipher_text: 由 `encrypt()` 生成的密文字符串。      Re, CryptoError, 加解密失败时抛出：密文被篡改、密钥不匹配或格式非法。, tests/test_crypto.py — app/core/crypto.py 单元测试。  测试覆盖： 1. 加密后字符串不等于原文。 2. 加密后再解密 (+8 more)

### Community 32 - "AiParseError"
Cohesion: 0.10
Nodes (33): AiParseError, AI 返回内容解析失败时抛出：JSON 格式非法、缺少必要字段等。, call_ai(), call_ai_text(), _make_retry_decorator(), AsyncClient, 发送 Chat Completions 请求，返回纯文本 content 字符串。      与 call_ai() 的区别：不强制 json_object 格, 构造 tenacity 重试装饰器：最多 3 次，指数退避 2s → 4s → 8s。 (+25 more)

### Community 33 - "save_export_record"
Cohesion: 0.13
Nodes (22): ExportRecord, AsyncSession, 写入一条导出记录。      Args:         session: 异步数据库会话（调用方负责事务管理）。         tenant_id: 机构, save_export_record(), tests/test_export_repository.py — 导出记录仓库层测试。  使用 SQLite 内存库（async_session fixtur, 写入倾听导出记录时，listening_record_id 字段正确持久化。, 未传 listening_record_id 时，字段默认为 None（向后兼容）。, 写入自制教玩具导出记录时，homemade_teaching_id 字段正确持久化。 (+14 more)

### Community 34 - "generate_listening_domain"
Cohesion: 0.13
Nodes (23): _build_context_text(), _detect_mime(), generate_listening_domain(), _image_to_data_url(), 调用视觉 AI 生成某领域的一对一倾听结构化内容。      Args:         images: 该领域绘画图片字节列表（经压缩后的 bytes，至少, 根据文件头检测图片 MIME 类型，无法识别时默认 image/jpeg。, 将图片字节转为 base64 data-url 字符串。, 构造给 AI 的说明文本（上下文 + 二级指标清单）。 (+15 more)

### Community 35 - "test_listening_service.py"
Cohesion: 0.13
Nodes (23): _clamp_star(), generate_domain_content(), 将 load_record_detail 结果转为 exporter 入参 (record, domains)（纯函数）。      images → [(da, 将星级归一化为 1~3 的整数，非法值回退默认。, 调用视觉 AI 生成某领域的一对一倾听内容，返回结构化结果。      Args:         session: 异步数据库会话。         tena, to_export_payload(), _ai_return(), P5 — 一对一倾听服务层测试。  覆盖：未配置视觉 Key、正常生成、指标缺失补默认 3 星、DB 提示词覆盖、整记录持久化。 (+15 more)

### Community 36 - "bootstrap_admin.py"
Cohesion: 0.16
Nodes (17): bootstrap_admin(), _main(), _prompt_password(), _prompt_str(), 系统管理员初始化脚本。  模式：   --init           创建 sys_admin 账号（默认模式）   --reset-password 重置, --init 模式：创建 sys_admin 账号。, --reset-password 模式：重置 sys_admin 密码。, 重置 sys_admin 密码（需旧密码验证），返回执行结果说明。 (+9 more)

### Community 37 - "compute_diff"
Cohesion: 0.14
Nodes (19): compute_diff(), 差异比对服务 — 使用 difflib 对原文与改写文进行逐句比对。  分句规则：以句号（。）、问号（？）、感叹号（！）、换行符为分隔符， 保留分隔符到句子末尾, 将文本按标点符号或换行符拆分为句子列表，过滤空串。, 对原文与改写文按句比对，返回带 changed 标记的句子列表。      Args:         original: 活动过程原文。         ad, _split_sentences(), tests/test_diff_service.py — 差异比对服务测试。, 完全相同的文本，所有句子 changed 为 False。, 修改一句后，该句 changed 为 True，其余句子不变。 (+11 more)

### Community 38 - "user_admin.py"
Cohesion: 0.17
Nodes (17): create_access_token(), decode_access_token(), JWT access token 生成与解码工具。, 生成 JWT access token。      payload 字段：     - sub: str(user_id)     - tenant_id: i, 解码并验证 JWT token，返回 payload 字典。      token 过期、签名无效等情况统一抛出 AuthError。, _get_current_user(), 系统管理员账号管理页面（路由：/user-admin）。  阶段二能力： - 系统管理员创建账号 - 列表筛选与分页 - 账号启停 - 管理员重置密码, user_admin_page() (+9 more)

### Community 39 - "User"
Cohesion: 0.17
Nodes (17): ensure_default_user(), AsyncSession, 应用启动引导：确保默认用户存在。  单用户模式下，系统启动时自动在 user 表中创建默认管理员账号。 如果已存在则跳过（幂等）。, 确保默认用户存在，不存在则创建。已存在则跳过。, User, User.display_name 可为 None（可空）。, User.display_name 可更新为字符串。, test_user_display_name_nullable() (+9 more)

### Community 40 - "read_dot_env"
Cohesion: 0.14
Nodes (15): 解析 .env 文件，返回 key-value 字典。      忽略空行与 # 开头的注释行。文件不存在时返回空字典。, 将 updates 中的 key-value 原子写入 .env，保留其余行不动。      若 .env 不存在则自动创建。写入失败时抛出 RuntimeEr, read_dot_env(), write_dot_env(), Path, 测试 app.core.env_writer 模块。  覆盖： - read_dot_env()：文件不存在返回 {}；解析 key=value；忽略注释和空行, 值中包含 = 时，仅在第一个 = 处分割。, TestReadDotEnv (+7 more)

### Community 41 - "export_homemade_teaching"
Cohesion: 0.24
Nodes (18): _build_from_scratch(), _clear_cell(), export_homemade_teaching(), _fill_template(), _get_value(), Any, Document, Path (+10 more)

### Community 42 - "process_lesson_plan"
Cohesion: 0.17
Nodes (19): LessonPlanResult, process_lesson_plan(), AsyncSession, 教案拆分与年龄适配的完整结果。      Attributes:         activity_goal: 活动目标（AI 拆分原文）。         a, 完整教案拆分与年龄适配流程。      Args:         session: 异步数据库会话（用于查询 AI Key）。         tenant_, _make_mock_ai_client(), _make_mock_ai_key(), AsyncClient (+11 more)

### Community 43 - "CourseReviewActivity"
Cohesion: 0.28
Nodes (15): CourseReviewActivity, 课程审议记录。      每条记录保存一次课程审议生成与教师编辑后的结果。班级、年龄段与教师姓名     采用冗余快照，避免后续系统设置变更影响历史导出。, create_course_review_activity(), delete_course_review_activity(), get_course_review_activity(), list_course_review_activities(), AsyncSession, 删除课程审议记录，强制 tenant_id + user_id 双重过滤。 (+7 more)

### Community 44 - "ConfigError"
Cohesion: 0.22
Nodes (16): ConfigError, Exception, 业务配置缺失时抛出：如用户尚未配置 AI Key。, generate_course_review_activity_content(), AsyncSession, generate_homemade_teaching_content(), AsyncSession, _make_mock_ai_key() (+8 more)

### Community 45 - "generate_observation"
Cohesion: 0.14
Nodes (19): _build_context_text(), _detect_mime(), generate_observation(), _image_to_data_url(), 将上下文 dict 转为给 AI 的说明文本。, 根据文件头检测图片 MIME 类型，无法识别时默认 image/jpeg。, 将图片字节转为 base64 data-url 字符串。, 调用视觉 AI 生成游戏观察记录四段内容。      Args:         images: 图片字节列表（1~3 张，经压缩后的 bytes）。 (+11 more)

### Community 46 - "mark_setup_complete"
Cohesion: 0.23
Nodes (9): is_setup_complete(), mark_setup_complete(), 检查系统是否已完成初始化配置（同步调用，纯文件检查，无 DB 查询）。, 写入 setup 完成标记文件。写入失败时静默忽略（不阻断正常流程）。, Path, 测试 app.core.setup_state 模块。  注意：setup_state 标记文件机制在单用户模式重构中已弃用。 这些测试保留以确保模块本身未被破, TestIsSetupComplete, TestMarkSetupComplete (+1 more)

### Community 47 - "startup.py"
Cohesion: 0.17
Nodes (12): build_sync_url(), _get_alembic_ini_path(), _get_alembic_script_location(), 应用启动模块：自动执行 Alembic 数据库迁移。  支持三种运行模式： - 开发模式（python -m app.main）：直接运行，alembic.in, 将异步驱动 URL 转换为 Alembic 所需的同步驱动 URL。      迁移（alembic/env.py）与应用运行时（app/core/databa, 在应用启动时自动执行 alembic upgrade head。      迁移失败时记录错误日志但不阻断启动，允许应用以降级模式运行（     例如数据库暂时, run_startup_migrations(), tests/test_settings_database.py — 数据库配置区域功能测试。  验证： - write_dot_env 正确写入 DATABAS (+4 more)

### Community 48 - "split_lesson_plan"
Cohesion: 0.21
Nodes (15): 将完整教案文本拆分为结构化字段。      Args:         raw_text: 用户粘贴的完整教案文本。         api_base_url:, split_lesson_plan(), _make_client(), AsyncClient, tests/test_lesson_plan_client.py — 教案拆分客户端测试。  使用 httpx.MockTransport 隔离真实 HTTP, AI 返回空 dict 时，抛出 AiParseError。, AI 返回额外字段时，只保留 5 个必要键。, 正常响应时，返回包含全部 5 个键的 dict。 (+7 more)

### Community 49 - "test_observation_ui_helpers.py"
Cohesion: 0.17
Nodes (15): build_export_filename(), 构造导出文件名。      格式：{tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx, 校验大环境值是否合法（仅允许 户外/室内/公共）。, 校验图片数量是否在合法范围（1~3 张）。, validate_big_env(), validate_image_count(), tests/test_observation_ui_helpers.py — 游戏观察 UI 工具函数测试。  测试覆盖（3 项纯函数）：   1. 导出文件名, 文件名格式为 {tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx。 (+7 more)

### Community 50 - "AuthMiddleware"
Cohesion: 0.17
Nodes (10): AuthMiddleware, Request, 路由守卫中间件（已禁用 — 单用户模式无需登录）。  保留模块以便后续恢复登录功能。当前为直通中间件，不做任何鉴权检查。 根路径 (/) 重定向到 /home。, 单用户模式：仅将根路径重定向到 /home，其余请求直接放行。, BaseHTTPMiddleware, tests/test_middleware.py — 单用户模式路由中间件测试。  验证： - 根路径 (/) 重定向到 /home - 其他路由直接放行，无认, 中间件可被实例化（接收 ASGI app 参数）。, test_middleware_instantiable() (+2 more)

### Community 51 - "app_data_dir"
Cohesion: 0.17
Nodes (12): get_env_path(), Path, 运行时 .env 文件读写工具。  路径策略： - PyInstaller 打包模式：可执行文件同级目录 - 开发 / Docker 模式：当前工作目录  这与, 返回 .env 文件的绝对路径（位于用户可写数据目录）。, app_data_dir(), Path, 跨平台可写数据目录解析。  打包（PyInstaller frozen）模式下，可执行文件常被安装到只读目录 （如 Windows 的 ``Program Fi, 返回应用可写数据目录，用于 SQLite、密钥、.env、状态标记等运行期文件。      - 打包模式：定位到操作系统的「用户数据目录」并确保其存在。 (+4 more)

### Community 52 - "HomemadeTeachingToy"
Cohesion: 0.30
Nodes (13): HomemadeTeachingToy, 教师自制教玩具记录。      每条记录保存一次 AI 生成或教师编辑后的教玩具方案。班级与教师姓名     采用冗余快照，避免后续设置变更影响历史导出。, create_homemade_teaching_toy(), delete_homemade_teaching_toy(), get_homemade_teaching_toy(), list_homemade_teaching_toys(), AsyncSession, 按 id 查询记录，强制 tenant_id 过滤。 (+5 more)

### Community 53 - "test_holiday_client.py"
Cohesion: 0.20
Nodes (6): get_special_day_tags(), 中国法定节假日客户端。  特性： - 查询指定日期是否为法定节假日（True / False / None） - 查询是否为法定节假日前一天（near_holi, 返回不放假节日标签列表（本地硬编码）。     空列表表示该日期无特殊节日标注。     返回值为副本，修改不影响内部数据。, 日期选择面板组件（可复用）。  功能： - 日期选择器（NiceGUI ui.date） - 选择日期后自动计算并显示：第几周、周几、是否工作日 - 节假日状态, Step 2.4 — 节假日客户端测试  使用自定义 httpx.AsyncBaseTransport 模拟 API，测试： - 正常响应的 bool 返回值（, TestGetSpecialDayTags

### Community 54 - "make_response"
Cohesion: 0.13
Nodes (16): is_adjusted_workday(), is_holiday(), 判断指定日期是否为调班工作日（节假日调休补班的周末）。      返回语义：     - True  ：调班工作日（API type == 3），周末需正常上班, 查询指定日期是否为法定节假日。      返回语义（固定）：     - True  ：法定节假日（API type == 2）     - False ：工作, make_response(), 普通工作日（type=0）返回 False, 普通周末（type=1）返回 False（与法定节假日语义严格区分）, 调班工作日（type=3）返回 False (+8 more)

### Community 55 - "Project Structure"
Cohesion: 0.15
Nodes (14): Coding Style & Naming Conventions, Project Structure, Security & Architecture Notes, Tenant Isolation, alembic/, app/api/, app/auth/, app/core/ (+6 more)

### Community 56 - "graphify skill"
Cohesion: 0.14
Nodes (14): Add & Watch Reference, Exports Reference, GitHub and Merge Reference, Hooks Reference, Query Reference, Transcribe Reference, Update Reference, graphify skill (+6 more)

### Community 57 - "Graphify Pipeline"
Cohesion: 0.15
Nodes (14): AST Extraction, Community Detection, FalkorDB Export, Graph Health Check, graph.json, GRAPH_REPORT.md, Incremental Update, Manifest (+6 more)

### Community 58 - "adapt_activity_process"
Cohesion: 0.25
Nodes (13): adapt_activity_process(), 将活动过程按年龄段改写。      Args:         original: 活动过程原文。         grade: 年龄段，如"小班"、"中班"、, _make_client(), AsyncClient, tests/test_adapt_client.py — 年龄适配客户端测试。, AI 返回缺少 adapted_process 字段时，抛出 AiParseError。, 原文为空字符串时，不发请求直接抛出 AiParseError。, 传入自定义 system prompt 时，正常调用不报错。 (+5 more)

### Community 59 - "pages/course_review_activity.py"
Cohesion: 0.24
Nodes (14): build_course_review_activity_filename(), _clean_filename_part(), course_review_activity_page(), format_setting_summary(), 课程审议页面（路由：/course-review-activity）。, validate_course_review_form(), validate_generation_context(), test_build_course_review_activity_filename() (+6 more)

### Community 60 - "hash_password"
Cohesion: 0.29
Nodes (11): hash_password(), 将明文密码哈希为 Argon2 格式字符串。, verify_password(), `verify_password` 对正确密码返回 True。, `verify_password` 对错误密码返回 False。, 同一密码两次哈希结果不同（Argon2 带 salt）。, test_empty_password(), test_hash_not_equal_to_plain() (+3 more)

### Community 61 - "add_image"
Cohesion: 0.21
Nodes (14): add_image(), delete_images_by_observation(), list_images_by_observation(), AsyncSession, 新增一张观察图片记录，返回带 id 的对象。, 查询某观察记录下的所有图片，按 image_index 升序排列。, 删除某观察记录下的所有图片（tenant 隔离）。, Phase D — 游戏观察图片仓库层测试。 (+6 more)

### Community 62 - "pages/homemade_teaching.py"
Cohesion: 0.29
Nodes (11): build_homemade_teaching_filename(), _clean_filename_part(), format_setting_summary(), homemade_teaching_page(), 自制教玩具页面（路由：/homemade-teaching）。, validate_generation_context(), test_build_homemade_teaching_filename(), test_build_homemade_teaching_filename_sanitizes_values() (+3 more)

### Community 63 - "Repository Guidelines"
Cohesion: 0.18
Nodes (12): Build, Test and Development Commands, Commit & Pull Request Guidelines, CONTEXT.md, DeepSeek backend, Graphify Backend Fallback Chain, graphify-out/, luna_worker sub-agent, OpenAI-compatible backend (+4 more)

### Community 64 - "main.py"
Cohesion: 0.14
Nodes (13): APIRouter, create_api_router(), 对外只读 REST API（二期）。  通过 :func:`create_api_router` 暴露 ``/api/v1`` 路由，由 ``app/main., 返回组装好的对外 API 路由（当前仅 v1）。, run_bootstrap(), main(), _on_global_exception(), Exception (+5 more)

### Community 65 - "get_legal_holidays_in_year"
Cohesion: 0.18
Nodes (10): _ensure_cache_fresh(), get_legal_holidays_in_year(), date, 一次性查询整年的法定节假日集合（单请求，避免逐日并发触发限流）。      用于「一对一倾听」批量选取工作日时排除节假日。复用 timor.tech 的「年」接, 若缓存日期不是今天，清空缓存（单日缓存 + 年节假日缓存）。, AsyncBaseTransport, 同年第二次查询命中缓存，不再发起 HTTP。, API 5xx → 返回 None（降级）。 (+2 more)

### Community 66 - "generate_activity_content"
Cohesion: 0.24
Nodes (11): generate_activity_content(), AsyncSession, 生成单项活动内容。      Args:         session: 异步数据库会话（查询 AI Key 与自定义提示词）。         tenant, _make_mock_ai_key(), tests/test_generate_service.py — 一日活动生成服务测试。  使用 Mock 隔离 AI 调用、AI Key 仓库与提示词仓库。, 用户未配置 AI Key 时抛出 ConfigError。, 无自定义提示词时，使用内置默认（system_prompt=None）并返回生成文本。, 存在激活的自定义提示词时，将其传给 generate_activity。 (+3 more)

### Community 67 - "._update_info"
Cohesion: 0.23
Nodes (7): DatePanel, 外部或内部直接设置日期值，触发联动更新（同步入口）。, 日期选择器选值回调（同步，启动异步联动）。, 日期选择面板，可嵌入任意 NiceGUI 页面。      参数：         semester_start: 学期开始日期，用于计算第几周；传 None, 渲染面板并返回外层 card 元素，可嵌入父容器。, card, date_type

### Community 68 - "test_listening_migration.py"
Cohesion: 0.17
Nodes (9): migrated_db(), P1 — 一对一倾听迁移与种子集成测试。  在临时 sqlite 文件库上实际执行 `alembic upgrade head`，验证： - 5 个新表创建成功, export_records 含 listening_record_id 列。, 种子 JSON：5 领域共 30 个二级指标，每个含 3 档标准、sort_order 连续。, 在临时 sqlite 文件库上执行 alembic upgrade head，返回库路径。, 每条种子三档标准非空，tenant_id=1，max_stars=3。, test_export_records_has_listening_col(), test_indicator_seed_integrity() (+1 more)

### Community 69 - "codebase-memory 14 MCP Tools"
Cohesion: 0.27
Nodes (11): codebase-memory Graph, Cypher Query Language, detect_changes, Edge Types, get_architecture, get_code_snippet, query_graph, search_graph (+3 more)

### Community 70 - "generate_course_review_activity"
Cohesion: 0.44
Nodes (10): _build_user_content(), generate_course_review_activity(), _make_client(), AsyncClient, test_generate_course_review_activity_filters_extra_keys(), test_generate_course_review_activity_invalid_string_payload_raises(), test_generate_course_review_activity_requires_boolean_fields(), test_generate_course_review_activity_success() (+2 more)

### Community 71 - "is_near_holiday"
Cohesion: 0.27
Nodes (6): is_near_holiday(), 判断 target_date 是否为法定节假日前一天。      返回语义：     - True  ：明天是法定节假日     - False ：明天不是法定, 法定节假日前一天（9月30日，10月1日为法定节假日）返回 True, 周五（普通周末前一天）返回 False，不视为 near_holiday, 普通工作日的前一天，次日也是工作日，返回 False, TestIsNearHoliday

### Community 72 - "create_pending_user"
Cohesion: 0.25
Nodes (10): create_pending_user(), 创建待审核用户（is_active=False，role=teacher），用于自助注册流程。      Args:         session: 异步数据, update_display_name(), Phase D — user_repository display_name / create_pending_user 扩充测试。, 同 tenant 重复用户名创建 pending user 应抛出唯一性异常。, update_display_name 可将显示名更新为新值。, create_pending_user 创建的用户 is_active=False，role=teacher。, test_create_pending_user_duplicate_username_raises() (+2 more)

### Community 73 - "register_user"
Cohesion: 0.18
Nodes (11): 自助注册：      - 若系统（tenant_id=1）尚无任何用户，注册者自动成为 sys_admin（is_active=True，可立即登录）。, register_user(), 空库第一个注册用户自动成为 sys_admin（is_active=True），可立即登录。, 已有用户后，第二个注册者成为 teacher（is_active=False），需管理员审核。, 同用户名注册两次时抛出 ValueError。, 注册时传入显示名，返回的用户对象应包含该显示名。, test_first_user_becomes_sys_admin_and_active(), test_register_duplicate_username_raises() (+3 more)

### Community 74 - "get_week_number"
Cohesion: 0.27
Nodes (5): get_week_number(), 返回 target_date 是开学后第几周（第 1 周起算）。      例：start_date=周一，target_date=同一天 → 第 1 周；, start_date 为周三时，目标日期在同一自然周内仍为第 1 周, 目标日期早于开学日，返回 ≤ 0（允许调用方自行处理，不抛异常）, TestGetWeekNumber

### Community 76 - "profile.py"
Cohesion: 0.22
Nodes (9): change_password(), 更新用户个人资料的显示名。      Args:         session: 异步数据库会话。         tenant_id: 租户 ID。, 验证旧密码后将密码更新为新哈希值。      旧密码错误或用户不存在时抛出 AuthError。, update_profile_display_name(), _get_current_user(), profile_page(), 个人资料页面（路由：/profile）。  功能：   - 查看并修改显示名（真实姓名）   - 修改密码, 更新显示名后，从 DB 取回的用户的 display_name 字段正确。 (+1 more)

### Community 77 - "test_observation_service.py"
Cohesion: 0.27
Nodes (9): generate_observation_content(), 调用视觉 AI 生成游戏观察四段内容，返回结果 dict（含 compressed_images）。      Args:         session: 异, tests/test_observation_service.py — 游戏观察服务层测试。  测试覆盖：   1. 未配置视觉 Key → ConfigErr, DB 中有激活的 game_observation 提示词时，覆盖内置默认提示词传给 AI。, 未配置 vision Key 时，服务层抛出 ConfigError。, 正常流程：mock AI 调用 + 图片压缩，返回 4 字段 + 压缩图片。, test_generate_observation_content_no_vision_key_raises_config_error(), test_generate_observation_content_success() (+1 more)

### Community 78 - "Extraction Spec"
Cohesion: 0.22
Nodes (9): Extraction Spec, Confidence Rubric, Gemini backend, Honesty Rules, Hyperedges, Node ID Format, Semantic Extraction, Semantic Similarity Edges (+1 more)

### Community 79 - "log_audit"
Cohesion: 0.31
Nodes (8): log_audit(), 记录一条审计日志。      Args:         action: 操作标识（如 login_success / change_password / ai, tests/test_audit.py — 审计日志测试。, 审计日志携带 audit_action / tenant_id / user_id 及附加字段。, 未提供 tenant_id / user_id 时默认为 None。, test_log_audit_defaults_none_ids(), test_log_audit_emits_structured_fields(), test_log_audit_never_raises()

### Community 81 - "is_within_semester"
Cohesion: 0.33
Nodes (3): is_within_semester(), 判断 target_date 是否在学期范围内（含首尾两天）。, TestIsWithinSemester

### Community 82 - "test_config_image_settings.py"
Cohesion: 0.29
Nodes (5): 测试图片相关配置项（Phase A）。  验证新增的 IMAGE_STORAGE_BACKEND 和 IMAGE_MAX_BYTES 配置项存在且默认值正确，, IMAGE_MAX_BYTES 默认值为 1048576（1MB）。, IMAGE_STORAGE_BACKEND 默认值为 mysql_blob。, test_image_max_bytes_default(), test_image_storage_backend_default()

### Community 84 - "Controlled AI Agent Boundary"
Cohesion: 0.50
Nodes (5): Controlled AI Agent Boundary, Foundation Agent, PlanPatch, ADR-0005 Controlled AI Agent Runtime, docs/design/agent-runtime.md

### Community 85 - "46b9fd5613c3_add_model_name_to_ai_api_key.py"
Cohesion: 0.40
Nodes (4): downgrade(), Upgrade schema.      列 model_name 可能已存在（来自另一台机器的未提交迁移）。     若不存在则新增；若已存在则修改为 NOT, Downgrade schema: 恢复为可空、无默认值。, upgrade()

### Community 86 - "4e2e0e079e56_drop_invite_code_table.py"
Cohesion: 0.40
Nodes (4): downgrade(), 删除 invite_code 表（邀请码功能已移除）。, 重建 invite_code 表（回滚用）。, upgrade()

### Community 87 - "a6c4d8e2f9b1_add_course_review_activity.py"
Cohesion: 0.80
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 88 - "_make_settings"
Cohesion: 0.12
Nodes (17): _build_fernet(), 将环境变量中的原始字符串密钥转换为 Fernet 实例。      Fernet 要求 32 字节的 URL-safe base64 编码密钥（共 44 个字符, Fernet, _make_settings(), 自动生成的 ENCRYPTION_KEY 应能被 app.core.crypto 正常使用。, 在受控环境下构造 Settings 实例，不读取磁盘 .env 文件。, 无任何配置时，Settings() 应成功实例化（修复必填字段导致的启动崩溃）。, ENCRYPTION_KEY 为空时应自动生成非空值。 (+9 more)

### Community 90 - "Alembic-only schema changes"
Cohesion: 0.50
Nodes (4): Alembic-only schema changes, Database and ORM instructions, ADR-0003 SQLite MySQL Alembic, SQLite default and Alembic authority

### Community 91 - "2f7a9c1d4e8b_add_teacher_name_to_class_config.py"
Cohesion: 0.83
Nodes (3): downgrade(), _has_column(), upgrade()

### Community 92 - "7c1e2a9b5d4f_add_homemade_teaching_toy.py"
Cohesion: 0.83
Nodes (3): downgrade(), _has_table(), upgrade()

### Community 93 - "d5e4f3a2b1c0_add_homemade_teaching_id_to_export_records.py"
Cohesion: 0.83
Nodes (3): downgrade(), _has_column(), upgrade()

### Community 95 - "Single-user UI decision"
Cohesion: 0.50
Nodes (4): ADR-0002 single-user UI and tenant API, Single-user UI decision, REST API reference, Read-only REST API v1

### Community 96 - "项目进度记录"
Cohesion: 0.50
Nodes (4): 项目进度记录, 历史进度证据不等于当前基线, 一对一倾听反馈修复与复测标签, 自制教玩具与课程审议交付记录

### Community 97 - "test_dependency_security_baseline.py"
Cohesion: 0.67
Nodes (3): Regression guard for dependency versions raised by Dependabot., _requirements_by_name(), test_dependabot_security_floors_are_not_downgraded()

## Ambiguous Edges - Review These
- `历史渐进式微服务拓扑` → `当前能力仍在主应用进程内`  [AMBIGUOUS]
  services/README.md · relation: conceptually_related_to

## Knowledge Gaps
- **80 isolated node(s):** `一日活动教案处理流水线`, `build-deb.sh script`, `AI client integration boundary`, `AI integration instructions`, `Fixed Word template layout` (+75 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `历史渐进式微服务拓扑` and `当前能力仍在主应用进程内`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `AiParseError` connect `AiParseError` to `generate_listening_domain`, `generate_course_review_activity`, `AiCallError`, `test_generate_client.py`, `process_lesson_plan`, `ConfigError`, `generate_observation`, `pages/game_observation.py`, `split_lesson_plan`, `one_on_one_listening.py`, `exceptions.py`, `adapt_activity_process`, `pages/course_review_activity.py`, `pages/homemade_teaching.py`, `CryptoError`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `log_audit()` connect `log_audit` to `generate_activity_content`, `listening_service.py`, `bootstrap_admin.py`, `test_listening_service.py`, `register_user`, `process_lesson_plan`, `test_auth_service.py`, `profile.py`, `ConfigError`, `test_observation_service.py`, `pages/game_observation.py`, `auth_service.py`, `one_on_one_listening.py`, `exceptions.py`, `pages/course_review_activity.py`, `pages/homemade_teaching.py`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `get_logger()` connect `exceptions.py` to `AiParseError`, `listening_exporter.py`, `main.py`, `export_daily_plan`, `User`, `export_homemade_teaching`, `test_generate_client.py`, `profile.py`, `pages/game_observation.py`, `export_observation`, `one_on_one_listening.py`, `test_holiday_client.py`, `course_review_activity_exporter.py`, `pages/course_review_activity.py`, `pages/homemade_teaching.py`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `AiParseError` (e.g. with `test_adapt_empty_original_raises_parse_error()` and `test_adapt_missing_adapted_process_raises_parse_error()`) actually correct?**
  _`AiParseError` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `DailyPlan` (e.g. with `ClassConfigOut` and `DailyPlanListOut`) actually correct?**
  _`DailyPlan` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Base` (e.g. with `AiApiKey` and `ClassConfig`) actually correct?**
  _`Base` has 17 INFERRED edges - model-reasoned connections that need verification._