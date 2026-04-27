
# 幼儿园每日活动计划系统

> 教学管理子系统 · `feature/week-plan` 分支

---

## 项目背景与架构

本仓库为幼儿园每日活动计划与周计划管理系统，包含一日计划、周计划、AI 生成、Word 导出、历史记录、系统设置等模块。

### 运行环境
- Python ≥ 3.12，依赖见 pyproject.toml
- NiceGUI ≥ 2.0
- MySQL 数据库
- OpenAI 兼容 AI 接口
- Word 导出模板见 templates/

### 目录结构
- app/: 主程序、页面、服务、模型
- templates/: Word 模板
- exports/: 导出文件目录
- docs/: 详细业务文档（见下）

---

## 详细业务文档索引

- 一日活动计划详细需求：[docs/daily-plan.md](docs/daily-plan.md)
- 周计划详细需求：[docs/week-plan.md](docs/week-plan.md)

---

## 启动与开发

1. 安装依赖：`uv sync`
2. 配置 .env（参考 .env.example）
3. 启动：`uv run python -m app.main`
4. 访问 http://localhost:8080

---

> 本文件为项目总入口，详细业务需求请见 docs/ 目录。所有架构、全局约束、模块索引变更请同步维护。
| `updated_at`       | DATETIME | 更新时间                           |

唯一键：`(semester_id, week_number, grade, class_name)`。

### 10.4 AI 提示词分类

新增 3 类，沿用现有提示词管理页：

| 分类                   | 用途                       |
| ---------------------- | -------------------------- |
| `weekly_morning_talk`  | 批量生成 5 天晨间谈话      |
| `weekly_outdoor_game`  | 批量生成 5 天户外游戏      |
| `weekly_area_game`     | 批量生成 5 天区域游戏      |
| `weekly_summary`       | 生成本周重点/环境/生活/家园 |

### 10.5 新增文件

| 文件                              | 作用                                     |
| --------------------------------- | ---------------------------------------- |
| `app/models/weekly_plan.py`       | WeekDayPlan / WeeklyPlan dataclass + CRUD |
| `app/pages/weekly_plan.py`        | 周计划页面（NiceGUI）                    |
| `templates/weekplan_mapping.md`   | 模板字段映射文档                         |

### 10.6 修改文件

| 文件                          | 改动                                   |
| ----------------------------- | -------------------------------------- |
| `app/db.py`                   | 新增 `weekly_plans` DDL + 迁移         |
| `app/services/date_utils.py`  | 新增 `get_week_info()` 等周级工具函数  |
| `app/services/ai_service.py`  | 新增 4 类周计划 AI 生成方法            |
| `app/services/word_export.py` | 新增 `export_weekly_plan_word()`        |
| `app/pages/settings.py`       | 新增教师姓名、保育员姓名设置项         |
| `app/pages/prompt_mgmt.py`    | 扩展周计划提示词分类                   |
| `app/main.py`                 | 新增 `/weekly-plan` 路由与导航项       |

### 10.7 周计划验收清单

1. 选择日期后自动推导本周周次、各天日期、工作日/放假日标记
2. 点击"从一日计划同步"后，已有一日计划的集体活动填入对应天格；缺失天保留空白
3. AI 生成整周晨间谈话、户外游戏、区域游戏、本周重点等内容
4. 节假日当天晨间谈话显示空，集体活动显示"放假"
5. 保存后刷新页面仍能恢复快照内容
6. 导出 Word：表格内容与 weekplan.docx 模板位置一致，教师/保育员/周次/日期正确填充

---

## 11. 一日计划验收清单

1. `uv run python -m app.main` 启动无报错,4 页面均可访问
2. MySQL 连接成功,5 张表自动创建
3. 设置页保存数据,刷新仍在
4. 粘贴教案 → AI 拆分 5 字段全部填充,活动过程双 Tab 可见 diff
5. 日期选择显示正确周次和星期
6. AI 生成 4 块活动内容
7. 导出 Word:表格结构与模板一致,AI 修改环节红字
8. 自定义提示词激活后实际生效
9. 历史记录可重新导出旧计划
