> 2026-09-10 最终收口：本报告及原始产物按字节保全。下文 closure_sha=null/未提交描述取证时状态；实际提交与 exact-SHA CI 由[收口账本](WP-A-closure-20260910.md)及 #77 最终回写绑定，不循环写入本提交自身 SHA。历史失败/未执行记录原样保留。

# 当前适用范围更新

2026-09-10用户明确LibreOffice仅备用打开，不要求格式。以下行距FAIL保留为原要求下的测量诊断，**不再阻塞WP-A/Word格式验收**，无需为此补Linux格式验证。未把技术结果改为PASS。

# WP-A Windows LibreOffice 26.8.0.3 实测

本轮已完成九份原合成fixture的独立LibreOffice渲染：9 PDF、12页PNG。**按固定20pt行距要求，九份均FAIL**。
short/compact各1页、long各2页；long另记单页FAIL。不能以页数满足替代格式满足。

## 身份、环境及执行

- handoff_sha：`eb3504383023eac6f6c93d8769b6d273a55abd7f`；evidence_closure_sha=null（未提交）。
- 客户端：Windows 11 Pro 10.0.26200 x64，LibreOffice26.8.0.3，build `bce0998afefdbc355585ca324285661a2170ba77`。
- 运行时间UTC：2026-09-10T13:09:07.918425+00:00 至 2026-09-10T13:10:36.557682+00:00；详情environment.json/run.json。
- 调用已安装soffice.com，专属临时UserInstallation配置，headless writer_pdf_Export；未接管用户配置。
- 未实际观察LibreOffice原生打开警告/打印预览；本结论限实际引擎PDF渲染，不冒称原生UI或Linux验收。
- 宋体Version5.24、SHA256 `1526ac24375f51f6eb73bc2d3f8072dbe4a80a3a65217677c9d9a84f67dab2ab`；字体文件不入仓。
- 运行前后便携bundle校验均Verified37files；逐份input前后hash一致；没有修改输入、模板、字号、行距或产品代码。
- 源模板hash仍 `f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b`。

## 逐份结果

| 样本 | 输入SHA256 | PDF页数 | 字体 | 行距 | 固定结构/非空字符 | 结论 |
|---|---|---:|---|---|---|---|
| normal-compact-candidate.docx | `e6d7a4dbb44418e0078fdd2280fec89bb12f33c0c3aaec67235ab9d1821bb350` | 1 | 嵌入SimSun12/16pt | 实测16.9pt，FAIL | 完整/一致 | 行距FAIL；仅页数为1 |
| normal-five-long.docx | `9cd738dd630228f8d3b3c314742f7f62e16de498904a097407b52edef7597f4f` | 2 | 嵌入SimSun12/16pt | 实测16.9pt，FAIL | 完整/一致 | 行距FAIL；单页FAIL |
| normal-five-short.docx | `7eca517011011b5cb7c3b74d38756fdfef6da5f2a7df44503bceefdbd07593c9` | 1 | 嵌入SimSun12/16pt | 实测16.9pt，FAIL | 完整/一致 | 行距FAIL；仅页数为1 |
| preceding-sunday-six-long.docx | `ff6088b80654fbfdd096b233e995ef1394b9209ea50728ea9b21ce43a4f0c6d6` | 2 | 嵌入SimSun12/16pt | 实测16.9pt，FAIL | 完整/一致 | 行距FAIL；单页FAIL |
| preceding-sunday-six-short.docx | `78b7f8fdab2714a4cb4a5cacfaba55092229462653811ce66503d61e2ff1109a` | 1 | 嵌入SimSun12/16pt | 实测16.9pt，FAIL | 完整/一致 | 行距FAIL；仅页数为1 |
| saturday-compact-candidate.docx | `4286ee43ced4a9043231264851c75cb9b1ddf76594294f23a3ac9f85066b69b3` | 1 | 嵌入SimSun12/16pt | 实测16.9pt，FAIL | 完整/一致 | 行距FAIL；仅页数为1 |
| saturday-six-long.docx | `600fc88240d87d03854d4a51c4985b654fb606015dcb1a771f8947f78c74d374` | 2 | 嵌入SimSun12/16pt | 实测16.9pt，FAIL | 完整/一致 | 行距FAIL；单页FAIL |
| saturday-six-short.docx | `99bfb2d7be462be4353a5b54affddac60c4bd257040f4a6e237f5bbd58073259` | 1 | 嵌入SimSun12/16pt | 实测16.9pt，FAIL | 完整/一致 | 行距FAIL；仅页数为1 |
| sunday-compact-candidate.docx | `45b02145e835b27d54d2ed57aa3a8f2e57bbb13c335b1c0fadd2dcf69288d27a` | 1 | 嵌入SimSun12/16pt | 实测16.9pt，FAIL | 完整/一致 | 行距FAIL；仅页数为1 |

## 关键差异：输入固定20pt，输出连续行16.9pt

所有样本OOXML非空段落都是 `w:spacing line="400" lineRule="exact" before="0" after="0"`。
但各PDF“体能大循环”及随后集体/自主游戏连续行，连续三次基线差均16.9pt。
例如normal-five-short的y坐标212.35077、229.25079、246.15076、263.05078pt。
同输入Word PDF对应连续差约19.92–20.07pt。详见line-spacing.json，保留文本、坐标及Word对照。
本诊断证明至少这些正文行未满足固定20pt，不能推断整个文档每一处都统一16.9pt，也未确证LibreOffice内部原因。
未修改源文件或通过调字号/行距获得单页。首次对照脚本因Word行尾空格未匹配目标文本出现IndexError，
仅修正诊断文本strip后重读PDF，未重生成/覆盖渲染。

## 几何、文字与边界

- PDF A4纵向595.30396×841.88977pt；源11906×16838twips，边距左右720/上下284。
- 源单表9行，总宽10466twips；五天grid933/920/1722/1722/1723/1723/1723，六天933/920/1435/1435/1435/1436/1436/1436。
- 标题源16pt加粗居中，正文12pt，PDF非空文字嵌入SimSun12/16pt；空格字体按用户明确要求不限制。
- 体能大循环、集体2/自主1各3目标、区域1/目标3/指导3/材料、重点3/环境3/习惯3/家园1均保留。
- 全部PDF页合并非空字符多重集与输入一致；这不单独证明顺序/裁切，另由独立逐页视觉复核。
- 绘图边界x35.75–559.55pt，y14.2007–827.7007pt，均在纸张内；与早先本机Brother驱动记录可打印范围也相容，但未实际打印。
- 保留所有long第二页；LibreOffice分页位置与Word不同，不复用Word跨页描述。

## 门边界与下一步

> 历史口径（2026-09-10 21:16 回写时，早于21:24用户客户端决定）：下列“整体不关闭”、追查行距及补 Linux 格式验证的建议保留为当时记录，现不再作为 WP-A 阻塞或下一执行步骤。当前采用本文顶部范围更新及最终收口账本；技术 FAIL 不改写。

Windows LibreOffice稳定版渲染已实测，结果为行距FAIL；“仅已安装/未实测”状态被本轮结果替代。
Windows Word原有非空字体和原生观察结论不受影响；本轮无权改写历史Linux alpha证据。
`tasks.md`明确Windows Word和Linux LibreOffice分别验收：本次Windows LibreOffice不是Linux证据。
WP-A整体不关闭；正式模板资格、产品/云端、共享授权/来源接口均不由本次通过。

下一步提示词：在隔离候选中只读定位LibreOffice26.8.0.3导入固定20pt却渲染16.9pt的原因；保留本轮9PDF/12PNG失败证据，
不改原fixture、正式模板、字号或固定内容。若需要修改行距或产品契约，先停止报告。另在Ubuntu稳定LibreOffice上对同hash九份样本独立实测，
不能把本次Windows结果冒充Linux结果。

[完整证据目录](../validation/wp-a-libreoffice-windows-20260910-2108/README.md)；独立Review与manifest见同名附件。

## 独立Review完成

[独立Review](WP-A-LibreOffice-Windows-20260910-review.md)已复核全部12页并独立重算九份正文基线，确认行距FAIL。
未见裁切/溢出/正文丢失；五列long拆开“本周/重点”标签，六列long指导3句尾跨页，第二页续“的记录。”。
每次转换exit0但stderr均有 `Could not find platform independent libraries <prefix>`，原样保留于run.json，未归因为行距原因。

## GitHub回写

已回写[#77补充评论](https://github.com/ywyz/kindergartenManager/issues/77#issuecomment-5619295160)并通过API读回，归一化CRLF/LF后正文一致；首次未归一化比较失败，仅换行差异。未关闭Issue。证据目前本地未提交，closure_sha仍null。
