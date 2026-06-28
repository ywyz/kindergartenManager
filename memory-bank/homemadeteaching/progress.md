# 自制教玩具子系统 — 开发与测试进度

> 配套：[design.md](design.md)、[dev-plan.md](dev-plan.md)、[test-plan.md](test-plan.md)。

## 当前状态

- 2026-06-28：已完成项目与 `memory-bank` 阅读，确认现有三套子系统模式。
- 模板确认：`templates/homemadeteaching.docx` 为标题 + 5 行 2 列表格：
  班级、姓名、教玩具名称、所用材料、玩法。
- 开发策略：按 P1~P6 分阶段推进，小功能自动测试，页面主流程完成后交给用户手动测试。
- 当前代码状态：P1~P5 已实现并通过相关自动测试；等待用户手动验收页面主流程。

## 阶段进度

| 阶段 | 内容 | 状态 | 测试 |
|------|------|------|------|
| P0 | 文档与模板分析 | 完成 | 模板结构已读取 |
| P1 | 教师姓名设置项 | 完成 | `tests/test_class_repository.py` 3 passed |
| P2 | 数据模型与仓库 | 完成 | `tests/test_homemade_teaching_repository.py` 4 passed |
| P3 | AI 客户端与服务 | 完成 | `tests/test_homemade_teaching_client.py` 7 passed；`tests/test_homemade_teaching_service.py` 3 passed |
| P4 | Word 导出 | 完成 | `tests/test_homemade_teaching_exporter.py` 4 passed；`tests/test_export_repository.py` 8 passed |
| P5 | UI 页面与导航 | 完成，待手动验收 | `tests/test_homemade_teaching_ui_helpers.py` 5 passed；`tests/test_app_shell_menu.py` 9 passed |
| P6 | 文档收尾与全量回归 | 完成 | 全量 `pytest tests/ -q`：497 passed |

## 自动测试记录

| 时间 | 范围 | 结果 |
|------|------|------|
| 2026-06-28 | P1 教师姓名设置项 | `tests/test_class_repository.py`：3 passed |
| 2026-06-28 | P1+P2 设置项与仓库 | `tests/test_class_repository.py tests/test_homemade_teaching_repository.py`：7 passed |
| 2026-06-28 | P1~P3 + 模型冒烟 | 相关测试：28 passed |
| 2026-06-28 | P4 Word 导出与导出记录 | `tests/test_homemade_teaching_exporter.py tests/test_export_repository.py`：12 passed |
| 2026-06-28 | P1~P5 相关回归 + 迁移 | 相关测试：54 passed；临时 SQLite `alembic upgrade head` 通过 |
| 2026-06-28 | 全量回归 | `pytest tests/ -q`：497 passed |

## 手动测试等待项

需要用户手动测试：
1. 设置页填写「教师姓名」并保存，刷新后可回填。
2. 左侧菜单进入「自制教玩具」。
3. 页面显示当前年级、班级、教师姓名；缺失时有提示。
4. 点击「AI 生成」后回填教玩具名称、所用材料、玩法，且三项可编辑。
5. 点击「保存」后历史区出现记录。
6. 点击「导出 Word」后打开文件核对：班级、姓名、教玩具名称、所用材料、玩法写入正确单元格。
7. 历史记录可「重新导出」与「删除」。
