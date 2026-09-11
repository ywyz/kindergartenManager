# WP-D 提示词只读审查与修订（2026-09-11）

本轮授权仅审查/修订提示词并同步本地仓库；未启动 WP-D，未发送 Issue 消息或执行远端写入。

- WP-C 源工作区：`/home/ywyz/code/km-wpc-complete-20260911`；分支 `feat/wp-c-complete-20260911`，检查时干净。
- tested_code_sha：`6352bf60d59abc1bd836a476f0eb94e9f48fb479`。
- 文档后继：`6e766d76926e77ef6f9945c9a091f431ca6c6b28`；祖先检查退出 0，差异仅文档。
- 源隔离 `.venv` 当前安装 `chinesecalendar 1.11.0`；未升级依赖，未来执行仍须核对完整候选日期窗口的支持年份。
- `.venv/bin/alembic heads`：`b153c7e9f026 (head)`；未连接或迁移业务数据库。
- 新隔离分支：`docs/wp-d-prompt-review-20260911`，目录 `/home/ywyz/code/km-wpd-prompt-review-20260911`，从上述文档后继建立；无手工跨工作区复制。修改前提示词与源文件 SHA-256 一致。
- 原主工作区仍有 CONTEXT/ROADMAP/design/memory-bank、graphify cache 修改及未跟踪 weekly-plan-authoring 材料；本轮不改动或提交它们。

## 证据完整性核查

已读取当前状态、完整关闭矩阵、WP-C 完整账本与独立 Review、最终 JSON 清单，以及 ADR-0011、spec §2.2–2.6、tasks、calendar/service/migration 契约。
用 Python hashlib 逐项检查清单全部 178 份 artifact：177 一致，1 不一致。46 个 changed_python_sha256 文件全部一致。此检查仅验证现有材料哈希，不是重跑历史测试。

`preservation-final.json`：

- 清单预期 SHA-256：`70da580b3ea3a5329d17f461ff192c39def8f4ff03fee079b69495d520fdff5c`。
- 当前实际 SHA-256：`3f3adfc4ca8debe0c1f7faaa371bdefc215ce35ab7cf106754d3290d4e0153f0`。
- 原始文件路径：`/home/ywyz/code/km-wpc-complete-evidence-20260911/preservation-final.json`。

未改写原 manifest 或原文件。差异来源/时序与保全影响尚未核查，列为执行前证据完整性待处置项；不能据此宣称原材料破坏或当前代码有缺陷。四类修复前 native 双 RED 历史缺口仍需决定者明确处置，后验重放不能修复顺序。

## 本轮修订

保留原提示词所有业务约束；补入精确基线、历史缺口逐项处置、新完整性差异、矩阵字段、假期完整文案、表头/日期一致性、数值预算、生成/重生成区别、候选生命周期与来源保存边界；明确可委派但 reviewer 只读不递归。将 WD-F 解释为 WP-F 最终目标，要求 WP-D → WP-E → WP-F 按实际关闭证据交接。仓库同步限定本轮本地文档提交。

本轮未重新运行产品测试、两库迁移、真实 AI、CI 或云端/Word；这些结果不由文档审查继承。文档链接与 git diff --check 在提交前核对。

## 本轮验证与独立审查

Main：四份文档的本地链接存在性检查通过，git diff --check 通过；未运行产品测试。独立只读 reviewer `prompt_review` 审查四份文档与阶段边界，未发现阻止性问题，并独立复核 diff --check；未修改文件、未递归委派、未运行产品测试。两项前置限制仍保留，不由审查通过消除。最终文档提交 SHA 由 Git 提交及交付回复提供，WP-C tested_code_sha 不变。
