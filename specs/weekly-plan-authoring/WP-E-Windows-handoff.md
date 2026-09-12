# WP-E Windows 续作交接（2026-09-12）

用户本次授权同步到仓库以切换 Windows。同步分支：
`feat/wp-e-continuation-20260912`。这是 WP-E 续作与 Word 材料交接，**WP-E 仍为
BLOCKED / NOT COMPLETE，WP-F 未执行**。push 不构成 PR、main 合并、部署、发布、
Issue 消息、真实模型或真实数据库迁移授权。

## Windows 获取

在已有仓库执行 `git fetch origin`，然后在新目录创建工作树，保留现有修改：

```powershell
git fetch origin
git worktree add --detach ..\km-wpe-windows origin/feat/wp-e-continuation-20260912
cd ..\km-wpe-windows
git rev-parse HEAD
py -3 specs/weekly-plan-authoring/validation/wp-e-handoff-20260912/verify_bundle.py
```

本工具仅使用 Python 标准库读取材料，不启动应用、不访问数据库。预期为
`INTEGRITY_OK: 26 files; not Word or WP-E PASS`。校验失败立即停止，不重写清单消除差异。
实际远端完整 SHA 以本次同步完成后的读回结果为准；不要把分支名当成代码验收 SHA。

## 已同步与材料角色

代码基线：`9cde71655c30cafdc6ac4e99ed22509ad989b121`。
原文档后继：`7c0acb9337534d0db60b9ff6d9e1abd09e382643`。
本次新增交接文件是文档/材料后继，不是新产品实现。当前代码唯一 Alembic head
`d375e9ab2148`；Windows 不执行真实业务库迁移。

- [WP-E 本地契约](WP-E-local-contract.md)、[本地交付](evidence/WP-E-20260912.md)、
  [续作复验](evidence/WP-E-continuation-20260912.md)、[继续提示词](WP-E-continuation-prompt.md)。
- `validation/wp-e-handoff-20260912/`：26份逐字校验副本，包括本轮170项专项日志/命令、
  保全前后清单、实际浏览器观察、独立复审，以及原WP-E/WP-D关闭回执和历史差异解释。
- 副本中 Linux 绝对路径、未提交/尚未push描述均保留其记录时状态；`manifest.json`给出
  副本相对路径与原位置。历史摘要中“全部829/318材料核验”不表示整套材料已打包：
  完整原始tar/运行日志仍保留在Linux外部目录，没有全量上传。
- 不包含真实凭据、业务数据库、运行时配置、原生Word资格或本轮新生成的Word待验DOCX。
  仓库中的WP-A旧候选只保持历史角色，不能用于替代WP-E当前代码资格。

## Windows 下一步

继续 WP-E，先读取本文件、最新用户授权、AGENTS、ADR-0011、spec §2.2–2.7、
tasks WP-E/F、本地契约、交付/续作记录、便携副本及独立复审；重新校验SHA/hash/工作区。
原WP-C四类历史native双RED缺口保持UNMET，177/178原始hash与重写时序解释不变。

1. 确认可用Microsoft Word产品及“文件→账户→关于Word”的完整版本/内部版本号。
2. 定位当前正式受控模板与released UUID/version/contract/hash。仓库模板是核验输入，
   不能由本地文件推断当前云端released状态。缺少材料或相应读取授权时保留BLOCKED。
3. 在核实基线后，准备当前WP-E renderer输出的待验五/六列文件及逐项矩阵，然后用真实
   Word打开，记录正常/长中文、多姓名、空格、书名号、数量、日期、假期、换行与所有页原生
   预览，检查A4、宋体12pt、固定20pt、无裁切/字体漂移。Word客户端与运行renderer分别绑定。
4. 未实际验证的格子保持NOT_RUN/BLOCKED。long三份两页FAIL与compact合成历史不变；
   不能以LO、OOXML、PDF页数、文件清单或本便携校验替代Word。
5. 原生材料独立复审后，再核对可信catalog安装输入与目标授权；不得把local-synthetic
   catalog移作正式资格。剩余实际页面全分支、云端/CI/OCI/真实模型等仍各自分门。

缺少Word控制工具时由用户操作原生Word并提供全页观察材料。不要执行WP-F、写
WP-F-next-prompt.md、关闭Issue或把同步成功视为WP-E COMPLETE。
