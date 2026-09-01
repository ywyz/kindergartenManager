# KindergartenManager 安全威胁模型

> 适用基线：当前本地账号/JWT/RBAC UI、可选 MySQL/Caddy、只读 `/api/v1`、AI/节假日外部接口和 Word/图片数据。

## 1. 保护资产

- 幼儿姓名、年龄、观察文本、绘画/活动图片。
- 教师姓名、班级、学期和教学计划。
- AI API Key、外部 API Key、HMAC secret、数据库凭据。
- SQLite/MySQL 数据库、迁移状态和备份。
- Word 导出及其本地路径。
- 提示词、AI 原始响应、审计和错误日志。
- 计划中 Agent 的短期 `AgentContext`、`ToolResult`、`PlanPatch` 和 operation/turn 身份。
- 发布包、模板和迁移脚本的完整性。

## 2. 信任边界

```text
不可信网络
  │
  ├─ Caddy / 直接暴露的 NiceGUI 端口
  │      ├─ UI（本地账号 + JWT + RBAC；匿名注册关闭）
  │      └─ /api/v1（Key/HMAC）
  │
  ├─ AI / Holiday 外部服务
  │    └─ Agent Provider（只返回文本/不受信 Tool call）
  │
本机/容器
  ├─ 应用进程与内存中的明文 Key
  ├─ Agent Runtime / Closed Tool Registry / 短期 Context
  ├─ SQLite/MySQL
  ├─ 用户数据目录与 .kindergarten_secrets
  ├─ 图片 BLOB
  └─ exports / DOCX
```

当前最大的边界事实：UI 已恢复本地账号登录、active 用户重读、JWT `jti` 会话与 RBAC，但这不能替代
TLS、强密码、受控 Bootstrap/轮换和网络访问控制。桌面 frozen 模式只监听回环；源码和 Docker 模式可能对局域网/公网开放。

## 3. 威胁分级

| 等级 | 含义 |
|---|---|
| 严重 | 可批量泄露幼儿数据/密钥、跨租户读取、远程接管或不可恢复数据损坏 |
| 高 | 单个租户敏感数据泄露、认证绕过、恶意导出或持久化破坏 |
| 中 | 局部隐私泄露、拒绝服务、审计缺失或错误降级 |
| 低 | 不影响数据机密性/完整性的可用性与信息暴露 |

## 4. 重点威胁与控制

### 4.1 UI 凭据、会话或权限边界被绕过

- 威胁：弱/复用的 Bootstrap 管理员密码、被盗 JWT、停用/降权后仍存活的旧标签页，或错误端口映射导致未授权操作。
- 当前控制：匿名注册不挂载；管理员只能显式 Bootstrap；受保护页面重读 active 用户并执行 RBAC；JWT 包含唯一 `jti`
  与 `auth_epoch`，退出、停用、降权、重新登录或改密后的旧会话会失效；frozen 模式监听 `127.0.0.1`。
- 2026-08-31 已验收：生产 Bootstrap 管理员恢复/标准轮换、旧凭据拒绝、旧会话失效和最终凭据重新登录。
- 必须补强：持续验证生产 TLS、强密码和网络限制；停用、降权、普通业务旧标签页和完整业务矩阵仍需真实浏览器回归。目标页语义自动化超时不能由上述人工可见登录验收替代。

### 4.2 API Key 泄露与重放

- 威胁：仅 API Key 的请求可被复制；Key 进入日志、代理或脚本历史。
- 当前控制：未配置时业务 API 关闭；每个 Key 绑定 tenant；可启用 HMAC 和时间窗；比较使用常量时间函数。
- 必须补强：生产强制 HMAC、TLS、Key 轮换和最小日志；评审重放窗口内的 nonce/幂等需求。

### 4.3 跨租户/跨用户访问

- 威胁：攻击者修改 ID、user_id 或查询参数读取他人记录。
- 当前控制：API principal 提供 tenant；repository 广泛使用 tenant_id；测试已有隔离线索。
- 必须补强：所有 get/update/delete 的负向越权测试；禁止信任调用方提交的 tenant_id；子表按 tenant/user/parent 联合验证。

### 4.4 AI Key 与数据库凭据泄露

- 威胁：密钥进入数据库明文、日志、异常、Graphify、导出或 Git。
- 当前控制：Fernet 加密 AI Key、脱敏显示、自动 secrets 文件。
- 必须补强：服务器显式密钥、文件权限、备份/轮换流程；日志脱敏测试；禁止打印完整数据库 URL。

### 4.5 恶意或错误 AI 输出

- 威胁：模型返回错误 JSON、提示注入、不适当内容，或覆盖教师原始输入。
- 当前控制：integration 结构化解析、超时/重试、教师可编辑、保存原文/结果。
- 必须补强：把所有 AI 内容视为不可信；限制长度/类型；失败不覆盖既有内容；避免把幼儿不必要信息发送到模型；记录供应商/数据处理决策。

### 4.6 图片与文档隐私

- 威胁：图片/Word 泄露、路径遍历、恶意 Office 内容、临时文件残留。
- 当前控制：图片压缩与类型元数据、固定模板、应用生成文件名。
- 必须补强：验证上传大小/MIME/解码；导出目录权限；安全文件名和原子写；清理临时文件；真实数据不进入测试/仓库。

### 4.7 迁移与数据损坏

- 威胁：迁移失败后应用继续写入不兼容 schema；SQLite 文件被同步/复制时不一致。
- 当前控制：Alembic 单线显式迁移；迁移和镜像变更前验证 owner-only、短期、绑定当前镜像且 artifact hash 可复算的恢复证据；应用/Bootstrap 启动零迁移。
- 必须补强：完成 SQLite/MySQL 一致备份生产与隔离恢复演练；全新/升级/回滚测试；数据库 readiness 仍按 Issue #54 独立闭合。

### 4.8 逻辑外键孤儿与误删

- 威胁：删除主记录后图片、指标或导出记录残留；错误 tenant 的子记录被删。
- 当前控制：观察和倾听聚合保存/覆盖/删除由 service/use-case 持有 Unit of Work，repository 只 flush，
  并以失败注入和 tenant/user 隔离测试守卫回滚与越权。
- 必须补强：继续做孤儿扫描和其余单记录路径审计；评审是否引入数据库 FK。

### 4.9 供应链与发布

- 威胁：宽松依赖解析、被篡改 Action/镜像、未验证安装包。
- 当前控制：`requirements.txt` 显式安全下限、`uv.lock` 精确快照、Dependabot、tag 构建、GitHub Release；
  2026-08-31 的当前锁刷新与历史告警映射见 [DEPENDENCIES.md](../DEPENDENCIES.md)；发布资产新增
  `docker-image.json` 和不可变引用条目，降低“同 tag 重映射”带来的回滚/审计偏移。
- 必须补强：锁定依赖/哈希、常规质量 CI、Action 固定 SHA 或治理策略、产物校验值、目标平台安装验收。

### 4.10 Agent prompt/Tool injection 与权限扩大（已实现，持续门禁）

- 威胁：教案、班级配置或模型输出中的文本诱导 Agent 忽略规则、伪造 actor/Permission、
  请求未知/WRITE Tool，或将文件、URL、SQL、MCP/插件动态加入 registry。
- 设计控制：Runtime 按精确名称从关闭 registry 选 Tool；Schema 拒绝额外参数；actor 来自受信 UI Context；
  Foundation 只登记 4 READ + 2 DRAFT，Provider/Adapter 不执行 Tool。
- 验证门禁：固定 Foundation 测试已覆盖 prompt injection、伪造 tenant/user/Permission、未知 Tool、额外参数和越界字段；
  后续受影响代码变化必须在新 SHA 重跑。

### 4.11 Agent 数据外泄与长期副本（已实现，持续门禁）

- 威胁：Context/ToolResult/Provider 原文包含密钥、绝对路径、幼儿身份、图片、完整历史或无关班级，
  并进入日志、数据库、备份、向量库或供应商托管 thread。
- 设计控制：每 turn 通过 READ Tool 重建最小裁剪 Context；不保存对话、thread、embedding、summary、profile、
  Patch 或隐藏摘要；错误、repr 和运行诊断不包含正文。
- 验证门禁：F009 固定 SHA 证明 Key、路径、图片、无关租户/用户和完整历史不进入 Context/log/repr，
  应用重启后无 Agent 状态可恢复；后续受影响代码变化必须重跑。

### 4.12 Agent 过期结果、资源消耗与未授权写入（已实现，持续门禁）

- 威胁：教师切换日期/页面或修改内容后，迟到的 Agent 结果覆盖当前内容；模型递归 Tool loop 耗尽资源；
  DRAFT 隐式写入 preview、audit、版本或数据库。
- 设计控制：Foundation 使用单 operation、串行 Tool call、次数/长度/超时/总时限；校验 operation/scope/fingerprint 并丢弃
  迟到结果，`PlanPatch` 只在内存展示。W007 的本地应用层只允许当前页面一份 Patch 经逐次显式确认后写入，
  不改变 Provider/Tool 能力面。
- 验证门禁：固定 Foundation/F009 证据覆盖 busy、取消、超时、超限、页面/日期切换和迟到响应；W007 另以
  session、plan id、revision、before hash、短事务 CAS、不可变审计和 commit-unknown 对账门禁保护，后续变更仍须重跑。

## 5. 安全不变量

1. 不把真实密钥、数据库、照片、导出或 `.env` 提交到 Git。
2. UI 必须保持本地账号/JWT/RBAC、active 重读、`jti`/`auth_epoch` 失效与匿名注册关闭；任何非回环暴露还必须有 TLS、强密码和网络控制。
3. API 业务端点默认关闭；生产同时使用 TLS、API Key 和 HMAC。
4. 所有业务查询以可信 tenant 为边界；资源 ID 不是授权。
5. AI 输出不自动成为不可修改事实；教师通过当前页面的显式确认决定是否采用一份 Patch。
6. 迁移和备份必须可恢复；迁移失败必须 fail-closed，不能用“页面启动成功”代表数据库健康。
7. 日志与审计不记录密钥或完整幼儿图片/文档内容。
8. Agent Foundation 只装配 ADR-0005 的六个 READ/DRAFT Tool，未知和 WRITE Tool 始终拒绝。
9. Agent Context 是当前 operation 的最小短期快照；不建立对话或向量记忆。
10. Agent Foundation DRAFT 不修改 UI 正文或任何持久化状态；过期、取消和迟到结果必须丢弃。W007 的 WRITE
    只由本地应用层显式确认流程执行，Provider/Tool 仍无 WRITE。

## 6. 生产前门禁

- [ ] 在已完成生产管理员轮换/旧会话失效验收的基础上，继续复验 RBAC、停用、降权、普通业务旧标签页、完整浏览器矩阵及网络暴露策略。
- [ ] 全量 tenant/user 越权测试通过。
- [ ] SQLite/MySQL 迁移和备份恢复通过。
- [ ] AI/图片/Word 的敏感数据流完成评审。
- [ ] API HMAC、TLS、Key 轮换和日志脱敏验证。
- [ ] 依赖与容器扫描、常规质量 CI 通过。
- [ ] Windows/Linux/Docker 目标部署分别验收。
- [ ] 发布 tag、source SHA、`docker-image.json`、OCI index digest、不可变引用和回滚说明可逐项收敛；部署只切镜像，不回滚 migration 或删除卷。
- [ ] 数据库 readiness 按 Issue #54 独立验收；`/api/v1/health` 不得作为数据库可接流量证据。
- [ ] Agent Foundation 的关闭 Tool/Schema、tenant/user 裁剪、无长期记忆、零写入、取消/过期和 prompt injection 门禁
  按固定 SHA 证据通过；W007 本地确认写入另按 ADR-0006 的 CAS/审计/回滚门禁复核。

## 7. 非目标

本文不宣称当前系统满足特定监管认证，也不替代园所的数据保护制度。若引入公网、多园 SaaS、家长端、云图片或第三方身份，应重新做威胁建模。
