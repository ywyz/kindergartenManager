# WP-D 提示词评估与线上 Bug 登记（2026-09-11）

本轮范围：评估提示词、补强文档、登记两个用户报告的 Bug，并按用户后续明确授权连同已有 WP-C 提交推送 `feat/wp-c-complete-20260911`；不合并 main。未实施 WP-D，未修复或登录生产诊断 Bug。

## 判断

原提示词不足以确保完整交付 WP-D。Main 对照 spec/tasks/calendar/service 契约检查，独立只读 reviewer 得到相同结论。基线为 `3f62231e8950cfe4e692fc6993007b746328c45d`；审查不改变 WP-C 的 tested_code_sha 或原有测试结论。

| 缺口 | 规格依据 | 本轮补强 |
|---|---|---|
| WP-C 未满足前置的处置含混 | current-status.md；WP-C-complete-20260911.md 历史 RED 限制 | 不补造或自动豁免；先明确处置再开始依赖实现 |
| 固定数量/空草稿边界抽象 | spec.md §2.3–2.6；service-contract.md | 游戏、区域、四类总结精确数量；空 slot 草稿与完整结果分开校验 |
| 日期/假期规则不够确定 | calendar-contract.md；spec.md §2.2 | 掩码先行、可见段首标名、寒暑假优先、冲突零写入、日历版本 |
| AI 应用闭环及版本绑定不足 | service-contract.md；spec.md §2.6 | 真实入口连通、actor 配置、prompt 版本、差异确认/保存重载 |
| 整门结束条件不明确 | tasks.md WP-D；现行证据规则 | 完整需求矩阵、两库/独立复审/精确 SHA 与未完成判定 |

修订见 [WP-D-next-prompt.md](../WP-D-next-prompt.md)。补强提高完整性与可验收性，但提示词无法保证执行成功；尤其 WP-C 四项历史原生 RED 证据缺口仍在，本轮没有豁免。WP-E/WP-F、正式导出、云端/Word 与发布门继续独立。

## Bug 登记

- [#80 Agent 运行时提示“关闭契约失败”，实际错误未知](https://github.com/ywyz/kindergartenManager/issues/80)。按用户原话记录，UI 原文与底层错误待核对。
- [#81 游戏观察记录已上传照片却仍提示未上传](https://github.com/ywyz/kindergartenManager/issues/81)。上传状态、触发步骤、关联/重载行为待复现。

两项均标记 bug，分别记录症状、预期、待补证据、排查范围和验收条件；根因、频率与实际部署 SHA 未知。不把用户报告写成已复现，也不把登记写成修复。

## 验证与同步边界

本轮仅修改文档，执行 diff 检查、文档相对链接检查和 Issue 正文读回比对，不重跑历史产品测试。Git 推送及远端分支 SHA 校验单独报告；推送不是 CI、合并或部署通过。原工作区未提交材料继续保留。

独立复审对修订提出一项来源措辞问题：四类周总结按规格由 AI 生成，不应与游戏/区域混写为来源优先。Main 已分开表述。两项 Issue 已读回，均为 OPEN，正文与提交内容经换行规范化后完全一致。
