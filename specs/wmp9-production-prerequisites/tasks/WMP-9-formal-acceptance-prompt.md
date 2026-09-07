# 下一门提示词：重新开始 WMP-9 云端正式业务与 Office 文档兼容性验收

```text
以上一门已回读的 WMP-9 production prerequisites evidence-closure 提交
`f07971d6624d7e9c032f21fe94a7415a55b0786c` 为基线。该门的 tested-code SHA 是
`72d759fc128b013c2345bd609875bb3e3d623ef1`；两者不能互相替代。

本次云端在线定位的文档闭合提交必须在提交后取得，并在该提交上重新回读自身
exact-SHA Quality/CodeQL 和文档契约测试成功后，才可填入：

`<WMP9_CLOUD_ONLINE_ACCEPTANCE_START_SHA>`

开始。

本门只执行 WMP-9 云端在线正式业务、权限、审计、零未授权持久化和 Office 文档兼容性验收；
不得实施 WMP-10、模板 CRUD、统一文档中心、远程对象存储、历史模板重生、
Issue #75 或其它已登记产品功能，也不得借验收修改 schema、Alembic、模板、
依赖或安全契约。

开始前只读核验：HEAD 精确等于上述文档闭合 SHA，工作区 clean，HEAD 与
origin/main 一致；ADR-0010 已接受，prerequisite tested-code SHA、evidence-closure SHA、75 节点
双次结果与 node-only hash、Review 0/0/0、自动回归、MySQL/SQLite 迁移证据及
prerequisite 两个 SHA 各自 Quality/CodeQL 均与 Issue #55/#56/#57 回写一致。确认 prerequisites closure
相对 tested code 只含文档和脱敏证据，并确认新的文档闭合 SHA 相对 prerequisites closure
只含本次文档、文档/开发契约资料、文档契约测试（包括
`tests/test_documentation_security_contracts.py`）和仅供 Codex 开发使用的
`.codex/config.toml`；这些测试和配置不构成产品运行时代码、schema、Alembic、模板、依赖或安全契约变化。
新的文档闭合 SHA、其自身 CI 结果和 Issue 回写不得预填或沿用 `f07971d…`、release source
或 tested-code SHA。任一不一致立即停止。

系统本体的唯一目标形态是部署在云服务器上的在线 Web 系统。不得构建、安装或验收 Windows/Linux
KindergartenManager 本地应用、便携包或 Debian 桌面包。源码/SQLite 只可用于自动回归和隔离诊断，不能
冒充正式业务入口。Microsoft Word 与 LibreOffice 仅作为云端系统导出 DOCX 的外部消费端，不运行本系统。

正式业务验收使用隔离、脱敏、与生产拓扑等价的云端验收环境：Caddy/HTTPS → NiceGUI app → MySQL 8。
记录 tested-code SHA、不可变镜像引用、服务器 OS/架构、域名证书状态、数据库版本/Alembic revision、浏览器
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
