# KindergartenManager 当前人工测试矩阵

> 每次验收记录固定 SHA、构建来源、平台、数据库和外部服务。历史账号管理测试已不适用于当前单用户 UI。

## 1. 记录头

```text
日期：
验收人：
Git SHA / tag：
构建来源：源码 / Windows installer / Windows portable / deb / Linux portable / Docker
操作系统：
Python/应用版本：
数据库：SQLite / MySQL（版本）
AI：mock / 真实文本模型 / 真实视觉模型
Word：Microsoft Word / LibreOffice / 未执行
```

## 2. 启动与迁移

- [ ] 全新数据目录启动，迁移到 `a6c4d8e2f9b1`。
- [ ] `/` 跳转 `/home`，没有登录表单。
- [ ] `/home`、`/settings` 可打开；旧 `/setup` 立即跳转 `/settings`。
- [ ] 重启后 SQLite、自动密钥和已保存 AI 配置可继续使用。
- [ ] 迁移失败时明确记录实际行为，不能只记“页面打开”。
- [ ] 日志不含 AI Key、数据库密码或完整幼儿图片内容。

## 3. 基础配置

- [ ] `/settings` 保存学期名称、起止日期。
- [ ] 保存年级、班级、教师、室内区域和户外内容。
- [ ] 日期面板正确显示教学周、星期和节假日状态。
- [ ] 节假日 API 不可用时出现降级提示，主流程仍可继续。
- [ ] `/settings` 分别保存/脱敏文本与视觉 AI Key，并验证连接失败/成功提示。
- [ ] `/prompts` 可创建版本、切换 active 和回滚。

## 4. 每日活动计划

- [ ] 选择日期后周次/星期正确。
- [ ] 粘贴教案后拆分目标、准备、重点、难点、过程。
- [ ] 年龄适配保留原文并生成可编辑适配稿。
- [ ] 晨间活动、晨间谈话、区域、户外、反思可生成/编辑。
- [ ] 保存后重开仍一致。
- [ ] Word 使用 `teacherplan.docx`，字段、中文字体和差异红字正确。
- [ ] 导出记录与业务记录关联正确。

## 5. 游戏观察

- [ ] 上传 1–3 张合法图片；无效/过大文件被拒绝并友好提示。
- [ ] 视觉 AI 生成目标、记录、评价、策略，教师可编辑。
- [ ] 保存、历史查询、重新导出正常。
- [ ] Word 中图片、文本、中文字体和布局正确。
- [ ] 另一 tenant/user 的 ID 不可见（数据库/API 级测试环境）。

## 6. 一对一倾听（当前优先闭环）

- [ ] 五领域 Tab、独立年月与三个工作日正确。
- [ ] 一键导入至少 15 张，按文件名分配，每领域 3 张，多余图片有明确提示。
- [ ] 图片统一横版，预览/AI/保存/Word 一致。
- [ ] 单领域生成和全部领域生成可控，失败不覆盖已填内容。
- [ ] 指标星级、评价、支持策略可编辑并保存。
- [ ] 历史详情、载入编辑、覆盖保存、取消编辑、删除均正确。
- [ ] 合并 DOCX、按领域 ZIP、批量按领域 ZIP 正确。
- [ ] Word 指标打勾位置、日期、图片、中文和分页正确。

## 7. 自制教玩具

- [ ] 正确读取年级、班级和教师快照。
- [ ] AI 生成名称、材料、玩法并允许编辑。
- [ ] 保存、历史、重新导出正常。
- [ ] `homemadeteaching.docx` 字段和中文格式正确。

## 8. 课程审议

- [ ] 输入活动信息和原始教案。
- [ ] AI 拆分与审议调整结构正确，可编辑。
- [ ] 保存、历史详情、重新导出和删除正常。
- [ ] `coursereviewactivity.docx` 使用第一张空白表，不保留示例内容。
- [ ] 二次修改稿、调整布尔值和理由与保存内容一致。

## 9. 只读 API

- [ ] `/api/v1/health` 可访问且不暴露敏感信息。
- [ ] 未配置 `API_KEYS` 时业务端点返回 401。
- [ ] 正确 Key 只能读取其 tenant。
- [ ] 错误 Key、错误/过期 HMAC 返回 401。
- [ ] 列表过滤、分页和 404 行为正确。
- [ ] 响应不含密码、AI Key、内部导出路径或图片 BLOB。

## 10. 安全与网络

- [ ] frozen 桌面版只监听 `127.0.0.1`。
- [ ] 源码/Docker 暴露范围符合验收环境，未把无登录 UI 直接暴露公网。
- [ ] `.env`、`.kindergarten_secrets`、数据库和 exports 权限合理。
- [ ] Compose 已覆盖所有示例默认密码。
- [ ] 上传、AI、导出异常不在 UI/日志显示密钥或 traceback。

## 11. 受控 AI Agent Foundation（F009）

> F003-F008 已实现并固定 GREEN；以下 F009 验收尚未闭合。自动矩阵、Linux 浏览器 mock 与真实模型必须
> 分开记录，任何一项未执行都不得把 MT-011A/B/C 全部填为通过。

### 11.1 通用记录与零写入边界

- [ ] 先固定 `tested_code_sha`（完整 40 位）；其后不得再修改产品代码、自动测试或 manual helper。
- [ ] 每日活动计划显示“仅生成建议，不会保存或修改当前计划。”，可提交问题、观察运行、取消和丢弃。
- [ ] Agent 卡内只有运行、取消、丢弃；没有采用、保存建议、确认写入、“总是允许”或隐藏 WRITE handler。
  页面其他合法业务按钮不属于 Agent 卡，验收时不得点击。
- [ ] 草案显示 Tool、字段路径和 before/after；文本建议/草案/丢弃/失败/取消后页面正文均不变。
- [ ] 自动矩阵在初始化/seed 后动态反射实际数据库全部表，覆盖受保护文件/exports、独立 audit logger、
  seed 后 DML/DDL attempts、配置/Context/plan/Provider/Tool 失败、四类取消、跨 tenant/user、prompt injection、
  未知/WRITE、busy/reentry、三类 timeout、stale、mutation 发布窗口、断开/关闭与 restart 无恢复。
- [ ] 人工步骤前后比较 SQLite 全表逻辑摘要、exports 摘要和 Git 状态；不得把 SQLite 物理文件 hash 当作
  零写入证据，也不得把原始日志、业务正文或凭据粘贴到 Issue。

### 11.2 Linux 浏览器 mock

- [ ] 从仓库根启动；数据库位于 `/tmp/km-f009.*`，应用端口 `127.0.0.1:18080`，mock 端口
  `127.0.0.1:18081`；启动前确认端口未被占用。
- [ ] 只使用虚构 `ENCRYPTION_KEY`、`JWT_SECRET` 和 text Key；mock Key 经现有 `save_ai_key()` 加密保存到
  临时数据库。不得读取真实应用 AI 配置，不得通过设置页改写仓库 `.env`。
- [ ] mock fail-closed 校验 Authorization 存在且匹配虚构值、请求路径正确、恰好六个双下划线 wire Tool，
  且没有 `store`、`parallel_tool_calls`；mock 不记录 Authorization、system Context 或业务正文。
- [ ] 文本场景先显示运行态，随后显示建议；丢弃后建议消失，正文不变。
- [ ] DRAFT 场景显示 `daily_plan.draft_section_patch`、`activity_goal` 与字段差异；丢弃后正文不变。
- [ ] cancel 场景先显示“正在取消”，终态显示已取消；超过 mock 延迟后迟到标记仍不出现。
- [ ] A→B→A 切日后 scope/正文始终对应当前日期，旧 assistant/Patch 和迟到标记不回填。
- [ ] 运行中刷新或离开页面，超过延迟后返回；不恢复旧消息/草案，再次文本运行成功，证明 busy 已释放。
- [ ] 迁移、seed、虚构 Key 保存和 Settings 权限收敛后、首次 Agent operation 前取得 baseline；停止应用后，
  实际数据库全部表逻辑摘要、exports 摘要、Git 状态和正文证据均与 baseline 相等；只终止本次捕获 PID，
  回写证据后再删除已验证前缀的临时目录。

### 11.3 应用安全配置真实模型

- [ ] 在 `tested_code_sha` 的隔离临时 worktree/SQLite 中 seed 合成计划；由用户亲自在该临时应用
  `/settings` 保存真实 active `text` 配置。脚本和浏览器自动化不得读取、复制或键入 Key/endpoint/密文。
- [ ] POSIX `.kindergarten_secrets` 为 `0600`，配置可由 repository 解密；设置保存与权限收敛完成后、首次
  Agent operation 前取得 baseline。任一条件不满足时记录 `BLOCKED` 与 `network_requests=0`，停止且不得
  改用环境变量临时注入真实 Key。
- [ ] 只从 `DailyPlanAgentController.run()` 发起，由 coordinator 短命取得配置；不导出/显示 Key，不直接
  构造 Provider，不调用 `/models`，不切换凭据或自动重试。
- [ ] 使用不含真实幼儿/教师信息的合成计划，先请求一次最短文本响应；如需证明 Tool loop，仅再请求一次
  不超过 20 字的一日反思 DRAFT。
- [ ] 只记录时间、`tested_code_sha`、`key_type=text`、模型名、终态、Patch 数量/字段路径，以及 DB/exports/UI
  正文前后逻辑摘要。不得记录 endpoint、Key、密文、assistant/Patch 正文、request ID、HTTP/HAR、system
  Context 或 Tool 参数。
- [ ] 文本为 `SUCCEEDED`，可选 DRAFT 为 `DRAFT_READY`；页面正文、全部业务表、version/preview/audit、
  exports 均不变。
- [ ] 如失败，仅摘录固定 adapter/Runtime 阶段，以及可选 HTTP 状态码、关闭 `finish_reason` 或关闭
  `transport_reason`；不得记录原始异常类型或消息及其他敏感上下文，同一 `tested_code_sha` 不重试。
- [ ] adapter 不使用独立 HTTP transport timeout 抢先于 Runtime；真实模型等待只受既有 Provider/total
  Runtime 上限与 host/page/scope 取消约束，不通过浏览器延时或同 SHA 重试放宽门禁。

### 11.4 证据闭合

- [ ] Linux mock 写入 `specs/agent-foundation/evidence/f009-linux-browser-mock.md`；真实模型写入
  `specs/agent-foundation/evidence/f009-real-model.md`。两份文件必须引用同一个 `tested_code_sha`，真实模型
  必须为 `PASS`。
- [ ] 提交两份证据后记录新的 `evidence_closure_sha`；最终 Standards/Spec Review 0/0、Quality success 与
  Issue #48 回写均绑定该 closure SHA。验收后不得再修改产品代码；如修改，必须生成新的 tested code SHA 并
  重做两类人工验收。

## 12. 打包与升级

每个平台独立记录：

- [ ] 安装/解压、首次启动、浏览器打开。
- [ ] 数据目录不位于只读安装目录。
- [ ] 升级保留数据库、密钥、模板和导出访问。
- [ ] 卸载不会静默删除业务数据，或已明确提示。
- [ ] Windows Defender/权限提示与文档一致。
- [ ] Docker 重建容器后 volume 数据保留。

## 13. 结果表

| 编号 | 场景 | 结果（通过/失败/未执行） | 证据 | 备注/Issue |
|---|---|---|---|---|
| MT-001 | 启动与迁移 |  |  |  |
| MT-002 | 基础配置 |  |  |  |
| MT-003 | 每日活动计划 |  |  |  |
| MT-004 | 游戏观察 |  |  |  |
| MT-005 | 一对一倾听 |  |  |  |
| MT-006 | 自制教玩具 |  |  |  |
| MT-007 | 课程审议 |  |  |  |
| MT-008 | API |  |  |  |
| MT-009 | 安全与网络 |  |  |  |
| MT-010 | 平台打包/升级 |  |  |  |
| MT-011A | Agent 自动零持久化矩阵 |  |  | 必须绑定 tested code SHA |
| MT-011B | Agent Linux 浏览器 mock |  |  | 必须绑定 tested code SHA |
| MT-011C | Agent 安全配置真实模型 |  |  | BLOCKED/未执行均不等于通过 |
