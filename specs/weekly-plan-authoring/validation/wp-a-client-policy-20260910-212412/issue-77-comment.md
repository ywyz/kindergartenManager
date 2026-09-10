WP-A验收范围更新（2026-09-10，用户明确决定；承接上一条Office实测回写）：

用户确认存在系统差异，LibreOffice只作备用打开软件，不对文档格式作要求，主要使用Microsoft Word系列软件。此前已明确空格字体无需宋体。

据此，本周计划的LibreOffice（含Linux）格式通过不再作为阻塞条件。上一条Windows LibreOffice实测的16.9pt行距、long两页及导出warning均保留为真实诊断，不将其技术结果改成PASS，也不再要求为本门追查或补Linux格式实测。

Windows Word365 16.0.20326.20132 x64的最短完整五天、前置周日六天、周六六天均满足单页、宋体12pt及固定20pt；原生只读打开/全部打印预览与独立Review已完成。WP-A最短完整排版可行性条件已满足，原LibreOffice格式阻塞解除，tasks对应两项勾选。

三份long在Word仍为2页，单页FAIL保留；compact只作合成候选。不能外推所有长度、所有Word系列版本、正式模板资格或产品/云端验收。正式exporter/云端受控渲染实现仍属后续门。

已同步spec/tasks/ADR-0011、当前证据及CONTEXT/ROADMAP历史指针。handoff_sha仍eb3504383023eac6f6c93d8769b6d273a55abd7f，证据尚未提交，evidence_closure_sha=null。输入/历史渲染与产品源码未改；未迁移、部署、创建PR或关闭#77/#57/#75。

可以保全证据后切回Ubuntu，按另行授权的WP-C-next-prompt推进下一小步；不再为LibreOffice格式一致性阻塞开发。
