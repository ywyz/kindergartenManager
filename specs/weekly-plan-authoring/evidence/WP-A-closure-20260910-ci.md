# WP-A exact-SHA CI 修正补充（2026-09-10）

首个证据提交 `bb84827afb59f29575f93028f162c9adafe3e0e5` 的
[Quality34488927576](https://github.com/ywyz/kindergartenManager/actions/runs/34488927576) 已完成，结论 failure。
其安装、audit、changed Python Ruff、fresh SQLite migration、Test 成功；常规 tests 为1215 passed/1 skipped，
Foundation 为260 passed/1 failed。此结果完整保留，不把它改成通过或借用历史 SHA。

唯一失败节点：`specs/agent-foundation/tests/test_f009_zero_persistence_matrix_red.py::test_restart_after_draft_has_fresh_ids_history_and_no_agent_schema`。
现有 `7c91e2a4b610` 迁移和 academic_identity 模型建立 `identity_audit`，其 action 只允许 `identity_manage`。
F009 的禁止名称守卫包含 audit 词，但精确非 Agent 业务表例外只列旧周/月表，误将已有身份审计表判为 Agent 新持久化。
其前面的 draft/restart/context/history/副作用断言均经过后才到该名称断言失败；不据此宣称整个 Foundation 成功。

只读 reviewer 独立核对 CI、测试、迁移及身份模型/仓储，确认仅在 `AUTHORIZED_NON_AGENT_BUSINESS_TABLES`
增加精确 `identity_audit` 是必要测试修正；它不能加入 Agent 写入证据集合。Main 同时新增
`assert "identity_audit" in names` 和 `assert rows_by_table["identity_audit"] == ()`。
`FORBIDDEN_AGENT_SCHEMA_TERMS`、禁止名称函数、全表反射、前后快照、SQL DML/DDL、UI、audit、文件保护全部保持，
没有用宽泛 audit 排除、skip/xfail 或忽略失败实现 GREEN。无产品代码、迁移或 WP-C 行为改变。

在修正前，用实际测试常量/名称函数和现有迁移 AST 的表名运行隔离守卫探针两次，均仅报 `identity_audit`（exit1）；
本地原测试字节 SHA256 为 `9dd9ed7d6bd7574731d5d09c513677ddf421b7549efc2a9cdc05ded8d22bd61a`。
修正后同探针 exit0，无意外禁止表。该探针只验证测试名称守卫的误判，不执行 DDL/业务接口，不冒称 WP-C 业务 RED/GREEN。
可复现入口见 [ci_guard_probe.py](../validation/wp-a-closure-20260910/ci_guard_probe.py)；测试新版本字节由最终清单绑定。

本地 Windows Python3.14.6：隔离守卫探针通过、改动测试 Ruff0.16.6 通过；未在本地运行完整 Foundation。
完整 Foundation 必须由后继实际 closure SHA 的 Python3.14.7 Quality 重跑并读回。该完整运行结果在最终 #77 评论记录，
未取得成功之前保持“WP-A实质条件满足、证据/CI收口未完成”。
旧 Office 人工验收仍只绑定原 DOCX/PDF/PNG 与当时脚本；本次测试守卫修正不改变那些样本或产品行为，未重渲染。
