# Reduction / Export 独立只读复审

- Reviewer：`/root/ui_impl`。
- 日期：2026-09-12。
- 当前核实代码 HEAD：`9cde71655c30cafdc6ac4e99ed22509ad989b121`。
- 工作树：`/home/ywyz/code/km-wpe-authoring-20260912`。
- 结论：下述有边界源审中，本 reviewer 提出的两项历史问题已在当前源码闭合；当前没有新增、可确定的 OPEN finding。本报告不是 WP-E COMPLETE、全代码独立审、独立两库重跑或 Word/云端验收。

## 独立性与范围

Reviewer 实现过 weekly UI/page projection；**本报告不审查、不验收该 reviewer 自己的 UI、page_application 或 weekly_page_repository**。本次仅独立读取未参与实现的 `reduction_application`、authoring 生命周期 hooks、Main 的 `export_application`、`weekly_export_repository` 和 `d375e9012abc` migration。没有修改这些产品文件，没有递归委派，没有调用真实模型、云端、凭据或生产操作。

authoring 原有 WP-D 应用整体不是本报告重新验收范围；这里审查的是缩减保存/对账/清理 hooks，以及 exporter 所消费的既有授权、双 CAS 和页面契约。source hash、历史测试日志与最终 exact-SHA 测试角色分别记录，不相互替代。

## 当前源码绑定

| 文件 | SHA256 |
|---|---|
| `app/service/shared_weekly/reduction_application.py` | `388e2f5c48748028004d63bb4a39438f8a8a4b18efd267272f27820fb3c089ea` |
| `app/service/shared_weekly/authoring_application.py` | `bc888918d40bccf47d8085af5971de8a2e60d27504530a0469351ddd60b333fa` |
| `app/service/shared_weekly/export_application.py` | `2c23ea36797d6cbf18d30b0b721f7572e6edd7bc0c5205ebb5854bf479078d02` |
| `app/repository/weekly_export_repository.py` | `5a1ed5b48ca58dd3bca2f94eca229ed5f30a115a86e69997831176b3d823f239` |
| `alembic/versions/d375e9012abc_shared_weekly_export_audit.py` | `1562ba4b8171494bcd7d5c254866a05d2bc455ab7385f7ae921b222235c74b97` |

HEAD 和上述文件 hash 在撰写报告前实时重新读取。export/reduction/authoring 的 hash 与此前逐段复审绑定一致；repository/migration 当前格式化版本另行重新读取。

## 历史 finding 与修复

### R1：过期已采用候选不释放（原 P1，当前源审 CLOSED）

原路径：真实 `propose → adopt` 后不保存、不显式 discard；authoring 页面 TTL 过期，但 reduction `_adopted` 仍保留整个候选。达到容量后新候选被永久 `candidate_capacity` 拒绝，旧页面又因过期无法正常 discard。该问题由本 reviewer 只读发现并交实现者取得修复前证据，未由 reviewer 改代码。

当前修复：`reduction_application.py:189` 的 `cleanup` 按仍存活的 authoring 页面清理 `_adopted` 和候选；`_cycle` 调用 cleanup，`authoring_application.py:156` 的既有生命周期清理也连接该 hook。旧候选正文不再因页面过期永久占用 adopted 容量。

实现者过程证据（相对本 evidence 根目录）：`reduction/expired-adopted-before.{json,tar.gz}`、`expired-adopted-red1/2.{json,log}`、`expired-adopted-green.{json,log}`。对应真实节点 `tests/test_wpe_reduction_application.py::test_expired_adopted_page_releases_candidate_body_and_capacity`。本次重新校验两个 RED 日志及 GREEN 日志的 hash 均与各 JSON 一致；记录为两次 exit 1，之后 exit 0 / 1 passed。该证据属于实现者历史执行，不冒充 reviewer 独立重跑。

### R2：缩减保存 commit_unknown 丢失 live 依赖（原 P1，当前源审 CLOSED）

原路径：缩减候选明确采用后，真实保存已经提交但连接异常抛出 `commit_unknown`；`super().save_edit` 清理原页并抛出，正常 `reduction.saved` hook 不执行。只读对账确认后重开，本次 live 缩减的 source/prompt/template 依赖没有恢复，可能被错误当作普通历史快照，绕过正常成功保存路径的漂移拒绝。

当前修复：`reduction_application.py:457` `_save_guard` 保留仅用于本次结果未知操作的 metadata；`:482` `unknown` 以 actor/operation 绑定元数据并移除 adopted 候选；`:488` `reconciled` 校验 scope/plan，只有只读对账确认的结果才恢复 `_saved` 依赖；`:521` `dependencies` 在未对账时拒绝继续。`authoring_application.py:942` 的 save hook 捕获结果未知并移交 metadata，`:965` 的 reconcile hook 在原有只读对账之后恢复依赖。没有自动重试保存，没有将对账当成再次提交。

实现者过程证据：`reduction/unknown-before.{json,tar.gz}`、`unknown-red1/2.{json,log}`、`unknown-both-phases-fixed.{json,log}`。节点 `tests/test_wpe_reduction_application.py::test_commit_unknown_reconcile_retains_live_prompt_baseline`；后续覆盖提交前/后两个分支。本次重新校验相关日志 hash 与 JSON 一致，历史 RED 各 exit 1，fixed 记录 exit 0 / 2 passed。`unknown-both-phases` 中间执行保留，不能被最终记录覆盖或改写。

## 其他复审判断

- 普通 AI/import 明确保存后形成历史快照，普通重开/手改不因旧源删除而禁止保存；本 reviewer 最初提出的“全部历史源/prompt永远重验”疑问经 Main 对 WP-D 边界核对后**不列 finding**。本次 live 缩减/渲染链依赖与历史快照语义分开。
- Main 自行发现的 binding guard 重入死锁、最终 export cancellation/page-busy 竞态，不记为本 reviewer 原始发现。当前 `export_application.py:223` 不在持有 binding lock 时再次 `resolve_binding`；`:292` 的 delivery nonce 检查、`:296` 取消入口，以及 `:315` / `:338` 的正式交付与 `_editing` 区间已见对应修复。`main/guard-*`、`main/delivery-*` 为 Main 过程证据；本次只校验 GREEN 日志 hash 与 JSON 相同，没有独立重跑。
- exporter 消费当前明确保存 v3，先校验完整性；实际 renderer 在数据库事务外等待，之后重验授权、plan/page、calendar、binding 与适用 live 依赖。候选/检查为一次性内存状态；正式交付无 AI 或隐式保存。
- audit repository 的 operation 查询带 tenant 条件；写入的是授权结果与 hash/版本等元数据，没有 DOCX/PDF/PNG 内容或文件路径，不是新增 ExportRecord。migration 使用复合 FK、明确 action/revision/hash 约束、两库 UPDATE/DELETE 拒绝触发器，并拒绝非空降级。本项为源码审查，不能替代数据库实测。
- 固定规则缩减保护已确认名称、引用区间、数字/否定上下文及固定字段；没有把自由语义重写视为已证明保持事实。规则不能缩短的正文应明确要求手工调整，不能自动无限重试或暗改字体行距。

## 测试证据角色及限制

本 reviewer **没有对上述五个模块在最终 HEAD 独立重跑测试**。之前本人执行的 UI SQLite/MySQL/callback/实际 LO 测试属于本人实现验证，不能充当本报告范围的独立验证，也不能拿来独立验收自己的 UI。

本次只读核对的历史实现者记录包括：`reduction/final-sqlite`（23 passed）、`reduction/final-mysql`（32772，23 passed）、`main/guard-green`（21 passed）、`main/delivery-green`（24 passed）；均重新核验 log hash。它们的 JSON `head` 是当时共同基线 `3fcefdf08a4b6aa6d3d7d5eb674cac2fce180713`，实际修复源必须结合各 source tar/manifest 理解，**不能直接称这些日志为最终 9cde716 的 exact-SHA 通过**。

最终 `9cde71655c30cafdc6ac4e99ed22509ad989b121` 的两库、回归、Foundation、lint/format、实际页面等验证由 Main 的最终日志/清单绑定；本报告不推断其未读完或仍在执行的状态。不声明独立两库 GREEN、远端 CI、真实模型、云端浏览器、原生 Microsoft Word、部署或发布通过。Word 主要客户端与 LibreOffice 备用、本地合成 qualification 不能代替正式资格的边界保持不变。

WP-C 四类历史 native 双 RED 缺口仍 UNMET，原 177/178 raw hash 事实及重写时序处置不由本报告修改。WP-E 整门结论仍由 Main 按最终矩阵和外部门决定。
