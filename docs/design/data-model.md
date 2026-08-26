# KindergartenManager 数据模型

> 合入基线：`main@ca3b7bd`；当前 `feat/agent-write` 工作树 Alembic head：`e5f7a9c2d4b6`。
> W005/W006 已通过各自远端精确 SHA CI；W006 fixed SHA 为 `253d37d…`。W007 稳定 RED 已固定在本地
> `e5f7317…` 且 GREEN 候选已通过本地全量；W008 的最终浏览器与真实 MySQL 8 验收尚未进入。

## 1. 建模原则

- 所有 schema 变化通过 Alembic。
- 主键使用 `BIGINT`，SQLite 下变体为 `INTEGER` 以支持自增。
- 所有 18 个 ORM 表均有 `tenant_id`。
- 除 `user` 与租户级参考表 `indicator_catalog` 外，其余 16 个 ORM 表均有 `user_id`。
- 可变业务表通常同时包含 `created_at` 和 `updated_at`；`export_records` 与两张 W006 evidence 表是明确的
  append-only/历史例外，只记录 `created_at`。
- 历史导出所需的年级、班级、教师等采用快照字段，避免设置变更改写历史。
- 图片子表、倾听子表和导出关联多数为逻辑外键；完整性由 repository/service 和测试承担。

## 2. 表总览

| 表 | 作用 | 所有权 |
|---|---|---|
| `user` | 保留的用户、角色和密码哈希 | tenant |
| `semester_config` | 学期和激活状态 | tenant + user |
| `class_config` | 年级、班级、教师、室内/户外配置 | tenant + user |
| `ai_api_key` | 加密 AI Key、base URL、模型、类型和启用状态 | tenant + user |
| `prompt_template` | 按任务类型和版本保存提示词 | tenant + user |
| `daily_plan` | 每日计划、教案拆分、适配和生成内容 | tenant + user |
| `daily_plan_operation_version` | 单次确认写入前的完整每日计划业务快照 | tenant + user |
| `agent_write_audit` | 单次确认写入的最小不可变成功审计 | tenant + user |
| `game_observation` | 游戏观察主记录 | tenant + user |
| `game_observation_image` | 游戏观察图片和存储元数据 | tenant + user |
| `listening_record` | 一对一倾听主记录 | tenant + user |
| `listening_domain` | 五领域独立日期、目标、评价和策略 | tenant + user |
| `listening_image` | 每领域图片、描述和存储元数据 | tenant + user |
| `listening_indicator_result` | 二级指标星级结果 | tenant + user |
| `indicator_catalog` | 年级/学期/领域指标参考数据 | tenant |
| `homemade_teaching_toy` | 自制教玩具方案 | tenant + user |
| `course_review_activity` | 课程审议输入、调整和修订稿 | tenant + user |
| `export_records` | 各业务 Word 导出路径和逻辑关联 | tenant + user |

## 3. 关系视图

```text
tenant
 ├─ user
 ├─ indicator_catalog
 └─ user-owned data
     ├─ semester_config
     ├─ class_config
     ├─ ai_api_key
     ├─ prompt_template
     ├─ daily_plan ───────────────┐
     ├─ game_observation          │
     │   └─ game_observation_image│
     ├─ listening_record          ├─ export_records
     │   ├─ listening_domain      │
     │   ├─ listening_image       │
     │   └─ listening_indicator_result ── indicator_catalog
     ├─ homemade_teaching_toy     │
     └─ course_review_activity ───┘
```

线条表示业务逻辑关系，不代表数据库中一定存在 `FOREIGN KEY`。

## 4. 身份与配置

### `user`

- `(tenant_id, username)` 唯一。
- `hashed_password` 使用 Argon2 生成。
- `role` 枚举为 teacher / teaching_admin / sys_admin。
- UI 登录已在当前工作树恢复：JWT `sub + tenant_id + jti` 先通过签名/时间校验，然后每次受保护页面入口按 tenant/user 重读 active `user`，角色和显示名以数据库为权威。
- 应用启动不再自动创建固定 `admin`，也不挂载匿名自注册；空库初始化与老版固定密码账号恢复只能通过显式本地 admin bootstrap。

### `semester_config`

- 学期名称、开始/结束日期和 `is_active`。
- “同一用户只有一个 active”由业务层保证，数据库没有局部唯一约束。

### `class_config`

- 保存年级、班级、教师、室内区域和户外内容。
- 生成类记录会复制必要字段形成历史快照。

## 5. AI 配置与提示词

### `ai_api_key`

- `api_key_encrypted` 只存密文。
- `key_type` 为 text/vision。
- 同类型只有一个 active Key 由 repository 操作保证。
- `/settings` 按当前可信 actor 的 tenant + user 持久化 endpoint、model 与加密 Key。日常跨 worktree 复测可复用仓库外专用非生产数据库，并从仓库外权限受限的环境文件为进程提供与其配对的稳定 `ENCRYPTION_KEY`/`JWT_SECRET`；AI Key 本身不写入 `.env`。
- 只备份数据库密文而丢失原 `ENCRYPTION_KEY` 无法恢复 Key。日常持久化 profile 不能代替指定 SHA 的 F009 全新隔离验收。

### `prompt_template`

任务类型当前包括：

- split、adapt
- morning_exercise、morning_talk、area_game、outdoor_game、daily_reflection
- game_observation、one_on_one_listening
- homemade_teaching、course_review_activity

每个 tenant/user/task 按 `version` 保存历史，active 切换由 repository 保证。

## 6. 每日活动计划

`daily_plan` 包含：

- 日期、周次、中文星期。
- 年级/班级快照。
- 目标、准备、重点、难点。
- 活动过程原文与年龄适配稿。
- 晨间活动、晨间谈话、室内区域、户外活动和一日反思。
- 显式非空正整数 `revision`：既有行迁移回填为 1，新行为 1，每次成功更新恰好 `N → N+1`。

原文与适配稿必须同时保留，Word 导出的差异标红依赖两者。
页面加载时保存精确 plan id + revision，保存时原样带回；Repository 必须先匹配这两个调用方观察值，
再由 ORM `version_id_col` 执行实际 UPDATE CAS。陈旧页面/并发写失败，调用方不能经字段参数覆写 revision；
公开 ORM 属性只读，SQLite/MySQL trigger 还拒绝非 1 初始值、纯 revision bump 及不满足“内容变化且
`OLD + 1`”的 UPDATE；MySQL 文本字段先 `CAST(... AS BINARY)` 再做 NULL-safe 比较，避免默认不区分大小写/
重音的 collation 把字节级真实变化误判为 no-op。只读 API 已显式返回 revision。该先决条件已随 W004-W006
提交并通过精确 SHA CI 与 Linux service-boundary 验收；最终浏览器矩阵和真实 MySQL 8 验收仍属于 W008。

删除同样不能只按日期：页面捕获实际加载的 plan id + revision，Repository 用 tenant/user/id/revision 单条
条件 DELETE；未命中抛 stale 并回滚。这样旧标签页不能删除另一个标签后来更新或替换的记录。

## 7. 游戏观察

`game_observation` 保存观察日期、环境、参与者、班级快照、观察者和四段生成内容。

`game_observation_image` 通过 `observation_id` 逻辑关联主记录，每条图片包含：

- `image_index` 排序。
- `storage_backend`。
- BLOB 或 `object_key`。
- MIME、大小、宽高。

删除观察时必须显式删除图片并同时验证 tenant/user。

## 8. 一对一倾听

### 主记录

`listening_record` 表示一个幼儿的一次记录，保存主观察年月、姓名、年龄、班级/学期和观察者快照。

### 领域

`listening_domain` 通过 `record_id` 逻辑关联主记录。每个领域可有独立年月、三个工作日、目标、综合评价和支持策略。

### 图片

`listening_image` 每领域最多三张，`domain + image_index` 对应领域日期。图片先做方向归一和压缩，再保存 BLOB/对象键及 AI 描述。

### 指标

`listening_indicator_result` 记录 `record_id`、领域、`catalog_id` 和 1–3 星。
`indicator_catalog.sort_order` 与 Word 模板行序绑定，不能随意重排。

保存、覆盖和删除必须把主记录、领域、图片、指标作为一个业务聚合处理。一对一倾听和游戏观察的聚合 service/use-case 现由 Unit of Work 持有事务，内部 repository 仅 `flush()`；失败注入测试验证中途失败时新建全回滚、覆盖保留旧聚合。新增聚合路径必须沿用同一边界，不能在内部 repository 提交。

## 9. 自制教玩具与课程审议

`homemade_teaching_toy` 保存班级/教师快照、名称、材料、玩法和可选 AI 原始 JSON。

`course_review_activity` 保存：

- 活动元数据和原始教案。
- 拆分后的目标、准备、过程。
- 是否调整、调整说明、修订字段和审议原因。
- 完整二次修改稿和可选 AI 原始 JSON。

两者均以可编辑结果为业务事实，AI 输出不是不可修改的权威。

## 10. 导出记录

`export_records` 是只增记录，保存文件名、路径，并可逻辑关联以下一种业务记录：

- `daily_plan_id`
- `observation_id`
- `listening_record_id`
- `homemade_teaching_id`
- `course_review_activity_id`

当前数据库未强制“只能一个关联非空”。新增写路径必须测试不生成歧义记录。

## 11. 租户与用户不变量

Repository 必须满足：

1. ID 不是授权信息；按 ID 查询仍需 tenant 过滤。
2. UI 用户资源按可信 session 回查得到的 tenant/user 查询；API 读取仍以独立 API principal 的 tenant 为权威，不与 UI JWT 混用。
3. 更新和删除与读取使用相同的隔离条件。
4. 子表不能只凭 `record_id` 操作；同时验证 tenant/user。
5. `indicator_catalog` 是租户级参考数据，不使用 user_id。
6. 测试至少包含“同 ID 不存在”“另一 tenant 不可见”“另一 user 不可见（适用时）”。

## 12. 时间与历史

- 业务日期使用 `date`；审计/创建更新时间使用 UTC 意图。
- MySQL/SQLite 对 timezone-aware `DateTime` 的保存行为需在集成测试中核对。
- 历史记录保存配置快照，不在读取时用当前设置覆盖。
- 提示词和 AI Key 用 active + 历史行管理；切换 active 应在事务中完成。

## 13. Agent Foundation 与确认写入的数据边界

当前有 18 张 ORM 业务表。`b7d9e1f3a5c2` 为 `daily_plan` 增加 revision，`c1a8e4f6b2d9` 修复
SQLite `user.id` 自增类型，当前 head `e5f7a9c2d4b6` 只增加
`daily_plan_operation_version` 与 `agent_write_audit` 两张 W006 evidence 表及其不可变 trigger。
[ADR-0005](../ADR/ADR-0005-controlled-ai-agent-runtime.md) 确定 Agent Foundation 的零 Agent 持久化边界，该 Foundation 已合入
`main@ca3b7bd`。

F009 自动矩阵曾在其固定 `tested_code_sha` 动态反射包含 Alembic 版本表在内的 17 张实际 SQLite 表，
并验证成功、失败、取消、超时、stale、越权、断开和重启不产生 Agent 持久化。两类人工摘要也只对该 SHA
有效。W006 自动矩阵把两张新 evidence 空表纳入动态 baseline，并继续证明 Foundation READ/DRAFT
对其零写入；其 fixed SHA `253d37d…` 已闭合本地/CI/service 验收与 Issue 门。这不刷新旧 Foundation
人工证据，旧结果仍只能作为历史证据。

以下对象只能作为当前 operation 的内存 DTO：

- `AgentContext` 和裁剪后的业务事实。
- 当前 operation/turn/call ID 及有界消息窗口。
- `ToolResult` 和 `PlanPatch`。

不新建 conversation、message、thread、run、embedding、vector、summary、profile 或供应商 thread 映射表，
也不在 `daily_plan`、preview 或导出记录中隐式保存 Agent 草案。未确认、取消、超时、作用域变化或应用退出
后的 Patch 直接丢弃；成功确认只留下下面两张表定义的版本/最小审计，不保存完整 Patch 或 Provider 正文。

[ADR-0006](../ADR/ADR-0006-trusted-ui-session-and-confirmed-agent-write.md) 与独立 spec 已冻结并实现 W005/W006 的条件：

- `daily_plan` 使用显式单调 revision；`updated_at` 和内容哈希都不能代替它。
- `daily_plan_operation_version` 保存可核对的完整操作前业务快照和受保护字段路径。
- `agent_write_audit` 保存最小不可变 action audit，不保存密钥、隐藏 Prompt、完整 Patch 或不必要的幼儿正文。
- 确认必须逐次绑定 session/actor/Patch/turn/target/revision/before/expiry，并在短事务中原子完成版本、CAS 更新与审计；已知失败全回滚。

当前 confirmation store 与生产 WRITE service 已实现；确认材料仍只在进程内短命保存。W007 采用 UI 已固定
稳定 RED 并正在 GREEN 实现，但尚未闭合 Review/CI/人工验收；Provider/Tool 仍恰好四 READ + 两 DRAFT，
也没有 conversation、长期 Patch 或新的通用 WRITE 表。

## 14. 迁移链

当前单线迁移从空 smoke revision 开始，依次覆盖用户、设置、AI、每日计划、提示词、导出、游戏观察、
一对一倾听、自制教玩具、课程审议与 Agent WRITE evidence，当前工作树 head 为 `e5f7a9c2d4b6`。
`b7d9e1f3a5c2` 以 `a6c4d8e2f9b1` 为 down revision，为 `daily_plan` 增加带服务器默认 1 和正数约束的
`revision`；现有行回填为 1，并建立 SQLite/MySQL trigger 强制 INSERT 从 1 开始、UPDATE 必须有业务内容
变化且恰好 `OLD + 1`；downgrade 先移除 trigger，再移除约束与列。

`c1a8e4f6b2d9` 以 `b7d9e1f3a5c2` 为 down revision，只在 SQLite batch-recreate `user`，把历史
`BIGINT PRIMARY KEY` 修复为 `INTEGER PRIMARY KEY`，保留既有用户、复合唯一约束和 tenant 索引；MySQL
继续使用原有 `BIGINT AUTO_INCREMENT`，upgrade/downgrade 均不改变 MySQL schema。

`e5f7a9c2d4b6` 以 `c1a8e4f6b2d9` 为 down revision，创建精确 14 列的
`daily_plan_operation_version` 与精确 17 列的 `agent_write_audit`；后者对 `confirmation_id`、
`nonce_sha256` 分别使用单列唯一约束。SQLite/MySQL 均各建四个 UPDATE/DELETE 拒绝 trigger；downgrade
先移除 trigger 再移除两表。MySQL `snapshot_json` 使用 `LONGTEXT`。真实 MySQL 8 往返和触发器行为仍属于
W008 独立人工门。

验证要求：

- 全新 SQLite：upgrade head。
- 已有支持版本：upgrade head，并验证数据保留。
- MySQL 专属 enum/BLOB/alter 行为：真实 MySQL 验证。
- PyInstaller：迁移路径和应用数据库路径必须解析到同一个文件。
- 禁止通过编辑旧迁移伪造新 head；已发布 schema 用新 revision 演进。

## 15. 已知模型债务

- 多处使用逻辑外键，数据库无法自动阻止孤儿数据。
- active 唯一性多由业务层保证，竞争写入时需要事务测试。
- 表时间戳类型/默认实现不完全统一。
- `export_records` 没有 `updated_at`，属于明确的不可变例外；仓库总规则应承认该例外。
- 可信 UI session 已恢复并进入分支/远端 CI，但当前会话不落独立 server-side session 表，后续撤销/运维策略需以独立需求收紧。
- W005/W006 已闭合逐次确认、操作前版本、不可变审计和原子 CAS；W007 产品 UI 正在 GREEN 实现，真实
  MySQL 8 与最终固定 SHA 可见验收仍属未进入的 W008。
