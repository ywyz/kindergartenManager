# 下一门提示词：继续 WMP-9 分阶段验收与云端准备

```text
先读取 specs/wmp9-production-prerequisites/evidence/formal-acceptance-local-20260907.md。
本轮用户授权 localhost + LibreOffice 阶段，云端与 Windows Word 延期；先完成可执行的
本地剩余矩阵，不得因延期跳过本地工作。headless PDF 不等于可见打开/警告/打印 UI PASS。
阶段记录不是 WMP-9 closure；01bf6349a7c6f5268eba4425212f546874d651b0 只是上一轮 acceptance start。

以上一门已回读的 WMP-9 production prerequisites evidence-closure 提交
`f07971d6624d7e9c032f21fe94a7415a55b0786c` 为基线。该门的 tested-code SHA 是
`72d759fc128b013c2345bd609875bb3e3d623ef1`；两者不能互相替代。

云端在线定位与文档修正的已验证基线为：
`cc3ebf89997a15d9ef4e237751c9792a236d457f`。
该 SHA 的 Quality run `34126422661` 与 CodeQL run `34126421919` 均为 success，
且 headSha 精确匹配。Quality 已通过 tests/ 与 Agent Foundation；本地 tests/ 结果为
`1163 passed, 1 skipped`。前一提交 `5f2b5db…` 的 Quality 曾因用户手册缺少显式
liveness URL 而失败；cc3ebf8 已补回 liveness/readiness 说明，没有修改该失败测试。
这些结果仅证明基线的自动检查通过，不是 WMP-9 正式业务或 Office 验收证据。

本门执行 WMP-9 分阶段业务、权限、审计、零未授权持久化和 Office 文档兼容性验收；
不得实施 WMP-10、模板 CRUD、统一文档中心、远程对象存储、历史模板重生、
Issue #75 或其它已登记产品功能，也不得借验收修改 schema、Alembic、模板、
依赖或安全契约。

开始前更新 origin/main 的远端引用，读取完整 HEAD 并记录为 acceptance_start_sha；不得把
它预填为包含本提示词的未知提交 SHA。要求执行工作区 clean、HEAD 与 origin/main 一致，且
HEAD 等于新适用基线 bd2457a9df4a720b169268ec30976db666ab6713 或是其后代。
明确例外链：cc3ebf8..01bf634 仅提示词；01bf634..44f676c97f18f607ecb85a20d9bbf2237cde4b38
仅 docs/ROADMAP.md 的指定断行合并（失败测试未改）；44f676c..bd2457a 仅
released_weekly_monthly_word_port.py 的 merged game rows 修复与对应新增 3 节点回归测试。
两次修复均经稳定 RED、确认失败、最小修复、回归和只读复审，已建立各自新基线，
不得以旧 cc3ebf8 白名单自动覆盖。bd2457a 自身 Quality 34132227138 / CodeQL 34132225804
均 success 且 headSha 精确匹配。若是后代，bd2457a..HEAD 的差异只能包含本提示词
和 WMP-9 脱敏证据 Markdown；任何产品、测试、配置、模板或依赖变化均须重新建立适用基线。
无论 HEAD 是否等于基线，都要回读 acceptance_start_sha 自身的 Quality/CodeQL success 与
精确 headSha；基线 CI 不能覆盖后续提示词提交。原工作区若有查询缓存或其它未提交修改，
保留它们，使用同一 SHA 的独立干净 worktree，不得为通过 clean 检查丢弃用户修改。

同时只读核验 ADR-0010 已接受，prerequisite tested-code SHA、evidence-closure SHA、75 节点
双次结果与 node-only hash、Review 0/0/0、自动回归、MySQL/SQLite 迁移证据及
prerequisite 两个 SHA 各自 Quality/CodeQL 均与 Issue #55/#56/#57 回写一致。确认 prerequisites closure
相对 tested code 只含文档和脱敏证据，并确认 cc3ebf8 基线相对 prerequisites closure
只含本次文档、文档/开发契约资料、文档契约测试（包括
`tests/test_documentation_security_contracts.py`）和仅供 Codex 开发使用的
`.codex/config.toml`；这些测试和配置不构成产品运行时代码、schema、Alembic、模板、依赖或安全契约变化。
本提示词的更新不代表新的 Issue 回写、独立 Review、正式验收或生产部署已经完成。
任一不一致立即停止；CI 尚未完成时等待结果，失败时先处理对应问题，不得开始正式验收。

系统本体的唯一目标形态是部署在云服务器上的在线 Web 系统。不得构建、安装或验收 Windows/Linux
KindergartenManager 本地应用、便携包或 Debian 桌面包。源码/SQLite 只可用于自动回归和隔离诊断，不能
冒充正式业务入口。Microsoft Word 与 LibreOffice 仅作为云端系统导出 DOCX 的外部消费端，不运行本系统。

本地阶段使用重新创建的独占临时 MySQL 8、合成数据、受保护 UI/application 入口；
应用仅绑定回环，数据库不发布端口，不复用未知 localhost 服务、旧数据库或已清理的临时凭据。
数据准备独立记录，不可调用内部 exporter/fake/binding 替代业务入口。已归档的 bd2457a 四份
原始 DOCX 与 headless PDF 不可覆盖；仅文档后代不要求重取。代码变更或切换正式云端环境时，
再通过该环境受保护入口重取四份原始 DOCX，完成适用的 LibreOffice 检查。可见界面不可用则单项 BLOCKED，
允许以诚实的分阶段记录结束，云端与 Word 保持延期。

恢复云端前，必须取得明确指定的隔离服务器、HTTPS 域名、受控连接与凭据引用，以及
Windows 11 + Word Microsoft 365 Current Channel 和 Linux + LibreOffice ≥24.2 的访问方式。
缺资源时仅提出最小准备方案并 BLOCKED；不得自行创建付费资源、进行未授权访问或探测生产凭据。

正式业务验收使用隔离、脱敏、与生产拓扑等价的云端验收环境：Caddy/HTTPS → NiceGUI app → MySQL 8。
bd2457a9df4a720b169268ec30976db666ab6713 是当前 runtime tested-code；后续仅提示词/证据
Markdown 后代的 acceptance_start_sha 须单独核验双 CI，但不替代 runtime tested-code，
也不要求因此重跑既有 runtime 证据。若验收中获准修复导致代码改变，记录新的
tested-code SHA 并重跑受影响证据，不得混用修改前后的结果。记录不可变镜像引用、服务器 OS/架构、
域名证书状态、数据库版本/Alembic revision（当前应为 `3c9f4b2a7d1e`）、浏览器
及版本；验证 liveness、database readiness、登录和 weekly/monthly 业务入口彼此独立。不得使用生产正文、
生产凭据或生产数据库，也不得把验收环境部署解释为发布或生产部署授权。

只使用隔离 tenant 与脱敏合成数据。weekly/monthly 分别经受保护 UI/application
入口，从 production repository 的 current immutable snapshot 经过唯一
PlanAuthorizationPort adapter，再调用 WMP-8 formal exporter；不得直接构造
binding、读取模板路径、调用内部 service/fake 冒充正式入口或写 ExportRecord。

逐项验收 teacher、teaching_admin、sys_admin 的正负权限矩阵；同租户精确
teacher+class grant、自审拒绝、跨 tenant/owner/class/plan/version/kind 拒绝；
旧 session、auth_epoch、停用/降权、重放、并发 CAS、grant/plan/active-binding
漂移全部 fail closed。跨教师 read/review/export 必须各自产生一条无正文
append-only success audit；拒绝不得产生 success audit。break-glass 因当前无
受控实现必须拒绝。

覆盖 DRAFT/SUBMITTED/RETURNED/APPROVED/ARCHIVED 合法状态图、非法跳转、
一次性短 TTL 删除确认、仅本人当前 DRAFT 删除、tombstone 与历史事实保护。
验证成功或失败均不修改既有正文、旧版本、DailyPlan、preview、模板、
ExportRecord 或未经授权的 audit/export 持久化。

weekly/monthly 各生成正常与长中文样本的原始正式 DOCX，核对内容完整、顺序、
换行、中文标点、空可选值、表格/合并/分页，以及无 marker、样例正文、None、
Python repr、异常正文、宏、ActiveX、OLE、未批准外链或可执行对象；不得 fallback、
retry、历史重生或从零构建正式文档。

两个外部 DOCX 消费端必须独立 PASS；它们不能互相替代，也不代表存在两套本地系统：
1. Windows 11 + Microsoft Word for Microsoft 365 Current Channel；
2. Linux + LibreOffice 24.2 或更高。

若隔离云端环境或任一 Office 消费端不可用，记录缺失条件并标记该验收门 BLOCKED；不得以源码
SQLite、mock、OOXML 解析或另一消费端的结果替代缺失的正式环境证据。

分别记录精确 OS/架构/区域/语言/时区、Office build、字体名称/版本/文件 SHA-256；
打开原始 exporter DOCX，不得出现修复/兼容/宏/外链警告；检查显示与打印布局，
导出 PDF，记录脱敏 DOCX/PDF SHA-256、大小、页数及受保护截图/附件引用。不得
覆盖原始 DOCX，也不得把 Office 自动改写字节当成 exporter 输出。

在同一记录的 WMP-9 tested-code SHA 上运行 prerequisite 75 节点、WMP-5～WMP-8、完整 WMP、
模板中心已实施门、Word/export、权限/session/audit、tests/、Agent Foundation、
changed-file Ruff check/format check 与 git diff --check。任何 finding 均严格执行：
finding → 稳定 RED → 确认失败 → 最小修复 → 回归 → 只读 reviewer 复审。
若必须修改 schema、模板、依赖或安全契约，停止并将 WMP-9 标记 BLOCKED，另行
申请实现门；不得在验收门内自行扩张。

只有云端 weekly/monthly 正式入口、全部适用权限矩阵、Windows Word 与 Linux LibreOffice 的外部文档
兼容性、自动回归、零未授权持久化、Review H/M/L=0/0/0、Issue #55/#56/#57
回写及最终 evidence-closure SHA 自身 Quality/CodeQL 全部通过，才能标记 WMP-9
PASS。WMP-9 PASS 不授权发布或生产部署；完成后停止，并输出独立的
release/production deployment GO/NO-GO 交接清单。
```
