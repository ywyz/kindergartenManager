# 一对一倾听观察子系统 — 测试计划

> 配套：[design.md](design.md)、[dev-plan.md](dev-plan.md)。
> 框架：`pytest` + `pytest-asyncio`；数据库用 `aiosqlite` 内存库 fixture（见 `tests/conftest.py`）；
> AI/图片/Word 用 mock/桩隔离。运行：`pytest tests/ -v`，单文件 `pytest tests/test_listening_*.py -v`。
> 原则：每个 service/repository 函数必有单测；每完成一小任务即运行对应测试。

## 测试文件总览

| 文件 | 覆盖阶段 | 主要对象 |
|------|---------|---------|
| `tests/test_migrations_smoke.py`（追加） | P1 | 迁移升级 + 指标种子行数 |
| `tests/test_indicator_repository.py` | P2 | 指标目录查询 |
| `tests/test_listening_repository.py` | P2 | 记录/领域/指标结果仓库 |
| `tests/test_listening_image_repository.py` | P2 | 图片仓库 |
| `tests/test_date_service.py`（追加） | P3 | `pick_three_workdays` |
| `tests/test_listening_client.py` | P4 | AI 客户端 |
| `tests/test_listening_service.py` | P5 | 服务层 |
| `tests/test_listening_exporter.py` | P6 | Word 导出 |
| `tests/test_listening_ui_helpers.py` | P7 | UI 纯函数 |

---

## P1 — 迁移与种子

**`test_migrations_smoke.py`（追加 / 复用既有模式）**
- `test_upgrade_head_creates_listening_tables`：升级到 head 后，`listening_record`、`listening_domain`、`listening_image`、`listening_indicator_result`、`indicator_catalog` 五表存在（查 sqlite_master / inspector）。
- `test_indicator_seed_count`：`indicator_catalog` 行数 = 30；按领域计数 健康7/语言6/社会7/科学6/艺术4。
- `test_indicator_seed_integrity`：随机抽样若干行，`standard_star1/2/3` 均非空、`sort_order` 在领域内连续从 0 起、`max_stars=3`。
- `test_export_records_has_listening_col`：`export_records` 含 `listening_record_id` 列。

## P2 — 仓库层

**`test_indicator_repository.py`**
- `list_indicators(grade='小班', term='下学期', domain='健康')` 返回 7 条且按 `sort_order` 升序。
- 跨租户隔离：tenant_id 不匹配返回空。
- 不存在的领域返回空列表。

**`test_listening_repository.py`**
- `save_record` 返回带 id 对象，字段持久化正确。
- `get_record_by_id` 强制 tenant_id（错误租户返回 None）。
- `list_records` 分页 + 年月/姓名筛选 + 按创建时间倒序。
- `save_domain` / `list_domains_by_record` 返回 5 领域。
- `save_indicator_result` / `bulk_upsert_indicator_results`：重复 upsert 不产生重复行、stars 更新生效。
- `update_record` / `delete_record` 强制 tenant_id+user_id，返回布尔。

**`test_listening_image_repository.py`**
- `add_image` 持久化 blob + domain + image_index + image_description。
- `list_images_by_record(domain=...)` 仅返回该领域、按 image_index 升序。
- `get_image` / `delete_images_by_record` tenant 隔离。

## P3 — 工作日选取

**`test_date_service.py`（追加 `TestPickThreeWorkdays`）**
- `test_returns_three_workdays`：普通月份返回 3 个 `date`，均为周一~周五。
- `test_three_distinct_weeks`：3 个日期分属当月前三个自然周。
- `test_skip_weekend`：月初为周末时跳到首个工作日。
- `test_skip_holiday`：注入 `is_holiday` 桩（某工作日为节假日）→ 该日被跳过取下一个。
- `test_holiday_api_unavailable`：`is_holiday` 返回 `None` → 不阻断，正常取日。
- `test_insufficient_workdays`：构造极端情形返回 < 3 个时不抛异常、返回已找到的。

## P4 — AI 客户端

**`test_listening_client.py`（mock `call_ai_vision`）**
- `test_generate_ok`：mock 返回完整 JSON → 解析出 goals/image_descriptions(3)/indicators/evaluation/support_strategy。
- `test_missing_field_raises`：缺 `evaluation` → `AiParseError`。
- `test_image_descriptions_count_mismatch`：描述数 ≠ 图片数 → `AiParseError`。
- `test_empty_images_raises`：空图片列表 → `AppError`。
- `test_system_prompt_priority`：传入 `system_prompt` 时使用之（断言 messages[0] 内容）。
- `test_indicators_partial`：AI 只返回部分指标星级 → 客户端原样返回（由服务层补默认，见 P5）。

## P5 — 服务层

**`test_listening_service.py`（mock AI client + 内存库）**
- `test_generate_domain_ok`：注入 mock `_ai_client` → 返回含 compressed_images 与五段内容。
- `test_default_three_stars`：AI 未覆盖某些指标 → 结果中该指标 stars=3。
- `test_no_vision_key_raises`：未配置视觉 Key → `ConfigError`。
- `test_prompt_from_db`：DB 有激活 `one_on_one_listening` 提示词 → 被传入 AI。
- `test_save_record_with_all`：保存后 `listening_record` 1 条、`listening_domain` 5 条、`listening_image` = 实际上传数、`listening_indicator_result` = 各领域指标数之和。
- `test_audit_logged`：生成时记录 `ai_listening` 审计（patch `log_audit`）。

## P6 — Word 导出

**`test_listening_exporter.py`（用真实模板；缺失则测降级）**
- `test_combined_reopen`：合并导出的 bytes 可被 `Document(BytesIO)` 重新打开，含 5 个表。
- `test_metadata_filled`：R0 元数据各行冒号后为期望值（年月/姓名/成人数/年龄/目标）。
- `test_dates_in_headers`：R1/R3/R5 表头月日为该领域 date_1/2/3。
- `test_indicator_check_mark`：给定某指标 stars=2 → 对应领域 `R8+3i+1`（★★ 行）C5 含 `√`，其它两档不含。
- `test_images_inserted`：R2/R4/R6 左格图片数量正确（统计 inline shapes 或 drawing 元素）。
- `test_eval_strategy_cells`：末两行 C1 含综合评价 / 支持策略文本。
- `test_split_by_domain_keys`：拆分返回 5 个领域键，每档可重新打开且只含 1 个领域表。
- `test_batch_by_domain`：传 2 个幼儿 → 每领域档含 2 份该领域表（断言表数量）。
- `test_chinese_font`：抽样 run 字体名为「宋体」且设置 `w:eastAsia`。
- `test_template_missing_fallback`：传不存在模板路径 → 走 `_build_from_scratch` 不抛异常。

## P7 — UI 纯函数

**`test_listening_ui_helpers.py`**
- `test_build_export_filename`：文件名格式符合约定（含租户/用户/幼儿/年月/领域）。
- `test_infer_age_by_grade`：小班→4岁、中班→5岁、大班→6岁。
- `test_validate_image_count`：1~3 合法、0 与 4 非法。
- `test_default_year_month`：默认取当前年月。

> 页面交互（上传、生成、保存、导出）由 🧑 手动测试覆盖（见 dev-plan P7/P8）。

## 手动测试清单（🧑 大目标验收）

### P7 验收
1. 进入 `/one-on-one-listening`，年级/学期默认回填，年龄随年级联动。
2. 「自动选取工作日」对每个领域生成 3 个前三周工作日，可手动改。
3. 每领域上传 3 张绘画并预览；点「生成本领域」→ 目标/3 图描述/指标星级/评价/策略回填且可编辑。
4. 未配置视觉模型时给出友好提示。
5. 「保存」成功，刷新后历史可见。

### P8 验收
6. 单幼儿「合并导出」→ 1 个 docx，5 领域表齐全、中文正常、图片/日期/目标/打勾/评价/策略就位。
7. 单幼儿「按领域导出」→ zip 含 5 个 docx，每个仅一个领域。
8. 历史多选 2+ 幼儿「批量按领域导出」→ zip 含 5 个 docx，每档含所选幼儿的该领域表。
9. 导出记录写入、可重新导出。

## 回归

- 每阶段结束运行该阶段测试文件；P9 运行 `pytest tests/ -v` 全量，确保 0 失败、无新增 warning（已知 Deprecation 除外）。
