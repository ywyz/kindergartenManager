# 自制教玩具子系统 — 设计文档

> 本文档记录「自制教玩具」子系统的需求与技术设计。配套文档：
> - 开发计划：[dev-plan.md](dev-plan.md)
> - 测试计划：[test-plan.md](test-plan.md)
> - 进度记录：[progress.md](progress.md)
>
> 阅读前置：[../overview.md](../overview.md)、[../architecture.md](../architecture.md)、
> [../tech-stack.md](../tech-stack.md)。

## 1. 目标与范围

教师根据当前系统设置中的年级、班级名称和教师姓名，调用文本 AI 生成一份自制教玩具建议：
「教玩具名称 / 所用材料 / 玩法」。系统将 AI 返回的 JSON 保存到数据库，并按
`templates/homemadeteaching.docx` 导出 Word 表格。

### 1.1 本期范围

- 设置页在「班级配置」中新增「教师姓名」。
- AI 依据年级和班级生成 1 条自制教玩具方案，返回结构化 JSON。
- 保存历史记录，支持历史查看、重新导出。
- Word 导出严格填充既有模板，不重排模板结构。
- 接入提示词管理：新增 `task_type=homemade_teaching`。

### 1.2 暂不做

- 多条方案一次生成、批量导出。
- 图片、视频或材料清单附件。
- 复杂审批流。

## 2. 关键决策

| # | 主题 | 决策 |
|---|------|------|
| 1 | 教师姓名来源 | 新增到 `class_config.teacher_name`，因为需求明确为「系统设置」中的填写项。 |
| 2 | 班级来源 | 读取 `class_config.grade` 和 `class_config.class_name`。 |
| 3 | AI 类型 | 使用文本模型配置（`ai_api_key.key_type='text'`）。 |
| 4 | AI 返回格式 | 严格 JSON：`toy_name`、`materials`、`play_methods` 三字段。 |
| 5 | 持久化 | 新表 `homemade_teaching_toy`，冗余保存 grade/class_name/teacher_name，保证历史导出不受后续设置变更影响。 |
| 6 | 导出模板 | 唯一模板 `templates/homemadeteaching.docx`。 |
| 7 | 历史行为 | 同一用户可保存多条自制教玩具记录，按创建时间倒序展示。 |

## 3. Word 模板字段映射

模板：`templates/homemadeteaching.docx`

结构：标题段落 + 1 个表格，表格 5 行 x 2 列。

| 行(0基) | 左列标题 | 右列写入 |
|---------|----------|----------|
| R0 | 班级 | `class_name` |
| R1 | 姓名 | `teacher_name` |
| R2 | 教玩具名称 | `toy_name` |
| R3 | 所用材料 | `materials` |
| R4 | 玩法 | `play_methods` |

写入规则：
- 写入前清空右侧单元格示例内容。
- 文字使用宋体并设置 `w:eastAsia`，避免中文乱码。
- 保留模板标题、表格样式、行高与边框。
- 模板缺失时降级生成简化 5 行 2 列表格，方便测试和应急导出。

## 4. 数据模型

所有业务表遵守项目约束：包含 `tenant_id / user_id / created_at / updated_at`，查询强制携带
`tenant_id`，schema 变更通过 Alembic。

### 4.1 `class_config` 增列

| 字段 | 类型 | 说明 |
|------|------|------|
| `teacher_name` | VARCHAR(64) NULL | 设置页填写的教师姓名，用于自制教玩具导出表。 |

### 4.2 新表 `homemade_teaching_toy`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 主键 |
| tenant_id / user_id | BIGINT | 租户与用户隔离 |
| grade | VARCHAR(16) | 年级，冗余自设置 |
| class_name | VARCHAR(32) | 班级名称，冗余自设置 |
| teacher_name | VARCHAR(64) | 教师姓名，冗余自设置 |
| toy_name | VARCHAR(128) | AI/用户生成的教玩具名称 |
| materials | TEXT | 所用材料 |
| play_methods | TEXT | 玩法 |
| ai_raw_json | TEXT NULL | AI 原始 JSON 字符串，便于追踪 |
| created_at / updated_at | DATETIME | 时间戳 |

## 5. AI 集成

新增 `app/integration/ai_client/homemade_teaching_client.py`：

```python
generate_homemade_teaching(
    context,
    api_base_url,
    api_key,
    model_name,
    system_prompt=None,
    *,
    _client=None,
) -> dict
```

输入上下文：

```json
{
  "grade": "小班",
  "class_name": "阳光班",
  "teacher_name": "张老师"
}
```

输出 JSON：

```json
{
  "toy_name": "彩虹穿线板",
  "materials": "废旧纸板、彩色毛根、打孔器、安全剪刀、彩笔。",
  "play_methods": "幼儿选择不同颜色毛根穿过纸板孔洞，尝试按颜色、长短或图案规律进行穿线。"
}
```

约束：
- 内容必须适合当前年级幼儿年龄特点。
- 材料应优先选择幼儿园常见、安全、低成本材料。
- 玩法写清目标动作、互动方式和教师支持要点。
- 禁止 Markdown，禁止返回多余字段。
- 缺字段或空字段抛 `AiParseError`。

## 6. 服务层与仓库层

新增仓库：
- `app/repository/homemade_teaching_repository.py`
  - `create_homemade_teaching_toy`
  - `get_homemade_teaching_toy`
  - `list_homemade_teaching_toys`
  - `delete_homemade_teaching_toy`

新增服务：
- `app/service/homemade_teaching_service.py`
  - `generate_homemade_teaching_content`：读取文本 AI Key、提示词、调用 AI。
  - `create_from_generation`：根据设置快照保存生成结果。
  - `export_homemade_teaching_to_word`：导出并写 `export_records`。

## 7. UI 与导航

新增页面 `/homemade-teaching`：
- 顶部展示当前设置：年级、班级、教师姓名。
- 未配置班级或教师姓名时提示到设置页补全。
- 「AI 生成」按钮：调用 AI 后回填三个字段。
- 三个字段可编辑：教玩具名称、所用材料、玩法。
- 「保存」按钮：保存当前表单。
- 「导出 Word」按钮：保存后导出当前记录。
- 历史区：按创建时间倒序展示，可重新导出，可删除。

导航：
- `app_shell` 的「教学管理」分组新增「自制教玩具」。
- 首页快捷入口可新增「自制教玩具」卡片。
- 提示词管理新增「自制教玩具」Tab。

## 8. 安全与审计

- AI Key 仅在内存中解密使用，不记录明文。
- 所有读取、列表、删除均强制 `tenant_id + user_id`。
- 审计动作：
  - `ai_homemade_teaching`
  - `export_homemade_teaching`

## 9. 验收标准

1. 设置页可填写并保存教师姓名，刷新后回填。
2. 进入 `/homemade-teaching` 可读取当前年级、班级、教师姓名。
3. 点击 AI 生成后，返回并回填教玩具名称、所用材料、玩法。
4. 保存后数据库中有对应记录，历史区可见。
5. 导出 Word 后，班级、姓名、名称、材料、玩法均写入模板正确单元格。
6. 未配置文本 AI Key、班级或教师姓名时有友好提示。
7. 提示词管理可维护 `homemade_teaching` 多版本并回滚。
