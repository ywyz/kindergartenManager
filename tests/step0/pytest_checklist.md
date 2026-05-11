# Step 0 pytest 测试清单

> 目标：验证阶段 0（Step 0.1 ~ Step 0.5）是否已经真正完成。\
> 说明：以下内容是 pytest 风格的验证清单，后续可以直接拆成 `tests/test_*.py`。

## 执行总则

- 按顺序执行 Step 0.1 到 Step 0.5。
- 任一项失败，都不能判定 Step 0 完整完成。
- 推荐先准备好本地测试环境变量文件 `.env`，再执行配置和数据库相关用例。

## 用例清单

| 用例 ID | 对应 Step | 用例名称 | 前置条件 | 执行命令 | 期望结果 | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| S0-01 | Step 0.1 | 标准目录结构存在 | 仓库已同步最新代码 | `find app tests alembic exports -type d | sort` | 输出包含实施计划要求的全部目录 | 目录缺失即失败 |
| S0-02 | Step 0.1 | Python 包可导入 | `app/core`、`app/service`、`app/auth` 已存在 `__init__.py` | `python -c "import app.core; import app.service; import app.auth"` | 无报错退出 | 任一导入报错即失败 |
| S0-03 | Step 0.1 | 包初始化文件完整 | 已创建目录结构 | `find app -name '__init__.py' | sort` | 关键 Python 包目录均有 `__init__.py` | 缺失即失败 |
| S0-04 | Step 0.1 | 运行时占位目录可用 | `exports/` 已存在 | `test -d exports && test -f exports/.gitkeep` | 目录和占位文件存在 | 缺失即失败 |
| S0-05 | Step 0.2 | 核心依赖清单完整 | `requirements.txt` 已提交 | `python -c "from pathlib import Path; print(Path('requirements.txt').read_text())"` | 包含 `nicegui`、`fastapi`、`sqlalchemy[asyncio]`、`aiomysql`、`alembic`、`pydantic-settings`、`passlib[argon2]`、`python-jose[cryptography]`、`httpx`、`tenacity`、`python-docx`、`apscheduler`、`pytest` | 任一核心依赖缺失即失败 |
| S0-06 | Step 0.2 | 核心库可导入 | 虚拟环境已激活且依赖安装完成 | `python -c "import nicegui, sqlalchemy, alembic, passlib, jose, httpx, tenacity, docx, apscheduler"` | 无报错退出 | 任一导入报错即失败 |
| S0-07 | Step 0.2 | 环境模板存在 | 仓库包含环境模板文件 | `test -f .env.example && grep -E 'DATABASE_URL|ENCRYPTION_KEY|JWT_SECRET|JWT_EXPIRE_MINUTES|HOLIDAY_API_URL|LOG_LEVEL' .env.example` | 六个配置项均可找到 | 任一配置项缺失即失败 |
| S0-08 | Step 0.3 | Settings 默认值正确 | `.env` 已准备测试假值 | `python -c "from app.core.config import Settings; s = Settings(); print(s.JWT_EXPIRE_MINUTES)"` | 输出 `60` | 默认值不对即失败 |
| S0-09 | Step 0.3 | Settings 能读取环境变量 | `.env` 中已填入测试假值 | `python -c "from app.core.config import Settings; s = Settings(); print(s.DATABASE_URL); print(s.HOLIDAY_API_URL)"` | 打印值与 `.env` 一致 | 读取失败或类型不对即失败 |
| S0-10 | Step 0.3 | Git 忽略规则生效 | 仓库含 `.gitignore` | `grep -E '^\.env(\.prod)?$' .gitignore` | `.env` 与 `.env.prod` 被忽略 | 任一规则缺失即失败 |
| S0-11 | Step 0.4 | JSON 日志输出 | `LOG_LEVEL` 已配置 | `python -c "from app.core.logging import get_logger; l = get_logger('test'); l.info('hello')"` | 输出包含 `message`、`level`、`logger`、`timestamp` 的 JSON 行 | 不是 JSON 或字段缺失即失败 |
| S0-12 | Step 0.4 | 日志级别受配置控制 | `LOG_LEVEL` 已改为非默认值做验证 | `python -c "from app.core.logging import get_logger; l = get_logger('test'); l.debug('dbg'); l.info('info')"` | 日志级别行为与配置一致 | 级别无效即失败 |
| S0-13 | Step 0.5 | 数据库基础模块可导入 | `app/core/database.py` 已就绪 | `python -c "from app.core.database import Base, AsyncSessionLocal; print('ok')"` | 输出 `ok` | 导入报错即失败 |
| S0-14 | Step 0.5 | Alembic 当前版本可读取 | `.env` 中 `DATABASE_URL` 有效 | `alembic current` | 命令可正常执行，首次可能为空版本 | 报错即失败 |
| S0-15 | Step 0.5 | Alembic 环境能加载 Base metadata | 迁移环境配置已完成 | `alembic history` | 能正常列出迁移历史或为空 | 加载失败即失败 |

## Step 0 总闸门

以下命令全部通过时，才可判定 Step 0 完整完成：

```bash
find app tests alembic exports -type d | sort
python -c "import app.core; import app.service; import app.auth"
python -c "import nicegui, sqlalchemy, alembic, passlib, jose, httpx, tenacity, docx, apscheduler"
python -c "from app.core.config import Settings; s = Settings(); print(s.JWT_EXPIRE_MINUTES)"
python -c "from app.core.logging import get_logger; l = get_logger('test'); l.info('hello')"
python -c "from app.core.database import Base, AsyncSessionLocal; print('ok')"
alembic current
```

## 后续建议

- 如果要把这份清单升级成真正的 pytest 集合，建议拆成以下文件：
  - `tests/test_bootstrap.py`
  - `tests/test_config.py`
  - `tests/test_logging.py`
  - `tests/test_database.py`
- 现阶段这份文件可先作为人工验收清单使用，后续再逐条转成自动化测试。