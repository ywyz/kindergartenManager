# 📚 kg_manager API文档

完整的kg_manager核心库API参考。

---

## 快速导航

- [安装](#安装)
- [初级用法](#初级用法) - 常用的4个函数
- [数据库API](#数据库api) - 5个函数
- [Word生成API](#word生成api) - 5个函数
- [验证API](#验证api) - 6个函数
- [AI API](#ai-api) - 3个函数
- [完整API列表](#完整api列表)

---

## 安装

### pip安装（推荐）

```bash
cd kindergartenManager
pip install -e .
```

### 验证安装

```python
import kg_manager as kg
print(kg.__version__)  # 输出版本号
```

---

## 初级用法

### 1. 验证教案数据 ✅

```python
import kg_manager as kg

plan_data = {
    "晨间活动": {"集体游戏": "...", "自主游戏": "..."},
    # ... 其他都字段
}

errors = kg.validate_plan_data(plan_data)
if errors:
    print("❌ 数据有问题:")
    for error in errors:
        print(f"  - {error}")
else:
    print("✅ 数据有效")
```

### 2. 保存教案 💾

```python
from datetime import date

# 保存到SQLite
kg.save_plan_data(
    db_path="examples/plan.db",
    date_str="2026-02-26",
    plan_data=plan_data
)

# MySQL也支持（需要先配置）
kg.save_plan_data(
    db_path="mysql://user:password@host/database",
    date_str="2026-02-26",
    plan_data=plan_data
)
```

### 3. 生成Word文档 📄

```python
kg.generate_plan_docx(
    template_path="examples/teacherplan.docx",
    plan_data=plan_data,
    week_text="第（1）周",
    date_text="周（一） 2月26日",
    output_path="output/教案_2026-02-26.docx"
)
```

### 4. 使用AI拆分 🤖

```python
draft = "小班数学活动《认识圆形》，通过教具和展示..."

result = kg.split_collective_activity(
    draft,
    api_key="sk-...",
    model="gpt-4o-mini"
)

print(result["活动主题"])
print(result["活动目标"])
# ...
```

---

## 数据库API

### save_semester()

保存学期信息。

```python
from datetime import date

kg.save_semester(
    db_path="examples/semester.db",
    semester_start=date(2026, 2, 23),
    semester_end=date(2026, 7, 10)
)
```

**参数**：
- `db_path` (str): SQLite数据库路径
- `semester_start` (date): 学期开始日期
- `semester_end` (date): 学期结束日期

---

### load_latest_semester()

加载最新的学期信息。

```python
semester = kg.load_latest_semester("examples/semester.db")
if semester:
    start_date, end_date = semester
    print(f"学期：{start_date} 至 {end_date}")
```

**返回**：
- `(date, date)`: (学期开始日期, 学期结束日期)
- 如果无数据返回 `None`

---

### save_plan_data()

保存教案数据。

```python
kg.save_plan_data(
    db_path="examples/plan.db",
    date_str="2026-02-26",
    plan_data=plan_dict
)
```

**参数**：
- `db_path` (str): SQLite数据库路径
- `date_str` (str): ISO格式日期，如"2026-02-26"
- `plan_data` (dict): 教案数据字典

---

### load_plan_data()

加载教案数据。

```python
plan = kg.load_plan_data(
    db_path="examples/plan.db",
    date_str="2026-02-26"
)

if plan:
    print(f"晨间活动: {plan['晨间活动']}")
```

**返回**：
- `dict`: 教案数据
- 如果无数据返回 `None`

---

### list_plan_dates()

列出所有已保存的教案日期。

```python
dates = kg.list_plan_dates("examples/plan.db")
print(f"已保存教案：{dates}")
# ['2026-02-26', '2026-02-27', ...]
```

**返回**：
- `list[str]`: ISO格式日期列表

---

## Word生成API

### generate_plan_docx()

一键生成完整的Word教案文档。

```python
from pathlib import Path

output_path = kg.generate_plan_docx(
    template_path="examples/teacherplan.docx",
    plan_data={...},
    week_text="第（1）周",
    date_text="周（一） 2月26日",
    output_path="output/教案.docx"
)

print(f"✓ Word已生成：{output_path}")
```

**参数**：
- `template_path` (str|Path): Word模板文件路径
- `plan_data` (dict): 教案数据字典
- `week_text` (str): 周次文本，如"第（1）周"
- `date_text` (str): 日期文本，如"周（一） 2月26日"
- `output_path` (str|Path): 输出文件路径

**返回**：
- `Path`: 输出文件的Path对象

---

### fill_teacher_plan()

填充教师教案模板（高级用法）。

```python
from docx import Document

doc = Document("examples/teacherplan.docx")

kg.fill_teacher_plan(
    doc=doc,
    plan_data={...},
    week_text="第（1）周",
    date_text="周（一） 2月26日"
)

doc.save("output/教案.docx")
```

---

### set_cell_text()

设置表格单元格文本（简单文本）。

```python
cell = table.cell(0, 1)  # 第0行，第1列

kg.set_cell_text(cell, "第（1）周")
```

---

## 验证API

### validate_plan_data()

验证教案数据的完整性和有效性。

```python
errors = kg.validate_plan_data(plan_data)

if errors:
    for error in errors:
        print(error)
    # ['缺少必填字段：晨间活动', '缺少子字段：集体活动.活动主题']
```

**返回**：
- `list[str]`: 错误信息列表，如果无错误返回空列表

---

### init_plan_db()

初始化教案数据库（创建表结构）。

```python
kg.init_plan_db("examples/plan.db")
```

此函数会自动创建所需的表，如果表已存在则不做任何事。

---

### calculate_week_number()

根据学期开始日期计算周次。

```python
from datetime import date

week = kg.calculate_week_number(
    semester_start=date(2026, 2, 23),
    target_date=date(2026, 2, 26)
)

print(f"第{week}周")  # 第1周
```

**返回**：
- `int`: 周次数字

---

### weekday_cn()

获取日期的中文星期名。

```python
from datetime import date

day_name = kg.weekday_cn(date(2026, 2, 26))
print(f"周{day_name}")  # 周四
```

**返回**：
- `str`: 中文星期名（"一" 到 "日"）

---

### build_week_text()

构建格式化的周次文本。

```python
week_text = kg.build_week_text(
    week_number=1,
    is_alternate_week=False
)

print(week_text)  # "第（1）周"
```

---

### build_date_text()

构建格式化的日期文本。

```python
from datetime import date

date_text = kg.build_date_text(date(2026, 2, 26))

print(date_text)  # "周（四） 2月26日"
```

---

## AI API

### split_collective_activity()

使用AI智能拆分集体活动原稿。

```python
result = kg.split_collective_activity(
    draft_text="完整的活动原稿...",
    api_key="sk-...",                          # 可选
    base_url="https://api.openai.com/v1",     # 可选
    model="gpt-4o-mini",                       # 可选
    system_prompt=None                         # 可选
)

# result = {
#     "活动主题": "...",
#     "活动目标": "...",
#     "活动准备": "...",
#     "活动重点": "...",
#     "活动难点": "...",
#     "活动过程": "..."
# }
```

**参数**：
- `draft_text` (str): 教案原稿
- `api_key` (str, 可选): OpenAI API Key，不提供则从环境变量读取
- `base_url` (str, 可选): 自定义API端点
- `model` (str, 可选): AI模型名，默认"gpt-4o-mini"
- `system_prompt` (str, 可选): 自定义系统提示词

**返回**：
- `dict`: 拆分结果（6个字段）

---

### set_custom_system_prompt()

设置全局AI提示词（影响后续所有的split_collective_activity调用）。

```python
kg.set_custom_system_prompt("""
你是幼儿园教案设计专家...
[详细要求]
""")

# 之后的调用都会使用该提示词
result = kg.split_collective_activity(draft_text)
```

---

### parse_ai_json()

手动解析AI返回的JSON字符串。

```python
json_str = '''{"活动主题": "...", ...}'''

result = kg.parse_ai_json(json_str)
```

**返回**：
- `dict`: 解析后的字典
- 如果格式无效会抛出异常

---

## 完整API列表

### 所有导出的符号

```python
import kg_manager as kg

# 常量
kg.FIELD_ORDER              # 字段顺序列表
kg.SUBFIELDS                # 子字段映射
kg.WORD_FONT_NAME           # 字体名
kg.WORD_FONT_SIZE           # 字体大小
kg.WORD_INDENT_FIRST_LINE   # 首行缩进

# 数据库
kg.init_plan_db()
kg.save_semester()
kg.load_latest_semester()
kg.save_plan_data()
kg.load_plan_data()
kg.list_plan_dates()

# Word生成
kg.generate_plan_docx()
kg.fill_teacher_plan()
kg.fill_doc_by_labels()
kg.set_cell_text()
kg.append_by_labels()
kg.normalize_label()          # 标签规范化

# 验证
kg.validate_plan_data()
kg.export_schema_json()
kg.calculate_week_number()
kg.weekday_cn()
kg.build_week_text()
kg.build_date_text()

# AI
kg.split_collective_activity()
kg.parse_ai_json()
kg.set_custom_system_prompt()
```

---

## 常见用途

### 场景1：批量生成教案

```python
import kg_manager as kg
from datetime import date, timedelta

start_date = date(2026, 2, 23)
num_days = 7

for i in range(num_days):
    current_date = start_date + timedelta(days=i)
    plan_data = load_plan(current_date)  # 你的加载函数
    
    kg.generate_plan_docx(
        template_path="template.docx",
        plan_data=plan_data,
        week_text=kg.build_week_text(...),
        date_text=kg.build_date_text(current_date),
        output_path=f"output/{current_date}.docx"
    )
```

### 场景2：与数据库配合

```python
import kg_manager as kg

# 初始化
kg.init_plan_db("plan.db")

# 保存
kg.save_plan_data("plan.db", "2026-02-26", plan_data)

# 加载
loaded = kg.load_plan_data("plan.db", "2026-02-26")

# 导出
kg.generate_plan_docx(
    "template.docx",
    loaded,
    "第（1）周",
    "周（四） 2月26日",
    "output.docx"
)
```

### 场景3：完整工作流

```python
import kg_manager as kg
from datetime import date

# 1. 验证
errors = kg.validate_plan_data(plan_data)
if errors:
    print("数据有问题，无法继续")
    exit(1)

# 2. 使用AI增强
if has_collective_draft:
    ai_result = kg.split_collective_activity(
        draft_text,
        api_key="sk-...",
        model="gpt-4o-mini"
    )
    plan_data["集体活动"] = ai_result

# 3. 保存数据
kg.save_plan_data("plan.db", "2026-02-26", plan_data)

# 4. 生成文档
kg.generate_plan_docx(
    "template.docx",
    plan_data,
    "第（1）周",
    "周（四） 2月26日",
    "output/教案.docx"
)

print("✅ 完成！")
```

---

## 错误处理

### API异常处理示例

```python
import kg_manager as kg

try:
    result = kg.split_collective_activity(
        draft_text,
        api_key="sk-..."
    )
except ValueError as e:
    print(f"❌ 数据错误: {e}")
except RuntimeError as e:
    print(f"❌ API错误: {e}")
except Exception as e:
    print(f"❌ 未知错误: {e}")
```

---

## 版本历史

| 版本 | 发布日期 | 重要更新 |
|------|---------|--------|
| 0.1.0 | 2026-02-10 | 初始版本，核心功能完成 |

---

## 许可证

MIT License - 详见项目LICENSE文件

---

🎉 **准备好了吗？** [查看示例](../../examples_usage.py)
