# BWH 隔离云端部署（2026-09-08）

## 本轮结论

**隔离 Web 环境已运行；WMP-9 正式业务验收未闭合，Aliyun 生产未升级。**
用户提供 `*.ywyz.tech → bwh` 并授权优先使用 bwh，资源不足时备用 `aliyun.ywyz.tech`。
本轮使用 `https://staging-manager.ywyz.tech`；没有使用备用环境或购买资源。
Office 客户端人工检查按用户要求延期，不预填 PASS。

## SHA、CI 与镜像

- fetch 后 `origin/main` / 本轮 acceptance start：`8dcc83376577695b562529ec42adc6b48817f004`。
- 部署候选 source SHA：`c08c8fb36118d53f9718c221a793c1a82283bb71`，来自独立分支
  `chore/aliyun-cloud-deployment-20260908`；[PR #76](https://github.com/ywyz/kindergartenManager/pull/76) 为 draft。
- 候选自身 [Quality 34189884838](https://github.com/ywyz/kindergartenManager/actions/runs/34189884838)、
  [Quality 34189984772](https://github.com/ywyz/kindergartenManager/actions/runs/34189984772)、
  [CodeQL 34189983228](https://github.com/ywyz/kindergartenManager/actions/runs/34189983228)
  均 completed/success，headSha 精确等于 c08c8fb。
- 候选与既有 runtime tested-code `bd2457a9df4a720b169268ec30976db666ab6713` 的
  `app/`、Alembic、模板、requirements 与 Dockerfile 无差异；后代测试/发布配置变更仍以自身 CI 核验。
- 镜像由候选干净 worktree 的 Dockerfile 本机构建，经 SSH 隧道推送到 bwh 自有回环 registry，
  再按以下不可变引用拉取和启动：
  `localhost:5018/kindergarten-staging@sha256:14924a4a907f40efb6e992f661a8464657bce45009672954dcbdd92454abbe58`。
- 这是 linux/amd64 隔离候选镜像，不是双平台生产 Release。
  不把该候选当作正式 release tag/source/descriptor/body/双平台 OCI 的闭合元组。
- 运行容器 revision label 精确等于 c08c8fb。按候选 Git 文件列表回读镜像内 203 个运行时文件，
  **0 mismatches**；文件清单 SHA-256：`67abe67fec37a68cfe4463834fc2904d7483a873711a87bd627157ca3de87c19`。

## 环境与隔离

- SSH `bwh`，Linux x86_64，1 vCPU、1589 MiB RAM、832 MiB swap；准备前可用 RAM 约 913 MiB，磁盘约 15 GiB。
- 项目目录 `/opt/kindergarten-staging-20260908`，Compose project `kg-wmp9-staging`。
- MySQL 8.4.11：512 MiB 内存上限、640 MiB memory+swap、0.7 CPU，仅连接独立 internal 网络，**无主机端口**。
- app：384 MiB 内存上限、512 MiB memory+swap、0.7 CPU，UID/GID 10001；仅发布
  `127.0.0.1:18089 → 8080`，连接 edge/private 两个独立网络。
- 数据库使用独立 named volume；应用 data/exports 位于本项目目录。未挂载或访问生产正文、生产数据库或生产凭据。
- app/db 配置和测试凭据均 owner-only；一次性 `migration.env` 已删除。测试账号仅为本轮合成账号。
- Caddy 保留原配置完整字节，仅附加 staging host → loopback upstream 块；candidate validate 与 reload 通过。
  原/新配置 SHA-256 为 `72c4e50568864f934e08422e28ac3469c60f3707b80c6bc25e0edc5b8493648a` /
  `7d0a7cce9df239bbb81cc0ab87023be6d2e06b93e4950ad831eb72c95e7e2bcc`。
  原配置备份留在本项目 private 目录，未提交其内容。
- 镜像传输完毕后已关闭本机 5018 SSH 隧道，并停止自有 staging registry 节省内存；镜像与 registry 数据保留。
  关闭后 app 约 132 MiB、db 约 214 MiB，主机 available 约 702 MiB；仅为该时点空闲负载观测。
  app/db 正常重启使用已拉取的 immutable image；将来需重新拉取时先启动该 registry。

## 数据准备与诊断

- 在新建、空白、独立 MySQL 上，以一次性迁移容器显式执行 Alembic migrations 到 `3c9f4b2a7d1e`。
  这是隔离合成环境初始化，不是生产升级、生产备份恢复证明或 R5 migration receipt；生产升级仍须走已验证备份和迁移 job。
- 数据准备脚本只 seed 合成数据，不调用 exporter：5 个用户、4 个 APPROVED current plans、16 个精确 scope grants。
- 准备脚本首次因 `/scripts` 的 Python 搜索路径缺少 `/app` 在 import 阶段失败，尚未写入数据库；
  仅为一次性准备容器补 `PYTHONPATH=/app` 后成功。
- Docker 内部网络未发布请求的回环端口；为 app 增加 edge 网络后端口可达，db 仍只连接 internal 网络。
  两项修正均为本轮隔离环境配置，没有修改产品代码或放宽数据库权限契约。

## 已执行的在线检查

2026-09-08 05:25 UTC 的 HTTPS 回读：

| 门 | 结果 | 边界 |
|---|---|---|
| TLS | 验证通过、TLSv1.3、SAN 精确含 staging-manager.ywyz.tech | 证书有效期 2026-09-08 至 2026-12-07 |
| `/api/v1/health` | HTTP 200 / ok | 存活 |
| `/api/v1/readiness` | HTTP 200 / ready / database ok | 数据库连接与当前 Alembic head |
| `/login` | HTTP 200；用户名/密码字段存在，无缺管理员提示 | 登录页可达，**不是浏览器登录 PASS** |
| 认证服务诊断 | teacher / teaching_admin / sys_admin 的密码校验及真实 token resolver 成功 | 一次性诊断容器调用受支持认证服务；没有伪造 TrustedUiSession |
| 认证拒绝诊断 | 错误密码、跨租户登录、无效 token 均拒绝 | 不是完整 WMP 权限矩阵 |
| 诊断前后数据 | 25 张表 count/hash 全部相同 | 仅限此次认证诊断的数据库快照 |

CUA 实际返回 `apps=[]`、`browsers=[]`，针对 staging 登录页的 `getBrowser` 返回
`No browser is available`。未绕过受控浏览器，也未替换 session guard、调用内部 exporter 或用认证诊断
冒充受保护 UI/application 业务结果。本轮没有取得云端原始 DOCX 或执行 Office 消费端检查。

## 复审与证据

- 独立只读部署复审 **H/M/L = 0/0/0**，核验镜像/revision、app loopback、db internal/no ports、
  独立存储、资源限制、配置权限及 Caddy host 块；范围不包含尚未执行的 UI 业务或生产切换。
- 脱敏 JSON 证据目录：`/home/ywyz/wmp9-cloud-staging-20260908-evidence`，目录 0700、文件 0600。
- 对 12 个证据/日志文件及 app 日志扫描本轮生成的秘密值，未发现泄漏；没有输出扫描值。
- 测试登录交接：`/home/ywyz/wmp9-cloud-staging-20260908-private/staging-login.txt`，文件 0600；
  服务端原始引用为项目 `private/users.json`。密码值未输出到聊天、日志、Issue 或 Git。
- Aliyun 现场再次回读：生产仍为 beta10 immutable ref
  `ghcr.io/ywyz/kindergartenmanager@sha256:f4c76e24375c129e3bc0ae2b97f3a60e21f18a832e9eca49ee27d4361f9c5d34`，
  running/healthy；本轮未修改它。

此记录的后续文档提交不是 WMP-9 evidence closure，也不把候选源码 CI 当作该文档提交的 CI。
下一步是在此 HTTPS 环境完成受控浏览器登录、周/月计划及适用权限/状态/审计/零未授权持久化矩阵；
然后独立准备生产双平台 Release、备份恢复、显式迁移和镜像切换。Office 人工检查保持用户指定的延期状态。

阶段文档复审曾要求缩窄未单独归档 raw-manifest 的媒介类型声明；已改为仅称 linux/amd64 隔离候选镜像。
修正后独立文档复审 H/M/L = 0/0/0；文档契约与 WMP-8 专项 59 passed，`git diff --check` 通过。
这两项结论仅覆盖阶段记录，不覆盖待执行的浏览器业务矩阵。
