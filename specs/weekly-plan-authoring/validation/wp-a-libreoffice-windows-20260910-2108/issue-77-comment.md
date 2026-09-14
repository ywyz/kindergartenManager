WP-A Windows Office 实测补充（2026-09-10）：保留失败，不关闭Issue。

handoff_sha=`eb3504383023eac6f6c93d8769b6d273a55abd7f`；本轮证据尚未提交，evidence_closure_sha=null。输入采用交接的九份同SHA256合成fixture，运行前后verify_wp_a_bundle均Verified37files，九份input及正式模板hash未变。未修改产品/模板/exporter、未迁移或部署。

Windows Word365 16.0.20326.20132 x64：9PDF/12页PNG；原生工具恢复后补齐9份只读打开+12页打印预览共21截图，独立逐张Review。未见可见修复/兼容警告或裁切。用户明确空格无需宋体，非空正文SimSun12pt/标题16pt的字体项通过。short/compact各1页，long各2页，长文单页FAIL保留。

新增Windows LibreOffice26.8.0.3，build bce0998afefdbc355585ca324285661a2170ba77，专属UserInstallation配置，headless实际导出9PDF/12PNG并独立逐页Review：
- 六份short/compact各1页，三份long各2页。
- 可见文字嵌入SimSun12/16pt，固定数量完整，非空字符多重集一致，未见裁切或丢失。
- 关键FAIL：九份所检查连续正文行基线都是16.9pt，源XML固定20pt；Word对照约19.92–20.07pt。故九份LibreOffice均行距FAIL，不能用一页结果授予布局PASS。
- 五列long“本周/重点”标签拆页；六列long区域指导3句尾跨页，第二页续“的记录。”；完整保留第二页。
- 每次转换exit0，但stderr有Could not find platform independent libraries <prefix>，保留原记录，不推断与行距有因果关系。

本地账本：specs/weekly-plan-authoring/evidence/WP-A-Windows-20260910.md及WP-A-LibreOffice-Windows-20260910.md，各附review/manifest。新渲染目录validation/wp-a-libreoffice-windows-20260910-2108/；原始二进制证据目前仅本地，未宣称已上传GitHub。

边界：本次是Windows LibreOffice headless渲染，未观察其原生警告/预览；tasks.md要求的Linux稳定LibreOffice独立门仍未取得，历史LibreOfficeDev26.8 alpha不能替代。WP-A不关闭，正式模板资格/产品云端/共享来源均未由本轮通过。CI沿用先前实际handoff SHA的Quality failure记录，没有新增CI成功主张。

下一步先保留本轮失败，在隔离候选中定位固定20pt在LibreOffice输出16.9pt的原因；不改原fixture、字号、固定数量或产品契约。可切回Ubuntu完成稳定LibreOffice独立实测，或另按WP-C-next-prompt推进已另行授权的小步，不以切换平台冒充WP-A关闭。不关闭#77/#57/#75，不创建PR。
