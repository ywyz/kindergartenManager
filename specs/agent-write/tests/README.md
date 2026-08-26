# Agent WRITE 稳定 RED 说明

本目录把 `spec.md` 第 5 节的深模块接口作为唯一产品测试 seam：

```text
ConfirmedDailyPlanWriteService
  issue_confirmation(ui_session, patch, *, expected_revision)
  apply(ui_session, confirmation_id)
  reconcile(ui_session, confirmation_id)
```

测试不预建生产占位模块，不读取 service 私有状态，也不把 Provider、Repository 或 ORM 暴露给 UI。数据库、
时间和连接中断是允许替换的系统边界：日常行为使用隔离 SQLite，数据库 trigger 验收使用真实 Alembic upgrade，
时钟使用确定性 UTC clock，commit-unknown 使用 SQLAlchemy 的 commit 边界注入。

## 行为矩阵

| 文件 | 固定行为 |
|---|---|
| `test_confirmation_binding_red.py` | 安全 Pending DTO、Patch 完整性、actor/tenant/user/jti、三个入口重读 active User、reconcile 精确 jti、target、revision、before、expiry、store 丢失、逐 Patch 确认、一次消费与并发双击 |
| `test_transaction_atomicity_red.py` | apply 前全部 operation 校验零 DML、等待期无连接、单短事务、精确 id+旧 revision CAS、snapshot/update/audit/commit 四个已知失败点及 commit 前任务取消全回滚、commit-unknown applied/not-applied 对账；reconcile 逐项绑定 nonce/patch/session/actor/plan/version/business 且永不重放 |
| `test_immutable_evidence_red.py` | 完整精确的操作前 daily-plan 快照及规范 hash、全 no-op 拒绝与 mixed no-op+真实变化的多字段成功、四字段 Result、最小脱敏审计、confirmation 数据库唯一约束、同/异 jti 的 nonce/session 单向 hash、SQLite migration trigger 的 ORM/直接 SQL 不可变性、MySQL 离线 DDL 四 trigger、Foundation 仍仅六个 READ/DRAFT Tool |

失败注入不使用 `sleep` 或真实网络。事务阶段通过实际 SQL 事件观察；失败后的完整数据库逻辑快照必须与
baseline 相同。操作前版本精确覆盖旧计划全部 identity/revision/date/class/body/timestamp；审计列使用关闭
allowlist。模拟 Key/endpoint 放在无关配置表，Provider warning 放在 Patch，测试证明二者不进入版本或审计；
计划正文只允许进入完整操作前版本，不得进入审计，原始 session id 两边都不保存。

## 2026-08-25 RED 证据

```text
.venv/bin/python -m pytest specs/agent-write/tests --collect-only -q
59 tests collected

.venv/bin/python -m pytest specs/agent-write/tests -q --tb=no
1 passed, 58 failed

.venv/bin/python -m pytest specs/agent-write/tests -q --tb=no
1 passed, 58 failed
```

两次 node-only 失败列表完全一致，使用
`sed -n 's/^FAILED \([^ ]*\).*/\1/p' <run-output> | sha256sum` 得到的 SHA-256 均为
`fe346fa3ebfe73deb1405eed183004278a99ca0618f28039c4aec1454110fc5e`；58 个 WRITE 节点的首个失败都是
`ModuleNotFoundError: app.service.agent.confirmed_write`。唯一 GREEN 是独立证明既有 Foundation registry
仍恰好为四 READ + 两 DRAFT 的关闭面。collection、普通 SQLite fixture 与真实 Alembic fixture 均先成功，
因此没有 fixture/迁移次生失败，也没有 skip、xfail 或 collection error。该结果只固定 W004 RED，不授权
W005-W008 的生产 GREEN、Review、commit、push、CI 或人工验收。
