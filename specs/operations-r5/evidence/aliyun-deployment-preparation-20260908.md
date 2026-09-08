# Aliyun 在线部署准备（2026-09-08）

本轮用户指定通过 `ssh aliyun` 部署在线系统，并将 Office 客户端人工测试延期到其 Windows 机器。
该安排不预填 Office PASS，也不取消备份、显式迁移、镜像绑定和业务验收门。

## 起点与工作区

- `origin/main` fetch 后为 `8dcc83376577695b562529ec42adc6b48817f004`。
- Quality `34137274986` 与 CodeQL `34137274399` 均 completed/success，headSha 精确匹配。
- 原工作区 HEAD 为 `01bf6349a7c6f5268eba4425212f546874d651b0`，有既有 Graphify 查询缓存修改；全部保留。
- 使用独立 worktree `/tmp/kg-aliyun-deploy-20260908`，基于上述远端 SHA 准备变更。
- 已读 `formal-acceptance-local-20260907.md`；交接提及的 `formal-acceptance-local-20260908.md`
  在该远端 SHA 不存在，不推定其内容或结论。

## 现场只读回读

- SSH alias `aliyun` 可用，用户 `ecs-user`，Linux x86_64；Docker 运维需要 `sudo -n`。
- Caddy 服务 active，应用和 MySQL 容器 running/healthy。
- 运行应用的 revision label 为 `6bbff57f0c410459bcdb3bdd86980013d4b6c80e`，version `3.4.0-beta10`。
- 容器 `.Config.Image` 与部署 state current 均为：
  `ghcr.io/ywyz/kindergartenmanager@sha256:f4c76e24375c129e3bc0ae2b97f3a60e21f18a832e9eca49ee27d4361f9c5d34`。
- GitHub beta10 Release 的 source/ref 与上述值一致；registry raw OCI index 恰含 linux/amd64、linux/arm64。
  这里只记录已执行的回读，不冒充完整 release convergence 或此次新部署证据。
- 运行镜像执行 `alembic current` 为 `2b7f3d5e9c8a (head)`；目标源码的 head 为 `3c9f4b2a7d1e`。
- `https://manager.ywyz.tech/api/v1/health` 返回 HTTP 200 / status ok。
- `https://manager.ywyz.tech/api/v1/readiness` 返回 HTTP 200 / status ready / database ok。
- `https://manager.ywyz.tech/login` 返回 HTTP 200；这是登录页可达，不是认证或登录后业务 PASS。
- 本机代理 CONNECT 返回 503；仅对探针命令使用 `--noproxy '*'` 后直连成功，没有修改全局代理。
- 未读取密码文件内容，未修改生产配置、镜像、数据库、卷或凭据。

## 本地准备变更

发布 workflow 移除 Windows/Linux 桌面构建、下载上传与安装说明；保留双平台 Docker 构建、
docker-image.json、draft Release 和完整元数据复验。在 verify-release job 显式固定 Python 3.14.7。
相关测试改为守卫云端交付及现存 Python job，不再要求已删除桌面路径。

额外回归发现 WMP application 测试会话在 2026-09-07 18:00 UTC 固定过期；全量和单节点各复现一次
`session_expired`。仅将测试 helper 改为执行时刻起有效九小时，产品过期拒绝逻辑和业务断言不变。
此测试修复不作为生产业务验收替代；本轮没有变更产品运行时代码、schema、模板、依赖或安全契约。

## 交付边界

本记录是部署准备，尚未形成新版本的发布元组、备份恢复证据、迁移 receipt 或实际镜像切换证据。
最新 WMP 云端业务/权限矩阵及最终 evidence closure 仍未完成；Office 延期不能代替这些结果。
现网继续运行 beta10，不得将当前 HTTPS 探针、历史 WMP 本地证据或发布 workflow 修正写成最新主线部署 PASS。

## 本地验证

- 修改后发布/文档/runtime/application 相关专项：68 passed。
- 完整 `tests/`、Agent Foundation、WMP prerequisites、weekly/monthly 合并回归：
  **1774 passed, 1 skipped in 99.98s**，执行时取消外部 `KINDERGARTEN_DATA_DIR` 覆盖。
- 四个变更 Python 文件的 Ruff check / format check，以及 `git diff --check` 通过。
- 待提供隔离云端验收使用的 HTTPS 域名；可按用户指定的 aliyun 主机准备独立容器/数据库，
  但不擅自选择域名、创建付费资源或复用生产数据库完成 WMP-9 正式权限矩阵。
- 独立只读复审提出一项 M：Release 说明在首次启动前展示 `docker compose exec` 初始化，顺序不完整。
  已移除该捷径并指向部署指南/用户手册的受控 Bootstrap 流程；canonical 文档的一次性 override 契约保留。
  修复后上述相关专项再次 **68 passed in 2.06s**。最终微调只涉及 Release 说明及对应契约，
  1774 项结果来自此次说明微调前的完整回归，不声称微调后重跑了全量。
- 修复后独立只读复审 **H/M/L = 0/0/0**，范围仅本地部署准备 diff；不构成 WMP-9 总门 Review、
  发布、迁移或生产切换证据。新提交的远端 CI 尚未执行，不能引用起点 SHA 的 CI 代替。
