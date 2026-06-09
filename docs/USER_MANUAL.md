# 幼儿园教学管理系统 — 用户使用手册

**版本**：v1.0 | **更新日期**：2026-06

---

## 目录

1. [系统简介](#1-系统简介)
2. [获取软件](#2-获取软件)
3. [首次配置](#3-首次配置)
4. [Windows 桌面版安装与启动](#4-windows-桌面版安装与启动)
5. [Linux 桌面版安装与启动](#5-linux-桌面版安装与启动)
6. [Docker 服务器版部署](#6-docker-服务器版部署)
7. [基础操作指南](#7-基础操作指南)
8. [常见问题（FAQ）](#8-常见问题faq)

---

## 1. 系统简介

幼儿园教学管理系统是一套面向幼儿园教师和教研管理员的日常教学计划辅助工具，主要功能包括：

- **每日活动计划撰写**：结合教学周、节假日信息，辅助生成晨间活动、区域活动、户外活动建议
- **AI 教案拆分与改写**：将完整教案自动拆分为结构化字段，并支持按年龄段适配改写
- **Word 文档导出**：按标准模板导出教案，差异内容以红字标注
- **云端存档**：所有计划自动保存，支持历史查看与重新下载

**适用角色**：

| 角色 | 权限说明 |
|------|---------|
| 教师 | 创建、编辑、导出自己班级的教学计划 |
| 教研管理员 | 查看、批注所有班级计划，管理 AI 提示词模板 |
| 系统管理员 | 账号管理、系统配置 |

---

## 2. 获取软件

请访问 GitHub Releases 页面下载对应版本：

```
https://github.com/ywyz/kindergartenManager/releases
```

根据您的使用场景选择：

| 使用场景 | 下载内容 |
|---------|---------|
| Windows 个人电脑（单机使用） | `幼儿园教学管理系统.exe` |
| Linux 个人电脑（单机使用） | `幼儿园教学管理系统`（无扩展名） |
| 服务器部署（多人共用） | 使用 Docker 方式，参见第 6 节 |

> **数据库说明**：
> - 桌面版（Windows/Linux）在未配置数据库地址时，自动使用内嵌 SQLite 数据库，数据存储在程序同目录，适合单机单用户使用。
> - 如需多人共用，请配置云端 MySQL 数据库地址（见第 3 节）或使用 Docker 服务器版。

---

## 3. 首次配置

所有版本在首次运行前，都需要在程序目录下创建一个名为 `.env` 的配置文件。

### 3.1 创建 .env 文件

**Windows**：在 `幼儿园教学管理系统.exe` 所在文件夹中，新建一个文本文件，命名为 `.env`（注意没有其他扩展名）。

> 如果 Windows 提示"必须键入文件名"，请先打开记事本，写入内容后选择"另存为"，文件类型选"所有文件"，文件名填 `.env`。

**Linux**：在可执行文件所在目录执行：
```bash
nano .env
```

**Docker**：在 `docker-compose.yml` 所在目录创建 `.env` 文件。

### 3.2 .env 配置内容

将以下内容复制到 `.env` 文件，并按说明修改：

```env
# ── 数据库配置 ────────────────────────────────────────────────────────────
# 留空（注释掉）：使用内嵌 SQLite，适合单机单用户
# 填写：连接云端 MySQL，适合多人共用
# DATABASE_URL=mysql+aiomysql://用户名:密码@数据库主机:3306/数据库名

# ── 安全配置（必填，请务必修改默认值） ───────────────────────────────────
# ENCRYPTION_KEY：用于加密 AI API Key 的密钥，随机32字节字符串
# 生成建议：在浏览器地址栏输入 python -c "import secrets; print(secrets.token_hex(16))"
ENCRYPTION_KEY=请替换为32字节随机字符串例如abc123def456ghi789

# JWT_SECRET：用于用户登录令牌签名，随机字符串
JWT_SECRET=请替换为随机字符串例如my-super-secret-2024

# 令牌有效期（分钟），默认 60 分钟
JWT_EXPIRE_MINUTES=60

# ── 节假日 API ────────────────────────────────────────────────────────────
# 用于判断法定节假日；留空时节假日提示功能降级（不影响主要功能）
HOLIDAY_API_URL=https://timor.tech/api/holiday/info/

# 日志级别：INFO（正常）/ DEBUG（调试）/ WARNING（仅警告）
LOG_LEVEL=INFO
```

> ⚠️ **安全提示**：请务必将 `ENCRYPTION_KEY` 和 `JWT_SECRET` 替换为您自己生成的随机字符串，使用默认值存在安全风险。

### 3.3 生成随机密钥（推荐方式）

如果您的电脑已安装 Python，可在命令行运行：

```bash
python -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_hex(16)); print('JWT_SECRET=' + secrets.token_urlsafe(32))"
```

将输出的两行直接复制到 `.env` 文件中替换对应行。

---

## 4. Windows 桌面版安装与启动

### 4.1 安装步骤

1. 从 GitHub Releases 下载 `幼儿园教学管理系统.exe`
2. 创建一个专用文件夹（如 `D:\幼儿园管理系统\`），将 .exe 移入
3. 在该文件夹中创建 `.env` 文件（参见第 3 节）
4. 文件夹结构应如下：
   ```
   幼儿园管理系统/
   ├── 幼儿园教学管理系统.exe
   ├── .env
   └── exports/          ← 首次运行后自动创建，存放导出的 Word 文件
   ```

### 4.2 启动

双击 `幼儿园教学管理系统.exe`，程序启动后：
1. 出现命令行窗口，显示启动日志（正常现象，请勿关闭）
2. 约 2-3 秒后，默认浏览器自动打开 `http://localhost:8080`
3. 看到登录页面即表示启动成功

### 4.3 Windows Defender 安全警告处理

首次运行时，Windows 可能显示如下提示：

> "Windows 已保护你的电脑"

**这是 PyInstaller 打包程序的常见现象，并非真实威胁。** 处理方式：

1. 点击"**更多信息**"
2. 点击"**仍要运行**"

如果提示持续出现，可将程序所在文件夹加入 Windows Defender 排除列表：
- 打开"Windows 安全中心" → "病毒和威胁防护" → "管理设置" → "添加或删除排除项"

### 4.4 停止程序

关闭命令行窗口，或在命令行窗口按 `Ctrl+C`。

---

## 5. Linux 桌面版安装与启动

### 5.1 安装步骤

```bash
# 1. 下载（替换版本号）
wget https://github.com/ywyz/kindergartenManager/releases/download/v1.0.0/幼儿园教学管理系统

# 2. 创建专用目录
mkdir -p ~/kindergarten-manager
mv 幼儿园教学管理系统 ~/kindergarten-manager/

# 3. 赋予执行权限
chmod +x ~/kindergarten-manager/幼儿园教学管理系统

# 4. 创建 .env 配置文件
cd ~/kindergarten-manager
nano .env   # 参考第 3 节内容填写
```

### 5.2 启动

```bash
cd ~/kindergarten-manager
./幼儿园教学管理系统
```

程序启动后，在终端显示启动日志，约 2-3 秒后浏览器自动打开 `http://localhost:8080`。

如浏览器未自动打开，手动访问：`http://localhost:8080`

### 5.3 后台运行（可选）

如希望关闭终端后继续运行：

```bash
nohup ./幼儿园教学管理系统 > app.log 2>&1 &
echo $! > app.pid   # 保存进程 ID 便于停止

# 停止程序
kill $(cat app.pid)
```

---

## 6. Docker 服务器版部署

适合多人共用场景，需要服务器（Linux）和 Docker 环境。

### 6.1 前置条件

- 安装 Docker：https://docs.docker.com/engine/install/
- 安装 Docker Compose（Docker Desktop 已内置）

### 6.2 部署步骤

```bash
# 1. 下载配置文件（从仓库）
wget https://raw.githubusercontent.com/ywyz/kindergartenManager/main/docker-compose.yml

# 2. 创建 .env 文件（必须包含 ENCRYPTION_KEY 和 JWT_SECRET）
cat > .env << 'EOF'
ENCRYPTION_KEY=请替换为32字节随机字符串
JWT_SECRET=请替换为随机字符串
HOLIDAY_API_URL=https://timor.tech/api/holiday/info/
LOG_LEVEL=INFO

# Docker 数据库配置（以下密码请修改）
MYSQL_ROOT_PASSWORD=kg_root_替换为安全密码
MYSQL_DATABASE=kindergarten_db
MYSQL_USER=kindergarten
MYSQL_PASSWORD=kg_替换为安全密码
EOF

# 3. 启动（首次启动会自动拉取镜像和执行数据库初始化）
docker compose up -d

# 4. 查看启动日志
docker compose logs -f app
```

### 6.3 访问

启动成功后，在服务器防火墙开放 8080 端口，用户通过浏览器访问：

```
http://服务器IP:8080
```

生产环境建议配置 Nginx 反向代理并启用 HTTPS。

### 6.4 数据备份

导出的 Word 文件存储在 Docker 卷 `exports` 中，数据库在卷 `db_data` 中：

```bash
# 备份数据库
docker compose exec db mysqldump -u kindergarten -pkg_替换密码 kindergarten_db > backup_$(date +%Y%m%d).sql

# 查看导出文件
docker compose exec app ls /app/exports/
```

### 6.5 更新版本

```bash
docker compose pull
docker compose up -d
```

---

## 7. 基础操作指南

### 7.1 首次登录

系统默认管理员账号由系统管理员创建后告知您。如您是首次部署的管理员，请参考部署文档创建初始账号。

登录后建议立即修改密码：点击右上角用户名 → "个人设置" → "修改密码"。

### 7.2 配置 AI 接口

教案拆分和 AI 生成功能需要配置 AI API Key：

1. 登录后点击右上角 → "个人设置"
2. 填写 API 地址（如 `https://api.openai.com/v1`）和 API Key
3. 点击"保存"

> 系统支持所有 OpenAI 兼容接口，包括 Azure OpenAI、国内各大模型平台等。

### 7.3 创建每日活动计划

1. 点击左侧导航"每日活动计划"
2. 选择日期（系统自动显示教学周信息和节假日提示）
3. 输入或粘贴教案内容，点击"AI 拆分"自动提取结构化字段
4. 根据需要使用"年龄适配"功能改写活动过程
5. 填写完成后点击"保存草稿"或直接"导出 Word"

### 7.4 导出 Word 文档

1. 在计划页面点击"导出 Word"按钮
2. 浏览器自动下载 `.docx` 文件
3. 年龄适配改写的部分在导出文件中以**红字**标注，便于教研审查

---

## 8. 常见问题（FAQ）

**Q：程序启动后浏览器没有自动打开？**

A：手动在浏览器地址栏输入 `http://localhost:8080`。如仍无法访问，检查命令行窗口是否有报错信息。

---

**Q：提示 "缺少 ENCRYPTION_KEY 配置"？**

A：`.env` 文件中 `ENCRYPTION_KEY` 字段未填写或文件不存在。请参考第 3 节创建并填写 `.env` 文件，确保文件与程序在同一目录。

---

**Q：Windows 提示 "Windows 已保护你的电脑"？**

A：点击"更多信息" → "仍要运行"。这是 Windows 对未经数字签名的新程序的默认警告，不影响程序安全性。

---

**Q：程序端口 8080 被占用？**

A：其他程序正在使用 8080 端口。可以：
- 找到占用程序并关闭
- 或在 `.env` 中添加 `APP_PORT=8081`（Docker 版本）后重启

---

**Q：SQLite 模式下数据存储在哪里？**

A：数据库文件 `kindergarten.db` 存储在程序所在目录。请定期备份此文件。

---

**Q：如何从 SQLite 迁移到 MySQL？**

A：目前需要手动迁移。建议从一开始就使用 MySQL 以避免后续迁移成本。如有迁移需求，请联系技术支持。

---

**Q：AI 功能提示"调用失败"？**

A：请检查：
1. 个人设置中 API Key 是否正确填写
2. API 地址是否可正常访问（可在浏览器中访问测试）
3. API Key 是否有余额/配额

---

**Q：导出的 Word 文件在哪里？**

A：
- 桌面版：程序目录下的 `exports/` 文件夹
- Docker 版：通过界面"导出历史"页面下载，或在服务器 `/app/exports/` 目录查找

---

*如遇到未列出的问题，请联系系统管理员或提交 Issue：https://github.com/ywyz/kindergartenManager/issues*
