# 🏗️ 系统架构

完整的系统架构说明和模块化设计。

---

## 总体架构

### 三层架构

```
┌─────────────────────────────────────────┐
│         表现层 (Presentation)            │
│  app.py (NiceGUI Web UI)                │
├─────────────────────────────────────────┤
│         业务逻辑层 (Business Logic)      │
│  kg_manager/ (核心库)                    │
├─────────────────────────────────────────┤
│         数据层 (Data Layer)              │
│  SQLite/MySQL (数据库)                   │
└─────────────────────────────────────────┘
```

---

## 模块层次

### kg_manager 核心库结构

```
kg_manager/
├── models.py          # 基础模块（无依赖）
│   ├─ FIELD_ORDER      # 字段顺序
│   ├─ SUBFIELDS        # 子字段映射
│   ├─ 字体和格式常量
│   └─ SAMPLE_PLAN_DATA # 示例数据
│
├── db.py              # 数据库模块（依赖：models）
│   ├─ init_plan_db()
│   ├─ save_semester()
│   ├─ load_latest_semester()
│   ├─ save_plan_data()
│   ├─ load_plan_data()
│   └─ list_plan_dates()
│
├── word.py            # Word生成模块（依赖：models）
│   ├─ normalize_label()
│   ├─ split_by_punctuation()
│   ├─ set_cell_content()
│   ├─ fill_by_row_labels()
│   ├─ generate_plan_docx()
│   └─ ... (8个helper函数)
│
├── validate.py        # 验证模块（依赖：models）
│   ├─ validate_plan_data()
│   ├─ calculate_week_number()
│   ├─ weekday_cn()
│   ├─ build_date_text()
│   ├─ export_schema_json()
│   └─ ... (2个helper函数)
│
├── ai.py              # AI集成模块（依赖：openai)
│   ├─ split_collective_activity()
│   ├─ parse_ai_json()
│   ├─ set_custom_system_prompt()
│   └─ DEFAULT_SYSTEM_PROMPT
│
└── __init__.py        # 统一接口（导出所有公开API）
    └─ 27+ 公开函数和常量
```

### 模块依赖关系

```
models.py (无依赖)
   ├──▶ db.py
   ├──▶ word.py
   ├──▶ validate.py
   └──▶ ai.py
        │
        └──▶ openai (外部库)

app.py (NiceGUI)
   │
   └──▶ __init__.py (统一接口)
        │
        └──▶ 所有其他模块
```

---

## 数据流

### 场景1：创建和保存教案

```
app.py (表单输入)
   │
   ├─ 收集表单数据 (form fields)
   │
   ├─ 调用 validate_plan_data() [validate.py]
   │   └─ 检查必填字段
   │   └─ 检查子字段结构
   │   └─ 返回错误列表或空列表
   │
   ├─ 如果无错误，调用 save_plan_data() [db.py]
   │   └─ 打开/初始化数据库 [models.py constants]
   │   └─ 插入或更新记录
   │   └─ 返回成功
   │
   └─ UI显示成功消息
```

### 场景2：生成Word文档

```
app.py (导出按钮)
   │
   ├─ 读取当前表单数据
   │
   ├─ 调用 generate_plan_docx() [word.py]
   │   ├─ 加载模板文档
   │   │
   │   ├─ 调用 flatten_plan_data() [word.py]
   │   │   └─ 将嵌套dict转为平坦dict
   │   │   └─ 添加父字段前缀
   │   │
   │   ├─ 逐行填充表格
   │   │   ├─ 调用 normalize_label() [word.py] 规范化标签
   │   │   ├─ 调用 smart_lookup() [word.py] 查找对应值
   │   │   └─ 调用 set_cell_content() [word.py] 设置单元格
   │   │
   │   ├─ 调用 apply_run_style() [word.py]
   │   │   └─ 设置字体为仿宋12pt [models.py constants]
   │   │
   │   └─ 保存文件到output/目录
   │
   └─ UI显示文件保存成功
```

### 场景3：使用AI拆分

```
app.py (分割按钮)
   │
   ├─ 读取用户输入的原稿
   │
   ├─ 从localStorage读取AI配置
   │   ├─ API Key
   │   ├─ Model
   │   └─ Base URL
   │
   ├─ 调用 split_collective_activity() [ai.py]
   │   ├─ 读取系统提示词 [models.py DEFAULT_SYSTEM_PROMPT]
   │   ├─ 构建请求体 (system + user message)
   │   ├─ 调用 OpenAI API
   │   ├─ 获取返回的JSON
   │   │
   │   ├─ 调用 parse_ai_json() [ai.py]
   │   │   └─ 解析JSON并检查格式
   │   │
   │   └─ 返回结构化数据字典
   │
   ├─ 映射结果到表单字段
   │   └─ "活动主题" → 活动主题字段
   │   └─ "活动目标" → 活动目标字段
   │   └─ ... (共6个字段)
   │
   └─ UI自动填充表单
```

---

## 关键设计决策

### 1. 模块化设计（高内聚，低耦合）

**为什么**：
- 便于重用 - kg_manager可独立用于其他项目
- 便于测试 - 每个模块可独立测试
- 便于维护 - 修改不会影响其他模块

**实现**：
- models.py 完全独立，零依赖
- 其他模块只依赖 models.py 或外部库
- 通过 __init__.py 统一导出接口

### 2. 向后兼容层（minimal_fill.py）

**为什么**：
- 现有的 app.py 依赖旧的 minimal_fill.py
- 重构后需要平滑过渡

**实现**：
- minimal_fill.py 中的所有函数保留
- 内部调用新的 kg_manager 模块
- 对外接口完全相同

### 3. 灵活的AI集成

**为什么**：
- 支持不同的AI提供商（OpenAI、ChatAnywhere等）
- 支持自定义提示词
- 支持线程安全的配置传递

**实现**：
- split_collective_activity() 接受明确的参数
- 支持从环境变量读取（向后兼容）
- set_custom_system_prompt() 用于全局自定义

### 4. 标准化的Word格式

**为什么**：
- 确保生成的文档格式统一
- 按照幼儿园教案的标准格式

**实现**：
- 所有常数定义在 models.py
- normalize_label() 处理不规则的标签
- apply_run_style() 统一设置字体

---

## 扩展点

### 添加新字段

1. 编辑 `models.py`:
   ```python
   FIELD_ORDER = [
       # ... 现有字段
       ("新字段", True),  # 标记是否必填
   ]
   
   SUBFIELDS = {
       # ... 现有子字段
       "新字段": ["子字段1", "子字段2"],
   }
   ```

2. 运行 `minimal_fill.py` 重新生成schema

3. 更新 `app.py` 的表单构建逻辑

### 集成新的数据库

1. 创建 `db_mysql.py` (或其他)

2. 实现相同的接口：
   - init_plan_db(db_path)
   - save_plan_data(db_path, date_str, plan_data)
   - load_plan_data(db_path, date_str)
   - list_plan_dates(db_path)
   - save_semester(db_path, start, end)
   - load_latest_semester(db_path)

3. 在 `db.py` 中添加dispatch逻辑

### 支持新的AI提供商

1. 编辑 `kg_manager/ai.py`

2. 修改 `split_collective_activity()` 中的API调用逻辑

3. 支持新的参数配置

---

## 性能考虑

### Word生成

- **瓶颈**：加载和解析Word文档
- **优化**：缓存模板，并行生成多个文档

### AI调用

- **瓶颈**：API延迟（通常2-5秒）
- **优化**：异步调用，显示进度指示

### 数据库操作

- **瓶颈**：SQLite单线程限制
- **优化**：对于多用户场景使用MySQL

---

## 安全考虑

### API Key管理

- ✅ API Key存储在浏览器localStorage（用户自己管理）
- ⚠️ localStorage不加密，不应存储在公共机器上
- ✅ 可通过清除缓存撤销访问权限

### 数据库连接

- ✅ 支持MySQL远程连接
- ⚠️ 密码明文存储在localStorage
- 💡 建议：使用MySQL用户权限限制只读/写特定表

### Word文件

- ✅ 文件存储在本地 `output/` 目录
- ⚠️ 输出文件所有人可读
- 💡 建议：定期清理输出目录

---

## 测试策略

### 单元测试（模块级）

```python
# test_validate.py
def test_validate_plan_data():
    result = validate_plan_data(valid_data)
    assert result == []
    
    result = validate_plan_data(invalid_data)
    assert len(result) > 0
```

### 集成测试（端到端）

```python
# test_full_flow.py
def test_full_workflow():
    # 1. 验证
    # 2. 保存
    # 3. 加载
    # 4. 生成Word
    # 5. 验证输出
```

### UI测试

- 使用NiceGUI的测试工具
- 测试表单提交流程
- 测试AI集成

---

## 部署架构

### 开发环境（本地）

```
PC/Mac
├─ Python环境 (conda)
├─ NiceGUI应用 (app.py)
├─ SQLite数据库 (examples/plan.db)
└─ Word模板 (examples/teacherplan.docx)
```

### 生产环境（服务器/云）

```
互联网
   │
   ├─ NiceGUI应用服务器
   ├─ MySQL数据库服务器
   └─ OpenAI API (或兼容API)
```

### Docker部署

```dockerfile
FROM python:3.9

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

CMD ["python", "app.py"]

# 数据库、API Key等通过环境变量配置
```

---

## 版本演进

### v0.1 - 初始版本
- 基础功能完成
- 单一 minimal_fill.py 文件

### v0.2 - 模块化重构
- **当前版本**
- 拆分为 kg_manager 库
- 增加AI集成
- 完整文档系统

### v0.3（计划）
- HTTP API (FastAPI)
- 命令行工具 (CLI)
- 更多测试覆盖

### v1.0（计划）
- 生产级稳定性
- 性能优化
- 用户权限管理

---

## 相关文档

→ [API 文档](../api/kg_manager.md) - 完整API参考

→ [开发快速开始](../development/quickstart.md) - 环境搭建

→ [集成指南](../development/integration-guide.md) - 集成到其他项目

→ [AI完整指南](../ai-integration/README.md) - AI功能深入
