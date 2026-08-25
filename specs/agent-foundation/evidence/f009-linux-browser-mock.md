# F009 Linux Chrome mock 人工验收证据

- 结论：PASS
- 执行日期：2026-08-25（Asia/Shanghai）
- `tested_code_sha`：`a50c6f6b9aa941996052c59a301a7a40bdbd706f`
- 平台：Ubuntu 24.04；Google Chrome 151.0.7922.173
- 隔离边界：全新 detached linked worktree 与 `/tmp/km-f009.*` 运行目录；初始无 `.env`、
  `.kindergarten_secrets` 或旧数据库复制；worktree 初始与结束均为固定 SHA 且 Git clean。

## 前置检查

- mock preflight：PASS。
- active text 配置恰好 1 个，模型名为 `f009-mock-model`；只使用 helper 源码内固定虚构 Key。
- secrets 为 absent；secrets lock 为普通 `0600` 空文件。
- helper 网络请求计数为 0；mock 与产品只绑定 loopback。

## Chrome 可见验收

在 `2026-09-07` 的合成计划 A 上建立 baseline，并依次核对：

1. Agent 卡显示“仅生成建议，不会保存或修改当前计划。”，卡片只有运行、取消、丢弃，无 Agent
   采用、保存或确认入口。
2. `F009_TEXT` 先显示运行态，再显示 `F009_MOCK_TEXT_OK`；丢弃后建议消失，11 个页面正文控件不变。
3. `F009_DRAFT` 先显示运行态，再显示 `daily_plan.draft_section_patch`、`activity_goal`、原值、建议值和
   复核提示；丢弃后页面正文不变。
4. `F009_SLOW_CANCEL` 先显示运行态，并通过页面内只读高频轮询捕获“正在取消”瞬态；终态为
   “本次运行已取消”。等待 8.5 秒后没有 `F009_LATE_CANCEL_MARKER`。
5. 计划 A 运行 `F009_SLOW_SCOPE` 后切换 B 再回 A；浏览器先后看见 B/A scope 与对应活动目标。等待
   8.5 秒后没有 `F009_LATE_SCOPE_MARKER`，当前 scope 为 `2026-09-07`，正文仍为计划 A。
6. 运行 `F009_SLOW_DISCONNECT` 后刷新；等待 8.5 秒后没有旧 intent、旧消息、旧草案或
   `F009_LATE_DISCONNECT_MARKER`。重新选择计划 A 后，`F009_TEXT` 再次经历运行态并成功，证明 busy
   已释放。

关闭 mock 计数共 7 次 wire request：text 2；draft 2（同一次 Tool operation 的 Provider 前后两轮）；
slow_cancel 1；slow_scope 1；slow_disconnect 1。不存在额外观察尝试、真实网络或真实凭据。

## 零持久化复核

- baseline/final 11 字段 UI digest：
  `f60b310f364f07ed2ebbc42df25722f524125f26f2550d8bfb0cb053c99b9acb`
- baseline/final 全逻辑 snapshot：
  `81601b80e0d3521b390704d9268dbca4ffe90e75c74dd9c44b260e21705c9040`
- 动态覆盖 17 个实际数据库表；exports 为 absent；Git porcelain 记录数为 0。
- compare：`changed_sections=[]`、`equal=true`。
- 四份脱敏摘要文件 mode 均为 `0600`。
- app 与 mock 已停止，Chrome 验收标签已关闭；未把原始日志、Authorization、Context、正文或 Tool 参数
  写入仓库或 Issue。

此文件只记录上述 `tested_code_sha` 的人工证据；不把它外推到任何后续产品代码 SHA。
