# 一对一倾听观察子系统 — 进度记录

> 配套：[design.md](design.md)、[dev-plan.md](dev-plan.md)、[test-plan.md](test-plan.md)。
> 分支：`dev3.1`（从 `dev3.0` 切出）。本文件随分支同步，便于跨电脑续作与测试。

## 当前状态（2026-06-19）

- **已完成并自动测试通过：P0 ~ P7**
- **待手动测试**：P7（UI 页面端到端流程 + 导出）— 已停在此里程碑等待手动测试反馈
- **未开始**：P8（历史列表 + 多幼儿批量按领域导出）、P9（文档收尾 + 全量回归）
- 自动化测试：一对一倾听相关新增 **54** 个测试全部通过；**全量 444 passed**
- 应用本地 sqlite 启动冒烟通过：`NiceGUI ready`，路由 `/one-on-one-listening` 返回 `HTTP 200`

## 数据库迁移（重要）

下次以 `.env` 配置的 **MySQL** 启动应用时，`run_startup_migrations()` 会自动应用以下两条新迁移（增量、安全）：

| 迁移版本 | 作用 |
|---------|------|
| `e3c0e63a65c4` | 建 5 张新表（listening_record / listening_domain / listening_image / listening_indicator_result / indicator_catalog）；`export_records` 增列 `listening_record_id`；`prompt_template.task_type` 枚举增加 `one_on_one_listening` |
| `9ec29bdc3822` | 种子：向 `indicator_catalog` 预置「小班·下学期」五大领域共 30 个二级指标（tenant_id=1），数据源 `alembic/seed_data/listening_indicators_xiaoban_xia.json` |

- 已在本地 sqlite 验证升级 / 降级 / 重升级均正常；MySQL 将于首次启动自动迁移。
- 当前 Alembic head：`9ec29bdc3822`。

## 本期改动文件清单

### 新增文件
| 类别 | 文件 |
|------|------|
| 模板 | `templates/OneOnOneListeningSmallSecond.docx`（小班下学期，5 领域表） |
| 种子 | `alembic/seed_data/listening_indicators_xiaoban_xia.json`（30 指标，每个 3 档标准） |
| 迁移 | `alembic/versions/e3c0e63a65c4_dev3_1_listening_tables_and_columns.py` |
| 迁移 | `alembic/versions/9ec29bdc3822_dev3_1_seed_indicator_catalog_xiaoban_.py` |
| 模型 | `app/core/models/{listening_record,listening_domain,listening_image,listening_indicator,indicator_catalog}.py` |
| 仓库 | `app/repository/{indicator_repository,listening_repository,listening_image_repository}.py` |
| AI | `app/integration/ai_client/listening_client.py` |
| 导出 | `app/integration/word_export/listening_exporter.py` |
| 服务 | `app/service/listening_service.py` |
| 页面 | `app/ui/pages/one_on_one_listening.py`（路由 `/one-on-one-listening`） |
| 文档 | `memory-bank/one-on-one-listening/{design,dev-plan,test-plan,progress}.md` |
| 测试 | `tests/test_listening_models.py`、`test_listening_migration.py`、`test_indicator_repository.py`、`test_listening_repository.py`、`test_listening_image_repository.py`、`test_listening_client.py`、`test_listening_service.py`、`test_listening_exporter.py`、`test_listening_ui_helpers.py` |

### 修改文件
| 文件 | 改动 |
|------|------|
| `app/core/models/__init__.py` | 注册 5 个新模型 |
| `app/core/models/prompt_template.py` | task_type 枚举增 `one_on_one_listening` |
| `app/core/models/export_record.py` | 增 `listening_record_id` 列 |
| `app/service/date_service.py` | 新增 `pick_three_workdays` |
| `app/ui/components/app_shell.py` | 「教学管理」菜单增「一对一倾听」 |
| `app/main.py` | 注册页面路由 |
| `tests/test_date_service.py` | 追加 `pick_three_workdays` 测试 |

## 各阶段功能与自动测试

| 阶段 | 功能要点 | 测试文件（数量） |
|------|---------|----------------|
| P1 | 5 表模型 + 迁移 + 种子 | test_listening_models(5)、test_listening_migration(5) |
| P2 | 仓库层（强制 tenant 隔离） | test_indicator_repository(5)、test_listening_repository(5)、test_listening_image_repository(3) |
| P3 | `pick_three_workdays`（前三周各一工作日、排节假日、降级） | test_date_service 追加(7) |
| P4 | AI 客户端（每领域 1 次视觉调用，结构化 JSON） | test_listening_client(6) |
| P5 | 服务层（生成 + 星级缺省补 3 星 + 持久化 + 审计） | test_listening_service(5) |
| P6 | Word 导出（合并 / 按领域拆分 / 批量按领域） | test_listening_exporter(14) |
| P7 | UI 页面纯函数 | test_listening_ui_helpers(5) |

## 运行与测试命令

```bash
# 启动应用（默认 .env 的 MySQL；首次启动自动应用 dev3.1 迁移）
.venv/bin/python -m app.main

# 全量自动化测试
.venv/bin/python -m pytest tests/ -q

# 仅本子系统测试
.venv/bin/python -m pytest tests/test_listening_*.py tests/test_indicator_repository.py -q

# 本地 sqlite 验证迁移（不触碰 MySQL）
env DATABASE_URL="sqlite+aiosqlite:////tmp/x.db" .venv/bin/alembic upgrade head
```

## 🧑 待手动测试清单（P7 里程碑）

**前置条件**：在「设置」页配置一个**视觉模型 API Key**（生成功能依赖；未配置会提示「尚未配置视觉模型 API Key」）。

1. 左侧菜单「教学管理 → 一对一倾听」可进入页面（路由 `/one-on-one-listening`）。
2. 基本信息：年/月（默认当前年月）、幼儿姓名、成人数目（默认 1）、年级·学期下拉（默认「小班·下学期」）、幼儿年龄（随年级联动：小 4/中 5/大 6 岁）、观察者。
3. 「自动选取工作日」→ 各领域 3 个日期填入当月前三周各一个工作日（排除法定节假日），可手动改。
4. 展开某领域 → 上传 1~3 张幼儿绘画 → 「生成X领域」→ 回填**目标 / 3 图描述 / 各二级指标星级 / 综合评价 / 支持策略**，均可编辑、可改星级（未涉及默认三星）。
5. 「保存」→ 提示成功（含记录 ID）；数据（含图片）入库。
6. 「导出合并 Word」→ 1 个 docx，5 领域表齐全；核对：观察日期(年月)/姓名/成人数/年龄/目标、3 个绘画日期、图片、图片描述、**指标打勾 √ 在正确星级行**、综合评价、支持策略、中文不乱码。
7. 「导出按领域(zip)」→ 解压得 5 个 docx，每个仅一个领域。

**反馈关注点**：交互顺畅度、AI 回填正确性、导出 Word 是否符合模板预期、星级打勾位置是否正确。

## 已知备注

- 单用户模式下 `get_current_user` 返回固定上下文（tenant_id=1, user_id=1），页面不依赖登录。
- 在**全新 sqlite** 启动时 bootstrap 默认管理员创建会报 `user.id NOT NULL`（预存问题，非本期引入；MySQL 正常，单用户模式不受影响）。
- 五大领域顺序：模板为 健康/语言/社会/科学/艺术；导出按领域时领域名为键，顺序可配置。
- 指标 `sort_order` 与模板行序严格一致（种子提取脚本已保证），导出打勾依此定位。

## 下一步（手动测试通过后）

- **P8**：历史记录列表（年月/姓名筛选）+ 单条重新导出 + 多幼儿勾选「批量按领域导出（5 档 zip）」+ 导出记录写库。
- **P9**：更新 `memory-bank/architecture.md` 与 `progress.md`；全量回归。
