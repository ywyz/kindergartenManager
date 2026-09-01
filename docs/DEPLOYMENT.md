# Deployment Guide（发布与生产运维）

本文件聚焦生产部署收敛：Docker 镜像不可变发布、部署/回滚流程、备份与恢复边界。

## 1. 发布镜像的不可变引用

`release.yml` 现在会在构建完成后生成 `docker-image.json` 资产，字段如下：

- `schema_version`
- `release_tag`
- `source_sha`
- `repository`
- `digest`
- `ref`（`repository@sha256:<digest>`）
- `media_type`（必须为 OCI image index）
- `platforms`（当前固定为 `linux/amd64`、`linux/arm64`）

发布说明正文会同时写入这几个字段用于人工回读。

### 1.1 OCI index digest 与 per-platform manifest digest

本流程关注的是 Docker 构建后的 OCI index digest（`docker/build-push-action` 的 `.outputs.digest`），
它表示“镜像清单索引”的不可变集合。

当镜像包含多架构时，index digest 与某个平台的单独 manifest digest 不同；发布收敛与回滚必须使用
`repository@sha256:<index-digest>` 这类 index 级引用，不要把某个单平台 manifest digest 当作可替代签名。

## 2. 现网部署/回滚操作（生产）

仓库新增 `scripts/deploy.py`：

- `deploy` 子命令：仅接收 digest 形式的 image ref（`...@sha256:...`）
- 三个镜像变更命令均须先验证 `--backup-evidence`，并以 `--protected-image` 绑定当前运行镜像
- 部署前通过 `docker buildx imagetools inspect --raw` 确认它是同时含 `linux/amd64`、`linux/arm64` 的 OCI index
- 使用文件锁串行化操作
- 写入/更新部署状态文件（owner-only）
- 执行 `docker compose pull` + `up --no-build`
- 校验 `.Config.Image` 与请求 image ref 完全一致
- 依次等待 liveness（`/api/v1/health`）与 database readiness（`/api/v1/readiness`）通过
- 部署失败自动尝试回退到部署前实际运行的 immutable image
- `rollback` 子命令：显式回退到历史 immutable ref（或可指定目标）
- `--dry-run`：仅展示计划，不执行 Docker 变更

示例：

```bash
cd /path/to/KindergartenManager
python scripts/deploy.py \
  --project-dir /home/ecs-user/compose/kindergarten-production \
  --service app \
  --state-dir /var/lib/kindergarten-manager/deploy-state \
  --backup-evidence /secure/path/backup-evidence.json \
  --protected-image ghcr.io/ywyz/kindergartenmanager@sha256:<当前digest> \
  --health-url https://manager.ywyz.tech/api/v1/health \
  --readiness-url https://manager.ywyz.tech/api/v1/readiness \
  deploy ghcr.io/ywyz/kindergartenmanager@sha256:872e9854fcdf62df1f510e4b825ccb4a25022e1b06383672f0712cf9c6ba7246
```

```bash
python scripts/deploy.py \
  --project-dir /home/ecs-user/compose/kindergarten-production \
  --service app \
  --state-dir /var/lib/kindergarten-manager/deploy-state \
  --backup-evidence /secure/path/backup-evidence.json \
  --protected-image ghcr.io/ywyz/kindergartenmanager@sha256:<当前digest> \
  --health-url https://manager.ywyz.tech/api/v1/health \
  --readiness-url https://manager.ywyz.tech/api/v1/readiness rollback
```

建议在部署前先用 `docker compose config` 或 CI 校验确认 compose 文件可解析。

`--health-url` 与 `--readiness-url` 必须是当前 Compose 经 Caddy/目标域名实际路由到的两个独立探针地址，
不能填另一个恰好返回 200 的服务。脚本还会核对运行容器的 `.Config.Image`；这些检查仍不能替代迁移兼容、
登录、业务或数据恢复验收。

> 遗留迁移说明：当前历史生产实例记录的是单平台 manifest digest。新脚本会对此失败关闭，不能直接把它
> 当作可回滚的 OCI index。首次采用新自动化前，应在部署状态为空时显式执行一次：

```bash
python scripts/deploy.py \
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

> 安全说明：应用与 Bootstrap 启动均不调用 Alembic。迁移必须先用同一备份证据执行独立
> `python -m app.jobs.migrate_database`；deploy/rollback/migrate-legacy 也会在 Docker 变更前重新验证证据并
> 核对其与当前运行镜像的绑定。镜像 rollback 仍不能还原数据库 schema/data；禁止自动 downgrade。

## 3. 健康/就绪边界

`/api/v1/health` 仅表示进程/HTTP 存活且不访问数据库。`/api/v1/readiness` 每次通过独立短 session 执行
`SELECT 1`；失败为 503。deploy、自动恢复、显式 rollback 与 legacy migration 只有在目标镜像两门均通过后
才更新状态；恢复镜像也必须重过两门。真实 MySQL 停止/恢复与零业务变化仍须按 Issue #54 独立验收。

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

部署和回滚仅切换应用镜像引用，不应执行数据库迁移或删除卷。

回滚建议流程：

1. 记录失败 deploy 的 image ref 和 liveness 现象
2. 执行 `rollback` 回退到上一条 immutable ref
3. 复查 liveness 与关键路径接口
4. 必要时回填 release 记录

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
