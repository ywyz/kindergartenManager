# 下一门提示词：重新开始 WMP-9 正式业务与双平台 Office 验收

```text
从 WMP-9 production prerequisites 已完成 Issue #55/#56/#57 回写，且
evidence-closure SHA 自身 exact-SHA Quality/CodeQL 均成功的：

`<WMP9_PREREQUISITES_EVIDENCE_CLOSURE_SHA>`

开始。

本门只执行 WMP-9 正式业务、权限、审计、零未授权持久化和目标 Office 验收；
不得实施 WMP-10、模板 CRUD、统一文档中心、远程对象存储、历史模板重生、
Issue #75 或其它已登记产品功能，也不得借验收修改 schema、Alembic、模板、
依赖或安全契约。

开始前只读核验：HEAD 精确等于上述 closure SHA，工作区 clean，HEAD 与
origin/main 一致；prerequisite tested-code SHA、evidence-closure SHA、75 节点
双次结果与 node-only hash、Review 0/0/0、自动回归、MySQL/SQLite 迁移证据及
两个 SHA 各自 Quality/CodeQL 均与 Issue #55/#56/#57 回写一致。确认 closure
相对 tested code 只含文档和脱敏证据。任一不一致立即停止。

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

两个目标环境必须独立 PASS：
1. Windows 11 + Microsoft Word for Microsoft 365 Current Channel；
2. Linux + LibreOffice 24.2 或更高。

分别记录精确 OS/架构/区域/语言/时区、Office build、字体名称/版本/文件 SHA-256；
打开原始 exporter DOCX，不得出现修复/兼容/宏/外链警告；检查显示与打印布局，
导出 PDF，记录脱敏 DOCX/PDF SHA-256、大小、页数及受保护截图/附件引用。不得
覆盖原始 DOCX，也不得把 Office 自动改写字节当成 exporter 输出。

在同一 tested-code SHA 上运行 prerequisite 75 节点、WMP-5～WMP-8、完整 WMP、
模板中心已实施门、Word/export、权限/session/audit、tests/、Agent Foundation、
changed-file Ruff check/format check 与 git diff --check。任何 finding 均严格执行：
finding → 稳定 RED → 确认失败 → 最小修复 → 回归 → 只读 reviewer 复审。
若必须修改 schema、模板、依赖或安全契约，停止并将 WMP-9 标记 BLOCKED，另行
申请实现门；不得在验收门内自行扩张。

只有 weekly/monthly 正式入口、全部适用权限矩阵、Windows Word、Linux
LibreOffice、自动回归、零未授权持久化、Review H/M/L=0/0/0、Issue #55/#56/#57
回写及最终 evidence-closure SHA 自身 Quality/CodeQL 全部通过，才能标记 WMP-9
PASS。WMP-9 PASS 不授权发布或生产部署；完成后停止，并输出独立的
release/production deployment GO/NO-GO 交接清单。
```
