# KindergartenManager 数据模型

> 审查基线：`dev4.0@0657c3a`；最近产品主线：`main@225fe139`；Alembic head：`a6c4d8e2f9b1`。

## 1. 建模原则

- 所有 schema 变化通过 Alembic。
- 主键使用 `BIGINT`，SQLite 下变体为 `INTEGER` 以支持自增。
- 所有 16 个 ORM 表均有 `tenant_id`。
- 除 `user` 与租户级参考表 `indicator_catalog` 外，其余 14 个 ORM 表均有 `user_id`。
- 除只增不改的 `export_records` 外，模型通常包含 `created_at` 和 `updated_at`。
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
- 当前单用户 UI 只依赖默认 `admin` 记录；保留表不等于登录已启用。

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

原文与适配稿必须同时保留，Word 导出的差异标红依赖两者。

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
2. UI 用户资源按固定 tenant/user 查询；API 读取以 API principal 的 tenant 为权威。
3. 更新和删除与读取使用相同的隔离条件。
4. 子表不能只凭 `record_id` 操作；同时验证 tenant/user。
5. `indicator_catalog` 是租户级参考数据，不使用 user_id。
6. 测试至少包含“同 ID 不存在”“另一 tenant 不可见”“另一 user 不可见（适用时）”。

## 12. 时间与历史

- 业务日期使用 `date`；审计/创建更新时间使用 UTC 意图。
- MySQL/SQLite 对 timezone-aware `DateTime` 的保存行为需在集成测试中核对。
- 历史记录保存配置快照，不在读取时用当前设置覆盖。
- 提示词和 AI Key 用 active + 历史行管理；切换 active 应在事务中完成。

## 13. Agent Foundation 的数据边界

当前 16 张 ORM 表中没有 Agent 表，当前 Alembic head 也不包含 Agent 迁移。
[ADR-0005](../ADR/ADR-0005-controlled-ai-agent-runtime.md) 确定 Agent Foundation 不改变这一事实。
F009 自动矩阵动态反射了包含 Alembic 版本表在内的 17 张实际 SQLite 表，并证明成功、失败、取消、超时、
stale、越权、断开和重启路径均不增加或修改 Agent 持久化状态；两类人工验收的前后逻辑摘要也完全相等。

以下对象只能作为当前 operation 的内存 DTO：

- `AgentContext` 和裁剪后的业务事实。
- 当前 operation/turn/call ID 及有界消息窗口。
- `ToolResult` 和 `PlanPatch`。

不新建 conversation、message、thread、run、embedding、vector、summary、profile 或供应商 thread 映射表，
也不在 `daily_plan`、preview、audit 或导出记录中隐式保存 Agent 草案。取消、超时、作用域变化或应用退出后
相关对象直接丢弃。

未来 Agent WRITE 不能依赖 `updated_at` 或内容哈希伪装业务 revision。它至少需要：

- `daily_plan` 显式单调 revision。
- 可核对的操作前版本和受保护字段路径。
- 最小不可变 Agent action audit，不保存密钥、隐藏 Prompt 或不必要的幼儿正文。

这些都必须在独立 ADR/spec 中冻结并使用新 Alembic revision；当前不预留空表、字段或猜测迁移编号。

## 14. 迁移链

当前单线迁移从空 smoke revision 开始，依次覆盖用户、设置、AI、每日计划、提示词、导出、游戏观察、一对一倾听、自制教玩具和课程审议，head 为 `a6c4d8e2f9b1`。

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
- UI 固定单用户与保留用户表并存，恢复认证前需要重新确认所有数据所有权语义。
- `daily_plan` 没有可供将来 Agent WRITE 使用的显式单调 revision；这不影响只读/草案 Foundation，
  但是 WRITE 的硬门禁。
