# 一对一倾听观察子系统 — 进度记录

> 配套：[design.md](design.md)、[dev-plan.md](dev-plan.md)、[test-plan.md](test-plan.md)。
> 分支：`dev3.1`（从 `dev3.0` 切出）。本文件随分支同步，便于跨电脑续作与测试。

---

## ⏸ 交接状态（2026-06-20，等待跨电脑手动验收）

> **下次续作：用户将切换电脑测试。阅读本文档后，用户的第一件事是反馈手动测试结果。**
> AI 助手：收到反馈后再决定是否迭代修复，不要在反馈前重复实现已完成的 P8/P8d/P9。

- **代码状态**：P0~P9 + P8d（体验增强 5 项）全部已实现并自测通过；**全量 461 passed**；尚未人工实机验收。
- **切换电脑后启动前置**：
  1. 拉取 `dev3.1` 分支最新提交。
  2. 以 `.env`（MySQL）启动应用 `.venv/bin/python -m app.main`：`run_startup_migrations()` 会自动应用 dev3.1 两条迁移（`e3c0e63a65c4` 建表/增列/枚举、`9ec29bdc3822` 种子 30 指标），增量且安全；当前 Alembic head 应为 `9ec29bdc3822`。
  3. **生成功能前置**：在「设置」页配置一个**视觉模型 API Key**（`key_type=vision`），否则点生成会提示「尚未配置视觉模型 API Key」。
- **验收清单**：见本文件下方「🧑 待手动验收清单（P7/P8 全功能）」。
- **反馈后**：如有问题，按反馈逐项修复并补测；全部通过后可考虑合并分支。

---

## 当前状态（2026-06-20）

- **已完成并自动测试通过：P0 ~ P9 + P8d（体验增强 5 项）**
- P7 手动测试已反馈通过；P8（历史/导出/编辑 UI）、P8d（体验增强）、P9（文档收尾 + 全量回归）均已实现并自测。
- 自动化测试：一对一倾听相关测试 107 passed；**全量 461 passed**（较基线 444 新增 17）。
- 应用本地 sqlite 启动冒烟通过：`NiceGUI ready`；路由 `/one-on-one-listening`、`/prompts`、`/game-observation` 均返回 `HTTP 200`。
- 待用户**手动验收**：一键导入 15 张 / 各领域独立年月与工作日 / 生成全部领域 / 历史详情·编辑·删除 / 三种导出 Word 核对（中文、打勾、横版图片、日期、评价策略）/ 提示词页倾听 Tab。

### P8 / P8d / P9 本期新增能力
- **P8a 后端**：`export_repository.save_export_record(listening_record_id=...)`；`listening_repository.delete_domains_by_record`；`indicator_repository.list_indicators_by_ids`；`listening_service.load_record_detail` / `to_export_payload`（纯函数）/ `update_record_with_all`（覆盖保存，与 `save_record_with_all` 共用 `_persist_domains`）。
- **P8b 历史 UI**：年月/姓名筛选、只读详情弹窗、单条「导出合并」「导出按领域(zip)」、多选「批量按领域导出(zip)」、删除（含图片+确认弹窗）；写 `export_records(listening_record_id)` + 审计 `export_listening`；表单内既有导出同步补审计与关联。
- **P8c 编辑**：历史「编辑」载入记录到表单（含 DB blob 重建 `CompressedImage`）→ 覆盖保存；顶部「编辑中」横幅 +「取消编辑/新建」。
- **P8d 体验增强**：① 领域时间方案 C（每领域独立年月 + 各自「自动选取本领域工作日」+ 顶部「一键为所有领域按各自年月选取」）；② 提示词页新增 `one_on_one_listening` Tab；③ 五领域改 Tab 布局；④ 图片统一横版 `normalize_to_landscape`（上传即归一）；⑤ 一键导入 15 张按文件名分配五领域 +「生成全部领域」串行。

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
| `app/repository/export_repository.py` | `save_export_record` 增 `listening_record_id` 参数（P8a） |
| `app/repository/indicator_repository.py` | 新增 `list_indicators_by_ids`（P8a） |
| `app/repository/listening_repository.py` | 新增 `delete_domains_by_record`（P8a） |
| `app/integration/image_processing.py` | 新增 `normalize_to_landscape`（P8d#4 横版统一） |
| `app/service/listening_service.py` | 新增 `load_record_detail` / `to_export_payload` / `update_record_with_all` + 抽 `_persist_domains`（P8a/P8c） |
| `app/ui/pages/one_on_one_listening.py` | Tab 布局、每领域/一键自动选工作日、一键导入 15 张、生成全部领域、历史区、详情、编辑覆盖、删除、批量导出、审计（P8b/P8c/P8d） |
| `app/ui/pages/prompt_mgmt.py` | 新增 `one_on_one_listening` 提示词 Tab（P8d#2） |
| `tests/test_export_repository.py` / `test_indicator_repository.py` / `test_listening_repository.py` / `test_listening_service.py` / `test_image_processing.py` / `test_listening_ui_helpers.py` | 追加 P8a/P8d 用例 |

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
| P8a | 导出记录关联 + 详情装配 + 导出转换 + 覆盖保存 | test_export_repository(+2)、test_indicator_repository(+1)、test_listening_repository(+1)、test_listening_service(+4) |
| P8d#4 | 图片横版统一 `normalize_to_landscape` | test_image_processing(+4) |
| P8b/P8d#5 | 历史/批量/导入纯函数（分配/zip/批量文件名/摘要） | test_listening_ui_helpers(+5) |
| P8b/P8c/P8d#1/#2/#3/#5 | 历史区·详情·编辑·删除·批量导出 / Tab 布局 / 领域时间 / 提示词 Tab / 一键导入 | 🧑 手动验收 |

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

## 🧑 待手动验收清单（P7/P8 全功能）

**前置条件**：在「设置」页配置一个**视觉模型 API Key**（生成功能依赖；未配置会提示「尚未配置视觉模型 API Key」）。

1. 左侧菜单「教学管理 → 一对一倾听」可进入页面（路由 `/one-on-one-listening`）。
2. 基本信息：年/月、幼儿姓名、成人数目、年级·学期下拉（默认「小班·下学期」）、幼儿年龄随年级联动、观察者。
3. **五领域为 Tab**：点一个标签显示一个领域。
4. **一键导入 15 张照片**：选 15 张 → 「分配到五领域」→ 每领域 3 张、统一横版、预览正确；非 15 张报错。
5. **领域时间独立**：可分别设健康 3 月、语言 4 月；「自动选取本领域工作日」按该领域年月填 3 个工作日；顶部「一键为所有领域按各自年月选取」对各领域按其自身年月填。
6. 上传/导入后「生成X领域」或「生成全部领域」→ 回填目标/3 图描述/各指标星级/综合评价/支持策略，均可编辑、可改星级（未涉及默认三星）。
7. 「保存」成功（含记录 ID）；数据（含图片）入库；历史区出现该记录。
8. **历史区**：年月/姓名筛选；「详情」只读弹窗（各领域内容 + 横版图片）；「编辑」载入表单修改后「覆盖保存」；「删除」确认后移除（含图片）。
9. **导出**：单条「导出合并」(1 docx) / 「按领域 zip」(5 docx)；勾选多名幼儿「批量按领域导出(zip)」(5 档，每档含所选幼儿)。Word 核对：观察日期(年月)/姓名/成人数/年龄/目标、3 绘画日期、**横版图片**、图片描述、**指标打勾 √ 在正确星级行**、综合评价、支持策略、中文不乱码。
10. 提示词页新增「一对一倾听」Tab，可保存版本与回滚。

**反馈关注点**：横版统一效果、一键导入分配正确性、各领域独立年月与工作日、AI 回填正确性、导出 Word 模板保真与打勾位置、编辑覆盖是否正确。

## 已知备注

- 单用户模式下 `get_current_user` 返回固定上下文（tenant_id=1, user_id=1），页面不依赖登录。
- 在**全新 sqlite** 启动时 bootstrap 默认管理员创建会报 `user.id NOT NULL`（预存问题，非本期引入；MySQL 正常，单用户模式不受影响）。
- 五大领域顺序：模板为 健康/语言/社会/科学/艺术；导出按领域时领域名为键，顺序可配置。
- 指标 `sort_order` 与模板行序严格一致（种子提取脚本已保证），导出打勾依此定位。

## 下一步

- 子系统 P0~P9 + P8d 全部完成并自测通过（全量 461 passed）。
- 等待用户**手动验收**（见上方清单）；如有问题再迭代，否则可合并分支并准备下一子系统。
