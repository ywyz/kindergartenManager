# 周计划云端交付记录

## 当前决定

2026-09-14 用户授权本轮五／六列周计划云端交付所必要的提交、推送、PR、合并、镜像与 Release、生产备份与迁移、阿里云镜像切换和上线验证。生产执行前须有可审查候选、镜像和有效验证；不重复索要这些动作的批准。

本轮及后续适用的文档兼容性／版式以 LibreOffice 实际 DOCX 内容、布局、字体和页数验收。取消 Windows／Microsoft Word 前置和历史双 RED、旧阶段补证作为本轮发布门；历史失败及证据缺口保持原状，不补写 PASS。

本轮超页由教师手动缩短，保存后实际重检，单页才允许导出；不截断、不缩字体、不伪造页数。自动缩减完善和验收延期。月计划、新 Agent 能力、桌面客户端及 Issue #77 远期范围不纳入本轮。

保留租户隔离、权限、并发保护、数据、凭证、备份和必要迁移；用户已允许专用合成验收租户写入，必要时创建；不改动真实教师计划正文；只增加用户单独确认的班级共享身份关系。

## 执行清单

- 已完成：主仓库三项既存修改保全为外部 patch，未修改原工作树。周计划起点 `7ec372f7dfb6128720e3c99d208c8d7d938882ff`，远端 main `8dcc83376577695b562529ec42adc6b48817f004`。
- 已完成：独立分支 `codex/wp-cloud-delivery-20260914` 集成 PR #76 的 `19eb8bfea9a941a73383a536fdec439587c39141`，合并提交 `7572532`。桌面构建退出；保留 OCI 双平台及 Release 元数据绑定。
- 已完成渲染镜像、开放字体供应与 CI 拆分；`1107547` 的 Real LibreOffice rendering CI 已通过。BWH 镜像内实际生成五／六列单页 DOCX/PDF，Main 已核对页面，资格 manifest SHA256 为 `20199d5fce4b48f735c7dff97ca06b87e18e2b3bdbb501d95509ba368d5f91f5`。
- 已创建交付 [PR #82](https://github.com/ywyz/kindergartenManager/pull/82)。候选 `ce276d71c0cb0de9d1843bfa1354045019d7fbe1` 的 Quality [34839981563](https://github.com/ywyz/kindergartenManager/actions/runs/34839981563)（普通检查及真实 LibreOffice）、CodeQL 全部通过；此前 1107547 的 7 项失败已修复，历史日志保留。
- BWH `https://staging-manager.ywyz.tech` 的 `kg-weekly-staging` / 独立 MySQL `wp_cloud_20260914` 已显式迁移至 `d375e9ab2148`。真实应用合成教师甲／乙登录、共享保存和可见性、旧版本 `plan_conflict` 拒绝、重载后正常保存通过。
- BWH 实际浏览器五列、六列保存／单页检查／DOCX 收件通过。长文实际 3 页拒绝导出；教师手动缩短 26 项、保存、重新检测实际 1 页后收到 DOCX。外部收件证据 `browser-bwh/{five,six,manual-shorten}-receipt.json` 与原始 DOCX 保存，不以服务 bytes 代替浏览器收件。
- 兼容回滚 `885835282c450c954dc89cee33ace2f3cb050de1` → OCI index `sha256:56964bb110dad97b56cde85d8cb759d025a977488eb59f35badd16a3e6cefb6f`。基于生产 beta10，仅新增迁移树与受限合成租户登录入口；Quality 34838959795 通过，BWH 在新 schema 上实际启动、readiness、教师登录首页及既存每日计划列表读取通过。该检查未写计划数据。
- 已完成：PR #82 与 PR #76 均合并，发布提交 `494bdddb6b27c7c7465f3224271d197075dd93b1`；[Release v3.4.0-beta11](https://github.com/ywyz/kindergartenManager/releases/tag/v3.4.0-beta11) 已发布且发布后元数据复读通过。生产备份、隔离恢复、显式迁移、共享班级设置、镜像切换与实际业务验收均通过。
- 镜像追踪：`2d5960194174595853a6b186214cd099e6e4c5cd` → OCI index `sha256:9e3f512a4a533dbc732b78e4aab5a4c80fb00cbecd34e45fd1d37af1d3743930`（资格材料）；`11075478872bb43f3bb5b9aa3929db0d28f7b2b0` → `sha256:7e20f1eb1dd96ebfe6715629d4a23af526d06ba99c108dcd7e453e8c9fbe1e6c`（BWH 实际业务及收件）；`ce276d71c0cb0de9d1843bfa1354045019d7fbe1` → `sha256:e7fe27eee7c6a699d421990b4bb12a5f75601ef824f7900cd0fa434f78d7474a`（最终候选）。1107547 至 ce276d7 的 app、Dockerfile、docker、templates、requirements.txt 无差异，复用该业务／渲染证据；变更的 fixture 与部署 helper 已有对应检查。

## 阻塞清单

| 事项 | 已知事实及影响 | 已尝试动作 | 所需决定／资源 | 状态 |
|---|---|---|---|---|
| 字体授权 | 用户允许开放授权中文宋体替代，不另设字体版式复验 | 选用 Debian fonts-noto-cjk 的 Noto Serif CJK SC，保留 OFL | 正常目标镜像实际单页检测仍执行 | 已解决 |
| 非生产目标 | 用户指定 BWH，明确不保留 kg-wmp9-staging | 只读核对后保全必要配置并替换旧测试项目 | 无 | 已解决 |
| 生产合成写入 | 用户允许专用合成验收租户写入及必要创建 | 保持真实教师数据隔离 | 无 | 已解决 |

## 已有与本轮验证

- 复用 [本地浏览器证据](WP-E-browser-delivery-20260914.md) 中未变源码／输入／环境对应的48项专项及2项真实 LO／SQLite结果，以及真实五／六列下载与手动缩短收件事实；这些不代表新镜像或云端验收通过。
- 本轮集成基本检查：`tests/test_release_workflow.py`、`tests/test_python_runtime_baseline.py`、`specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py`，52 passed。解释器为主仓库 `.venv/bin/python`，cwd 为隔离交付工作树；未跑全套。
- pi 初次使用 `coding-plan/ark-code-latest` 返回 `Connection error.`；仅该进程清除代理后成功。实际成功响应的 `responseModel` 报告 `kimi-k2.7-code`，仅记录服务返回字段，未另发路由验证请求。

外部任务、日志及保全材料：`/home/ywyz/code/wp-cloud-delivery-20260914/`。未取得的 CI、镜像、测试部署、生产结果不预写通过。

字体来源：[Debian trixie fonts-noto-cjk](https://packages.debian.org/trixie/fonts-noto-cjk)，[Noto CJK Serif OFL](https://github.com/notofonts/noto-cjk/blob/main/Serif/LICENSE)。新生成周计划明确声明 Noto Serif CJK SC，历史 SimSun 材料保持；不冒充宋体已供应。


用户追加确认真实上线映射：tenant 1 的现有教师 ID 2、3 共享“中四班”；学年 2026-09-01 至 2027-08-31，第一学期 2026-09-01 至 2027-01-25。只新增本轮 canonical identity 与共享assignment，不修改旧配置历史。

本轮检查：pi deployment profile 基本检查72通过；Main兼容回滚影响范围7通过。周计划普通检查首轮发现两项旧字体断言及主仓库虚拟环境缺日历依赖；改正断言、使用已存在startup handoff环境（Python3.14.7 / chinesecalendar1.11.0）后，受影响45项通过。首轮其余27项startup检查已通过，未重复执行。真实渲染和云端结果另行记录。

本轮环境探针与部署检查85通过；登录及显式租户入口27通过。无主机工具 PATH 下的启动资格单元检查40通过，真实渲染另由镜像 CI 验证，未把 mock 当成真实字体或排版证据。
pi 业务验证脚本任务曾返回 AccountQuotaExceeded；用户升级订阅后已以原 coding-plan/ark-code-latest 重试，不切换模型。

## 生产交付结果

- 发布源码 `494bdddb6b27c7c7465f3224271d197075dd93b1`，对应 [Quality 34842785944](https://github.com/ywyz/kindergartenManager/actions/runs/34842785944) 和 [Release Build 34842786023](https://github.com/ywyz/kindergartenManager/actions/runs/34842786023) 均成功。发布源树与已验收 PR 源树一致；本记录后续提交只封存证据，不重新构建产品镜像。
- 正式 OCI index：`ghcr.io/ywyz/kindergartenmanager@sha256:5a25f7871b81ee1dbf226d393f11c02f7e14e151a55b74ce0df4cdd952bb6217`。Release id `388378650`，tag、源码 SHA、唯一 `docker-image.json`、Release 正文和双平台 index 已收敛。发布前后均由 `release_convergence` 实际复读。
- 实际生产目标：[manager.ywyz.tech](https://manager.ywyz.tech)，阿里云 `kindergarten-manager` / 既存 `kindergarten_prod` MySQL。当前 Compose：`/home/ecs-user/compose/kindergarten-production/releases/v3.4.0-beta11/compose.yml`，基础配置已收敛到上述正式 digest；四项资格配置启用 tenant `1,11`，受限合成登录入口只额外允许 tenant `11`。
- 一致性备份与隔离 MySQL 恢复校验通过：`/var/lib/kindergarten-manager/weekly-delivery-20260914/backups/run-5998934a316c4f8fb9dcc6dde25fb757/backup-evidence.json`；归档 SHA256 `bd2a8b4616661aba993d0869505305462a057e8b48c545c4a52ef31c0603046e`。显式迁移 `2b7f3d5e9c8a → d375e9ab2148`，receipt 绑定真实数据库、备份、Release 和目标镜像。备份资产中的固定 `secrets/.kindergarten_secrets` 成员在本环境保存的是原 `app.env` 字节，恢复目标是原 env 路径，不是 JSON secrets 文件；详见受保护运维目录 recovery notes。
- 生产合成 tenant `11` 的两位教师实际登录、共享保存／可见性、旧版本 `plan_conflict` 拒绝、重载后正常保存通过。浏览器五列和六列均保存后实际单页检测通过并收到 DOCX；长文实际 3 页时拒绝且无新文件，教师手动改短 26 项后保存、实际重检 1 页并收件。三个收件 SHA256：五列 `0da4739dc24a1feb40e229c0be9d3cf7ea361f38cfc09b2b9dfee1452f5203f2`；六列 `defa260bde0b71499837e92c1ebadb1569c419704b8911baf81c94eda6d2e56d`；手改 `1844d63e8a21ad284439dd254bf87cc88cb4f1c7bbd601d8987e613fa5c3f361`。外部 `browser-production/` 保留文件、时间、内容核对及收件记录。
- 部署门通过新鲜 challenge 接收 Main 实际浏览器观察与原始下载文件，校验绑定、时限和文件 hash 后才记录成功；没有伪造 runner 输出。生产 state 当前镜像为正式 `5a25…6217`，previous 为经过 BWH 新 schema 验证的 `56964…fb6f` 兼容恢复镜像。最终 liveness、数据库 readiness 均通过。回滚保留当前数据库，按流程取得新鲜备份后切换兼容镜像，不自动 downgrade 或覆盖数据。
- 已落实真实 tenant `1` 教师 ID `2,3` 的唯一“中四班”共享关系及已确认学年／学期日期。只新增 canonical identity 和两项 assignment，旧配置未修改；临时 manager 授权已撤销并保留审计。任务结束时连接析构出现非致命 `Event loop is closed`，发生在提交和回读成功之后，未重跑写入。

## 已解决的执行问题与清理

- 生产备份首调因 MySQL 引用带 tag 被严格拒绝；改为同 digest 的 `mysql@sha256` 后成功。暂停解除后的首次 readiness 为 503，随后恢复 ready/healthy；未将瞬时失败写为通过。
- 阿里云直连镜像层缓慢；通过 BWH 取得同一发布镜像并经 SSH 导入，传输归档双方 SHA256 一致，重新 pull 原 index 后确认 digest 与源码标签一致。
- 首次部署与恢复启动均因 Compose project directory 导致相对 env 路径错误而失败，运行容器未切换。修正为 release 目录后配置检查通过，重试完成正式部署和所有真实业务门；历史失败日志保留。
- Release 本地首调遇到代理 URLError；仅该进程取消代理后，正式发布及发布后复读通过，未修改全局配置。
- 后续运维准备子任务因额度停止，Main 接手完成；pi 升级后的重试任务有效结果已复用。无未解决的用户决策／资源阻塞。
- BWH 旧 `kg-wmp9-staging` 容器及数据库卷已移除，新 `kg-weekly-staging` 保持服务；既存证据和生产真实数据保留。自动缩减、月计划远期范围、Windows／Word 验收及桌面产品均未作为本轮前置或额外实施。

收尾核对：BWH 已同步正式 `5a25…6217` 镜像并通过 healthy／database ready；不重做源码与输入未变的业务验收。阿里云临时 GitHub 认证输入和备份用 env 副本已删除，Bootstrap 密码文件仍为 ecs-user／0600。生产所有观察由部署门消费并写入最终 state 后，运维容器已退出；仅本地 SSH 传输连接滞留，核实远端无任务后关闭该本地连接，未重启部署。主仓库原三项既存修改保持未提交状态。
