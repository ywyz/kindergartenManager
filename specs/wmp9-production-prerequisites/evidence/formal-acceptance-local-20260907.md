# WMP-9 本地阶段记录（2026-09-07，分阶段 BLOCKED）

## 状态和 SHA 边界

**WMP-9 仍为 BLOCKED。** 本文只记录隔离 localhost + MySQL + Chrome +
LibreOffice 的已完成本地阶段，不能作为云端验收、Microsoft Word 兼容性、发布或生产部署
的 PASS 依据。本文不是 evidence-closure，未回写 Issue #55/#56/#57，也没有新的 closure
SHA。

| 用途 | SHA | 已回读的 CI |
|---|---|---|
| 本轮 acceptance start | `01bf6349a7c6f5268eba4425212f546874d651b0` | [Quality 34127776649](https://github.com/ywyz/kindergartenManager/actions/runs/34127776649) success、[CodeQL 34127775586](https://github.com/ywyz/kindergartenManager/actions/runs/34127775586) success；两者 head SHA 均精确匹配 |
| ROADMAP 最小断行修复后的适用基线 | `44f676c97f18f607ecb85a20d9bbf2237cde4b38` | [Quality 34129801929](https://github.com/ywyz/kindergartenManager/actions/runs/34129801929) success、[CodeQL 34129801339](https://github.com/ywyz/kindergartenManager/actions/runs/34129801339) success；两者 head SHA 均精确匹配 |
| 合并游戏行内容修复后的新 tested-code 基线 | `bd2457a9df4a720b169268ec30976db666ab6713` | [Quality 34132227138](https://github.com/ywyz/kindergartenManager/actions/runs/34132227138) success、[CodeQL 34132225804](https://github.com/ywyz/kindergartenManager/actions/runs/34132225804) success；两者 head SHA 均精确匹配 |
| prerequisite tested-code | `72d759fc128b013c2345bd609875bb3e3d623ef1` | 仅是 prerequisite implementation gate 的 tested-code，不能替代本轮 tested-code |
| prerequisite evidence closure | `f07971d6624d7e9c032f21fe94a7415a55b0786c` | 仅是 prerequisite 的文档证据闭合，不能替代 `72d759f…` 或本轮 tested-code |

`01bf…` 是本轮开始时读取的 acceptance start，不是本轮 closure SHA。`44f…`
只合并 `docs/ROADMAP.md` 中“最终 exact-SHA 证据以本轮 Issue #56/#57 回写为准”的
断行。该变更超出旧 `cc3ebf8` 后代白名单，所以先作为独立适用基线并回读自身双 CI。

本地 UI 下载发现真实内容丢失后，`bd2457a…` 仅修改
`app/integration/word_export/released_weekly_monthly_word_port.py::_fill_weekly`，并新增
`tests/test_released_weekly_plan_game_completeness.py`。它把横向合并的户外/区域游戏行
各写入一次，按周一至周五标签序列化，未修改模板字节、binding/profile、parser、权限/会话、
schema、迁移或依赖。它是新 tested-code 基线，故 `44f…` 的 DOCX/PDF 只保留为 RED
证据，未复用作 `bd2457a…` 的 GREEN 证据。

prerequisite 两 SHA 自身 CI 再次回读一致：72d759f 的 Quality `34093237305` / CodeQL
`34093236646`；f07971d 的 Quality `34093871974` / CodeQL `34093872040`，均 success 且
headSha 精确匹配。Issue #55/#56/#57 的既有 closure comments
`5566521346` / `5566521923` / `5566522371` 与该门 75 节点双次/hash、Review 0/0/0、
SQLite/MySQL 8.4.11 迁移往返及 SHA 角色一致。本轮未修改这些 Issue。

原工作树的 `graphify-out/cache/last_query_stamp` 用户修改保留；工作在独立 worktree
`/tmp/wmp9-formal-acceptance`。每次 runtime 基线集成后均确认 clean、HEAD=origin/main。

## finding、稳定 RED 和最小修复

ROADMAP finding 先保持原失败测试不变，重现指定 exact-SHA 文字断行断言失败；最小合并后
完整 `test_wmp8_formal_exporter_red.py` 为 43 passed，只读 reviewer 无 H/M/L finding。
后续本轮 docs 契约与该 WMP-8 文件联合回归也通过，原失败测试始终未修改。


`templates/weekplan.docx` 的两张 9×7 表中，第 3、4 行的 weekday 内容格横向合并
col 2..6。旧 `_fill_weekly` 对每个 weekday 重复写这些相同格，后一次覆盖前一次。
通过 protected UI 下载的 `44f…` 正常/长中文 weekly DOCX 都只保留周五的
`outdoor_game` 与 `area_game`。

- `local/artifact_completeness_red.py` 对这两份原始 DOCX 连续两次 exit 1，报告周一至周四
  的两个字段均缺失；原始文件未覆盖。
- renderer 回归正常/长中文两节点也连续两次失败，直接证明 merged cell 的覆盖根因。
- 最小修复后，新 renderer 回归为 **3 passed**，包含 normal、long Chinese 和 empty
  optional weekday；后者确认空日保留为 `周三：` 的位置标签而不借用其它日正文、也不出现
  `None`。
- 独立只读代码复审为 H/M/L = **0/0/0**；它不等于 WMP-9 总门 Review。

## 自动回归（`bd2457a…`）

以下命令均在新 tested-code SHA 上执行；完整命令、exit 和原始输出保存于受保护归档
`/home/ywyz/wmp9-acceptance-evidence-20260907/wmp9-bd2457a-evidence/` 的同名日志及 `regression-results.json`。

| 集合 | 结果 |
|---|---:|
| 新 merged-game renderer 回归 | 3 passed |
| prerequisite 节点收集，连续两次 | 75 collected / 75 collected；node-only SHA-256 均为 `8bf5e9b3e25fda30ac498277dfba288a66a2e822dfad05a25fdb5f3c3b18279d` |
| prerequisite 节点运行，连续两次 | 75 passed / 75 passed |
| WMP-5 至 WMP-8 精确集合 | 155 passed |
| 完整 weekly-monthly specs 集合 | 272 passed |
| 已实施 Template Center 精确集合 | 239 passed |
| 权限、会话、审计、Word/export 精确集合 | 375 passed |
| 仓库 `tests/` | 1166 passed, 1 skipped |
| Agent Foundation | 261 passed |

本轮不会以 Template Center 全目录中的未授权 future RED 替代上述已实施门。此前因设置
`KINDERGARTEN_DATA_DIR` 导致 Agent Foundation fixture 路径不一致的运行器错误，已在不改变
产品/测试的情况下以 `env -u KINDERGARTEN_DATA_DIR` 复跑为 261 passed；该错误不能作为
产品 RED。

## 隔离本地运行和数据边界

本阶段使用独占 Docker 网络、临时 MySQL 8.4.11 和脱敏合成数据。
本地构建 app image ID 为
`sha256:38704c87b77c5ba0fe335b290ddb60a831fe75f2bb301fd7da21b54df8d48462`，
revision label 精确为 bd2457a；这是本地诊断镜像，不是已发布 OCI repository@digest。
MySQL 使用 `mysql@sha256:b3b90af2a6552ae30c266fdb7d5dd55f3afb72404bb78d37fe8a23eb857fd3fb`。数据库容器未发布主机端口；
应用仅绑定 host loopback 的临时端口。迁移从空库到 Alembic revision
`3c9f4b2a7d1e` 成功，seed 记录为 5 个合成用户、4 个 APPROVED current plans、16 个精确
scope grants，未在 seed 中调用 exporter。

应用 health 与 database readiness 分别返回成功。下载走真实 Chrome 登录和受保护 weekly/monthly
UI/application 入口；`docx-manifest.json` 标记源为 `protected UI Chrome download`。这并不把
local source/容器运行解释为云端 Caddy/HTTPS 验收或生产部署。

导出四份 DOCX 的专门零持久化快照为 `before-ui.json` 对 `after-four-docx.json`：所有表的
count/hash 都相同，其中 `export_records` 与 `weekly_monthly_audit_event` 均保持 0。之后的
工作流/权限 UI 操作刻意创建独立 fixtures、版本和无正文 audit，不能混入或反向解释为四次
导出的零持久化快照。

## 新基线的原始 DOCX 与 headless LibreOffice PDF

以下均为 `bd2457a…` 的 protected UI 原始下载。DOCX 未被覆盖；LibreOffice 以 headless
`writer_pdf_Export` 生成另一 PDF 制品，转换 exit 均为 0。

| 样本 | 原始 DOCX SHA-256 / bytes | PDF SHA-256 / bytes / 页数 |
|---|---|---|
| weekly normal | `88304a4f0316c7a831a6de35b409143c0b4ca284fec45452a1ef316933380c38` / 18,031 | `d083310d105cb8ef9b50f4790f274aefa5aef19983fce48824e500d7afab5aba` / 107,809 / 3 |
| weekly long Chinese | `e847ee8de66d8b25bf5c3a33f84d8b6f138b8bce250e962a723e6c1bd59abc57` / 24,162 | `8156fc7f23536fc165c4563e1f91aac29f0845d1022290c57aa4cedf218f1e28` / 539,986 / 57 |
| monthly normal | `bee626f3e1e5ae86589d496e04ae056167626d0c6f8d5700544cbe1be1c943dd` / 9,666 | `3599bdcd0fdcc182fef74a9f2f52f7585e8e29357148c4541827c4d1c2beb9c6` / 56,992 / 2 |
| monthly long Chinese | `e6ab7b67ac75a405dc7b1dab7543835308deebf13c66e9f2e860e4819e9df429` / 10,777 | `c2b8a30cece47bfa7a21045402644bf2ccf02357d0b567cb197b4792be7fc199` / 145,314 / 25 |

独立 read-only package/content 检查为 PASS：四份 DOCX 均匹配 manifest，未发现 forbidden
parts、external relationships 或可见 marker；weekly 两张表的两个 merged game rows 都含 5 个
周一至周五有序条目。DOCX field hash/order 检查通过。PDF 文本提取仅辅助页数和尾部 token，
不用于跨列/跨页完整正文的决定。

环境记录为 Ubuntu 26.04.1 LTS x86_64、`LANG=C.UTF-8`、`Asia/Shanghai`、Google Chrome
152.0.7977.82、LibreOffice 26.2.5.2。字体 inventory/hash、完整 package/content 检查、
DOCX/PDF manifests 和受保护截图引用均在受保护归档目录的 `local/artifacts/`。

另完成 PDF 视觉复审：4 份 PDF 共 87 页均经 overview，weekly long 额外放大 11 个跨页/合并行
代表页，monthly long 额外放大 6 个代表页；未见裁切、重叠、空白页或字形方块。weekly long 的
57 页反映合并格写入五日长文后的预期增页；列高不同造成的留白未见内容丢失。记录和 PNG contact
sheets 在 `local/artifacts/visual-review/visual-check.json` 及同目录。

这些仅是 **LibreOffice headless** 转换与 PDF 视觉证据，不能证明可见 LibreOffice 打开、兼容/
宏/外链警告、打印 UI 或 Microsoft Word 行为；因此不能写为完整 Office PASS。

## UI/application 本地执行和证据限制

`local/artifacts/ui-matrix.json` 是 51 项现场断言日志。记录 helper 在真实 DOM 中等待并
检查 expected 片段后才追加时间戳，函数文本另存 `ui-recording-functions.txt`。日志本身只有
name/expected/observed_at，未保存每一步完整 DOM/截图及逐项数据库快照；不能将它单独作为
完整正式矩阵 PASS。本文保留现场执行事实与下述独立数据库观察，完整逐项证据仍待补齐。

现场执行包括：

- teacher 周/月提交、旧 version/revision 重放拒绝、非法跳转、wrong-kind、自审拒绝；
  周删除确认缺失/一次性，月确认真实等待 318 秒过期再重新确认删除，APPROVED 删除拒绝。
- teaching_admin 周/月跨教师 read/export，以及两个完整状态链：DRAFT → SUBMITTED →
  RETURNED → SUBMITTED → APPROVED → ARCHIVED；自身周/月提交后以精确 v2/r2 自审拒绝。
- sys_admin 无隐式计划权限、同租户其它 owner 无可读计划、跨租户账户登录拒绝、身份切换后
  旧回调拒绝；auth_epoch 漂移和停用后的回调跳转登录；管理员降为 teacher 后，即使 grant
  仍 active，跨 owner 读取也拒绝。降权前针对自身计划的探索读取仍合法，未冒充降权负例。
- 页面加载后独立撤销合成 grant，周/月 read/export 四次拒绝；该数据准备是明确记录的外部
  fixture 状态改变，不是 UI grant 管理功能。停用/降权/auth_epoch 的准备也与业务操作分开。
- 两个浏览器页面对同一周/月 v1/r1 发出提交，各一次成功到 v2、另一次拒绝。前后 DOM 在
  `weekly-two-tab-{before,after}.txt`、`monthly-two-tab-{before,after}.txt`；它不能证明
  数据库事务窗口确实重叠，也不替代自动 CAS 测试。

`before-admin-read-export.json` → `after-admin-read-export.json` 只有 audit 从 10 增到 14，
对应周/月各 read/export 一次；其它表 count/hash 一致。管理员列表加载本身会逐个 cross-owner
read 并审计，必须与显式读取分别计数。`before/after-grant-denials.json`、
`before/after-epoch-denial.json`、`before/after-disable-denial.json`、
`before/after-demote-cross-owner-denial.json` 各自所有表 count/hash 完全一致。

`final-workflow-observation.json` 是独立只读中间观察：原四份 plan 的全部 seed 字段 hash
一致；5/6 的 v1..v6 状态链完整；7/8 tombstone、current_version=null、正文版本已清除；
9/10 为 v2 submitted。对 before-workflow 除允许的 WMP 表外无其它表变化。
后续增加了独立 CAS 草稿 11/12，以及明确记录的 user/grant fixture 变化。最终独立观察
`final-workflow-observation-complete.json`（SHA-256
`8108ae0837782c79544e4abd2376c37e4a2fc923dc8975e35af9eb848d13d07c`）确认 11/12 各仅一次
submit 成功到 v2；全部 audit 共 44 条：submit 8、review 4、archive 2、delete 2、read 26、
export 2。四份原始 plan 字段 hash 仍全部匹配，四组正确 scoped denial pair 全表不变。
不得拿中间快照覆盖后续操作，也不得把 fixture 的 user/grant 变化计作业务越权写入。

现有 UI 没有 exporter await 中途的同步 barrier，不能可重复证明 actor/plan/grant/
active-binding 在 snapshot/render/post-revalidate 精确窗口漂移。对应受保护 application
自动回归已 GREEN，但本地双页面操作不能冒充这些窗口的真实 UI 证据。跨 class/任意 plan/
version 篡改和 break-glass 等细项仍需逐项关联现有自动证据与适用的正式入口结果，不能预填。

## 环境 finding 和复审边界

初次本地容器以 host UID 运行而无 passwd 用户名，aiomysql 的 getpass 解析失败；独立复现后
仅补非秘密 `USER=wmp9-local`。业务账号执行已有 trigger 迁移时 MySQL 1419 拒绝；独立探针
确认后，只重建自有 tmpfs 空库并通过独立临时 root 凭据执行迁移，应用仍使用低权限业务账号。
未放宽 binlog/trust-function，也未改迁移。CAS fixture 已 commit 后报告路径不存在的准备器
错误由独立只读回查补录，未重复 seed 或伪造业务创建。

下一步提示词的 M finding（把文档后代 acceptance_start_sha 当 runtime tested-code）经两次
稳定 RED、最小文本修复和 GREEN，明确 runtime 仍为 bd2457a，文档后代只单独核验自身双 CI。
UI 日志缺乏逐项原始附件的复审意见保留为正式证据缺口，不以事后复制 expected 伪造 actual
或补拍历史状态。代码、内容、PDF 视觉与阶段文档 Review 均仅对各自范围负责，未预填总门 Review。

## 未满足条件和停止结论

本地阶段没有也未声称满足下列正式验收条件：

1. 明确指定的隔离云服务器、HTTPS 域名、Caddy → NiceGUI → MySQL 8 拓扑、受控连接和凭据引用；
2. 云端部署的不可变镜像与运行 revision 核验；
3. Windows 11 + Microsoft Word Microsoft 365 Current Channel 的原始 DOCX 打开、警告、显示、打印和 PDF 证据；
4. Linux LibreOffice 的**可见**打开、警告、显示和打印界面证据；
5. 全部适用受保护 UI/application 权限、状态、drift/replay/CAS、删除、append-only audit 和零未授权持久化矩阵的最终记录与独立 Review；
6. Issue #55/#56/#57 回写、最终 evidence-closure commit 及该 closure SHA 自身的 Quality/CodeQL。

因此 **WMP-9 = BLOCKED**。本地证据受保护归档到
`/home/ywyz/wmp9-acceptance-evidence-20260907`；该归档不是新 closure 或 Issue 证据。
333 个制品逐文件 SHA-256 复制回读一致；`manifest.json` SHA-256 为
`76435db696e267599ad6f56f44436f9b5ad82c87dae609ca6df86910fdd9f9c2`。目录 mode 0700，
文件 mode 0600，原始 DOCX mode 0400；没有把原始 DOCX/PDF、合成正文、凭据或截图提交仓库。
临时 private/app-data/LO profile/regression-data 已排除；已清理专属 app/MySQL 容器和网络，tmpfs 数据库销毁，
127.0.0.1:32769 关闭，临时凭据与会话文件删除，浏览器页面置空，没有使用剪贴板。

归档复审发现旧 regression-data 的临时 secrets/lock 误入归档（H），以及两个中间目录
权限 0775 与声明不符（M）。提交暂停后各经路径/权限断言稳定 RED 两次，移除整个临时
regression-data（未输出秘密内容），收紧所有目录到 0700，重建清单并 GREEN。修复前的清单
hash 不再适用；上述 333 项新清单才是最终归档。cleanup.json 位于归档中的
`wmp9-bd2457a-evidence/local/cleanup.json`，实际 mode 0600。
`archive-secret-green.txt` 是明确允许保留的 0-byte 检查输出（mode 0600），不是秘密材料；
敏感路径排除检查针对 `.kindergarten_secrets*` 与上述运行数据目录，而非禁止日志文件名中的
英文单词 secret。

阶段文本的独立只读复审 H/M/L = 0/0/0，仅限声明准确性；不代表总门 Review 或证据 closure。
本文与提示词将作为分阶段文档提交，其完整 SHA 和自身 Quality/CodeQL 须在提交后另行回读，
不得用 bd2457a 的 CI 预填该文档提交 CI。

## 独立 release / production deployment GO/NO-GO

**NO-GO。** 没有发布授权、没有生产部署授权、没有创建或修改云端资源。本地 Docker/MySQL/Chrome/
LibreOffice 仅为隔离验收阶段，不能替代云端 HTTPS 或两类消费端。恢复云端阶段前应先取得隔离服务器、
域名、受控连接、凭据引用、不可变镜像和两类外部 Office 消费端的明确访问方式；不得探测、复用或传递
生产凭据、生产正文或生产数据库。

服务器部署在架构上受支持（Caddy → application → MySQL 8），当前只能提出隔离验收准备方案：
提供一台明确授权的隔离主机、HTTPS 域名/证书与受控连接引用，再构建并记录匹配 tested-code 的
不可变 OCI 镜像，独立验证 revision、liveness、readiness 和登录。不得新增付费资源或复用生产凭据。
正式发布还须另行核对 tag/source SHA/docker-image.json/release body/OCI digest 一致性，以及
精确 SHA CI、部署、数据库 readiness、UI 登录、凭据轮换/旧会话失效与 rollback 各自的证据。
现有 release workflow 的 legacy desktop 路径不在本门改造，不能由本地验收推导发布 GO。

后续执行入口见 [下一步提示词](../tasks/WMP-9-formal-acceptance-prompt.md)。
