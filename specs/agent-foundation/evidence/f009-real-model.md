# F009 应用安全配置真实模型人工验收证据

- 结论：PASS
- 执行日期：2026-08-25（Asia/Shanghai）
- `tested_code_sha`：`a50c6f6b9aa941996052c59a301a7a40bdbd706f`
- 平台：Ubuntu 24.04；Google Chrome 151.0.7922.173
- 隔离边界：与 mock 不同的全新 detached linked worktree、SQLite 和 `/tmp/km-f009.*` 运行目录；
  seed 不创建 AI 配置，也未读取、复制或注入旧配置、`.env`、endpoint、Key 或密文。

## 安全配置与请求门禁

- 用户亲自在隔离应用 `/settings` 的文本模型表单保存现有安全配置；浏览器自动化没有读取、复制或键入
  endpoint、Key 或密文。
- 保存前 preflight 因 active text 配置为 0 安全 BLOCKED，helper 网络请求为 0；没有用环境变量、直构
  Provider、`/models` 探测、配置切换或重试绕过门禁。
- 保存后 preflight：PASS；active text 配置恰好 1 个，`key_type=text`，模型名 `mimo-v2.5`；secrets 与
  secrets lock 均为普通 `0600` 文件；helper 网络请求仍为 0。
- 第一个 Chrome 标签在请求输入前已不存在，浏览器控制在 `fill` 阶段失败，运行按钮从未点击、网络请求仍为
  0。随后在同一隔离应用打开新标签、重新选择计划 A，并取得与原 baseline 完全一致的恢复后 baseline。

## 唯一真实模型请求

- 用户在原 baseline 后已明确确认发送；标签恢复只重建同一计划 A 的可见页面并再次证明 baseline 完全相同，
  其间没有执行 Agent operation。
- 动作时间：`2026-08-25T06:30:33.238Z`（Asia/Shanghai `2026-08-25 14:30:33.238`）。
- intent：最短合成文本，只要求模型回复固定的验收短语；证据不记录模型回复正文。
- 通过每日计划页面的公开 Agent Controller seam 点击运行恰好 1 次；没有重试、模型探测、配置切换或第二个
  DRAFT 请求。
- 可见终态：`SUCCEEDED`；运行态曾出现；Patch 数量为 0；11 个页面正文控件逐字段不变。
- 未记录 endpoint、Key/密文、assistant/Patch 正文、request ID、HTTP/HAR、system Context 或 Tool 参数。

## 零持久化复核

- baseline/final 11 字段 UI digest：
  `f60b310f364f07ed2ebbc42df25722f524125f26f2550d8bfb0cb053c99b9acb`
- baseline/final 全逻辑 snapshot：
  `bdb45487c2106c1de1cc0a60ee126461701936206d46f56d494c3c1f8ca5f0af`
- 动态覆盖 17 个实际数据库表、受保护文件、exports、Git porcelain 与 11 字段 UI 正文；自动化矩阵另行
  覆盖独立 audit logger 和 seed 后 DML/DDL attempts。
- compare：`changed_sections=[]`、`equal=true`。
- 四份最终比较所用脱敏摘要文件 mode 均为 `0600`。
- 应用已停止，Chrome 验收标签已关闭；原始应用日志、凭据和模型正文未写入仓库或 Issue。

此文件只记录上述 `tested_code_sha` 的人工证据；不把它外推到任何后续产品代码 SHA。
