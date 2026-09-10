# 当前状态：2026-09-11 WP-C 授权/教学日事实子步

WP-A 已限定关闭，#77/#75 仍 OPEN。本轮共享授权和必需教学日事实子步已本地实现并独立复审，
不是整个 WP-C、产品或云端验收完成。交付与验证只见[本轮账本](evidence/WP-C-authorization-20260911.md)。
下一步仅按[根/版本/CAS提示词](WP-C-root-next-prompt.md)另轮推进，本轮未实现。

- 公开续作基线为 `718b26c4a8249080c3f262b66b7f397e08e11b9f`，身份提交 `00afdc878b306475508c777997956cdf4638dbef`
  已是其祖先；相差三个提交，app/ 与 alembic/ 无差异。远端 handoff 再次 fetch 后未变。
- 当前代码仅本地 `59677fc656bab152485c0355f3470f5763951888`，工作区 `/home/ywyz/code/km-wpc-authorization-20260911`。
  未 push，无本轮远端 CI；不能提供此提交的 GitHub blob 链接。
- 源码 Alembic head 为 `7c91e2a4b610`，本步无 schema 改动或新 migration。一次性测试库不等于真实迁移。
- [Quality 34490160211](https://github.com/ywyz/kindergartenManager/actions/runs/34490160211) 的 success
  精确绑定公开收口 SHA `718b26c…`，只证明它的实际运行范围，不证明本轮代码、全分支 Ruff 或产品总验收。
- 本轮当前入口修改不继承 WP-A manifest/hash/Review；旧清单请按收口 Git revision 核验。

Word 为主要格式客户端；既有实测只覆盖 Microsoft 365 Word 16.0.20326.20132 x64。
最短完整五/六列可行性完成，三份 long 两页仍 FAIL；compact 仅合成候选。
LibreOffice 仅备用打开，历史16.9pt/分页/warning保留，不再要求补Linux格式实测。
正式模板资格、缩减和产品/云端验收仍未完成。[WP-A最终关闭评论](https://github.com/ywyz/kindergartenManager/issues/77#issuecomment-5620485046)。

本轮复用 IdentityApplication / IdentityRepository，唯一数据库 policy 增加 shared 专用内部路径；
旧个人周/月 policy 未放宽。服务端锁定日历数据、学期边界与当前 assignment 决定权限；
页面不能提交教学日列表或选择 legacy discriminator 自授。旧页面 stamp 每次重算核验，不是离线许可。
export 只验证政策，没有最终下载、正文读取或虚构成功导出审计。

根唯一性、不可变版本/CAS、日期占用、源逐日投影、显式映射、人工重复选择、快照、重导入仍逐项未执行。
WP-A移交的对应业务RED不能被身份或本轮授权GREEN抹去。WP-D完整日期/假期文案/结构/AI，
WP-E模板/填写/缩减/导出，WP-F云端/Word产品验收继续独立。
