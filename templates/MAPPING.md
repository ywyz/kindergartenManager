# Word 模板字段映射

文件：`templates/teacherplan.docx`  
单张表格，共 **19 行**（Row 0–18），第 0 列为标签列，第 1 列为数据列（部分行为合并单元格）。

---

## Python 数据模型 → Word 单元格 映射表

| Row  | cells[*] | 模板标签内容          | Python 字段                                           | DB JSON 列                      | 红字 field_name               |
|------|----------|-----------------------|-------------------------------------------------------|---------------------------------|-------------------------------|
| 0    | 合并全行 | （空，显示周次）      | `plan.week_number`                                    | —（直接读计划字段）             | —                             |
| 1    | 合并全行 | （空，显示日期）      | `plan.plan_date`, `plan.day_of_week`                  | —                               | —                             |
| 2    | cells[1] | 集体 / 自（选）       | `ma.group_activity_name`, `ma.self_selected_name`     | `morning_activity_json`         | `morning_activity`            |
| 3    | cells[1] | 重点指导 / 活动目标 / 指导要点 | `ma.key_guidance`, `ma.activity_goal`, `ma.guidance_points` | `morning_activity_json` | `morning_activity`  |
| 4    | cells[1] | 谈话主题（带冒号）    | `mt.topic`                                            | `morning_talk_json`             | `morning_talk`                |
| 5    | cells[1] | 问题设计              | `mt.questions`                                        | `morning_talk_json`             | `morning_talk`                |
| 6    | cells[1] | 活动主题（带冒号）    | `ga.theme`                                            | `group_activity_json`           | `group_activity_theme`        |
| 7    | cells[1] | 活动目标              | `ga.goal`                                             | `group_activity_json`           | `group_activity_goal`         |
| 8    | cells[1] | 活动准备              | `ga.preparation`                                      | `group_activity_json`           | `group_activity_preparation`  |
| 9    | cells[1] | 活动重点（带冒号）    | `ga.key_point`                                        | `group_activity_json`           | `group_activity_key_point`    |
| 10   | cells[1] | 活动难点（带冒号）    | `ga.difficulty`                                       | `group_activity_json`           | `group_activity_difficulty`   |
| 11   | cells[1] | 活动过程（带冒号）    | `ga.process`                                          | `group_activity_json`           | `group_activity_process` ★    |
| 12   | cells[1] | 游戏区域（带冒号）    | `ia.game_area`                                        | `indoor_area_json`              | `indoor_area`                 |
| 13   | cells[1] | 重点指导 / 活动目标 / 指导要点 | `ia.key_guidance`, `ia.activity_goal`, `ia.guidance_points` | `indoor_area_json`  | `indoor_area`       |
| 14   | cells[1] | 支持策略              | `ia.support_strategy`                                 | `indoor_area_json`              | `indoor_area`                 |
| 15   | cells[1] | 游戏区域（带冒号）    | `og.game_area`                                        | `outdoor_game_json`             | `outdoor_game`                |
| 16   | cells[1] | 重点观察 / 活动目标 / 指导要点 | `og.key_guidance`, `og.activity_goal`, `og.guidance_points` | `outdoor_game_json` | `outdoor_game`      |
| 17   | cells[1] | 支持策略              | `og.support_strategy`                                 | `outdoor_game_json`             | `outdoor_game`                |
| 18   | cells[1] | （空，一日活动反思）  | `plan.daily_reflection`                               | —（直接读计划字段）             | —                             |

> ★ Row 11（活动过程）使用专用函数 `_fill_process_cell()`，按"环节"聚合 AI 标记决定红/黑，逐行生成独立 `<w:p>` 段落。

---

## 数据模型字段说明

### DailyPlan（`app/models/daily_plan.py`）

| 字段                    | 类型                  | 说明                                  |
|-------------------------|-----------------------|---------------------------------------|
| `id`                    | `int \| None`         | 数据库自增主键                        |
| `plan_date`             | `date \| None`        | 计划日期                              |
| `week_number`           | `int \| None`         | 第几周                                |
| `day_of_week`           | `str`                 | 星期几（中文，如"星期一"）            |
| `grade`                 | `str`                 | 年级（小班/中班/大班）                |
| `class_name`            | `str`                 | 班级（1班/2班/3班/4班）               |
| `semester_id`           | `int \| None`         | 学期 ID（FK）                         |
| `morning_activity`      | `MorningActivity`     | 晨间活动                              |
| `morning_talk`          | `MorningTalk`         | 晨间谈话                              |
| `group_activity`        | `GroupActivity`       | 集体活动（含教案拆分结果）            |
| `indoor_area`           | `AreaActivity`        | 室内区域活动                          |
| `outdoor_game`          | `AreaActivity`        | 户外游戏活动                          |
| `daily_reflection`      | `str`                 | 一日活动反思                          |
| `original_lesson_text`  | `str`                 | 原始教案文本（不导出到 Word）         |
| `ai_modified_parts`     | `dict`                | `{"fields": [...]}` AI 修改字段列表  |
| `status`                | `str`                 | `draft` / `completed`                 |

### MorningActivity

| 字段                   | 说明         |
|------------------------|--------------|
| `group_activity_name`  | 集体活动名称 |
| `self_selected_name`   | 自选活动名称 |
| `key_guidance`         | 重点指导     |
| `activity_goal`        | 活动目标     |
| `guidance_points`      | 指导要点     |

### MorningTalk

| 字段       | 说明     |
|------------|----------|
| `topic`    | 谈话主题 |
| `questions`| 问题设计 |

### GroupActivity

| 字段               | 说明                               |
|--------------------|------------------------------------|
| `theme`            | 活动主题                           |
| `goal`             | 活动目标                           |
| `preparation`      | 活动准备                           |
| `key_point`        | 活动重点                           |
| `difficulty`       | 活动难点                           |
| `process`          | 活动过程（导出版，可为 AI 修改版） |
| `process_original` | 活动过程原始版（仅存库，不导出）   |

### AreaActivity（室内区域 / 户外游戏共用）

| 字段               | 说明     |
|--------------------|----------|
| `game_area`        | 游戏区域 |
| `activity_goal`    | 活动目标 |
| `key_guidance`     | 重点指导（户外模板标签为"重点观察"）|
| `guidance_points`  | 指导要点 |
| `support_strategy` | 支持策略 |

---

## 红字规则（`ai_modified_parts.fields`）

| field_name                    | 影响的 Word 行      |
|-------------------------------|---------------------|
| `morning_activity`            | Row 2、3            |
| `morning_talk`                | Row 4、5            |
| `group_activity_theme`        | Row 6               |
| `group_activity_goal`         | Row 7               |
| `group_activity_preparation`  | Row 8               |
| `group_activity_key_point`    | Row 9               |
| `group_activity_difficulty`   | Row 10              |
| `group_activity_process`      | Row 11（按环节聚合）|
| `indoor_area`                 | Row 12、13、14      |
| `outdoor_game`                | Row 15、16、17      |

活动过程（Row 11）红字判定逻辑（`_compute_process_red_flags`）：
1. 优先以**强标题**（中文数字`一、`/`（一）`/`第N步|环节|部分|阶段|课时`）划分节
2. 无强标题时，退回**弱标题**（阿拉伯数字`1.`/`(1)`）划分节
3. 若某节内存在 `【AI修改】`/`[AI新增]`/`(AI补充)` 等标记，则整节所有行染红
4. 完全无标题时，仅含 AI 标记的行染红

---

## 导出文件命名规范

```
{年级}{班级}_{YYYY-MM-DD}_{第N周周X}.docx
示例：大班1班_2026-04-26_第12周星期日.docx
```

批量合并导出：`{author_name}备课笔记.docx`
