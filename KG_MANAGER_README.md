# kg_manager - 幼儿园教案管理核心库

一个模块化的幼儿园教案管理系统核心库，支持数据验证、Word文档生成、数据库存取和AI内容拆分等功能。

## 特性

- ✅ **模块化设计** - 功能独立，便于集成到其他系统
- ✅ **数据验证** - 完整的教案数据验证和约束检查
- ✅ **Word生成** - 自动填充Word模板文档
- ✅ **数据持久化** - SQLite数据库存取教案和学期信息
- ✅ **AI集成** - OpenAI API支持自动拆分集体活动原稿
- ✅ **灵活配置** - 可自定义字段、字体、提示词等

## 安装

### 方式1：本地开发安装

```bash
cd kindergartenManager
pip install -e .
```

### 方式2：从Git安装

```bash
pip install git+https://github.com/ywyz/kindergartenManager.git@tplan
```

### 方式3：手动拷贝

将 `kg_manager/` 目录拷贝到你的项目中，直接导入使用。

## 快速开始

### 基本使用

```python
import kg_manager as kg
from datetime import date
from pathlib import Path

# 1. 验证教案数据
plan_data = {
    "晨间活动": {"集体游戏": "...", "自主游戏": "..."},
    "晨间活动指导": {"重点指导": "...", "活动目标": "...", "指导要点": "..."},
    # ... 其他字段
}
errors = kg.validate_plan_data(plan_data)
if not errors:
    print("✓ 教案数据有效")

# 2. 保存到数据库
kg.save_plan_data("plan.db", date.today().isoformat(), plan_data)

# 3. 从数据库加载
loaded = kg.load_plan_data("plan.db", "2026-02-26")

# 4. 生成Word文档
kg.generate_plan_docx(
    template_path="template.docx",
    plan_data=plan_data,
    week_text="第（1）周",
    date_text="周（一） 2月26日",
    output_path="output.docx"
)
```

### AI拆分集体活动

```python
import kg_manager as kg
import os

# 设置OpenAI API密钥
os.environ["OPENAI_API_KEY"] = "your-api-key"

# 使用AI拆分原稿
draft = "完整的集体活动原稿..."
result = kg.split_collective_activity(draft)

print(result)
# {
#     "活动主题": "...",
#     "活动目标": "...",
#     "活动准备": "...",
#     "活动重点": "...",
#     "活动难点": "...",
#     "活动过程": "..."
# }
```

## 模块说明

### `kg_manager.models`
定义了常量和数据模型：
- `FIELD_ORDER` - 教案字段顺序和必填标记
- `SUBFIELDS` - 分组字段的子字段列表
- `SAMPLE_PLAN_DATA` - 样本数据
- `WORD_FONT_*` - Word格式常数

### `kg_manager.db`
数据库操作：
- `save_semester()` - 保存学期信息
- `load_latest_semester()` - 加载最新学期
- `save_plan_data()` - 保存教案
- `load_plan_data()` - 加载教案
- `list_plan_dates()` - 列出所有教案日期
- `delete_plan_data()` - 删除教案
- `get_plan_data_info()` - 获取元数据

### `kg_manager.word`
Word文档操作：
- `generate_plan_docx()` - 生成教案Word文档
- `fill_teacher_plan()` - 填充教师教案文档
- `fill_doc_by_labels()` - 按标签填充文档
- `set_cell_text()` - 设置表格单元格文本
- `append_by_labels()` - 按标签追加内容

### `kg_manager.validate`
数据验证和转换：
- `validate_plan_data()` - 验证教案数据
- `export_schema_json()` - 导出字段Schema
- `calculate_week_number()` - 计算周次
- `weekday_cn()` - 获取中文星期名
- `build_week_text()` - 构建周次文本
- `build_date_text()` - 构建日期文本

### `kg_manager.ai`
AI集成：
- `split_collective_activity()` - 使用AI拆分集体活动原稿
- `parse_ai_json()` - 解析AI返回的JSON
- `set_custom_system_prompt()` - 设置自定义AI提示词

## 环境变量

- `OPENAI_API_KEY` - OpenAI API密钥（使用AI功能时必需）

## 字段定义

### 必填字段
- 晨间活动
- 晨间活动指导
- 晨间谈话
- 集体活动
- 室内区域游戏
- 下午户外游戏

### 可选字段
- 一日活动反思

### 自动生成字段
- 周次 - 自动根据学期开始日期计算
- 日期 - 自动根据目标日期生成

## 数据库架构

### semesters 表
```sql
CREATE TABLE semesters (
    id INTEGER PRIMARY KEY,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    created_at TEXT NOT NULL
)
```

### plan_entries 表
```sql
CREATE TABLE plan_entries (
    id INTEGER PRIMARY KEY,
    plan_date TEXT NOT NULL UNIQUE,
    plan_data TEXT NOT NULL,  -- JSON格式
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

## 集成示例

### 作为子模块集成

```python
# 在大系统中使用
from kg_manager import (
    validate_plan_data,
    save_plan_data,
    load_plan_data,
    generate_plan_docx,
    split_collective_activity,
)

class KindergartenSystem:
    def create_lesson_plan(self, plan_data, plan_date):
        # 验证
        errors = validate_plan_data(plan_data)
        if errors:
            return {"success": False, "errors": errors}
        
        # 保存
        save_plan_data(self.plan_db, plan_date, plan_data)
        
        # 导出
        output = generate_plan_docx(...)
        
        return {"success": True, "output": output}
```

## 自定义配置

### 修改AI提示词

```python
import kg_manager as kg

new_prompt = "你是教案编写专家，请按照以下格式..."
kg.set_custom_system_prompt(new_prompt)
```

### 自定义字段

修改 `kg_manager/models.py` 中的 `FIELD_ORDER` 和 `SUBFIELDS`：

```python
FIELD_ORDER = [
    ("你的字段", True),  # (字段名, 是否必填)
    ...
]

SUBFIELDS = {
    "你的分组字段": ["子字段1", "子字段2"],
    ...
}
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 贡献

欢迎提交Issue和Pull Request！

## 相关项目

- [幼儿园管理系统](https://github.com/ywyz/kindergartenManager) - 完整的幼儿园管理系统
