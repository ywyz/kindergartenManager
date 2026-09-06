# 全局白天/夜间模式切片

状态：本地 GREEN，待 exact-SHA 远端与生产门（从 `182646344f023dfc7ff022d4360272e8a6b420f5` 开始）

## 范围

- 所有已认证页面共用的 `app_shell` 与 `render_shell` 顶栏提供“白天模式”和“夜间模式”。
- 默认模式为白天；非法或缺失的浏览器偏好回退白天。
- 切换立即影响 NiceGUI dark mode、header、drawer、正文背景/文字/边框，以及主题控件的 hover/selected 状态。
- 偏好只保存在当前站点的浏览器 `localStorage`，值严格为 `day` 或 `night`；不写数据库、NiceGUI user storage、用户资料或服务端业务状态。

## 存储判断

NiceGUI 3.16.0 的 `app.storage.browser` 是加密 cookie，且初始请求提交后不能再修改；它不适合作为顶栏点击后的偏好写入 seam。本切片使用 NiceGUI 官方 `ui.run_javascript` 在同源浏览器 `localStorage` 中保存固定非敏感枚举，并使用官方 `ui.dark_mode` 应用模式。浏览器禁用或拒绝 `localStorage` 时仍保持当前页面模式，不影响登录或业务操作。

## 非目标

- 不新增数据库字段、Alembic migration、用户资料字段、服务器业务写入、外部 CDN 或遥测。
- 不修改登录/session/JWT、菜单权限、路由导航或 Agent Foundation/W007 行为。
- 不实施 WMP-7、WMP-8、WMP-9、模板 active、正式导出或任何周/月业务。

## 验收

组件测试覆盖默认白天、白天→夜间→白天、非法值归一、两种 shell 共享 renderer、同源本地枚举、语义色对比度与敏感信息不泄漏。Linux 浏览器验收使用隔离临时 SQLite、合成账号和 Google Chrome，实际覆盖导航、刷新、非法值、两个浏览器上下文、hover/selected 和截图证据。
