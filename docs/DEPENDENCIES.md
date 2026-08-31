# Python 依赖安全基线

> 安全基线日期：2026-08-23；当前环境复核日期：2026-08-31。本文记录默认分支依赖策略、
> Dependabot #11–#38 的修复边界和质量门禁。完整开发工具与 Skills 换机清单见
> [DEVELOPMENT_WORKSTATION.md](DEVELOPMENT_WORKSTATION.md)。后续升级必须重新解析依赖并回读 GitHub 告警。

当前复核结果：`.python-version`、Docker 和 CI/Release 均以 Python `3.14.7` 为审查基线；
`uv.lock` revision 3 当前锁定 80 个包，`uv lock --check`、`uv tree --locked --all-groups`
与 `.venv/bin/python -m pip check` 均通过。下文的 82/103 等数量是固定 SHA 的历史验收记录，
不得当作当前环境快照。CI、Docker 和 Release 仍通过安全下限型 `requirements.txt` 安装，尚未
直接消费精确 `uv.lock`；该差异需单独收敛，不能仅凭本机锁验证宣称发布环境完全可复现。

2026-08-31 已使用 uv `0.12.7` 完成当前工作区的显式锁刷新与同步；锁文件中的以下包由旧快照升级，
其余包保持解析结果不变：

| 包 | 当前锁定版本 |
|---|---:|
| `bidict` | `0.24.1` |
| `click` | `8.5.0` |
| `cryptography` | `50.0.1` |
| `pydantic` | `2.13.5` |
| `pydantic-core` | `2.46.5` |
| `python-engineio` | `4.14.0` |
| `websockets` | `17.1` |

本次 `uv lock --check`、`uv sync` 和 `uv pip check` 均通过。Ruff、pip-audit 与 PyInstaller 的本机工具
版本分别为 `0.16.5`、`2.10.1`、`6.22.2`；CI workflow 当前仍显式 pin Ruff `0.15.22`，不能把本机最新版
误写为 CI 已更新。本轮分别使用 PyPI 与 OSV 后端执行实时漏洞查询时，代理均返回 503；因此只能确认
工具版本、锁解析和包兼容性，不能把历史审计结果当作当前漏洞扫描结论。依赖图告警是否 `fixed` 仍须在
网络恢复后从默认分支和 GitHub 回读。

## 1. 历史 Dependabot 告警（#11–#38）

GitHub 曾将 27 项开放告警归因到历史 `uv.lock` 中的漏洞版本。仅删除锁文件并刷新
`requirements.txt` 后，旧锁快照仍保留在依赖图中；本次恢复 `pyproject.toml` 并重新
生成安全的 `uv.lock`，用于让依赖图以新快照覆盖旧版本。告警是否转为 `fixed` 仍须在
变更进入默认分支、依赖图完成刷新后回读，不能作为误报直接关闭。

#11–#37 已在 `main@863a238` 的新锁快照中转为 `fixed`。该锁随后暴露了此前未被
依赖图追踪的 `ecdsa` 告警 #38；它没有上游修复版本，必须移除依赖链，不能通过升级或
dismiss 闭环。

| 依赖族 | 告警 | 安全下限 |
|---|---:|---:|
| `aiohttp` | #11–#19、#32–#34（12 项） | `3.14.3` |
| `cryptography` | #20、#35–#37（4 项） | `50.0.0` |
| `starlette` | #21、#22、#27、#28（4 项） | `1.3.1` |
| `python-multipart` | #23–#26（4 项） | `0.0.31` |
| `python-engineio` | #29、#30（2 项） | `4.13.2` |
| `python-socketio` | #31（1 项） | `5.16.2` |
| `ecdsa` | #38（1 项） | 无修复版本；移除 `python-jose` 依赖链 |

`requirements.txt` 采用不低于上表、并已联合验证的版本：aiohttp 3.14.3、
cryptography 50.0.0、Starlette 1.6.0、python-multipart 0.0.32、
python-engineio 4.13.5 和 python-socketio 5.16.4。NiceGUI 3.16.0 与 FastAPI
0.141.1 一并升级，避免在 Web 框架兼容面上单独强推传递依赖。

## 2. RED 与质量门禁

- Issue：[#49](https://github.com/ywyz/kindergartenManager/issues/49)。
- 稳定 RED：`ab1a621625fabc43e42aadbda1e189d2a2f0185e`，修复前连续三次得到
  同一组六族失败。
- #38 稳定 RED：`4c9bd2c2a8c80d459411a451988da11b8c592aed`，连续三次得到
  `PyJWT` 安全下限缺失、锁中存在 `ecdsa` / `python-jose` 的同一失败。
- `tests/test_dependency_security_floor.py` 固定最低安全版本，并禁止精确锁重新引入
  无修复的 `ecdsa` / `python-jose` 运行时依赖链。
- `.github/workflows/quality.yml` 在常规 push 和 pull request 上使用 Python 3.14.7，
  执行安装、`pip check`、`pip-audit`、变更 Python 文件 Ruff、全新 SQLite 迁移和全量 pytest。
- `main@225fe13` 已有 47 条 Ruff 历史告警，本安全 PR 不跨范围机械修改业务代码；门禁对
  每次 push/PR 的变更 Python 文件执行严格 Ruff，阻止新增债务，同时保留全仓测试覆盖。

## 3. 约束策略

- `pyproject.toml` 中的运行与开发依赖只声明包名，不添加版本约束；`uv lock --upgrade`
  解析当时与 Python 3.12+ 兼容的最新版，并在 `uv.lock` 中记录精确版本。
- `requirements.txt` 继续保留 `>=` 安全下限，供现有 Quality 安装流程和稳定 RED
  回归测试使用。两者分别承担安全下限门禁与可复现锁定职责。
- 直接声明传递依赖是为了防止解析回落，不表示应用直接调用这些包。
- 新版本发布不会自动使锁文件过期；升级时必须显式执行 `uv lock --upgrade`，并提交
  `pyproject.toml` 与 `uv.lock` 的一致变更。
- 本地通过不等于 GitHub 告警已关闭。只有变更进入默认分支且依赖图重新计算后，
  才能回读告警的最终 `fixed` 状态。

## 4. 无修复依赖处理

`python-jose` 传递依赖 `ecdsa==0.19.2` 对应 `PYSEC-2026-1325`、
`GHSA-wj6h-64fc-37mp` / `CVE-2024-23342`，且没有上游修复版本。应用只使用 HS256，
但保留未使用的漏洞包仍不是可接受闭环，因此以 `PyJWT>=2.13.0` 替换 `python-jose`，
重新生成的锁文件不得包含 `ecdsa` 或 `python-jose`。Quality 不再保留该漏洞的
`pip-audit` 忽略项；完成状态以默认分支依赖图将 #38 回读为 `fixed` 为准。

## 5. 本地复验

### 5.1 当前锁定环境

在 Python `3.14.7` 的 uv 环境中执行：

```bash
uv sync --locked --all-groups
uv lock --check
uv pip check
.venv/bin/python -m pytest tests/ -q
```

迁移复验必须显式指向一次性 SQLite，避免读取 `.env` 后连接生产或旧开发库；临时目录在当前 shell 退出时清理：

```bash
quality_db_dir="$(mktemp -d)"
trap 'rm -rf -- "$quality_db_dir"' EXIT
quality_database_url="sqlite+aiosqlite:///$quality_db_dir/quality.sqlite3"
DATABASE_URL="$quality_database_url" .venv/bin/python -m alembic upgrade head
DATABASE_URL="$quality_database_url" .venv/bin/python -m alembic current
```

若要复现 CI 的安全下限安装，使用 workflow 中的 Ruff pin；本机最新版工具不改变 CI 的历史验证事实：

```bash
uv lock --check
uv sync --locked --all-groups
uv pip check
python -m pip install -r requirements.txt ruff==0.15.22 pip-audit==2.10.1
python -m pip check
python -m pip_audit -r requirements.txt --strict
ruff check app/auth/jwt.py tests/test_jwt.py tests/test_dependency_security_floor.py
quality_db_dir="$(mktemp -d)"
trap 'rm -rf -- "$quality_db_dir"' EXIT
quality_database_url="sqlite+aiosqlite:///$quality_db_dir/quality.sqlite3"
DATABASE_URL="$quality_database_url" python -m alembic upgrade head
DATABASE_URL="$quality_database_url" python -m alembic current
python -m pytest tests/ -q
```

### 5.2 历史验收记录

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

2026-08-23 的锁文件恢复复验记录：

- 基线：`main@af33c142be04760b618703859fcbe7668f7dfb6d`；Python 3.14.7、uv 0.11.30。
- `pyproject.toml` 的 28 个直接依赖均无版本约束；`uv lock --upgrade` 解析 82 个包，
  隔离环境安装 79 个包，`uv lock --check` 与 `uv pip check` 均通过。
- 六族精确锁定版本：aiohttp 3.14.3、cryptography 50.0.0、Starlette 1.6.0、
  python-multipart 0.0.32、python-engineio 4.13.5、python-socketio 5.16.4。
- 对已安装锁定环境执行 pip-audit：`No known vulnerabilities found, 1 ignored`；唯一忽略项
  仍为第 4 节记录的 `PYSEC-2026-1325`。
- 全新 SQLite 从空库迁移到 `a6c4d8e2f9b1 (head)`；全量 pytest：`530 passed`。

2026-08-23 的 #38 GREEN 复验记录：

- 基线：`main@863a2388c2a828078e85c30d5943faf16650f1bb`；稳定 RED：
  `4c9bd2c2a8c80d459411a451988da11b8c592aed`。
- 环境：Python 3.14.7、uv 0.11.30；锁文件解析 78 个包，隔离环境安装 75 个包。
- `python-jose 3.5.0`、`ecdsa 0.19.2`、`rsa 4.9.1`、`pyasn1 0.6.4` 和 `six 1.17.0`
  已从精确锁中移除，替换为 `PyJWT 2.13.0`；HS256 token 接口与字段保持不变。
- `uv lock --check`、`uv pip check` 与 Ruff 均通过；无忽略项执行 pip-audit：
  `No known vulnerabilities found`。
- 全新 SQLite 从空库迁移到 `a6c4d8e2f9b1 (head)`；目标测试 `8 passed`（含旧
  `python-jose` HS256 token 跨库兼容），全量 pytest：`532 passed`。
