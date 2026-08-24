# F009 人工验收辅助

本目录只服务于 F009 的 Linux 浏览器 mock 与安全配置真实模型验收。辅助脚本不增加或执行 Agent WRITE，
不保存会话，也不代替浏览器可见断言、真实模型 PASS、双轴 Review 或精确 SHA Quality。

## 共同安全门

1. 先固定完整 40 位 `tested_code_sha`；固定后不得再改产品代码、自动测试或本目录 helper。
2. mock 与真实模型各自在该 SHA 的全新 detached linked worktree 中运行。worktree 根的 `.git` 必须是文件，
   Git 状态必须干净，且初始不得有任何类型的 `.env`、`.kindergarten_secrets` 或
   `.kindergarten_secrets.lock` 项；不要从主工作树复制它们。
3. 运行目录必须由 `mktemp -d /tmp/km-f009.XXXXXX` 创建，SQLite、脱敏摘要和进程日志都留在该目录；不得
   把原始 app/mock 日志贴入 Issue。
4. `f009_seed.py seed` 在所有 `app`/配置 import 前完成以上检查。seed 只用合成用户、班级、学期和 A/B
   两日计划。mock 模式仅通过现有 `save_ai_key()` 保存源码内固定的虚构 text Key；real 模式不创建 AI 配置。
5. 只终止本次捕获的 PID。验收、摘要比较和证据回写完成后，才删除已人工核对为 `/tmp/km-f009.*` 的运行
   目录和隔离 worktree。不得使用宽目录、glob 或未解析变量做删除目标。

所有命令都从隔离 worktree 根执行。下文的 `TESTED_SHA`、`RUN_DIR` 是操作者显式核对后的值，不要用缩写 SHA。

## Helper 提供的证明

`f009_seed.py snapshot` 使用 SQLite 只读事务动态枚举全部非 SQLite-internal 实际表。每表只输出列/schema
摘要、行数和规范化行摘要；BLOB 只进入长度与 SHA-256，绝不输出单元值。它还输出：

- `.env` / `.kindergarten_secrets` 的存在类型、mode、长度和内容摘要，以及 secrets lock 的类型、mode、
  长度；不输出任何正文；
- exports 的路径摘要、长度/内容摘要，不输出文件名或内容；
- Git porcelain 字节流的条目数与摘要，不输出路径；
- 调用方 UI 正文规范 JSON 的长度与摘要，不输出字段正文。

SQLite/WAL/journal 的物理文件 hash 从不作为零写入证据。`compare` 必须返回 `equal: true`；任何
`changed_sections` 都是失败，不能人工忽略。

为便于先停应用再取 final DB 摘要，可在应用仍可见时把 UI 正文 JSON 通过 stdin 交给 `ui-digest`；它只写
`0600` 的长度/hash 文件。正文不得通过命令行参数、普通临时文件或 Issue 传递。UI JSON 必须精确包含页面
实际显示的 11 个正文控件：`activity_goal`、`activity_prep`、`activity_key`、`activity_difficult`、
`activity_process_original`、`activity_process_adapted`、`morning_activity`、`indoor_area`、
`outdoor_activity`、`morning_talk_topic`、`daily_reflection`。模型中的第 12 个字段
`morning_talk_questions` 当前没有独立页面控件，由同一次数据库全表逻辑摘要覆盖，不能在浏览器证据中伪造。

## Linux 浏览器 mock

先确认 `127.0.0.1:18080` 与 `127.0.0.1:18081` 空闲，再执行：

```text
python specs/agent-foundation/manual/f009_seed.py seed \
  --mode mock --tested-sha TESTED_SHA --database RUN_DIR/kindergarten.db
python specs/agent-foundation/manual/f009_seed.py preflight \
  --mode mock --tested-sha TESTED_SHA --database RUN_DIR/kindergarten.db
```

在两个单独终端启动关闭 mock 与产品真实 UI。两者都会再次核对 tested SHA、linked worktree、Git 清洁和
配置项不存在；应用 launcher 只绑定 loopback：

```text
python specs/agent-foundation/manual/f009_mock_server.py \
  --tested-sha TESTED_SHA --slow-seconds 8
python specs/agent-foundation/manual/f009_seed.py run-app \
  --mode mock --tested-sha TESTED_SHA --database RUN_DIR/kindergarten.db
```

mock 只接受固定 holiday GET 与 `POST /v1/chat/completions`。Chat 请求必须携带固定虚构 Bearer、固定模型、
恰好六个按既定顺序的双下划线 wire Tool，且 payload 只能有
`model/messages/tools/tool_choice/max_completion_tokens`；
`store`、`parallel_tool_calls`、错误路径或未知意图全部 fail closed。服务端日志只有递增计数和预定义场景名，
不会记录 Authorization、system Context、正文或 Tool 参数。

在浏览器选中 `2026-09-07`，确认计划 A 的 11 个可见正文控件后，在第一次 Agent operation 前捕获 baseline。
数据库摘要同时覆盖未独立显示的 `morning_talk_questions`。先通过 stdin 生成 UI digest，再用该 digest 生成
logical snapshot：

```text
python specs/agent-foundation/manual/f009_seed.py ui-digest \
  --output RUN_DIR/ui-baseline.json
python specs/agent-foundation/manual/f009_seed.py snapshot \
  --tested-sha TESTED_SHA --database RUN_DIR/kindergarten.db \
  --ui-body-digest RUN_DIR/ui-baseline.json --output RUN_DIR/baseline.json
```

浏览器按顺序执行并记录可见断言：

1. 卡片显示“仅生成建议，不会保存或修改当前计划。”，只有运行、取消、丢弃，没有 Agent 采用/保存/确认。
2. 输入 `F009_TEXT`：先见运行态，再见 `F009_MOCK_TEXT_OK`；丢弃后建议消失，正文不变。
3. 输入 `F009_DRAFT`：显示 `daily_plan.draft_section_patch`、`activity_goal` 与原值/建议；丢弃后正文不变。
4. 输入 `F009_SLOW_CANCEL` 后取消：先见“正在取消”，终态已取消；8 秒后不得出现
   `F009_LATE_CANCEL_MARKER`。
5. A 日输入 `F009_SLOW_SCOPE`，立即切 B 再切 A；8 秒后不得出现 `F009_LATE_SCOPE_MARKER`，scope 与正文仍
   对应当前 A 日。
6. 输入 `F009_SLOW_DISCONNECT` 后刷新或离开；8 秒后返回，不恢复旧消息/草案，也没有
   `F009_LATE_DISCONNECT_MARKER`；再次运行 `F009_TEXT` 成功，证明 busy 已释放。

最后在页面恢复 A 日、正文稳定时经 stdin 捕获 `ui-final.json`，停止本次 app PID，再取 final snapshot 并比较：

```text
python specs/agent-foundation/manual/f009_seed.py ui-digest \
  --output RUN_DIR/ui-final.json
python specs/agent-foundation/manual/f009_seed.py snapshot \
  --tested-sha TESTED_SHA --database RUN_DIR/kindergarten.db \
  --ui-body-digest RUN_DIR/ui-final.json --output RUN_DIR/final.json
python specs/agent-foundation/manual/f009_seed.py compare \
  --baseline RUN_DIR/baseline.json --final RUN_DIR/final.json
```

## 应用安全配置真实模型

使用同一 `tested_code_sha` 的另一个全新隔离 worktree 和新的 `/tmp/km-f009.*` 目录。seed 不读取、复制、输出
或键入任何真实 Key、endpoint 或密文：

```text
python specs/agent-foundation/manual/f009_seed.py seed \
  --mode real --tested-sha TESTED_SHA --database RUN_DIR/kindergarten.db
python specs/agent-foundation/manual/f009_seed.py run-app \
  --mode real --tested-sha TESTED_SHA --database RUN_DIR/kindergarten.db
```

real launcher 会移除子进程继承的 `ENCRYPTION_KEY`/`JWT_SECRET`，让隔离应用自己创建 `0600`
`.kindergarten_secrets`；它不读取或输出其正文。随后必须由用户亲自在该临时应用 `/settings` 正常保存真实
active `text` 配置。脚本和浏览器自动化不得读取、复制、键入 Key/endpoint/密文，也不得改用环境变量、直构
Provider、探测 `/models`、切换凭据或重试。

保存完成后、第一次 Agent operation 前执行非敏感 preflight；它只报告 secret/lock 文件类型与 mode、active
text 配置数量和模型名，不选择 endpoint、Key 或密文，也不发网络请求。它不会尝试解密真实 Key；后续唯一一次
Controller 成功才证明 coordinator 经 repository 解密并完成短命 Provider 装配：

```text
python specs/agent-foundation/manual/f009_seed.py preflight \
  --mode real --tested-sha TESTED_SHA --database RUN_DIR/kindergarten.db
```

若 secret/lock 不是普通 `0600` 文件、active text 配置数量不是 1，preflight 会以 `BLOCKED`、
`network_requests=0` 退出，F009 保持未完成。满足前置后，按 mock 相同方式捕获 baseline，只在每日计划
Agent 卡请求一次最短合成文本；可选地再请求一次不超过 20 字的一日反思 DRAFT。只能记录时间、完整 SHA、
`key_type=text`、模型名、终态、Patch 数量/字段路径和 DB/exports/UI 摘要；不得记录 endpoint、Key/密文、
assistant/Patch 正文、request ID、HTTP/HAR、system Context 或 Tool 参数。最终先捕获 UI digest，停止 app，
再取 final snapshot；`compare` 必须为 `equal: true`，且真实文本终态必须为 `SUCCEEDED`。

失败诊断只可从本地进程日志摘录固定 adapter/Runtime 阶段枚举，以及可选 HTTP 状态码或关闭
`finish_reason`；不得复制原始 app 日志。任何 URL、header、正文、异常、request id、模型输出或凭据都不能
进入证据。失败后仍不得在同一 `tested_code_sha` 重试。

两份证据分别写入既定 evidence 文件并绑定同一 `tested_code_sha`；不要把本目录 helper、原始日志或产品代码在
验收后继续修改。任何这类变更都会产生新 tested SHA，必须重做 mock 与真实模型验收。
