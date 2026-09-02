# Deployment Guide（发布与生产运维）

本文件聚焦生产部署收敛：Docker 镜像不可变发布、部署/回滚流程、备份与恢复边界。

## 1. 发布镜像的不可变引用

R5-P 只接受一个闭合发布元组：

```text
release tag ↔ source SHA ↔ repository ↔ OCI index digest
            ↔ docker-image.json ↔ Release body
```

任一成员不一致都不是可发布或可部署候选。`release.yml` 在构建完成后生成 `docker-image.json`，字段如下：

- `schema_version`
- `release_tag`
- `source_sha`
- `repository`
- `digest`
- `ref`（`repository@sha256:<digest>`）
- `media_type`（必须为 OCI image index）
- `platforms`（当前固定为 `linux/amd64`、`linux/arm64`）

发布说明正文会同时写入这些字段。Release 先以 draft 创建，按 release id 验证 tag target、source SHA、
repository、OCI index digest、immutable ref、descriptor 和唯一 Release asset 全部收敛；workflow 验证后仍
保持 draft。只有生产门全部通过，才使用 `release_convergence --publish` 执行发布前验证、publish、同一
release id 发布后复读；任一步失败都不得标记 release closure。

### 1.1 OCI index digest 与 per-platform manifest digest

本流程关注的是 Docker 构建后的 OCI index digest（`docker/build-push-action` 的 `.outputs.digest`），
它表示“镜像清单索引”的不可变集合。

当镜像包含多架构时，index digest 与某个平台的单独 manifest digest 不同；发布收敛与回滚必须使用
`repository@sha256:<index-digest>` 这类 index 级引用，不要把某个单平台 manifest digest 当作可替代签名。
R5-P 的平台集合必须恰好为 `linux/amd64` 与 `linux/arm64`；缺少任一平台或包含第三个平台均失败关闭。

## 2. 现网部署/回滚操作（生产）

仓库新增 `scripts/deploy.py`：

- `deploy` 子命令：仅接收 digest 形式的 image ref（`...@sha256:...`），并要求受控 acceptance runner
- 三个镜像变更命令均须先验证 `--backup-evidence`，并以 `--protected-image` 绑定当前运行镜像
- 部署前通过 `docker buildx imagetools inspect --raw` 确认它是恰好含 `linux/amd64`、`linux/arm64` 的 OCI index
- 使用文件锁串行化操作
- 写入/更新部署状态文件（owner-only）
- 执行 `docker compose pull` + `up --no-build`
- 校验 `.Config.Image` 与请求 image ref 完全一致
- 依次等待 liveness（`/api/v1/health`）与 database readiness（`/api/v1/readiness`）通过
- 部署失败或登录/业务门失败时，自动尝试回退到部署前实际运行的 immutable image
- `rollback` 子命令：显式回退到历史 immutable ref（或可指定目标），回切后重新执行登录与关键业务门
- `--dry-run`：仅展示计划，不执行 Docker 变更

`scripts/deploy.py` 只切换镜像并执行它声明的门禁；它不运行 migration、不修改 secrets、不删除卷、不执行
Alembic downgrade 或数据库 restore。dry-run 始终是 `NOT_IMAGE_BOUND`，不能作为镜像绑定、迁移、部署、回切、
登录、业务验收或 Release 证据。

除仅建立历史 index 基线的 `migrate-legacy` 外，`deploy` 与 `rollback` 都必须提供 `--acceptance-runner`。
helper 只有在 liveness、readiness、登录和关键业务四类独立门全部通过后才原子写 deployment state；目标动作
或恢复动作任一门失败（包括双重失败）时，原 state 保持不变。

R5-R 的 database identity 与 Alembic revision 不是命令行参数。备份 producer 从实际配置数据库读取并写入
`backup-evidence.json`；`deploy.py` consumer 使用 `--backup-evidence` 消费该 producer evidence，并在任何
Docker 变更或 deployment state 写入前自动从当前配置数据库复读 identity/revision，要求与 evidence 精确一致。
因此不得手工传入、复制或改写 identity/revision；证据、当前数据库和 `--protected-image` 的绑定必须由程序
复核。

无 schema 变化时使用与当前数据库 revision 匹配的新鲜 producer evidence。revision 变化时先由目标代码执行：

```bash
python -m app.jobs.migrate_database \
  --backup-evidence /secure/path/backup-evidence.json \
  --protected-image ghcr.io/ywyz/kindergartenmanager@sha256:<当前digest> \
  --target-image ghcr.io/ywyz/kindergartenmanager@sha256:<目标digest> \
  --source-sha <目标release的40位source-SHA> \
  --receipt-output /secure/path/migration-receipt.json \
  --release-descriptor /secure/path/docker-image.json \
  --release-repo ywyz/kindergartenManager \
  --release-id <draft-release-id>
```

migration job 在 Alembic 前还会从 GitHub draft Release 按 release id 复读 tag/SHA/body/唯一 asset，并验证
双平台 OCI index 及两个 platform manifest 的 `org.opencontainers.image.revision` 都等于 source SHA。随后它从
producer evidence 与当前数据库自动复读 identity/before revision，迁移后再复读同一 database identity 与
after revision，并生成 `0600` receipt。目标部署必须同时带入 receipt：

隔离演练在尚未创建 draft Release 时只能使用 `--isolation-run-id <id>` 取代 `--release-repo/--release-id`。
该模式强制旧/目标镜像都来自 `localhost` 或 `127.0.0.1` registry，descriptor tag 必须精确为
`r5p-isolation-<id>`，数据库名必须精确为 `r5_p_<id>`（连字符转下划线），且本地 migration checkout 必须 clean
并等于 source SHA。它不能消费生产镜像、发布 Release 或作为生产证据；生产仍必须使用上述 GitHub Release 绑定。

```bash
cd /path/to/KindergartenManager
python -m scripts.deploy \
  --project-dir /home/ecs-user/compose/kindergarten-production \
  --service app \
  --state-dir /var/lib/kindergarten-manager/deploy-state \
  --backup-evidence /secure/path/backup-evidence.json \
  --protected-image ghcr.io/ywyz/kindergartenmanager@sha256:<当前digest> \
  --migration-receipt /secure/path/migration-receipt.json \
  --source-sha <目标release的40位source-SHA> \
  --acceptance-runner /secure/path/r5-acceptance-runner \
  --health-url https://manager.ywyz.tech/api/v1/health \
  --readiness-url https://manager.ywyz.tech/api/v1/readiness \
  deploy ghcr.io/ywyz/kindergartenmanager@sha256:872e9854fcdf62df1f510e4b825ccb4a25022e1b06383672f0712cf9c6ba7246
```

```bash
python -m scripts.deploy \
  --project-dir /home/ecs-user/compose/kindergarten-production \
  --service app \
  --state-dir /var/lib/kindergarten-manager/deploy-state \
  --backup-evidence /secure/path/backup-evidence.json \
  --protected-image ghcr.io/ywyz/kindergartenmanager@sha256:<当前digest> \
  --acceptance-runner /secure/path/r5-acceptance-runner \
  --health-url https://manager.ywyz.tech/api/v1/health \
  --readiness-url https://manager.ywyz.tech/api/v1/readiness rollback
```

建议在部署前先用 `docker compose config` 或 CI 校验确认 compose 文件可解析。

`--health-url` 与 `--readiness-url` 必须是当前 Compose 经 Caddy/目标域名实际路由到的两个独立探针地址，
不能填另一个恰好返回 200 的服务。脚本还会核对运行容器的 `.Config.Image`；这些检查仍不能替代迁移兼容、
登录、业务或数据恢复验收。

`--acceptance-runner` 由受控运维方提供，必须是当前用户所有的绝对路径普通文件、mode `0700`。helper 通过已
打开的 fd 执行它，且仅传 `PATH`、phase、image ref 与 gate 名，不转交部署进程的数据库、密钥或其他环境。
runner 对 login gate 必须返回唯一 `login=passed`；对 business gate 必须返回且仅返回每日计划、游戏观察、
一对一倾听、自制教玩具、课程审议、图片/BLOB、AI 密钥解密、Word 导出、数据快照九项 `passed` 的关闭 JSON。
空输出、单纯 `exit 0`、未知/缺失字段、ref/phase/gate 错绑或超长输出均失败关闭。

> 遗留迁移说明：当前历史生产实例记录的是单平台 manifest digest。新脚本会对此失败关闭，不能直接把它
> 当作可回滚的 OCI index。首次采用新自动化前，应在部署状态为空时显式执行一次：

```bash
python -m scripts.deploy \
  --project-dir /home/ecs-user/compose/kindergarten-production \
  --service app \
  --state-dir /var/lib/kindergarten-manager/deploy-state \
  --backup-evidence /secure/path/backup-evidence.json \
  --protected-image <当前运行的精确legacy-manifest-ref> \
  --health-url https://manager.ywyz.tech/api/v1/health \
  --readiness-url https://manager.ywyz.tech/api/v1/readiness \
  migrate-legacy \
  <当前运行的精确legacy-manifest-ref> \
  ghcr.io/ywyz/kindergartenmanager@sha256:<release中的OCI-index-digest>
```

`migrate-legacy` 要求显式提供当前运行的 legacy digest，并在执行时核对它与容器一致；同时验证目标是双平台
OCI index、切换并验活，然后把新
index 写成唯一基线（`previous_image=null`），不把单平台历史写入长期回滚状态。若切换失败，它只在该次
显式迁移中恢复操作前的精确 legacy digest；恢复成功后仍不建立 deployment state，需排障后重新发起。
`--dry-run` 使用显式 legacy ref 生成完整计划但不查询或改变容器。

> 安全说明：应用与 Bootstrap 启动均不调用 Alembic。迁移前 evidence 仍只绑定 before revision；migration
> receipt 只是由已执行的迁移把它桥接到当前 after revision，不会把旧 evidence 改写为新备份。目标部署失败时
> 可尝试旧镜像回切，但镜像 rollback 仍不能还原 schema/data，禁止自动 downgrade。旧镜像若不能在新 schema 上
> 重新通过 readiness、登录和关键业务，必须进入明确的 database restore 方案，不能继续依赖单纯镜像回切。
> migration receipt 只授权紧接迁移的那一次目标部署及其同一受控动作内的自动镜像回切。若该动作结束后再手工
> 执行 `rollback`，必须先对“当前运行镜像 + 当前已迁移数据库 revision”重新生成新鲜 producer backup evidence；
> 不得复用迁移前 evidence 或 receipt。显式回切必须带 acceptance runner，登录与业务门通过前 helper 不更新
> deployment state，也不得宣称 closure。

## 3. 健康/就绪边界

`/api/v1/health` 仅表示进程/HTTP 存活且不访问数据库。`/api/v1/readiness` 每次通过独立短 session 检查
`SELECT 1` 与实际 Alembic revision 等于当前镜像唯一 head；任一失败为 503。deploy、自动恢复、显式 rollback 与 legacy migration 只有在目标镜像两门均通过后
才可完成其 HTTP 门；R5-P 的最终 deployment state 还必须等待登录与关键业务验收。恢复镜像必须重新通过
liveness、readiness、登录和关键业务。四类门彼此独立，不能互相替代。真实 MySQL 停止/恢复与零业务变化仍须
按 Issue #54 独立验收。

## 4. Bootstrap 管理员生产凭据

当前 Aliyun 生产环境的管理员密码文件位于：

```text
/home/ecs-user/compose/kindergarten-production/secrets/bootstrap_admin_password
```

该文件属于 `ecs-user:ecs-user`，权限必须保持为 `0600`。只允许受控初始化、恢复或轮换任务读取它；不得用
`cat`、shell tracing 或会回显参数/环境的方式查看，不得复制到聊天、Issue、日志、截图、`.env` 或 Git。
备份如因轮换临时产生，也必须保留在受保护的 secrets 目录、保持 owner-only，并按既定保留期清理。

2026-08-31 的生产验收已完成以下独立检查：恢复密码文件与数据库哈希漂移、通过标准管理员重置入口完成最终
轮换、旧凭据被拒绝、旧 UI 会话失效、最终凭据重新登录并进入 `/home`。浏览器扩展与 Native Messaging
链路可用，但目标页语义控制仍出现超时；因此登录表单填写与可见页面确认采用用户在场的受控剪贴板交接，
不能据此宣称目标页浏览器自动化已完全修复。临时本机密码文件已删除，剪贴板已覆盖为非敏感文本。

以后每次轮换仍须重新完成上述门禁，不能沿用本次结果；不得在文档中记录用户名或密码值。

## 5. 备份与回滚边界

生产部署时应保留并明确以下卷：

- `app_data`
- `db_data`
- `exports`
- `caddy_data`
- `caddy_config`

部署和回滚仅切换应用镜像引用，不执行数据库迁移、不改 secrets、不删除卷。

回滚建议流程：

1. 记录失败 deploy 的 image ref 和 liveness 现象
2. 执行 `rollback` 回退到上一条 immutable ref
3. 依次复查 liveness、readiness、登录和关键业务
4. 若旧镜像不兼容新 schema，停止并执行已冻结的数据库恢复方案；不得自动 downgrade
5. 仅在恢复门全部通过后确认 deployment state 保持动作前值；Release 仍保持 draft/未 closure

## 6. 近期发布事实（历史不追溯）

以下是当前仓库最近一次已发布事实，仅作当前手工核对，不代表新的 digest 自动化行为已经用于该历史发布：

- Release tag：`v3.4.0-beta2`
- 合并 SHA：`ec592def71658a5036359e7c79e35c9b6b0ab99b`
- 工作流运行：`33312637621`
- OCI index digest：`sha256:872e9854fcdf62df1f510e4b825ccb4a25022e1b06383672f0712cf9c6ba7246`
- 已部署到 `manager.ywyz.tech` 的 linux/amd64 manifest：`sha256:be4ee7e841621f6c9ec7142ec15271a37573a5587658e61c7329a7059f7a4b2c`

当前生产因既有私有 GHCR 代理路径固定到了 `linux/amd64` manifest；这是可回读的历史现状。新发布工作流构建
`linux/amd64` 与 `linux/arm64` 的 OCI index，通用部署/回滚记录应固定 index digest，不能把两种 digest 混写。

## 7. 与其他文档的入口

- 生产部署入口和管理员初始化：`README.md`、`docs/USER_MANUAL.md`
- 变更门禁与复审计划：`docs/ROADMAP.md`
- 部署安全/发布与完整性边界：`docs/security/threat-model.md`
