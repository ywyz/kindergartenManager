# 模板中心第一期冻结规格

- 状态：冻结稳定 RED；双轴 Review Standards 0 / Spec 0；不授权生产 GREEN、迁移、合并或发布
- 关联方向：[`docs/PRODUCT_DIRECTION.md`](../../docs/PRODUCT_DIRECTION.md) §3.1、§5
- 前置门：Issue #55 的角色/跨教师读取/审核/导出/删除矩阵；[ADR-0008](../../docs/ADR/ADR-0008-word-template-authority-versioning-and-secure-storage.md)
  （取代或细化 [`ADR-0004`](../../docs/ADR/ADR-0004-ai-and-fixed-word-boundaries.md) 的固定模板权威来源子决策）
- 目标阶段：R6-P0，先复用当前五类 exporter，再由独立的周/月业务 spec 接入周/月文档类型

本规格只冻结模板基础设施。它不冻结周/月计划的业务事实，也不把模板管理、权限治理和统一教学文档中心
合并成一个交付。

## 1. 目标与停止边界

模板中心把“开发者直接从仓库读取固定 DOCX”升级为“受契约约束、可追溯、可回滚的版本化模板源”。
一期必须让模板操作具备以下性质：

1. 文档类型是关闭 registry，版本是不可变的、按租户与类型寻址的对象。
2. 上传先经过安全的 OOXML/占位符/结构校验；失败不留下 blob、版本、激活指针或审计半成品。
3. 激活、停用和回滚使用乐观并发版本；任意时刻每个租户/文档类型最多一个 active 版本。
4. UI 只获得经过 Issue #55 授权投影的元数据和操作集合，不获得存储路径、原始 blob、ORM 或内部端口。
5. 合成预览只消费明确标记的合成数据，不读取真实教学/幼儿正文，不创建正式导出记录。
6. 生命周期和安全拒绝可由最小脱敏审计复原；审计和模板 blob 不提供 update/delete。
7. 备份与恢复采用受控、可验证、分阶段提交的端口；失败保持源状态不变。
8. 现有 exporter 通过版本引用和解析报告获得模板；缺 active 版本时不得悄悄从零构建或切换未审计模板。

以下内容明确不在一期：

- 周/月计划的数据模型、页面、保存/复制/审核流、业务字段映射和批量规则；它们属于独立业务 spec/RED。
- 统一教学文档中心、导出物长期索引/归档/ZIP 管理、资源复用、完整审核工作流或成长档案。
- 在线拖拽式 Word 编辑器、宏/脚本/ActiveX/OLE 执行、任意 XML 修复、模型自动选模板或自动改模板。
- 改写当前五类 exporter 的业务字段；本期只定义接线端口和验收边界。
- 自动增加数据库表、Alembic migration、租户/教师/幼儿主数据、Provider WRITE、Agent Tool 或长期记忆。

任何新增文档类型、占位符字段、角色能力、导出持久化语义或外部存储后端，都需要独立变更说明和相应
Review RED；不能从本 spec 的局部 GREEN 推导其他阶段已授权。

## 2. 现状与模板权威来源

当前代码中的五个 exporter 各自直接打开仓库文件，并在缺失/异常时有从零构建兜底：

| registry key | 当前代码入口 | 当前仓库源文件 | 本期处理 |
|---|---|---|---|
| `daily_plan` | `app.integration.word_export.exporter.export_daily_plan` | `templates/teacherplan.docx` | 首批导入，保留现有结构契约 |
| `game_observation` | `app.integration.word_export.observation_exporter.export_observation` | `templates/ObservationRecord.docx` | 首批导入，保留图片/中文字体结构契约 |
| `one_on_one_listening` | `app.integration.word_export.listening_exporter.export_*` | `templates/OneOnOneListeningSmallSecond.docx` | 首批导入，保留五领域/图片/指标结构契约 |
| `homemade_teaching` | `app.integration.word_export.homemade_teaching_exporter.export_homemade_teaching` | `templates/homemadeteaching.docx` | 首批导入 |
| `course_review_activity` | `app.integration.word_export.course_review_activity_exporter.export_course_review_activity` | `templates/coursereviewactivity.docx` | 首批导入 |

以上文件是当前 checkout 的仓库基线源。迁移到模板中心后，运行时权威改为模板中心的版本 blob、版本元数据、
契约 manifest 和 active 指针；仓库文件只用于可复现的 seed/开发校验，不得绕过 registry 成为正式导出源。
每个 seed 必须记录来源相对路径、来源 SHA-256、导入时的代码/契约版本和导入人/时间；不能把工作树的绝对
路径或任意可变文件名写入运行时记录。

`templates/weekplan.docx` 与 `templates/monthplan.docx` 是当前工作树提供的候选参考资产：

- `weekplan.docx` 对应“每周活动计划/周视角”，`monthplan.docx` 对应“月主题活动计划/月视角”；
- 它们不属于本期五类 initial registry，不在本期 seed、激活、备份白名单或模板中心 RED 的通过条件内；
- 只有在周/月业务 spec 的数据模型、字段映射、Word 解析验收和独立 RED 通过后，才能以新的文档类型契约
  导入模板中心；本期不得修改、重命名、删除、跟踪或替换这两个用户提供的文件。

模板源的权威层次固定为：

1. 已接受的模板契约 ADR、本文的 registry/安全/生命周期约束；
2. 模板中心保存的不可变 blob + 经验证的版本/契约 manifest + active 指针；
3. 受保护备份中的同一版本对象和校验 manifest；
4. 仓库固定模板只作为带 SHA 的初始 seed/可复现开发输入。

若源文件、数据库元数据、blob 或备份 manifest 的 hash 不一致，必须 fail closed；不得按文件名、最新修改时间
或目录遍历结果猜测“当前模板”。

## 3. 领域概念与数据模型

### 3.1 关闭文档类型 registry

全局已知文档类型闭合为七个；其顺序和 key 均属于契约：

```text
daily_plan
game_observation
one_on_one_listening
homemade_teaching
course_review_activity
weekly_activity_plan
monthly_theme_activity_plan
```

一期 enabled registry 恰好启用前五个类型，顺序和 key 均属于一期契约；全局 known 的后两个类型在一期只作为
明确的 disabled/reserved key 存在。只有周/月两个独立业务 spec 的数据模型、导出契约、稳定 RED 和 Review 通过，
并得到单独 GREEN 授权后，后续 registry 才能一次性 enabled 全部七个类型。任何 enabled 集合变化都不是运行时
开关或页面 payload 能力。

对 disabled/reserved 的 `weekly_activity_plan` 和 `monthly_theme_activity_plan`，一期所有
`upload`、`activate`、`resolve_active` 和 `project` 调用均必须 fail closed；它们不能出现在一期
`descriptors()`、active 查询、导出解析或权限投影结果中。registry 不提供任意字符串注册、运行时反射、fallback
alias 或动态 exporter discovery。

一期 registry 的最小查询契约为 `known_keys() -> tuple[7]`、`descriptors() -> tuple[5]` 和
`is_enabled(document_type) -> bool`；known 与 enabled 必须由同一闭合契约发布，不能依赖数据库或页面传入的
feature flag。后续启用七类必须发布新的 registry/contract 版本并通过 T011，不得在一期运行时偷偷改变 `descriptors()`。

每个 `DocumentTypeDescriptor` 至少包含：

- `key`、显示名、契约 ID/版本、占位符契约版本；
- 允许的导出 parser/renderer port 标识；
- 初始 seed 的仓库相对路径和固定 SHA（若该类型由仓库 seed 初始化）；
- 结构检查配置的版本；
- 可见的操作 capability 名称集合。内部 ORM、文件路径和 blob key 不出现在 UI 投影。

descriptor 本身由代码/契约发布，不由教师上传或页面 payload 改写。任何 registry 演进须先更新 spec、RED 和
迁移/兼容说明。

### 3.2 不可变版本与 active 指针

每个版本由以下不可变 `TemplateVersionRef` 表示；引用不携带 blob 内容：

```text
template_version_id: UUID
tenant_id: positive int
document_type: closed registry key
version: positive int, per (tenant_id, document_type) monotonic and never reused
content_sha256: lowercase 64-hex SHA-256
size_bytes: positive int, <= 16 MiB
mime_type: exact application/vnd.openxmlformats-officedocument.wordprocessingml.document
extension: .docx
blob_ref: content-addressed reference derived only from content_sha256
contract_id: closed contract identifier
contract_version: positive int
validation_receipt_id: UUID
validation_status: validated
validated_at_utc: timezone-aware UTC
validator_version: closed validator identifier
source: repository_seed | upload | restore
created_by_user_id: positive int (null only for repository_seed)
created_at_utc: timezone-aware UTC
```

上传请求中的 raw candidate 只在校验事务内短暂处于 `uploaded`；只有通过当前 contract/profile 安全校验的对象
才会以 `validation_status=validated` 写入版本库。失败 candidate 不成为版本。版本的 validation 证据和
active pointer 是两个独立的不可变/追加记录；`active` 不是版本字段，也不是版本状态：

- `TemplateVersionRef` 没有 `active`、`inactive` 或任何终态生命周期字段，不能通过 update/delete 修改验证结果、内容
  或版本号；
- `TemplateRegistryState` 只由追加的 pointer transition 推导；一个仍满足当前 contract 的 `validated` 版本
  可以被激活、停用后再次激活，也可以被回滚多次；停用只把 pointer 置空，不使验证结果失效；
- 只有当前有效的 validation 证据才能成为 active；contract/profile/安全规则升级导致证据失效时，必须重新验证并
  创建新版本，不能把旧对象原地修复。

版本元数据没有 `UPDATE` 或 `DELETE` seam。`TemplateRegistryState` 中由 append-only pointer transition 推导的指针为：

```text
registry_revision: positive int
active_version_id: UUID | null
active_content_sha256: lowercase 64-hex | null
last_transition_event_id: UUID
```

激活/停用/回滚必须以 `(tenant_id, document_type, expected_registry_revision, expected_active_version_id)`
做 compare-and-swap；成功使 `registry_revision` 恰好加一，并追加一个不可变 transition event。每个类型只允许
一个 active 指针；停用后的导出解析必须明确返回 `template_not_active`，不能恢复旧指针或切换仓库文件。
回滚只是把 active 指针指向一个仍经当前 contract 验证的旧版本，不修改任何版本/validation 记录，也不重排 `version`。

版本和事件返回给 UI/导出方时，只返回必要的 ID、版本号、hash、契约版本和时间；不返回 blob、绝对路径、压缩包
成员、数据库对象、业务正文或 secret。

### 3.3 存储边界

生产代码只能通过窄 `TemplateBlobStorePort` 读写内容寻址 blob：

```text
put_if_absent(content_sha256, content) -> BlobRef
read(blob_ref, expected_sha256) -> bytes
exists(blob_ref, expected_sha256) -> bool
```

实现可以是受控本地目录或对象存储，但服务层不接收任意路径，不拼接用户输入，不让 UI/导出方拿到存储
root。相同 hash 的内容只保留一个不可变 blob；每次通过授权且通过校验的 upload 都必须创建新的版本号和版本 ID，
即使其内容 hash 与历史版本相同，blob 仍由 `put_if_absent` 去重。hash 冲突、读取 hash 不符、非普通文件、symlink、
权限不安全或存储异常均 fail closed。

版本库的写入不能由 service 直接 append，也不能依赖事后删除/更新补偿。只允许通过 staged
`TemplateUnitOfWorkPort` 完成可见性提交：

```text
begin(tenant_id, document_type) -> TemplateUnitOfWork
TemplateUnitOfWork.stage_version(version_ref) -> None
TemplateUnitOfWork.stage_transition(transition_event) -> None
TemplateUnitOfWork.stage_audit(audit_event) -> None
TemplateUnitOfWork.commit() -> CommitReceipt
```

`TemplateVersionStorePort` 的读端口只提供 `get_version`、`snapshot` 和一致性读取；版本、transition 和 audit
在 `commit()` 前均不可见，且一次 commit 要么全部可见，要么全部不可见。stage/commit 失败只丢弃本次未提交的
staging，不暴露任意 record-level `UPDATE`/`DELETE`。active pointer 的 CAS 约束在同一 unit of work 内检查和
提交；任何审计写入失败都不能提交已 stage 的版本或 transition，且失败的 audit event 本身也不可见。

本地存储根目录必须位于仓库、源码、运行时 `exports` 和数据库目录之外；目录 owner-only（POSIX 根目录 `0700`，
blob 文件 `0600`）。生产实现不得以临时文件、编辑器锁文件、SQLite WAL/journal 或未完成 rename 的半成品作为
可见版本。

### 3.4 上传与 OOXML 安全校验

`validate_upload(content, filename, content_type, contract)` 是无副作用、可单独测试的公共 port；通过前不得调用
版本库、blob 或 active 指针，也不得由 validator 自己写审计。校验必须同时满足：

- 文件名是规范化的单一 basename，大小写归一后扩展名恰为 `.docx`，并且请求 MIME 恰为
  `application/vnd.openxmlformats-officedocument.wordprocessingml.document`；拒绝绝对路径、`..`、`/`、反斜杠、控制
  字符、隐藏锁文件、`.docm`/`.dotm` 和任意非 UTF-8 文件名；
- 内容是 ZIP/OOXML，必须有固定的 `[Content_Types].xml`、根关系、`word/document.xml` 和契约允许的
  WordprocessingML 部件；ZIP 成员名为相对 POSIX 路径，不得有路径穿越、重复名、symlink 或未知可执行部件；
- ZIP 成员最多 256 个，全部解压后的成员合计不超过 64 MiB，单部件不超过 16 MiB，压缩比超过 100:1 的部件拒绝；坏 CRC、截断、加密 ZIP、
  XML 解析失败、外部 entity/外部关系、外部链接、远程图片/模板关系、宏 `vbaProject.bin`、ActiveX、OLE、
  `customUI` 或宏启用 content type 一律拒绝；
- `word/document.xml` 与契约允许的 header/footer 等部件可解析，必需结构锚点/表格形状存在；当前五个 legacy
  模板的结构 manifest 由各 exporter adapter 提供，不能用“能被 python-docx 打开”替代结构校验；
- 解析出的占位符只允许出现在对应类型的闭合 contract 中；未知、缺失、重复策略不符、嵌套、表达式、URL、
  文件路径、宏指令、条件/循环/包含语法一律拒绝；校验报告只含 token ID、kind、位置和 hash，不含 token 值。

上传流程必须是 `validate → write blob if absent → stage version + audit → commit` 的一个受控用例；每次通过授权的
upload（包括相同内容 hash 的重复 upload）都要分配新的、永不复用的 version 和 UUID，且同 hash 只产生一个 blob。
validator 拒绝时，service 必须在不泄露输入的前提下追加一条完整的拒绝审计，但不得创建 blob、版本或 active
指针；validator 自身仍不写审计。任何后续步骤失败时，版本不可见，已写入但未被引用的 blob 只能由受控
orphan-cleaner 在独立门中清理，
不能由调用方直接删除或复用。上传不会自动激活。

### 3.5 占位符与 contract manifest

一期冻结的通用 token 语法为 `{{kg.<document_type>.<field>}}`，其中 `<document_type>` 和 `<field>` 只允许对应 contract 的
小写 ASCII 闭合标识符及点号，
不得包含空白、引号、冒号、斜杠、反斜杠、括号、表达式、模板控制语句或任意函数调用。token 可以被 Word 拆分
到多个 run；解析器必须在同一文本容器内按文档顺序重建文本后识别，不能靠单个 run 的 substring 判断。token
允许跨 run，但不得跨段落、表格单元格、表格、文档 part 或不受支持的文本框/绘图边界；跨边界的 token 必须拒绝。

每个文档类型的 `TemplateContractManifest` 由代码发布，至少列出：

- contract ID/版本、允许的 token ID、每个 token 的 `text`/`rich_text`/`image` kind；
- 必填 token、单次/可重复 occurrence policy、允许的 OOXML 部件和结构锚点；
- renderer/parser 版本及中文字体、图片尺寸、差异标色、指标/分页等现有 exporter 约束引用。

中心只验证 token/结构和 payload 类型，不解释业务字段，不提供循环/条件/脚本。当前五个模板大多是固定表格
标签和结构位置而非通用 token；它们以 `legacy_structural_v1` contract 注册，由对应 adapter 负责结构锚点，不能
借机把业务字段或周/月字段写入模板中心。未来新模板应逐步迁移到 token manifest，迁移本身需独立 RED。

### 3.6 权限投影与租户边界

模板中心不复制或发明 Issue #55 的角色矩阵。它只依赖一个受信的
`TemplatePermissionPolicyPort`：

```text
project(current_trusted_session, document_type) -> TemplatePermissionProjection
authorize(current_trusted_session, action, document_type, tenant_id) -> PermissionDecision
```

policy port 必须在每个有副作用或跨 await 的入口重新验证 active 用户、tenant、session/jti 和当前角色；不得
信任页面捕获的旧 role，也不得由请求参数指定 actor/tenant。中心按 policy 返回的 capability 集合过滤投影，
而不是把完整 User/ORM/Repository 传给 UI。

`TemplatePermissionProjection` 只含当前 tenant、文档类型、可见的版本摘要、active 摘要和关闭的 capability
枚举；不得含其他租户版本、教师/幼儿正文、blob/path、密钥、数据库对象或原始 policy。未得到明确 decision 的
action 默认拒绝；`restore`、全局 seed、删除物理 blob 等运维能力不得因为 `sys_admin` 字符串出现在 payload
中就自动放行。

Issue #55 必须先冻结三类角色的跨教师读取、审核、导出和删除矩阵，并把该矩阵的版本 ID 作为 policy port
输入/证据；本 spec 的测试只证明“授权由窄 policy projection 决定、越权 fail closed、无跨租户泄漏”，不把
矩阵未决项偷偷变成模板中心 GREEN。

### 3.7 激活、停用与回滚

公开服务 seam 固定为以下行为（具体 DTO 字段按本 spec 关闭）：

```text
TemplateCenter.project(actor, document_type?) -> TemplatePermissionProjection
TemplateCenter.upload(actor, *, document_type, filename, content_type, content) -> TemplateVersionRef
TemplateCenter.activate(actor, *, document_type, version_id,
                        expected_registry_revision, expected_active_version_id) -> TransitionReceipt
TemplateCenter.deactivate(actor, *, document_type, expected_registry_revision,
                          expected_active_version_id) -> TransitionReceipt
TemplateCenter.rollback(actor, *, document_type, target_version_id,
                         expected_registry_revision, expected_active_version_id) -> TransitionReceipt
TemplateCenter.preview(actor, *, document_type, version_id, synthetic_case) -> TemplatePreviewReceipt
TemplateCenter.resolve_active(actor, *, document_type) -> TemplateExportBinding
TemplateCenter.create_backup(actor, *, destination_handle, protected_image, now) -> BackupAttestation
TemplateCenter.restore_backup(actor, *, artifact_handle, target_handle) -> RestoreReceipt
```

构造 service 时只注入 `version_store`（读端）、`transaction_port`（§3.3 staged 写端）、`blob_store`、policy、contract
registry、export、backup 和 clock；不存在绕过 unit of work 的独立 `audit_sink` 或版本 `append/update/delete` port。

这些入口不能接收开放 `**kwargs`、原始 ORM、SQLAlchemy session、任意路径、业务正文或可编辑版本 DTO。
所有写入均通过 §3.3 的 `TemplateUnitOfWorkPort`：先重读 tenant/actor/registry，复核 version validation
证据、hash/contract，再把 version（上传时）、pointer transition 和完整 audit event stage 到同一 unit of work，
最后一次 `commit()`；过期、绑定错误、权限变化、版本不存在/不属于 tenant、契约失效或并发 stale 均在指针写入
前拒绝。commit 前任何对象都不可见；已知失败不留下部分 version、transition 或假 audit。

上传 candidate 的短暂校验过程是 `uploaded → validated`；active pointer 是独立的 `null ↔ validated version` 追加
transition，不是版本状态机。不得让 UI 直接设置 `active`、`inactive` 或 `approved` 等字符串绕过
transition。一个已验证版本可以反复成为 active；停用只清空 pointer，不删除、更新或终结该版本。
没有 active 版本时 `resolve_active` 明确失败；禁止调用现有 exporter 的 from-scratch fallback 作为正式模板
结果。如何兼容现有 exporter 的 fallback 属于每类接线 GREEN 的独立验收，不在本 RED 中偷偷改写现有行为。

### 3.8 合成预览

`SyntheticPreviewCase` 必须是不可变、带 `provenance="synthetic"` 的最小 payload；其内容只能来自 contract
测试夹具或调用方明确标记的合成值。中心不得从业务 repository、真实教师/幼儿记录、历史导出或 AI provider 读取
预览数据。

预览流程：

1. 重新授权并读取指定 tenant 内的已验证版本；
2. 以版本 hash、contract ID/版本和合成 case 调用窄 `TemplateExportPort.render`；
3. 通过 `parse` 检查输出为合法、无宏/外部关系、无未解析必填 token 的 DOCX；
4. 返回 bytes 的短命 receipt、版本 ID/hash、结构/解析摘要和 `persisted=False`。如实现需要临时文件，只能使用
   受控 owner-only 目录，完成读取后立即删除，且不得把该文件路径暴露给调用方。

receipt 不写 `ExportRecord`、exports、业务表、preview 表、版本、active 指针或长期缓存；不得把合成 case 原文、
导出正文、图片或异常正文写日志/审计，也不得为 preview 追加模板管理审计事件。预览与正式导出使用同一版本 hash，但预览不得替代 Microsoft Word/
LibreOffice 的人工分页/中文/图片验收。

### 3.9 审计

`TemplateAuditPort` 是独立的 append-only sink，但 service 不直接调用 append；事件只能经
`TemplateUnitOfWork.stage_audit(event)` 随同对应写入提交。上传、激活、停用、回滚、备份、恢复及安全拒绝至少记录
固定 action/outcome code、tenant/user、session hash、document type、version IDs/hashes、
contract ID/版本、registry revision、UTC 时间和审计 schema 版本。`action` 使用上述闭合动作名，`outcome` 至少
区分 `accepted`、`denied`、`rejected`、`stale` 和 `failed`；每个 service-level 尝试最多追加一条完整事件。

审计严禁保存：原始 jti、JWT、密码、Key/endpoint、绝对路径、blob bytes、文件正文、placeholder 值、合成数据、
真实教学/幼儿正文、原始异常/SQL/HTTP。写 audit 失败必须使对应生命周期操作失败并保持业务状态/active 指针
不变；validator 自身保持纯函数，因此在 validator 层没有拒绝审计；service 层只能追加一条完整且脱敏的拒绝
事件。预览不追加模板管理审计事件。审计自身不能被 ORM 或 SQL UPDATE/DELETE，物理清理只由另一个已批准保留
策略治理。审计只有在包含它的 unit of work 成功 commit 后才可见。

### 3.10 备份与恢复

模板备份必须与 R5-R 的受控备份边界一致：受信运维配置显式提供 destination handle，由实现解析到位于仓库、
源码、数据库和运行时 `exports` 外的备份根目录；页面和普通业务调用方不能传入原始路径。根目录和运行目录 `0700`，
artifact/evidence 为当前 owner 的非 symlink 普通文件、POSIX `0600`。
不得备份 `.~lock.*`、临时文件、WAL/journal、孤儿 blob 或未知 ZIP 成员。

窄 `TemplateBackupPort` 固定为（所有 destination/artifact/target 均为受信运维配置产生的 opaque handle，不是
页面传入的路径字符串）：

```text
create_template_backup(snapshot, destination_handle, *, protected_image, now) -> BackupAttestation
restore_template_backup(artifact_handle, target_handle, *, expected_tenant_id) -> RestoreReceipt
```

生产者不能接受调用方提供的 `status=verified`、hash、active 指针或 checks；这些只能从实际 snapshot、blob 和
隔离恢复结果计算。manifest v1 至少包含 schema version、tenant/document type、每个不可变版本的 ID、版本号、
contract ID/版本、blob 相对成员、字节数和 SHA-256、active pointer/registry revision、artifact hash/size、
protected image 与 UTC 生命周期；不得含 secret、正文、绝对路径、数据库 URL 或原始 session。

恢复必须先解包到全新隔离 staging，拒绝 symlink、路径穿越、未知成员、hash/size/contract/tenant 不匹配、active
指针缺失、宏/外部关系或权限不安全；全部验证通过后以一次受控提交替换目标模板状态。任一步失败都不改源库、
目标 active 指针、版本库或审计，不执行删除/回滚源数据。恢复后必须重新计算 manifest，并把结果绑定到恢复的
版本 hash；不允许把备份当作新的上传者输入绕过权限或 contract。

### 3.11 导出解析端口

现有 exporter 的业务 service 不得直接读文件或动态选择模板；一期和所有正式导出只依赖同一个
`TemplateExportPort` 的 `resolve_active`、`render`、`parse` 三个方法：

```text
TemplateExportPort.resolve_active(tenant_id, document_type) -> TemplateExportBinding
TemplateExportPort.render(binding, payload) -> RenderedTemplate
TemplateExportPort.parse(binding, rendered_bytes) -> ExportParseReport
```

`TemplateExportBinding` 是唯一的 opaque binding 类型。对正式导出，`resolve_active` 是唯一解析入口，必须绑定
tenant、document type、version ID、version number、content SHA-256、contract ID/版本；它只返回该 opaque binding，
绝不返回 blob bytes、文件路径、下载 URL、ORM 或可编辑 payload。正式 service 不提供 `resolve_for_export`、
`get_template_bytes`、`get_template_path`、fallback binding 或第二套 resolver。正式 `render`/`parse` 只接受本 port
的 `resolve_active` 产生的 binding；T011 候选 job 只能使用 §3.12 内部 qualification context 产生的 candidate-kind
binding，页面/业务层不得自行拼装 binding。render 的 bytes 只在受控导出/预览/候选资格流水线内部流转，不能由
`resolve_active` 或 UI 投影泄露。
`RenderedTemplate` 必须带同一 binding 的版本证据；`ExportParseReport` 只含合法 DOCX、部件/结构摘要、解析 token
状态、宏/外部关系检查和 hash，不含业务正文。

正式的 `resolve_active`/render/parse 都必须使用已授权的 tenant scope；binding 失效、active 变更、hash 不符、
payload 类型错误、未知 token、未解析必填 token、生成的 DOCX 非法或 parser 异常均 fail closed。中心不提供
`fallback_template`、“从零构建正式文档”、路径参数或重试另一个版本的能力。每份正式导出由后续业务接线记录实际
version ID/hash；
统一文档中心需要另行 spec。

### 3.12 周/月 reserved candidate qualification（T011 内部窄 seam）

周视角/每周活动计划和月视角/月主题活动计划在 T011 前仍是 global known-but-disabled 的 candidate，不能通过
一期的 `TemplateCenter` CRUD 或正式导出端口。它们的候选资格验证只能由受控 seed/fixture qualification job 触发，
不是面向教师或业务 API 的新入口：

```text
TemplateCandidateQualificationJob.qualify(
    document_type: weekly_activity_plan | monthly_theme_activity_plan,
    seed_handle: ControlledSeedHandle,
    fixture: SyntheticQualificationFixture,
    profile_id: closed candidate profile,
) -> CandidateQualificationEvidence
```

当前受控 v2 发布物固定为：weekly handle `controlled-weekplan-seed-v2`、profile
`weekly_activity_plan-profile-v2`（3×9×7 表结构、SHA-256
`157abf313206d94a90337807e490e0ea0ad8b72cf0d3eb6d7ef0ed6a6aa93f14`）；monthly handle
`controlled-monthplan-seed-v2`、profile `monthly_theme_activity_plan-profile-v2`（1×8×4 表结构、SHA-256
`de806aed3289f0a5f0019318aec63380f681dae3113383d47d03b363337b69d5`）。v1 seed/profile 与其 Office
证据已失效，不得与 v2 混用。

该 job 的构造只允许注入 `controlled_seed_store`、唯一的 `TemplateExportPort`、`office_qualification_port` 和
`qualification_evidence_store`；它没有 actor/session、policy、`TemplateCenter` 或业务 repository 依赖。`qualify` 是
唯一的内部方法，`CandidateQualificationEvidence` 的关闭字段至少为：

```text
qualification_id: UUID
document_type: reserved known key
seed_sha256: lowercase 64-hex SHA-256
profile_id: closed profile identifier
profile_version: positive int
rendered_sha256: lowercase 64-hex SHA-256
parse_report_sha256: lowercase 64-hex SHA-256
office_evidence_id: opaque evidence reference
office_client_versions: tuple of supported client identifiers
fixture_id: closed synthetic fixture identifier
checker_version: closed checker identifier
qualified_at_utc: timezone-aware UTC
qualification_status: passed | failed
```

该 job 只接受闭合的 `seed_handle`（例如受控发布物中的 weekplan/monthplan seed ID）和登记过的
`SyntheticQualificationFixture(provenance="synthetic")`；不接受用户路径、URL、任意 bytes、业务 repository、真实
教师/幼儿正文、页面 actor 或可编辑 payload。它先对 seed 做相同的字节/MIME/ZIP/XML/结构安全检查，再在内存中
创建一个仅供内部 job 使用的 opaque `TemplateExportBinding`（candidate kind，无 tenant active pointer），调用唯一
`TemplateExportPort.render(binding, synthetic_payload)` 和 `TemplateExportPort.parse(binding, rendered_bytes)`；不得
调用 `TemplateExportPort.resolve_active`，不得调用 `TemplateCenter.preview`。

资格门按顺序短路，不能把受控登记当作安全信任边界：

1. 闭合 document type、seed handle、synthetic fixture 和 candidate profile 的前置检查失败时，不读取 seed、不调用
   安全 validator、render/parse 或 Office port；这类拒绝不得留下任何资格 evidence。
2. 已登记 seed 读取后，必须复用 T004 的同一个纯字节/MIME/ZIP/XML/结构/profile validator。宏、ActiveX/OLE、外部
   relationship、坏 ZIP/CRC、截断包、未知部件、结构锚点或 profile mismatch 均在 render 前拒绝；不得为了候选资格
   放宽安全规则或改用第二套 validator，也不得写入 `qualification_status=passed` evidence。
3. 只有安全/profile 阶段通过后才可做 synthetic render/parse；render/parse 失败、输出 hash/结构不一致或解析报告不
   完整时拒绝，不调用 Office qualification。无论失败发生在哪一阶段，都不创建 active/version/ExportRecord 或正式
   下载物，不触发 registry enablement。
4. Office 结果只有同时满足 `status=passed`、非空 opaque `evidence_id`，以及 profile 要求的两项精确目标客户端版本/
   build 才能通过：一项 Microsoft Word（`16.0.xxxxx.xxxxx` build）和一项 LibreOffice（`24.2` 或更高的精确版本/
   build）。缺 Word、缺 LibreOffice、只有 family 无精确版本、缺 evidence ID 或 `status=failed` 均 fail closed；不得
   追加 `qualification_status=passed`，也不得启用 reserved 类型。失败 evidence 若被记录只能是不可变 `failed` 结果，
   且不含 seed/rendered bytes、路径、业务正文或客户端原始输出。

资格结果只生成/保存不可变的 `CandidateQualificationEvidence`，至少含 qualification ID、reserved document type、
seed SHA-256、profile ID/版本、rendered/parse 结构 hash、Office/LibreOffice qualification evidence ID 与客户端
版本、fixture ID、checker 版本和 UTC 时间；不含 rendered bytes、seed bytes、路径、URL、业务正文或 active/version
记录。内部 job 不创建 TemplateVersion、active pointer、正式 audit/ExportRecord、正式下载物，也不读写业务数据；
它没有 public `project`/`upload`/`preview`/`resolve_active`/CRUD 方法。资格 evidence 不是 `TemplatePreviewReceipt`，
不返回 preview bytes 或 `persisted` 标志，不能替代正式 Preview 或 Office 人工门。

只有在两个独立周/月业务 spec 的数据模型/导出契约、稳定 RED、Review、候选 synthetic render/parse、结构 profile
和 Word/LibreOffice evidence 均通过后，治理迁移才可以把对应两项从 reserved 改为 enabled；该变更发布新的 registry/
contract 版本，且首次正式导入仍须走普通五类之外另行批准的 seed/version 流程。candidate qualification evidence 本身
不会自动启用类型，不能成为通用 CRUD、模板下载、active 查询或业务导出能力。

## 4. 验收标准

### 4.1 关闭能力面

- global known registry 恰好七类；phase1 enabled registry 恰好五类。周/月两个 known-but-disabled 类型在一期的
  upload/activate/resolve/project 均拒绝；未知、任意 alias 和 WRITE/动态发现也拒绝。后续启用七类必须经过各自
  周/月 spec、稳定 RED、Review 和独立 GREEN 门。
- 所有 DTO/receipt/projection 关闭额外字段、不可变；`repr`/异常/日志不含 blob、正文、绝对路径、secret 或原始
  session。
- 公共 service 只依赖列明的 policy/blob/version/transaction/backup/export ports，不接受 ORM/session/UI Widget。

### 4.2 上传安全与占位符

- 合法 synthetic/minimal `.docx` 可得到 hash/size/contract/validation 绑定的候选版本；每次授权 upload（包括同
  内容重复上传）都有新的 version ID/编号，同内容只保留一个 blob，version number 仍按类型单调。
- 非 `.docx`、路径穿越、恶意 ZIP、宏/ActiveX/OLE、外部关系、压缩炸弹、坏 XML、未知/缺失 token、结构不匹配
  均在任何持久化前失败；纯 validator 本身不产生副作用。
- 失败后 blob、版本、active 指针与操作前完全一致；service 对到达 service 的拒绝动作恰好追加一条不含敏感数据的
  完整审计事件（审计 sink 本身失败时不产生事件），不得留下半成品审计。

### 4.3 生命周期与并发

- 激活只允许当前 contract/profile 仍有效的 `validated` version；成功恰好一次 CAS、恰好一个 transition audit，
  active 唯一；stale/越权/跨租户在写入前失败且指针不变。
- 停用使正式 resolve 明确失败但不删除、更新或终结版本/blob；同一 validated version 可在停用后再次 active，回滚
  只能指向同租户的已验证旧版本，不改变任何版本内容、validation 证据或版本号；重复点击/并发 transition 不能
  产生双 active/双 event。
- version、pointer transition 和 audit event 通过同一 staged unit of work 原子提交；audit stage/commit 失败时，
  本次 version/transition/active/audit 均不可见。

### 4.4 预览、审计、备份和导出

- preview 必须是 synthetic provenance，返回版本证据与 `persisted=False`；数据库、业务正文、exports、
  `ExportRecord`、preview/audit/version/active 状态无变化。
- 审计 action/outcome/actor scope/版本 hash 可审计，且不保存 secret、正文、路径、原始 session 或异常。
- backup→isolated restore→manifest verify 全部通过才提交；篡改、未知成员、权限/路径/hash/tenant 不匹配全都
  fail closed 且源/目标状态不部分改变。
- `resolve_active/render/parse` 始终返回同一 version ID/hash；没有 active、contract 不兼容或输出含未解析 token/
  宏/外链时不得 fallback。
- T011 candidate qualification 只能使用受控 weekplan/monthplan seed 与 synthetic fixture，通过同一 opaque
  `TemplateExportPort.render/parse` 产生 hash/profile/Office evidence；已登记但不安全/损坏/结构或 profile 不匹配的
  seed 必须在安全阶段拒绝，Office failed/缺 Word/缺 LibreOffice/缺 evidence ID/缺精确版本也必须在 Office 阶段拒绝。
  这些失败不产生 passed evidence 或 enablement；候选 job 不产生 active/version/public projection/upload/preview/
  resolve_active/正式下载，且 evidence 未同时满足周/月独立业务门时不得启用 reserved 类型。

### 4.5 一期非目标的自动证明

- RED/GREEN 不能创建周/月业务表、字段、页面、导出器或迁移；首期 registry 不能对两个 disabled 类型 upload、
  activate、resolve 或 project。
- RED/GREEN 不能改变现有五类 exporter 的业务字段行为；五类真正接线和 Word/LibreOffice 人工验收是后续独立
  门，结果必须绑定实际 template version/hash。
- RED/GREEN 不能实现统一文档中心、审核流、跨教师业务读取或 Agent 能力。

## 5. 门禁与稳定 RED

稳定 RED 只放在 `specs/template-center/tests/`；正式模板测试只穿过本 spec §3.3、§3.7–§3.11 的公开 seam，T011 测试
只穿过 §3.12 的内部窄 seam。测试不读取私有字段、
不读用户真实模板/凭据、不使用真实网络、固定长 sleep、skip/xfail 或源码文本匹配。测试使用确定性内存 port、
合成 OOXML 字节和事件协调；不会修改 `templates/` 或常规 `tests/`。

RED 需要满足：

1. `--collect-only` 成功，无 collection error。
2. 连续两次执行得到完全相同的 collected/passed/failed 与失败 node ID；失败只能归因于缺失
   `app.service.template_center` 正式 seam 或该 seam 尚未满足本规格。
3. 现有常规测试和 Agent Foundation/WRITE 测试不被本目录测试改写或依赖；本期只运行本目录 pytest 作为交付
   证据，完整回归留给 main 在合并前独立执行。
4. 固定 RED 后才可进入最小 GREEN；GREEN 后每个 Review finding 先添加独立稳定 RED，再修正并重跑完整矩阵。

建议 RED 矩阵：

| 文件 | 公开行为 |
|---|---|
| `test_template_center_registry_red.py` | global known 七类、phase1 enabled 五类、disabled 周/月拒绝、不可变版本摘要、policy projection、tenant scope |
| `test_template_center_upload_red.py` | DOCX/ZIP/XML/宏/外链/路径/压缩炸弹/占位符校验、原子失败和 hash/size 证据 |
| `test_template_center_lifecycle_red.py` | validation/active pointer 分离、validated 重复 active、CAS/stale/并发/跨租户拒绝、唯一 active、审计与 blob 不删除 |
| `test_template_center_preview_export_red.py` | synthetic-only preview、零持久化、resolve/render/parse 版本证据、无 active 不 fallback |
| `test_template_center_backup_red.py` | 受控 manifest、隔离恢复、篡改/未知成员/权限/路径/tenant/hash 失败关闭和原子性 |
| `test_template_center_candidate_qualification_red.py` | T011 受控周/月 seed/fixture、同一 opaque export port 的 synthetic render/parse、profile/hash/Office evidence、无 public CRUD/active/正式 Preview |

## 6. 最小 GREEN 顺序

在权限矩阵 ADR、模板契约 ADR、稳定 RED Review 通过并得到明确授权后，只按以下顺序实现：

1. **T001：权限矩阵治理门** —— 接受 Issue #55 的角色、跨教师读取、审核、导出、删除和模板管理边界；没有
   policy version 不实现模板权限。
2. **T002：模板权威 ADR 门** —— 接受 ADR-0008（并确认与 ADR-0004/0007 的关系）；没有安全、版本、回滚和
   占位符权威来源不进入 GREEN。
3. **T003：契约与关闭 registry** —— 冻结 global known 七类、phase1 enabled 五类、disabled 规则、DTO、错误码、
   legacy structural manifests 和 policy/export/clock/transaction ports；不触数据库、不接 UI。
4. **T004：纯校验器** —— 完成文件名、ZIP、OOXML、结构和 token contract 检查；用合成 bytes 验证无副作用。
5. **T005：内容寻址 blob + 不可变版本** —— 只加入必要的 schema/migration（另行审核），实现每次授权 upload 新建
   version、同 hash blob 去重、validation receipt 和 staged 原子提交；不激活、不接现有 exporter。
6. **T006：生命周期** —— 实现 validated version 与 active pointer 分离、CAS、停用、回滚和最小脱敏 audit；通过
   并发/失败回滚/重复激活测试，且不提供 record-level delete/update。
7. **T007：权限投影** —— 接入 Issue #55 冻结后的 current-session policy；完整测试 tenant/user/role/审核/导出/
   删除边界和 disabled 文档类型，不把权限判断散落在 UI。
8. **T008：合成预览与解析端口** —— 只接 synthetic case、版本证据和 parser report；preview 不写正式 exports/
   `ExportRecord`，无 active 不 fallback。
9. **T009：备份/恢复** —— 复用 R5-R 的 owner-only artifact/evidence、opaque handle 和隔离 staging；验证失败原子性、
   manifest 和保护镜像绑定。
10. **T010：五类 exporter 接线** —— 每一类单独建立 adapter/RED/GREEN/Word 验收，正式导出记录实际 template
    version/hash；不在模板中心 GREEN 中顺手改周/月业务。
11. **T011：reserved candidate qualification 与 enablement gate** —— 在周/月各自独立 spec/RED/Review 通过后，先运行
    §3.12 内部窄 seam；它只产生候选资格 evidence，不进入 TemplateCenter 的 public seam。所有 hash/profile/Office
    evidence 和人工门通过后，才发布 registry/contract v+1，将两个 reserved 类型启用。

每一步都按 `Issue/任务 → 稳定 RED → 最小 GREEN → 双轴 Review → 当前 SHA 自动验证 → 目标平台人工验收`。
任何 GREEN/Review/CI 结果都不自动授权下一步、merge、Issue 关闭或 release。
