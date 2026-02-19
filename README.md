# 幼儿园教案管理系统 (Kindergarten Manager)

## 📖 项目简介

幼儿园教案管理系统是一个基于NiceGUI的Web应用程序，用于创建、管理和导出幼儿园教师教案。

### ✨ 核心特性

- 📝 **可视化表单编辑**: 动态生成教案表单，支持周次、日期自动计算
- 🤖 **AI智能辅助**: 使用OpenAI API自动拆分集体活动原稿
- 💾 **数据库管理**: 支持SQLite本地存储和MySQL云部署
- 📄 **Word文档导出**: 一键生成符合格式要求的Word教案文档
- ⚙️ **配置管理**: 直观的UI配置AI和数据库参数，配置自动保存
- 🔄 **批量导出**: 支持连续日期教案的批量生成

### 🏗️ 系统架构

```
kindergartenManager/
├── app.py                  # NiceGUI Web应用主入口
├── minimal_fill.py         # 向后兼容层（重定向到kg_manager）
├── kg_manager/             # 核心库（可复用的模块化代码）
│   ├── models.py           # 数据模型和常量
│   ├── db.py               # 数据库操作
│   ├── word.py             # Word文档生成
│   ├── validate.py         # 数据验证
│   ├── ai.py               # AI集成
│   └── __init__.py         # 公共API
├── examples/               # 示例文件和模板
│   ├── teacherplan.docx    # Word模板
│   ├── plan_schema.json    # 表单schema
│   ├── semester.db         # 学期数据库（SQLite）
│   └── plan.db             # 教案数据库（SQLite）
└── output/                 # 生成的Word文档输出目录
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 使用conda (推荐)
conda env create -f environment.yml
conda activate kindergarten

# 或使用pip
pip install nicegui python-docx chinesecalendar openai
```

### 2. 启动应用

```bash
python app.py
```

### 3. 访问界面

打开浏览器访问: **http://localhost:8080**

### 4. 配置系统

1. 点击页面顶部的 **⚙️ 系统配置** 展开配置面板
2. 在 **AI配置** 标签页输入OpenAI API密钥
3. 在 **数据库配置** 标签页选择数据库类型（SQLite或MySQL）
4. 点击"保存配置"按钮

---

## 📚 使用指南

### 创建教案

1. **设置学期信息**
   - 输入学期开始和结束日期
   - 点击"保存学期"按钮

2. **填写教案内容**
   - 选择教案日期（自动计算周次）
   - 在各字段填入教案内容
   - （可选）使用"填充测试数据"快速填充示例

3. **使用AI辅助** (可选)
   - 在"集体活动管理原稿"输入框填写活动描述
   - 点击"分割集体活动"按钮
   - AI会自动拆分为：活动主题、活动目标、活动准备、活动重点、活动难点、活动过程

4. **保存或导出**
   - **保存到数据库**: 存储教案数据供后续使用
   - **导出为Word**: 生成符合格式的Word文档（保存在`output/`目录）

### 管理已保存的教案

- **加载教案**: 在"已保存教案日期"下拉框中选择日期 → 点击"加载到表单"
- **导出单个**: 选择日期 → 点击"导出选中日期"
- **批量导出**: 设置起始日期和连续天数 → 点击"连续导出"

---

## ⚙️ 配置说明

### AI配置

| 字段 | 说明 | 示例 |
|------|------|------|
| API Key | OpenAI API密钥（必填） | `sk-proj-...` |
| AI模型 | 使用的模型名称 | `gpt-4o-mini` (默认) |
| API地址 | 自定义API端点（可选） | `https://api.openai.com/v1` |

### 数据库配置

#### SQLite (本地存储)
- **优点**: 无需额外配置，即装即用
- **文件位置**: `examples/plan.db`, `examples/semester.db`
- **适用场景**: 单用户本地使用

#### MySQL (云部署)
- **优点**: 支持多用户、远程访问
- **配置项**:
  - 数据库地址 (Host)
  - 端口 (Port, 默认3306)
  - 数据库名 (Database)
  - 用户名 (Username)
  - 密码 (Password)
- **适用场景**: 团队协作、云部署

### 配置持久化

所有配置自动保存到浏览器localStorage中，下次访问自动恢复。

---

## 🤖 AI功能说明

### 集体活动拆分

使用OpenAI GPT模型将集体活动原稿智能拆分为6个子字段：

**输入**: 
```
小班数学活动《认识圆形》，目标是让幼儿认识圆形，感知其特征...
```

**AI输出**:
- **活动主题**: 小班数学活动《认识圆形》
- **活动目标**: 1. 认识圆形，感知圆形特征...
- **活动准备**: 圆形教具、PPT课件...
- **活动重点**: 理解圆形的基本特征
- **活动难点**: 区分圆形与其他形状
- **活动过程**: 1. 导入环节... 2. 探索环节...

### AI模型支持

默认使用 `gpt-4o-mini`，也可配置为:
- `gpt-4o`
- `gpt-4-turbo`
- `gpt-3.5-turbo`
- 或其他OpenAI兼容的API端点

---

## 📄 Word文档格式

生成的Word文档符合以下格式规范:

- **字体**: 仿宋 12pt (全部内容)
- **段落缩进**: 首行缩进2字符
- **表格**: 19行2列，固定格式
- **自动计算**: 周次和日期自动填充
- **内容标签**: 支持多行分段显示

---

## 🛠️ 开发指南

### 作为库使用

```python
import kg_manager as kg

# 加载学期信息
semester = kg.load_latest_semester("examples/semester.db")

# 保存教案数据
kg.save_plan_data("examples/plan.db", "2026-02-26", plan_data)

# 生成Word文档
kg.fill_teacher_plan(
    "examples/teacherplan.docx",
    "output/教案_2026-02-26.docx",
    semester_start,
    semester_end,
    target_date,
    plan_data
)

# AI拆分
result = kg.split_collective_activity(text, model="gpt-4o-mini")
```

### 安装为Python包

```bash
pip install -e .
```

---

## 📖 文档索引

**所有文档已整理到 [`docs/`](docs/) 目录，按场景分类方便查找。**

### 快速导航

**👤 我是普通用户** → [用户快速开始](docs/user-guide/quickstart.md)  
**👨‍💻 我是开发者** → [开发快速开始](docs/development/quickstart.md)  
**🤖 我要接入AI** → [AI集成完整指南](docs/ai-integration/README.md)  
**📚 我要深入学习** → [完整文档导航](docs/README.md)

### 主要文档
- [系统架构](docs/architecture/README.md)
- [API文档](docs/api/kg_manager.md)
- [系统配置指南](docs/user-guide/config-guide.md)
- [AI接入指南](docs/ai-integration/README.md)
- [开发指南](docs/development/quickstart.md)
- [版本日志](docs/changelog/CHANGELOG.md)

---

## 🔧 技术栈

- **Web框架**: [NiceGUI](https://nicegui.io/) - Python响应式Web UI
- **Word处理**: [python-docx](https://python-docx.readthedocs.io/) - Word文档操作
- **AI集成**: [OpenAI API](https://platform.openai.com/) - GPT模型
- **日历库**: [chinesecalendar](https://github.com/LKI/chinese-calendar) - 中国节假日判断
- **数据库**: SQLite3 (内置) / MySQL (可选)

---

## 📋 系统要求

- **Python**: ≥ 3.8
- **浏览器**: 支持localStorage的现代浏览器 (Chrome, Firefox, Edge, Safari)
- **操作系统**: Windows, macOS, Linux
- **网络**: 使用AI功能需联网访问OpenAI API

---

## 🐛 故障排查

### 应用无法启动
```bash
# 检查依赖安装
pip list | grep -E "nicegui|python-docx|openai"

# 重新安装依赖
pip install -r requirements.txt
```

### AI功能无响应
1. 检查配置中是否输入了有效的API密钥
2. 确认网络可以访问OpenAI服务
3. 查看浏览器控制台错误信息

### 配置未保存
1. 检查浏览器是否启用localStorage
2. 尝试清除浏览器缓存后重新配置
3. 检查浏览器隐私设置是否阻止本地存储

### MySQL连接失败
1. 确认MySQL服务正在运行
2. 检查连接参数（主机、端口、用户名、密码）
3. 验证数据库用户权限

---

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 提交问题
- 使用GitHub Issues报告bug
- 提供详细的复现步骤和错误信息

### 提交代码
- Fork本仓库
- 创建功能分支 (`git checkout -b feature/AmazingFeature`)
- 提交变更 (`git commit -m 'Add some feature'`)
- 推送到分支 (`git push origin feature/AmazingFeature`)
- 提交Pull Request

---

## 📜 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 📞 联系方式

项目地址: [https://github.com/your-username/kindergartenManager](https://github.com/your-username/kindergartenManager)

---

## 🎉 版本历史

### v1.0 (最新)
- ✅ 配置UI完整实现
- ✅ localStorage配置持久化
- ✅ AI配置和数据库配置分离
- ✅ MySQL云数据库支持
- ✅ 完整文档系统

### v0.2
- ✅ 系统模块化重构
- ✅ kg_manager核心库
- ✅ 向后兼容层

### v0.1
- ✅ 基础教案生成功能
- ✅ Word文档导出
- ✅ NiceGUI界面

---

**感谢使用幼儿园教案管理系统！** 🎓
