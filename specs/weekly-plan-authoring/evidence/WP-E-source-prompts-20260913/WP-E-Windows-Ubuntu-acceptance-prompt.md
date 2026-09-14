# WP-E Windows 补验与 Ubuntu 测试站续作提示词

以下正文可直接交给续作开发/验收任务。本提示词承接 2026-09-12 已有材料，不代表验收通过，也不自行授予部署、生产或外部消息权限。

---

继续 KindergartenManager 的 WP-E 验收。最终目标是完整关闭 WP-E 后具备进入 WP-F 的条件；当前不执行 WP-F，不提前生成 WP-F-next-prompt.md。Windows 是原生 Microsoft Word 排版验收客户端，Ubuntu 是后续 Web 测试站运行环境，两者证据分别记录。

## 1. 先核对现场、代码与材料

保留 main、现有 worktree 和所有未提交文件。在授权可写目录使用隔离 checkout/worktree；不得覆盖旧现场。先读实际分支 AGENTS.md、ADR-0011、weekly-plan-authoring/spec.md §2.2–2.7、tasks.md WP-E/F、WP-E-local-contract.md、WP-E-Windows-handoff.md、WP-E-continuation-prompt.md、WP-E 两份原交付/续作证据，以及本次新增记录：

- evidence/WP-E-header-week-20260912.md
- evidence/WP-E-native-Word-20260912.md
- evidence/WP-E-dedup-recheck-20260912.md

已知当前产品 SHA 为 `0bded3377c01956833bcbb6cd306f9a7f5d924e1`；写作前最新文档后继为 `247fc3472481bcdc7b161b36301e08f205da9c71`。本提示词可能位于更晚的文档后继，须现场核验 ancestry、app/tests 差异和工作树，区分产品 SHA、文档 SHA 与测试站实际运行 SHA。

Windows 隔离分支为 `codex/wp-e-windows-holiday-20260912`。此前远端 `origin/feat/wp-e-continuation-20260912` 的已知引用为 `84f189f160808c0001cd9d316d6b99fbf6816f34`，原产品基线为 `9cde71655c30cafdc6ac4e99ed22509ad989b121`。这些远端事实可能变化，先获取最新引用再比较；不能认为该远端已经含本轮本地修改。Ubuntu 若缺当前提交或外部材料，明确记录缺口，经允许的传递方式核验后再复验，不用旧 SHA 代替。

先运行 `specs/weekly-plan-authoring/validation/wp-e-handoff-20260912/verify_bundle.py`，预期精确输出 `INTEGRITY_OK: 26 files; not Word or WP-E PASS`。失败不得改写清单。26 份便携材料不包含新待验 DOCX/原生截图，也不等于全部外部证据已打包。不得使用 main 旧 WMP-9 `bd2457a` 或四份归档 DOCX 替代当前 WP-E 输入。

Windows 外部材料根目录：
`C:/Users/admin/.codex/visualizations/2026/09/12/01a0937c-3f64-7ce2-98f9-fecd1934901c`

| 子目录/文件 | 用途 |
|---|---|
| wp-e-header-week-20260912/candidate-manifest-final.json、candidates-final | 当前 renderer 八份原始候选及正文/输出绑定 |
| wp-e-native-final-20260912 | 八份候选的12页原生观察、环境、49份材料清单与有限复审 |
| wp-e-reduction-20260912/proposal-review.md/json | 四份长文去重的采用前逐字段差异 |
| wp-e-reduction-20260912/adoption-save-receipt.json、accepted-files | 用户明确采用后保存的四份本地正文与 DOCX |
| wp-e-reduction-20260912/native-recheck.json、native、evidence-manifest.json | 四份去重版的8页原生重检与38项材料清单 |

逐件核对清单 hash、原件 hash、renderer 与模板 hash；没有文件时标记缺失，不能只凭 Markdown 叙述补写通过。清单的覆盖范围按生成时点解释，不要求它包含自己或后续独立复审。

## 2. 保留当前真实结果，不重写历史

Windows Server 2025 Datacenter 已获用户明确接受，验收通过即计 Windows PASS，不因 Server 名称阻塞。前次现场记录为 24H2、OS build 26100.32860；Word 账户为 Microsoft 365 2608、Click-to-Run 20326.20132、当前频道；关于 Word 为 Microsoft Word for Microsoft 365 MSO 2608、Build 16.0.20326.20072、64位。两处 build 分开记录。新会话核验实际环境；去重批次只引用前次环境，并未重新打开账户/关于界面。

八份原始候选已完成全部页观察：四份正常内容各1页、四份长文各2页；四份长文经用户确认去重后仍各2页。各自单页结果分别保留 PASS/FAIL，不能覆盖历史 long 三份两页 FAIL 或 compact 仅合成候选的记录。

五列正常样本仅所选正文确认宋体、小四12pt；全文段落行距框为空（混合），仅“家园共育”单段确认固定20磅。其他文件未完成属性对话框检查。50% 全页截图不足以判全文数量、细微裁切、字体漂移或完整格式 PASS。

已确认去重只删除每个受影响段落中紧邻的第二遍重复句，每份25个字段，保留第一遍、名称、人员、日期、数量等。用户的“确定”仅绑定已展示的四份去重提案，不要求重复确认同一提案，也不扩展为进一步删除事实的批准。

上述去重是本地合成材料的手改采用与文件保存，没有产品 plan/session 身份、真实超页 ticket 或产品数据库新版本。不得登记为产品“有限缩减→采用→保存”链、真实模型或正式导出 PASS。AST 提取纯规则函数的无变化结果，也不是完整 ReductionApplication 调用证据。

WP-C 四类历史 native 双 RED 缺口仍 UNMET，保留用户允许继续 WP-E 本地工作的决定，不补造历史 RED。

## 3. Windows 必须补齐的原生验收

先完成已有正常五/六列样本的格式与内容细查，再验当前产品正式保存快照生成的新文件。逐文件、逐检查项记录 PASS/FAIL/NOT_RUN/BLOCKED、观察时间、输入 hash、产品 SHA、模板绑定、原生客户端和原始证据位置。

1. 核实实际 Word 账户/关于的产品、版本、build；只保留必要信息，可用不含账户个人信息的局部证据。遵循当前分支 Microsoft Word 客户端政策，不继承旧 WMP-9 产品/通道限制。
2. 五/六列正常及长中文、多姓名、空格、书名号、固定游戏和目标数量、区域与总结数量、日期顺序/假期空格、换行、无样例残留，逐字段与生成输入对账。
3. 原生确认 A4、正文宋体12pt、固定20pt、标题遵循受控模板；定位“全文行距混合”的具体段落。区分实际正文、空段落和合并单元格结构，不能先把混合显示认定为产品缺陷，也不能直接忽略。
4. 原生打印预览观察全部页，增加足够倍率的上下/左右细节，检查裁切、重叠、缺字和字体漂移。页数、属性和视觉结果分别记录，不以共用 renderer 推断其他文件通过。
5. 所有原件只读保留；新结果另存并记录 hash。COM、OOXML、LibreOffice、PDF或浏览器 CSS 可辅助定位，不能替代原生 Word 资格。可见控制不可用时，由用户操作原生 Word，提供全部页和所需属性观察材料，未观察项保持未验。
6. 完成独立只读复审；复审需要补充的内容明确列出，有限页数复审不等于完整格式或正式模板资格复审。

## 4. Ubuntu 测试站必须完成的产品链

先核实目标 URL、测试环境、tenant、操作账号/角色、数据与运行授权、当前产品 SHA、配置和数据库 revision。缺必需输入时具体列出，继续不依赖它的本地准备。不得用直接改数据库或伪造 session、binding、ticket 的方法冒充真实目标页面验收。

定位当前正式受控模板和 released 记录，核对读取授权、来源、UUID/version/contract/hash 及 active 状态。仓库 seed 声明为 UUID `00000000-0000-0000-0000-000000000801`、version8、contract `kg.template.weekly_activity_plan.candidate` v2，仅是源码声明，不能证明当前云端 released。当前 renderer hash 为 `6186fd0bc62ca8a31af2236645d22d07e7fbe8ee4a53069181b78638ba0240f7`，seed hash 为 `f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b`；有变化须重新绑定适用证据。

依据可信 catalog 契约先独立审查 Word 资格材料，再核验安装输入和目标授权。`local-synthetic`、`local_only=True` 或默认空 catalog 的失败关闭都不能登记正式资格/正式导出 PASS。资格缺失导致产品流程不能运行时记录 BLOCKED，不关闭保护门以制造验收结果。

在真实目标页面补齐以下分支，历史 localhost 步骤只覆盖其实际记录，不等于云端矩阵：

- 来源零/一/多、重复选择与来源变化；缺项生成、选字段重生成；拒绝与采用。
- 同班两教师共享、人员不被另一个教师打开时覆盖；并发保存与冲突处理。
- 取消、超时、候选过期、来源/权限/人员/模板/版本/页面修订漂移，正文和旧版本保持正确。
- 显式保存、重开读取、commit_unknown 只读对账；不重发未知保存或下载。
- 当前保存版本的真实超页检查→有限候选→原文差异→明确采用→数据库保存新版本→重开核对→重新渲染→Windows 原生复验。另验拒绝不变、取消/过期不采用、次数限制和无自动重试。
- 没有可用固定短写时明确提示手改；无法收敛时保留正文且不交付已知两页文件。再用获确认的可容纳正文完成成功链，不能只证明拒绝分支。
- 下载前后的会话/成员/保存版本/模板绑定检查、临时文件清理、授权审计和无新增 ExportRecord 等按现行契约验收。

长文原始两页是负例，不要求任意长文被强塞进一页。可容纳输入的成功导出与无法收敛输入的正确拒绝是两个独立通过项；负例不能被记成“单页 PASS”。本地去重文件重检不能代替这些页面行为。

真实模型仅通过当前操作教师的应用配置/解密/adapter；不得读出、复制或注入密钥，不借来源教师凭据。记录实际模型与必要请求证据，不将 mock 或开发代理手工改写算成产品真实模型调用。

## 5. 何时修改 Ubuntu 开发端代码

先定位，后决定，不因长文两页或证据未补齐就自动修改实现。

- 发现实际正文未满足固定20pt、字体或排版要求，按 renderer 缺陷处理。
- 发现已知超页被错误放行、未保存内容导出、采用/保存错误、取消漂移失效、来源/旧版本被改等，按产品行为缺陷处理。
- 现行有限规则只允许固定谓语短写及受保护边界外的空格规范化，没有匹配时要求手改。若要让产品自动做本次重复句去重，这是规则能力变更；先明确需求与现行 ADR/spec/本地契约的关系，按要求补契约及保护测试，不用提示词绕过固定校验，不扩大产品 Agent 工具。

新行为缺陷按现行门保全修复前源与 hash、连续两次稳定应用业务 RED、最小修复、相关回归和独立只读复审。环境/测试错误不计 RED。修改后冻结新产品 SHA，运行适用迁移/隔离/并发/旧兼容/Agent 回归及 lint/format/diff；重新生成和复验受影响 Word 材料，旧 SHA 的人工通过不自动继承。不暗中减字号、减行距、删固定条目来解决超页。

## 6. 交付与关闭判据

交付可追溯矩阵：每行列明检查项、平台、实际输入/输出 hash、产品 SHA、证据、状态、缺口及下一步。分别记录 Windows 原生完整格式资格、Ubuntu 页面链、真实模型、正式 released/catalog、exact-SHA CI、不可变 OCI、迁移、部署与相关授权。

本地实现/测试、测试站部署、正式验收、生产发布互不推导。没有授权不自动部署、迁移、操作生产、推送/合并或发送 Issue 消息。Ubuntu 的应用/渲染服务要按实际受控运行版本验收，但 LibreOffice 客户端排版与 Word 一致不是本分支新增门。

所有必需 WP-E 门实际满足才记 WP-E COMPLETE；Windows 单项或正常文件一页不等于整门完成。未关闭时继续交付 WP-E 续作记录，保留全部历史 FAIL/UNMET。只有完整关闭后，才依据 tasks.md 的 WP-F 全矩阵撰写 WP-F-next-prompt.md，不提前宣称 WP-F 执行或完成。
