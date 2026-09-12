# WP-E 原生 Word 实测 2026-09-12

本轮在真实 Windows Word 中打开最终八份待验原件，逐件进入原生打印预览并观察全部页。结果为四份正常内容各一页、四份长中文各两页；长文实际单页 FAIL。正常文件只完成部分格式核验，不记整份 Word PASS。WP-E BLOCKED，WP-F NOT_RUN。

## 绑定与环境

- 产品代码：`0bded3377c01956833bcbb6cd306f9a7f5d924e1`；本轮开始文档后继：`7989da2825399ff60dc8ea34cd8e82321dcead24`。本轮没有修改产品代码。
- 候选批次：任务根目录下 `wp-e-header-week-20260912/candidates-final`；原 manifest SHA256 `8570185e52b0a9ca50ea298556ad6607ebc9014e66cc01f26716ffc4c76e7936`，不改写其生成时 NOT_RUN。
- Renderer SHA256 `6186fd0bc62ca8a31af2236645d22d07e7fbe8ee4a53069181b78638ba0240f7`；seed SHA256 `f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b`。仍为合成验收正文。
- seed 的源码声明 UUID `00000000-0000-0000-0000-000000000801`、version 8、contract `kg.template.weekly_activity_plan.candidate` v2 不证明当前 Ubuntu 云端 released 状态；正式资格与 catalog 安装 BLOCKED。
- OS：Windows Server 2025 Datacenter，24H2，26100.32860。用户明确接受此 Windows 验收环境。
- Word“账户”：Microsoft 365，2608，Click-to-Run build 20326.20132，当前频道。
- “关于 Word”：Microsoft Word for Microsoft 365 MSO，2608，Build 16.0.20326.20072，64 位。两处 build 分别记录，不混同。

## 原生观察矩阵

| 原件 | 原生全部页 | A4 纵向 | 实际单页 | 格式整体验收 |
|---|---:|---|---|---|
| five-normal | 1/1 | PASS | PASS | PARTIAL |
| five-long | 2/2 | PASS | FAIL | FAIL / 其余未全检 |
| five-holiday | 1/1 | PASS | PASS | PARTIAL |
| five-holiday-long | 2/2 | PASS | FAIL | FAIL / 其余未全检 |
| six-sunday-normal | 1/1 | PASS | PASS | PARTIAL |
| six-sunday-long | 2/2 | PASS | FAIL | FAIL / 其余未全检 |
| six-saturday-normal | 1/1 | PASS | PASS | PARTIAL |
| six-saturday-long | 2/2 | PASS | FAIL | FAIL / 其余未全检 |

每份完整页截图默认 50% 预览，正常五列另有 75% 上下细节。全部页已观察并不等于全部文字逐字、高倍率裁切和字体漂移检查完成。其他七份字体与段落属性对话框 NOT_RUN，不能从共用 renderer 外推。

五列正常样本：从主题行到末表格的正文选择已保存 selected-body 文本；原生字体对话框确认中文宋体、小四（12pt）、常规。正文整体段落对话框行距/值为空（混合），减去选择末尾后仍混合；单独“家园共育”段落确认固定值 20 磅。故固定 20pt 全文检查 PARTIAL，不能把这个局部样本等同全文 PASS。先前 OOXML 诊断仅为定位辅助，不能替代原生格式资格。

原生文本及页面覆盖了当前周次跟日期、左上空白、星期不附日期、多教师姓名、主题内空格、书名号、编号与换行的样本。五列假期、六列周日/周六的日期与假期空活动在原生页面可见；逐项完整数量对账、所有段落及高倍率字体漂移矩阵仍待补齐。`five-long-native-text.txt` 只是可访问的局部文本，不是全文证据。

## 独立原始材料

任务根：`C:/Users/admin/.codex/visualizations/2026/09/12/01a0937c-3f64-7ce2-98f9-fecd1934901c`。
本轮观察目录：`wp-e-native-final-20260912`。`native-matrix.json` 逐件绑定输出 hash、页数、观察文件和未验项，SHA256 `a2862f7b7a9914e060690c1a4b27b830693586947daeeeba67b69ec48ae65908`。
`evidence-manifest.json` 固定其生成时的 49 份原始/机器记录 hash；不包含它自身及后续独立复审。文档截图与格式对话框截图独立于原始 DOCX 保留。

全部八份 DOCX 在原生打开前与原 manifest 核对，打开后 `input-hashes-after-shared-read.json` 再次八项一致，未保存修改、未打印。最初 PowerShell Get-FileHash 因 Word 文件共享锁失败，产生 `input-hashes-after.json` 的 false；它是失败的读取尝试，不是内容漂移，由成功的共享只读核验明确取代，原失败记录保留。

自动审批拒绝保存包含邮箱/OneDrive 的完整账户界面，理由为超出必要版本核验范围；改为仅保存 `environment.json` 必要产品/版本/build，没有保存被拒绝的账户截图。

交付包校验仍为 `INTEGRITY_OK: 26 files; not Word or WP-E PASS`，未改清单。该 26 文件不含本轮 DOCX/原生截图，不代表完整外部证据已打包。main 与原未跟踪文件保留。

## 继续 WP-E

四份新长文两页结果作为本次真实超页输入保留，不覆盖历史 long 三份两页 FAIL 或 compact 合成候选。后续按现行页面流程执行有限缩减、原文差异、显式采用/保存、再次原生检查以及仍超页时手改；本轮未执行该链，不能直接删文字或缩小字号把原件改判 PASS。

未验证的当前 released/catalog、目标页面全分支、真实模型、exact-SHA CI、不可变 OCI、迁移/部署与对应授权继续分别核对。WP-C 四类历史 native 双 RED 仍 UNMET，用户允许继续本地工作的决定不变。不生成 WP-F-next-prompt，不发布、推送或发送 Issue 消息。

## 独立只读复审

`preparation_review` 完成本轮有限原生观察复审：49/49 证据大小与 hash 一致，清单自身 SHA256 `e5b5062431403bd8a4830171eeeb0010fcb3ead2b800d3ccdda78cc6c7e65cf5`；共享只读重新计算 8/8 DOCX 与 8/8 body 均匹配。独立查看全部 12 页原生截图，支持四份正常单页 PASS、四份长文单页 FAIL，未发现需要纠正的通过状态。

复审确认字体截图支持所选正文宋体/小四/常规，整体行距为空、家园段固定 20 磅，因此全文仍 PARTIAL。50% 总览不足以完成逐字数量、细微裁切和字体漂移复审。账户/关于 Word 的产品版本由现场观察记录证明，未留存对应截图供此独立复审再次核验。该复审不构成正式资格、完整 Windows Word PASS 或 WP-E 关闭。
