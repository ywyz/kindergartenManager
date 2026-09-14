# WP-E 需求验收矩阵（本地已执行，长文采用待用户答复）

测试输入均为合成数据。初次已通过覆盖与本轮几何缺陷双RED独立记账；不存在用测试数量替代条目覆盖的结论。Widget shim回调测试不能称浏览器。tested_code_sha=0b3656c919ddfe6f09db4ed0aa0732a828727a5c。浏览器角色为真实app.main+合成SQLite+mock AI；成功渲染/下载使用local_only合成资格，不是正式资格。

| 需求 | 真实应用/自动化入口 | 已取得证据角色 | 浏览器观察 |
|---|---|---|---|
| 五列/前置周日六列/周六六列/假期 | calendar_application、test_wpe_word_layout、shared_weekly_plan | 当前日期事实及OOXML固定结构；实际renderer复验完成 | 已实际载入四种页面；前置周日与周六六列，国庆节字段禁用；五列/周日前置六列成功下载 |
| 零/一/多来源及明确选择 | source_application、test_wpc_collaboration::test_full_import_manual_check_cancel_reimport_history | 两库真实会话+应用+映射+不可变历史 | 周一零、周二一、周三双教师重复；明确选甲/乙来源后比较差异并采用，活动名称NULL保持待手填 |
| 同班共享/人员不覆盖/最后编辑者 | test_wpc_collaboration::test_shared_people_defaults_initialization_and_history；test_wpe_ui_callbacks | 两库应用+UI回调（shim不是浏览器） | 甲/乙实际登录；乙保存后甲重载读到乙编辑者与同一正文；人员未操作 |
| 生成缺项/指定重生成/名称手填/固定条数 | authoring_application、test_wpd_concurrency、test_wpe_ui_callbacks | mock AI隔离边界，真实应用契约 | 名称手填；三条缺项候选拒绝后空值保持，再生成采用仍未保存；单字段重生成仅一差异，拒绝保持。首个单字段候选因重复值被拒绝，未冒称成功 |
| 拒绝/取消/TTL/来源/授权/版本/提示词失效 | test_wpd_concurrency参数化漂移与one_shot | SQLite/MySQL当前覆盖，不是历史RED | 拒绝与取消生成实际通过；TTL/来源/授权/版本/提示词漂移是两库自动化，浏览器未注入 |
| 采用仅内存/显式保存/revision/快照重载 | test_wpe_reduction_application::test_explicit_difference_reject_adopt_save_preserves_history | 两库真实应用、旧版本/源/人员hash保持 | 实际导入+生成采用显示未保存；显式保存root1 revision2→3；甲真实重载；旧12版本及3日计划hash保持 |
| 双教师CAS一成一败 | test_wpc_shared_root及test_wpd_concurrency | SQLite当前全量；MySQL适用并发104集 | 实际甲保存revision3→4成功，乙旧版本被拒且保留输入；明确放弃并重载后见甲成功主题 |
| 默认资格拒绝 | app.main→configure_shared_weekly_production默认空authority | 直接resolve_binding=qualification_required；不是超页检测 | 默认127.0.0.1:18777真实登录/页面检查显示正式模板五/六列Word资格未完成 |
| 保存快照真实检查/成功下载 | test_wpe_render_pipeline::test_saved_actual_renderer_delivery_no_new_version | 双DB各连续2RED已固定，双DB GREEN；实际LO+local-synthetic authority | 正常五列2026-09-14/六列2026-09-20已实际收到下载目录DOCX；版本不增加，ExportRecord=0；缺项保存快照被拒 |
| 真实超页→有限缩减→差异→采用→保存→重检 | test_wpe_render_pipeline::test_actual_overflow_explicit_reduction_save_recheck | 真实LO、mock AI、应用保存；新合成正文 | 合成长文实际LO2页拒绝→首轮26字段可见差异；新正文采用待用户明确答复，尚未改写/保存 |
| 仍超页保留正文/禁止下载 | test_wpe_reduction_application与render_pipeline | 两库限制/失败计数，实际LO已复验；历史八长文2页FAIL保持 | 浏览器合成长文2页显示不交付；未采用仍原revision2；自动化已覆盖缩减后仍超页拒绝 |
| actor/session/member撤销/双CAS/模板源漂移 | test_wpe_export_application、test_wpd_concurrency | 两库真实事务+可控等待/故障注入；不声称浏览器故障演练 | 浏览器双教师CAS已运行；其他撤销/漂移按两库自动化记录，未做浏览器故障注入 |
| unflushed输入/取消/replay/commit_unknown只读对账 | test_wpe_ui_callbacks、test_wpe_export_application及reduction_application | 真应用和shim回调区分；无重发保存/下载断言 | 手填后检查提示先保存；生成等待期间取消显示正文保持；replay/unknown只读对账为自动化覆盖，浏览器未注入 |
| 生产Word资格/新SHA原生Word/真实AI/云端/新远端CI | 严格独立外部门 | NOT_VERIFIED/NOT_RUN，本轮无相应授权或材料 | NOT_RUN |
