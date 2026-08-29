# KindergartenManager 用户手册

## 1. 使用前须知

应用启动后进入 `/login`，业务页面按当前 active 用户隔离。全新空库不会匿名注册或自动创建默认管理员；
首次管理员必须在应用主机上通过受控命令显式初始化。

- Windows/Linux 打包版默认用于本机使用。
- 源码和 Docker 模式可能监听局域网；即使已有登录，也不要在未配置 TLS、强密码和网络访问控制时直接暴露公网。
- 系统可以不配置 AI 使用手工编辑/历史能力；AI 生成需要配置相应文本或视觉模型。
- 幼儿姓名、图片和导出 Word 是敏感数据，请使用受控设备和目录。

## 2. 启动

### 源码

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.main
```

打开 `http://localhost:8080`。

全新空库不会自动创建默认管理员。先在应用主机显式运行：

```bash
.venv/bin/python -m app.jobs.bootstrap_admin --init
```

按安全提示提供首次管理员信息后，再从 `/login` 登录；仓库不再提供源码已知的默认密码。

### Docker

```bash
cp .env.example .env
# 填写已解析到本机的 CADDY_DOMAIN，并用密码管理器填写
# MYSQL_ROOT_PASSWORD、MYSQL_PASSWORD，
# 并固定 ENCRYPTION_KEY、JWT_SECRET；MySQL 密码使用十六进制随机值。
docker compose up -d
docker compose exec app python -m app.jobs.bootstrap_admin --init
```

初始化命令会交互读取管理员密码且不回显。Compose 会在缺少生产域名或数据库密码时失败关闭；域名必须
先通过 DNS 解析到部署主机，并允许 Caddy 使用 80/443 端口自动申请和续期 HTTPS 证书。生产或共享环境
还必须固定加密/JWT 密钥、保留 `app_data`、`db_data` 与 `exports` 卷，并限制 UI 的网络访问。

### Windows/Linux 安装包

从与目标版本 tag 对应的 GitHub Release 获取。首次运行可能需要允许防火墙/Defender 提示；应核对发布来源和版本。

Windows 安装版在安装结束时先不要启动应用；若已自动启动请关闭，再在 PowerShell 中运行（便携包则在解压目录运行同名程序）：

```powershell
cd "$env:ProgramFiles\KindergartenManager"
.\KindergartenManager.exe --init
```

Linux 便携包在解压目录运行：

```bash
./KindergartenManager --init
```

Debian 安装版需要先停服务，再复用 systemd 的受保护配置运行同一个初始化入口：

```bash
sudo systemctl stop kindergarten-manager
sudo systemd-run --wait --pty --collect \
  --property=User=kindergarten-manager \
  --property=EnvironmentFile=/etc/kindergarten-manager/env \
  --property=WorkingDirectory=/var/lib/kindergarten-manager \
  /opt/kindergarten-manager/KindergartenManager --init
sudo systemctl start kindergarten-manager
```

以上初始化方式都交互读取密码，不要把管理员密码写入 URL、命令参数、脚本或聊天记录。完成后从
`http://localhost:8080/login` 登录。

## 3. 首次配置

### 3.1 学期和班级

进入“配置中心 → 学期班级配置”：

1. 填写学期名称、开始日期和结束日期。
2. 填写年级、班级名称和教师姓名。
3. 按需填写室内区域和户外内容。
4. 保存后回到首页。

这些配置会作为生成上下文；保存业务记录时会复制必要快照，因此以后修改设置不会自动改写历史记录。

### 3.2 AI 接口

进入“配置中心 → 学期班级配置”（`/settings`）的 AI 配置区。旧 `/setup` 只会跳转到这里：

1. 填写 OpenAI 兼容 API Base URL。
2. 填写 API Key。
3. 填写模型名称。
4. 选择/确认文本或视觉类型，测试连接后保存。

API 地址、模型名和 Key 按当前 tenant + user 保存到数据库，Key 以应用密钥加密，保存后只显示脱敏值；正常
重启不需要重填。文本模型用于计划、自制教玩具和课程审议；视觉模型用于游戏观察和一对一倾听。要跨
worktree 复用，必须同时保留同一非生产数据库和原 `ENCRYPTION_KEY`；不要把明文 AI Key 写进仓库 `.env`。

### 3.3 提示词

进入“AI 提示词管理”，选择任务类型，新建版本并设为 active。回滚会切换到历史版本，不应删除历史。

## 4. 每日活动计划

1. 进入“教学管理 → 每日活动计划”。
2. 选择日期，核对周次、星期和节假日提示。
3. 粘贴教案，使用 AI 拆分，或手工填写各字段。
4. 按年龄适配活动过程，并核对原文/适配稿。
5. 生成或手工填写晨间、谈话、区域、户外和反思。
6. 保存记录。
7. 导出 Word，并在 Microsoft Word/LibreOffice 中检查内容和差异红字。

AI 或节假日接口失败时，保留已输入内容，按提示重试或继续手工编辑。

## 5. 游戏观察

1. 选择日期、环境、区域和人员信息。
2. 上传 1–3 张图片。
3. 使用视觉 AI 生成观察目标、记录、评价和支持策略。
4. 人工检查并编辑。
5. 保存后可在历史区查询、查看和重新导出。

不要上传无关或不应发送给外部 AI 的幼儿图片。

## 6. 一对一倾听

1. 填写幼儿、年级、学期、班级和观察者。
2. 在健康、语言、社会、艺术、科学五个领域分别设置年月和三个工作日。
3. 每领域上传 3 张图片，或一次导入至少 15 张并自动分配。
4. 单领域生成，或按顺序生成全部领域。
5. 核对目标、图片描述、指标星级、综合评价和支持策略。
6. 保存；在历史区查看、编辑覆盖或删除。
7. 选择合并导出、按领域导出或批量按领域导出。

导出后重点检查图片横版、日期、中文、指标打勾位置和分页。

## 7. 自制教玩具

1. 确认设置中已有年级、班级和教师。
2. 进入“自制教玩具”。
3. 输入需求并生成名称、材料、玩法。
4. 人工编辑后保存和导出。
5. 历史记录可重新查看/导出。

## 8. 课程审议

1. 填写活动名称、人数、时间和原始教案。
2. 生成拆分内容与审议调整。
3. 核对是否调整、调整理由和二次修改稿。
4. 保存并导出固定模板。
5. 历史区支持查看、重新导出和删除。

## 9. 数据位置与备份

- 源码/开发模式未设置 `DATABASE_URL` 时，使用启动工作目录下的 `kindergarten.db`；打包模式使用系统用户数据
  目录（Windows `%LOCALAPPDATA%\KindergartenManager`，Linux `~/.local/share/KindergartenManager` 或
  `$XDG_DATA_HOME/KindergartenManager`，macOS `~/Library/Application Support/KindergartenManager`）。
- 自动生成的 `ENCRYPTION_KEY`/`JWT_SECRET` 位于同一数据根下 owner-only 的 `.kindergarten_secrets`。
- Word 位于运行时导出目录。
- Docker 数据位于命名 volume。

备份应同时覆盖数据库、密钥和必要导出。应用运行中不要直接复制 SQLite 文件作为唯一备份；在正式备份流程建立前，先停止应用或使用 SQLite 一致快照工具。

## 10. 常见问题

### 页面能打开但保存失败

查看日志中的数据库迁移/连接错误。当前启动迁移失败会 fail closed；必须先修复数据库或迁移问题。

### AI 提示未配置 Key

到 `/settings` 配置对应的文本/视觉模型；确认 URL、模型名和 Key 类型。

### 节假日信息不可用

系统允许继续操作，但日期需要人工核对。

### Word 格式不正确

确认 `templates/` 中对应模板存在；使用实际 Word/Office 打开核对，并记录版本和问题截图。

### 如何退出或切换账号

使用侧边栏“退出登录”。退出或在另一标签重新登录后，旧页面的保存、AI、导出和删除操作会因 session 已变化
而拒绝；请在新会话页面重新发起操作。

## 11. 反馈问题时提供

- 应用版本/tag 和 Git SHA（如可见）。
- 操作系统、安装方式、数据库类型。
- 复现步骤、期望和实际结果。
- 已脱敏的日志片段和截图。
- 不要发送真实 API Key、数据库密码或不必要的幼儿隐私数据。
