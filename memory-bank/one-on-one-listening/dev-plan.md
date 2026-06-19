# 一对一倾听观察子系统 — 开发计划

> 配套：[design.md](design.md)（需求与技术设计）、[test-plan.md](test-plan.md)（测试计划）。
> 分支：`dev3.1`（从 `dev3.0` 切出）。
> 工作方式：**小任务完成即自动测试（pytest）；大目标（带 🧑）完成后停下，由用户手动测试并反馈，通过后再继续。**

## 阶段总览

| 阶段 | 内容 | 验证 | 状态 |
|------|------|------|------|
| P0 | 分支 + 模板分析 + 设计文档 | ✅ 迁移 smoke、模型导入 | ✅ 完成 |
| P1 | 数据模型 + Alembic 迁移 + 指标种子 | ✅ 迁移 smoke、模型导入 | ✅ 完成 |
| P2 | 仓库层（指标目录 + 倾听记录/领域/图片/指标结果） | ✅ 仓库单测 | ✅ 完成 |
| P3 | 工作日选取 `pick_three_workdays` | ✅ 纯函数单测 | ✅ 完成 |
| P4 | AI 客户端 `listening_client` + 提示词 task_type | ✅ mock 单测 | ✅ 完成 |
| P5 | 服务层 `listening_service`（生成 + 持久化） | ✅ mock 单测 | ✅ 完成 |
| P6 | Word 导出 `listening_exporter`（三模式） | ✅ 导出单测 | ✅ 完成 |
| P7 | UI 页面 + 菜单 + 路由 | 🧑 手动测试 | ✅ 已实现，⏸ 待手动测试 |
| P8 | 导出 UI（三模式 + zip）+ 历史多选 | 🧑 手动测试 | ⬜ 未开始 |
| P9 | 文档收尾 + 全量回归 | ✅ `pytest tests/ -v` | ⬜ 未开始 |

> 详细文件清单与手动测试清单见 [progress.md](progress.md)。

---

## P0 — 分支 + 模板分析 + 设计文档 ✅（已完成）

- [x] 从 `dev3.0` 切出 `dev3.1`。
- [x] 用 python-docx 解析 `templates/OneOnOneListeningSmallSecond.docx`，确认 5 表结构、行列映射、星级/指标/综合评价定位。
- [x] 提取小班下学期五大领域指标目录 → `alembic/seed_data/listening_indicators_xiaoban_xia.json`（30 个二级指标，每个 3 档标准，校验通过）。
- [x] 撰写 `design.md` / `dev-plan.md` / `test-plan.md`。

---

## P1 — 数据模型 + 迁移 + 种子 ✅自动测试

**新建模型**（`app/core/models/`）：
- `listening_record.py` — `ListeningRecord`（design §4.1）
- `listening_domain.py` — `ListeningDomain`（design §4.2）
- `listening_image.py` — `ListeningImage`（design §4.3，BLOB 复用 game_observation_image 写法）
- `listening_indicator.py` — `ListeningIndicatorResult`（design §4.4）
- `indicator_catalog.py` — `IndicatorCatalog`（design §4.5）

**模型改动**：
- `prompt_template.py` — Enum 增加 `one_on_one_listening`
- `export_record.py` — 增加 `listening_record_id`

**迁移**（确保模型已在 `Base.metadata` 注册，即被某处 import）：
1. schema 迁移：`alembic revision --autogenerate -m "dev3.1 listening tables"` → 人工校验生成的 5 表 + 2 增列；补充索引。
2. 数据迁移：新建迁移读取 `alembic/seed_data/listening_indicators_xiaoban_xia.json`，`op.bulk_insert` 到 `indicator_catalog`（tenant_id=1，term=下学期，grade=小班）。
   - 路径以迁移文件相对定位（`Path(__file__).resolve().parents[1] / "seed_data" / ...`）。

**验证**：
- `alembic upgrade head` 成功；`alembic current` 为新 head。
- `tests/test_migrations_smoke.py` 模式：升级到 head 后断言 5 表存在、指标行数 = 30。
- 模型可被 import（`python -c "import app.core.models.listening_record ..."`）。

---

## P2 — 仓库层 ✅自动测试

**新建**（`app/repository/`）：
- `indicator_repository.py` — `list_indicators(session, tenant_id, grade, term, domain) -> list`（按 sort_order 升序）；`list_all_domains(...)`。
- `listening_repository.py` — `save_record` / `get_record_by_id` / `list_records`（分页 + 年月/姓名筛选）/ `update_record` / `delete_record`；`save_domain` / `list_domains_by_record` / `update_domain`；`save_indicator_result` / `list_indicator_results` / `bulk_upsert_indicator_results`。
- `listening_image_repository.py` — `add_image` / `list_images_by_record(domain 可选)` / `get_image` / `delete_images_by_record`（复用 observation_image_repository 写法）。

**约束**：所有查询强制 `tenant_id` 过滤；删除强制 `tenant_id + user_id`。

**验证**：`tests/test_listening_repository.py`、`test_indicator_repository.py`、`test_listening_image_repository.py`（aiosqlite 内存库 fixture）。

---

## P3 — 工作日选取 ✅自动测试

**改动** `app/service/date_service.py`：新增 `pick_three_workdays(year, month, is_holiday=None) -> list[date]`（design §7）。

**验证**：`tests/test_date_service.py` 追加用例：
- 正常月份返回 3 个工作日，分属前三周。
- 含周末/法定节假日时跳过（注入桩 `is_holiday`）。
- `is_holiday` 返回 `None`（API 不可用）时不阻断。
- 月初即周末、跨周边界等边界。

---

## P4 — AI 客户端 + 提示词 ✅自动测试

**新建** `app/integration/ai_client/listening_client.py`：
- `DEFAULT_LISTENING_PROMPT`（内置默认提示词，含图片文字识别 + 指标星级 + 200 字评价/策略约束）。
- `generate_listening_domain(images, context, indicators, api_base_url, api_key, model_name, system_prompt=None, *, _client=None) -> dict`。
- 复用 `vision_base.call_ai_vision`；校验 `goals/image_descriptions/indicators/evaluation/support_strategy` 必填；数量/覆盖校验；缺失抛 `AiParseError`。

**改动**：`prompt_template` Enum 增值已在 P1；提示词管理页 P7 接入 Tab。

**验证**：`tests/test_listening_client.py`（mock `call_ai_vision`）：
- 正常返回解析。
- 缺字段 / image_descriptions 数量不符 / indicators 未覆盖 → `AiParseError` 或服务层默认补全（在 P5 测）。
- 空图片列表 → `AppError`。

---

## P5 — 服务层 ✅自动测试

**新建** `app/service/listening_service.py`：
- `generate_domain_content(session, tenant_id, user_id, domain, images, context, *, _ai_client=None) -> dict`：
  取视觉 Key → 查 `one_on_one_listening` 提示词 → 查该领域指标目录 → 压缩图片 → 调 `generate_listening_domain` → 缺失指标星级降级默认 3 星 → 审计 `ai_listening` → 返回（含 compressed_images）。
- `save_record_with_all(session, record_data, domains_data, storage) -> int`：
  事务写 `listening_record` + 5×`listening_domain` + 15×`listening_image`（逐图存储）+ 指标结果。

**验证**：`tests/test_listening_service.py`（mock AI + 内存库）：生成流程、默认 3 星补全、未配置视觉 Key 抛 `ConfigError`、保存后各表行数正确。

---

## P6 — Word 导出 ✅自动测试

**新建** `app/integration/word_export/listening_exporter.py`（design §8）：
- `_fill_domain_table(table, domain_data, images, indicators)` — 填一个领域表（元数据/日期/图片/描述/指标打勾/评价/策略）。
- `export_combined(record, domains, images_by_domain, indicators_by_domain) -> bytes` — 单幼儿 1 档。
- `export_split_by_domain(...) -> dict[str, bytes]` — 单幼儿 5 档。
- `export_batch_by_domain(records_payload, domain_order=None) -> dict[str, bytes]` — 多幼儿按领域 5 档（deepcopy 表追加）。
- 复用 `_set_font`/`_clear_cell`/`_write_cell`/`_add_images_to_cell`；模板缺失降级。

**验证**：`tests/test_listening_exporter.py`：
- 生成的 docx 可被 python-docx 重新打开。
- 元数据/日期/目标/评价/策略写入正确单元格。
- 指标 `√` 落在正确星级行的 C5。
- 图片插入数量正确。
- 拆分模式返回 5 个领域、批量模式每档含正确幼儿数。

---

## P7 — UI 页面 + 菜单 + 路由 🧑手动测试

**新建** `app/ui/pages/one_on_one_listening.py`（路由 `/one-on-one-listening`）：
- 基本信息：观察年月（默认本月）、幼儿姓名、成人数目（默认 1）、年级+学期下拉（默认回填 class_config/semester_config）、幼儿年龄（按年级推断）、观察者。
- 5 领域分区（Tab 或折叠）：每领域「自动选取 3 工作日」按钮 + 3 个可编辑日期 + 3 张图片上传/预览 + 「生成本领域」按钮 + 目标/3 图描述/指标星级（下拉或星级控件，可改）/综合评价/支持策略（均可编辑）。
- 「保存」按钮 → `save_record_with_all`。
- 纯函数（单测）：`build_export_filename`、`infer_age_by_grade`、`validate_image_count` 等。

**改动**：
- `app/main.py` 顶部 `from app.ui.pages import one_on_one_listening`。
- `app/ui/components/app_shell.py` `_ALL_MENU_ITEMS` 增「一对一倾听」。
- `app/ui/pages/prompt_mgmt.py` 增 `one_on_one_listening` Tab。

**验证**：纯函数单测 + 🧑 手动：填写一个幼儿、5 领域上传生成、保存，确认页面交互与回填正确。

---

## P8 — 导出 UI + 历史 🧑手动测试

- 详情页/历史区：单条记录「导出（合并）」「导出（按领域 zip）」。
- 历史列表：年月/姓名筛选 + 多选幼儿 →「批量按领域导出（zip）」。
- zip 打包辅助（`io.BytesIO` + `zipfile`）；`ui.download` 下发；写 `export_records`（listening_record_id）。
- 审计 `export_listening`。

**验证**：🧑 手动：三种导出下载并用 Word 打开核对（中文、打勾、图片、布局）。

---

## P9 — 文档收尾 + 回归 ✅自动测试

- 更新 `memory-bank/architecture.md`（新表清单、模块清单、子系统说明）与 `memory-bank/progress.md`。
- 更新本目录 `progress.md`（如建）记录各阶段完成情况。
- 全量回归 `pytest tests/ -v`，确保 0 失败。

---

## 复用清单（直接参照游戏观察同名实现）

| 复用项 | 位置 |
|--------|------|
| 视觉调用 | `app/integration/ai_client/vision_base.py::call_ai_vision` |
| 视觉 Key | `app/repository/ai_key_repository.py::get_active_ai_key(key_type='vision')` |
| 图片压缩 | `app/integration/image_processing.py::compress_image` |
| 图片存储 | `app/integration/image_storage/blob_backend.py::BlobImageStorage` |
| Word 辅助 | `app/integration/word_export/observation_exporter.py`（`_set_font` 等） |
| 提示词 | `app/repository/prompt_repository.py::get_active_prompt` |
| 班级/学期 | `app/repository/class_repository.py`、`semester_repository.py` |
| 用户上下文 | `app/core/user_context.py::get_current_user` |
| 布局 | `app/ui/components/app_shell.py::render_shell` |
| 审计 | `app/core/audit.py::log_audit` |
| 导出记录 | `app/repository/export_repository.py::save_export_record` |

## 风险与注意

1. python-docx 复制表格用 `copy.deepcopy(table._tbl)` 后 `body.append`，需同时复制前置标题段落；deepcopy 后图片关系需重新 `add_picture`（不要 deepcopy 含图片的表，批量导出按「每幼儿现填」而非复制已填表）。
2. 元数据/绘画表头/末两行单元格含示例文本，写入前必须清空。
3. Alembic autogenerate 对 Enum 变更（MySQL）需人工核对 ALTER；SQLite 下 Enum 即 VARCHAR 无影响。
4. 指标 `sort_order` 必须与模板行序严格一致，否则打勾错位——已由种子提取脚本保证。
5. 每领域 1 次视觉调用，5 领域串行可能较慢；UI 需进度提示、允许逐领域生成。
