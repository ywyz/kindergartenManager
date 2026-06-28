# 自制教玩具子系统 — 测试计划

> 测试框架：`pytest` + `pytest-asyncio`。数据库测试使用 `tests/conftest.py`
> 的 SQLite 内存库 fixture；AI 与 Word 导出使用 mock 或真实模板隔离验证。

## 测试文件总览

| 文件 | 阶段 | 覆盖对象 |
|------|------|----------|
| `tests/test_class_repository.py` | P1 | `teacher_name` 保存与回填 |
| `tests/test_homemade_teaching_repository.py` | P2 | 自制教玩具仓库 CRUD |
| `tests/test_homemade_teaching_client.py` | P3 | AI JSON 客户端 |
| `tests/test_homemade_teaching_service.py` | P3/P4 | 生成服务、保存装配、导出服务 |
| `tests/test_homemade_teaching_exporter.py` | P4 | Word 模板导出 |
| `tests/test_homemade_teaching_ui_helpers.py` | P5 | UI 纯函数 |
| `tests/test_app_shell_menu.py` | P5 | 菜单项 |
| `tests/test_export_repository.py` | P4 | `homemade_teaching_id` 导出记录 |
| `tests/test_migrations_smoke.py` | P1/P2/P3/P4 | ORM/迁移冒烟 |

## P1 — 设置项

- `upsert_class_config` 新建记录时保存 `teacher_name`。
- `upsert_class_config` 更新记录时覆盖 `teacher_name`。
- `teacher_name` 可为空，兼容旧数据。
- `get_class_config` 回填最新教师姓名。

## P2 — 仓库层

- `create_homemade_teaching_toy` 保存全部字段。
- `get_homemade_teaching_toy` 强制 tenant 过滤。
- `list_homemade_teaching_toys` 强制 tenant + user 过滤，按最新在前。
- `delete_homemade_teaching_toy` 强制 tenant + user，删除成功返回 True。

## P3 — AI 与服务

AI 客户端：
- 正常 JSON 返回三字段。
- 多余字段被忽略。
- 缺 `toy_name/materials/play_methods` 任一字段抛 `AiParseError`。
- 字段为空字符串抛 `AiParseError`。
- 自定义 system prompt 被使用。

服务层：
- 未配置文本 AI Key 抛 `ConfigError`。
- 有激活 `homemade_teaching` 提示词时传入 AI。
- 生成结果包含 `ai_raw_json`。
- 生成成功记录 `ai_homemade_teaching` 审计。

## P4 — Word 导出

- 导出返回非空 bytes，可被 `python-docx` 重新打开。
- 模板表格保持 5 行。
- R0~R4 右侧单元格分别写入班级、姓名、教玩具名称、材料、玩法。
- 中文字体为宋体，设置 `w:eastAsia`。
- 模板缺失时降级文档可打开。
- `save_export_record(..., homemade_teaching_id=...)` 可持久化关联。

## P5 — UI 纯函数与手动测试

自动：
- `build_homemade_teaching_filename` 文件名含班级、教师、记录 ID。
- `validate_generation_context` 缺年级/班级/教师姓名时给出错误。
- `format_setting_summary` 输出设置摘要。
- 菜单包含 `homemade-teaching`。

手动：
1. 设置页填写教师姓名并保存，刷新后仍在。
2. 进入「自制教玩具」，能看到年级、班级、教师姓名。
3. 点击 AI 生成后，三个字段回填且可编辑。
4. 保存成功，历史列表出现记录。
5. 导出 Word，打开核对五个字段在正确单元格。
6. 历史记录可重新导出，可删除。

## 回归

每个小阶段运行对应测试文件；P6 运行：

```bash
.venv/bin/python -m pytest tests/ -q
```
