# 课程审议记录子系统 — 开发计划

> 配套：[design.md](design.md)、[test-plan.md](test-plan.md)、[progress.md](progress.md)。

## 阶段总览

| 阶段 | 内容 | 验证 | 状态 |
|------|------|------|------|
| P0 | 文档与模板分析 | 模板结构确认 | 完成 |
| P1 | 数据模型、迁移、仓库、导出记录关联 | 自动测试 | 完成 |
| P2 | AI 客户端与服务层 | 自动测试 | 完成 |
| P3 | Word 导出器 | 自动测试 | 完成 |
| P4 | NiceGUI 页面、菜单、首页入口、提示词 Tab | 自动测试 | 完成 |
| P5 | 用户手动测试 | 手动验收 | 完成 |
| P6 | 文档收尾与全量回归 | 全量 pytest | 完成 |

## P1 — 数据层

- 新增 `CourseReviewActivity` ORM 模型。
- 新增 `course_review_activity_repository.py`。
- Alembic 创建 `course_review_activity` 表。
- `prompt_task_type` 扩展 `course_review_activity`。
- `export_records` 增加 `course_review_activity_id`。

## P2 — AI 与服务

- 新增 `course_review_activity_client.py`，严格解析课程审议 JSON。
- 新增 `course_review_activity_service.py`，读取 text AI Key、激活提示词并写审计日志。

## P3 — Word 导出

- 新增 `course_review_activity_exporter.py`。
- 填充模板第一张空白表，删除后方示例内容。
- 模板缺失时降级生成简化文档。

## P4 — UI 与导航

- 新增 `/course-review-activity` 页面。
- 左侧菜单与首页增加入口。
- 提示词管理增加「课程审议」Tab。

## P5 — 手动测试结果

用户反馈：测试通过。

已覆盖主流程：
1. 设置读取。
2. AI 生成。
3. 编辑保存。
4. 导出 Word。
5. 历史重新导出与删除。
