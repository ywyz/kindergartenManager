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
| `test_transaction_atomicity_red.py` | apply 前全部 operation 校验零 DML、等待期无连接、单短事务、精确 id+旧 revision CAS、snapshot/update/audit/commit 四个已知失败点及 commit 前任务取消全回滚、commit-unknown applied/indeterminate 对账；reconcile 逐项绑定 nonce/patch/session/actor/plan/version/business 且永不重放 |
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
RED。W007 初始 GREEN commit `63ff0d31bac36ec5191eca19e59e7b8e54dbddda` 本地基线为 WRITE
`99 passed`、Foundation `261 passed`、ordinary `847 passed`。首轮 fixed-SHA Review 为 Standards M2、
Spec M1/L1；`cf38725` 后修正 commit `706aa2e889ee719d622bf6a16774606fc2e51393` 基线为 WRITE
`110 passed`、Foundation `261 passed`、ordinary `847 passed`。二轮 fixed-SHA Review 为 Standards M1、
Spec M1/L1，finding RED 已由 `40f25b7` 固定；`40f25b7` 后修正 commit
`b2b312e6c89b9470d5e29815db37bc89a0ca0e6e` 基线为 WRITE `112 passed`、Foundation `261 passed`、
ordinary `847 passed`。
三轮 fixed-SHA Review 为 Standards M1、Spec M1，finding RED 已由 `43636a0` 固定；`43636a0` 后修正基线为 WRITE `113 passed`、Foundation `261 passed`、ordinary `847 passed`。
提交前终态 identity 审计发现 M1，finding RED 已由 `9972aab` 固定。第四轮 fixed-SHA 双轴 Review 绑定
`bc742d6c64744234f2702622fd4dbb1988b5650d`，结果为 Standards H0/M1/L0、Spec H0/M1/L0：权威 terminal
ledger/integrity latch 不应只在 UI，且畸形 APPLIED identity 不得发布成功。
`bc742d6c64744234f2702622fd4dbb1988b5650d` 的统一测试基线为 WRITE `115 passed`、Foundation `261 passed`、ordinary
`847 passed`。finding RED 已由 `a58c719796e9136a55932c59c930f1f0c98f14b9` 固定，稳定为 `10 failed / 9 passed`，
node hash `eae4be37be04be28ba2647bac31e1ff57d871810fd29c1437e5c100c2261b7a5`。
`a58c719796e9136a55932c59c930f1f0c98f14b9` 后第一版修复候选统一测试为 WRITE `125 passed`、Foundation
`261 passed`、ordinary `847 passed`。提交前只读 precheck 发现 3M/1L（异 Patch 并发 issue、
wrong-plan/invalid-revision exact identity、session guard 迟发 success、close/capability cleanup）；finding RED 已由
`e8722f843f99aea4eb3321b06ad8074728adfd4a` 固定，连续两轮为 `6 failed / 15 passed`，combined node hash
`157c6a8aed7025a7963af47ef1bcf5f0f332b44be37867fe006d4084de5d796a`。
`e8722f843f99aea4eb3321b06ad8074728adfd4a` 后第二版修复候选统一测试为 WRITE `131 passed`、Foundation
`261 passed`、ordinary `847 passed`。取消/会话 precheck 复核发现 3M（same-key joiner cancel 取消
owner/shared task；cancelled close/disconnect 跳过 cleanup；commit-unknown 后 session 变化仍重开旧 reconcile）；
finding RED 已由 `ce8b7756eb1fc1069f4d31109d49dd6d7cccc14f` 固定，连续两轮为 `5 failed / 21 passed`，
combined node hash `56d901193c517d284526b39f61a1f0286587ca20d7276838bc0c4a7859ece345`。
`ce8b7756eb1fc1069f4d31109d49dd6d7cccc14f` 后第三版修复候选统一测试为 WRITE `136 passed`、Foundation
`261 passed`、ordinary `847 passed`。独立取消状态审计为 H0/M2：owner cancel 若 inner 吞取消/抛 BaseException
可迟发 APPLIED 或留 PENDING 重放；controller/UI 并发 close/disconnect 无共享 completion barrier。finding RED 已由
`149d45e0fb4a1b7110c3fb3676a4e44d495e810c` 固定，连续两轮为 `8 failed / 26 passed`，combined node hash
`e12d635b2fa86999ce626d2763a81f4b9063c5ad83c42176f913b399464ce29b`。
`149d45e0fb4a1b7110c3fb3676a4e44d495e810c` 后第四版修复候选统一测试为 WRITE `144 passed`、Foundation
`261 passed`、ordinary `847 passed`。独立 GREEN precheck 结果为 Standards H0/M0、Spec H0/M1：inner issue
已完成但 owner cancel 在 shield 投递前使 same-key joiner 拿旧 PENDING。finding RED 已由
`c20aaa2f2b0c276bf985bb3d8ecf3fca4b364504` 固定，单节点连续两轮均为 `1 failed`，node hash
`1a6cf115cba623fcef1e99cd11d5d3d1cdd8698717f01ec9d4b9971389e49a35`。
`c20aaa2f2b0c276bf985bb3d8ecf3fca4b364504` 后第五版修复候选统一测试为 WRITE `145 passed`、Foundation
`261 passed`、ordinary `847 passed`。后继 Patch identity 独立 precheck 结果为 Standards H0/M0、Spec H0/M1：
无条件 current snapshot 让旧 apply/reconcile joiner 收到后继 Patch B。finding RED 已由
`827b1113f1679b9b5af4736652c91d6742a63fc4` 固定，代表节点连续两轮均为 `1 failed`，node hash
`29b35e46c1ee8f3bc872b09eaf1fcb23fa959e8d4c61b8b5b5b93f9506f551c5`。当前修复使用 per-flight cancellation override；
两个新节点 `2 passed`、finding 两文件 `36 passed`。
`827b1113f1679b9b5af4736652c91d6742a63fc4` 后第六版修复候选统一测试为 WRITE `146 passed`、Foundation
`261 passed`、ordinary `847 passed`。后续独立 precheck 发现 Spec M1：done-but-undelivered issue waiter 在
explicit invalidate/close 后仍发布旧 PENDING。finding RED 已由 `b2f91e7c604e92f1ae8461e709399c3842ac6c43`
固定，invalidate/close 两参数连续两轮均为 `2 failed`，combined node hash
`f0f3a9b8ea6c99674746d7b8c8fc9d80342b097b5b21c097be40e09a833146b8`。当前修复使用
live per-flight waiter registry + lifecycle override；新增 `2 passed`、finding 两文件 `38 passed`。
`b2f91e7c604e92f1ae8461e709399c3842ac6c43` 后第七版修复候选统一测试为 WRITE `148 passed`、Foundation
`261 passed`、ordinary `847 passed`。独立 lifecycle/cancel 审计为 H0/M2：pre-start cancel non-caller 分支把旧 A
waiter 投到后继 B；close/disconnect 的 BaseException 穿透并由 traceback 保留 writer。finding RED 已由
`7d51d63994ceaf939833fc9679db31de3f21baf7` 固定，3 节点连续两轮均为 `3 failed`，combined node hash
`d66294717711ef2581d15bcaa1ebe76754267d7d825acdb847574c16da01cf42`。当前 suppress_failure 区分显式
lifecycle/cancel override 与 spontaneous BaseException；`3 passed`、finding 两文件 `41 passed`。
`7d51d63994ceaf939833fc9679db31de3f21baf7` 后第八版修复候选统一测试为 WRITE `151 passed`、Foundation
`261 passed`、ordinary `847 passed`。joiner-cancel 后 shield loop handler 原始异常泄漏，审计 H0/M1。finding RED
已由 `bb539771f477e068d86e5bc3790f2a503e275ce9` 固定，单节点连续两轮均为 `1 failed`，node hash
`915ad0796ad3b8ca96ae4c2efe0e8f2ed4946d0c4e4c5875dfafd19920f866ba`。修复以 asyncio.wait + task.result
替代 per-waiter shield，保留 owner spontaneous BaseException；新增 `1 passed`、finding 两文件 `42 passed`。
`bb539771f477e068d86e5bc3790f2a503e275ce9` 后第九版修复候选统一测试为 WRITE `152 passed`、Foundation
`261 passed`、ordinary `847 passed`。owner identity 独立审计为 H0/M1：joiner cancel 先 finally 清全局
`_inflight_owner`，随后 owner cancel 无法收敛，controller/repeat 留 PENDING（20/20）。finding RED 已由
`21c0a9e6a4ed4f8e7a6e91584d4b8cdba37a2d24` 固定，单节点连续两轮均为 `1 failed`，node hash
`95dba951ab937642ec1518f5af44dcc5e58ec3d9c146e7c210339bd2d533dfd2`。当前修复使用 `_FlightState.owner` +
仅 owner finally 释放 current flight；代表节点 `1 passed`、finding 两文件 `43 passed`。
`21c0a9e6a4ed4f8e7a6e91584d4b8cdba37a2d24` 后第十版修复候选统一测试为 WRITE `153 passed`、Foundation
`261 passed`、ordinary `847 passed`。第五轮 fixed-SHA 双轴 Review 绑定
`7bd5c11ccee6af26d55959803a0594ff0a277ccc`，结果为 Standards H0/M3/L1、Spec H0/M0/L0：Standards findings
覆盖 projection `repr` 正文隐私、UI Protocol 的只读真实 stub/类型契约、W007 lineage 单一 canonical ledger，
以及复合 lifecycle cleanup 与 gated APPLIED 发布边界；Spec 无 finding。finding RED 已由
`68e4c340e0188f456ff8bc1caca5181f07410b15` 固定，连续两轮均为 `7 failed`，node hash
`980d2c23c873546843b385700cbb1d4f4680d8aa5213eeccc5da02af2ef56052`。

第五轮 finding RED 之后的提交前只读审计继续按独立门固定如下；每一项均连续复现两次，且只提交测试：

- `0b03fab4791aefa1e066b2fe59a7c2001684d572`：self-close cycle、pre-start cancel、ledger、raw traceback 与
  loop-handler 泄漏共 `5 failed`，node hash
  `8b0c909bff9138b55a4c2fe78ac198ca5505bcae71ea1e285451cf3681ec7c3b`。
- `4f7e91f7cd36d831892f19dd237aa45ee5c07e65`：external/finally 与 composite cycle、abandoned operation、
  scheduler/pre-start failure 共 `5 failed`，node hash
  `a12cf1153dc44fddaff3a73d928472e6e2e95c8b2eb6cbb4e49baaa6db776342`。
- `2dc21889a615475b72860b63545befe4b4b87374`：completed lifecycle Task 的 caller context/capability
  滞留及 spawned close 迟发发布共 `3 failed`，node hash
  `248089196799c54e12a495301e8b269c1d19ff1366db10beb429618c0b833641`。
- `49d4aa7332313f886de34b076451fd3af6677e1e`：single-flight Handle lease 的契约与证据过时，`1 failed`，
  node hash `e23a7939725d35eaa67d41750c6b9aba115d9d7e3358538994f502b02286ac7b`。
- `b4f27c2f72ecbd6edfa5a60dfdd96bf48c3deca6`：origin capture failure cycle 与 caller-local cancel 污染
  repeated/external joiner 共 `3 failed`，node hash
  `4c1df7ed032bc04662393a89c1858bcb2c1dbb4ddb0c36a76e116a67010786e8`。
- `6e83fd988343fd639456c9e7928277f2db7f336d`：confirmation/Agent cleanup failure precedence、composite
  external/finally cycle、logger failure raw retention/non-fail-fast 共 `5 failed`，node hash
  `bc86542aaca96dc6696e6630c5827e1b8ce2e4654f9fad997634ec612e489436`。
- `b768d3effc5ce8bb44c3a5a2b065d276a8e52814`：capture failure 把普通 external joiner 误判为 origin，
  `1 failed`，node hash `9242724607ede9ac5acd74fa43127e898129c15beeb09a61e857c1c8bce7fd1c`。
- `5f22728b49f8f85219eb12a6e83c5cd71484526d`：capture 与 validator 同时失败时 self-close 半关闭、
  external-close-finally 环共 `2 failed`，node hash
  `f3e11ad28b12315df216e4c394a8ded53b7be7a0504b94950ea2629e0920fe66`。

第五轮 finding 修复候选 commit `74e0ec591e6b1432eaa0fde29d812b206f6f827c` 的第六轮 fixed-SHA 双轴
Review 结果为 Standards H0/M2/L0、Spec H0/M0/L0。Standards findings 分别固定内部 confirmation
flight/shutdown Task 不得继承并长期保留 caller `ContextVar` capability，以及安全 guard 的诊断日志故障不得
覆盖已经提交的终态或让 UI 停在 busy。finding RED 已由
`0dc9d39` 固定，3 个节点连续两轮均为 `3 failed`，node hash
`1bfea83fcc37e6ea981feccc5f9e711abaaf8b400a27c5a71c2e898b078e8420`。

第六轮 finding 修复候选 commit `4f31e1e3762b20ab4742b7a4e8aa48cbbd47aa78` 的第七轮 fixed-SHA 双轴
Review 结果为 Standards H0/M1/L1、Spec H0/M0/L0。前述 `Context` 与 best-effort logger 两项 M2 已闭合；
新 findings 是九份当前状态文档与既有测试锁死过时 Review 轮次/SHA，以及第六轮测试读取 service 私有
`_shutdown_task`。finding RED 已由 `1a080908e28dcc3debb5e41e70b5770d981994a0` 固定，2 个节点连续两轮
均为 `2 failed`，node hash `ca535f495b0bba8f4bef9c5038101f6ab887d957660b3996e87cdb10d5f5507d`。

当前第七轮 finding 修复候选已本地 GREEN，尚未取得新 fixed-SHA Review 0/0。相关治理矩阵
`18 passed`、全部 W007 `114 passed`、完整 WRITE `192 passed`、Foundation `261 passed`、ordinary
`847 passed`，Ruff/format/diff 检查通过且变更范围 Pyright 为 0。尚未 push、CI、人工验收或 Issue 回写，
W008 未进入，也不得据此宣称 Standards/Spec 0/0、merge、Issue 关闭或 release。

第七轮 finding 修复候选 commit `3d1f6e9bd3642f34c048c682af8a3eb0345f6142` 的第八轮 fixed-SHA 双轴
Review 结果为 Standards H0/M1/L1、Spec H0/M0/L0。新 findings 是把尚未回写 W007 的 Issue #52 与
canonical ledger 并列成精确状态双权威，以及第七轮守卫只匹配特定“第五轮”/SHA/`_shutdown_task` 事故而
不能覆盖后续轮次或其他 confirmation-flow 私有字段。finding RED 已由
`ec098ab04d17cb3985a2ecea5eab793d12e0f9c6` 固定，2 个节点连续两轮均为 `2 failed`，node hash
`30c5fdc405b62ecf40b46e2679906d76adfa0a64ff2caae5dfc990182b242ede`。

当前第八轮 finding 修复候选已本地 GREEN，尚未取得新 fixed-SHA Review 0/0。治理守卫矩阵
`10 passed`、全部 W007 `118 passed`、完整 WRITE `196 passed`、Foundation `261 passed`、ordinary
`847 passed`，Ruff/format/diff 检查通过且变更范围 Pyright 为 0。尚未 push、CI、人工验收或 Issue 回写，
W008 未进入，也不得据此宣称 Standards/Spec 0/0、merge、Issue 关闭或 release。

第八轮 finding 修复候选 commit `d80252482cc2ab8c1c88d4df5b1696af130e4b74` 的第九轮 fixed-SHA 双轴
Review 结果为 Standards H0/M2/L1、Spec H0/M0/L0。新 findings 是 W007 Markdown heading 与状态正文跨段
时漏检、confirmation-flow 私有读取守卫依赖 receiver 拼写而漏掉 alias/`getattr`，以及第八轮测试以源码
片段而非行为反例锁定实现。finding RED 已由 `c0da4c19679b2ac826f6c8002b32131a778a2eba` 固定，
2 个节点连续两轮均为 `2 failed / 1 passed`，node hash
`837a9d94542f33841e70565c8f76b3686558ee7ebad05beed0bfa3700d7822c5`。

第九轮 Review finding 修复已本地 GREEN：行为守卫 `7 passed`、全部 W007 `119 passed`、完整 WRITE
`197 passed`、Foundation `261 passed`、ordinary `847 passed`。但提交前独立对抗 precheck 已另报
H0/M2/L0：fenced/nested Markdown scope 与跨段状态仍有漏报/误报，AST alias 分析仍漏掉结构赋值和
`getattr` alias 且可能跨作用域误报。该 precheck finding 尚待独立稳定 RED；当前候选不得进入 fixed-SHA
Review、push、CI、人工验收或 Issue 回写。

上述提交前 precheck finding RED 已由 `141f238e66151f5e01685ecf829c1e352ba9e726` 固定：Markdown 跨段、
nested/fenced scope 和 AST `getattr` alias、结构赋值、无关 `.flow`、跨函数污染共 8 个节点，连续两轮均为
`8 failed`，node hash `b623a654fdfec07ee3d00d6c093c09f46ca145d51ca23a895e61dc3f8b21d7d6`。
第一版修复已本地 GREEN：行为守卫 `15 passed`、全部 W007 `127 passed`、完整 WRITE `205 passed`、
Foundation `261 passed`、ordinary `847 passed`。但第二次独立 recheck 已另报 H0/M2/L1：CommonMark
closing/缩进 heading 仍有漏报/误报，函数默认值、decorator、闭包、分支 join 仍可绕过 AST 守卫，且普通
`flow` 参数/无关 harness 名称会误报。该 finding 尚待独立稳定 RED；当前候选仍不得进入 fixed-SHA Review、
push、CI、人工验收或 Issue 回写。

第二次 precheck finding RED 已由 `9228bd7d7e1f4043b35e64206c6100fa6fa7e527` 固定：CommonMark closing、
四空格 indented code、缩进 peer heading，以及函数默认值/decorator/闭包/If join/无关名称共 10 个节点，
连续两轮均为 `10 failed / 8 passed`，node hash
`16e2dc258797698788f7b23e8122ff5c077d85241c1d7e1713140acf28dd10a4`。第二版修复改用显式依赖的
CommonMark parser，并按词法作用域、参数遮蔽、结构赋值和 If path join 分析 AST；本地为守卫
`25 passed`、全部 W007 `137 passed`、完整 WRITE `215 passed`、Foundation `261 passed`、ordinary
`847 passed`，Ruff/format/diff、Pyright 与 `pip check` 通过。

第三次独立 recheck 已另报 H0/M2/L1：`try`/`while` path join、class 独立词法状态，以及
for/with/except/comprehension target 遮蔽仍有漏报/误报。该 finding 尚待独立稳定 RED；当前候选仍不得
进入 fixed-SHA Review、push、CI、人工验收或 Issue 回写。

第三次 precheck finding RED 已由 `f0ec4387db198dacf7c12078f0e9246628ce5524` 固定：try/while/class 的
漏报及 for/with/except/comprehension 的 target 误报共 7 个节点，连续两轮均为
`7 failed / 18 passed`，node hash
`653c0b354826bca8f2795c56750cb9ad33ef0720085643ad7782be86544c83cc`。第三版修复以 path-state union、
独立 class scope 与显式 binding target 遮蔽收敛常见控制流；本地为守卫 `32 passed`、全部 W007
`144 passed`、完整 WRITE `222 passed`、Foundation `261 passed`、ordinary `847 passed`，
Ruff/format/diff、Pyright 与 `pip check` 通过。当前候选尚未取得新的 fixed-SHA Review 0/0，不得进入
push、CI、人工验收或 Issue 回写。

第九轮修复候选 `ab27c7fa8541e707da4ca2ae0a841fb6ed32fd78` 的第十轮 fixed-SHA 双轴 Review
结果为 Standards H0/M1/L1、Spec H0/M0/L0。Standards findings 是测试专用
`markdown-it-py` 只进入 `requirements.txt` 而未进入 `pyproject.toml` dev 依赖与 `uv.lock`，以及
confirmation-flow 私有读取守卫已膨胀为手写 Python 数据流分析器。第十轮 finding RED 以可复现 dev
依赖图和刻意保持 syntax-local 的守卫边界固定这两项：2 个节点连续两轮均为 `2 failed`，node hash
`54f775b5fd3260e33b0efcaf07c578b37b58cc80a7da0100284a16c40ec31f0e`。当前仍不得进入 push、CI、
人工验收或 Issue 回写。

第十轮 finding RED 已由 `4944b45be000fa949e651f5b8d397d8c5a5a4301` 固定。最小修复把
`markdown-it-py` 加入无版本约束的 dev 依赖并增量锁定 `markdown-it-py 4.2.0`、`mdurl 0.1.2`；私有读取
守卫收缩为直接 `flow` / `confirmation_flow` / `harness.flow` 接收者的 syntax-local AST smoke guard，删除
只验证 alias、闭包、分支、循环、with、class 与 comprehension 的通用分析器契约。finding 节点连续两轮
均为 `2 passed`，相关治理矩阵 `16 passed`、全部 W007 `128 passed`、完整 WRITE `206 passed`、
Foundation `261 passed`、ordinary `847 passed`；`uv lock --check`、隔离 locked dev import、
Ruff/format/diff、Pyright 与 `pip check` 均通过。当前修复候选尚未取得新的 fixed-SHA 双轴 Review 0/0，
仍不得进入 push、CI、人工验收或 Issue 回写。

W007 最终产品/helper/test SHA `eb8273a20b1b955276eef4ae5cb781b3efb054b7` 随后闭合独立外部门：
第十一轮 fixed-SHA 双轴 Review 为 Standards H0/M0/L0、Spec H0/M0/L0；远端分支精确回读同 SHA；Quality
`33039376661` success 且 `headSha` 精确一致；Linux 可见矩阵 PASS 8/8；脱敏证据已回写 OPEN Issue #52
comment `5440130787`。这些外部门不改变 Provider/Tool 的四 READ + 两 DRAFT + 零 WRITE，也未授权 merge、
Issue 关闭或 release；W007 全部门闭合后才进入 W008。

W008 验收基础设施 RED 已由 `fa3ee34aaae47e1b52138326390ca458b7fc1ec9` 固定：Agent WRITE
`225 collected`，新增 browser/MySQL 合同 19 节点连续两轮均为 `19 failed`，仅因两个 helper 不存在；
node hash `d78e8d7e42feadf073f9a34794e3243d9567cad5f3a58d360339fc6127ca13a6`。第一版 helper 合同转绿后，
独立审计发现真实 launcher 仍为占位、MySQL app import 会创建配置文件、MySQL 合成 weekday 超过真实列宽，
以及 SQLite run path 未封闭。finding RED 已由 `0aebdbb` 固定：4 节点连续两轮均为 `4 failed`，node hash
`c339a09db034bd0d3a2b943b6c199a1b635891da33f04ed4cf668892a648aadc`。

`0aebdbb` 后的 W008 helper GREEN 候选只增加测试态 browser/MySQL runner 与操作合同，不改生产能力面。
初始合同 + finding 节点为 `23 passed`，完整 Agent WRITE 为 `229 passed`，Ruff/format/diff、编译与变更范围
Pyright 为 0。该候选的 exact SHA 必须以包含本段的后续 Git commit 为准；在 fixed-SHA Review、本地全门、
push、精确 SHA CI、真实 MySQL 8、Linux 浏览器矩阵和 OPEN Issue 回写全部完成前，不得宣称 W008 闭合、
merge、Issue 关闭或 release。

上述 helper GREEN commit `4b51519a89fedbbc6008a71c270cba983ef6c810` 的 W008 首轮 fixed-SHA 双轴
Review 为 Standards H1/M0/L1、Spec H0/M0/L0。Standards hard finding 是文档在 linked worktree 内先跑
Alembic 时必创建 `.kindergarten_secrets.lock`（缺少合成 Key 时还会创建 secrets），随后 live helper 又拒绝
这些配置生命周期文件，导致 documented MySQL 往返不可执行；low finding 是 browser helper 保留未接入
launcher 的自由字符串 `sanitize_report`，不能兑现关闭脱敏承诺。两项 finding 的稳定 RED 已由
`1ded7bf164c16c7df9e8f31f0361be2ae2f6d5c3` 固定：14 个相关节点连续两轮均为
`2 failed, 12 passed`，失败 node 完全一致，node hash
`507a9e2607d54fc812b5aabc57d15fe0dfb8cf858936a169939386f88c1ffb04`。当前尚未修正、push、CI、
MySQL/浏览器验收或 Issue 回写；Spec 0/0 不能替代 Standards findings。

首版 finding 修复把 Alembic 运行 cwd 移到 owner-only 外部临时目录，并删除未接入实际 launcher 的自由
字符串 sanitizer；相关 14 节点与完整 WRITE 分别为 `14 passed`、`230 passed`。提交前变更范围 Pyright
连续两轮都只在既有测试事件联合类型解包处报同一个错误，最小 `cast` 只收窄测试类型、不改变运行行为。
提交前该版本尚无 fixed SHA；任何 fixed-SHA Review、MySQL/浏览器证据都必须绑定随后实际 commit。

该修复实际提交为 `9fc21f9d6e75f7e3f2393f364e795649cb3a8351`；其第二轮 fixed-SHA 双轴 Review
为 Standards H0/M0/L1、Spec H0/M1/L0。两轴共同 finding 是上一段仍以现在时把已提交候选称为“未提交”，
使 canonical ledger 错报当前门状态。对应状态 RED 已由
`f5becb455450a97d491aa90cfccf48c5ad021fc9` 固定：状态合同连续两轮均为 `1 failed, 5 passed`，
失败 node 完全一致，node hash `c8d542f2c2373c86a9278d5c9d142c8b2e1f2cbeeb66bde1c4034d4b4e940a18`。在修正措辞并生成
新 SHA 前，旧 Review 不得视为 0/0，也不得进入后续本地、push、CI、MySQL、浏览器或 Issue 门。

措辞修正 commit `2b4bea62ae2621572da947e272c9a649bfa8cd1a` 的第三轮 fixed-SHA 双轴 Review 已达
Standards H0/M0/L0、Spec H0/M0/L0；本地 revision/WRITE/Foundation/ordinary 分别为
`12/231/261/847 passed`，静态门与依赖审计 GREEN。首次真实 MySQL 8 单次验收使用官方 image digest
`sha256:e9027fe4d91c0153429607251656806cc784e914937271037f7738bd5b8e7709`，fresh 空库与
MySQL `8.0.27` 已确认，但 app migration 在 revision b7d9e1f3a5c2 创建首个 trigger 时被 errno `1419` 拒绝；
只读诊断为 `@@log_bin=1`、`@@log_bin_trust_function_creators=0`、head 仍为 a6c4d8e2f9b1、trigger 为 0。
失败后未重跑、未执行 live helper；容器保留完成只读诊断后按精确名称停止，`--rm + tmpfs` 已移除合成库。
该 finding 合同连续两轮均为 `1 failed, 6 passed`，失败 node 完全一致，node hash
`2bd8936f94bd9a89eec6e27e0413824c5fd391d7c9acada292338ee0f59f97c0`，并由
`44bdf21a34b45f9ac6c1fcab1f851c9b080e0d9f` 固定；旧 Review/本地证据均不得作为后续新 SHA 的
最终证据。

修复候选的完整 WRITE precheck 另发现上述 W008 migration revision 的反引号记法会被既有 W007
唯一-ledger 守卫当作 W007 commit lineage；对应既有守卫节点连续两轮均为 `1 failed`，node hash
`2bbe8db6e0ec5fc1d0956d69726d876e69852aa1c7bd819a6b0458123c251217`。该 RED 已包含在 `44bdf21…`
ancestry；最小修正只把 migration revision 改成非 commit 引用记法，不放宽 W007 守卫。

提交前最小修正候选的 MySQL 前提合同为 `7 passed`，W007 唯一-ledger 守卫恢复 GREEN，完整 WRITE 为
`232 passed`。实际 fixed SHA 只由包含本段的后续 commit 决定；这些 precheck 不预先宣称新 SHA 的
Review、本地全门、真实 MySQL、浏览器、CI 或 Issue 门通过。

MySQL 前提修正 commit `367ad33f5092fd6e4dfd5c001c934a9bb178d7ee` 的 fixed-SHA Review 为
Standards H0/M1/L0、Spec H0/M0/L0。Standards finding 是 `tasks.md` 状态表仍把已闭合的 W007 标成
“交付门进行中”、把已进入多轮门的 W008 标成“未进入”，与 canonical ledger 相反。任务表只应把 W007
标为完成、W008 标为进行中并指向 ledger，不复制逐轮事实。该轮 Spec 0/0 不能替代 Standards finding；
后续状态合同连续两轮均为 `1 failed`，失败 node 完全一致，node hash
`6339519d44c7f306eb4faaa837cdb037e6a38cc1ebabb9852fb8adc9f7420bdf`，并由
`3c69c239b5f67f2f856acede293ad714f0ed1611` 固定。

任务状态修正 commit `d85334e6bb6212dafed96fcaeb15a31b136924f7` 的 fixed-SHA Review 为
Standards H0/M0/L1、Spec H0/M1/L0。两轴共同 finding 是上一段在已经记录稳定 RED 且任务表已修正后，
仍以现在时称“尚待稳定 RED 与修正”，使 canonical ledger 同时表达待办与完成。对应状态诚实性合同在
本轮连续两次均为 `1 failed`，失败 node 完全一致，node hash
`cf19c9d1d43de29ae375accbe3baae62766997086da008ca68aa8632416baea3`，并由
`bf0dc52551c067b4e9561093bf103549bfc07df6` 固定；旧 Review 不能作为后续修正文档 SHA 的 0/0 证据。

状态收敛 commit `2539f104fe2d41ad6f11fb731501c4845183652a` 的 fixed-SHA 双轴 Review、完整本地门、
真实 MySQL 8 与精确 `headSha` CI 曾分别达到 0/0 与 GREEN；但随后 Linux Chrome 可见故障矩阵在
`after_version` 首个注入场景发现 helper 未触发故障：页面错误显示采用成功，目标 revision 由 1 变为 2，
version/audit 各新增 1 行，writer 计数为 `1/1/0`。矩阵在 finding 后立即停止，旧 SHA 的终点证据随即失效。

真实 Alembic/SQLite 公共 writer 路径的 finding RED 已由
`3e6d4c2bf33cc1e642b0aad23ccab59113417115` 固定：同一节点连续两轮均为 `1 failed`，失败均为
`DID NOT RAISE ConfirmedWriteRejected`，node hash
`9d28c8d1f28b57e005ff5a2a2af5843d9e1846a0b8802c65f6d12c1431bd2345`。根因是 helper 只接受 exact
`str` 表名，而真实 ORM 表名为 `str` 子类 `quoted_name`，使 `after_version` 与 `after_audit` 均无法登记。
最小修复已由 `a734934634f393e29c848177eb9dcb9763100944` 提交，只放宽该测试态表名识别；目标节点、
全部 W008 合同与完整 WRITE 分别为 `1/27/233 passed`，Ruff/format/diff、变更范围 Pyright 与
`pip check` 通过。该修复尚未取得 fixed-SHA Review；不得据此恢复旧 Review、CI、MySQL、浏览器或
Issue 门，也不得宣称 W008 闭合、merge、Issue 关闭或 release。

Chrome finding 修复状态 SHA `e7f171822ab4dcdc212463682a4969a2654ab990` 的 fixed-SHA 双轴 Review 为
Standards H0/M0/L0、Spec H0/M2/L0。Spec findings 是 live MySQL helper 接受 root URL 且未验证实际
principal 只具单 schema 权限，以及 browser helper 继承宿主 HTTP(S)/ALL proxy、未在 app import 前强制
mock 流量直连 loopback。对应 finding RED 已由 `a0b4d8f050d169f5f6a8a5744e949abb32b52408` 固定：
两个相关文件连续两轮均为 `5 failed, 16 passed`，失败节点完全一致，node hash
`cadc1ae0cdc32ca4f7aa85434c88a9fef3b46c58e79cdb6cdba4b061b96b10a9`；该轮 Standards 0/0 不能替代
Spec findings。

最小修复候选拒绝 root URL，并在任何验收 DML 前只读验证连接 principal 只有 USAGE 与目标 schema grants；
browser helper 在应用导入前移除继承 proxy 并固定双写 loopback `NO_PROXY`。全部 W008 合同为 `37 passed`。
该候选尚无 fixed SHA，尚未运行完整本地门、复审、真实 MySQL、push/CI、完整 Chrome 矩阵或 Issue 回写。

上述两项 Spec finding 修复候选已由 `89bb093c6010a05daff75666c541dbed75a20829` 提交，提交前 W008/WRITE
为 `37/243 passed`；但 precommit 审计发现 MySQL database-level grant 中未转义 `_`/`%` 是通配符，
原 classifier 还用 `casefold()` 接受大小写错配，可能把跨 schema 权限误报为单 schema。该 hard finding
的 RED 已由 `76dd5aacd0092da8f28cdfcba7e77b61edb54b5c` 固定：MySQL helper 文件连续两轮均为
`5 failed, 19 passed`，失败节点完全一致，node hash
`51117cf0ab127871ceab6be424f792336eaa5b3e99f9a693171a6d21118516ac`；中间候选不得进入复审或外部门。

最小修复已由 `595394cca283c1e710bb98583d3f9d742a490c7a` 提交：disposable schema 改为无 grant
通配字符的 `kmw008`，URL gate 拒绝非字母数字 schema，classifier 按大小写精确匹配并只接受正确转义的
历史 wildcard grant。全部 W008/WRITE 分别为 `42/248 passed`，Ruff/format/diff、变更范围 Pyright 与
`pip check` 通过。该修复的后续状态收敛 Review 见下段；不得据此宣称真实 MySQL、push/CI、Chrome
矩阵、Issue 回写或 W008 闭合。

状态收敛 SHA `08799d89b7e72144ee3dfb560ef18d22ae0ef653` 的 fixed-SHA 双轴 Review 为
Standards H0/M0/L0、Spec H0/M0/L0。本段只记录该已闭合历史门；包含本段的后续 fixed SHA 仍须取得
自身的双轴 Review，不能继承 `08799d8` 的结果。

后续证据记录 SHA `d9e04f05b02cca11e0bad97196d2267c802f5e2c` 的 Standards Review 在独立子审计
回流后更正为 H0/M1/L1；Spec 为 H0/M0/L0。Medium finding 是 `CONTEXT.md` 仍把远端分支写成只到
W006，与本 ledger 已闭合的 W007 外部门及实际远端矛盾；Low finding 是 browser/MySQL helper 分别复制
fixed-SHA、Git、linked-worktree/clean 与 import activation 信任根。对应 finding RED 已由
`82931c2e60fa75eda6840c6cb754a3071de38f78` 固定：两个节点连续两轮均为 `2 failed`，失败节点完全一致，node hash
`1c118801d3b7f832dd009e8599805f6c81f4633f4705f0b58d3ce3df4f7f5423`。旧 Review 结论不得作为后续
SHA 的 0/0；修复后仍须重新执行双轴 Review、本地、MySQL、push/CI、Chrome 与 Issue 门。

最小修复已由 `198c2ab7ae1c578c3f5a072cb62d3df7f2c9c1bd` 提交：`CONTEXT.md` 不再复制过时的
W006 远端 SHA，并把精确门状态委托给本 ledger；browser/MySQL runner 通过一个纯 stdlib 深 module 共用
fixed-SHA、Git、linked-worktree/clean 与 import activation 信任根，同时以参数保留两入口不同的受保护
文件策略。finding 节点与全部 W008 合同为 `2/44 passed`，完整 WRITE 为 `250 passed`；Ruff/format/diff
与变更范围 Pyright 通过。该 GREEN commit 尚未取得自身的 fixed-SHA 双轴 Review；包含本段的后续 SHA
也必须重新 Review，且不得预先宣称真实 MySQL、push/CI、Chrome、Issue 或 W008 闭合。

状态收敛 SHA `c0d7210892063ad8b7c94423f68f0014d40373d1` 的 fixed-SHA Review 为 Standards
H0/M1/L0、Spec H0/M0/L0。先前 duplicated-code finding 已关闭；剩余 Medium finding 是
`CONTEXT.md` 的“当前共同下一步”仍称 W007 闭合后才进入 W008，与同文件分支状态及 canonical ledger
矛盾。对应 finding RED 已由 `009e842f98bacd43b9c13b523fbf7cae64f727fe` 固定：目标文件连续两轮均为
`1 failed, 2 passed`，失败节点完全一致，node hash
`a1687b69f353c4795b2aaf117a3c1060b13ac81afde8ff7d902755fb7a3dd83e`。该轮 Spec 0/0 不能替代
Standards finding；修复后生成的新 SHA 仍须取得自身双轴 Review，且所有后续门保持未闭合。

最小措辞修复已由 `f4efaa720591968eb4359c4cb8201b86d59ad054` 提交：`CONTEXT.md` 现在明确 W007
已闭合、当前按 canonical ledger 完成 W008 剩余门；目标 finding 文件为 `3 passed`，连同 W008 状态合同
为 `11 passed`，Ruff/format/diff 通过。该修复不改产品或 helper 行为；包含本段的后续 fixed SHA 仍须
独立双轴 Review，不能继承 `c0d7210` 的 Spec 0/0。

状态收敛 SHA `a93b148def7ef561a82b2b1d63ad72a3c580ca33` 曾完成 W008 外部门并回写 Issue #52 comment
`5461698915`；但 PR #53 自动 Review 随后报告两个新 finding：默认 Compose 未向 MySQL 8 提供应用 principal
创建 trigger 的必要前提，以及 `INDETERMINATE` 在确定对账后永久占用 confirmation store 容量。前者稳定
RED commit `78e2908` 连续两轮均为 `1 failed`，最小 Compose 修复为 `cd1672f`；后者稳定 RED commit
`0628c00` 连续两轮均为 `2 failed`，覆盖 applied/not-applied 两种确定对账，最小状态机修复为 `172818f`。
目标回归当前为 Compose `1 passed`、确定对账及既有 commit-unknown `4 passed`、transaction/W006 reconcile
`33 passed`。这些修复改变产品/部署/test，旧 `a93b148…` 的 Review、CI、MySQL、Chrome 与 Issue 终点证据
全部失效；包含本段的后续 fixed SHA 必须重新完成 W008 全部门，才能进入已单独授权的 W009。

随后 release-readiness 核查确认发布说明仍把兼容 `/setup` 错写为匿名管理员入口，PyInstaller 产物也没有
可调用的 bootstrap 子命令；Compose 还硬编码 healthcheck/数据库密码、缺独立运行数据卷，Debian 服务以 root
运行且声明数据目录与真实 frozen 路径不一致。对应测试 lineage 为：说明 RED `653cb29`（连续两轮
`3 failed, 2 passed`）、打包入口 RED `b1a3b04`（clean worktree `3 failed`）、自定义 healthcheck RED
`457e740`（连续两轮 `1 failed, 1 passed`）、显式 Compose 密码 RED `3c34fcf`（连续两轮
`1 failed, 2 passed`）、README 边界 RED `d5f914c`（连续两轮 `1 failed, 5 passed`）、显式数据目录与 Debian
权限 RED `e9fb538`（clean worktree `9 failed, 1 passed`）、发布环境说明 RED `44b1f3a`（连续两轮
`3 failed, 4 passed`）。最小 GREEN 依次由 `b1884f4`、`f837c8c`、`219633c`、`15ec854` 与说明提交
`9376a54`/`46abd4f` 完成；打包入口现在支持交互 `--init`，Compose 密码缺失时失败关闭并把运行数据放在
独立 `/data` 卷，Debian 使用专用非 root 用户、`0700/0600` 数据权限和同一显式数据目录。新增/受影响目标
合同当前合计 `23 passed`，Ruff、YAML parse、Debian shell syntax 与 diff check 通过。以上改动再次使所有
旧 fixed-SHA Review/CI/MySQL/Chrome 证据失效；只有包含本段的后续 commit 才能作为新的 W008 候选。

候选 `0079ab182d41546d5f401bf5d79a180b523acc7a` 的本地 revision/WRITE/Foundation/ordinary 为
`12/253/261/868 passed`；Ruff、最终增量 Pyright、lock/dependency consistency、严格依赖审计与 fresh SQLite
upgrade→downgrade→upgrade 均 GREEN，SQLite 最终为 head e5f7a9c2d4b6、`19` tables、`6` triggers、
mode `0600`。真实 MySQL `8.4.11` 的同一迁移往返也成功，且只读诊断确认 app principal、head 与四个 evidence
trigger 精确；但 live helper 在任何 live SQL 前拒绝前序测试留下的 owner-only、`0600`、零内容
`.kindergarten_secrets.lock`，只输出脱敏失败。该锁同时是 browser helper 的显式前提，因此旧 helper 合同存在
顺序矛盾；失败容器保留完成只读诊断后已按精确名称停止，tmpfs 合成库已移除，未重跑 helper。

对应前检 RED commit `afff51e1c9b601defd2b34c4a846294749bc30e1` 连续两轮均为 `1 failed, 8 deselected`；
最小 GREEN `2ce7dc0ec5f03131750bb845caaee3b69d172c9c` 只允许该无内容 lock，仍拒绝 `.env` 与
`.kindergarten_secrets`，并在 application import 前继续安装 file-free synthetic config。目标 MySQL helper
合同与既有 helper 矩阵为 `33 passed`，Ruff/format/diff 通过。该 helper/test/docs 改动使 `0079ab1…` 的全部
本地/MySQL 结果不能作为终点证据；只有包含本段的后续 commit 才能重新进入 W008 全门。

候选 `8cef83d5d67ee357b8cb16cd34aa7b25ac4fcc43` 的 revision/WRITE/Foundation/ordinary 为
`12/254/261/868 passed`，Ruff、最终增量 Pyright、lock/dependency consistency、严格依赖审计、fresh
SQLite upgrade→downgrade→upgrade、真实 MySQL 8.4.11 live helper 与 13 场景 Linux Chrome 矩阵均
GREEN；mock 精确接受 26 次请求，即 13 份草案各两次串行 Provider 请求。但该 SHA 的 fixed-SHA Review
随后报告 Standards H1/L1、Spec H1/M2：Debian 发布命令以 root 而非 service user 初始化 owner-only
数据，默认 Compose 的 Caddy 实际只提供 HTTP，升级说明遗漏 `exports` 卷，`.env.example` 仍把 SQLite
描述为程序同目录。旧候选不得 merge 或 release。

四项 finding 的纯测试 RED 由 `5d359e0224a8fe4f1d1fb13c55b016342ee00adb` 固定；Caddy 断言随后在
`f5c318811e79369f4b75616b5635d080064b22a9` 修正为接受合法的同行 `{` 语法，该 detached tree 仍精确为
`4 failed, 16 passed`。最小修复已由 `63cab67010ff59745ae3d628229d0b3d9e169aa6` 固定：Compose
显式要求生产域名，Caddy 对该域名自动 HTTPS，所有 Debian init 说明复用 service user，并同步持久卷与
SQLite 数据目录文案。该 `tested_code_sha` 的目标 finding 合同为 `20 passed`；
revision/WRITE/Foundation/ordinary 分别为 `12/254/261/872 passed`，Ruff、最终增量 Pyright、
lock/dependency consistency、严格依赖审计、fresh SQLite upgrade→downgrade→upgrade 与真实 MySQL 8.4.11
live helper 均 GREEN。MySQL helper 只读证据为 head e5f7a9c2d4b6、四个 trigger rejection、
CAS `[false, true]`、最终 revision `2` 与 lock errno `1205`。Linux Chrome 的 13 场景可见矩阵全部通过：
正常双击仅一次写入；过期、错误会话、旧 revision、A→B→A、跨标签与刷新均关闭或丢弃页面能力；
四种确定失败完整回滚；两种未知提交分别经只读对账收敛为未生效/已生效。mock 精确接受 `26` 次请求，
13 个场景的数据库 revision/version/audit 与 writer issue/apply/reconcile 计数均符合合同。上述临时数据库、
容器、应用进程、mock 与浏览器标签已清理。本段只闭合 `tested_code_sha` 的本地证据；包含本段的
evidence-closure SHA 仍须重新完成双轴 Review、push/PR CI、Issue、merge-SHA Review/CI 与 release 门。

证据闭合候选 `e66906ba87d058d1e954b8bea42abc96d53953df` 的 fixed-SHA Review 为 Standards
H0/M1/L1、Spec H1/M0/L0：开发/人工测试文档仍停在旧迁移 head；源码/打包 SQLite 数据目录措辞仍混淆；
默认 Compose 还把包含 MySQL root 密码的完整 `.env` 注入 app 容器。对应 finding RED 已由
`72776b8` 固定，两个目标文件连续两轮均为 `3 failed, 13 passed`，失败节点完全一致。下一候选必须让
app 只接收普通 MySQL principal 的 URL 与显式应用配置、保留 db-only root 配置，并统一当前 head 与数据目录
事实；旧 `e66906b…` Review 与所有先前本地/MySQL/Chrome 终点证据均不能作为新候选的闭合门。

最小修复及上述 RED lineage 的 `tested_code_sha=942aaec7e7b6360f0b12ba29f8a4828be2e71cf2` 已完成
重新验收：revision/WRITE/Foundation/ordinary 为 `12/254/261/874 passed`；Ruff、增量 Pyright、
lock/dependency consistency、严格依赖审计、Compose 缺域名失败关闭、生产/开发渲染的 app 环境不含
`MYSQL_ROOT_PASSWORD`、官方 Caddy validate 与 fresh SQLite 往返均 GREEN。SQLite 最终 head
e5f7a9c2d4b6、`19` tables、`6` triggers、目录/库 mode `0700/0600`。真实 MySQL 8.4.11 往返与 live helper
再次得到四个 trigger rejection、CAS `[false, true]`、revision `2`、lock errno `1205`。Linux Chrome 13 场景
全部得到预期可见状态，mock 精确接受 `26` 次请求，各场景最终 revision/version/audit 分别为正常与
unknown-after-commit `2/1/1`、人工保存旧 revision `2/0/0`、其余 `1/0/0`。本轮一次并发预启动因本机资源
压力在任何浏览器操作前停止，不计入矩阵；随后全部场景按独立进程与唯一端口顺序完成。所有合成 secret、
临时数据库/目录、MySQL tmpfs 容器、应用/mock 进程与浏览器标签均已删除或停止。包含本段的 evidence-closure
SHA 仍须取得自身的双轴 Review、PR CI，之后才可进入 `--no-ff` merge 与 merge-SHA 后续门。

证据闭合候选 `aa1167a8b515772a159ab7a7fcb12254c1464fd6` 的 fixed-SHA Review 为 Standards
H0/M1/L1、Spec H1/M1/L0：开发者指南仍把当前已提交分支写成“正在实现尚未提交”；README、
ADR-0003 与系统架构文档仍混淆源码/打包模式的默认数据与密钥路径；且移除 app 的整体
`env_file` 后，Compose 首次管理员命令连接远程 MySQL，却未提供仅限本次调用的
`BOOTSTRAP_ADMIN_ALLOW_REMOTE=true`，会按默认 fail-closed。对应 finding RED 已由
`0f09dd5e29214fbeb7d31e7612d8f3b9e9d7f72a` 固定；三个目标节点连续两轮均为 `3 failed, 16 passed`，
失败节点完全一致。下一候选必须统一三处路径语义、把开发状态委派给本 ledger，并在
README、用户手册与 release body 中使用同一条 one-shot Compose bootstrap 命令；常驻 app 环境
仍必须不含该 override，MySQL root 凭据仍必须仅属于 db。本段不预先宣称 GREEN、后续 Review、
完整本地门、PR CI、merge、Issue 或 release 通过。

最小修正及上述 RED lineage 的
`tested_code_sha=bba33dc2c7cab3208622c2c8807518dd57865189` 已重新完成本地门：三个 finding 节点与
完整目标文件为 `19 passed`，发布/文档/bootstrap 矩阵为 `38 passed`，revision/WRITE/
Foundation/ordinary 为 `12/254/261/877 passed`。变更范围 Ruff/format/Pyright、diff check、
`uv lock --check`、pip/uv dependency consistency 与严格依赖漏洞审计均 GREEN，已有历史 migration 的
三处未使用导入不属于本轮 diff，未改写历史 migration。Compose 缺域名精确 fail-closed；
生产/开发渲染均确认 app 不含 `MYSQL_ROOT_PASSWORD` 或
`BOOTSTRAP_ADMIN_ALLOW_REMOTE`、db 保留 root 配置；官方 Caddy validate 确认自动 TLS 与 HTTP→HTTPS
重定向。fresh SQLite upgrade→downgrade→upgrade 最终为 head e5f7a9c2d4b6、`19` tables、
`6` triggers、目录/库 mode `0700/0600`。

真实官方 `mysql:8` image digest
`sha256:e9027fe4d91c0153429607251656806cc784e914937271037f7738bd5b8e7709` 在本机解析为
MySQL `8.0.27`；binary log 与 `log_bin_trust_function_creators` 均为 `1`，schema-scoped app principal 的
head→a6c4d8e2f9b1→head 往返与 live helper 均 GREEN。helper 脱敏证据为四个 trigger rejection、
CAS `[false, true]`、最终 revision `2`、lock errno `1205`。Linux 浏览器最终矩阵在重启的
fresh mock 上按独立进程/数据库顺序完成 13 场景，mock 精确接受 `26` 次串行 Provider 请求。
正常双击与 unknown-after-commit 终态为 `2/1/1`，另一标签普通保存后的旧 revision 场景为
`2/0/0`，过期、错误会话、A→B→A、跨标签、reload、四种确定故障与 unknown-before-commit 均为
`1/0/0`；每个场景的 writer issue/apply/reconcile 公开操作均未超过一次。最终矩阵前的两次
浏览器脚本连接/选择器预检中断未执行 WRITE，已重启 mock 并使用 fresh DB，不计入最终矩阵。
全部合成 secret、临时数据库/目录、MySQL tmpfs 容器、应用/mock 进程与浏览器标签已删除或停止。
包含本段的 evidence-closure SHA 仍须取得自身的双轴 Review、push/PR CI，之后才可进入
`--no-ff` merge 与 merge-SHA 后续门。

PR #53 的远端自动 Review 随后在 `2e056d2979a0b1569efb5dcef74ea1a26a8f5f14` 发现三项新问题：显式
`KINDERGARTEN_DATA_DIR/.env` 写入后启动仍从 cwd 读取；已有宽权限数据目录未在运行文件访问前收敛；
commit-unknown 的原 COMMIT 仍在执行时，首次 audit 阴性读取会被 UI 永久终结为 not-applied。对应第一组
纯测试 RED `7de8547` 连续两轮均为 `7 failed`。路径首版 GREEN 的独立 Review 又发现安全快照后按路径二次
打开、显式 subclass dotenv 被覆盖、中间 symlink/不可信可写祖先与目录项未 fsync 四项缺口；第二组纯测试
RED `a630805` 连续两轮均为 `5 failed`。

commit-unknown 最小修复 `a45198f` 取消无数据库负证据的 `RECONCILED_NOT_APPLIED` 终态：audit 暂不可见时
同一 confirmation 保持 indeterminate、可重复只读 reconcile 且永不重放，后续完整证据可见才收敛 applied；
有界 store 压力下 fail closed。路径最小修复 `0d2547f` 逐组件安全打开 POSIX 数据根，在同一目录 FD 上完成
`.env` 的 `0600` 读取、原子替换与目录 fsync，并让默认 Settings 直接消费安全 dotenv 快照，同时保留标准
source 优先级和显式 override。Main 复跑路径/config `58 passed`、commit-unknown service/UI `93 passed`；
两组独立 GREEN Review 均为 H0/M0/L0。上述产品/helper/test 变化已使 `bba33dc…` 的完整 MySQL 与浏览器证据
失效；包含本段的后续候选必须重新执行全部本地、MySQL、13 场景浏览器、fixed-SHA Review 与 PR CI 门，本文
不预先宣称这些后续门通过。

上述修复与 RED lineage 的精确本地验收候选为
`tested_code_sha=9cc05c89eb83712aea00196cea17f3796cad90cf`。Main 在该 SHA 的 clean detached linked
worktree/主 checkout 组合上重新得到 revision/WRITE/Foundation/ordinary
`12/256/261/889 passed`；变更范围 Ruff 与 format、`git diff --check`、path/config 目标 Pyright、
`pip check`、`uv lock --check`、locked uv 环境 dependency consistency 和严格依赖漏洞审计均 GREEN。
service 整文件 Pyright 仍会报告既有 `_reject` 返回类型导致的控制流收窄问题，不冒充本候选新增通过项，且
当前 CI 不以该整文件命令为门。

fresh SQLite 的最终有效运行使用 W008 owner-only umask，完成
head→a6c4d8e2f9b1→head 往返；最终为 head e5f7a9c2d4b6、`19` tables、`6` triggers，目录/数据库
mode `0700/0600`。此前一次默认 umask 预检得到数据库 `0644`，未计入证据并清理。真实官方 `mysql:8`
image digest 仍为
`sha256:e9027fe4d91c0153429607251656806cc784e914937271037f7738bd5b8e7709`，本机解析为 MySQL
`8.0.27`；binary log 与 `log_bin_trust_function_creators` 均为 `1`。fresh schema 上 schema-scoped
app principal 完成 head→a6c4d8e2f9b1→head，live helper 脱敏证据为四个 trigger rejection、
CAS `[false, true]`、revision `2`、lock errno `1205`，且 `tested_code_sha` 精确匹配。本轮前两个 disposable
MySQL harness 分别因错误解析 venv 解释器和未使用 clean linked worktree 而在 migration/live helper 前置门
停止；只读诊断确认未把它们当作 live PASS，容器清理后第三个全新 schema 才形成上述有效证据。

同一 `tested_code_sha` 的 Linux 浏览器矩阵在一个 fresh mock 上，以 13 个独立 `0600` SQLite、独立应用
进程与唯一 loopback 端口顺序完成。正常双击和 unknown-after-commit 的最终
revision/version/audit 为 `2/1/1`；另一标签普通保存后的旧 revision 场景为 `2/0/0`；过期、错误会话、
A→B→A、跨标签、reload、`after_version`、`after_cas`、`after_audit`、`known_before_commit` 与
unknown-before-commit 均为 `1/0/0`。unknown-before-commit 在一次显式人工对账后仍保持
indeterminate、保留同页对账入口且不出现确认采用按钮；unknown-after-commit 经一次只读对账收敛为已采用。
mock 精确接受编号 `1..26` 的 `26` 次串行 Provider 请求；每个有效场景 writer
issue/apply/reconcile 公开操作均未超过一次。最终有效计数之外共有七次 fresh-DB 浏览器输入/连接/日期动画
预检中断：六次未发 Provider 请求，一次任意提示词被关闭 mock 以 `422` 拒绝；七次均为零 WRITE、数据库
baseline，均未在同一 DB 自动重试。最终 mock、应用、浏览器标签、合成数据库/secret 与本轮 linked
worktree 已停止或清理。

本轮 Graphify 辅助刷新严格按 `OpenAI-compatible -> DeepSeek -> luna_worker` 执行：OpenAI 返回 0 但遗漏
目标 ledger，DeepSeek 在自适应拆分后的响应读取中持续停滞，luna_worker 只读核对仍确认该 ledger 为 0 节点。
当前图虽可解析、规模无不明缩水且无断边，但不能证明本段 evidence 覆盖；因此 Graphify 在本候选上标记为
unavailable，不使用 stale graph 作为 Review、测试或交付证据，生成图文件也不进入本候选提交。

本段只闭合 `tested_code_sha` 的本地自动化、SQLite、MySQL 与浏览器证据。包含本段的后续
evidence-closure SHA 仍须取得自身的固定 SHA Standards/Spec 双轴 0/0/0 Review、PR exact-head CI 与远端
自动 Review；之后才可核对最新 main 漂移并以 `--no-ff` 集成，merge SHA 仍须重新完成 Review/CI，才能关闭
Issue #52、发布与部署。

证据闭合候选 `521418aa1df2dfa30d7e57b8a536ead41b8e5d07` 的 fixed-SHA Review 为 Spec
H0/M0/L0、Standards H1/M0/L0：Windows 发布说明把 frozen 应用的 `.env` 错写为安装目录，而当前实现从
`%LOCALAPPDATA%\KindergartenManager\.env` 读取。对应文档合同 RED 由
`231d5dd5a8677658d798ee6abed4ee636a860029` 固定；最小 GREEN
`fbf3f7c56378955ed217c66b63c78f3cbd9c37fd` 统一发布说明与现有数据目录合同，目标文档测试为
`15 passed`。原 Standards reviewer 对修复后 diff 的复核为 H0/M0/L0；但新增测试使旧 SHA 的手工与完整
本地证据失效，因此本段以下证据均重新绑定到
`tested_code_sha=fbf3f7c56378955ed217c66b63c78f3cbd9c37fd`。

Main 在该 SHA 的 clean detached linked worktree 重新得到 revision/WRITE/Foundation/ordinary
`12/256/261/890 passed`；变更范围 Ruff、format、`git diff --check`、`pip check`、
`uv lock --check` 与严格依赖漏洞审计均 GREEN。一次 Foundation 预检错误继承了 Main checkout 的显式
`KINDERGARTEN_DATA_DIR`，导致 `37` 个 setup error；移除该非候选环境后，在同一 clean worktree 的完整
`261 passed` 才计入有效证据。fresh SQLite 使用 owner-only 目录/数据库，完成
head→a6c4d8e2f9b1→head；最终为 head e5f7a9c2d4b6、`19` tables、`6` triggers，mode
`0700/0600`。

首个真实 MySQL 预检在任何 DML 前由 helper 拒绝：普通测试在该 disposable worktree 留下 Git-ignored、
owner-only 的 `.kindergarten_secrets`。独立只读诊断确认该运行已到达 MySQL `8.4.11`、精确 head、四个
trigger 与 schema-scoped app principal，但 evidence/audit/user/plan 均为零，故不计为 live PASS，也不需要
产品修复；销毁该容器后，在不含受保护文件的 exact-SHA manual worktree 和全新 schema 重跑。最终官方
`mysql:8` digest 为
`sha256:b3b90af2a6552ae30c266fdb7d5dd55f3afb72404bb78d37fe8a23eb857fd3fb`，解析为 MySQL
`8.4.11`；binary log 与 `log_bin_trust_function_creators` 为 `1`，app principal 完成
head→a6c4d8e2f9b1→head。helper 脱敏证据为四个 trigger rejection、CAS `[false, true]`、最终
revision `2`、lock errno `1205`，且 `tested_code_sha` 精确匹配。

同一 `tested_code_sha` 的 Linux 浏览器最终矩阵在 fresh mock 上，以 13 个独立 `0600` SQLite、独立应用
进程与唯一 loopback 端口顺序完成。正常双击和 unknown-after-commit 的最终
revision/version/audit 为 `2/1/1`；另一标签普通保存后的旧 revision 场景为 `2/0/0`；过期、错误会话、
A→B→A、跨标签、reload、`after_version`、`after_cas`、`after_audit`、`known_before_commit` 与
unknown-before-commit 均为 `1/0/0`。四种确定故障均显示确认关闭、正文不变，writer 为
issue/apply/reconcile `1/1/0`；unknown-before-commit 一次人工对账后仍不确定、保留同页对账入口且无确认
按钮，unknown-after-commit 一次对账后可见收敛为 `✅ Agent 草案已确认采用（revision 1 → 2）`，两者
writer 均为 `1/1/1`。mock 精确接受编号 `1..26` 的 `26` 次串行 Provider 请求。

最终矩阵前的非证据预检与有效场景严格分离：一次任意提示词被 mock 以 `422` 拒绝且零 WRITE；一次 seed
目录名不满足 helper 的 owner-only 前提而未创建数据库；错误会话与旧 revision 的三次端口释放竞争均在应用
启动/WRITE 前停止。随后均使用 fresh DB、唯一端口和最终有效场景，没有在同一 DB 自动重试。最终 mock、
应用、浏览器标签与所有验收端口均已停止；两个 MySQL disposable 容器均已销毁。本轮 Graphify 仍按既定
fallback 得不到覆盖目标 ledger 的语义节点，因此继续标记 unavailable，不把 stale graph 当作交付证据，
`graphify-out/**` 生成噪声不进入候选提交。

本段只闭合 `tested_code_sha` 的本地自动化、SQLite、MySQL、浏览器与 review-finding 修复复核。包含本段的
后续 evidence-closure SHA 仍须取得自身固定 SHA Standards/Spec 双轴 0/0/0 Review、PR exact-head CI 与
远端自动 Review；之后才可核对最新 main 漂移并以 `--no-ff` 集成，merge SHA 仍须重新完成 Review/CI，
才能关闭 Issue #52、发布与部署。

候选 `ff0d26e4da498e788c4e995cd88c31a4c77db2ec` 的 fixed-SHA Review 为 Spec H0/M0/L0、
Standards H1/M0/L0：本 ledger 把前一 closure commit 错写为不存在的 SHA，破坏固定 SHA lineage。
对应合同 RED `99d448a1645e3a16b40517a29fc6e3ab0f76e345` 连续两轮均为同一节点 `1 failed`；最小
GREEN `c17e5233d4038adebde054a92c4292b3e114ab22` 修正为真实
`521418aa1df2dfa30d7e57b8a536ead41b8e5d07`，文档合同为 `16 passed`。正确的 Ruff format 门随后在
`c17e523…` 报告新测试需格式化，纯机械修正由
`66955b9ba93a5d2445280c6c65dfc984725c0c6d` 固定；Ruff check/format 与同一 `16 passed` 均 GREEN。
新增测试与格式字节使旧手工证据失效，因此本段全部终点证据绑定
`tested_code_sha=66955b9ba93a5d2445280c6c65dfc984725c0c6d`。

Main 在该 SHA 的全新 detached linked worktree 得到 revision/WRITE/Foundation/ordinary
`12/256/261/891 passed`；变更范围 Ruff check/format、`git diff --check`、`pip check`、
`uv lock --check` 与严格依赖漏洞审计均 GREEN。此前一次把 `-z` 误放在 Git pathspec 之后的 Ruff 调用被
识别为无效调用，不计证据；修正命令后的结果才形成上述静态门。fresh SQLite 首次预检误用同步
`sqlite://`，在任何 migration 前被 async engine 拒绝；全新 owner-only DB 使用
`sqlite+aiosqlite://` 完成 head→a6c4d8e2f9b1→head，最终为 head e5f7a9c2d4b6、`19` tables、
`6` triggers、目录/数据库 `0700/0600`。

真实官方 `mysql:8` digest 为
`sha256:b3b90af2a6552ae30c266fdb7d5dd55f3afb72404bb78d37fe8a23eb857fd3fb`，解析为 MySQL
`8.4.11`，binary log 与 `log_bin_trust_function_creators` 均为 `1`，fresh schema table count `0`。
schema-scoped app principal 完成 head→a6c4d8e2f9b1→head；live helper 脱敏证据为四个 trigger
rejection、CAS `[false, true]`、revision `2`、lock errno `1205`，且 SHA 精确匹配。Docker 健康控制面在
本机高负载下超时，但 host 直连只读检查、三次 migration revision 与 helper 均形成有效证据；证据完成后
常规 `docker stop` 仍超时，Main 只对本次精确 disposable `mysqld` PID 执行 SIGKILL，`--rm + tmpfs` 已清除，
容器名与 loopback `13306` 均为空。

同一 `tested_code_sha` 的最终 Linux 浏览器矩阵在收敛日期控件交互后，使用一个重新启动的 fresh mock、
13 个独立 `0600` SQLite、独立 app 进程和唯一 loopback 端口顺序完成。mock 只包含最终有效矩阵并精确接受
编号 `1..26` 的 `26` 次串行 Provider 请求。正常双击与 unknown-after-commit 最终为
revision/version/audit `2/1/1`；另一标签普通保存后的旧 revision 为 `2/0/0`；过期、错误会话、A→B→A、
跨标签、reload、四种确定故障、known-before-commit 与 unknown-before-commit 均为 `1/0/0`。四种确定
故障全部显示确认关闭、正文不变；unknown-before-commit 一次对账后仍不确定、保留同页入口且没有确认按钮；
unknown-after-commit 一次对账后可见收敛为 `✅ Agent 草案已确认采用（revision 1 → 2）`。每个有效场景的
公开 writer issue/apply/reconcile 均未超过一次。

最终 fresh mock 前的浏览器连接、登录重定向、端口释放和日期动画/选择器预检均使用独立 DB；一项错误日期的
旧-revision 预检曾在其 disposable DB 上采用一次 Patch，因此对应 DB 与整轮 mock 都明确作废，而不是拼入
终点矩阵或在同一 DB 重试。其余无效交互也在 whole-mock 边界丢弃；月份/日期操作收敛后才启动上述最终
`1..26` mock。最终所有 app/mock、浏览器标签、MySQL 容器与验收端口均已停止。Graphify 仍无法生成覆盖
目标 ledger 的语义节点，继续标记 unavailable，不把 stale graph 当作证据，`graphify-out/**` 不进入候选。

本段只闭合 `tested_code_sha` 的本地、SQLite、MySQL 与浏览器证据。包含本段的后续 evidence-closure SHA
仍须取得自身 fixed-SHA Standards/Spec 双轴 0/0/0 Review、PR exact-head CI 与远端自动 Review；之后才可
核对最新 main 漂移并以 `--no-ff` 集成，merge SHA 仍须重新完成 Review/CI，才能关闭 Issue #52、发布与部署。

证据闭合候选 `0581840b2e9265b03cdf8b6dc27307e40411afb9` 的 fixed-SHA Review 为 Spec
H0/M0/L0、Standards H2/M0/L0：本 ledger 另有两处 reviewer SHA 尾位写错，分别把真实
`afff51e1c9b601defd2b34c4a846294749bc30e1` 与
`0f09dd5e29214fbeb7d31e7612d8f3b9e9d7f72a` 记录成不存在的 commit。通用文档 ledger
commit-ref 合同 RED `67de0554686cae6d4e10e26cb0b9ed6f329dacde` 连续两轮均为同一节点
`1 failed`；最小 GREEN `5cd4bbd0c4dc8c74fb6c0dd8d3d63c4b9cb8fd29` 只修正上述两个引用。
该测试字节变化使旧 fixed-SHA 手工证据失效，因此本段全部有效证据重新绑定
`tested_code_sha=5cd4bbd0c4dc8c74fb6c0dd8d3d63c4b9cb8fd29`。

Main 在该 SHA 的 clean detached linked worktree 得到 revision/WRITE/Foundation/ordinary
`12/257/261/891 passed`；变更范围 Ruff check/format、增量 Pyright、`git diff --check`、
`pip check`、`uv lock --check` 与严格依赖漏洞审计均 GREEN。一次未显式绑定共享解释器的 Pyright
调用只产生环境依赖解析错误，未计入证据；绑定绝对 `--pythonpath` 后的增量门为 `0 errors`。fresh
SQLite 在 owner-only 目录/数据库完成 head→a6c4d8e2f9b1→head，最终为 head
e5f7a9c2d4b6、`19` tables、`6` triggers、目录/数据库 `0700/0600`。

重启前的三个 disposable MySQL 预检均因本机 Docker/资源运行时失稳而在完整证据形成前作废，不归因于
产品或 migration finding，也没有拼接到本段 PASS。宿主机重启恢复后，Main 从新的 tmpfs schema 单次完成
正式验收：官方 `mysql:8` digest
`sha256:b3b90af2a6552ae30c266fdb7d5dd55f3afb72404bb78d37fe8a23eb857fd3fb` 解析为 MySQL
`8.4.11`，binary log 与 `log_bin_trust_function_creators` 均为 `1`，fresh table count 为 `0`；
schema-scoped app principal 完成 head→a6c4d8e2f9b1→head。live helper 返回四个 trigger rejection、
CAS `[false, true]`、最终 revision `2`、管理员竞争锁 errno `1205`，且 `tested_code_sha` 精确匹配。
证据捕获后该 exact container 与 loopback `13306` 均已清空。

同一 `tested_code_sha` 的最终 Linux Chrome 矩阵使用 fresh mock、13 个独立 `0600` SQLite、独立应用进程
与唯一 loopback 端口顺序完成；mock 精确接受编号 `1..26` 的 `26` 次串行 Provider 请求。正常双击与
unknown-after-commit 最终 revision/version/audit 为 `2/1/1`；另一标签普通保存后的旧 revision 场景为
`2/0/0`；过期、错误会话、A→B→A、跨标签、reload、`after_version`、`after_cas`、`after_audit`、
`known_before_commit` 与 unknown-before-commit 均为 `1/0/0`。四种确定故障全部可见显示确认关闭且
writer issue/apply/reconcile 为 `1/1/0`；unknown-before-commit 一次对账后仍不确定、保留同页对账入口、
没有确认按钮且 writer 为 `1/1/1`；unknown-after-commit 一次对账后可见收敛为
`✅ Agent 草案已确认采用（revision 1 → 2）`，writer 同为 `1/1/1`。浏览器跨端口复用合成登录的预检
在 Provider/WRITE 前停止并丢弃对应 DB，不进入有效矩阵；最终 mock 中仍只有上述 `1..26` 请求。
所有 app/mock、浏览器标签、MySQL 容器与验收端口均已停止。

本段只闭合 `tested_code_sha` 的本地自动化、SQLite、MySQL 与浏览器证据。包含本段的后续
evidence-closure SHA 仍须取得自身 fixed-SHA Standards/Spec 双轴 0/0/0 Review、PR exact-head CI 与
远端自动 Review；之后才可重新核对最新 main 漂移并以 `--no-ff` 集成。merge SHA 仍须重新完成
Review/CI，才能关闭 Issue #52、发布与部署；Issue #48 始终不在本轮关闭范围。

随后审阅的历史候选 `58625055d9bfba202c18f40ff1e19b981e711b27` 的 fixed-SHA Review 为 Standards
H0/M0/L0、Spec H0/M1/L0：`tests/test_documentation_security_contracts.py` 仍把旧的
`521418aa…` 当作最新 ledger closure，而上段最新候选已是
`0581840b2e9265b03cdf8b6dc27307e40411afb9`；该整文件复现为 `15 passed, 1 failed`，因此候选未进入
push/PR/merge。最小修正 `61ab16d8228837cd878b75073f1bd4621439788a` 对齐最新预期并收敛测试说明；独立
复核随后发现其负向 guard 使用了不存在的假 SHA，不能保护真实旧 closure。最终修正
`69e77ed0e884a035ae0288f74e34dc7752cf96e3` 改为真实旧 closure 的完整 SHA guard；
独立 Review 为 H0/M0/L0，文档安全合同 `16 passed`、Agent WRITE ledger 合同 `1 passed`。测试字节变化使
旧候选的手工与完整本地证据失效，因此本段全部终点证据绑定
`tested_code_sha=69e77ed0e884a035ae0288f74e34dc7752cf96e3`。

本段首稿完整复述负向 guard 值，文档安全合同如预期以同一节点 `15 passed, 1 failed` 阻止闭合；改用短
SHA 后，第二稿又把 review finding 候选误标为新的“证据闭合候选”，同一合同再次以 `15 passed, 1 failed`
阻止闭合。收敛为短 SHA 与准确的历史候选表述后才重新进入文档门，两次失败均不作为通过证据。

Main 在该 SHA 的 clean detached linked worktree 得到 revision/WRITE/Foundation/ordinary
`12/257/261/891 passed`；相对 main 的全部 `113` 个 Python 变更文件通过 Ruff check/format，新增文档合同
测试的增量 Pyright 为 `0 errors`，`git diff --check`、`pip check`、`uv lock --check`、locked dependency
consistency 与严格依赖漏洞审计均 GREEN。一次误把全历史 Python 变化纳入增量 Pyright 的调用报告
`247` 个既有类型问题，范围不符合本轮门且明确不计为通过证据。fresh SQLite 在 owner-only 目录/数据库完成
head→a6c4d8e2f9b1→head，最终为 head e5f7a9c2d4b6、`19` tables、`6` triggers，mode
`0700/0600`。

真实 MySQL 首次预检在应用 import、migration 与数据库写入前 fail closed：自动化 worktree 中有普通测试
遗留的 Git-ignored、owner-only `.kindergarten_secrets`，只读检查确认 fresh schema 仍为 `0` tables，故该次
不计为 live PASS。销毁该容器后，从不含受保护文件的 exact-SHA manual worktree 和全新 schema 重跑；官方
`mysql:8` digest 为
`sha256:b3b90af2a6552ae30c266fdb7d5dd55f3afb72404bb78d37fe8a23eb857fd3fb`，解析为 MySQL
`8.4.11`，binary log 与 `log_bin_trust_function_creators` 均为 `1`。schema-scoped app principal 完成
head→a6c4d8e2f9b1→head；live helper 返回四个 trigger rejection、CAS `[false, true]`、最终 revision
`2`、管理员竞争锁 errno `1205`，且 `tested_code_sha` 精确匹配。证据完成后 exact container 与 loopback
`13306` 均已清空。

同一 `tested_code_sha` 的最终 Linux Chrome FINAL2 矩阵使用一个 fresh mock、13 个独立 `0600` SQLite、
独立应用进程与唯一 loopback 端口顺序完成，13/13 场景通过；mock 只接受编号 `1..26` 的 `26` 次串行
`draft` Provider 请求。正常双击与 unknown-after-commit 最终 revision/version/audit 为 `2/1/1`；另一
标签普通保存后的旧 revision 场景为 `2/0/0`；过期、错误会话、A→B→A、跨标签、reload、
`after_version`、`after_cas`、`after_audit`、`known_before_commit` 与 unknown-before-commit 均为
`1/0/0`。四种确定故障均可见显示“写入未完成，本次确认已关闭”、正文与审计保持基线；
unknown-before-commit 一次人工对账后仍明确禁止重复采用、保留同页对账入口且无确认按钮；
unknown-after-commit 一次对账后可见收敛为 `✅ Agent 草案已确认采用（revision 1 → 2）`。整轮 writer
issue/apply/reconcile 汇总为 `13/9/2`，每个场景的每类公开操作均未超过一次；最终数据库逐项断言和
`18081..18094` 端口释放检查均 PASS。

FINAL2 前的非证据输入与整轮边界严格分离：任意提示词被 mock 以 `422` 拒绝的一轮、跨端口登录预检、
日期控件 transport timeout 的整轮，以及超时前只完成前四项和部分 A→B→A 的整轮均全部作废，不拼接
可见结果、数据库输出或 Provider 计数，也不在同一 DB 自动重试。浏览器连接恢复后才从 fresh DB 和 fresh
mock 完成上述 FINAL2；一个丢失进程会话句柄但尚未开始浏览器动作的 ABA 实例也先精确停止并从种子重建。
最终所有 app/mock、Chrome 标签、MySQL 容器与验收端口均已停止。

本轮 Graphify 辅助刷新按固定 fallback 的首项 OpenAI-compatible 一次完成，不需要进入 DeepSeek 或
luna_worker。当前图相对即时备份从 `4938` nodes/`11753` edges 增至 `4946/11754`，目标 ledger 节点从
`3` 增至 `11`，`built_at_commit` 精确为 `69e77ed0e884a035ae0288f74e34dc7752cf96e3`；multigraph 诊断为
missing/dangling endpoint、self-loop 与 exact duplicate edge 全部 `0`，无不明缩水。Graphify 仍只作辅助
覆盖证据，不替代 live tests/Review/CI，全部 `graphify-out/**` 生成文件继续排除在本候选提交之外。

本段只闭合 `tested_code_sha` 的本地自动化、SQLite、MySQL、浏览器与前一 Review finding 修复复核。
包含本段的后续 evidence-closure SHA 仍须取得自身 fixed-SHA Standards/Spec 双轴 0/0/0 Review、PR
exact-head CI 与远端自动 Review；之后才可重新核对最新 main 漂移并以 `--no-ff` 集成。merge SHA 仍须
重新完成 Review/CI，才能关闭 Issue #52、发布与部署；Issue #48 始终不在本轮关闭范围。
