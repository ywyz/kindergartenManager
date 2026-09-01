# R5-54 Readiness 冻结规格与 stable RED 设计

## 契约

- `GET /api/v1/health` 保持免鉴权 liveness，响应兼容且绝不访问数据库。
- 新增免鉴权 `GET /api/v1/readiness`。每次请求使用独立短生命周期 session/connection，只执行一次方言中立、
  无副作用的 `SELECT 1`；不得读取业务表、commit、flush、审计或执行 DML/DDL。
- 成功为 HTTP 200、`status=ready`、`checks.database=ok`；连接、查询或固定硬超时失败为 HTTP 503、
  `status=not_ready`、`checks.database=failed`。
- host cancellation 必须传播，不得伪装成 503；并发探针彼此独立，不共享 session 或业务事务。
- 失败响应和日志不得含异常正文、SQL、数据库 URL/主机/用户名/密码/API Key/tenant/user。
- 不做业务重试。断连由 SQLAlchemy/driver 使坏连接失效；数据库恢复后由后续独立探针重新取连接验证，
  不要求重启应用，也不得因此运行迁移或写业务数据。
- Compose 的 app healthcheck 使用镜像内 Python 标准库访问 readiness；Caddy 初次启动等待 app
  `service_healthy`；db healthcheck 与 app→db `service_healthy` 保持，app 不获得 root 凭据。
- `scripts/deploy.py --health-url` 继续表示 liveness，并新增独立、必填 `--readiness-url`。deploy、自动恢复、
  显式 rollback、legacy migration 的每次目标/恢复镜像都必须先通过 liveness、再通过 readiness，之后才可
  写部署状态或宣告成功。任一门失败都不得运行 migration、删除卷或更改 secret。

## stable RED

RED 必须 collection clean，连续两次命令得到同一 collected/passed/failed 分布；失败只能指向未实现 seam。

1. `tests/test_api_routes.py`：免鉴权、成功、连接失败、查询失败、超时、取消、并发、恢复、脱敏、零写入，
   并证明 health 不触库。
2. `tests/test_docker_compose.py`：app Python stdlib readiness healthcheck、Caddy `service_healthy`、db 依赖与
   root 凭据隔离。
3. `tests/test_deploy_script.py`：URL 分离与校验、双门顺序、目标失败恢复、恢复后二次双门、四条 action 在
   双门前零状态写入；尤其覆盖首次 live image snapshot 不得提前建立 state。

稳定 RED 结果记录回 `evidence-ledger.md` 后才进入最小 GREEN；不得使用 skip/xfail、真实网络、固定长 sleep
或放宽既有 immutable digest 契约制造 RED/GREEN。

