# WP-C F 人员默认证据（2026-09-11）

本证据只覆盖 `weekly_person_defaults` 与共享人员快照接线，不把人员姓名当作授权依据。默认行按 `(tenant_id, user_id, class_instance_id)` 隔离；`SharedWeekScope.semester_id` 只在同一 `IdentityApplication` 事务中重新执行当前 shared-week 授权。缺失默认行返回 `None`，`PeopleDefaults.revision` 不接受 0。

## Worker checkpoint 代码与原始日志哈希

工作区：`/home/ywyz/code/km-wpc-complete-20260911`。以下是本 worker 最终双库测试 checkpoint 的 SHA-256；Main 后续 lint 或集成若改动这些文件，需重新计算并以新 head 绑定测试。原始 stdout、stderr 与预修复源码包已归档到 `/home/ywyz/code/km-wpc-complete-evidence-20260911/people/`，文件清单及哈希见该目录的 `SHA256SUMS`。

| 文件 | SHA-256 |
|---|---|
| `app/service/shared_weekly/people_contracts.py` | `95cece52cc63c647bd9e59361d37b0d04164ce57c00e065c4feee3b39536e522` |
| `app/service/shared_weekly/people_application.py` | `b7875a28ca027b956d9a2e8212dba1b1f93437a494e5c0c80cedc6fe4521b0e7` |
| `app/repository/weekly_people_repository.py` | `6643ad7a95484e3bb4f9f5de6c2325d39b18cde0c48456f1388ec41745aad622` |
| `app/core/models/weekly_people.py` | `0480eff2a1cf661672e5f4e1930c0e73f66d42fca5d02e42fa98f70f300ce06a` |
| `alembic/versions/b153c7e9f026_weekly_people_defaults.py` | `ec013e35114dc762744d3f27ca214ff5983ecdebe027aeec516e093b70164519` |
| `tests/test_wpc_people.py` | `553bb6c3d95aca47c30a9b718a22e804c5b4f8ca1763399e8a300c1fa1a99daf` |

实现前冻结的六个源码文件已打包保存为 `/home/ywyz/code/km-wpc-complete-evidence-20260911/people/wp-c-people-pre-reconcile-20260911.tar`，SHA-256 为 `073c8f9935c130b8e8a898e4769965fb0490e47167e09177f1fcb66ee92ce111`。

真实双 RED 原始 stdout/stderr 已逐次保存到上述外部 evidence 目录。场景相同：operation 1 成功创建，operation 2 修改默认值，随后对账 operation 1。旧实现读取当前默认行并返回 `defaults_conflict`，不满足不可变 operation stamp。每个数据库连续运行两次，均为真实失败；没有插入假失败或跳过 application seam。

| 环境与第几次 | 命令 | 结果 | 日志 SHA-256 |
|---|---|---:|---|
| SQLite 1 | `.venv/bin/pytest tests/test_wpc_people.py::test_defaults_cas_and_operation_ledger_are_explicit -q` | `1 failed` | `87f201a3945af5f03bc9a123c5b3846e92e4fdedd8f29b1f3eaab15552432973` |
| SQLite 2 | 同上 | `1 failed` | `2a0e29eae3aad5e5469cee609a99fa39d1f5295fceac880de9668db1951cf875` |
| MySQL 8（32770）1 | `WPC_MYSQL_PORT=32770 .venv/bin/pytest tests/test_wpc_people.py::test_defaults_cas_and_operation_ledger_are_explicit -q` | `1 failed` | `356fe371b5a62d12cedeb9049bb53bd1603af9c3e0eba0255405c01160d33978` |
| MySQL 8（32770）2 | 同上 | `1 failed` | `f69c7cd868a658a1802cca25c12898bc32a3aa36eff5130b54885419dbfb7aea` |

最终日志为当次 `pytest` stdout/stderr 原文，已保存到上述外部 evidence 目录并计算 SHA-256：

| 环境与命令 | 结果 | 日志 SHA-256 |
|---|---:|---|
| SQLite：`.venv/bin/pytest tests/test_wpc_people.py -q` | `12 passed` | `73653e2ffb3d66115fa1c3757745627ed4abf48f51b5c1b08ddb5d83ec6fffad` |
| MySQL 8：`WPC_MYSQL_PORT=32770 .venv/bin/pytest tests/test_wpc_people.py -q` | `12 passed` | `421e38f21b97a7bce1ea3c5a168457c4787f3e068a47f086415cea7eefe6c70f` |
| SQLite：`tests/test_wpc_collaboration.py::test_shared_people_defaults_initialization_and_history` | `1 passed` | `c8195e475881a53aa3b3b955f23e19b19838d952648311a45cd875e464ca9720` |
| MySQL 8：同上 | `1 passed` | `129d6bf5db5a76730f76f2745a6a72aa2915246d2366bdcaa01c99a0d9b8cc1b` |

## F 覆盖矩阵

“初始覆盖”表示该断言在当前真实 application/repository/schema 首次跑即通过；本次 stale-operation 语义有 SQLite/MySQL 各连续两次真实 RED，再以最小 DTO/repository/application 修正收敛。

| 项目 | 实际生产 seam 与断言 | RED 状态 | 双库结果 |
|---|---|---|---|
| 1. DTO、隔离与 CAS | `test_people_contract_is_closed_and_revision_zero_is_absent`；`test_defaults_are_isolated_and_missing_row_is_not_revision_zero`；`test_defaults_cas_and_operation_ledger_are_explicit` | 初始覆盖；stamp 增加严格 revision/hash/outcome | SQLite/MySQL 通过 |
| 2. 并发共享默认保存 | `test_concurrent_default_cas_has_one_winner_and_one_conflict`：同一 actor、同一 class、同一 revision 的两次真实 application 保存恰好一成一败 | 初始覆盖 | SQLite/MySQL 通过 |
| 3. tenant/user/class 边界与姓名不授权 | `test_default_names_do_not_grant_shared_week_authority`；`test_defaults_reject_cross_class_and_cross_tenant_access`；同一 class 的另一 user 行独立 | 初始覆盖 | SQLite/MySQL 通过 |
| 4. 撤销与会话失效 | `test_defaults_revalidate_revocation_and_session[revoke]`、`[session]`；read/save/reconcile 均在 policy 事务中重新拒绝 | 初始覆盖 | SQLite/MySQL 通过 |
| 5. operation 重放、未知对账与对应 hash | `test_defaults_cas_and_operation_ledger_are_explicit`：未知 operation 前后审计行不变；operation 1 创建、operation 2 改值后，对账 operation 1 返回其原 revision、`people_hash`、`created` outcome；不读取当前 defaults、不返回姓名正文 | 双 RED：SQLite/MySQL 各连续 2 次 | SQLite/MySQL 通过 |
| 6. 首次初始化、重复创建、快照历史 | `test_shared_people_defaults_initialization_and_history`：首次 create 使用发起者默认，重复 create 不覆盖，默认更新不改既有版本，另一教师显式 shared save 才产生新版本 | 初始覆盖 | SQLite/MySQL 通过 |

## 数据库约束覆盖

- `test_people_migration_compound_foreign_keys`：SQLite 开启 `PRAGMA foreign_keys=ON` 后与 MySQL 均拒绝错误 tenant/user/class 复合外键。
- `test_people_operation_audit_is_immutable_and_nonempty_downgrade_is_denied`：两库均拒绝 audit UPDATE/DELETE，非空 `weekly_person_defaults`/audit 拒绝 downgrade。
- `test_people_migration_empty_roundtrip`：两库均完成 head → `a042b6d8e915` → head，最终版本为 `b153c7e9f026`，人员表重新存在且为空。

审计表只保存 actor、class、revision、operation、session hash、`people_hash` 与 outcome，不保存教师姓名、保育员姓名或正文。`reconcile` 先在当前 session/actor/class 授权事务内读取对应 immutable audit，再构造 `PeopleOperationStamp`；后续默认 revision 前进不会伪装旧 operation，也不会触发 `defaults_conflict`。
