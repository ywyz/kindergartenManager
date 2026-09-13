# WP-E Windows 独立只读初审 — 2026-09-13

审查人：本轮独立 readonly_review agent。范围：现行契约、工作树/产品绑定及历史材料字节完整性；未控制 Word，未把历史截图当作本轮新观察，未运行产品测试、访问远端或修改历史材料。

## 当前基线

- 隔离工作树：`C:/Users/admin/.codex/visualizations/2026/09/12/01a0937c-3f64-7ce2-98f9-fecd1934901c/wp-e-windows-84f189f`。
- 分支 `codex/wp-e-windows-holiday-20260912`，HEAD `247fc3472481bcdc7b161b36301e08f205da9c71`。
- 对产品 `0bded3377c01956833bcbb6cd306f9a7f5d924e1` 的 tracked diff 仅四份文档：current-status、WP-E-dedup-recheck、WP-E-header-week、WP-E-native-Word。无产品 tracked diff。
- 工作树有两份未跟踪续作提示词（Windows-Ubuntu 与 Windows-only），保留。main worktree 仍在 `8dcc833`；不推断远端具有本地提交。
- 已读取实际分支 AGENTS.md、ADR-0011、spec §2.2–2.7、tasks WP-E/F、WP-E-local-contract，以及两份指定 20260912 原生/去重证据。

## 独立完整性结果

| 材料 | 本轮只读结果 | 证明边界 |
|---|---|---|
| handoff verify_bundle.py | `INTEGRITY_OK: 26 files; not Word or WP-E PASS` | 原清单不变；不含新 DOCX/截图，也不代表完整外部包 |
| 8 原始候选 body | 8/8 SHA256 一致 | 合成输入字节绑定 |
| 8 原始候选 DOCX | 8/8 SHA256 一致 | 原始输出字节绑定 |
| native-final 历史清单 | 49/49 大小及 SHA256 一致 | 不等于本轮原生格式重验 |
| reduction 历史清单 | 34/38 大小及 SHA256 一致，4 项缺失 | 保留原 38 项范围，不能改写为 38/38 |
| 4 accepted body / DOCX | 各 4/4 与 adoption-save-receipt SHA256 一致 | 本地合成文件采用保存，不是产品数据库保存 |

Renderer `app/integration/word_export/shared_weekly_word.py` 当前 SHA256 为 `6186fd0bc62ca8a31af2236645d22d07e7fbe8ee4a53069181b78638ba0240f7`；seed `templates/weekplan.docx` 为 `f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b`，均与候选 manifest 和去重 receipt 一致。候选 manifest、receipt 均声明上述产品 SHA。

历史 native-final 清单 SHA256：`e5b5062431403bd8a4830171eeeb0010fcb3ead2b800d3ccdda78cc6c7e65cf5`。
历史 reduction 清单 SHA256：`8b87ea32750bbbacc432c1bc2202bf89ea584b4107af10035183f5afa4f6c103`。

缺失项（按原清单精确保留）：

- `accepted-files/~$ve-holiday-long-dedup.docx`
- `accepted-files/~$ve-long-dedup.docx`
- `accepted-files/~$x-saturday-long-dedup.docx`
- `accepted-files/~$x-sunday-long-dedup.docx`

这些名称是 Word 临时 owner/锁文件形式；仅报告本轮缺失，不从名称推定确切删除原因或时点。实际 accepted DOCX/body 全部仍匹配。历史文档写作时的 38/38 是历史记录；本轮必须并列报告 34/38，不篡改历史清单或补造临时文件。

初次 PowerShell Get-FileHash 读取 five-normal.docx 因当前 Word 共享锁失败；随后使用 FileAccess.Read + FileShare.ReadWrite 完成全部 8+4 DOCX/body 核对，匹配。读取错误不是文件漂移或业务 RED。默认 python 不在 PATH；改用受支持 bundled Python 执行原 verify_bundle.py 成功，此环境错误同样不是 RED。

## 契约判断与待复审范围

1. 当前授权足以继续四份可容纳正常输入的原生格式补验。Windows Server 名称、Ubuntu 测试站、真实模型/数据库及云端资格缺失都不是这次候选格式补验的前置阻塞。
2. 正常四份历史结果是 A4 一页、格式 PARTIAL。整体行距混合必须定位正文/空段落/合并格结构，不得认定或忽略缺陷；单份所选正文宋体小四及局部固定20pt不能外推四份全体。
3. 需要逐文件原生属性与足够倍率全部文字/边界检查，覆盖标题、主题、班级后周次和日期、空左上角、星期无日期、多姓名/空格/书名号、固定栏/游戏/目标/总结数量、假期空活动与无残留。50%全页或机器解析不能替代。
4. 原四份长文与已采用四份去重均保留各两页 FAIL；历史三 long 与 compact 状态不变。当前规范允许无法收敛后提示手改，因此两页不单独证明 renderer 缺陷。此次没有新的修订成功例。
5. 新手改须具体差异和明确采用；已有去重确认只绑定原提案，不重复要求也不扩大。不能把文件保存或截图说成数据库保存、真实模型调用或应用拒绝下载行为验收。
6. 当前 released/catalog 资格仍未核实，候选通过最多表述为当前产品 SHA/实际 Word 客户端的候选格式验收。WP-C 四类历史 native 双 RED UNMET，WP-E 总门未关闭，WP-F NOT_RUN。
7. 本报告只完成初始证据/契约复审；新增原生截图、实际 Word 客户端版本和逐项最终矩阵仍待独立复审。无新产品缺陷结论，无正式 Word 或 WP-E PASS 结论。

## five-normal OOXML 定位附录（非原生验收）

按原字节只读解析 `word/document.xml`，共定位 37 个正文层/表格段落；35 个显式 `lineRule=exact, line=400`（20pt）。仅以下两个空段落没有显式 spacing：

- `body/child[4]/tbl/tr[3]/tc[1]/p[1]`：vMerge continuation 空段落。
- `body/child[4]/tbl/tr[5]/tc[1]/p[1]`：vMerge continuation 空段落。

未见表格后独立正文空段落。完整位置及原文见同目录 `five-normal-ooxml-paragraph-diagnostic.json`。这提供原生定位混合行距的线索，不能证明 Word 的实际继承值、可见正文属性或将整体混合判为缺陷/通过；仍须在原生 Word 区分上述合并结构与可见正文。
