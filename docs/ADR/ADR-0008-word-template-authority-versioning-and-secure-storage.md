# ADR-0008：Word 模板权威来源、版本化与安全存储契约

- 状态：接受（2026-09-02；双轴 Review Standards 0 / Spec 0）
- 日期：2026-09-02
- 关联：Issue #55；[ADR-0004](ADR-0004-ai-and-fixed-word-boundaries.md)

## 背景

当前 Word 导出器位于 `app/integration/word_export/`，按源码中的固定路径读取
`templates/` 下的五套 DOCX，然后用 `python-docx` 填充单元格。部分导出器在模板缺失时会
从零构建简化文档，当前测试也把这种降级路径作为可打开性测试；这能维持旧功能可用，但不能
证明输出仍符合正式模板。`ExportRecord` 目前只保存租户、用户、业务关联、文件名和路径，尚未
记录逻辑文档类型、模板版本、模板 hash、输出大小或输出 hash。

现有导出测试已经固定了一些保真要求：每日计划是 19 行模板表格，活动过程差异改写部分用红字，
中文 run 设置宋体和 `w:eastAsia`；游戏观察要求图片数量和表格字段；一对一倾听要求五个领域、
日期、指标星级、评价和支持策略的位置；自制教玩具和课程审议要求固定行列映射、示例内容清理和
原稿/二次修改段落。`tests/test_backup_restore.py` 与 `app/jobs/backup_restore.py` 还已经把
数据库、五个固定模板、exports、owner-only 权限、清单 hash、锁文件/缓存排除、隔离恢复和 ZIP
路径遍历拒绝作为 R5-R 的安全基线。该备份基线不自动覆盖未来的模板中心版本对象。

本工作树另有两个供 Issue #55 后续业务切片使用的未跟踪种子文件：

- `templates/weekplan.docx`：读取到 2 个表格，每个表格为 9 行 × 7 个逻辑列；正文有标题、元数据和
  两周的样例主题、班级、教师与活动内容；没有显式机器占位符。
- `templates/monthplan.docx`：读取到 1 个 8 行 × 4 个逻辑列的表格；正文有标题和班级、执行年月、
  带班/保育老师样例；没有显式机器占位符。

两份文件均只读检查，当前没有把它们登记为运行时模板，也不能由样例正文推导业务数据模型。
若以后把它们纳入中心，必须以本 ADR 的闭合结构映射/占位符契约重新校验；不能把样例内容当作
占位符或正式业务事实。

产品方向要求模板中心、周/月业务模型和导出契约拆成独立切片。该 ADR 只冻结模板基础设施的
权威、安全、版本和验证边界；周/月字段、聚合关系和用户验收场景由独立 spec 冻结。模板中心
第一期在本 ADR 与稳定 RED Review 通过前不得进入 GREEN。

## 决策

### 1. 逻辑文档类型和权威来源

逻辑类型注册表是全局闭合且版本化的，永远只认识下面七个 `document_type`。这里的“认识”不等于
当前可以上传或导出：阶段能力集合另行冻结，不能由文件名、请求参数或上传内容动态发现新类型。

| `document_type` | 发布种子/候选文件 | 全局注册状态 |
|---|---|---|
| `daily_plan` | `templates/teacherplan.docx` | phase-1 enabled |
| `game_observation` | `templates/ObservationRecord.docx` | phase-1 enabled |
| `one_on_one_listening` | `templates/OneOnOneListeningSmallSecond.docx` | phase-1 enabled |
| `homemade_teaching` | `templates/homemadeteaching.docx` | phase-1 enabled |
| `course_review_activity` | `templates/coursereviewactivity.docx` | phase-1 enabled |
| `weekly_activity_plan` | `templates/weekplan.docx` | global known；phase-1 reserved |
| `monthly_theme_activity_plan` | `templates/monthplan.docx` | global known；phase-1 reserved |

集合含义是硬契约：global known 始终为七个；模板中心第一期 phase-1 enabled **恰好为前五个**；
只有周/月两个独立业务 spec 的数据模型、导出契约、字段映射、模板结构验收和稳定 RED 完成 Review
门后，enabled 集合才扩为七个。phase-1 的 `weekly_activity_plan`（周视角/每周活动计划）和
`monthly_theme_activity_plan`（月视角/月主题活动计划）是保留键，不是可用能力：在该门之前，上传、
激活、停用、回滚、预览、解析投影、resolve 和导出绑定均必须以稳定错误码拒绝；它们不得出现在
`descriptors()`、active 查询、phase-1 seed/profile 或备份白名单中。周/月种子文件可以留在源码树供
只读审阅，但不得被模板中心导入、解析或作为导出 fallback。

权威分两层，且不得混用：

1. **发布种子权威**：版本化发布物中的 `templates/` 文件是 phase-1 五类初始导入的只读输入。
   导入时按原始字节计算 SHA-256、大小和结构签名；导入过程不得改写仓库种子，也不得把源码路径
   直接暴露给调用方。`weekplan.docx` 和 `monthplan.docx` 在周/月业务 spec、映射清理和人工验收
   完成前只是候选文件，不属于 phase-1 seed。
2. **运行时权威**：模板中心中的租户级、不可变 `TemplateVersion` 对象及其 active 指针是
   导出时唯一权威。运行中的 exporter 不再按用户提供的绝对路径、文件名、URL 或仓库路径读取
   模板；必须通过 `tenant_id + document_type + active template_version_id` 解析受控对象。

phase-1 每个租户独立持有五类模板的版本和 active 指针。系统种子只能复制为租户的第一个版本，
不能让一个租户直接读取或激活另一个租户的版本。周/月门通过后，七类仍分别按租户隔离；未来若需要
全局基线或租户覆盖，必须增加明确的继承/覆盖 ADR；本 ADR 不允许隐含的跨租户 fallback。

### 2. 版本对象、激活和回滚

每个 `(tenant_id, document_type)` 的版本号从正整数开始单调递增，永不复用。版本对象至少绑定：

- `tenant_id`、闭合 `document_type`、正整数 `version`；
- 受控存储对象引用（相对 object key，不是调用方给出的路径）；
- 原始 DOCX 字节的 `size_bytes`、`sha256`、固定 MIME、扩展名；
- 模板契约/结构映射版本、内容校验状态、创建者和 UTC 创建时间；
- 必要的审计事件引用。

文件字节、hash、结构映射和元数据一旦写入不得原地修改。任何内容、占位符、结构、映射或安全
策略变化都必须创建新版本。每次经授权且通过校验的上传，即使原始字节的 SHA-256 与已有版本
相同，也必须为该 `(tenant_id, document_type)` 分配下一个单调版本号并追加一条新的不可变版本
元数据；blob 存储按 SHA-256 `put_if_absent` 做内容寻址去重，因此相同 hash 的多个版本可以
共享同一个不可变 blob。重复 hash 不是幂等 no-op，也不能覆盖已有版本。
物理 blob 即使在存储层按 hash 被跨租户复用，也只能通过带租户边界的版本引用读取；去重不得暴露
blob、版本元数据或任何下载句柄给另一个租户。

内容校验状态和 active pointer 是两个独立概念，不能合并成一个生命周期字段：

| 概念 | 记录方式 | 语义 |
|---|---|---|
| `content_validation_state` | 版本元数据中的不可变校验结果 | 上传候选先处于未发布的 `unvalidated`；安全、结构和契约检查通过后才可追加为 `validated` 版本；拒绝输入不产生可寻址版本。后续发现完整性/安全问题只能追加 `revoked`/`quarantined` 事件，不能修改原始 bytes 或 hash。 |
| active pointer | `(tenant_id, document_type)` 的 append-only registry state | `active_version_id` 或 null；每个租户/类型最多一个指针。它不是版本字段，版本可以在没有指针时仍保持 validated。 |
| 选择性事件投影 | registry 的追加事件/派生视图 | `retired` 表示曾被选中但当前不再被指向；`disabled` 表示不参加默认候选选择。二者都不删除、不过期也不否定内容校验，**单独不能阻止合法回滚**；只有目标仍属同一租户/类型、仍为 validated 且重新验证 hash/存储/当前契约通过，授权回滚才可将 pointer 指回它。`revoked`/`quarantined` 才是阻止激活和回滚的内容安全状态。 |

`validated` 版本可以被授权人多次激活；每次激活都是新的 CAS 事件，不改变版本元数据。激活、停用
和回滚必须在短事务（或提供同等原子保证的受控 port）中完成：重新读取 actor、租户/类型、当前
registry revision、期望的 active ID、目标版本的 hash 和契约，然后 CAS 更新 pointer 并追加审计；
pointer 只有在该次受控提交完整成功后才可见。停用只是清空 pointer，使 resolve 返回
`template_not_active`，不删除版本/blob；回滚只是把 pointer 指向通过当前检查的历史 validated
版本。并发或过期 revision 必须拒绝且不改变现有 pointer，不能静默丢失更新。

上传的受控原子流程固定为：`validate（纯函数、无副作用）→ blob put_if_absent → append version
metadata → append audit`，且上传不会自动激活。校验开始前不得创建可寻址 version、blob 或 active
pointer；校验拒绝时至多追加一条脱敏拒绝审计，不能留下 version/blob/pointer。若 blob 写入、版本
元数据或审计提交的后续步骤失败，则该次版本对读取端不可见，active/pointer 保持原状；已经写入
且无引用的 deduplicated blob 只能由独立的 orphan cleaner 后续回收，调用方不得删除或复用它来
伪造版本。激活/停用/回滚同样要求 pointer、状态事件和审计在一个受控提交中一起成功，审计失败
即整次状态转换失败且不暴露半成品。

回滚不是删除或修改历史文件，而是将一个仍满足当前契约的既有不可变版本重新设为 active，并
产生新的激活事件。active、曾用于导出的版本以及仍可能用于回滚的版本不得硬删除；停用或保留
期策略若要物理清理，必须先证明无 active/导出/备份引用并单独记录。契约校验器升级后，旧版本
若不再通过当前安全/结构校验，回滚应 fail closed，而不是自动修复或自动转换。

模板管理的上传、校验、预览、激活、停用、回滚、保留和下载均必须在可信 UI 会话中进行，并
以 `(tenant_id, user_id)` 重新读取 active 用户。具体 `teacher`、`teaching_admin`、`sys_admin`
动作矩阵以 Issue #55 接受后的权限决策为唯一授权来源；本 ADR 不扩大该矩阵，也不允许模板中心
绕过它。所有成功和拒绝的管理动作都记录脱敏审计事件。

### 3. 安全存储、路径和输入大小

模板版本、临时上传、预览产物、导出文件和备份恢复都使用应用受控的数据根（遵守 ADR-0003
的源码/打包模式和 `KINDERGARTEN_DATA_DIR` 规则），不以仓库 `templates/` 作为运行时写目录。
示意 object key 为 `templates/<tenant-id>/<document-type>/<version>/template.docx`；调用方
只能得到受控 ID 或下载句柄，不能指定最终路径。

实现必须满足以下不变量：

- 路径组件由闭合枚举/正整数生成；拒绝绝对路径、Windows 驱动器或 UNC 路径、反斜杠、`..`、
  空组件、控制字符、NUL、冒号和路径规范化前后不一致的值。所有祖先目录拒绝 symlink 和不可信
  可写祖先；模板对象只能是 regular file。
- POSIX 目录使用 `0700`、文件使用 `0600`，并检查当前所有者；临时文件在同一受控目录创建，
  写入后 `fsync`，再通过原子 rename/replace 发布。staging 中的临时上传、未完成的版本元数据和
  pointer 事务不可被读取端看见；事务失败时清理临时文件和半成品，不改变 active 指针。若此前的
  `put_if_absent` 已留下无引用 blob，不在失败路径由调用方删除，而由独立 orphan cleaner 回收。
  Windows 也必须保持等价的应用访问控制与原子发布语义。
- 单个上传 DOCX 原始字节最多 16 MiB；DOCX ZIP 最多 256 个成员，单成员最多 16 MiB，所有
  解压后的成员合计最多 64 MiB，并设置压缩比/读取时间/CPU 限制以拒绝 zip bomb。限制应在内存
  读取和临时落盘前后都执行，不能只相信请求头。
- 只接受扩展名 `.docx` 与精确 MIME
  `application/vnd.openxmlformats-officedocument.wordprocessingml.document`。MIME 头不可信，
  必须同时检查 ZIP `PK` 签名、`[Content_Types].xml` 和必需的 OOXML 关系；`.docm`、宏模板和
  任意 ZIP 一律拒绝。
- ZIP 成员必须是规范化相对 POSIX 路径；拒绝重复成员、目录伪装、symlink/非 regular 属性、
  加密成员、CRC/大小不一致和未知的可执行/活动部件。流式读取时重新计算每个成员大小与 SHA-256，
  不把整个未压缩包无界载入内存。
- 解析 XML 时禁用 DTD、外部实体、实体替换、外部 schema、XInclude 和网络访问；拒绝 malformed
  XML、超出 part 限制的 XML、`altChunk`、外部数据连接、宏、`vbaProject.bin`、ActiveX、OLE、
  `embeddings`、`customUI` 等可执行或外部活动部件。`weekplan.docx` 中存在的 `customXml`
  只有在关系内部、路径安全、大小受限且不含外部目标时才能保留；不能因“能被 python-docx
  打开”就放宽包级安全校验。
- 扫描全部 `.rels` 关系，拒绝 `TargetMode="External"` 以及 HTTP(S)、`file:`、UNC、驱动器
  路径或其他绝对目标；不允许模板在打开或预览时联网、加载外部图片/模板或执行脚本。缺少、损坏
  或无法安全解析的关系 fail closed。
- 模板字节、上传正文、幼儿/教师正文、图片和异常正文不得写入日志、错误响应、审计或备份证据
  JSON。日志只保留文档类型、版本、大小、hash、受控错误码和操作者范围。

### 4. 占位符、重复和表格结构契约

模板中心使用版本化、闭合的字段注册表。显式占位符的规范形式为
`{{kg.<document_type>.<field>}}`，其中 `document_type` 和 `field` 只能来自对应契约版本的
ASCII 小写闭合白名单；注册表同时声明字段类型、格式化方式、是否必填、基数
（`single`/`repeatable`）和允许出现的文档区域。注册表由对应业务 spec 和模板中心版本共同引用，
运行时不接受任意字段名、表达式、函数、条件或用户自定义模板语法。

占位符扫描按 OOXML 文本顺序处理：同一段落内相邻的 `w:t`/run 边界只是排版边界，完整 token
可以跨 run；token 不得跨段落、表格单元格、表格、文档 part 或不受支持的文本框/绘图边界。表头、
页脚等区域只有在该文档类型注册表明确声明并有独立测试时才可使用。跨 table 的 token、未闭合
token、损坏 token、未知 token、未知字段或不匹配的字段类型都必须在激活前拒绝，不能原样带到
正式导出中。

字段出现规则如下：

- `required + single` 必须在注册的结构位置出现且恰好一次；缺失、重复、空值或类型不合法均使
  激活/导出失败。
- `optional + single` 可不出现；出现时仍必须是白名单字段且按类型校验。导出时缺失可按业务 spec
  的明确空值表现输出，不得把缺失字段静默改成其他字段。
- `repeatable` 只有在注册表明确允许时才可重复；每一处都按确定的同一字段规则替换，顺序和
  空值语义由业务 spec 冻结。首期不支持隐式列表循环、任意复制行或按文本猜测重复区域；需要
  重复表格行必须登记显式 block/region 结构并加入新的 RED。
- 注册表中的必填字段不等于业务输入必定有值。导出前仍须对当前租户、当前业务快照做必填校验，
  缺值直接 fail closed，不以样例正文、旧记录或另一个租户的数据补值。

模板的结构映射也是不可变白名单。激活前必须验证文档 part、表格数量、表格顺序、行列数、合并
单元格签名、锚点位置、段落/区域类型以及每个字段允许的 cell/paragraph；增加、删除、重排或
不匹配的结构都拒绝，不能让 exporter 继续使用“第一个表格/第 N 行”猜测。既有五类模板可以在
迁移期间使用其已测试的固定映射；其映射必须被登记为闭合 profile，而不是继续依赖源码路径。

由于当前 `weekplan.docx` 和 `monthplan.docx` 是已填样例且没有显式 token，phase-1 对它们采取
硬拒绝：不上传、不激活、不预览、不解析投影、不 resolve、不导出绑定。它们的两个 9×7/一个
8×4 表格观察结果只作为待审阅事实，不能被当作结构 profile、占位符或周/月领域模型。

在周/月独立业务 spec 冻结数据模型、字段/列表/日期/空值/重复区块及导出验收，并通过稳定 RED
Review 后，才可以为 `weekly_activity_plan` 和 `monthly_theme_activity_plan` 分别建立 profile。
届时每个 profile 必须选择以下受控方式之一：

1. 在不改变版式的前提下制作经过审阅的显式占位符版本；或
2. 为已批准的种子登记不可变的结构映射 profile，把固定 cell/paragraph 锚点视为逻辑占位符，
   并在导入时清理所有样例主题、班级、教师和活动正文。

第二种方式不允许对任意上传模板开放，也不允许自动推断标签。周/月 profile 通过各自的结构、
人工 Word/LibreOffice 和导出验收后，才可在新的启用门中把全局保留键加入 enabled 集合；若业务
spec 选择不同的块数量或重复策略，必须创建新结构 profile 和新的模板版本，不得隐式改变当前签名。

### 5. 预览和 Word/LibreOffice 验收

模板上传/导入必须依次通过：字节/MIME/ZIP/XML 安全检查、闭合 placeholder/profile 检查、合成
数据预览和结构解析检查。预览使用不含真实幼儿/教师敏感正文的固定 fixture，绑定候选
`tenant_id + document_type + template_version_id + sha256`；预览不能激活模板，也不能改变业务
记录、版本、审计或 `ExportRecord`。临时预览文件在受控目录中短命保存，过期或失败时删除。

每个可激活版本都必须有两类相互独立的证据：

1. **自动结构证据**：使用 `python-docx`/Open XML 检查包可解析、结构签名、必填/重复/未知占位符、
   中文字体、图片/差异/指标位置、长文本换行、空可选值、样例内容清理以及输出 hash；必要时
   运行 XML schema/关系安全检查。测试不得使用真实密钥、真实幼儿正文或真实外部链接。
2. **目标 Office 证据**：按下列冻结的支持矩阵分别打开并导出/打印；必须无修复提示、宏/外链警告
   或版式破坏，并核对中文字体、表格/合并、分页、长文本、图片尺寸/方向、每日计划活动过程红字、
   倾听指标勾选以及对应业务 spec 的具体验收项。

人工支持矩阵是本 ADR 的验收契约：

| 目标环境 | 冻结的支持族/下限 | 每次执行必须记录 |
|---|---|---|
| Windows | Windows 11 + Microsoft Word for Microsoft 365 **Current Channel**；不得以“Office 可打开”替代该目标。执行时记录精确 Word build（`16.0.xxxxx.xxxxx`）和 channel。 | Windows edition/release/build、架构、区域/语言/时区；Word product/channel/build；字体名称、版本和文件 SHA-256；打印 PDF。 |
| Linux | Linux + **LibreOffice 24.2 或更高**；执行时记录精确 LibreOffice 版本/build。 | 发行版/release、kernel、架构、区域/语言/时区；LibreOffice 精确版本/build；字体名称、版本和文件 SHA-256；打印 PDF。 |

若执行环境无法在 ADR 通过前固定一个精确 Office build，则冻结上述版本族和下限，并把执行时的精确
版本/OS/字体清单与打印 PDF 作为不可省略的证据；缺任何一项都不能宣称人工门通过。两种环境都须
执行，且结果分别判定，不能用一侧通过替代另一侧。

人工/自动证据的必填字段冻结如下（正文、幼儿/教师姓名和密钥不得进入证据）：

`evidence_schema_version`、`evidence_id`、`result`、稳定 `error_code`（失败时）、`document_type`、
`tenant_scope`、`template_version_id`、单调 `template_version`、`template_sha256`、
`template_size_bytes`、`contract_id`/`contract_version`、`profile_id`/`profile_version`、
validator/parser/renderer 的代码 SHA、合成 `fixture_id`/`fixture_sha256`、输出 DOCX 的
`output_sha256`/`output_size_bytes`、目标客户端 family/version/build/channel、OS/distro/release/
kernel/build/architecture、语言/区域/时区、字体名称/版本/文件 SHA-256、打印 PDF 的受控引用/
`pdf_sha256`/页数、执行 UTC 时间、操作者范围、附件引用，以及修复提示、外链/宏/活动部件和解析
检查结果。结果和附件引用存放在受保护的 owner-only 证据目录；只记录受控摘要，不记录模板正文。

自动结构测试、预览成功或历史模板可打开都不能替代这两个目标环境的人工门。模板字节、映射、解析器、
字体、Office/LibreOffice 版本或导出代码发生影响版式的变化时，相关证据失效，必须用新证据字段
重新运行；不允许用旧 SHA 的人工通过覆盖新版本。

### 6. 导出记录绑定

模板中心 GREEN 后，新的 `ExportRecord` 写入契约至少增加并强制填充：

- `document_type`；
- `template_version`/`template_version_id`；
- `template_sha256`；
- 输出 object key、`output_size_bytes` 和 `output_sha256`；
- 现有 tenant/user、业务关联和创建时间。

记录仍为 append-only；现有旧记录的空字段只能按明确的 legacy 读取规则处理，不能伪造模板版本或
hash。导出开始时冻结 active 版本及 hash，在整个 exporter 调用、文件原子发布和记录写入中使用同一
版本字节；读取失败、hash 不一致、active 被撤销或租户边界失配时不生成可交付文件，也不写成功
记录。批量导出必须在开始时为每个逻辑文档类型冻结版本，按文件分别记录绑定信息，不能混用
中途切换的 active 版本。

文件名可以是用户可见标签，但实际存储必须使用系统生成的受控 object key。下载、重新生成、归档
和后续文档中心查询都以记录的 tenant、业务关联、版本和 hash 为约束；绝不能仅凭 ID 或文件名
跨租户读取。

### 7. 备份、恢复和回滚

模板版本 bytes、版本元数据、active 指针、契约/profile 版本和导出记录是一个可恢复关系；不得
只备份当前 active 文件而丢弃可回滚版本。phase-1 的 R5 备份清单只允许当前启用的五类模板，清单
内容为“数据库记录 + 五类全部保留的模板版本对象 + active 映射 + exports”，并为每个对象记录大小
和 SHA-256；`weekplan.docx`/`monthplan.docx` 等周/月保留键不得进入 phase-1 备份白名单。周/月门
通过并启用七类后，清单才扩展为七类的全部版本。仓库种子只用于重新部署时的受控导入，不能替代
运行时版本备份。

备份/恢复沿用 [ADR-0007](ADR-0007-explicit-migration-and-verified-backup-gate.md) 和现有 R5-R
闭合格式：先取得一致数据库快照，再打包受控文件；manifest、文件大小和 hash 必须由 producer 从
实际文件生成，evidence JSON 不含模板/密钥/业务正文。备份目录和文件保持 owner-only；锁文件、
缓存、临时上传和不完整候选版本不得进入可恢复清单。

恢复必须在全新安全目录完成，先验证 manifest、成员规范化、大小、SHA、数据库 revision、模板
引用和 active 指针，再原子替换受控运行时目录；任何 manifest 不匹配、ZIP 加密/重复成员、路径
遍历、symlink、权限或校验失败都删除本次新建的临时目录，不改变现有运行时状态。恢复验证不能
通过人工编辑 evidence 或只比较 ZIP 外层 hash 绕过成员校验；不能因恢复模板失败而自动回退到
从零构建文档。迁移仍由显式 job 负责，备份/恢复不会重新引入启动自动迁移。

### 8. Fail-closed、ADR 关系和 Agent 非目标

以下任一情况必须阻断激活或正式导出，并返回不含敏感内容的稳定错误码：phase-1 保留的周/月类型
（`document_type_reserved_until_gate`）、缺少 active、模板对象不存在、tenant 不匹配、版本/契约/
profile 不一致、hash/大小改变、权限/路径不安全、MIME/ZIP/XML 校验失败、外链/宏/活动部件存在、
结构不匹配、未知/重复/缺失占位符、业务必填值缺失、输出写入或 Office 验收证据失效。模板缺失
或填充异常时，模板中心管理的文档类型不得使用当前旧 exporter 的 `_export_from_scratch` 简化
降级；“返回可解析 bytes”不等于正式模板成功。

本 ADR **只取代/细化 ADR-0004 中“Word exporter 复制并填充仓库固定模板、模板缺失可降级”这一
模板权威子决策**，并在本 ADR 接受后取代其运行时选择规则。ADR-0004 关于 AI 只能在
`app/integration/ai_client/`、密钥加密与短暂解密、AI 结果须经教师编辑/采用、图片/差异/字体契约
以及自动测试和真实 Word/Office 独立验收的其他决策继续有效；本 ADR 不改变 AI 或教师最终采用边界。
接受前，ADR-0004 的状态和现有 exporter 行为不因本文件自动改变。

本 ADR 不给受控 Agent 增加能力。遵守 ADR-0005/0006 的 Agent 仍不能读取模板文件、选择/上传/
激活/回滚模板、调用通用 Word 导出、写 `ExportRecord` 或通过 URL、shell、Python、SQL、MCP、
插件访问模板中心；Agent 仍保持每日计划四个 READ、两个 DRAFT 和既定的本地确认 WRITE 边界。

## 分阶段门

以下门必须按顺序分别通过，不得在一个 GREEN 中合并权限、模板基础设施和周/月业务功能：

1. **治理门**：Issue #55 接受三类角色的跨教师读取、审核、导出、删除和模板管理边界；本 ADR
   Review 通过并明确其与 ADR-0004/0007 的关系。
2. **业务契约门**：分别建立并 Review “模板中心第一期”与“周/月计划领域与导出契约”两个 spec；
   周/月 spec 先冻结数据模型、周视角/每周活动计划与月视角/月主题活动计划的验收标准、逻辑
   `document_type`、字段/列表/日期/空值和导出记录绑定，再建立各自稳定 RED。
3. **模板中心 RED 门**：在不改变业务代码的前提下，稳定测试覆盖全局七类型/phase-1 恰好五类型
   /周月保留键拒绝、租户/会话授权、版本不可变、相同 hash 的单 blob 多版本、原子激活/回滚、
   hash/大小/MIME、ZIP/XML/宏/外链/遍历/解析防护、占位符跨 run 与跨 table 边界、结构 profile、
   预览、备份恢复、失败清理和 fail-closed。连续运行应得到相同 collection 与失败分布，不能用
   skip/xfail 或模板缺失兜底制造 RED。
4. **模板中心最小 GREEN 门**：只实现模板版本存储、校验、预览、激活、回滚和安全恢复所需的
   最小 seam；只迁移/登记 phase-1 的五类模板，周/月种子保持未登记且所有相关操作继续拒绝。
   该门不实现周/月业务聚合、复杂审核流、文档中心或 Agent 能力。
5. **周/月最小 GREEN 门**：在两个独立业务 spec 的数据模型/导出验收、稳定 RED Review 和模板
   中心 GREEN 均通过后，分别为周视角/每周活动计划和月视角/月主题活动计划建立审阅过的
   profile、清理样例并单独启用两个保留键，使 enabled 集合从五个扩为七个；再分别实现最小业务
   GREEN，并让每个导出记录绑定版本和 hash。两类业务不互相代替，也不回写模板中心权限或通用
   文档中心。
6. **人工与恢复门**：按每个版本分别取得 Microsoft Word、LibreOffice、SQLite/MySQL（需要时）
   以及备份→隔离恢复→hash/active 指针对账证据。所有证据绑定当前代码 SHA；旧 SHA 或旧模板的
   人工通过不能覆盖新版本。

## 非目标

- 在线拖拽 Word 编辑器、任意 DOCX/ZIP 浏览器、宏/脚本/OLE/外链执行和自动修复/自动推断占位符。
- 从 URL、共享盘或用户路径拉取模板；使用动态字段、动态文档类型、动态 exporter 或模板中心
  作为 Agent Tool。
- 在本 ADR 中实现三类角色权限矩阵、复杂审核状态、跨园继承、多园 SaaS、家长访问、资源复用或
  统一文档中心；这些能力分别由 Issue #55 或后续 spec/ADR 冻结。
- 将周/月样例正文当作领域模型，或在没有周/月 spec 和稳定 RED 时直接接入模板中心。
- 通过删除 active/历史版本、伪造备份 evidence、改变路径权限、从零构建简化表格或放宽安全检查
  来绕过版本、回滚和 Office 验收门。

## 后果与剩余风险

正面后果是：导出可以追溯到租户、逻辑文档类型、不可变模板版本和精确字节 hash；激活/回滚不再
依赖源码路径；未知字段、危险 DOCX 部件和损坏备份在边界处被拒绝；Word/LibreOffice 保真证据
不再被“python-docx 能打开”替代；模板和导出文件可以随数据库一起恢复。

代价和风险是：需要新增模板版本/映射元数据和 Alembic 迁移、租户授权、受限 DOCX 检查器、预览
隔离和导出记录字段；版本保留会增加存储和备份体积；不同 Word/LibreOffice、字体和分页行为仍
需逐版本人工验收。当前五个 exporter 的固定路径、缺失降级和 `ExportRecord` 缺少版本/hash 是
实现前必须由稳定 RED 显式锁定的迁移债务。两个周/月种子仍无机器占位符且含样例数据，任何在
业务 spec 之前直接填充它们的实现都应视为越过本 ADR 的门禁。
