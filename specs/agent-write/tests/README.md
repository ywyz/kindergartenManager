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
| `test_w007_confirmation_ui_red.py` | 页面本地单 Patch capability、安全只读 snapshot、逐次 issue/apply/reconcile、single-flight、生命周期失效、过期/stale/失败关闭、commit-unknown 只允许用户显式对账且不自动重试 |

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

## 2026-08-26 W007 RED 证据

W006 独立门闭合后，本地 commit `e5f7317…` 新增 W007 公共 UI-flow RED，并同步演进 Foundation UI 契约：

```text
W007 新模块节点（连续两轮）：21 failed；node hash 8bad6854…
完整 Agent WRITE（连续两轮）：77 passed, 22 failed；node hash e0898e89…
Agent Foundation（连续两轮）：259 passed, 2 failed；node hash fb168e7a…
ordinary：847 passed
```

三组 RED 均 collection clean，无 skip/xfail/error；失败只固定尚未满足的页面本地单 Patch confirmation flow、
基础面板可选动作端口和每日计划页安全接线。Provider registry 仍恰好四 READ + 两 DRAFT，测试不授权 Provider
WRITE、自动重试、批量/跨页面采用、设置/文件/Word/删除/创建写入或长期 Patch 持久化。该证据只固定 W007
RED。W007 初始 GREEN commit 本地基线为 WRITE `99 passed`、Foundation `261 passed`、ordinary `847 passed`。
首轮 fixed-SHA Review 为 Standards M2、Spec M1/L1；`cf38725` 后修正基线为 WRITE `110 passed`、Foundation `261 passed`、ordinary `847 passed`。
二轮 fixed-SHA Review 为 Standards M1、Spec M1/L1，finding RED 已由 `40f25b7` 固定；本轮修复候选已转 GREEN，下一门是第三轮 fixed-SHA 双轴 Review。
本轮修复候选经统一测试为 WRITE `112 passed`、Foundation `261 passed`、ordinary `847 passed`，也尚未取得 Standards/Spec 0/0、push、CI、人工验收或 Issue
回写；W008 未进入。
