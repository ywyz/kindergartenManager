# 自制教玩具子系统 — 开发计划

> 配套：[design.md](design.md)、[test-plan.md](test-plan.md)、[progress.md](progress.md)。
>
> 工作方式：小功能先写自动测试，再实现并运行对应测试；页面主流程完成后停下等待用户手动测试反馈。

## 阶段总览

| 阶段 | 内容 | 验证 | 状态 |
|------|------|------|------|
| P0 | 文档与模板分析 | 文档齐备 | 完成 |
| P1 | 设置项：`teacher_name` + 迁移 + 仓库/UI 回填 | 自动测试 | 完成 |
| P2 | `homemade_teaching_toy` 模型与仓库 | 自动测试 | 完成 |
| P3 | AI JSON 客户端与服务层 | 自动测试 | 完成 |
| P4 | Word 导出与导出记录 | 自动测试 | 完成 |
| P5 | NiceGUI 页面、菜单、路由、提示词 Tab | 自动测试 + 手动测试 | 完成，待手动验收 |
| P6 | 文档收尾与全量回归 | 全量 pytest | 完成 |

## P1 — 教师姓名设置项

改动：
- `ClassConfig` 新增 `teacher_name`。
- Alembic 迁移为 `class_config` 增列。
- `upsert_class_config` 支持 `teacher_name`，保持旧调用兼容。
- `/settings` 班级配置区新增「教师姓名」输入框并保存/回填。

测试：
- `tests/test_class_repository.py`：保存、更新、回填教师姓名。
- `tests/test_migrations_smoke.py` 或模型冒烟测试追加字段可写入。

## P2 — 数据模型与仓库层

新增：
- `app/core/models/homemade_teaching.py`
- `app/repository/homemade_teaching_repository.py`
- Alembic 迁移创建 `homemade_teaching_toy`。

测试：
- 创建记录后可查询。
- 列表按 `created_at/id` 倒序。
- 跨租户/跨用户不可见。
- 删除强制 `tenant_id + user_id`。

## P3 — AI 客户端与服务层

新增：
- `app/integration/ai_client/homemade_teaching_client.py`
- `app/service/homemade_teaching_service.py`
- `prompt_template.task_type` 增加 `homemade_teaching`。

测试：
- AI 客户端正确解析 JSON。
- 缺字段/空字段抛 `AiParseError`。
- 服务层未配置 AI Key 抛 `ConfigError`。
- 服务层会读取 DB 激活提示词。
- 审计 `ai_homemade_teaching` 被调用。

## P4 — Word 导出

新增：
- `app/integration/word_export/homemade_teaching_exporter.py`
- `export_records` 增加 `homemade_teaching_id`。
- `save_export_record` 增加可选参数。

测试：
- 导出 bytes 可被 python-docx 打开。
- 5 行右侧单元格写入正确。
- 字体设置宋体与 `w:eastAsia`。
- 模板缺失时降级生成可打开文档。
- 导出记录可保存 `homemade_teaching_id`。

## P5 — UI 页面

新增页面 `/homemade-teaching`：
- 设置快照展示。
- AI 生成、编辑、保存、导出。
- 历史列表、重新导出、删除。

改动：
- `app/main.py` 注册页面。
- `app/ui/components/app_shell.py` 新增菜单项。
- `app/ui/pages/home.py` 新增快捷入口。
- `app/ui/pages/prompt_mgmt.py` 新增 `homemade_teaching` Tab。

自动测试：
- 纯函数：导出文件名、表单校验、设置快照摘要。
- 菜单测试覆盖新菜单项。

手动测试：
- 设置教师姓名。
- 生成、编辑、保存、导出、历史重新导出、删除。
- Word 模板核对。

## P6 — 文档与回归

- 更新 `memory-bank/architecture.md`、`overview.md`、`progress.md`。
- 运行全量 `pytest tests/ -q`。
- 给出用户手动验收清单与当前运行方式。
