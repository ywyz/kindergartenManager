# Python 依赖安全基线

> 快照日期：2026-08-23。本文记录 Python 运行时、`requirements.txt` 安全下限、Dependabot 告警映射和验证规则。
> PyPI 最新版本会变化，后续升级必须重新查询官方 PyPI 并重跑依赖解析。

## 0. Python 运行时

- 项目运行时基线：[Python 3.14.7](https://www.python.org/downloads/release/python-3147/)。
- `.python-version`、`Dockerfile` 和 GitHub Release 工作流使用相同的精确补丁版本。
- Python 小版本升级后必须在新解释器创建的干净虚拟环境中重新解析全部依赖并运行全量测试。

## 1. 本次升级

| 包 | 新的最小版本 | 原因 |
|---|---:|---|
| `nicegui` | `3.16.0` | 当时 PyPI 最新稳定版；项目 UI 框架 |
| `fastapi` | `0.141.1` | 当时 PyPI 最新稳定版；与 Starlette 1.6.0 联合解析 |
| `cryptography` | `50.0.0` | Dependabot #20/#35–#37；包含 CVE-2026-69247/69248/69249 修复版本 |
| `aiohttp` | `3.14.3` | Dependabot #11–#19/#32–#34 |
| `python-socketio` | `5.16.4` | Dependabot #31；NiceGUI 实时通信依赖 |
| `python-engineio` | `4.13.5` | Dependabot #29/#30；Socket.IO 传递依赖 |
| `starlette` | `1.6.0` | Dependabot #21/#22/#27/#28 |
| `python-multipart` | `0.0.32` | Dependabot #23–#26 |

上述版本来自官方 PyPI 项目页和 `pip index versions`。Dependabot 编号来自
`ywyz/kindergartenManager` 在快照日期的开放告警。

## 2. 约束策略

- 项目当前使用 `requirements.txt` 和 `>=` 安全下限，安装时解析当时兼容的较新版本。
- 直接写入传递依赖的目的是防止解析回落到已知易受攻击版本，不表示应用直接调用这些包。
- NiceGUI、FastAPI、Starlette、Socket.IO 和 Engine.IO 属于一个联合兼容面，升级时必须在同一次 pip 解析中验证。
- 当前还没有带哈希的锁文件；因此验证报告必须记录实际解析版本，不得只报告下限。

## 3. 验证

```bash
python3.14 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install --upgrade -r requirements.txt
.venv/bin/pip check
.venv/bin/python -m pytest tests/ -q
```

至少记录 NiceGUI、FastAPI、Starlette、Socket.IO、Engine.IO、cryptography、aiohttp 和
python-multipart 的实际版本。如修改了图片链，另跑 `tests/test_image_processing.py` 和
`tests/test_config_image_settings.py`。

## 4. Dependabot 回读

本地修改和测试不会立即关闭 GitHub 告警。只有当变更进入 GitHub 默认分支，依赖图重算后
对应告警才可能关闭。交付时应分别记录：

1. 本地 `requirements.txt` 与解析版本。
2. 推送后的远端 SHA/CI `headSha`。
3. Dependabot 告警的最终 open/fixed 回读。

## 5. 2026-08-23 本地验证记录

- 基线：`dev4.0@0657c3a`（本地维护审查起点；结果不代表 `main` 已发布）。
- 环境：Python 3.14.7、uv 0.12.5。
- 安装：当前环境 `uv pip check --python .venv/bin/python` 检查 83 个包，报告无依赖冲突；此前本分支依赖升级解析记录为 79 个包。
- 关键实际版本：NiceGUI 3.16.0、FastAPI 0.141.1、Starlette 1.6.0、
  cryptography 50.0.0、aiohttp 3.14.3、python-socketio 5.16.4、
  python-engineio 4.13.5、python-multipart 0.0.32。
- 自动回归：清理后包含依赖安全下限和 Python 运行时一致性测试的全量 pytest `535 passed`。
- 迁移：全新 SQLite 数据库从空库升级到 `a6c4d8e2f9b1 (head)` 成功。
- Linux PyInstaller 冒烟：PyInstaller 6.22.2 在 Python 3.14.7 下成功生成 onedir 产物。
- Docker Hub 已确认 `python:3.14.7-slim` 标签可用；本机 Docker daemon 不可访问，未把标签检查写成完整镜像构建通过。
- `pip-audit` 对实际安装环境报告一个不在当前 Dependabot 列表中的残余风险：
  `python-jose` 传递依赖 `ecdsa==0.19.2` 对应 `PYSEC-2026-1325` / `GHSA-wj6h-64fc-37mp` /
  `CVE-2024-23342`，当前无上游修复版本。消除该风险需独立评估并替换 JWT 库，不属于本次版本升级。
