# 课程审议记录子系统 — 测试计划

> 测试框架：`pytest` + `pytest-asyncio`。数据库测试使用 SQLite 内存库；AI 调用使用 `httpx.MockTransport` 或 mock。

## 测试文件

| 文件 | 覆盖对象 |
|------|----------|
| `tests/test_course_review_activity_repository.py` | 仓库 CRUD、排序、隔离 |
| `tests/test_course_review_activity_client.py` | AI JSON 解析与校验 |
| `tests/test_course_review_activity_service.py` | AI Key、提示词、审计 |
| `tests/test_course_review_activity_exporter.py` | Word 模板填充与示例移除 |
| `tests/test_course_review_activity_ui_helpers.py` | 文件名、设置摘要、表单校验 |
| `tests/test_export_repository.py` | 导出记录关联字段 |
| `tests/test_migrations_smoke.py` | ORM 与枚举冒烟 |
| `tests/test_app_shell_menu.py` | 菜单入口 |

## 场景

- 数据层：创建、查询、列表倒序、租户隔离、用户隔离、删除。
- AI：正常 JSON、多余字段忽略、缺字段报错、非布尔值报错、过程调整为空报错、自定义提示词。
- 服务层：未配置 AI Key 抛 `ConfigError`；激活提示词传入 AI；成功写审计。
- Word：导出文件可打开；只保留一张表；单元格映射正确；目标/准备勾选正确；原稿与二次修改写入；示例内容不残留；模板缺失降级可用。
- UI 纯函数：文件名清理、设置缺失提示、生成前与保存前表单校验。

## 回归命令

```bash
.venv/bin/pytest tests/ -q
```
