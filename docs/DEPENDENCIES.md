# Python 依赖安全基线

> 快照日期：2026-08-23。本文记录默认分支依赖策略、Dependabot #11–#37
> 的修复边界和质量门禁。后续升级必须重新解析依赖并回读 GitHub 告警。

## 1. 27 项 Dependabot 告警

GitHub 当前将 27 项开放告警归因到已经从仓库删除、但仍存在于依赖图快照中的
`uv.lock`。默认分支原有的 `requirements.txt` 下限同样不安全，因此不能把这些告警
作为误报直接关闭。

| 依赖族 | 告警 | 安全下限 |
|---|---:|---:|
| `aiohttp` | #11–#19、#32–#34（12 项） | `3.14.3` |
| `cryptography` | #20、#35–#37（4 项） | `50.0.0` |
| `starlette` | #21、#22、#27、#28（4 项） | `1.3.1` |
| `python-multipart` | #23–#26（4 项） | `0.0.31` |
| `python-engineio` | #29、#30（2 项） | `4.13.2` |
| `python-socketio` | #31（1 项） | `5.16.2` |

`requirements.txt` 采用不低于上表、并已联合验证的版本：aiohttp 3.14.3、
cryptography 50.0.0、Starlette 1.6.0、python-multipart 0.0.32、
python-engineio 4.13.5 和 python-socketio 5.16.4。NiceGUI 3.16.0 与 FastAPI
0.141.1 一并升级，避免在 Web 框架兼容面上单独强推传递依赖。

## 2. RED 与质量门禁

- Issue：[#49](https://github.com/ywyz/kindergartenManager/issues/49)。
- 稳定 RED：`ab1a621625fabc43e42aadbda1e189d2a2f0185e`，修复前连续三次得到
  同一组六族失败。
- `tests/test_dependency_security_floor.py` 固定最低安全版本，避免未来解析回落。
- `.github/workflows/quality.yml` 在常规 push 和 pull request 上使用 Python 3.14.7，
  执行安装、`pip check`、`pip-audit`、变更 Python 文件 Ruff、全新 SQLite 迁移和全量 pytest。
- `main@225fe13` 已有 47 条 Ruff 历史告警，本安全 PR 不跨范围机械修改业务代码；门禁对
  每次 push/PR 的变更 Python 文件执行严格 Ruff，阻止新增债务，同时保留全仓测试覆盖。

## 3. 约束策略

- 项目当前使用 `requirements.txt` 和 `>=` 安全下限，安装时解析当时兼容的较新版本。
- 直接声明传递依赖是为了防止解析回落，不表示应用直接调用这些包。
- 当前没有带哈希的锁文件，因此验收必须记录实际解析版本，不能只报告声明下限。
- 本地通过不等于 GitHub 告警已关闭。只有变更进入默认分支且依赖图重新计算后，
  才能回读 27 项告警的最终 `fixed` 状态。

## 4. 已知无修复例外

`python-jose` 传递依赖 `ecdsa==0.19.2` 仍对应 `PYSEC-2026-1325`、
`GHSA-wj6h-64fc-37mp` / `CVE-2024-23342`。当前没有上游修复版本；消除该风险需要
独立评估并替换 JWT 库，不属于 #49 的 27 项 Dependabot 修复范围。质量门禁只对这个
明确编号使用 `--ignore-vuln`，其他可检测漏洞仍会使构建失败。

## 5. 本地复验

在 Python 3.14.7 新建的隔离环境中执行。迁移复验必须显式指向一次性 SQLite，
避免读取 `.env` 后修改应用数据库或真实集成数据库；临时目录在当前 shell 退出时清理：

```bash
python -m pip install -r requirements.txt ruff==0.15.22 pip-audit==2.10.1
python -m pip check
python -m pip_audit -r requirements.txt --strict --ignore-vuln PYSEC-2026-1325
ruff check tests/test_dependency_security_floor.py
quality_db_dir="$(mktemp -d)"
trap 'rm -rf -- "$quality_db_dir"' EXIT
quality_database_url="sqlite+aiosqlite:///$quality_db_dir/quality.sqlite3"
DATABASE_URL="$quality_database_url" python -m alembic upgrade head
DATABASE_URL="$quality_database_url" python -m alembic current
python -m pytest tests/ -q
```

2026-08-23 的 #49 GREEN 复验记录：

- 基线：`main@225fe139`；稳定 RED：`ab1a621625fabc43e42aadbda1e189d2a2f0185e`。
- 环境：Python 3.14.7、uv 0.12.5；隔离环境解析并安装 103 个包，`pip check`
  返回 `No broken requirements found.`。
- 实际关键版本：NiceGUI 3.16.0、FastAPI 0.141.1、aiohttp 3.14.3、
  cryptography 50.0.0、Starlette 1.6.0、python-multipart 0.0.32、
  python-engineio 4.13.5、python-socketio 5.16.4。
- `pip-audit 2.10.1`：`No known vulnerabilities found, 1 ignored`；唯一忽略项为
  第 4 节明确记录的 `PYSEC-2026-1325`。
- 全新 SQLite 从空库迁移到 `a6c4d8e2f9b1 (head)`；全量 pytest：`530 passed`。
