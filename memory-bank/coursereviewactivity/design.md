# 课程审议记录子系统 — 设计文档

> 配套：[dev-plan.md](dev-plan.md)、[test-plan.md](test-plan.md)、[progress.md](progress.md)。

## 1. 目标与范围

教师填写活动名称、幼儿人数、活动时间并粘贴一篇原始教案；系统读取设置中的年龄段、班级名称、教师姓名，调用文本 AI 拆分并生成课程审议内容，保存为历史记录，并按 `templates/coursereviewactivity.docx` 导出 Word。

本期范围：
- 课程审议 AI 生成结构化 JSON。
- 保存历史记录，支持历史重新导出和删除。
- Word 导出严格填充模板第一张空白表，并移除模板示例内容。
- 接入提示词管理：`task_type=course_review_activity`。

## 2. 关键决策

| # | 主题 | 决策 |
|---|------|------|
| 1 | 班级（年龄段）单元格 | 只填写年龄段，如“小班”；班级名仅用于历史摘要与文件名。 |
| 2 | 教师字段 | 组织教师、记录人均使用设置中的 `teacher_name`。 |
| 3 | 活动形式 | 不新增输入项，保留模板默认“集体√、区域、亲子、小组、其他”。 |
| 4 | 二次修改 | AI 返回完整二次修改稿，导出到“二次修改”位置。 |
| 5 | AI 类型 | 使用文本模型配置（`ai_api_key.key_type='text'`）。 |
| 6 | 持久化 | 新表 `course_review_activity`，冗余保存设置快照。 |

## 3. Word 模板映射

模板：`templates/coursereviewactivity.docx`

使用第一张空白表，填充后删除后方示例表和示例教案。

| 行列 | 内容 |
|------|------|
| R0C1 | 活动名称 |
| R1C3 | 年龄段 |
| R1C5 | 幼儿人数 |
| R2C1 / R2C3 | 教师姓名 |
| R2C5 | 活动时间 |
| R4C1 | 活动目标原稿 |
| R5C1 | 活动准备原稿 |
| R6C1 | 活动过程记录原稿 |
| R4C4 / R5C4 | 根据是否调整写入 `√` 与调整内容 |
| R6C4 | 活动过程调整内容 |
| R7C1 | 课程审议后调整理由 |
| “附教案：原稿”后 | 用户粘贴的原始教案 |
| “二次修改”后 | AI 返回的完整修改稿 |

## 4. 数据模型

`course_review_activity`：
- 标准字段：`id / tenant_id / user_id / created_at / updated_at`。
- 设置快照：`grade / class_name / teacher_name`。
- 用户输入：`activity_name / child_count / activity_time / lesson_plan_original`。
- AI 结果：`activity_goal / activity_prep / activity_process`。
- 审议调整：`goal_adjusted / goal_adjustment / activity_goal_revised / prep_adjusted / prep_adjustment / activity_prep_revised / process_adjustment / activity_process_revised / review_reason / revised_lesson_plan`。
- 追踪字段：`ai_raw_json`。

`export_records` 新增 `course_review_activity_id` 逻辑关联字段。

## 5. AI 输出

AI 必须返回 JSON：

```json
{
  "activity_goal": "...",
  "activity_prep": "...",
  "activity_process": "...",
  "goal_adjusted": true,
  "goal_adjustment": "...",
  "activity_goal_revised": "...",
  "prep_adjusted": false,
  "prep_adjustment": "",
  "activity_prep_revised": "...",
  "process_adjustment": "...",
  "activity_process_revised": "...",
  "review_reason": "...",
  "revised_lesson_plan": "完整二次修改稿"
}
```

校验规则：
- `goal_adjusted`、`prep_adjusted` 必须是布尔值。
- 活动过程必须调整，`process_adjustment` 不得为空。
- 目标或准备标记调整时，对应 adjustment 不得为空。

## 6. 验收标准

1. 页面能读取当前年龄段、班级名称、教师姓名。
2. 填写活动名称、幼儿人数、活动时间、原始教案后可 AI 生成。
3. 生成结果可编辑并保存到历史记录。
4. 导出 Word 后字段落在正确单元格，示例内容不残留。
5. 历史记录可重新导出、可删除。
6. 提示词管理可维护课程审议提示词版本。
