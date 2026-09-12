# WP-E 本地实现契约与剩余门（2026-09-12）

本记录接续冻结矩阵 `WP-E-preflight-20260912.md`。该前置记录保留其写作时的 BLOCKED 状态，不改写历史。用户随后对“保留四类缺口 UNMET，允许依赖继续 WP-E 本地实现与隔离验证？”明确回复“授权”。这只解除 WP-E 本地依赖处置阻塞，不消除 WP-C 四类历史 native 双 RED 缺口，不扩展到远端或 WP-F。

WP-D 基线已逐件实时核验：tested_code_sha `258a9b0978e89397c90a4b7e271388d58b13b8d7`、文档后继 `3fcefdf08a4b6aa6d3d7d5eb674cac2fce180713`、318 材料/28 代码/16 文档 hash、干净状态及单一 head。原 177/178 raw hash 事实与 JSON 重写时序解释仍保留。当前隔离分支 `feat/wp-e-authoring-20260912`；最终代码及文档 SHA 由交付清单记录。

## 需求到真实入口与证据

| 门 | 真实 UI / 应用入口 | 输入输出与拒绝 | 验证节点 | 状态边界 |
|---|---|---|---|---|
| E1 | `/home`、菜单→`/weekly-plan`；`WeeklyEditor`、`WeeklyPageApplication` | 权威班级/学期、五六列、共享人员快照、最后编辑者、单层书名号、完整分组手填、未保存提醒 | `test_wpe_ui_callbacks`、`test_wpe_ui_navigation`、实际受控浏览器 | 本地实现；浏览器证据与最终 SHA 单列 |
| E2 | 现有 `composition.authoring` 的 sources/structure/generate/regenerate/adopt/save/reconcile | opaque候选ID、关闭schema、双CAS、缺名称手填、假期不生成；取消/失效不改正文，普通历史与本次live依赖有界 | WP-D回归、UI回调、reduction/export事务用例 | 不新增授权policy/共享根/产品Agent工具 |
| E3 | `SharedWeeklyWordPort` + `LayoutAuthority` | 受控原模板hash；新profile独立资格，绑定实际released active UUID/version/contract/hash；五六列填充/回读 | `test_wpe_word_layout`、`test_wpe_word_authority` | 本地真实LibreOffice合成证据；正式Word资格 BLOCKED |
| E4 | `SharedWeeklyExportApplication.check_saved` | 只检测当前保存版本，缺必需项/schema/字体/renderer/超页/裁切明确拒绝；合法缺项草稿可保存 | `test_wpe_export_application`、`test_wpe_render_pipeline` | 不以预算、OOXML或CSS推断实际一页 |
| E5 | 提示词管理 `weekly_reduction`、`ReductionApplication` | 实际超页ticket→最多两次候选→差异→明确采用→显式保存→重检 | `test_wpe_reduction_application`、`test_wpe_reduction_rules`、真实渲染pipeline | 保守固定规则；不能收敛时保留正文、手动调整 |
| E6 | `export_saved` / `reconcile` | 进入/等待后/最终重验actor/session/assignment、plan双CAS、page、binding和live依赖；取消/漂移不交付；unknown只读对账 | 两库export用例、迁移往返/拒绝降级、回归与跨模块只读复审 | 无隐式保存/AI/审核前置；不新增ExportRecord |
| X | exact-SHA CI / OCI / 云端页面 / 真实模型 / Word产品版本 | 各自单独授权及实际证据 | 尚未执行 | BLOCKED / NOT_RUN；不得写 WP-E COMPLETE |

## 正式资格与渲染契约

受控 `templates/weekplan.docx` 原字节不改写。新 `shared-weekly-v3.v1` profile从该种子生成九行五/六列布局，保留固定标题、标签、数量、宋体12pt、固定20pt、A4和边框；不复用旧合同的资格结论。标题、日期顺序、多姓名、换行及假期空白逐格回读。真实渲染后以PDF页数、SVG表格边框和完整文字bbox、逐格文本一致性检查裁切/溢出；临时DOCX/PDF/PNG/SVG在独立目录结束时清理。

`LayoutAuthority` 的可信catalog是 manifest路径+预期hash，由应用运营配置，不接受教师上传pass标志。资格含五/六列DOCX/PDF/PNG/native报告hash、Word具体产品版本、实际渲染器版本、原模板hash及当前正式released binding。每次resolve/guard重新校验材料和正式依赖；active切换使用同一锁和CAS。生产默认无资格时明确失败关闭。组合函数允许由受信应用组装代码传入已配置的word_port；没有新增教师激活API。测试 `local_only=True` catalog只证明本地算法，不可安装为正式Word资格。

历史 long三份两页FAIL和compact仅合成可行性候选不变。当前LibreOffice结果不升级成Word或云端PASS。

## 保存、候选与交付契约

正文权威仍为 `weekly-authoring.v3` 的slot/schema/calendar/budget/archive。保存允许缺项，导出完整性独立校验。生成、导入及缩减候选只在有TTL/容量限制的进程内存中；采用只改当前页面，显式保存才创建不可变版本。源DailyPlan、旧版本、旧快照和人员历史不会反写。

缩减 `weekly-reduction.rules.v1` 仅接受固定句法边界内的等义谓语短写及非保护区域空格规范化，严格保护已确认名称、引号/书名号、数字、日期、否定、固定栏及假期格。Provider输出必须逐字段与闭合规则结果一致；不能自由删事实。每session+plan的1800秒内存周期最多两次请求（失败也计数），无自动重试；保存/重开不重置本次周期。候选拒绝/取消不改内存正文和版本。重启清空所有候选和检查，需要重新检测，不是计划终身次数配额。

本次live缩减来源和prompt/binding依赖跨采用、保存、重开保留；普通历史手改不强加永久live来源依赖。commit_unknown只保存操作ID、scope和有界依赖元数据，先只读对账，不重发保存或下载。

检查及导出均使用保存快照。渲染期间无数据库事务；交付短事务重授权、锁定双CAS并写入无正文的 `shared_weekly_export_audit`。该表记录授权线性化，不是文件下载成功/浏览器已收到的证明；不含文件路径、预览、正文或姓名。UPDATE/DELETE禁止，非空拒绝downgrade。最终等待保持页面写锁和取消令牌，UI同时验证未flush输入epoch；若提交已成立但后续取消/ack未知，允许保留授权审计而不交付文件，只读对账不重发。整个流程不创建ExportRecord。

## 未关闭门

实际Word原生全页预览、字体/裁切/固定数量及具体产品版本证据缺失；生产catalog尚未安装。远端exact-SHA CI、不可变OCI、受控云端浏览器、真实模型和真实数据库revision没有本轮授权/证据。实现/本地mock/两库/LibreOffice/浏览器/独立复审分别绑定证据角色。WP-E未完整关闭时只交续作阻塞提示词，不执行WP-F、不回写Issue，不推断远端状态。
