# WP-A 最终证据收口（2026-09-10）

WP-A 实现基线、契约与最短完整 Word 五／六列单页可行性完成。
long 三份仍为两页；共享业务实现、正式模板资格、缩减流程和产品/云端验收属于后续门。
本页记录收口材料；**正式关闭还须本轮独立复审、提交/push、closure SHA 自身适用 CI 和 #77 读回全部完成**。
最终绑定在 [Issue #77](https://github.com/ywyz/kindergartenManager/issues/77) 的本轮收口评论，避免提交自身 SHA 的循环提交。
未取得适用 CI 成功时，只能称 WP-A 实质条件满足、证据/CI 收口未完成。#77 整体保持 OPEN。

## 权威口径和历史结论

本轮实时读取 AGENTS、CONTEXT、ROADMAP、spec/tasks、WP-A/WP-C-next 提示词、ADR-0011、
服务/日历契约、迁移提案、各轮 evidence 和 #77 全正文/相关评论。现有正文仍有旧双客户端验收文字，
其适用性已被 [2026-09-10 用户客户端决定](https://github.com/ywyz/kindergartenManager/issues/77#issuecomment-5619437453)
明确取代；不是新的产品歧义。本轮仅更新 WP-A 阶段检查项并加当前说明，产品验收总项不勾选。

| 历史缺项/finding | 当前处置与依据 | 不代表什么 |
|---|---|---|
| R1 完整新共享业务 RED | [9月9日获批移交 WP-C 首门](https://github.com/ywyz/kindergartenManager/issues/77#issuecomment-5592757010)；WP-A 保留冻结契约/断言及首批差距 RED | 共享/撤销/选源/重导入/CAS/日期占用测试未执行，必须先 RED 后 GREEN |
| R2 样本几何与证据绑定 | 历史 reviewer 已关闭几何 finding；9月9日新样本及9月10日 Word 的五/六列宽度、完整内容及原生预览补证 | 9月8日已丢失的旧二进制没有恢复，不作同 hash 重跑 |
| R3 来源身份映射 revision | 历史窄复审确认契约和提案已补 mapping ID/revision | 未实现来源映射或变化提醒 |
| R4 部分周成员规则 | [9月9日用户确认](https://github.com/ywyz/kindergartenManager/issues/77#issuecomment-5592555046)至少一个实际教学日交集允许整周访问；历史窄复审关闭 | 仍须 WP-C 真实授权 RED，逐日源授权不放宽 |
| 真实宋体缺失 | 9月9日 SimSun 限定 renderer 证据、9月10日 Word 非空可见文字证据已补；空格无需宋体的用户决定保存在 validation 字体范围记录 | 不能声称 PDF 全 span 仅宋体或生产容器字体已验收 |
| Word 原生观察缺失 | 9份只读打开、12页打印预览共21张原生截图，历史独立逐张 Review 完成 | 截图时刻以外的警告、其它 Word 版本、实际纸张打印未验收 |
| LibreOffice 格式/分页、Linux稳定客户端缺项 | 用户明确只作备用打开，解除该格式阻塞且无需补 Linux 格式验证 | 16.9pt 行距 FAIL 和 long 两页仍保留；未执行原生 LibreOffice UI 验收 |
| long 单页失败 | 3份 Word long 均2页，保留负向证据；WP-A 只验最短完整五/六列可行性 | 不要求本门实现缩减；compact 仅合成候选，非真实采用流程 |

[历史总账本](WP-A-20260908.md)、[历史 Review](review.md)、[字体补充](WP-A-fonts-20260909.md)
原始 BLOCKED、H/M/L 和测量失败保留；本轮补充不替原 reviewer 重写历史结论。

`wp-a-font-scope-20260910-210617/clarification.json` 的 `NOT_YET_OBTAINED`、早间
`environment.json` 的 native `BLOCKED` 及各 `prior-*` 都是记录时快照，不是当前状态。
LibreOffice 当前实测以 Windows LibreOffice 报告/manifest 为准，晚间 Word 原生观察以21张截图及追加 Review 为准。

## 版本与客户端绑定

| 标识 | 实际版本与用途 |
|---|---|
| WP-A 基线/9月9日样本生成源码 | `8dcc83376577695b562529ec42adc6b48817f004`；样本同时绑定实际脚本及逐文件 SHA256，不能只由该代码 SHA 推断产物 |
| handoff_sha | `eb3504383023eac6f6c93d8769b6d273a55abd7f`；本轮起始 HEAD 与远端 handoff 分支一致 |
| 远端 main（本轮只读核实） | `8dcc83376577695b562529ec42adc6b48817f004`；未合并 |
| Windows 输入 | 已提交的9份合成 DOCX，见 [37项便携清单](../validation/wp-a-simsun-20260909/manifest.json)；Word/LibreOffice及只读副本使用同 hash |
| Word 实际产品 | Microsoft Word 适用于 Microsoft 365，O365HomePremRetail，16.0.20326.20132 x64；Windows 11 Pro 10.0.26200，zh-CN，Brother DCP-T725DW 驱动 |
| LibreOffice 实际产品 | Windows 26.8.0.3，build `bce0998afefdbc355585ca324285661a2170ba77`，headless、隔离 UserInstallation；非 Linux/原生 UI |
| evidence_closure_sha | 提交完成后由 #77 最终评论记录完整实际 SHA 和该 SHA 的 CI；原运行 manifest 的 null 表示取证当时未提交，不冒写 tested-code |

没有重渲染、编辑或另存已验收 DOCX/PDF/PNG；没有修改产品 app、Alembic、模板、依赖或工作流。
WP-B 名称与 WP-C 身份子步代码是 handoff 已包含的历史工作，本轮不新增 WP-C～WP-F 行为。

## 证据、保全及验证

- [Word 报告](WP-A-Windows-20260910.md)、[Review](WP-A-Windows-20260910-review.md)、[manifest](WP-A-Windows-20260910-manifest.json)：9份输入、9 PDF、12页 PNG；另有9个只读副本和21张原生截图。
- [LibreOffice 报告](WP-A-LibreOffice-Windows-20260910.md)、[Review](WP-A-LibreOffice-Windows-20260910-review.md)、[manifest](WP-A-LibreOffice-Windows-20260910-manifest.json)：同输入9 PDF、12页 PNG，固定20pt要求下行距 FAIL 保留。
- [最终交付清单](WP-A-closure-20260910-manifest.json)记录所有 validation 材料及本轮说明的路径、bytes、SHA256；历史 prior manifest 的旧文档引用按快照时点解释，不递归当作当前清单。
- 原有未提交文件先记录路径/bytes/hash，并在工作区外保留原 diff；没有 reset/clean/stash 或撤销其它工作。取证产物保持原字节。
- 最终保全复核：入场192个未提交文件均仍存在，其中72个 DOCX/PDF/PNG 与入场 hash 全部相同。
- 入场时实跑已有 `verify_wp_a_bundle.py`：37文件通过；Word manifest 132项、LibreOffice 58项逐项核验，0缺失/0 hash或大小不符。
- 只读 PyMuPDF 重新数18份现有 PDF 共24页：每个客户端均6份一页、3份两页，与9份样本清单/PNG数量一致。没有重新执行 Office 验收。
- 新增 `verify_wp_a_closure.py` 支持工作树或 `--revision` Git 字节核验；`--pdf`只读实际PDF页数。该检查只证明材料一致，不替代历史人工格式验收。
- `.gitattributes` 对清单绑定材料禁用换行转换，防止本机 `core.autocrlf=true` 令 push/跨平台 checkout 后文本 hash 改变；提交后再核对实际 Git 对象。

首次暂存检查发现三个契约文档及旧 bundle verifier 的 Git LF/工作树 CRLF 不一致，已仅对这四个路径
重新按属性暂存；忽略行末换行的 diff 为空，没有修改契约或 verifier 行为。原生报告/快照中的 CRLF 与
Word PDF 提取 `page-*.txt` 的行尾空格均按原字节保留；全量普通 whitespace 检查会报告这些历史字节。
对其余暂存文件使用 `git -c core.whitespace=cr-at-eol diff --cached --check`（排除原始 `page-*.txt`）通过，
没有为了 whitespace GREEN 删除字体/空格证据。

本轮核验用 Python 3.14.6、Ruff 0.16.6（Windows 本机可用解释器）；不是项目 Python 3.14.7 的完整本地业务测试。
PDF 元数据检查首次 stdout 使用 GBK 出现编码错误，改为 Python `-X utf8` 后完成；不计业务失败，也未改变任何 PDF。

## 持久化及公开信息检查

采用交接目录 README 已有的仓库内合成 QA 材料方式：提交 validation 中必要合成 fixture、PDF、PNG、报告和脚本。
这些是隔离验证材料，非真实业务导出；不写 exports、不增加 ExportRecord。字体二进制不入仓。
提交后以固定 closure SHA 的 GitHub blob/tree 链接访问，不以 Windows/Linux 本地路径冒充远端链接。

新增文本材料经凭据/私钥/密码/token 等模式扫描，未发现匹配；18 PDF 的作者/标题/主题/关键词均为空、无嵌入附件，
9个源 DOCX 的 core properties 无个人字段、无 external relationships。原生图的合成教师姓名及打印机型号属于本次 QA 环境；
主代理抽看三种 short 的全部打印预览和五列打开图，未见凭据/个人账号信息。
环境报告含历史工具安装/工作目录路径，属于复现定位，不包含用户配置文件本体、Office profile、数据库或真实教案。
原始截图不裁剪、不改图；独立 reviewer 的实际核验范围另记。

## CI 原因及最小脚本修正

实时回读 [handoff Quality run 34469759797](https://github.com/ywyz/kindergartenManager/actions/runs/34469759797)：
headSha 精确为 `eb3504383023eac6f6c93d8769b6d273a55abd7f`，Ruff changed Python files **65 errors / failure**；
依赖安装和 audit 成功，fresh SQLite migration、Test、Agent Foundation **skipped**。没有把它们写成通过。
该分支首推比较默认分支，触及历史 WP-B/C 产品文件及归档脚本；本轮不顺带清理这些产品文件。

本轮新纳入的三个 Windows 验证脚本单独 lint 报9条：import 排序、UTC别名、set comprehension、subprocess 显式check。
原字节保存到 [original-scripts](../validation/wp-a-closure-20260910/original-scripts/)，新可执行副本只作等价机械修正，
`check=False` 保持原有手工检查 returncode 的行为。修正后 Ruff 通过；不以旧人工验收声称执行过新脚本，不重跑会写文件的渲染脚本。
原记录与新脚本版本分别保留 hash，原始产物由旧脚本生成的事实不变。

首个收口提交的 Quality 按既有 workflow 使用 before=handoff 的变更 Python 范围；成功也不表示上述历史65条已修复，
更不代表相对 main 的完整分支 lint/PR CI 成功。本轮不修改质量规则或排除列表。
closure SHA 的远端运行必须另行读回；不能借用 handoff 或旧代码的测试结果。

首个收口提交 `bb84827afb59f29575f93028f162c9adafe3e0e5` 已 push，Git对象442项核验通过，但
[其自身 Quality](https://github.com/ywyz/kindergartenManager/actions/runs/34488927576) 最终为 failure：
Test 1215 passed/1 skipped，Foundation 260 passed/1 failed。已有非 Agent 的 `identity_audit` 表命中 F009
旧名称守卫。此提交不是最终 CI 关闭证据，不能把此前“待CI”的文字读成成功。
经只读 reviewer 确认后仅修正测试的精确业务表枚举，并新增该表存在/为空断言；产品和 Office 样本无改动。
完整原因、隔离探针与复审边界见[CI 补充](WP-A-closure-20260910-ci.md)。后继提交的 push before 为 `bb84827…`，
其实际 closure SHA 和重新运行的完整 Foundation/Quality 结果仍由 #77 最终评论绑定；不继承前一 SHA 的任何成功状态。

## 独立复审及未执行边界

本轮明确调用只读 `wp_a_reviewer`，不递归、不修改文件、不撤销他人工作；实际结果见
[最终 Review 补充](WP-A-closure-20260910-review.md)。提交前不预填 Review 0/0。

最终 reviewer 已支持上述限定实质完成结论；初轮两项已处理，无新的证据/hash/隐私/范围实质矛盾。
其最后要求的 LibreOffice/Word 历史段局部标记已补，剩余为提交、Git 字节核验、exact-SHA CI 及 #77 读回。

本轮未执行共享业务 RED/GREEN、全库本地测试、迁移、真实模型、浏览器产品验收、Word/LibreOffice 重验、
实际打印、Linux 稳定 LibreOffice 格式检查、正式模板资格、发布、部署或生产验收。
后续分门：WP-C 共享授权/权威教学日事实→唯一根/版本/CAS→逐日来源/映射/人工选择/快照；
WP-D 完整日历/固定结构/AI；WP-E 页面、正式模板资格、缩减采用与单页导出；WP-F 产品回归与云端/实际 Word 客户端验收。
唯一下一产品入口为 [WP-C-next-prompt.md](../WP-C-next-prompt.md)，本轮不实施。
