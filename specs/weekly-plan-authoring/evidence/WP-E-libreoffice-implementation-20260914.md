# WP-E LibreOffice 资格适配与本地验证（2026-09-14）

状态：**LO 资格适配与本轮本地验证完成；WP-E 整体 OPEN。**用户已授权本轮跳过 Windows，使用 LO，允许子代理和 OpenCode 完成本地续作。生产部署、远端发布及 Issue 回写不在本轮执行范围。

基线 `c69b9e4435c0a70c4801836cb3d901728216af0e`，工作树 `/home/ywyz/code/km-wpe-libreoffice-20260914`，分支 `codex/wp-e-libreoffice-20260914`。主仓库及上一交付树保持，原未提交流程决策复制到新树；保护快照位于 `/home/ywyz/code/wp-e-lo-coordination-20260914/preservation-before.json`。

## 本轮契约

`weekly-layout-qualification.v1` 增加明确的 `libreoffice-rendered` role。该类型的 client 与 renderer 必须同为 LibreOffice 且产品/版本完全相等；报告 role/client/renderer 与 manifest 严格一致。历史 `word-native` 资格保持兼容；`local-synthetic` 只用于显式隔离 authority。`native-report.json` 是沿用的文件键，不表示 LO 报告由 Microsoft Word 生成。

四项受信运维环境输入、默认无资格拒绝、released binding、模板/材料哈希、5/6列两fixture、运行时版本复验与交付锁继续适用。教师没有新增资格入口。LO 审阅通过的材料只在隔离本地环境演练普通启动，不代表生产已安装。

## 执行证据

- OpenCode CLI 1.18.30 / `opencode-go/glm-5.3-flash` 在指定工作树实现；首次 503 转发错误没有修改文件，进程级清除大小写代理变量后连通并完成。未改全局代理配置。Main 审查实际 diff；子代理分别只读审查契约、真实 LO 材料，并编写一次性集成验证脚本。
- OpenCode 原代码双 RED 各为 5 failed / 12 passed；两次测试源 SHA256 都是 `8043b3eb9b8d06a811aea88438e31388066bc3451bdf15eaad519ee2db08b722`。Main 从 JSON 工具事件重建该源并核对 hash，见外部 `red-test-source.py`、`red-source-provenance.json`。失败原因包括原 authority 拒绝新增 LO role；已有负向通过不回填成 RED。
- 首次实现后两个漂移测试先被测试夹具自身 client/renderer 版本不一致拦截，OpenCode 修正夹具默认值及错配用例后 17 passed。因此其首份总结“测试源从 RED 到 GREEN 未变”不成立，已由 Main 指出并要求纠正；保留原始日志，不改写。随后补充 local_only 拒绝两种正式 role 的 2 项覆盖并格式化，新文件最终为 19 项。新增/修正覆盖没有倒填为原双 RED。
- Main 独立调用：`env -u WPC_MYSQL_PORT -u DATABASE_URL -u KM_WEEKLY_LAYOUT_MANIFEST -u KM_WEEKLY_LAYOUT_SHA256 -u KM_WEEKLY_LAYOUT_TENANT_ID -u KM_WEEKLY_LAYOUT_ACTIVATE PYTHONPATH=. /home/ywyz/code/km-wpe-startup-handoff-20260913/.venv/bin/python -m pytest tests/test_wpe_libreoffice_qualification.py tests/test_wpe_word_authority.py tests/test_wpe_startup_qualification.py -q`，cwd 为本工作树；退出码 0，**48 passed in 3.50s**，日志 `main-focused-tests.log`。这组使用合成资格 bytes，正向启动读取实际 LO 版本；其中既有 authority 用例运行真实 LO 渲染。无真实业务数据库/真实 AI。
- Main 对两个改动 Python 文件 Ruff check 通过；authority 另做 Ruff 格式修正，并用 AST 比较确认行为完全相同，未为格式改动重复行为测试。OpenCode 自行运行的邻近29项只作为其自检，未叠加到 Main 计数。
- 实际环境为 Python 3.14.7、chinesecalendar 1.11.0、LibreOffice 26.2.5.2 620(Build:2)，`fc-match SimSun` 返回 `SimSun,宋体`，未安装字体或依赖。Main 初次误用包名 `chinesecalendar` 作 import 得到 ModuleNotFoundError，改用其实际模块名 `chinese_calendar` 后确认包已安装；不是缺依赖或业务 RED。

## 真实 LO 材料与普通启动链路

四份 normal 均由独立子代理实际查看已存在的 LO PNG，并结合 PDF 页面/文字边界、输入、DOCX OOXML 核对：A4纵向1页、正文宋体12pt/固定20pt、全部文字可见、五六列/假期/多人名及固定数量正确。八份 long 仍为2页。复用原渲染材料，不声称它们是本次新代码重新生成；当前五份 renderer/契约源码 hash 与原 manifest 一致，authority 改动不涉及填充或渲染算法。

- 独立材料报告：`/home/ywyz/code/wp-e-lo-coordination-20260914/lo-material-review.md`，SHA256 `831db670c312075c2cde25b367c9422c9967e832cb8a27b8ee101b31a12711b5`。
- Main 选择 `five-normal` / `six-sunday-normal`，保持原 DOCX/PDF/PNG 字节，另建 `libreoffice-rendered` 报告和 catalog；不修改原 Windows handoff 中的 NOT_RUN 字段。
- 新 catalog：`/home/ywyz/code/wp-e-lo-coordination-20260914/reviewed-lo-catalog/manifest.json`，独立预期 SHA256 `ddf9c3d54a64f8ee75e7cf312ea99750640ca2caa8933085c2ca75a601de0faf`。记录 `catalog-review.json` 和一次性组装脚本同在外部协调目录。该 catalog 使用真实 LO 文档材料、合成教学输入；不是测试里伪造的 artifact bytes。
- Main 实际运行子代理编写的一次性集成脚本 `test_lo_runtime_acceptance.py`：普通 loader 和 production composition 不替换 authority、不伪造 renderer；临时 SQLite 经 Alembic 升级，受信运维配置只激活租户11，真实已保存版本检查/导出无新增版本且恰有1条导出审计。另一个全新合成场景验证长文缩减显式采用只改页面，保存后重检仍超页，导出拒绝且无成功审计。**2 passed in 5.93s**，退出码0；日志 `main-runtime-tests-ready.log`，精确 argv/cwd/data-dir 见 `runtime-invocation.json`。
- 首次集成收集被 app-data 祖先权限门拒绝：`/home/ywyz/code` 为775；这是环境前置失败，没有执行产品用例。没有改祖先权限，另用 `mkdtemp` 创建0700目录 `/tmp/km-wpe-lo-runtime-20260914-n8eiyaah` 后运行通过。首份失败日志 `main-runtime-tests.log` 保留；不同环境两次结果不混淆。
- 测试导出 DOCX 仅保存在外部 `runtime-artifacts/`，不提交业务文档或字体。这里证明应用字节交付和审计链路，不宣称浏览器收到文件。

## 当前代码身份与交付

本轮没有提交、推送或创建PR。HEAD `c69b9e4435c0a70c4801836cb3d901728216af0e` 是基线，**不是包含本次改动的新 tested_code_sha**；测试对象为该基线上的工作树，绑定以下最终文件 SHA256：

| 文件 | SHA256 |
|---|---|
| `app/service/shared_weekly/layout_authority.py` | `ce006dbc80ab226c462f40f4bda0ebaec7ae3334b6ac2d7e89a3bd0caf5f7ab0` |
| `tests/test_wpe_libreoffice_qualification.py` | `793dc2e94eca44bbcdd344679e92bcd4ec809249cf2d840fec0d3fdc940f2cbd` |

外部 `tested-worktree-source.json` 记录基线与源hash。只改一个产品模块、新增一个测试模块，并更新当前需求/任务/状态/契约入口与本轮记录。主仓库和前一交付工作树的 HEAD、status及既存修改文件hash均实测保持。

## 剩余范围与内容决定

旧合成服务 PID1869693 已不存在，18778 无监听，旧浏览器 tab 也已关闭；旧候选不恢复、不冒充当前可用。旧 `/tmp/km-wpe-synthetic-20260913` 数据保留。本次资格集成演练使用新的临时 SQLite 场景，与旧 plan6 无关，不重置旧数据以绕过缩减次数。

用户尚未回答本轮已展示的23字段缩减规则确认；`focus.0–2` 历史三条确认仍保持，整份旧候选采用/保存/重检未执行。新集成测试中的显式采用仅为自动化合成夹具，不代表用户内容采用。八份历史长文两页 `layout_overflow` 保留，不能交付成单页成功。

Windows 为 `SKIPPED_BY_USER`，不是本轮阻塞项；生产资格安装、真实 AI、远端 CI/镜像/云端/部署及 WP-F 未执行，不用本地结果宣称整个 WP-E 或 #77 完成。
