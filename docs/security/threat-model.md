# KindergartenManager 安全威胁模型

> 适用基线：当前单用户 UI、可选 MySQL/Caddy、只读 `/api/v1`、AI/节假日外部接口和 Word/图片数据。

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
  │      ├─ UI（当前无登录）
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

当前最大的边界事实：UI 没有有效登录保护。桌面 frozen 模式只监听回环；源码和 Docker 模式可能对局域网/公网开放，因此不能把“单用户”误解为“自动安全”。

## 3. 威胁分级

| 等级 | 含义 |
|---|---|
| 严重 | 可批量泄露幼儿数据/密钥、跨租户读取、远程接管或不可恢复数据损坏 |
| 高 | 单个租户敏感数据泄露、认证绕过、恶意导出或持久化破坏 |
| 中 | 局部隐私泄露、拒绝服务、审计缺失或错误降级 |
| 低 | 不影响数据机密性/完整性的可用性与信息暴露 |

## 4. 重点威胁与控制

### 4.1 无登录 UI 被网络访问

- 威胁：源码模式监听 `0.0.0.0`；同网段或错误端口映射可让他人直接操作全部数据。
- 当前控制：frozen 模式监听 `127.0.0.1`；Docker 可由 Caddy/主机网络控制。
- 必须补强：默认部署文档明确网络限制；服务器场景恢复认证前不得公网开放 UI；增加启动警告或明确绑定配置。

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
- 当前控制：Alembic 单线迁移、异常日志。
- 必须补强：决定 fail-closed 策略；迁移前备份；全新/升级/回滚测试；SQLite 使用一致快照而非运行中直接复制。

### 4.8 逻辑外键孤儿与误删

- 威胁：删除主记录后图片、指标或导出记录残留；错误 tenant 的子记录被删。
- 当前控制：service/repository 显式清理和隔离测试。
- 必须补强：事务化聚合删除、失败回滚、孤儿扫描；评审是否引入数据库 FK。

### 4.9 供应链与发布

- 威胁：宽松依赖解析、被篡改 Action/镜像、未验证安装包。
- 当前控制：`requirements.txt` 显式安全下限、Dependabot、tag 构建、GitHub Release；
  2026-08-22 的基线和告警映射见 [DEPENDENCIES.md](../DEPENDENCIES.md)。
- 必须补强：锁定依赖/哈希、常规质量 CI、Action 固定 SHA 或治理策略、产物校验值、目标平台安装验收。

### 4.10 Agent prompt/Tool injection 与权限扩大（计划）

- 威胁：教案、班级配置或模型输出中的文本诱导 Agent 忽略规则、伪造 actor/Permission、
  请求未知/WRITE Tool，或将文件、URL、SQL、MCP/插件动态加入 registry。
- 设计控制：Runtime 按精确名称从关闭 registry 选 Tool；Schema 拒绝额外参数；actor 来自受信 UI Context；
  Foundation 只登记 4 READ + 2 DRAFT，Provider/Adapter 不执行 Tool。
- 验证门禁：用 prompt injection、伪造 tenant/user/Permission、未知 Tool、额外参数和越界字段建立稳定负向测试。

### 4.11 Agent 数据外泄与长期副本（计划）

- 威胁：Context/ToolResult/Provider 原文包含密钥、绝对路径、幼儿身份、图片、完整历史或无关班级，
  并进入日志、数据库、备份、向量库或供应商托管 thread。
- 设计控制：每 turn 通过 READ Tool 重建最小裁剪 Context；不保存对话、thread、embedding、summary、profile、
  Patch 或隐藏摘要；错误、repr 和运行诊断不包含正文。
- 验证门禁：证明 Key、路径、图片、无关租户/用户和完整历史不进入 Context/log/repr，应用重启后无 Agent 状态可恢复。

### 4.12 Agent 过期结果、资源消耗与未授权写入（计划）

- 威胁：教师切换日期/页面或修改内容后，迟到的 Agent 结果覆盖当前内容；模型递归 Tool loop 耗尽资源；
  DRAFT 隐式写入 preview、audit、版本或数据库。
- 设计控制：单 operation、串行 Tool call、次数/长度/超时/总时限；校验 operation/scope/fingerprint 并丢弃迟到结果；
  `PlanPatch` 只在内存展示，没有采用/保存路径。
- 验证门禁：覆盖 busy、取消、超时、超限、页面/日期切换和迟到响应；成功/失败均证明业务持久化零变化。

## 5. 安全不变量

1. 不把真实密钥、数据库、照片、导出或 `.env` 提交到 Git。
2. UI 当前无认证；任何非回环暴露都必须被明确识别和控制。
3. API 业务端点默认关闭；生产同时使用 TLS、API Key 和 HMAC。
4. 所有业务查询以可信 tenant 为边界；资源 ID 不是授权。
5. AI 输出不自动成为不可修改事实，教师拥有最终采用权。
6. 迁移和备份必须可恢复；不能用“页面启动成功”代表数据库健康。
7. 日志与审计不记录密钥或完整幼儿图片/文档内容。
8. Agent Foundation 只装配 ADR-0005 的六个 READ/DRAFT Tool，未知和 WRITE Tool 始终拒绝。
9. Agent Context 是当前 operation 的最小短期快照；不建立对话或向量记忆。
10. Agent DRAFT 不修改 UI 正文或任何持久化状态；过期、取消和迟到结果必须丢弃。

## 6. 生产前门禁

- [ ] 明确 UI 网络暴露和认证策略。
- [ ] 全量 tenant/user 越权测试通过。
- [ ] SQLite/MySQL 迁移和备份恢复通过。
- [ ] AI/图片/Word 的敏感数据流完成评审。
- [ ] API HMAC、TLS、Key 轮换和日志脱敏验证。
- [ ] 依赖与容器扫描、常规质量 CI 通过。
- [ ] Windows/Linux/Docker 目标部署分别验收。
- [ ] 发布 SHA、资产校验值和回滚说明可回读。
- [ ] 如实现 Agent：关闭 Tool/Schema、tenant/user 裁剪、无长期记忆、零写入、取消/过期和 prompt injection 门禁全部通过。

## 7. 非目标

本文不宣称当前系统满足特定监管认证，也不替代园所的数据保护制度。若引入公网、多园 SaaS、家长端、云图片或第三方身份，应重新做威胁建模。
