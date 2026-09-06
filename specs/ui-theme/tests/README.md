# UI 主题切片测试证据

## 稳定 RED

基线：`182646344f023dfc7ff022d4360272e8a6b420f5`（未修改生产代码）。

收集命令：

```text
.venv/bin/pytest tests/test_ui_theme.py --collect-only -q
```

结果：`9 collected`。

node-only hash（按 pytest 收集顺序的 9 个 node id，含换行）：`4807333be73b06a6ea91e298950d12ef91c4fcd7ba3f1607d61e3de4ab2c4eb6`。

连续运行两次：

| run | collected | passed | failed | failure node set | failure hash |
| --- | ---: | ---: | ---: | --- | --- |
| RED-1 | 9 | 0 | 9 | 9 个 `tests/test_ui_theme.py::test_*` | `465707c01b8e7c05e9f0381f5918cc636cd54055fe3eb1a189bd7aec124015f4` |
| RED-2 | 9 | 0 | 9 | 与 RED-1 相同 | `465707c01b8e7c05e9f0381f5918cc636cd54055fe3eb1a189bd7aec124015f4` |

失败仅来自尚不存在的主题公共 seam/共享 renderer/控件契约（`normalize_theme_mode`、主题常量/脚本/CSS 与 `_render_shell_chrome`）；无 skip、xfail、真实网络或真实凭据。

failure hash 计算方式：对 `pytest -q --tb=short` 输出中 `^FAILED ` 行按原顺序取 SHA-256。

## GREEN

初始组件 GREEN 连续两次均为 `10 collected / 10 passed / 0 failed`。

只读 reviewer 随后发现三个 Medium：非 POSIX 安全写入未 fail-closed、夜间语义蓝色对比度不足、真实浏览器证据缺失。Main 分别补稳定 RED 后修复：

- non-POSIX RED 连续两次 `1 failed`，证明会进入 `os.open`；修复后在无法证明 owner-only 创建语义的平台写入前失败关闭；
- 13 个实际使用的语义色 RED 连续两次 `13 failed`；修复后全部在 `#0f172a` 背景达到至少 4.5:1；
- 浏览器 evidence RED 连续两次 `1 failed`；真实 Chrome 运行还捕获并修复了 drawer/selected CSS 优先级问题。
- 最终复审的证据绑定与误连远端两个 Low 均先连续两轮 `2 failed`；修复后测试会复算每张 PNG 的
  magic、字节数和 SHA-256，浏览器 runner 也会在启动 Chrome 前拒绝非 HTTP loopback URL。

最终相关矩阵包含主题、shell、root/login session、敏感/业务页面 guard 与完整恢复演练，连续两次均为
`276 collected / 276 passed / 0 failed`。node-only hash（按 pytest 收集顺序的 node id，含换行）为
`fcf1025af740701e51cfe42c38f12f7aa06b51924785ed5e7e70b63cfe842e74`。

真实浏览器使用 Google Chrome `152.0.7977.82`、隔离临时 SQLite 和两个合成登录用户，覆盖默认白天、
白天→夜间→白天、导航/刷新保持、非法存储回退、独立浏览器上下文默认白天、主题存储无身份/凭据，以及
header/drawer/body/text/border/hover/selected。脱敏结构化结果与两张截图见 `../evidence/`；截图 SHA-256
由 `manual/browser_acceptance.cjs` 运行时复算。

runner 仅用于临时、合成数据环境，并强制 `THEME_BASE_URL` 为 HTTP loopback；输入验证发生在加载
Playwright 之前。`manual/package.json` 和 lockfile 将测试专用 `playwright-core` 固定为 1.57.0，可在
`manual/` 下执行 `npm ci --ignore-scripts`，再启动隔离应用并以环境变量传入合成账号密码：

```text
THEME_BASE_URL=http://127.0.0.1:<temporary-port> \
THEME_ADMIN_PASSWORD=<synthetic-password> \
THEME_TEACHER_PASSWORD=<synthetic-password> \
node specs/ui-theme/manual/browser_acceptance.cjs
```

本次证据使用当前安装的同版本受控运行时，`NODE_PATH` 指向其 `playwright-core` 模块目录；未下载浏览器，
而是使用 `/usr/bin/google-chrome`。

输出仅为 `evidence/browser-acceptance.json` 与两张 PNG，不包含账号、密码、token、tenant 或 user id。

初次全库为 `1142 passed / 1 skipped`。最终全库为 `1162 passed / 1 skipped`，Agent Foundation 为
`261 passed`；历史 F009/Agent 证据不覆盖本切片。
