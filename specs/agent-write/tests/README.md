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
