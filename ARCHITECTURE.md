# kg_manager 架构与集成指南

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      幼儿园管理系统 (其他系统)                     │
├─────────────────────────────────────────────────────────────────┤
│  教师服务 │ 课程管理 │ 评估系统 │ 家长通知 │ 其他功能...            │
└──────────────┬────────────────────────────────────────────────────┘
               │
               │ import
               │
┌──────────────▼────────────────────────────────────────────────────┐
│                     kg_manager (教案管理核心库)                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   数据验证    │  │ Word文档生成  │  │ 数据库操作    │              │
│  │  validate.py │  │   word.py    │  │    db.py     │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│        ▲                  ▲                   ▲                      │
│        └──────────────────┴───────────────────┘                     │
│                           │                                        │
│                    ┌──────▼──────┐                                 │
│                    │ models.py    │                                │
│                    │ (常量&配置)   │                                │
│                    └──────────────┘                                │
│                                                                     │
│  ┌──────────────┐                                                  │
│  │   AI集成      │                                                  │
│  │    ai.py     │  ◄─ OPENAI_API_KEY                              │
│  └──────────────┘                                                  │
│                                                                     │
│                __init__.py (统一接口)                              │
└────────────────────────────────────────────────────────────────────┘
               ▲
               │ import
               │
┌──────────────┴────────────────────────────────────────────────────┐
│              app.py (NiceGUI Web界面 - 当前系统)                  │
├────────────────────────────────────────────────────────────────────┤
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                      │
│  │表单  │ │验证  │ │保存  │ │加载  │ │导出  │  ...                │
│  │输入  │ │数据  │ │数据  │ │教案  │ │Word  │                      │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘                      │
└────────────────────────────────────────────────────────────────────┘
```

## 模块依赖关系

```
models.py (无依赖)
   │
   ├──▶ db.py
   ├──▶ word.py
   ├──▶ validate.py
   └──▶ ai.py
        │
        └──▶ openai (外部)

app.py ◀─── __init__.py (导出所有)
```

## 当前架构 vs 重构后

### 重构前（单文件模式）

```
minimal_fill.py (全部逻辑)
    │
    ├─ Word操作
    ├─ 数据验证
    ├─ 数据库操作
    └─ 常数定义
         │
         └──▶ app.py (UI层)
```

**问题：**
- ❌ 代码混杂，难以复用
- ❌ 其他系统要使用功能，需要导入整个文件
- ❌ 修改一个功能可能影响其他功能
- ❌ 难以单独测试

### 重构后（模块化模式）

```
kg_manager/
├─ models.py (常量)
├─ db.py (数据持久化)
├─ word.py (文档生成)
├─ validate.py (数据校验)
├─ ai.py (AI功能)
└─ __init__.py (接口)
    │
    ├──▶ app.py (当前系统UI)
    ├──▶ 其他系统1 (某功能)
    ├──▶ 其他系统2 (某功能)
    └──▶ 其他系统N (某功能)
```

**优势：**
- ✅ 代码清晰，功能独立
- ✅ 任何系统可直接导入使用
- ✅ 模块独立维护、测试
- ✅ 低耦合、高内聚

## 数据流

### 教案创建流程

```
┌─────────────┐
│  用户输入    │
│ (NiceGUI)   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│  validate_plan_data()    │  ◀──── validate.py
│  (验证表单数据)          │
└──────┬──────────────────┘
       │ ✓ 通过
       ▼
┌─────────────────────────┐
│  save_plan_data()        │  ◀──── db.py
│  (保存到数据库)           │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  generate_plan_docx()    │  ◀──── word.py
│  (生成Word文档)           │
└──────┬──────────────────┘
       │
       ▼
┌─────────────┐
│  Word文件    │
│  (output/)  │
└─────────────┘
```

### AI拆分流程

```
┌──────────────────────┐
│  原稿文本             │
│  (集体活动完整方案)    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────┐
│  split_collective_activity()  │  ◀──── ai.py
│  (调用OpenAI API)             │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  parse_ai_json()              │  ◀──── ai.py
│  (解析返回的JSON)             │
└──────────┬───────────────────┘
           │
           ▼
┌─────────────────────────┐
│  {活动主题, 目标, ...}    │
│  (结构化数据)             │
└──────┬──────────────────┘
       │
       ▼
┌──────────────────┐
│  回填到表单       │
│  (app.py)         │
└──────────────────┘
```

## 三层架构

```
┌────────────────────────────────────────┐
│         应用层 (Application)            │
│  app.py (NiceGUI Web界面)              │
│  其他系统的功能模块                     │
└────────┬─────────────────────────────┘
         │ 调用接口
┌────────▼─────────────────────────────┐
│      业务逻辑层 (Business Logic)      │
│  kg_manager/__init__.py               │
│  导出所有函数和常量 (20+ 函数)        │
└────────┬─────────────────────────────┘
         │ 内部使用
┌────────▼─────────────────────────────┐
│       数据访问层 (Data Access)        │
│  db.py (SQLite)                      │
│  models.py (配置定义)                 │
│  其他模块 (word, validate, ai)        │
└────────────────────────────────────────┘
```

## 集成场景示例

### 场景1：教师端集成

```python
# teacher_module.py
import kg_manager as kg

class TeacherService:
    def create_lesson_plan(self, teacher_id, plan_date, plan_data):
        # 1. 验证
        errors = kg.validate_plan_data(plan_data)
        if errors:
            raise ValueError(errors)
        
        # 2. 保存
        kg.save_plan_data("shared/plan.db", plan_date, plan_data)
        
        # 3. 生成Word
        output = kg.generate_plan_docx(...)
        
        # 4. 保存到教师文件库
        self.save_to_teacher_files(teacher_id, output)
        
        return output
```

### 场景2：家长通知集成

```python
# parent_notification.py
import kg_manager as kg

class ParentNotification:
    def notify_daily_activities(self, date_str):
        # 从共享数据库加载教案
        plan_data = kg.load_plan_data("shared/plan.db", date_str)
        
        if plan_data:
            # 生成简化版本给家长
            message = self.format_for_parents(plan_data)
            return self.send_notification(message)
```

### 场景3：课程评估集成

```python
# curriculum_assessment.py
import kg_manager as kg

class CurriculumAssessment:
    def analyze_activities(self, date_range):
        # 从数据库获取多天教案
        dates = kg.list_plan_dates("shared/plan.db")[:]
        
        for date_str in dates:
            plan_data = kg.load_plan_data("shared/plan.db", date_str)
            # 分析教案内容
            self.analyze_plan(plan_data)
```

## 配置管理

### 修改字段定义

```python
# kg_manager/models.py

FIELD_ORDER = [
    ("周次", False),
    ("日期", False),
    ("你的新字段", True),  # 添加新字段
    # ...
]

SUBFIELDS = {
    "你的分组字段": ["子1", "子2"],
}
```

### 修改AI提示词

```python
# 在任何系统中
import kg_manager as kg

kg.set_custom_system_prompt("""
你是教案写作专家，请按照...
""")

result = kg.split_collective_activity(draft)
```

### 修改Word格式

```python
# kg_manager/models.py

WORD_FONT_NAME = "宋体"  # 改为宋体
WORD_FONT_SIZE = 14      # 改为14pt
WORD_INDENT_FIRST_LINE = 32  # 改为4个字符
```

## 部署检查清单

### 本地开发

- [ ] `python -m pytest` - 运行单元测试（如果有）
- [ ] `python examples_usage.py` - 运行使用示例
- [ ] `python app.py` - 启动Web界面
- [ ] 验证导入：`from kg_manager import *`

### pip安装

- [ ] `pip install -e .` - 开发模式安装
- [ ] `python -c "import kg_manager; print(dir(kg_manager))"` - 验证导出

### 其他系统集成

- [ ] 添加依赖：`pip install kg-manager`
- [ ] 导入模块：`import kg_manager as kg`
- [ ] 测试接口调用：`kg.validate_plan_data({})`
- [ ] 验证数据库操作
- [ ] 验证Word生成
- [ ] 验证AI功能（如选用）

## 后续演进方向

```
当前 (本地Web应用)
  │
  ├──▶ API微服务 (FastAPI)
  │    │
  │    └──▶ 其他系统通过HTTP调用
  │
  ├──▶ Docker容器化
  │    │
  │    └──▶ 便于云部署
  │
  └──▶ 插件系统
       │
       └──▶ 用户自定义字段和功能
```

---

**版本**：kg_manager 0.1.0  
**最后更新**：2026年2月  
**适配系统**：Python 3.8+
