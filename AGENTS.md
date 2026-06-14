# 幼儿园教学管理系统 — AI 编程代理指南

## 项目概述

**语言：Python 3.12+**。Monorepo 架构，NiceGUI 主系统 + FastAPI 子系统，Docker Compose AIO 编排。
当前为**单用户模式**（登录功能后续恢复），默认 SQLite，可选 MySQL。

详见：
- 产品需求：[memory-bank/PRD.md](memory-bank/PRD.md)
- 技术栈选型：[memory-bank/tech-stack.md](memory-bank/tech-stack.md)
- 实施计划：[memory-bank/implementation-plan.md](memory-bank/implementation-plan.md)

## 目录结构规范

```
app/
  ui/              # NiceGUI 页面与组件（每个页面独立文件）
  api/             # 对外 REST API
  service/         # 业务逻辑（教案拆分、年龄适配、生成建议）
  repository/      # 数据访问层（SQL 查询封装）
  integration/
    ai_client/     # OpenAI 兼容调用（渐进迁移到 ai-service）
    holiday_client/# 节假日接口（渐进迁移到 holiday-service）
    word_export/   # Word 导出（渐进迁移到 word-service）
  auth/            # JWT、RBAC、密码策略（保留待恢复登录功能）
  core/            # 配置、日志、异常定义、常量、引导
  jobs/            # APScheduler 定时任务
services/          # 子系统（各为独立 FastAPI Docker 容器）
  ai-service/      # AI 调用微服务
  word-service/    # Word 导出微服务
  holiday-service/ # 节假日微服务
alembic/           # 数据库迁移脚本
tests/             # pytest 测试
memory-bank/       # 项目文档（PRD、技术栈、计划）
```

**禁止将所有代码堆入单一大文件**，每个功能模块必须拆分到对应子目录。

## 编写代码前必读

1. 阅读 [memory-bank/PRD.md](memory-bank/PRD.md) 了解业务流程与验收标准
2. 阅读 [memory-bank/tech-stack.md](memory-bank/tech-stack.md) 了解技术选型理由
3. 阅读 [memory-bank/implementation-plan.md](memory-bank/implementation-plan.md) 确认当前所在步骤，按步执行
4. 数据库表结构变更前查阅 `alembic/` 迁移历史，避免字段冲突
5. 写任何代码前查阅 `memory-bank/architecture.md`（若已存在，包含完整数据库结构）
6. 每完成一个重大功能或里程碑后，必须更新 `memory-bank/architecture.md`

## 核心约定

### 数据隔离
所有业务表必须包含以下字段，缺一不可：
```python
tenant_id: int   # 机构（幼儿园）隔离
user_id: int     # 用户隔离
created_at: datetime
updated_at: datetime
```

### 鉴权
- 面向用户：账号密码 + JWT（access token）+ RBAC
- 三种角色：`teacher`（教师）、`teaching_admin`（教研管理员）、`sys_admin`（系统管理员）
- 权限校验统一放在 `app/auth/` 中，不在 UI 层做权限逻辑

### 敏感信息
- AI API Key 入库前必须加密（应用层加密，密钥来自环境变量）
- 页面展示 API Key 时必须脱敏
- 密码使用 Argon2（`passlib`），禁止 MD5/SHA1

### AI 调用
- 统一走 `app/integration/ai_client/`，禁止在 service 层直接发 HTTP 请求
- 必须设置超时与 tenacity 重试（指数退避）
- 返回值强约束 JSON schema，解析失败时记录日志并抛出业务异常

### 节假日判定
- 调用中国法定节假日 API，结果本地缓存
- API 失败时降级（不阻断流程，仅标注"节假日信息不可用"）
- 非工作日：**仅提示，不阻止继续生成**

### Word 导出
- 主方案：`python-docx`（直接操控 XML，支持表格定位与红字标注）
- 备方案：`docxtpl`（仅在主方案无法满足时切换）
- 差异标注：原文与年龄适配改写文逐段比对，差异段落字体颜色设为红色（`RGBColor(255, 0, 0)`）

### 数据库迁移
- 所有 schema 变更必须通过 Alembic 迁移脚本完成
- 禁止在应用启动时自动 `create_all()`（生产环境风险）

### 日志
- 使用结构化 JSON 日志格式
- 关键操作必须记录审计日志：AI 调用、导出、账号变更、权限变更

## 环境配置

配置统一通过 `pydantic-settings` 读取 `.env` 文件：

```
DATABASE_URL=mysql+pymysql://user:pass@host:3306/db
ENCRYPTION_KEY=<随机32字节，用于加密AI Key>
JWT_SECRET=<随机字符串>
JWT_EXPIRE_MINUTES=60
HOLIDAY_API_URL=<节假日API地址>
```

不同环境使用 `.env.dev` / `.env.prod`，禁止将真实密钥提交到仓库。

## 测试规范

- 测试框架：`pytest`
- 每个 service 层函数必须有对应单元测试
- AI 调用、Word 导出、数据库操作使用 mock/fixture 隔离
- 运行命令：`pytest tests/ -v`

## 里程碑与范围边界

| 里程碑 | 内容 |
|--------|------|
| M1 | 原型联调（登录 + 日期计算 + AI拆分） |
| M2 | 首期闭环可用（完整教案流程 + Word导出 + 云端存档） |
| M3 | 稳定性与安全加固 |
| M4 | 上线试运行 |
| M5（二期） | 对外 REST API + 数据库只读视图 |
| M6 | Docker Compose AIO + 子系统拆分 + Caddy HTTPS |
| M7 | 恢复登录与多用户支持 |

## 部署方式

### Docker Compose AIO（生产）
```bash
# 生产模式：Caddy + 主系统 + MySQL
docker compose up -d

# 开发模式：仅主系统 + MySQL（直接暴露端口）
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 本地开发（无 Docker）
```bash
# 默认 SQLite，直接运行
.venv/bin/python -m app.main
```

### 子系统开发
每个子系统在 `services/` 下独立运行或作为 Docker 容器加入编排。

## 常见开发陷阱

1. NiceGUI 的 UI 更新必须在主线程或使用 `ui.run_javascript` / `app.storage` 正确传递状态
2. SQLAlchemy 2 使用 `Session` 时注意异步兼容（NiceGUI 底层 async，repository 层建议用 `AsyncSession`）
3. python-docx 操作中文字体时需显式指定字体名称（如"宋体"），否则可能出现乱码
4. Alembic autogenerate 不能识别所有 SQLAlchemy 特性（如部分约束），迁移后需人工验证 SQL
