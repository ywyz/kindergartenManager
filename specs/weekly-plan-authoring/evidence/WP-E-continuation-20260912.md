# WP-E 续作现场复验（2026-09-12）

状态：**BLOCKED / NOT COMPLETE**。本轮未修改产品代码，未执行 WP-F。

代码仍为 `9cde71655c30cafdc6ac4e99ed22509ad989b121`；原文档后继
`7c0acb9337534d0db60b9ff6d9e1abd09e382643`。新隔离工作树
`/home/ywyz/code/km-wpe-continuation-20260912`，分支
`feat/wp-e-continuation-20260912`。本记录是未提交的补充材料，不冒充新的代码冻结。
外部证据：`/home/ywyz/code/km-wpe-continuation-evidence-20260912`。

## 现场完整性与授权

读取本轮用户授权、AGENTS、ADR-0011、spec §2.2–2.7、tasks WP-E/F、本地契约、
交付清单和跨模块独立复审。再次核验 WP-E 829 材料、33 代码、13 文档 hash，
WP-D 318 材料、28 代码、16 文档 hash，全部一致。两个后继的代码/文档角色保持。
现场唯一 Alembic head 为 `d375e9ab2148`，没有真实数据库迁移。
14 个既有工作树的 HEAD/status/index hash 及初始脏文件 hash 均未变化；原 WP-E 外部
清单也再次验证通过。细节见 `integrity-final.json` 和 `preservation-before.json` / `preservation-after.json`。

WP-C 四类历史 native 双 RED 缺口继续 UNMET；用户允许继续 WP-E 本地工作的授权
继续有效。原 177/178 raw hash 与 JSON 重写时序解释已重读，不补写 PASS。
未从本地分支推断远端；未访问远端 CI/OCI/数据库/云端页面，未调用真实模型或读取真实 key，
未写 Issue、push、PR、合并、部署或发布。

## 本轮验证与证据角色

Main 在独立受保护运行目录重跑 14 个专项文件，**170 passed / 12 warnings**，
覆盖人员、来源、WP-D 应用、WP-E 保存/导出/迁移/缩减/UI callback/实际 LO pipeline。
日志为 `local-chain-configured.log`；本轮实际执行命令与14文件hash的Main回执见
`local-chain-configured.json`；lint/format分别见 `lint.log` / `format.log`，
diff/head见 `checks.json`。使用原 WP-E `.venv`，日历包实际为 1.11.0。
原代码未改变，因此不将本轮专项复验冒充新的全仓/Foundation/MySQL重跑；此前完整回归
与两库证据仍是其原有执行角色。范围 lint/format 与 diff 检查通过。

首次数据目录祖先权限拒绝，以及使用主工作树虚拟环境缺日历包/隔离字体导致的失败，
分别保留在 `local-chain.log`、`local-chain-retry.log`，属于环境错误，不计业务 RED。
本轮未确认新产品缺陷，未制造修复前 RED 或将初次覆盖改写为历史 RED。

新 `8096` 实例源码逐件绑定，实际浏览器补验登录/首页入口、共享周打开、重复来源选择/
差异拒绝、缺项生成/采用、单字段重生成/拒绝、显式保存、实际一页检查、第二教师打开
保留已保存人员与正文。详见 `browser-observations.md`；这是 Main 实际观察记录，
不是完整原始 AX 导出，也不是全分支/云端/Word PASS。

独立 reviewer 只读审阅 qualification/Word/composition，20 项局部测试通过；报告
`qualification-review.md`。Main复核后，reviewer撤回“Word client与LO renderer冲突”
的推导：二者本来就是独立字段。合成生产角色 manifest 的接线验证不是真实 Word 资格。
最终未确认这部分新的代码缺陷。默认空 catalog 是失败关闭；应用注入 seam 存在，
正式运营材料/安装/恢复路径仍未实际交付，不能称正式导出已通过。

## 仍未关闭

- 当前 Word 产品/版本的原生五/六列完整矩阵与独立资格材料尚未取得；历史 long 三份
  两页 FAIL、compact 合成候选不变。不能以本轮 LO 一页代替。
- 正式 released binding、完整独立 Word 材料及可信 catalog 安装输入尚未提供；未安装
  任何正式资格。是否将独立完整矩阵报告摘要纳入 catalog，须在材料可用后逐项核对。
- 本轮浏览器仍未覆盖单来源、全部漂移、等待中取消、候选过期、commit_unknown、双会话
  并发及新轮真实超页→有限缩减→显式保存/重检/手改全链，不能升级旧观察为本轮完整覆盖。
- exact-SHA CI、OCI、云端浏览器、真实模型、凭据/真实迁移等未获对应执行授权，保持 BLOCKED。

继续使用 `WP-E-continuation-prompt.md`。不生成 `WP-F-next-prompt.md`，不回写或关闭 Issue。

补证独立只读复审见外部 `documentation-review.md`：14测试源hash及14工作树前后明细一致，
先前命令/保全明细的文档缺口已关闭；该结论不扩大产品或外部门状态。
