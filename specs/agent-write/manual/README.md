# W008 固定 SHA 交付验收

本目录只提供测试态验收适配器，不增加产品能力。Provider/Tool 面始终是四个 READ、两个 DRAFT、零个
WRITE；Agent WRITE 仍只有当前页面、当前计划、当前 revision 的单份 Patch，经本地应用显式确认后执行。
helper 不提供自动重试、批量/跨页面采用、设置/文件/Word/删除/创建写入或 Patch 持久化。

## 共同门禁

1. 先提交产品、helper、测试与本文，人工核对完整 40 位 `TESTED_SHA`。之后任一产品/helper/test 字节变化
   都使 Review、CI、MySQL 与浏览器证据失效。
2. 除下述 Alembic 子进程外，所有命令从该 SHA 的全新 detached linked worktree 根执行；`.git` 必须是文件，
   Git 必须干净。Alembic 只在 owner-only 外部临时运行目录中启动，但代码、配置与 migration 仍全部取自该
   fixed-SHA worktree。解释器使用已验证主 checkout 的绝对 `.venv/bin/python`，不得在验收 worktree 创建
   `.venv` 链接。
3. 只用合成用户、计划、Provider 配置与随机 MySQL 密码。Issue 不记录密码、Key、endpoint、Provider/
   Patch 正文、JWT、session、confirmation、nonce、原始异常或日志。
4. 一次失败即停；不得在同一场景自动重试。容器 health readiness 轮询不属于 Provider/WRITE 重试。
5. 每个浏览器场景使用从同一 pristine seed 复制出的独立 `0600` SQLite；禁止复用已发生 WRITE 的数据库。
6. 只停止本次明确记录的 PID/容器。默认停止在 merge、关闭 Issue 与 release 之前。

## Linux 浏览器故障矩阵

W008 复用已审计的 F009 **mock seed 与关闭 mock server 作为合成 fixture**，但不复用 F009 的零写比较器，
也不把 F009 证据冒充 W008 PASS。先在 fixed-SHA worktree 中创建两个 owner-only 临时目录：

```text
SEED_DIR=$(mktemp -d /tmp/km-f009.XXXXXX)
RUN_DIR=$(mktemp -d /tmp/km-w008.XXXXXX)
chmod 700 "$SEED_DIR" "$RUN_DIR"
ABS_PYTHON=/absolute/path/to/verified/.venv/bin/python

"$ABS_PYTHON" specs/agent-foundation/manual/f009_seed.py seed \
  --mode mock --tested-sha TESTED_SHA --database "$SEED_DIR/pristine.db"
"$ABS_PYTHON" specs/agent-foundation/manual/f009_mock_server.py \
  --tested-sha TESTED_SHA --slow-seconds 8
```

seed 只创建合成用户、A/B 两日计划与固定虚构 Provider 配置；它不执行 Agent WRITE。每个场景先执行一次：

```text
install -m 600 "$SEED_DIR/pristine.db" "$RUN_DIR/SCENARIO.db"
```

普通场景省略 `--fault`；expiry 可把 TTL 缩短到 3 秒。事务故障只选一个关闭枚举值：

```text
"$ABS_PYTHON" specs/agent-write/manual/w008_browser.py \
  --tested-sha TESTED_SHA --database "$RUN_DIR/SCENARIO.db" \
  --port 18080 --ttl 300

"$ABS_PYTHON" specs/agent-write/manual/w008_browser.py \
  --tested-sha TESTED_SHA --database "$RUN_DIR/SCENARIO.db" \
  --port 18080 --ttl 300 --fault after_version
```

helper 在任何 application/NiceGUI import 前重验 exact SHA、linked worktree、Git、SQLite 类型/权限、合成
secrets lock 与 loopback 端口。fault 仅包装 `ConfirmedDailyPlanWriteService` 的 session factory；普通保存、
登录、Provider 与其他页面 session 不受影响。stdout 只输出 `issue/apply/reconcile` 脱敏计数。

每个 fresh DB 只执行一个场景并记录可见断言：

1. **逐 Patch + 双击**：生成一份 DRAFT，双击“准备确认”仍只有一个 pending；双击“确认采用”仍只有一次
   apply，revision `N → N+1`，version/audit 各新增一行。
2. **过期**：`--ttl 3`，可见等待真实过期后确认；显示已过期、零 DML、零自动重试。
3. **错误会话**：签发后退出/重新登录，再从旧页确认；页面 fail closed，writer apply 为 0，数据库不变。
4. **并发旧 revision**：另一标签经普通“保存草稿”使 revision `N → N+1`；旧确认显示 revision 已变化，
   Agent version/audit 仍为 0/0。
5. **页面边界回归**：A→B→A、另一标签、reload/disconnect 均不恢复或跨页采用旧 Patch。
6. **确定性事务故障**：分别使用 `after_version`、`after_cas`、`after_audit`、
   `known_before_commit`；页面显示关闭失败，业务正文/revision/version/audit 全回 baseline，apply 恰一次。
7. **commit unknown / not applied**：`unknown_before_commit` 后只能显式点“人工对账”；显示未生效，
   reconcile 恰一次，数据库全回 baseline。
8. **commit unknown / applied**：`unknown_after_commit` 后显式人工对账；显示已采用，revision `N → N+1`，
   version/audit 各恰一行；不得再次 apply。

每次操作前后只查询合成日期、revision 与证据计数，不输出正文：

```text
sqlite3 -readonly "$RUN_DIR/SCENARIO.db" \
  "SELECT plan_date,revision FROM daily_plan ORDER BY id; \
   SELECT 'version',COUNT(*) FROM daily_plan_operation_version; \
   SELECT 'audit',COUNT(*) FROM agent_write_audit;"
```

mock 每份 DRAFT 仍恰有两个串行 Provider 请求；issue/apply/reconcile、页面等待、确认与对账不得增加请求。

## 真实 MySQL 8

不得使用仓库 Compose 的持久 volume。只使用一次性、固定名称、loopback 端口与 tmpfs；启动前先确认同名
容器和端口均为空。镜像 pull 是独立可见门，失败不自动重试。

```text
MYSQL_CONTAINER=km-w008-mysql
MYSQL_PORT=13306
MYSQL_ROOT_PASSWORD=$(openssl rand -hex 32)
MYSQL_APP_PASSWORD=$(openssl rand -hex 32)

sudo -n docker pull mysql:8
sudo -n docker run --detach --rm --name "$MYSQL_CONTAINER" \
  --publish "127.0.0.1:$MYSQL_PORT:3306" \
  --tmpfs '/var/lib/mysql:rw,nosuid,nodev,noexec,size=2g' \
  --env MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  --env MYSQL_DATABASE=kmw008 \
  --env MYSQL_USER=km_w008 \
  --env MYSQL_PASSWORD="$MYSQL_APP_PASSWORD" \
  --health-cmd='MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqladmin ping --silent -h 127.0.0.1 -uroot' \
  --health-interval=1s --health-timeout=5s --health-retries=120 \
  mysql:8 \
  --log-bin-trust-function-creators=1
```

该 server 参数只适用于本次 loopback/tmpfs disposable 验收容器：保留默认 binary log，但显式允许没有全局
`SUPER` 的 schema-scoped app user 创建 migration 定义的 trigger；不得外推为共享生产 MySQL 的默认配置，
也不得以 `--skip-log-bin`、root migration URL 或 app `SUPER` 代替。容器 healthy 后记录官方 image digest，
并只读确认 MySQL major 8、`@@GLOBAL.log_bin=1`、`@@GLOBAL.log_bin_trust_function_creators=1` 与 fresh schema
table count `0`：

```text
sudo -n docker exec "$MYSQL_CONTAINER" sh -lc \
  'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -N -B -h127.0.0.1 -uroot -D kmw008 \
  -e "SELECT VERSION(), @@GLOBAL.log_bin, @@GLOBAL.log_bin_trust_function_creators; SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE();"'
```

随后用随机 app 密码只在进程环境中组装 URL；Alembic 与 live helper 都不得使用 root/SUPER principal，
不得把 URL 作为 CLI 参数或贴入证据：

```text
MYSQL_URL="mysql+aiomysql://km_w008:$MYSQL_APP_PASSWORD@127.0.0.1:$MYSQL_PORT/kmw008?charset=utf8mb4"
TESTED_WORKTREE=$PWD
MYSQL_MIGRATION_RUNTIME=$(mktemp -d /tmp/km-w008-mysql-migrations.XXXXXX)

run_w008_alembic() {
  (
    cd "$MYSQL_MIGRATION_RUNTIME" || exit 1
    PYTHONPATH="$TESTED_WORKTREE" \
      ENCRYPTION_KEY="f009-fictional-encryption-key-do-not-use" \
      JWT_SECRET="f009-fictional-jwt-secret-do-not-use" \
      DATABASE_URL="$MYSQL_URL" \
      "$ABS_PYTHON" -m alembic -c "$TESTED_WORKTREE/alembic.ini" "$@"
  )
}

run_w008_alembic upgrade head
run_w008_alembic current
run_w008_alembic downgrade a6c4d8e2f9b1
run_w008_alembic current
run_w008_alembic upgrade head
run_w008_alembic current

W008_MYSQL_DATABASE_URL="$MYSQL_URL" \
  "$ABS_PYTHON" specs/agent-write/manual/w008_mysql.py --tested-sha TESTED_SHA
```

固定虚构 Key 只阻止配置层生成 secrets；POSIX lifecycle lock 只会落在
`MYSQL_MIGRATION_RUNTIME`，不会污染或放宽 fixed-SHA worktree。函数使用 subshell，因此每次 migration 后
自动返回 worktree 根；live helper 随后仍会拒绝 worktree 内任何 `.env`/secrets/lock。

三个 `current` 必须依序为 `e5f7a9c2d4b6`、`a6c4d8e2f9b1`、`e5f7a9c2d4b6`。live helper 单次验证：

- 官方 MySQL major 8 与最终 exact head；
- 两张 evidence 表的 UPDATE/DELETE 四个 trigger 精确存在，四次真实 DML 均返回 errno 1644，且全行 digest
  不变；
- 两个真实 session 对同一 revision 的生产 CAS 恰一真一假，最终 revision 为 2；
- 生产 `get_user_by_id(..., for_update=True)` 持锁时，竞争 session 返回 errno 1205；释放后可重新取锁；
- 输出仅含 SHA、head、trigger 数量、CAS 布尔值/revision 与 lock errno。

任一迁移或行为门失败都保留该 disposable 容器供只读诊断，不自动修补或重跑。全部脱敏证据捕获后，只停止
精确容器名；`--rm + tmpfs` 使合成数据库随容器停止而消失：

```text
sudo -n docker stop "$MYSQL_CONTAINER"
unset MYSQL_ROOT_PASSWORD MYSQL_APP_PASSWORD MYSQL_URL
```

## 最终证据

同一 `TESTED_SHA` 必须同时具备 Standards/Spec 0/0、本地全门 GREEN、远端分支精确 SHA、Quality success、
真实 MySQL 8 PASS、Linux 浏览器矩阵 PASS 与 OPEN Issue 脱敏回写。任一项不能替代另一项；本文、helper 或
测试在人工验收后再变化时，必须生成新 SHA 并重跑受影响的全部门。
