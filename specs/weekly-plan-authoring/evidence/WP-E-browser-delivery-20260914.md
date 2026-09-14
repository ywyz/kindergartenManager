# WP-E 本轮浏览器验证与分支交付

本轮本地页面流程通过：五列、六列修改保存与浏览器 DOCX 收件，以及长文超页拒绝→教师手动缩短→保存→重检→收件。使用 LibreOffice；自动缩减完善及验收延期，Windows SKIPPED_BY_USER。云端新镜像/部署/业务验收尚未执行，WP-E整体仍OPEN。

## 代码和运行边界

验证对象为基线 `c69b9e4435c0a70c4801836cb3d901728216af0e` 上的本轮工作树，包含 LO authority 适配。authority SHA256 `ce006dbc80ab226c462f40f4bda0ebaec7ae3334b6ac2d7e89a3bd0caf5f7ab0`，测试文件 SHA256 `793dc2e94eca44bbcdd344679e92bcd4ec809249cf2d840fec0d3fdc940f2cbd`，与既有48项测试和2项集成通过记录一致；未重跑全套。提交后的源码身份另在外部 delivery.json 记录。

工作树 `/home/ywyz/code/km-wpe-libreoffice-20260914`；真实Chrome通过CUA操作 `http://127.0.0.1:18777`。新0700数据目录 `/tmp/wp-e-browser-data-20260914`，SQLite经Alembic迁移，租户11，合成教师 synthetic3。普通layout_startup加载已审阅LO catalog，`local_only=False`，四项运维输入完整，manifest预期 SHA256 `ddf9c3d54a64f8ee75e7cf312ea99750640ca2caa8933085c2ca75a601de0faf`。没有替换authority或renderer；AI边界为隔离mock，本轮未调用生成或自动缩减。不是MySQL、真实AI或云端证据。

## 页面观察

1. 真实登录后进入每周工作计划；五列日期2026-09-14至18，修改本周重点为“观察春天”，出现“草稿已保存”，实际单页检测通过，页数1，点击导出。浏览器下载目录收到DOCX且OOXML含该保存文本。
2. 在同一五列计划输入合法长文：家园共育396字，六个重点/环境栏目各154字且内容不重复；保存版本15后检测明确显示页数2和“不交付文件”。点击导出得到“请先检测已保存版本，检测通过后才能导出”，导出审计中无版本15授权记录。
3. 在真实页面手动将上述六栏改为“手动调整1”至“手动调整6”，家园共育改为“亲子观察并交流发现。”；保存版本16，重检页数1，点击导出，浏览器下载文件包含新文本。未采用历史候选。
4. 六列日期2026-09-20至25，页面显示周日至周五六个日期；本周重点改为“六列保存验证”，保存版本17，实际单页检测页数1，浏览器收到DOCX且包含保存文本。五列DOCX表格grid为7（含标签列），六列为8。

初次过长字段超过160字符上限、一次相同条目违反不重复约束，均保存拒绝，未当作排版超页。调整为契约内不同条目后执行上述长文链路。

## 浏览器收件证据

Chrome内部下载页受浏览器工具URL策略禁止，未绕过。受支持download事件监听一次15秒超时，但下载文件实际落盘；最终以页面点击之后出现在用户系统下载目录的真实文件、时间、大小、SHA256和OOXML内容证明收件，不用服务返回bytes替代。收件文件未由脚本创建或复制。五列为核实事件重新检查并导出了一次，保留两份文件。

| 浏览器下载文件（位于 `/home/ywyz/下载`） | bytes | SHA256 |
|---|---:|---|
| `周计划-2026-09-14 (3).docx` | 17508 | `245be9ef68148453c5e8b7bbea7b8773e0b8a89e1317a961197ae8bd14066cb5` |
| `周计划-2026-09-14 (2).docx` | 17472 | `5e2eb36e4d583f77f44cb0e15a758f8cf3993f20163a935d11db13ae57690ac7` |
| `周计划-2026-09-14 (1).docx` | 17472 | `22363bca83674e2b0222628ea5ef4b224a8e9dbdcecc0d115a19d0e726f60305` |
| `周计划-2026-09-20 (1).docx` | 17527 | `d6120e95ac0f7f6f039bcb564c937dbc9e77941b5df3c7c40b53cdd06432eeed` |

导出授权审计共4条：plan2/version13两次、plan2/version16一次、plan3/version17一次；审计授权本身不代表收件，文件证据单独核实。原始记录位于 `/home/ywyz/code/wp-e-browser-delivery-20260914/`：`download-receipts.json`、`browser-export-audit.json`、`browser-fixture-20260914.json`、`main-browser-server.log`、`opencode.jsonl`、`preservation.json`。启动包装的环境失败及短暂进程终止保留，最终由Main持续session成功运行。

## 交付边界

OpenCode仅同步文档，Main审查实际diff并执行页面操作；子代理准备隔离数据、只读核对云端准备。主仓库原三份修改保留。页面通过后按用户授权提交当前分支并推送；不创建PR、合并、发布或生产部署。远端CI结果必须绑定新提交SHA，外部delivery.json记录。历史基线CI run34787949329因缺宋体失败，不代表本轮新SHA结果。
