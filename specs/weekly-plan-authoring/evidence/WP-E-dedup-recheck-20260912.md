# WP-E 长文去重采用与原生重检 2026-09-12

用户在四份逐字段去重差异展示后回复“确定”。本轮按该明确确认保存四份本地正文快照，使用当前 WP-E renderer 生成四份新 DOCX，并在原生 Word 逐件观察全部八页。四份均仍为两页，实际单页 FAIL；没有进一步删改未经确认的正文，没有改字号、行距或 renderer。

## 材料和采用边界

任务根 `C:/Users/admin/.codex/visualizations/2026/09/12/01a0937c-3f64-7ce2-98f9-fecd1934901c`，本批次目录 `wp-e-reduction-20260912`。
`proposal-review.md/json` 保留采用前逐字段差异，`adoption-save-receipt.json` 记录确认、原/新 hash 与保存角色，`accepted-files` 保留已采用正文和 DOCX，`native` 为独立全页截图，`native-recheck.json` 为本次结果，`evidence-manifest.json` 固定生成时 38 个材料的 hash（不含清单自身及后续复审）。

每份只改 25 个字段：删除相邻的第二遍完全重复观察/交流/整理句，保留第一遍及原开头，清理相接的“。，”。姓名、日期、名称、数量、假期、来源、人员和其余字段不改。四份 slot 字符数分别为 1773→972、1764→963、1778→977、1764→963；字符数不是页数证明。

初次保存辅助脚本因提案 JSON 末尾换行不符合产品 canonical parser 被拒，尚未写出正文/DOCX。之后仅移除 JSON 文件末尾换行，字段值不变；采用提案 hash 和 canonical 保存 hash 在 receipt 中分别绑定。原提案及原始长文保留。

这是本地合成验收材料的采用/文件保存，不是应用中的计划版本保存。原始 fixture 没有产品 plan/session 身份，未进入当前目标页面、未产生产品数据库版本，也未伪造 check ticket。产品“检测→有限缩减→采用→显式保存→重检”链仍 NOT_RUN。
现行规则纯函数对四份输入无可用自动短写；此前 AST 提取的纯函数检查只证明这一点，不是完整 ReductionApplication 或真实模型调用。去重属于用户确认后的手改，不能登记为自动缩减、AI 调用或两次请求配额验收。

## 冻结绑定与原生结果

产品 SHA `0bded3377c01956833bcbb6cd306f9a7f5d924e1`，本轮开始文档后继 `6e07ff89c39f7ec308e2ef0faabbf22a4131fffb`；产品代码未改。
Renderer SHA256 `6186fd0bc62ca8a31af2236645d22d07e7fbe8ee4a53069181b78638ba0240f7`，seed SHA256 `f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b`；来源声明 binding 继承记录，当前 Ubuntu released 状态仍未核实。

| 新文件 | 原生观察页 | A4 纵向 | 单页 |
|---|---:|---|---|
| five-long-dedup.docx | 1、2 / 共2页 | PASS | FAIL |
| five-holiday-long-dedup.docx | 1、2 / 共2页 | PASS | FAIL |
| six-sunday-long-dedup.docx | 1、2 / 共2页 | PASS | FAIL |
| six-saturday-long-dedup.docx | 1、2 / 共2页 | PASS | FAIL |

四份打开后共享只读重新核对 DOCX hash 均与保存 receipt 一致。未打印、未在 Word 保存编辑。每页 50% 原生总览只支持分页观察，不足以单独判细微裁切、字体漂移、逐字数量或全部段落格式 PASS；本批次属性对话框 NOT_RUN，不能继承前批局部字体通过。

本次沿用同一 Windows 主机和已安装 Word，重新启动原生 Word。具体版本引用前批现场 `wp-e-native-final-20260912/environment.json`：Windows Server 2025 Datacenter 24H2 build 26100.32860；账户 Microsoft 365 2608 Click-to-Run 20326.20132，关于 Word MSO 2608 build 16.0.20326.20072 64位。此次未重新打开账户/关于界面，不将引用记录写成新现场版本核验。

## 剩余门

本次仅去重未解决单页。若继续手改，须另展示具体差异并明确采用后保存、重检，不把重复去重或新请求计作原应用有限请求验收。已采用版和原长文均保留，历史 long/compact 不改。完整 Word 格式、正式资格/catalog、受控页面全分支、真实模型、exact-SHA CI、OCI、迁移和部署继续分别保留原缺口；WP-C 四类历史 native 双 RED 仍 UNMET，WP-E BLOCKED，WP-F NOT_RUN。

## 独立只读复审

`preparation_review` 独立核对清单 38/38 文件 hash、四份 DOCX/body 与 receipt 一致；确认四份 accepted 正文与展示提案逐字一致，仅 JSON 末尾换行差异，每份恰好改 25 个 slot 值，其余字段、来源和引用不变。独立查看全部八页原生截图，支持四份各两页、A4 纵向、实际单页 FAIL。

未发现证据或边界表述错误。复审范围为去重采用材料和原生分页，未将本地文件保存混同产品数据库保存；未重读账户/关于 Word、格式 NOT_RUN 的限制保持。正式资格、完整 Word 格式与 WP-E 总门仍未关闭。
