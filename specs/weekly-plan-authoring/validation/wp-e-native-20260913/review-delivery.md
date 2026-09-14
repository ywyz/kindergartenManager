# Windows 候选格式交付独立只读复审 — 2026-09-13

结论：本次交付文字和矩阵可接受，未发现尚需修订的阻断项。支持四份正常输入在当前产品SHA/客户端下的候选格式PASS；不支持正式模板资格、Windows全部资格或WP-E总门关闭。

## 本次独立检查

- 阅读Windows-acceptance-report.md、windows-matrix.json、integrity-final.json、git-final.json、build_delivery.py、seal_evidence.py；结合本审查者此前逐件原始PNG、属性选区、输入JSON及补证复审。重新核对实际隔离分支spec.md §§2.2–2.7相关内容及tasks.md WP-E/F，特别正文12pt/20pt、表头新位置、五六列、固定条数、超页保留调整与正式绑定的区别。
- 独立重新计算19项输入/原始输出/manifest/renderer/seed hash，全匹配；独立核对两份历史清单自身hash及每一现存成员hash，49项49 MATCH，38项34 MATCH+4 MISSING、0 MISMATCH。缺失项仍为原清单四个Word临时锁文件，未縮小38范围，未重造文件。
- 26文件bundle的本轮实际执行和最初独立运行均为INTEGRITY_OK: 26 files; not Word or WP-E PASS；报告正确说明其不含新DOCX/截图，也非全部外部包。
- 正常矩阵的全部证据JSON、JSON所引PNG及独立复审文件均实际存在。四份分别有36、24、26、29个JSON/复审引用（此数字是引用计数，非完整证据清单范围）。四份原件hash与manifest绑定；环境保留账户与关于各自build，不合并或外推。
- 重新读取历史native-matrix.json确认四份原始长文在产品SHA 0bded3377c01956833bcbb6cd306f9a7f5d924e1下各2页、all-pages observed、single-page FAIL；与当前矩阵hash一致。四份已采用去重长文从原native-recheck保留各2页FAIL和采用hash，未伪称本轮重观或完整格式通过。
- 实时只读Git确认隔离HEAD 247fc3472481bcdc7b161b36301e08f205da9c71，相对产品SHA仅四个既有文档变化；两个未跟踪提示词仍保留。git-final另记录main HEAD 8dcc833及其未跟踪文件，不假定远端含本地提交。

## 范围与限制复核

正常四件的PASS只限合成候选、当前SHA/客户端。five-normal的range-c仅区域标签与四总结正文，再补area、game总标签及四总结标签；其他三件五组逐文件范围及字体证据均有独立支撑。整体混合行距、末端空位置单倍、five-holiday排除末端仍混合、隐藏合并结构未作原生统一20pt断言均在报告保留。没有从OOXML认定原生末端结构或用混合属性直接宣布正文失败。

细字和边界的组合证据支持最终正常格式结论；报告没有声称每一PNG的每条细线都清晰，也未把字体对话框样式匹配提示改成字体缺失。所有候选原始文件未改，未建立业务RED，未以长文超页为由修代码。报告对原始/去重八个长文FAIL、历史三长文/compact状态、新修订成功例NOT_RUN均分开记载。

spec §2.7允许仍不满足时提示调整；因此新修订成功例没有被强行补写或由去重两页升级。应用拒绝下载、真实模型、产品保存版本、正式catalog资格、Ubuntu页面、CI/OCI/迁移部署均在后续门；本轮本地文件保存不冒充应用数据库版本。WP-C历史native双RED仍UNMET、WP-E仍OPEN、WP-F NOT_RUN，未提前生成WP-F-next-prompt或发布。

## 已关闭的交付歧义

初稿original_long_cases复制candidate manifest的native_status=NOT_RUN，与历史2页FAIL并列易误读。已反馈给主操作agent，由其修改build_delivery.py和新矩阵。本审查重新确认四件现均为candidate_manifest_native_status=NOT_RUN、native_status=FAIL_SINGLE_PAGE_HISTORICAL、this_batch_native_observation=NOT_RUN；历史原件未修改。此项已闭合，不是产品缺陷或业务RED。

## 新证据封存边界

seal_evidence.py只封存今日目录直接文件、排除自身输出清单，包含脚本和本报告；明确原DOCX仍在矩阵绑定路径，历史26/49/38范围不变。已有清单时仅校验集合/size/hash，不重写清单；首次封存前要求本报告存在并检查观察JSON的PNG引用。静态审查未见范围偷换。

本报告生成时新delivery-evidence-manifest.json尚待主操作agent生成及再次校验，因此这里不伪报最终封存成功或其文件数。该最后完整性步骤不改变本报告关于原生候选格式的结论；执行结果应随最终交付返回。审查者未修改其他交付文件、历史证据或产品代码，未控制Word或执行远端操作。
