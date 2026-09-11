> 2026-09-11 WP-D 已按用户授权进入实现：日期投影、显式 v3 正文、分项生成与确认/CAS 应用闭环已接线。最终范围、代码 SHA、验证与剩余门只以[当前状态](current-status.md)及[WP-D 矩阵](WP-D-completion-contract.md)为准。下方 WP-C / WP-D 未启动措辞为历史时点，不表示当前执行状态；WP-C 四项历史过程缺口仍未满足。

> 2026-09-11 WP-C完整协作路径已实现；[关闭矩阵](WP-C-completion-contract.md)、[本轮证据](evidence/WP-C-complete-20260911.md)与[当前状态](current-status.md)说明实际覆盖和未完成门。历史阶段描述不代表当前实现缺项。

> 当前入口（2026-09-11本地交付）：[状态与证据边界](current-status.md)；[WP-C本轮证据](evidence/WP-C-complete-20260911.md)。下方阶段快照按记录时点解释。

> 2026-09-10 最终收口口径：WP-A 实现基线、契约与最短完整 Word 五／六列单页可行性完成；long 三份仍为两页。共享业务实现、正式模板资格、缩减流程和产品/云端验收属于后续门。最终独立复审、提交与 exact-SHA CI 的关闭绑定见[收口账本](evidence/WP-A-closure-20260910.md)及其 Issue 回写；未完成 CI 时不得据此宣布正式关闭。

# 周计划阶段资料与Windows交接

本目录于2026-09-10汇总到`handoff/wp-a-windows-20260910`分支，供Windows拉取。
该分支继承WP-B `41b63c9cf6492d31c91faa07bd021e4096eb5379`及WP-C身份子步
`00afdc878b306475508c777997956cdf4638dbef`，汇入最新WP-A/B/C未提交设计和交付资料。
历史账本中“尚未提交/无可访问链接”描述当时状态，保留原文，不据本次同步改写历史证据或CI结论。

**历史Windows交接任务入口：[WP-A-Windows-validation-prompt.md](WP-A-Windows-validation-prompt.md)。**

- [可携带的九份合成样本及Linux参照](validation/wp-a-simsun-20260909/README.md)
- [WP-A宋体/Office历史边界](evidence/WP-A-fonts-20260909.md)
- [WP-B交付](evidence/WP-B-20260910.md)
- [WP-C身份子步及尚缺接口](evidence/WP-C-20260910.md)
- [Windows之后的WP-C下一小步](WP-C-next-prompt.md)

同步仅提交既有代码/最新项目文档和必要合成QA材料；不包含字体二进制、密钥、数据库、业务导出、
运行缓存或机器配置。原工作区及WP-A/B/C工作树全部保留，main未合并，不创建PR或发布部署。
源模板/产品代码在本次交接未更改；新增的校验脚本仅计算样本文件完整性。
外部Linux运行目录的历史日志/运维脚本仍是历史本地路径，Windows任务使用本目录自带材料，
不依赖重新执行那些Linux命令。没有因为上传历史材料产生新的Office/云端/Quality PASS。

## WP-D 提示词续审（仅文档）

[修订提示词](WP-D-next-prompt.md)与[本轮核对记录](evidence/WP-D-prompt-revision-20260911.md)已更新。WP-D 尚未执行；四类历史 RED 缺口未豁免，外部 preservation-final.json 与原清单哈希不一致另列执行前待核查。后续按 WP-D → WP-E → WP-F 交接，本轮仅本地文档同步。
