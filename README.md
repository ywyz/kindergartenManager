# 🏫 幼儿园每日活动计划系统

幼儿园教学管理子系统，支持 AI 辅助生成一日活动计划、导出 Word 文档、历史记录查看等功能。

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 一日计划 | AI 一键生成晨间活动、晨间谈话、集体活动、区域活动、户外游戏 |
| 教案拆分 | 粘贴原始教案文本，AI 拆分为结构化活动字段 |
| 活动过程修改 | 按年龄段最小化 AI 优化活动过程，差异部分红字标注 |
| Word 导出 | 填充 `templates/teacherplan.docx` 模板，AI 修改部分红字显示 |
| 历史记录 | 查看、重新导出历史计划 |
| 提示词管理 | 6 大分类提示词增删改激活，支持在线测试 |
| 系统设置 | 学期/班级配置、AI API 配置、区域与户外内容设置 |
| 数据库配置 | 首次使用时配置 MySQL 连接信息，支持在线测试 |

---

## 环境要求

- **Python** ≥ 3.12（推荐使用 [uv](https://github.com/astral-sh/uv) 管理）
- **MySQL** ≥ 5.7 或 MariaDB ≥ 10.3
- **操作系统**：Windows 10/11、macOS、Linux 均可

---

## 快速开始

### 方式一：从源码运行（开发者）

```bash
# 1. 克隆仓库
git clone https://github.com/ywyz/kindergartenManager.git
cd kindergartenManager

# 2. 安装依赖
uv sync

# 3. 复制并编辑配置文件
cp .env.example .env
# 编辑 .env，填写 MySQL 连接信息和应用密钥

# 4. 启动应用
uv run python -m app.main
```

浏览器访问：http://localhost:8080

### 方式二：使用打包版本（Windows）

1. 从 [Releases](../../releases) 页面下载最新版 `.zip` 压缩包
2. 解压到任意目录（路径不要含中文或空格）
3. 双击运行 `kindergartenManager.exe`
4. 浏览器会自动打开，**首次运行**会进入「数据库配置」页面
5. 填写 MySQL 连接信息，点击「保存并进入系统」

> **注意**：打包版不含 `.env` 文件，必须通过系统内置的「数据库配置」页面完成初始化配置。

---

## 数据库准备

在 MySQL 中提前创建数据库（表结构会由应用自动创建）：

```sql
CREATE DATABASE kindergarten CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 如需创建专用用户（推荐）
CREATE USER 'kgm_user'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON kindergarten.* TO 'kgm_user'@'%';
FLUSH PRIVILEGES;
```

---

## 配置文件说明（.env）

```env
# 数据库连接
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=kindergarten

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8080
APP_SECRET_KEY=your_random_secret_key   # 用于加密 AI Key，设置后请勿修改

# AI 默认配置（可选，也可在系统设置页面配置）
DEFAULT_AI_URL=https://api.openai.com/v1
DEFAULT_AI_KEY=sk-xxx
DEFAULT_AI_MODEL=gpt-4o
```

> `.env` 文件位于应用程序（或可执行文件）所在目录，不会提交到 Git。
> 使用打包版时，通过系统内置的「数据库配置」页面保存后会自动生成此文件。

---

## AI 接入

系统支持任何 OpenAI 兼容接口，在「系统设置 → AI 配置」中填写：

- **API 地址**：如 `https://api.openai.com/v1`，或 DeepSeek、阿里云百炼等兼容接口
- **API Key**：密钥会加密后存入数据库
- **模型名称**：如 `gpt-4o`、`deepseek-chat`、`qwen-plus` 等

---

## 项目结构

```
kindergartenManager/
├── app/
│   ├── main.py              # NiceGUI 入口 + 路由 + 导航
│   ├── config.py            # 环境变量配置
│   ├── db.py                # PyMySQL 封装 + 自动建表
│   ├── models/
│   │   └── daily_plan.py    # 数据模型
│   ├── pages/
│   │   ├── db_setup.py      # 数据库连接配置页（首次部署）
│   │   ├── settings.py      # 学期/AI/区域内容设置
│   │   ├── daily_plan.py    # 一日计划主页
│   │   ├── lesson_split.py  # 教案拆分
│   │   ├── prompt_mgmt.py   # 提示词管理
│   │   ├── plan_history.py  # 历史记录
│   │   └── startup_check.py # 系统自检
│   └── services/
│       ├── ai_service.py    # AI 调用封装
│       ├── word_export.py   # Word 模板导出
│       ├── plan_service.py  # 计划读写服务
│       ├── date_utils.py    # 日期/周次/节假日工具
│       └── crypto.py        # Fernet 加解密
├── templates/
│   └── teacherplan.docx     # Word 导出模板
├── exports/                 # 导出文件目录
├── .env.example             # 配置示例（复制为 .env 后填写）
└── README.md
```

---

## 常见问题

**Q: 打开后显示 500 错误或无法加载页面？**  
A: 通常是数据库未配置或无法连接。请访问 http://localhost:8080/db-setup 完成配置。

**Q: AI 生成失败？**  
A: 进入「系统设置」检查 AI API 地址和 Key 是否正确，也可前往「系统自检」页面查看各项状态。

**Q: 修改了 APP_SECRET_KEY 后 AI Key 报解密错误？**  
A: 密钥变更后，需在「系统设置 → AI 配置」中重新填写并保存 API Key。

**Q: 如何迁移数据到新服务器？**  
A: 在新服务器的 MySQL 中导入旧库的数据，修改 `.env` 中的数据库地址即可。

---

## 技术栈

- **界面框架**：[NiceGUI](https://nicegui.io/) ≥ 2.0
- **数据库驱动**：PyMySQL
- **AI 接口**：openai SDK（兼容任意 OpenAI 格式接口）
- **Word 生成**：python-docx
- **加密**：cryptography（Fernet）
- **节假日**：chinesecalendar（支持 2004–2026，含调休）
- **包管理**：[uv](https://github.com/astral-sh/uv)
