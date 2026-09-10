# WP-C 授权/事实：独立只读 Review

Main记录实际reviewer `docs_review` 返回；不递归、不修改代码，不以Main测试冒充独立运行。

1. 设计审查：确认旧PlanAuthorizationRequest绑定legacy根/version，不能伪造复用；新应用须走真实
   IdentityApplication事务及同一数据库policy。支持先完整读取/校验真实事实、最终许可尚未启用的安全基线，
   双RED后启用许可；拒绝以缺接口、import错误或假授权替代业务RED。
2. 中间SQLite独立实跑45 passed/2 failed：其他学期前置调休周日漏冲突；当前assignment未重验完整学期范围。
   与Main已捕获的边界缺陷相同，Main快照+连续双RED后最小修正；reviewer确认修正落点。
3. 修正后独立47 passed，未发现新实质缺陷。建议补真实锁定日历中的补班周末，Main随后增加真实9/20及10/10等覆盖。
4. **最终代码SHA `59677fc656bab152485c0355f3470f5763951888`**：独立核对12个代码/依赖/测试改动路径，
   parent为718b26c，diff whitespace通过。独立复跑共享授权、身份和迁移专项 **66 passed in 11.71s**。
   专属设置目录`/home/ywyz/.km-wpc-review-20260910/docs-review-20260911`（0700）。
   初次尝试位于.codex下的目录被安全祖先检查拒绝，不计业务结果；改用上述安全目录后取得实际结果。

审查覆盖：真实session/jti/auth_epoch/role、tenant/class/semester、部分周/零交集、真实/合成日历、
完整窗口/七列/未知年/跨学期、当前任职/撤销/新assignment与旧stamp、指纹漂移、await过期、
双向撤销排序、关闭DTO/production builder/隔离级别观察和无正文写入；legacy policy无caller discriminator绕过。

最终无新实质代码finding。Reviewer没有重复MySQL、全库、legacy或Foundation，相关数字属于Main证据。
没有root、不可变共享版本/CAS、source、UI、模板资格或最终下载验证，不能称整个WP-C或产品Review通过。
文档收口复核另由后续追加记录，不冒称本页文字已包含在代码SHA。

## 最后文档与回写核对

Reviewer只读检查实际交付文档、下一根提示词及#77拟回写，未重复产品测试。发现一处政策前置条件
表述省略：先检查同actor/class/semester任一当前有效assignment完整范围位于实际学期，矛盾则拒绝，
再判至少一天实际教学日交集。Main已在冻结契约和拟回写补全，未改产品代码或测试。
其余本地SHA/CI范围、346/1旧兼容失败、root/source/WP-D边界及Word/LibreOffice历史结果无实质矛盾。
