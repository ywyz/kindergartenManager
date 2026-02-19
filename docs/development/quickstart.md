# 👨‍💻 开发快速开始

为开发者准备的环境搭建和启动指南。

---

## 环境要求

- **Python**: 3.8+
- **操作系统**: Windows / macOS / Linux
- **Git**: 用于版本控制
- **浏览器**: 支持localStorage的现代浏览器

---

## 第一步：克隆项目

```bash
git clone https://github.com/ywyz/kindergartenManager.git
cd kindergartenManager

# 切换到开发分支（如果需要）
git checkout tplan
```

---

## 第二步：创建Python环境

### 方案A：使用conda（推荐）

```bash
# 从yml文件创建环境
conda env create -f environment.yml

# 激活环境
conda activate teacher
```

### 方案B：使用venv

```bash
# 创建虚拟环境
python -m venv venv

# 激活环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install nicegui python-docx openai chinesecalendar
```

---

## 第三步：启动应用

### 方式一：直接运行

```bash
python app.py
```

### 方式二：安装为包后运行

```bash
# 安装kg_manager为可开发包
pip install -e .

# 现在可以在任何地方导入
python -c "import kg_manager as kg; print('✓ 导入成功')"

# 再启动app
python app.py
```

### 访问应用

打开浏览器访问：**http://localhost:8080**

---

## 第四步：验证安装

运行示例代码：

```bash
python examples_usage.py
```

应该看到类似的输出：
```
============================================================
示例 1: 基本工作流
============================================================
✓ 教案数据验证通过
✓ 学期信息已保存：2026-02-23 - 2026-07-10
✓ 最新学期：2026-02-23 - 2026-07-10
✓ 教案已保存：2026-02-26
✓ 教案已加载：2026-02-26
✓ 数据库中的教案日期：['2026-02-26']
...
```

---

## 项目结构

```
kindergartenManager/
├── app.py                      # 🌐 NiceGUI Web应用 (主入口)
├── minimal_fill.py             # 🔄 向后兼容层
├── examples_usage.py           # 📚 使用示例
├── setup.py                    # 📦 包配置
├── environment.yml             # 🐍 conda环境配置
│
├── kg_manager/                 # 📦 核心库
│   ├── __init__.py             #    公共接口
│   ├── models.py               #    数据模型和常量
│   ├── db.py                   #    数据库操作
│   ├── word.py                 #    Word生成
│   ├── validate.py             #    数据验证
│   └── ai.py                   #    AI集成
│
├── examples/                   # 📋 示例资源
│   ├── teacherplan.docx        #    Word模板
│   ├── plan_schema.json        #    表单schema
│   ├── plan.db                 #    教案数据库
│   └── semester.db             #    学期数据库
│
├── output/                     # 📤 Word导出目录
│   └── (生成的Word文件)
│
├── docs/                       # 📚 文档目录
│   ├── README.md               #    文档首页
│   ├── user-guide/             #    用户指南
│   ├── api/                    #    API文档
│   ├── architecture/           #    架构文档
│   ├── ai-integration/         #    AI集成文档
│   ├── development/            #    开发指南
│   ├── changelog/              #    版本日志
│   └── reference/              #    参考资料
│
└── .github/
    └── copilot-instructions.md # 🤖 Copilot配置

```

---

## 常用开发命令

### 启动应用（开发模式）

```bash
python app.py
```

### 运行示例

```bash
# 运行所有示例
python examples_usage.py

# 运行特定测试
python test_full_flow.py
```

### 生成表单schema

```bash
# 更新plan_schema.json
python minimal_fill.py
```

### 安装依赖

```bash
# 安装生产依赖
pip install -r requirements.txt

# 开发依赖（如果有）
pip install -r requirements-dev.txt
```

### 代码检查

```bash
# 检查导入格式
python -m py_compile kg_manager/*.py

# 运行pylint（如果已安装）
pylint kg_manager/
```

---

## 代码规范

### 文件头

```python
"""
模块说明：用一句话描述模块的作用
"""

# 导入标准库
import os
from pathlib import Path

# 导入第三方库
from docx import Document

# 导入本地模块
from .models import FIELD_ORDER
```

### 函数注释

```python
def calculate_week_number(semester_start, target_date):
    """
    根据学期开始日期计算周次
    
    Args:
        semester_start (date): 学期开始日期
        target_date (date): 目标日期
        
    Returns:
        int: 周次数字
        
    Raises:
        ValueError: 如果target_date早于semester_start
    """
    pass
```

### 类型注解（推荐）

```python
from typing import Dict, List, Optional
from datetime import date

def save_plan_data(
    db_path: str,
    date_str: str,
    plan_data: Dict[str, any]
) -> None:
    """保存教案数据"""
    pass

def list_plan_dates(db_path: str) -> List[str]:
    """列出所有教案日期"""
    pass
```

---

## 开发工作流

### 1. 功能开发

```bash
# 创建功能分支
git checkout -b feature/your-feature-name

# 编写代码
# 测试代码
python examples_usage.py

# 提交变更
git add kg_manager/
git commit -m "feat: 添加新功能"

# 推送
git push origin feature/your-feature-name

# 提交Pull Request
```

### 2. Bug修复

```bash
# 创建修复分支
git checkout -b bugfix/issue-name

# 修复问题
# 运行测试验证
python test_full_flow.py

# 提交
git add .
git commit -m "fix: 修复问题描述"

# 提交Pull Request
```

### 3. 文档更新

```bash
# 编辑 docs/ 下的相关文件
# 本地预览（使用Markdown查看器）

git add docs/
git commit -m "docs: 更新文档"
git push
```

---

## 调试技巧

### 1. 检查导入

```bash
# 快速检查导入是否正常
python -c "import kg_manager as kg; print('✓')"
```

### 2. 查看数据库内容

```bash
# 查看SQLite数据库
sqlite3 examples/plan.db

# 在sqlite提示符中
sqlite> SELECT * FROM plan_data;
sqlite> .schema
sqlite> .quit
```

### 3. 调试Word生成

```python
# 在代码中添加调试
from docx import Document

doc = Document('examples/teacherplan.docx')
table = doc.tables[0]

for i, row in enumerate(table.rows):
    print(f"Row {i}: {row.cells[0].text}")
```

### 4. 浏览器控制台调试

在浏览器中按 F12 打开开发者工具：

```javascript
// 查看AI配置
console.log(localStorage.getItem('kg_manager_ai_key'));

// 查看所有配置
for (let i = 0; i < localStorage.length; i++) {
  const key = localStorage.key(i);
  console.log([key, localStorage.getItem(key)]);
}

// 清除配置
localStorage.clear();
```

---

## 常见问题

### 导入错误：ModuleNotFoundError

```
ModuleNotFoundError: No module named 'kg_manager'
```

**解决**：
```bash
# 重新安装包
pip install -e .
```

### Word模板文件未找到

```
FileNotFoundError: examples/teacherplan.docx
```

**解决**：
- 确保在项目根目录运行
- 检查文件是否存在：`ls examples/teacherplan.docx`

### SQLite数据库锁定

```
OperationalError: database is locked
```

**原因**：多个进程同时访问数据库

**解决**：
```bash
# 关闭其他程序，或删除数据库重新创建
rm examples/plan.db
python examples_usage.py  # 会自动创建
```

### localhost拒绝连接

```
ConnectionRefusedError: [Errno 111] Connection refused
```

**解决**：
- 检查app.py是否在运行
- 尝试访问 http://127.0.0.1:8080
- 查看终端输出是否有错误信息

---

## IDE配置

### VS Code

1. 安装Python扩展
2. 选择解释器：Ctrl+Shift+P → Python: Select Interpreter → 选择conda环境
3. 创建 `.vscode/settings.json`:
   ```json
   {
     "python.linting.enabled": true,
     "python.formatting.provider": "black",
     "[python]": {
       "editor.formatOnSave": true
     }
   }
   ```

### PyCharm

1. 新建项目，选择现有目录
2. 配置解释器：Settings → Project → Python Interpreter → 选择conda环境
3. 运行配置：Run → Run... → 创建Python run configuration

---

## 资源链接

- 📖 [完整文档](../README.md)
- 🤖 [AI集成指南](../ai-integration/README.md)
- 📚 [API参考](../api/kg_manager.md)
- 🏗️ [系统架构](../architecture/README.md)
- 🔗 [项目主页](https://github.com/ywyz/kindergartenManager)

---

准备好了吗？开始开发吧！🚀
