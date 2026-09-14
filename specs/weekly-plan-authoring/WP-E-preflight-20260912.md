# WP-E 前置核查与冻结矩阵（2026-09-12）

状态：**BLOCKED：WP-C 四类历史过程缺口的 WP-E 依赖处置尚未获明确授权；WP-E 未实现、未 COMPLETE。**
本轮用户允许核查、尝试修复历史缺口、保留既有更改及有边界委派，同时明确“本文件本身不授权执行”、不得将 2026-09-11 的 WP-D 处置扩大为其他阶段豁免。先保全和核查，不回退已修复代码制造历史 RED。

## 实时核查

- WP-D tested_code_sha：`258a9b0978e89397c90a4b7e271388d58b13b8d7`。
- 文档后继：`3fcefdf08a4b6aa6d3d7d5eb674cac2fce180713`，祖先检查成功，差异仅 16 个 Markdown/JSON 文档。
- WP-D worktree 干净；只读 `alembic heads` 返回唯一 `c264d8fa1037`，没有执行迁移。
- 最终清单 318/318 外部材料字节长度/hash、28/28 改动代码 hash、交付关闭记录 16/16 文档 hash 匹配。
- 原始核查 JSON：`/home/ywyz/code/km-wpe-preflight-20260912/wpd-integrity.json`。本轮没有重跑两库或回归；原测试日志属于 WP-D 代码 SHA 的历史验证。本轮只确认其完整性及绑定。
- 已读取 AGENTS.md、ADR-0011、spec §2.2–2.7、tasks WP-E/F、current-status、CONTEXT/ROADMAP、WP-D 关闭矩阵、账本、最终清单与独立复审。WP-D 矩阵所有必需本地行记录 LOCAL_PASS，X1/X2 明确移交。本次未发现 WP-D 本地关闭材料缺项；这不关闭 WP-C 历史门。
- 原始授权 `authorization.txt` 明确回应“授权执行 WP-D”的问题。四类历史缺口仍为 UNMET；原清单 177/178 raw hash 及 JSON 在清单生成后重新序列化的时序解释保留。缺失的原 70da 字节不重建，不重算原清单。

## 保全

隔离分支 `docs/wp-e-preflight-20260912`，worktree `/home/ywyz/code/km-wpe-preflight-worktree-20260912`，从上述已核实文档后继建立。创建前记录全部 12 个既有 worktree 的 HEAD、status、staged/unstaged binary diff hash 及可见已修改/未跟踪文件 hash，见外部 `preservation-before.json`；不复制业务数据库、配置、密钥或无关代码。必要授权/完整性解释/交付关闭/复审输入复制后逐字 hash 相同，见 `copied-inputs.json`。最终复核 12 处原 worktree 的 HEAD/status/staged/unstaged diff 及 133 份初始材料 hash 均匹配，见外部 `preservation-after.json`。原工作区保持原样。

## 需求→真实入口→输入输出/拒绝→测试→证据→状态

下表冻结实现与验证要求。测试列为待实施场景，不冒充已有测试节点或 RED；现有 WP-D 节点仅作为依赖。真实当前教师入口是 `app/ui/pages/weekly_monthly_plans.py` 的 `/weekly-monthly-plans`，当前提供旧周/月查看及导出；新填写尚未接线。新应用依赖是 `get_shared_weekly_services().authoring`；不增加第二套 policy 或共享根。

| 需求 | 当前/拟接入真实入口 | 输入输出与明确拒绝 | 必需验证 | 证据与状态 |
|---|---|---|---|---|
| E1 表头、人员、共享及完整填写 | 上述教师页面；authoring.begin_authoring/header/update_edit/update_slots | 授权班级、规范五/六日期、周次、单层书名号、多姓名；打开不写；显示最后编辑者、共享与未保存 | 两教师打开/默认变化不覆盖；全部固定 slot 可手填；桌面 A4 比例、窄屏可用 | 新真实 UI 证据待采；NOT_IMPLEMENTED |
| E2 来源、生成、差异采用、保存 | authoring.list_sources/select_sources/propose_import；list_structure/propose_structure；generate_missing/regenerate/adopt_generated/save_edit/reconcile | opaque ID/关闭协议；缺 activity_name 待手填；假期不生成；取消/过期/replay/源、mapping、page、prompt、target 漂移保留正文；双 CAS | 实际页面选择重复源、生成缺项/选字段重生成、拒绝/采用、保存重载；两库并发/撤销两顺序/commit_unknown；普通历史编辑与本次 live 来源分开 | WP-D 有应用依赖证据；WP-E UI 与集成证据待采 |
| E3 正式五/六列模板资格 | template_center.candidate_qualification、旧 qualification_orchestration/template_enablement 为边界参考；新 profile/contract 待实现 | 明确模板 hash、active version、契约版本；A4/宋体12pt/固定20pt、固定栏目数量、日期假期、多姓名换行、无样例 | 当前正式模板各五/六列填充回读、资格失败与 binding 漂移；原生 Word 全页观察 | 尚无本门正式资格；WP-A compact 仅合成候选 |
| E4 保存版本单页检查 | 新 shared exporter/layout 应用入口待实现；旧 formal_exporter 只作为既有契约参照 | 仅明确保存的不可变 v3；缺必需项/schema错/缺字体或renderer/超页/裁切/溢出失败，零文件交付；合法缺项仍能保存 | 真实渲染页数及裁切/溢出；超页文件不返回；不可变版本及 hash 保持 | NOT_IMPLEMENTED；预算/OOXML 不作为实际一页 |
| E5 有限缩减 | /prompts 现有管理；新增缩减 task/schema 与 authoring 窄流程待实现 | 最多两轮候选、逐次差异确认；AI/手填/导入均同等确认；拒绝不改内存/版本；保留事实、标题、日期、数量、假期格与排版 | mock integration 最小上下文/当前教师配置；超时取消漂移零采用；第二轮仍失败保留内容；无自动重试 | NOT_IMPLEMENTED；不扩产品 Agent 工具/WRITE或 #79 |
| E6 正式交付与清理 | 新 shared export 应用入口；旧 WeeklyMonthlyFormalExporter.export 的 resolve/render/parse/binding 重验边界参考 | 入口、等待后、最终交付重验 actor/session/assignment、双CAS、binding及适用来源/候选；无内部AI/隐式save/审核前置 | 两库撤销及保存线性化；失败取消成功均清理临时DOCX/PDF/PNG；零ExportRecord/持久预览/源反写/半提交 | NOT_IMPLEMENTED；不复用旧类型冒充新共享资格 |
| E7 整门回归和外部门 | 当前真实应用和实际客户端 | 精确区分 Main/Reviewer、SQLite/MySQL/mockAI、CI、真实AI、云端、Word | 常规/Foundation/旧周月/Agent、迁移、lint/format/diff、独立只读复审；真实目标页操作；实测 Word 产品版本全部页 | 本轮未运行；云端/真实模型/凭据/真实迁移/发布需独立授权；Word 无本门证据 |

## 冻结的资格与导出契约

资格必须绑定当前受控 `weekplan.docx` 的实际模板字节、正式 profile/contract、active version 和五/六列独立证据，不能修改历史资格 hash 使其覆盖 v3。当前未选择/激活任何新模板，不声称现有 active binding 已支持本门。

正文权威是 `weekly-authoring.v3` 的固定 slot/schema/calendar/budget/archive；草稿保存与导出完整性分离。正式 exporter 只读已保存的当前不可变版本，不能调用 AI、隐式保存或返回已知超页文件。生成的实际页数和裁切/溢出由受控渲染检测，缺字体/渲染器失败关闭；Word 主客户端验收仍须原生全页预览和实测产品/版本。LibreOffice 仅备用打开；历史 long 三份两页 FAIL、compact 仅合成可行性候选不变。

新发现行为缺口须先保留修复前源 tar/hash，在真实应用业务入口连续两次 RED 后最小修复，再独立只读复审；初次通过单列覆盖。缺接口、NameError、环境/字体缺失和文件存在断言不能计业务 RED。禁止把现在执行的旧版本复现倒写为历史修复前已执行 RED。

## 继续条件

独立 reviewer `wpc_history_audit` 已只读审计四类历史材料，未发现此前遗漏的合格原证据，历史门继续 UNMET。source audit 虽有两库各两次失败，属于独立 FK probe；hash 非空与 event 身份各只有 SQLite 两次 probe；reimport 下界虽有两库各两次，也属于 isolated probe。原始分类见 `/home/ywyz/code/km-wpc-complete-evidence-20260911/source/SOURCE_EVIDENCE_HANDOFF.md` 和 `MAIN-ASSESSMENT.md`；不将这些材料升级为 native 应用证据。需要用户明确决定是否允许这些缺口保持 UNMET 而继续 **WP-E 本地实现及隔离验证**；2026-09-11 的 WP-D 授权不代替这一决定。不能通过再改一次正确代码消除过去的执行顺序缺口。

WP-E 未关闭，因此不生成 WP-F 实施授权提示词、不执行 WP-F。不 push/PR/合并/Issue 消息/部署/真实模型/真实迁移/发布，不关闭 #77/#57/#75。下一轮仅从本核查及最终独立审计结论继续，重新验证基线漂移。
