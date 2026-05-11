# 测试说明与执行情况

## 1. 文档目的

记录当前仓库的测试组织方式、Step 0 测试覆盖范围、执行命令与最近一次验证结果，作为后续阶段扩展测试时的基线说明。

## 2. 当前测试资产

### 2.1 Step 0 自动化测试文件

- `tests/conftest.py`
  - 作用：提供 Step 0 测试默认环境变量、仓库根目录 fixture、模块重载辅助函数。
- `tests/step0/test_bootstrap.py`
  - 作用：验证目录结构、Python 包初始化、`exports/.gitkeep`、`requirements.txt` 依赖项、`.env.example` 关键字段。
- `tests/step0/test_config.py`
  - 作用：验证 `Settings` 默认值、环境变量读取、`.gitignore` 中 `.env` / `.env.prod` 忽略规则。
- `tests/step0/test_logging.py`
  - 作用：验证 `get_logger()` 输出 JSON 结构化日志，并校验日志级别是否受配置控制。
- `tests/step0/test_database.py`
  - 作用：验证数据库基础模块导出项、`get_async_session()` 结构、Alembic 脚手架文件存在、`env.py` 读取 `Settings.DATABASE_URL` 并绑定 `Base.metadata`。
- `tests/step0/pytest_checklist.md`
  - 作用：保留人工验收版测试清单，便于与自动化测试逐项对照。

## 3. Step 0 测试范围说明

### 3.1 覆盖范围

Step 0 自动化测试覆盖以下内容：

1. 项目骨架目录是否齐全。
2. Python 包初始化文件是否齐全。
3. 运行时占位目录 `exports/` 是否存在且包含 `.gitkeep`。
4. `requirements.txt` 是否包含阶段 0 所需核心依赖。
5. `.env.example` 是否包含核心配置项。
6. `app/core/config.py` 中 `Settings` 默认值与环境变量读取是否正确。
7. `.gitignore` 是否正确忽略 `.env` 与 `.env.prod`。
8. `app/core/logging.py` 是否输出 JSON 日志，且字段包含 `timestamp`、`level`、`logger`、`message`。
9. `LOG_LEVEL` 是否能影响日志输出级别。
10. `app/core/database.py` 是否正确暴露 `Base`、`AsyncSessionLocal`、`get_async_session()`。
11. Alembic 脚手架是否存在，且 `alembic/env.py` 是否读取配置并绑定 `Base.metadata`。

### 3.2 设计约束

- Step 0 测试以“启动基线验证”为目标，不要求真实 MySQL 可连接。
- 数据库相关测试仅验证模块结构、引擎配置与 Alembic 接线，不执行真实迁移。
- 测试通过 `tests/conftest.py` 注入默认环境变量，避免因本地未准备 `.env` 导致 pytest 收集阶段失败。

## 4. 执行方式

### 4.1 推荐命令

在仓库根目录执行：

```bash
.venv/bin/pytest tests/step0 -q
```

如果需要更详细输出，可执行：

```bash
.venv/bin/pytest tests/step0 -v --tb=short
```

## 5. 最近一次测试情况

### 5.1 执行信息

- 执行日期：2026-05-11
- 执行命令：`.venv/bin/pytest tests/step0 -q`
- 覆盖目录：`tests/step0/`

### 5.2 执行结果

- 总结果：`18 passed, 1 warning in 2.06s`
- 结论：Step 0 对应的自动化测试全部通过，可作为阶段 0 已完成的回归基线。

### 5.3 Warning 说明

- warning 来源：`pythonjsonlogger.jsonlogger` 的第三方弃用提示。
- 影响判断：不影响本项目 Step 0 测试结论，不属于当前业务代码失败。
- 后续处理建议：后续若升级日志模块，可评估将导入路径从 `pythonjsonlogger.jsonlogger` 调整为新版推荐路径。

## 6. 当前结论

截至 2026-05-11，阶段 0 已具备以下测试基线：

1. 有可重复执行的 pytest 用例。
2. 有人工验收版 markdown 清单与自动化测试实现一一对应。
3. 有最近一次执行结果留档，可供后续 Step 1 开发前回归验证。

## 7. 后续扩展建议

1. 阶段 1 开始后，继续按同样方式为账号、鉴权、仓库层与服务层补充 pytest。
2. 后续增加统一命令入口，例如 `Makefile`、`scripts/test.sh` 或 CI 工作流。
3. 在阶段 8 全量测试前，逐步将各步骤的 markdown 验收清单同步转成自动化用例。