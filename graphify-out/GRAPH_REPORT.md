# Graph Report - .  (2026-07-11)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2074 nodes · 4714 edges · 124 communities (120 shown, 4 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 214 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9a32f108`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 108|Community 108]]
- [[_COMMUNITY_Community 109|Community 109]]

## God Nodes (most connected - your core abstractions)
1. `AiParseError` - 58 edges
2. `ConfigError` - 39 edges
3. `Base` - 37 edges
4. `DailyPlan` - 37 edges
5. `log_audit()` - 36 edges
6. `get_active_ai_key()` - 36 edges
7. `系统顶层总览` - 36 edges
8. `get_logger()` - 33 edges
9. `AuthError` - 32 edges
10. `save_ai_key()` - 31 edges

## Surprising Connections (you probably didn't know these)
- `异常模块` --implements--> `AI集成`  [INFERRED]
  app/core/exceptions.py → memory-bank/tech-stack.md
- `节假日客户端` --implements--> `AI集成`  [INFERRED]
  app/integration/holiday_client/client.py → memory-bank/tech-stack.md
- `日期服务` --implements--> `AI集成`  [INFERRED]
  app/service/date_service.py → memory-bank/tech-stack.md
- `图片处理模块` --implements--> `视觉AI`  [INFERRED]
  app/integration/image_processing.py → memory-bank/game-observation/design.md
- `认证中间件` --implements--> `RBAC权限`  [EXTRACTED]
  app/auth/middleware.py → memory-bank/PRD.md

## Import Cycles
- None detected.

## Communities (124 total, 4 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (63): _build_domain_doc(), _build_from_scratch(), _clear_cell(), _domain_of_title(), export_batch_by_domain(), export_combined(), export_split_by_domain(), _extract_block() (+55 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (41): PromptTemplate, PromptTemplate — 提示词模板数据模型。  支持以下任务类型，每种类型独立维护版本历史，同一用户同一类型只能有一条 is_active=True, get_active_prompt(), list_versions(), AsyncSession, prompt_repository — 提示词模板数据访问层。  支持提示词多版本管理：保存新版本、回滚、查询激活版本、列出所有版本。  约束： - 同一用户同, 将指定版本设为激活，其余版本设为 inactive。      Args:         session: 异步数据库会话。         tenant_i, 返回指定任务类型的所有版本，按版本号降序排列。      Args:         session: 异步数据库会话。         tenant_id: (+33 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (52): AppError, 通用业务异常：输入非法、文件格式错误等非 AI / 非鉴权类业务错误。, _build_context_text(), _detect_mime(), generate_listening_domain(), _image_to_data_url(), 一对一倾听单领域生成 AI 客户端。  针对某一领域（健康/语言/社会/艺术/科学），输入该领域 3 张幼儿绘画照片 + 班级信息 + 该领域二级指标清单，一次, 调用视觉 AI 生成某领域的一对一倾听结构化内容。      Args:         images: 该领域绘画图片字节列表（经压缩后的 bytes，至少 (+44 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (34): _build_collective_cell(), export_batch_daily_plans(), export_daily_plan(), _export_from_scratch(), _fill_fields_cell(), _fill_plain_cell(), _fill_process_cell(), _fill_template() (+26 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (46): ListeningDomain, ListeningDomain — 一对一倾听单领域内容。  每条 listening_record 对应 5 条本表（健康/语言/社会/艺术/科学各一）。 年, ListeningIndicatorResult, ListeningIndicatorResult — 一对一倾听二级指标达成结果。  每条 listening_record 的每个领域每个二级指标一条，记录达, ListeningRecord, ListeningRecord — 一对一倾听观察记录主表。  一条记录对应一个幼儿的一次「一对一倾听」观察，覆盖五大领域。 领域级内容（目标/日期/图片/指标, delete_domains_by_record(), delete_indicator_results_by_record() (+38 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (49): AuthError, 鉴权失败：token 无效、已过期、签名错误或用户名密码错误时抛出。          故意不区分"用户不存在"和"密码错误"，防止用户枚举攻击。, approve_user(), change_password(), create_user_by_admin(), login(), AsyncSession, 验证用户名和密码，成功则返回 JWT access token。      用户不存在或密码错误时统一抛出 AuthError，不区分具体原因。     账号被 (+41 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (43): create_pending_user(), get_user_by_id(), has_active_sys_admin(), list_pending_users(), list_users_by_tenant(), AsyncSession, query_users_by_tenant(), 用户数据访问层。  所有查询必须携带 tenant_id 过滤条件，确保多租户数据隔离。 (+35 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (32): AiApiKey, AiApiKey — AI 接口 Key 数据模型。  安全约束： - `api_key_encrypted` 字段仅存密文，明文禁止入库、禁止写入日志。 -, get_active_ai_key(), get_decrypted_key(), AsyncSession, ai_key_repository — AI API Key 数据访问层。  所有函数均携带 tenant_id + user_id 过滤，确保数据隔离。  安, 解密并返回明文 API Key。      Args:         ai_key: 由 `get_active_ai_key` 取得的模型对象。, 加密 API Key 后入库，同时将该用户同类型旧记录标记为 inactive。      Args:         session: 异步数据库会话。 (+24 more)

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (43): _build_prefix(), _build_user_content(), generate_activity(), _holiday_hint(), 构建消息开头的班级与教学周信息。      context 支持 grade、class_name、week_number、weekday 字段；     we, 当 near_holiday 为 True 时返回临近节假日提示行，否则返回空字符串。      near_holiday 取值：True 表示明日为法定节假日, 根据任务类型和上下文构建发送给 AI 的用户消息。      context 支持以下字段：         grade, class_name, activi, 生成单项一日活动内容（纯文本输出）。      Args:         task_type: 任务类型（morning_exercise / morning (+35 more)

### Community 9 - "Community 9"
Cohesion: 0.07
Nodes (40): _build_context_text(), _detect_mime(), generate_observation(), _image_to_data_url(), 游戏观察生成 AI 客户端。  调用 OpenAI 兼容多模态接口，输入 1~3 张游戏照片 + 元数据， 输出「观察目标 / 观察记录 / 评价分析 / 支持, 将上下文 dict 转为给 AI 的说明文本。, 根据文件头检测图片 MIME 类型，无法识别时默认 image/jpeg。, 将图片字节转为 base64 data-url 字符串。 (+32 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (40): CompressedImage, _clamp_star(), generate_domain_content(), load_record_detail(), _persist_domains(), AsyncSession, 一对一倾听服务层 — 单领域生成与整记录持久化。  职责：   - generate_domain_content：取 vision Key → 查提示词 →, 写入某记录下的各领域内容（领域 + 图片 + 指标结果）。      save_record_with_all（新建）与 update_record_with_ (+32 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (36): log_audit(), 记录一条审计日志。      Args:         action: 操作标识（如 login_success / change_password / ai, bootstrap_admin(), _main(), main_cli(), _prompt_password(), _prompt_str(), 系统管理员初始化脚本。  模式：   --init           创建 sys_admin 账号（默认模式）   --reset-password 重置 (+28 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (38): compute_diff(), 差异比对服务 — 使用 difflib 对原文与改写文进行逐句比对。  分句规则：以句号（。）、问号（？）、感叹号（！）、换行符为分隔符， 保留分隔符到句子末尾, 将文本按标点符号或换行符拆分为句子列表，过滤空串。, 对原文与改写文按句比对，返回带 changed 标记的句子列表。      Args:         original: 活动过程原文。         ad, _split_sentences(), LessonPlanResult, process_lesson_plan(), AsyncSession (+30 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (21): get_holiday_name(), 返回法定节假日名称，如"国庆节"、"春节"。      返回语义：     - str  ：该日期是法定节假日，返回节日名称（如"国庆节"）     - Non, make_response(), MockTransport, Request, Response, 法定节假日前一天（9月30日，10月1日为法定节假日）返回 True, 周五（普通周末前一天）返回 False，不视为 near_holiday (+13 more)

### Community 14 - "Community 14"
Cohesion: 0.11
Nodes (36): _add_images_to_cell(), _build_from_scratch(), _clear_cell(), export_observation(), _fill_template(), Document, Path, RGBColor (+28 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (28): Base, GameObservation, GameObservationImage — 游戏观察图片数据模型。  可插拔存储：本期实现 MySQL BLOB 后端（blob_content 存压缩后二进, GameObservation — 游戏观察记录数据模型。  每条记录对应教师的一次游戏观察，包含元数据（日期/环境/人员） 和 AI 生成的四段内容（观察目标, delete_observation(), get_observation_by_id(), list_observations(), Any (+20 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (22): AiCallError, ConfigError, 业务配置缺失时抛出：如用户尚未配置 AI Key。, AI 接口调用失败时抛出：HTTP 4xx/5xx、网络超时、超过重试次数等。, format_user_error(), Exception, build_homemade_teaching_filename(), _clean_filename_part() (+14 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (25): create_access_token(), decode_access_token(), JWT access token 生成与解码工具。, 生成 JWT access token。      payload 字段：     - sub: str(user_id)     - tenant_id: i, 解码并验证 JWT token，返回 payload 字典。      token 过期、签名无效等情况统一抛出 AuthError。, create_user(), 创建用户并持久化到数据库，返回已持久化的 User 对象。, AsyncSession (+17 more)

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (15): 解析 .env 文件，返回 key-value 字典。      忽略空行与 # 开头的注释行。文件不存在时返回空字典。, 将 updates 中的 key-value 原子写入 .env，保留其余行不动。      若 .env 不存在则自动创建。写入失败时抛出 RuntimeEr, read_dot_env(), write_dot_env(), Path, 测试 app.core.env_writer 模块。  覆盖： - read_dot_env()：文件不存在返回 {}；解析 key=value；忽略注释和空行, 值中包含 = 时，仅在第一个 = 处分割。, TestReadDotEnv (+7 more)

### Community 19 - "Community 19"
Cohesion: 0.12
Nodes (12): get_weekday_cn(), is_workday(), pick_three_workdays(), date, 日期计算服务 — 纯函数，无 IO，无数据库依赖。, 仅根据是否为周六/周日判断工作日（节假日由独立客户端判断，不耦合此处）。, 从指定年月的全部工作日中随机选取 3 个不同日期，按时间升序返回。      用于「一对一倾听」自动选取 3 个观察工作日（分布于全月，避免总是月初、1 号）。, Random (+4 more)

### Community 20 - "Community 20"
Cohesion: 0.11
Nodes (29): build_batch_export_filename(), build_export_filename(), default_year_month(), distribute_images_by_filename(), format_record_summary(), format_stage_label(), infer_age_by_grade(), pack_domain_files_to_zip() (+21 more)

### Community 21 - "Community 21"
Cohesion: 0.07
Nodes (31): API认证, API路由, API响应模型, JWT模块, 密码模块, 配置模块, 加密模块, 数据库模块 (+23 more)

### Community 22 - "Community 22"
Cohesion: 0.18
Nodes (28): _build_from_scratch(), _clear_cell(), _clear_paragraph(), export_course_review_activity(), _fill_template(), _get_bool(), _get_value(), _iter_body_blocks() (+20 more)

### Community 23 - "Community 23"
Cohesion: 0.18
Nodes (14): 审计日志：记录关键操作（登录、改密、AI 调用、Word 导出等）。  审计日志通过结构化 JSON logger 输出，统一携带 audit_action 与, get_logger(), 年龄适配 AI 客户端。  将活动过程原文按年龄段（小班/中班/大班）改写，返回改写后文本。  输出 Schema：     {"adapted_process, call_ai_text(), _make_retry_decorator(), AsyncClient, AI 客户端基础模块 — 通用 Chat Completions 调用。  所有 AI 调用必须通过此模块，禁止在 service 层直接发 HTTP 请求。, 发送 Chat Completions 请求，返回纯文本 content 字符串。      与 call_ai() 的区别：不强制 json_object 格 (+6 more)

### Community 24 - "Community 24"
Cohesion: 0.12
Nodes (19): _build_fernet(), decrypt(), encrypt(), 应用层对称加密工具（Fernet）。  密钥来源：Settings.ENCRYPTION_KEY（原始字符串，UTF-8 编码后取前 32 字节， 再经 bas, 将环境变量中的原始字符串密钥转换为 Fernet 实例。      Fernet 要求 32 字节的 URL-safe base64 编码密钥（共 44 个字符, 加密明文字符串，返回 URL-safe base64 密文字符串。      Args:         plain_text: 待加密的明文（禁止在调用方写入, 解密密文字符串，还原为原始明文。      Args:         cipher_text: 由 `encrypt()` 生成的密文字符串。      Re, CryptoError (+11 more)

### Community 25 - "Community 25"
Cohesion: 0.11
Nodes (20): ABC, ImageStorageBackend, 存储图片字节，返回存储引用 dict。          Returns:             dict，键因后端而异（blob_backend 含 blo, 从存储引用还原图片字节。          Args:             stored: 与 put 返回格式相同的 dict。          Ret, 可插拔图片存储后端抽象。      put / get 与数据库 session 解耦：     - put 返回 stored_ref dict，由 repo, BlobImageStorage, MySQL BLOB 图片存储后端。  put/get 只操作内存 dict，实际 DB 写入由 repository 层完成。, MySQL BLOB 后端：图片二进制存入 game_observation_image.blob_content。 (+12 more)

### Community 26 - "Community 26"
Cohesion: 0.13
Nodes (13): _build_signing_string(), get_api_principal(), parse_api_keys(), Request, 对外 REST API 鉴权：API Key + 可选 HMAC 签名。  鉴权模型（服务间调用）： 1. **API Key**（必填）：调用方在 `X-Ap, 解析 `API_KEYS` 配置为 {api_key: tenant_id} 映射。      格式："key1:1,key2:2"；忽略空段与格式非法段（te, 校验 HMAC-SHA256 请求签名与时间戳新鲜度。, FastAPI 依赖：校验 API Key（必填）与签名（按配置可选），返回调用方主体。 (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.14
Nodes (25): IndicatorCatalog, IndicatorCatalog — 一对一倾听指标目录（参考数据，迁移预置）。  按 (grade, term, domain) 组织一级/二级指标及三档（★, get_indicator_by_id(), list_available_stages(), list_indicators(), list_indicators_by_ids(), AsyncSession, indicator_repository — 指标目录数据访问层。  只读参考数据查询（指标目录按 tenant_id + grade + term + dom (+17 more)

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (23): ExportRecord, 导出记录数据模型。  对应数据库表：export_records 记录每次 Word 导出操作的元信息（文件名、路径、关联教案）。 导出记录为只增不改（immu, AsyncSession, 写入一条导出记录。      Args:         session: 异步数据库会话（调用方负责事务管理）。         tenant_id: 机构, save_export_record(), tests/test_export_repository.py — 导出记录仓库层测试。  使用 SQLite 内存库（async_session fixtur, 写入倾听导出记录时，listening_record_id 字段正确持久化。, 未传 listening_record_id 时，字段默认为 None（向后兼容）。 (+15 more)

### Community 29 - "Community 29"
Cohesion: 0.13
Nodes (16): app_shell(), get_display_name(), get_menu_items(), 共享布局组件 app_shell。  提供统一的左侧导航菜单 + 顶栏，供所有页面复用。  纯函数（可在 NiceGUI 渲染外调用，支持单测）： - get_, 根据角色返回可见菜单项列表，每项含 selected 标记。      Args:         role: 用户角色，如 'teacher' / 'teac, 返回顶栏显示名：优先 display_name，回退 username。      Args:         user: 包含用户信息的字典，通常来自 dec, 统一布局：左侧分组菜单 + 顶栏。      用法::          async with app_shell(user, active="daily-pl, home_page() (+8 more)

### Community 30 - "Community 30"
Cohesion: 0.13
Nodes (9): get_db(), AsyncSession, 对外 REST API 的 FastAPI 依赖。, 提供独立的异步数据库会话（只读查询，无需提交）。      测试可通过 ``app.dependency_overrides[get_db]`` 注入内存库会话, 对外 REST API 路由集成测试（httpx ASGITransport + SQLite 内存库）。, _seed(), TestConfigEndpoints, TestDailyPlans (+1 more)

### Community 31 - "Community 31"
Cohesion: 0.11
Nodes (16): _build_engine(), get_async_session(), AsyncSession, _resolve_database_url(), get_env_path(), Path, 运行时 .env 文件读写工具。  路径策略： - PyInstaller 打包模式：可执行文件同级目录 - 开发 / Docker 模式：当前工作目录  这与, 返回 .env 文件的绝对路径（位于用户可写数据目录）。 (+8 more)

### Community 32 - "Community 32"
Cohesion: 0.23
Nodes (17): ApiPrincipal, get_daily_plan(), health(), date, query_classes(), query_daily_plans(), query_semesters(), 对外 REST API v1 路由（只读）。  所有业务端点强制经过 API Key 鉴权，并以鉴权得到的 tenant_id 作为查询隔离条件， 调用方无法越 (+9 more)

### Community 33 - "Community 33"
Cohesion: 0.16
Nodes (20): AiParseError, AI 返回内容解析失败时抛出：JSON 格式非法、缺少必要字段等。, call_ai(), 发送 Chat Completions 请求，返回解析后的 dict。      Args:         messages: 消息列表，格式为 [{"rol, _make_error_response(), _make_openai_response(), Response, tests/test_ai_client_base.py — AI 客户端基础模块测试。  使用 httpx.MockTransport 隔离真实 HTTP 请 (+12 more)

### Community 34 - "Community 34"
Cohesion: 0.10
Nodes (20): GameObservationImage, Phase B — 数据模型冒烟测试（ORM + SQLite in-memory）。  测试策略： - 用 async_session fixture（SQL, GameObservation 可插入并按 id 查询。, GameObservation.tenant_id 非空约束生效。, AiApiKey 不传 key_type 时默认为 'text'。, GameObservationImage.blob_content 可存取二进制字节，值完全相同。, invite_code 表已通过迁移删除，ORM 模型已不存在。, ClassConfig 可保存 teacher_name 字段。 (+12 more)

### Community 35 - "Community 35"
Cohesion: 0.18
Nodes (18): ListeningImage, ListeningImage — 一对一倾听绘画图片数据模型。  每个领域 3 张（共 15 张/记录）。复用游戏观察图片的可插拔 BLOB 存储， 新增 do, add_image(), delete_images_by_record(), get_image(), list_images_by_record(), AsyncSession, listening_image_repository — 一对一倾听图片数据访问层。 (+10 more)

### Community 36 - "Community 36"
Cohesion: 0.17
Nodes (13): _get_state_path(), is_setup_complete(), mark_setup_complete(), Path, 首次运行状态管理：通过标记文件判断系统是否已完成初始化配置。  标记文件路径： - PyInstaller 打包模式：可执行文件同级目录 .kindergart, 返回 setup 完成标记文件的路径（位于用户可写数据目录）。, 检查系统是否已完成初始化配置（同步调用，纯文件检查，无 DB 查询）。, 写入 setup 完成标记文件。写入失败时静默忽略（不阻断正常流程）。 (+5 more)

### Community 37 - "Community 37"
Cohesion: 0.14
Nodes (13): is_near_holiday(), 中国法定节假日客户端。  特性： - 查询指定日期是否为法定节假日（True / False / None） - 查询是否为法定节假日前一天（near_holi, 判断 target_date 是否为法定节假日前一天。      返回语义：     - True  ：明天是法定节假日     - False ：明天不是法定, DatePanel, 日期选择面板组件（可复用）。  功能： - 日期选择器（NiceGUI ui.date） - 选择日期后自动计算并显示：第几周、周几、是否工作日 - 节假日状态, 外部或内部直接设置日期值，触发联动更新（同步入口）。, 日期选择器选值回调（同步，启动异步联动）。, 日期选择面板，可嵌入任意 NiceGUI 页面。      参数：         semester_start: 学期开始日期，用于计算第几周；传 None (+5 more)

### Community 38 - "Community 38"
Cohesion: 0.22
Nodes (17): CourseReviewActivity, 课程审议记录。      每条记录保存一次课程审议生成与教师编辑后的结果。班级、年龄段与教师姓名     采用冗余快照，避免后续系统设置变更影响历史导出。, create_course_review_activity(), delete_course_review_activity(), get_course_review_activity(), list_course_review_activities(), AsyncSession, 删除课程审议记录，强制 tenant_id + user_id 双重过滤。 (+9 more)

### Community 39 - "Community 39"
Cohesion: 0.24
Nodes (18): _build_from_scratch(), _clear_cell(), export_homemade_teaching(), _fill_template(), _get_value(), Any, Document, Path (+10 more)

### Community 40 - "Community 40"
Cohesion: 0.13
Nodes (15): Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online(), build_sync_url(), _get_alembic_ini_path(), _get_alembic_script_location(), 应用启动模块：自动执行 Alembic 数据库迁移。  支持三种运行模式： - 开发模式（python -m app.main）：直接运行，alembic.in (+7 more)

### Community 41 - "Community 41"
Cohesion: 0.13
Nodes (14): APIRouter, create_api_router(), 对外只读 REST API（二期）。  通过 :func:`create_api_router` 暴露 ``/api/v1`` 路由，由 ``app/main., 返回组装好的对外 API 路由（当前仅 v1）。, 应用启动引导。  dev3.4 恢复登录系统后，不再自动创建默认管理员账号。 首次管理员应通过安装器初始化、CLI 或 `/setup-admin` 页面创建。, 应用启动时调用：登录模式下无需自动创建用户。, run_bootstrap(), main() (+6 more)

### Community 42 - "Community 42"
Cohesion: 0.18
Nodes (17): add_image(), delete_images_by_observation(), get_image(), list_images_by_observation(), AsyncSession, observation_image_repository — 游戏观察图片数据访问层。, 新增一张观察图片记录，返回带 id 的对象。, 查询某观察记录下的所有图片，按 image_index 升序排列。 (+9 more)

### Community 43 - "Community 43"
Cohesion: 0.15
Nodes (19): 认证中间件, 审计模块, 认证服务, auth_service, user_repository, 审计日志, 数据隔离, JWT鉴权 (+11 more)

### Community 44 - "Community 44"
Cohesion: 0.20
Nodes (16): DailyPlan, 每日活动计划数据模型。  对应数据库表：daily_plan 包含教案拆分、年龄适配改写、一日活动生成等所有字段。, 每日活动计划表。      字段说明：     - plan_date：计划日期（对应学期中的某一天）     - week_number：第几周（由 date, delete_daily_plan(), get_daily_plan_by_date(), get_daily_plan_by_id(), list_daily_plans(), AsyncSession (+8 more)

### Community 45 - "Community 45"
Cohesion: 0.17
Nodes (16): build_export_filename(), 游戏观察记录页面（路由：/game-observation）。  功能：   - 表单输入观察元数据（日期、大环境、游戏区域、人数、幼儿、观察者）   - 图片, 构造导出文件名。      格式：{tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx, 校验大环境值是否合法（仅允许 户外/室内/公共）。, 校验图片数量是否在合法范围（1~3 张）。, validate_big_env(), validate_image_count(), tests/test_observation_ui_helpers.py — 游戏观察 UI 工具函数测试。  测试覆盖（3 项纯函数）：   1. 导出文件名 (+8 more)

### Community 46 - "Community 46"
Cohesion: 0.17
Nodes (18): 系统架构文档, AI密钥表, 班级配置表, 课程审议活动表, 每日活动计划表, 导出记录表, 游戏观察表, 游戏观察图片表 (+10 more)

### Community 47 - "Community 47"
Cohesion: 0.13
Nodes (17): create_initial_admin(), 自助注册：      创建 is_active=False 的待审核教师账号，需管理员审核通过后方可登录。      tenant_id 固定为 setting, 创建首次系统管理员。      仅当当前租户不存在启用的 sys_admin 时允许创建，用于安装器初始化与     `/setup-admin` 首次启动兜底, register_user(), 无 active sys_admin 时可创建首次管理员。, 已有 active sys_admin 时不能重复初始化管理员。, 没有系统管理员时，注册应提示先初始化管理员。, 已有管理员后，注册者成为 teacher（is_active=False），需管理员审核。 (+9 more)

### Community 48 - "Community 48"
Cohesion: 0.17
Nodes (15): generate_observation_content(), AsyncSession, 游戏观察服务层 — 生成与持久化。  职责：   - generate_observation_content：取 vision Key → 查提示词 → 压缩, 事务写入观察记录 + 图片，返回 observation_id。      Args:         session: 异步数据库会话。         ob, 调用视觉 AI 生成游戏观察四段内容，返回结果 dict（含 compressed_images）。      Args:         session: 异, save_observation_with_images(), tests/test_observation_service.py — 游戏观察服务层测试。  测试覆盖：   1. 未配置视觉 Key → ConfigErr, DB 中有激活的 game_observation 提示词时，覆盖内置默认提示词传给 AI。 (+7 more)

### Community 49 - "Community 49"
Cohesion: 0.22
Nodes (13): ensure_default_user(), AsyncSession, User, UserRole, has_any_user(), 检查指定租户是否已有任意用户，用于判断注册者是否是第一个用户。, create_test_teacher(), str (+5 more)

### Community 50 - "Community 50"
Cohesion: 0.28
Nodes (13): HomemadeTeachingToy, 教师自制教玩具记录。      每条记录保存一次 AI 生成或教师编辑后的教玩具方案。班级与教师姓名     采用冗余快照，避免后续设置变更影响历史导出。, create_homemade_teaching_toy(), delete_homemade_teaching_toy(), get_homemade_teaching_toy(), list_homemade_teaching_toys(), AsyncSession, 按 id 查询记录，强制 tenant_id 过滤。 (+5 more)

### Community 51 - "Community 51"
Cohesion: 0.22
Nodes (13): SemesterConfig, get_active_semester(), list_semesters(), AsyncSession, date, 查询当前用户的激活学期配置，若不存在返回 None。, 保存学期配置：若已存在激活记录则更新，否则新建。     同一用户只保留一条 is_active=True 的记录。, 按租户（可选用户）查询学期配置列表，按更新时间降序。 (+5 more)

### Community 52 - "Community 52"
Cohesion: 0.23
Nodes (14): _build_user_content(), generate_homemade_teaching(), generate_homemade_teaching_content(), AsyncSession, _make_client(), AsyncClient, test_generate_homemade_teaching_filters_extra_keys(), test_generate_homemade_teaching_invalid_payload_raises() (+6 more)

### Community 53 - "Community 53"
Cohesion: 0.21
Nodes (15): 将完整教案文本拆分为结构化字段。      Args:         raw_text: 用户粘贴的完整教案文本。         api_base_url:, split_lesson_plan(), _make_client(), AsyncClient, tests/test_lesson_plan_client.py — 教案拆分客户端测试。  使用 httpx.MockTransport 隔离真实 HTTP, AI 返回空 dict 时，抛出 AiParseError。, AI 返回额外字段时，只保留 5 个必要键。, 正常响应时，返回包含全部 5 个键的 dict。 (+7 more)

### Community 54 - "Community 54"
Cohesion: 0.24
Nodes (14): build_course_review_activity_filename(), _clean_filename_part(), course_review_activity_page(), format_setting_summary(), 课程审议页面（路由：/course-review-activity）。, validate_course_review_form(), validate_generation_context(), test_build_course_review_activity_filename() (+6 more)

### Community 55 - "Community 55"
Cohesion: 0.17
Nodes (12): _ensure_cache_fresh(), get_legal_holidays_in_year(), is_adjusted_workday(), date, 一次性查询整年的法定节假日集合（单请求，避免逐日并发触发限流）。      用于「一对一倾听」批量选取工作日时排除节假日。复用 timor.tech 的「年」接, 判断指定日期是否为调班工作日（节假日调休补班的周末）。      返回语义：     - True  ：调班工作日（API type == 3），周末需正常上班, 若缓存日期不是今天，清空缓存（单日缓存 + 年节假日缓存）。, AsyncBaseTransport (+4 more)

### Community 56 - "Community 56"
Cohesion: 0.19
Nodes (8): is_holiday(), 查询指定日期是否为法定节假日。      返回语义（固定）：     - True  ：法定节假日（API type == 2）     - False ：工作, 普通工作日（type=0）返回 False, 普通周末（type=1）返回 False（与法定节假日语义严格区分）, 调班工作日（type=3）返回 False, API 返回 5xx 时降级，返回 None, 同一日期第二次调用命中缓存，不发出 HTTP 请求, TestIsHoliday

### Community 57 - "Community 57"
Cohesion: 0.14
Nodes (15): adapt_client, api_router, audit, daily_plan_repository, diff_service, generate_client, middleware, prompt_repository (+7 more)

### Community 58 - "Community 58"
Cohesion: 0.19
Nodes (9): AuthMiddleware, Request, 路由守卫中间件。  登录恢复后，NiceGUI 页面在页面函数内通过 `app.ui.auth_context` 校验登录态； 中间件保持直通，避免 WebSo, BaseHTTPMiddleware, tests/test_middleware.py — 登录恢复后的路由中间件测试。  验证： - 登录页面根路径 (/) 直接放行 - 其他路由直接放行，页面层, 中间件可被实例化（接收 ASGI app 参数）。, test_middleware_instantiable(), test_non_root_passes_through() (+1 more)

### Community 59 - "Community 59"
Cohesion: 0.25
Nodes (13): adapt_activity_process(), 将活动过程按年龄段改写。      Args:         original: 活动过程原文。         grade: 年龄段，如"小班"、"中班"、, _make_client(), AsyncClient, tests/test_adapt_client.py — 年龄适配客户端测试。, AI 返回缺少 adapted_process 字段时，抛出 AiParseError。, 原文为空字符串时，不发请求直接抛出 AiParseError。, 传入自定义 system prompt 时，正常调用不报错。 (+5 more)

### Community 60 - "Community 60"
Cohesion: 0.19
Nodes (9): _get_plain_key_for_save(), _mask_api_key(), 个人 AI 接口配置页面（路由 /setup）。, 根据输入框内容解析要保存/验证的明文 Key。, setup_page(), tests/test_setup_page.py — 简化后的 /setup 页面 AI 配置逻辑测试。  验证： - setup 页面仅包含 AI 配置功能（, 8位以上 key 显示 sk-**** + 末4位。, 短于8位的 key 只显示 sk-****。 (+1 more)

### Community 61 - "Community 61"
Cohesion: 0.21
Nodes (14): 游戏观察AI客户端, 视觉AI模块, 图片处理模块, 游戏观察服务, 共享布局, 五大领域, 游戏观察, 指标体系 (+6 more)

### Community 62 - "Community 62"
Cohesion: 0.25
Nodes (14): lesson_plan_client, 登录系统, 手动测试文档, AI接口调用约定, 数据库与ORM约定, 项目README, 依赖清单, Alembic迁移 (+6 more)

### Community 63 - "Community 63"
Cohesion: 0.23
Nodes (11): Path, 应用配置：通过 pydantic-settings 从 .env 文件和环境变量加载。  首次部署（无 .env 文件）时的行为： - DATABASE_URL, 返回自动生成密钥的持久化文件路径（位于用户可写数据目录）。, 解析 key=value 文件，忽略空行与注释行。, 将新键值追加/覆盖到持久化文件（已有键保留）。, 自动生成缺失的密钥并持久化，保证重启后可还原。, _read_kv_file(), _secrets_file_path() (+3 more)

### Community 64 - "Community 64"
Cohesion: 0.21
Nodes (13): 年龄适配客户端, 活动生成客户端, 教案拆分客户端, Word导出器, 差异比对服务, 教案服务, 活动生成, 年龄适配 (+5 more)

### Community 65 - "Community 65"
Cohesion: 0.21
Nodes (13): 课程审议AI客户端, 自制教玩具AI客户端, 课程审议服务, 自制教玩具服务, 课程审议, 自制教玩具, 文本AI, 课程审议活动设计 (+5 more)

### Community 66 - "Community 66"
Cohesion: 0.30
Nodes (10): get_class_config(), list_class_configs(), AsyncSession, 查询当前用户的班级配置，若不存在返回 None。, 保存班级配置：若已存在则更新，否则新建。     每个用户只保留一条班级配置记录（最新）。, 按租户（可选用户）查询班级配置列表，按更新时间降序。, upsert_class_config(), test_upsert_class_config_saves_teacher_name() (+2 more)

### Community 67 - "Community 67"
Cohesion: 0.24
Nodes (11): generate_activity_content(), AsyncSession, 生成单项活动内容。      Args:         session: 异步数据库会话（查询 AI Key 与自定义提示词）。         tenant, _make_mock_ai_key(), tests/test_generate_service.py — 一日活动生成服务测试。  使用 Mock 隔离 AI 调用、AI Key 仓库与提示词仓库。, 用户未配置 AI Key 时抛出 ConfigError。, 无自定义提示词时，使用内置默认（system_prompt=None）并返回生成文本。, 存在激活的自定义提示词时，将其传给 generate_activity。 (+3 more)

### Community 68 - "Community 68"
Cohesion: 0.32
Nodes (12): 更新日志, 倾听AI客户端, 倾听服务, listening_repository, listening_service, 一对一倾听, indicator_catalog表, listening_domain表 (+4 more)

### Community 69 - "Community 69"
Cohesion: 0.20
Nodes (12): 异常模块, AI基础模块, 节假日客户端, 日期服务, AI集成, 课程审议记录子系统, 自制教玩具子系统, Word导出 (+4 more)

### Community 70 - "Community 70"
Cohesion: 0.17
Nodes (9): migrated_db(), P1 — 一对一倾听迁移与种子集成测试。  在临时 sqlite 文件库上实际执行 `alembic upgrade head`，验证： - 5 个新表创建成功, export_records 含 listening_record_id 列。, 种子 JSON：5 领域共 30 个二级指标，每个含 3 档标准、sort_order 连续。, 在临时 sqlite 文件库上执行 alembic upgrade head，返回库路径。, 每条种子三档标准非空，tenant_id=1，max_stars=3。, test_export_records_has_listening_col(), test_indicator_seed_integrity() (+1 more)

### Community 71 - "Community 71"
Cohesion: 0.17
Nodes (11): P1 — 一对一倾听数据模型冒烟测试（ORM + SQLite in-memory）。  用 async_session fixture（create_all）, IndicatorCatalog 可创建并保存三档标准。, ListeningRecord 可创建；adult_count 默认 1。, ListeningDomain 支持领域级年月与 3 个日期。, ListeningImage 存储 blob + domain + image_index + 描述。, ListeningIndicatorResult 不传 stars 时默认 3。, test_indicator_catalog_create(), test_listening_domain_create() (+3 more)

### Community 72 - "Community 72"
Cohesion: 0.44
Nodes (10): _build_user_content(), generate_course_review_activity(), _make_client(), AsyncClient, test_generate_course_review_activity_filters_extra_keys(), test_generate_course_review_activity_invalid_string_payload_raises(), test_generate_course_review_activity_requires_boolean_fields(), test_generate_course_review_activity_success() (+2 more)

### Community 73 - "Community 73"
Cohesion: 0.27
Nodes (4): get_special_day_tags(), 返回不放假节日标签列表（本地硬编码）。     空列表表示该日期无特殊节日标注。     返回值为副本，修改不影响内部数据。, Step 2.4 — 节假日客户端测试  使用自定义 httpx.AsyncBaseTransport 模拟 API，测试： - 正常响应的 bool 返回值（, TestGetSpecialDayTags

### Community 74 - "Community 74"
Cohesion: 0.27
Nodes (5): get_week_number(), 返回 target_date 是开学后第几周（第 1 周起算）。      例：start_date=周一，target_date=同一天 → 第 1 周；, start_date 为周三时，目标日期在同一自然周内仍为第 1 周, 目标日期早于开学日，返回 ≤ 0（允许调用方自行处理，不抛异常）, TestGetWeekNumber

### Community 75 - "Community 75"
Cohesion: 0.33
Nodes (3): is_within_semester(), 判断 target_date 是否在学期范围内（含首尾两天）。, TestIsWithinSemester

### Community 76 - "Community 76"
Cohesion: 0.22
Nodes (5): display_name 有值时返回 display_name。, display_name 为 None 时返回 username。, display_name 为空字符串时返回 username。, user dict 中无 display_name 键时返回 username。, TestGetDisplayName

### Community 77 - "Community 77"
Cohesion: 0.36
Nodes (6): get_current_user(), 已弃用的单用户上下文兼容模块。  dev3.4 起页面应使用 `app.ui.auth_context.get_current_user_or_redirect, tests/test_user_context.py — 单用户上下文测试。  覆盖： - get_current_user 返回正确的默认用户字典 - 返回值, 每次调用返回独立副本，修改不影响后续调用。, test_returns_copy_each_call(), test_returns_default_user()

### Community 78 - "Community 78"
Cohesion: 0.50
Nodes (7): generate_course_review_activity_content(), AsyncSession, _make_mock_ai_key(), _result(), test_generate_course_review_activity_content_no_ai_key_raises(), test_generate_course_review_activity_content_success_with_default_prompt(), test_generate_course_review_activity_content_uses_db_prompt()

### Community 79 - "Community 79"
Cohesion: 0.36
Nodes (8): get_current_user_or_redirect(), 读取当前登录用户；未登录或无权限时跳转。      Args:         redirect_to: 未登录/无效 token 时跳转地址。, 渲染顶栏和左侧抽屉（无 context manager 版本）。      供已有页面调用：在页面函数开头调用一次，内容随后在同一层级放置。      Args, render_shell(), game_observation_page(), one_on_one_listening_page(), profile_page(), user_admin_page()

### Community 80 - "Community 80"
Cohesion: 0.36
Nodes (8): Docker Compose生产配置, Docker Compose开发配置, app服务, caddy服务, db服务, GitHub Release工作流, Caddy反向代理, MySQL数据库

### Community 81 - "Community 81"
Cohesion: 0.29
Nodes (4): 入库后 api_key_encrypted 不能与明文相同。, 新保存的记录 is_active 应为 True。, api_base_url 字段应与传入值一致。, TestSaveAiKey

### Community 82 - "Community 82"
Cohesion: 0.29
Nodes (5): 测试图片相关配置项（Phase A）。  验证新增的 IMAGE_STORAGE_BACKEND 和 IMAGE_MAX_BYTES 配置项存在且默认值正确，, IMAGE_MAX_BYTES 默认值为 1048576（1MB）。, IMAGE_STORAGE_BACKEND 默认值为 mysql_blob。, test_image_max_bytes_default(), test_image_storage_backend_default()

### Community 83 - "Community 83"
Cohesion: 0.40
Nodes (4): downgrade(), Upgrade schema.      列 model_name 可能已存在（来自另一台机器的未提交迁移）。     若不存在则新增；若已存在则修改为 NOT, Downgrade schema: 恢复为可空、无默认值。, upgrade()

### Community 84 - "Community 84"
Cohesion: 0.40
Nodes (4): downgrade(), 删除 invite_code 表（邀请码功能已移除）。, 重建 invite_code 表（回滚用）。, upgrade()

### Community 85 - "Community 85"
Cohesion: 0.80
Nodes (4): downgrade(), _has_column(), _has_table(), upgrade()

### Community 86 - "Community 86"
Cohesion: 0.40
Nodes (5): _auto_pick_workdays(), _parse_iso_date(), date, 容错解析 YYYY-MM-DD，失败返回 None。, 单次查询整年法定节假日（避免逐日并发触发限流），随机返回本月 3 个工作日。      Returns:         (dates, holidays_av

### Community 87 - "Community 87"
Cohesion: 0.40
Nodes (4): async_session(), AsyncSession, 公共测试 fixture。  提供基于 SQLite 内存库的异步 session，用于仓库层集成测试， 与真实 MySQL 连接完全隔离。, 每个测试函数获得独立的 SQLite 内存库 + 全新表结构。

### Community 89 - "Community 89"
Cohesion: 0.83
Nodes (3): downgrade(), _has_column(), upgrade()

### Community 90 - "Community 90"
Cohesion: 0.83
Nodes (3): downgrade(), _has_table(), upgrade()

### Community 91 - "Community 91"
Cohesion: 0.83
Nodes (3): downgrade(), _has_column(), upgrade()

## Knowledge Gaps
- **63 isolated node(s):** `build-deb.sh script`, `用户使用手册`, `Monorepo架构`, `DockerComposeAIO`, `Caddy反向代理` (+58 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AiParseError` connect `Community 33` to `Community 2`, `Community 37`, `Community 72`, `Community 8`, `Community 9`, `Community 12`, `Community 45`, `Community 16`, `Community 52`, `Community 53`, `Community 54`, `Community 23`, `Community 20`, `Community 59`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `log_audit()` connect `Community 11` to `Community 67`, `Community 5`, `Community 6`, `Community 37`, `Community 10`, `Community 12`, `Community 45`, `Community 78`, `Community 47`, `Community 48`, `Community 16`, `Community 52`, `Community 20`, `Community 54`, `Community 23`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `get_logger()` connect `Community 23` to `Community 0`, `Community 2`, `Community 3`, `Community 37`, `Community 6`, `Community 39`, `Community 41`, `Community 9`, `Community 45`, `Community 14`, `Community 16`, `Community 20`, `Community 22`, `Community 54`, `Community 31`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `AiParseError` (e.g. with `format_user_error()` and `test_adapt_empty_original_raises_parse_error()`) actually correct?**
  _`AiParseError` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `ConfigError` (e.g. with `LessonPlanResult` and `format_user_error()`) actually correct?**
  _`ConfigError` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Base` (e.g. with `AiApiKey` and `ClassConfig`) actually correct?**
  _`Base` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `DailyPlan` (e.g. with `ClassConfigOut` and `DailyPlanListOut`) actually correct?**
  _`DailyPlan` has 17 INFERRED edges - model-reasoned connections that need verification._