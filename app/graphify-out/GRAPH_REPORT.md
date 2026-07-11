# Graph Report - .  (2026-07-11)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 834 nodes · 1374 edges · 54 communities (51 shown, 3 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 261 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e32df16c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_ClassConfig|ClassConfig]]
- [[_COMMUNITY_Base|Base]]
- [[_COMMUNITY_get_current_user_or_redirect|get_current_user_or_redirect]]
- [[_COMMUNITY_._update_info|._update_info]]
- [[_COMMUNITY_AppError|AppError]]
- [[_COMMUNITY_listening_exporter.py|listening_exporter.py]]
- [[_COMMUNITY_app_data_dir|app_data_dir]]
- [[_COMMUNITY_get_active_ai_key|get_active_ai_key]]
- [[_COMMUNITY_DailyPlan|DailyPlan]]
- [[_COMMUNITY_User|User]]
- [[_COMMUNITY_one_on_one_listening.py|one_on_one_listening.py]]
- [[_COMMUNITY_main|main]]
- [[_COMMUNITY_get_active_prompt|get_active_prompt]]
- [[_COMMUNITY_ImageStorageBackend|ImageStorageBackend]]
- [[_COMMUNITY_AiParseError|AiParseError]]
- [[_COMMUNITY_AuthError|AuthError]]
- [[_COMMUNITY_course_review_activity_exporter.py|course_review_activity_exporter.py]]
- [[_COMMUNITY_GameObservation|GameObservation]]
- [[_COMMUNITY_observation_exporter.py|observation_exporter.py]]
- [[_COMMUNITY_bootstrap_admin.py|bootstrap_admin.py]]
- [[_COMMUNITY_GameObservationImage|GameObservationImage]]
- [[_COMMUNITY_IndicatorCatalog|IndicatorCatalog]]
- [[_COMMUNITY_ListeningImage|ListeningImage]]
- [[_COMMUNITY_CourseReviewActivity|CourseReviewActivity]]
- [[_COMMUNITY_call_ai|call_ai]]
- [[_COMMUNITY_HomemadeTeachingToy|HomemadeTeachingToy]]
- [[_COMMUNITY_process_lesson_plan|process_lesson_plan]]
- [[_COMMUNITY_homemade_teaching_exporter.py|homemade_teaching_exporter.py]]
- [[_COMMUNITY_generate_activity|generate_activity]]
- [[_COMMUNITY_get_env_path|get_env_path]]
- [[_COMMUNITY_has_active_sys_admin|has_active_sys_admin]]
- [[_COMMUNITY_log_audit|log_audit]]
- [[_COMMUNITY_save_export_record|save_export_record]]
- [[_COMMUNITY_decode_access_token|decode_access_token]]
- [[_COMMUNITY_compute_diff|compute_diff]]
- [[_COMMUNITY_get_db|get_db]]
- [[_COMMUNITY_split_lesson_plan|split_lesson_plan]]
- [[_COMMUNITY_user_context.py|user_context.py]]
- [[_COMMUNITY_generate_course_review_activity|generate_course_review_activity]]
- [[_COMMUNITY_register.py|register.py]]

## God Nodes (most connected - your core abstractions)
1. `DailyPlan` - 20 edges
2. `log_audit()` - 19 edges
3. `Base` - 19 edges
4. `User` - 14 edges
5. `get_current_user_or_redirect()` - 14 edges
6. `render_shell()` - 14 edges
7. `get_active_ai_key()` - 13 edges
8. `AuthError` - 12 edges
9. `ConfigError` - 12 edges
10. `AiParseError` - 12 edges

## Surprising Connections (you probably didn't know these)
- `query_daily_plans()` --calls--> `list_daily_plans()`  [INFERRED]
  api/routes.py → repository/daily_plan_repository.py
- `HealthOut` --uses--> `DailyPlan`  [INFERRED]
  api/schemas.py → core/models/daily_plan.py
- `PageMeta` --uses--> `DailyPlan`  [INFERRED]
  api/schemas.py → core/models/daily_plan.py
- `DailyPlanOut` --uses--> `DailyPlan`  [INFERRED]
  api/schemas.py → core/models/daily_plan.py
- `DailyPlanListOut` --uses--> `DailyPlan`  [INFERRED]
  api/schemas.py → core/models/daily_plan.py

## Import Cycles
- None detected.

## Communities (54 total, 3 thin omitted)

### Community 0 - "ClassConfig"
Cohesion: 0.06
Nodes (48): ApiPrincipal, _build_signing_string(), get_api_principal(), parse_api_keys(), Request, 对外 REST API 鉴权：API Key + 可选 HMAC 签名。  鉴权模型（服务间调用）： 1. **API Key**（必填）：调用方在 `X-Ap, 解析 `API_KEYS` 配置为 {api_key: tenant_id} 映射。      格式："key1:1,key2:2"；忽略空段与格式非法段（te, 校验 HMAC-SHA256 请求签名与时间戳新鲜度。 (+40 more)

### Community 1 - "Base"
Cohesion: 0.06
Nodes (50): Base, ListeningDomain, ListeningDomain — 一对一倾听单领域内容。  每条 listening_record 对应 5 条本表（健康/语言/社会/艺术/科学各一）。 年, ListeningIndicatorResult, ListeningIndicatorResult — 一对一倾听二级指标达成结果。  每条 listening_record 的每个领域每个二级指标一条，记录达, ListeningRecord, ListeningRecord — 一对一倾听观察记录主表。  一条记录对应一个幼儿的一次「一对一倾听」观察，覆盖五大领域。 领域级内容（目标/日期/图片/指标, DeclarativeBase (+42 more)

### Community 2 - "get_current_user_or_redirect"
Cohesion: 0.05
Nodes (40): get_current_user_or_redirect(), AsyncSession, 从 JWT token 解析并刷新当前用户信息。      token 有效只是第一步；还需要查询数据库，确认用户仍存在、处于启用状态，     并用数据库中的, 读取当前登录用户；未登录或无权限时跳转。      Args:         redirect_to: 未登录/无效 token 时跳转地址。, resolve_current_user(), app_shell(), get_display_name(), get_menu_items() (+32 more)

### Community 3 - "._update_info"
Cohesion: 0.08
Nodes (37): AsyncBaseTransport, card, date_type, _ensure_cache_fresh(), get_holiday_name(), get_legal_holidays_in_year(), get_special_day_tags(), is_adjusted_workday() (+29 more)

### Community 4 - "AppError"
Cohesion: 0.06
Nodes (38): AppError, 通用业务异常：输入非法、文件格式错误等非 AI / 非鉴权类业务错误。, _build_context_text(), _detect_mime(), generate_listening_domain(), _image_to_data_url(), 一对一倾听单领域生成 AI 客户端。  针对某一领域（健康/语言/社会/艺术/科学），输入该领域 3 张幼儿绘画照片 + 班级信息 + 该领域二级指标清单，一次, 调用视觉 AI 生成某领域的一对一倾听结构化内容。      Args:         images: 该领域绘画图片字节列表（经压缩后的 bytes，至少 (+30 more)

### Community 5 - "listening_exporter.py"
Cohesion: 0.09
Nodes (43): _build_domain_doc(), _build_from_scratch(), _clear_cell(), _domain_of_title(), export_batch_by_domain(), export_combined(), export_split_by_domain(), _extract_block() (+35 more)

### Community 6 - "app_data_dir"
Cohesion: 0.06
Nodes (36): BaseSettings, Path, 应用配置：通过 pydantic-settings 从 .env 文件和环境变量加载。  首次部署（无 .env 文件）时的行为： - DATABASE_URL, 返回自动生成密钥的持久化文件路径（位于用户可写数据目录）。, 解析 key=value 文件，忽略空行与注释行。, 将新键值追加/覆盖到持久化文件（已有键保留）。, 自动生成缺失的密钥并持久化，保证重启后可还原。, _read_kv_file() (+28 more)

### Community 7 - "get_active_ai_key"
Cohesion: 0.06
Nodes (34): _build_fernet(), decrypt(), encrypt(), 应用层对称加密工具（Fernet）。  密钥来源：Settings.ENCRYPTION_KEY（原始字符串，UTF-8 编码后取前 32 字节， 再经 bas, 将环境变量中的原始字符串密钥转换为 Fernet 实例。      Fernet 要求 32 字节的 URL-safe base64 编码密钥（共 44 个字符, 加密明文字符串，返回 URL-safe base64 密文字符串。      Args:         plain_text: 待加密的明文（禁止在调用方写入, 解密密文字符串，还原为原始明文。      Args:         cipher_text: 由 `encrypt()` 生成的密文字符串。      Re, AiApiKey (+26 more)

### Community 8 - "DailyPlan"
Cohesion: 0.09
Nodes (39): DailyPlan, 每日活动计划数据模型。  对应数据库表：daily_plan 包含教案拆分、年龄适配改写、一日活动生成等所有字段。, 每日活动计划表。      字段说明：     - plan_date：计划日期（对应学期中的某一天）     - week_number：第几周（由 date, _build_collective_cell(), export_batch_daily_plans(), export_daily_plan(), _export_from_scratch(), _fill_fields_cell() (+31 more)

### Community 9 - "User"
Cohesion: 0.14
Nodes (24): User, UserRole, create_pending_user(), create_user(), get_user_by_username(), has_any_user(), list_pending_users(), list_users_by_tenant() (+16 more)

### Community 10 - "one_on_one_listening.py"
Cohesion: 0.10
Nodes (23): _auto_pick_workdays(), build_export_filename(), default_year_month(), distribute_images_by_filename(), format_record_summary(), format_stage_label(), infer_age_by_grade(), one_on_one_listening_page() (+15 more)

### Community 11 - "main"
Cohesion: 0.09
Nodes (18): create_api_router(), 对外只读 REST API（二期）。  通过 :func:`create_api_router` 暴露 ``/api/v1`` 路由，由 ``app/main., 返回组装好的对外 API 路由（当前仅 v1）。, APIRouter, AuthMiddleware, Request, 路由守卫中间件。  登录恢复后，NiceGUI 页面在页面函数内通过 `app.ui.auth_context` 校验登录态； 中间件保持直通，避免 WebSo, BaseHTTPMiddleware (+10 more)

### Community 12 - "get_active_prompt"
Cohesion: 0.14
Nodes (20): column, PromptTemplate, PromptTemplate — 提示词模板数据模型。  支持以下任务类型，每种类型独立维护版本历史，同一用户同一类型只能有一条 is_active=True, label, get_active_prompt(), list_versions(), AsyncSession, prompt_repository — 提示词模板数据访问层。  支持提示词多版本管理：保存新版本、回滚、查询激活版本、列出所有版本。  约束： - 同一用户同 (+12 more)

### Community 13 - "ImageStorageBackend"
Cohesion: 0.12
Nodes (12): ABC, ImageStorageBackend, 存储图片字节，返回存储引用 dict。          Returns:             dict，键因后端而异（blob_backend 含 blo, 从存储引用还原图片字节。          Args:             stored: 与 put 返回格式相同的 dict。          Ret, 可插拔图片存储后端抽象。      put / get 与数据库 session 解耦：     - put 返回 stored_ref dict，由 repo, BlobImageStorage, MySQL BLOB 图片存储后端。  put/get 只操作内存 dict，实际 DB 写入由 repository 层完成。, MySQL BLOB 后端：图片二进制存入 game_observation_image.blob_content。 (+4 more)

### Community 14 - "AiParseError"
Cohesion: 0.16
Nodes (11): AiCallError, AiParseError, ConfigError, CryptoError, 加解密失败时抛出：密文被篡改、密钥不匹配或格式非法。, 业务配置缺失时抛出：如用户尚未配置 AI Key。, AI 接口调用失败时抛出：HTTP 4xx/5xx、网络超时、超过重试次数等。, AI 返回内容解析失败时抛出：JSON 格式非法、缺少必要字段等。 (+3 more)

### Community 15 - "AuthError"
Cohesion: 0.18
Nodes (18): AuthError, 鉴权失败：token 无效、已过期、签名错误或用户名密码错误时抛出。          故意不区分"用户不存在"和"密码错误"，防止用户枚举攻击。, get_user_by_id(), 在指定租户中更新用户启停状态，返回是否更新成功。, 在指定租户下按 ID 查询用户，不存在时返回 None。, update_user_active(), approve_user(), change_password() (+10 more)

### Community 16 - "course_review_activity_exporter.py"
Cohesion: 0.28
Nodes (18): _build_from_scratch(), _clear_cell(), _clear_paragraph(), export_course_review_activity(), _fill_template(), _get_bool(), _get_value(), _iter_body_blocks() (+10 more)

### Community 17 - "GameObservation"
Cohesion: 0.17
Nodes (16): GameObservation, GameObservation — 游戏观察记录数据模型。  每条记录对应教师的一次游戏观察，包含元数据（日期/环境/人员） 和 AI 生成的四段内容（观察目标, delete_observation(), get_observation_by_id(), list_observations(), Any, AsyncSession, date (+8 more)

### Community 18 - "observation_exporter.py"
Cohesion: 0.21
Nodes (16): _add_images_to_cell(), _build_from_scratch(), _clear_cell(), export_observation(), _fill_template(), Document, Path, RGBColor (+8 more)

### Community 19 - "bootstrap_admin.py"
Cohesion: 0.20
Nodes (15): _main(), main_cli(), _prompt_password(), _prompt_str(), 系统管理员初始化脚本。  模式：   --init           创建 sys_admin 账号（默认模式）   --reset-password 重置, 重置 sys_admin 密码（需旧密码验证），返回执行结果说明。, --init 模式：创建 sys_admin 账号。, --reset-password 模式：重置 sys_admin 密码。 (+7 more)

### Community 20 - "GameObservationImage"
Cohesion: 0.21
Nodes (12): GameObservationImage, GameObservationImage — 游戏观察图片数据模型。  可插拔存储：本期实现 MySQL BLOB 后端（blob_content 存压缩后二进, add_image(), delete_images_by_observation(), get_image(), list_images_by_observation(), AsyncSession, observation_image_repository — 游戏观察图片数据访问层。 (+4 more)

### Community 21 - "IndicatorCatalog"
Cohesion: 0.20
Nodes (12): IndicatorCatalog, IndicatorCatalog — 一对一倾听指标目录（参考数据，迁移预置）。  按 (grade, term, domain) 组织一级/二级指标及三档（★, get_indicator_by_id(), list_available_stages(), list_indicators(), list_indicators_by_ids(), AsyncSession, indicator_repository — 指标目录数据访问层。  只读参考数据查询（指标目录按 tenant_id + grade + term + dom (+4 more)

### Community 22 - "ListeningImage"
Cohesion: 0.21
Nodes (12): ListeningImage, ListeningImage — 一对一倾听绘画图片数据模型。  每个领域 3 张（共 15 张/记录）。复用游戏观察图片的可插拔 BLOB 存储， 新增 do, add_image(), delete_images_by_record(), get_image(), list_images_by_record(), AsyncSession, listening_image_repository — 一对一倾听图片数据访问层。 (+4 more)

### Community 23 - "CourseReviewActivity"
Cohesion: 0.26
Nodes (10): CourseReviewActivity, 课程审议记录。      每条记录保存一次课程审议生成与教师编辑后的结果。班级、年龄段与教师姓名     采用冗余快照，避免后续系统设置变更影响历史导出。, create_course_review_activity(), delete_course_review_activity(), get_course_review_activity(), list_course_review_activities(), AsyncSession, 删除课程审议记录，强制 tenant_id + user_id 双重过滤。 (+2 more)

### Community 24 - "call_ai"
Cohesion: 0.23
Nodes (10): call_ai(), call_ai_text(), _make_retry_decorator(), AsyncClient, AI 客户端基础模块 — 通用 Chat Completions 调用。  所有 AI 调用必须通过此模块，禁止在 service 层直接发 HTTP 请求。, 发送 Chat Completions 请求，返回纯文本 content 字符串。      与 call_ai() 的区别：不强制 json_object 格, 构造 tenacity 重试装饰器：最多 3 次，指数退避 2s → 4s → 8s。, 发送 Chat Completions 请求，返回解析后的 dict。      Args:         messages: 消息列表，格式为 [{"rol (+2 more)

### Community 25 - "HomemadeTeachingToy"
Cohesion: 0.29
Nodes (9): HomemadeTeachingToy, 教师自制教玩具记录。      每条记录保存一次 AI 生成或教师编辑后的教玩具方案。班级与教师姓名     采用冗余快照，避免后续设置变更影响历史导出。, create_homemade_teaching_toy(), delete_homemade_teaching_toy(), get_homemade_teaching_toy(), list_homemade_teaching_toys(), AsyncSession, 按 id 查询记录，强制 tenant_id 过滤。 (+1 more)

### Community 26 - "process_lesson_plan"
Cohesion: 0.20
Nodes (8): adapt_activity_process(), 年龄适配 AI 客户端。  将活动过程原文按年龄段（小班/中班/大班）改写，返回改写后文本。  输出 Schema：     {"adapted_process, 将活动过程按年龄段改写。      Args:         original: 活动过程原文。         grade: 年龄段，如"小班"、"中班"、, LessonPlanResult, process_lesson_plan(), AsyncSession, 教案拆分与年龄适配的完整结果。      Attributes:         activity_goal: 活动目标（AI 拆分原文）。         a, 完整教案拆分与年龄适配流程。      Args:         session: 异步数据库会话（用于查询 AI Key）。         tenant_

### Community 27 - "homemade_teaching_exporter.py"
Cohesion: 0.44
Nodes (10): _build_from_scratch(), _clear_cell(), export_homemade_teaching(), _fill_template(), _get_value(), Any, Document, Path (+2 more)

### Community 28 - "generate_activity"
Cohesion: 0.27
Nodes (9): _build_prefix(), _build_user_content(), generate_activity(), _holiday_hint(), 一日活动生成客户端 — 包含 5 种活动类型的内置默认提示词。  任务类型对应关系： - morning_exercise  →  晨间活动 - morning, 构建消息开头的班级与教学周信息。      context 支持 grade、class_name、week_number、weekday 字段；     we, 当 near_holiday 为 True 时返回临近节假日提示行，否则返回空字符串。      near_holiday 取值：True 表示明日为法定节假日, 根据任务类型和上下文构建发送给 AI 的用户消息。      context 支持以下字段：         grade, class_name, activi (+1 more)

### Community 29 - "get_env_path"
Cohesion: 0.31
Nodes (8): get_env_path(), Path, 运行时 .env 文件读写工具。  路径策略： - PyInstaller 打包模式：可执行文件同级目录 - 开发 / Docker 模式：当前工作目录  这与, 返回 .env 文件的绝对路径（位于用户可写数据目录）。, 解析 .env 文件，返回 key-value 字典。      忽略空行与 # 开头的注释行。文件不存在时返回空字典。, 将 updates 中的 key-value 原子写入 .env，保留其余行不动。      若 .env 不存在则自动创建。写入失败时抛出 RuntimeEr, read_dot_env(), write_dot_env()

### Community 30 - "has_active_sys_admin"
Cohesion: 0.25
Nodes (6): has_active_sys_admin(), 自助注册：      创建 is_active=False 的待审核教师账号，需管理员审核通过后方可登录。      tenant_id 固定为 setting, register_user(), login_page(), 首次管理员初始化页面（路由：/setup-admin）。, setup_admin_page()

### Community 31 - "log_audit"
Cohesion: 0.33
Nodes (6): log_audit(), 审计日志：记录关键操作（登录、改密、AI 调用、Word 导出等）。  审计日志通过结构化 JSON logger 输出，统一携带 audit_action 与, 记录一条审计日志。      Args:         action: 操作标识（如 login_success / change_password / ai, bootstrap_admin(), create_initial_admin(), 创建首次系统管理员。      仅当当前租户不存在启用的 sys_admin 时允许创建，用于安装器初始化与     `/setup-admin` 首次启动兜底

### Community 32 - "save_export_record"
Cohesion: 0.29
Nodes (5): ExportRecord, 导出记录数据模型。  对应数据库表：export_records 记录每次 Word 导出操作的元信息（文件名、路径、关联教案）。 导出记录为只增不改（immu, AsyncSession, 写入一条导出记录。      Args:         session: 异步数据库会话（调用方负责事务管理）。         tenant_id: 机构, save_export_record()

### Community 33 - "decode_access_token"
Cohesion: 0.33
Nodes (5): create_access_token(), decode_access_token(), JWT access token 生成与解码工具。, 生成 JWT access token。      payload 字段：     - sub: str(user_id)     - tenant_id: i, 解码并验证 JWT token，返回 payload 字典。      token 过期、签名无效等情况统一抛出 AuthError。

### Community 34 - "compute_diff"
Cohesion: 0.40
Nodes (5): compute_diff(), 差异比对服务 — 使用 difflib 对原文与改写文进行逐句比对。  分句规则：以句号（。）、问号（？）、感叹号（！）、换行符为分隔符， 保留分隔符到句子末尾, 将文本按标点符号或换行符拆分为句子列表，过滤空串。, 对原文与改写文按句比对，返回带 changed 标记的句子列表。      Args:         original: 活动过程原文。         ad, _split_sentences()

### Community 35 - "get_db"
Cohesion: 0.40
Nodes (4): get_db(), AsyncSession, 对外 REST API 的 FastAPI 依赖。, 提供独立的异步数据库会话（只读查询，无需提交）。      测试可通过 ``app.dependency_overrides[get_db]`` 注入内存库会话

### Community 36 - "split_lesson_plan"
Cohesion: 0.50
Nodes (3): 教案拆分 AI 客户端。  调用 OpenAI 兼容接口，将完整教案文本拆分为结构化字段。  输出 Schema（5 个必填键）：     activity_g, 将完整教案文本拆分为结构化字段。      Args:         raw_text: 用户粘贴的完整教案文本。         api_base_url:, split_lesson_plan()

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Base` connect `Base` to `ClassConfig`, `save_export_record`, `app_data_dir`, `get_active_ai_key`, `DailyPlan`, `User`, `get_active_prompt`, `GameObservation`, `GameObservationImage`, `IndicatorCatalog`, `ListeningImage`, `CourseReviewActivity`, `HomemadeTeachingToy`?**
  _High betweenness centrality (0.304) - this node is a cross-community bridge._
- **Why does `settings_page()` connect `get_active_ai_key` to `ClassConfig`, `get_current_user_or_redirect`, `get_env_path`?**
  _High betweenness centrality (0.122) - this node is a cross-community bridge._
- **Why does `DailyPlan` connect `DailyPlan` to `ClassConfig`, `Base`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `DailyPlan` (e.g. with `ClassConfigOut` and `DailyPlanListOut`) actually correct?**
  _`DailyPlan` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `log_audit()` (e.g. with `bootstrap_admin()` and `reset_admin_password()`) actually correct?**
  _`log_audit()` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Base` (e.g. with `AiApiKey` and `ClassConfig`) actually correct?**
  _`Base` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `User` (e.g. with `Base` and `has_active_sys_admin()`) actually correct?**
  _`User` has 6 INFERRED edges - model-reasoned connections that need verification._