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
