# 教案管理系统重构文档

## 一、重构目标

将原有的单文件系统（`minimal_fill.py` + `app.py`）重构为模块化结构，便于其他系统集成和复用核心功能。

## 二、新的目录结构

```
kindergartenManager/
├── kg_manager/                 # 核心库（可复用）
│   ├── __init__.py            # 公开接口
│   ├── models.py              # 常量和数据模型
│   ├── db.py                  # 数据库操作
│   ├── word.py                # Word文档操作
│   ├── validate.py            # 数据验证
│   └── ai.py                  # AI集成
│
├── app.py                      # NiceGUI Web界面
├── minimal_fill.py             # 原文件（保留兼容性）
├── setup.py                    # Python包配置
├── KG_MANAGER_README.md        # 模块使用文档
├── examples_usage.py           # 使用示例
└── README.md                   # 项目README
```

## 三、模块拆分说明

### 1. **models.py** - 常量和配置

包含所有常量定义，便于其他系统修改配置：

```python
FIELD_ORDER          # 教案字段顺序
SUBFIELDS           # 分组字段定义
WORD_FONT_NAME      # Word字体
SAMPLE_PLAN_DATA    # 样本数据
```

**用途**：被所有其他模块引用，集中管理配置。

### 2. **db.py** - 数据库操作

| 函数 | 功能 |
|------|------|
| `save_semester()` | 保存学期信息 |
| `load_latest_semester()` | 加载最新学期 |
| `save_plan_data()` | 保存教案 |
| `load_plan_data()` | 加载教案 |
| `list_plan_dates()` | 列出所有教案日期 |
| `delete_plan_data()` | 删除教案 |
| `get_plan_data_info()` | 获取元数据 |

**用途**：数据持久化，支持多系统共享数据库。

### 3. **word.py** - Word文档操作

| 函数 | 功能 |
|------|------|
| `generate_plan_docx()` | 生成教案Word文档 |
| `fill_teacher_plan()` | 填充教师教案 |
| `fill_doc_by_labels()` | 按标签填充文档 |
| `append_by_labels()` | 追加标签内容 |
| `set_cell_text()` | 设置单元格文本 |

**用途**：Word文档生成，独立于UI，可在任何系统中使用。

### 4. **validate.py** - 数据验证和工具

| 函数 | 功能 |
|------|------|
| `validate_plan_data()` | 验证教案数据 |
| `export_schema_json()` | 导出字段Schema |
| `calculate_week_number()` | 计算周次 |
| `weekday_cn()` | 获取中文星期名 |
| `build_week_text()` | 构建周次文本 |
| `build_date_text()` | 构建日期文本 |

**用途**：数据验证和转换，无外部依赖。

### 5. **ai.py** - AI集成

| 函数 | 功能 |
|------|------|
| `split_collective_activity()` | AI拆分集体活动 |
| `parse_ai_json()` | 解析AI返回JSON |
| `set_custom_system_prompt()` | 设置自定义提示词 |

**用途**：OpenAI集成，支持自定义提示词。

### 6. **__init__.py** - 公开接口

统一导出所有公开函数和常量，使其他系统通过单一导入即可使用：

```python
import kg_manager as kg

# 直接调用
kg.validate_plan_data()
kg.save_plan_data()
kg.load_plan_data()
kg.generate_plan_docx()
kg.split_collective_activity()
```

## 四、依赖关系图

```
models.py
   ↓
┌──────────────┬──────────────┬──────────────┬──────────┐
│              │              │              │          │
db.py      word.py      validate.py      ai.py     app.py
   ↓          ↓              ↓              ↓          ↓
┌──────────────────────────────────────────────────────┐
│           __init__.py (公开接口)                      │
└──────────────────────────────────────────────────────┘
```

## 五、其他系统集成方式

### 方案1：作为pip包安装

```bash
# 从本地安装
pip install -e /path/to/kindergartenManager

# 从GitHub安装
pip install git+https://github.com/ywyz/kindergartenManager.git@tplan
```

### 方案2：作为子模块（推荐）

```bash
# 在大系统中添加
git submodule add https://github.com/ywyz/kindergartenManager.git kg_manager

# 导入使用
from kg_manager import kg_manager as kg
```

### 方案3：直接拷贝（快速集成）

将 `kg_manager/` 目录拷贝到你的项目中，直接导入：

```python
from kg_manager import validate_plan_data, save_plan_data
```

## 六、迁移指南

### 旧代码 → 新代码

| 旧 | 新 |
|-----|-----|
| `from minimal_fill import validate_plan_data` | `import kg_manager as kg; kg.validate_plan_data()` |
| `from minimal_fill import fill_teacher_plan` | `kg.fill_teacher_plan()` |
| `from minimal_fill import save_plan_data` | `kg.save_plan_data()` |
| `from minimal_fill import FIELD_ORDER` | `kg.FIELD_ORDER` |

### app.py 中的更新

```python
# 旧
from minimal_fill import (
    validate_plan_data,
    fill_teacher_plan,
    FIELD_ORDER,
    SUBFIELDS,
)

# 新
import kg_manager as kg
from kg_manager import FIELD_ORDER, SUBFIELDS
```

## 七、向后兼容性

`minimal_fill.py` 保留在项目中，通过导入 `kg_manager` 继续工作：

```python
# minimal_fill.py 中可添加以下代码
from kg_manager import *  # 导出所有函数
```

这样，使用 `from minimal_fill import ...` 的旧代码仍能工作。

## 八、扩展点

### 自定义字段

在 `kg_manager/models.py` 中修改：

```python
FIELD_ORDER = [
    ("你的字段", True),  # (字段名, 是否必填)
]

SUBFIELDS = {
    "你的分组字段": ["子字段1", "子字段2"],
}
```

### 自定义AI提示词

```python
import kg_manager as kg

custom_prompt = "你是教案专家..."
kg.set_custom_system_prompt(custom_prompt)
result = kg.split_collective_activity(draft)
```

### 自定义Word格式

修改 `kg_manager/models.py` 中的 Word 配置：

```python
WORD_FONT_NAME = "仿宋"
WORD_FONT_SIZE = 12
WORD_INDENT_FIRST_LINE = 24
```

## 九、测试验证

运行使用示例验证模块功能：

```bash
python examples_usage.py
```

启动Web界面：

```bash
python app.py
```

## 十、文件清理

- ✅ `kg_manager/` - 新建核心库目录
- ✅ `minimal_fill.py` - 保留（可标注为deprecated）
- ✅ `app.py` - 更新为使用新模块
- ✅ `setup.py` - 新建，便于pip安装
- ✅ `KG_MANAGER_README.md` - 新建，模块使用文档
- ✅ `examples_usage.py` - 新建，使用示例

## 十一、后续改进方向

1. **API服务** - 可基于 `kg_manager` 创建 FastAPI 微服务
2. **CLI工具** - 可创建命令行工具使用核心库
3. **插件系统** - 支持自定义字段和功能扩展
4. **数据迁移** - MySQL 等其他数据底层的支持
5. **文档生成** - 支持更多格式（PDF、HTML等）

## 总结

通过模块化重构，`kg_manager` 从单一的UI应用演变为：
- ✅ 可复用的核心库
- ✅ 支持多系统集成
- ✅ 清晰的功能划分
- ✅ 灵活的扩展机制
- ✅ 向后兼容的设计

其他幼儿园子系统可通过导入 `kg_manager` 而无需关注 UI 实现细节。
