# 幼儿园信息管理系统 — 顶层总览

本系统是面向幼儿园教研场景的 **SaaS 式教学管理平台**，提供日常教学计划生成、游戏观察记录、账号管理及对外数据接口等功能。

---

## 1. 系统定位

| 维度 | 说明 |
|------|------|
| 用户 | 幼儿园教师、教研管理员、系统管理员 |
| 核心价值 | AI 辅助生成日活动计划 → 一键导出标准 Word 模板 |
| 数据范围 | 多租户（`tenant_id` 硬隔离）；首期每个幼儿园为一个租户 |
| 部署方式 | Ubuntu 服务器 + systemd + Nginx 反向代理 |

---

## 2. 子系统地图

```
幼儿园信息管理系统
├── 教学管理
│   └── 一日活动计划（主模块）
│       ├── 教案 AI 拆分 & 年龄适配
│       ├── 一日活动 AI 生成（5 种类型）
│       ├── Word 模板导出（差异标红）
│       └── 提示词多版本管理（7 种任务类型）
├── 游戏观察记录（dev3.0）
│   ├── 多图上传 + 视觉 AI 生成观察报告
│   ├── Word 模板导出（ObservationRecord.docx）
│   └── 历史查询与重新导出
├── 账号与鉴权
│   ├── 登录（账号密码 + JWT）
│   ├── 自助注册（邀请码 + 管理员审核）
│   ├── 个人资料（显示名管理）
│   └── 系统管理（用户列表、邀请码管理）
└── 对外只读 REST API（二期，/api/v1）
    └── 供幼儿园信息管理主系统读取教学计划数据
```

---

## 3. 角色与权限

| 角色 | 标识 | 权限 |
|------|------|------|
| 教师 | `teacher` | 创建/编辑/导出/查看同班计划与游戏观察；不可跨班 |
| 教研管理员 | `teaching_admin` | 可查看/编辑/批注教学计划；可管理提示词 |
| 系统管理员 | `sys_admin` | 账号管理、邀请码生成、系统配置 |

---

## 4. 技术栈一览

| 层次 | 技术选型 |
|------|---------|
| 前后端 | NiceGUI（基于 FastAPI + uvicorn） |
| 数据库 | MySQL 8（云端），开发/测试使用 SQLite |
| ORM / 迁移 | SQLAlchemy 2（AsyncSession）+ Alembic |
| 鉴权 | JWT（HS256，python-jose）+ RBAC + Argon2（argon2-cffi） |
| AI 调用 | OpenAI 兼容接口（httpx + tenacity 重试） |
| 文档导出 | python-docx（主方案）+ 模板填充 |
| 定时任务 | APScheduler |
| 配置管理 | pydantic-settings（.env 文件） |
| 测试 | pytest + pytest-asyncio（SQLite 内存库 fixture） |
| 日志 | python-json-logger（结构化 JSON） |
| 部署 | Docker / systemd + Nginx |

---

## 5. 核心约束速查

| 约束 | 说明 |
|------|------|
| 数据隔离 | 所有业务表必须包含 `tenant_id`、`user_id`、`created_at`、`updated_at` |
| 迁移规范 | 所有 schema 变更通过 Alembic；禁止应用启动时 `create_all()` |
| AI Key 安全 | Fernet 对称加密入库，明文禁止入库/写日志；展示时脱敏 |
| 密码安全 | Argon2（argon2-cffi），禁止 MD5/SHA1/bcrypt |
| 审计日志 | login_success / change_password / ai_split / ai_generate / export_word |
| 路由守卫 | `AuthMiddleware` 统一鉴权，`/`、`/register`、`/setup` 为白名单 |

---

## 6. 数据库表清单（Alembic head）

| 表名 | 用途 | 迁移版本 |
|------|------|---------|
| `users` | 账号、角色、密码哈希 | `5e03413fdeca` |
| `invite_code` | 邀请码（自助注册） | dev3.0 |
| `semester_config` | 学期配置 | `fd6d29f921b4` |
| `class_config` | 班级配置（年级/室内区域/户外内容） | `67b4aef28796` |
| `ai_api_key` | AI 接口配置（加密存储） | `1a0d0e46f700` / `46b9fd5613c3` |
| `daily_plan` | 每日活动计划（教案拆分+一日活动） | `f6d79ac6bf21` |
| `prompt_template` | 提示词版本管理（7+1 种任务类型） | `bcd07e51527d` / `e2a3f1b8c9d0` |
| `export_record` | 导出记录（Word 文件路径） | `d60766786069` |
| `game_observation` | 游戏观察记录 | dev3.0 |
| `game_observation_image` | 观察照片（MySQL BLOB） | dev3.0 |

---

## 7. 部署拓扑

```
互联网
  │
  ▼
Nginx（HTTPS 终止 + 反向代理）
  │
  ▼
NiceGUI 应用（uvicorn，port 8080）
  │
  ├── 页面路由（/、/home、/daily-plan、/setup 等）
  │    └── AuthMiddleware（JWT 校验）
  │
  ├── REST API（/api/v1/*）
  │    └── API Key + 可选 HMAC 签名鉴权
  │
  └── 数据库（MySQL 8 云端实例）
       └── 多租户隔离（tenant_id 字段）
```

---

## 8. 文档导航

| 文档 | 说明 |
|------|------|
| [PRD.md](PRD.md) | 产品需求文档（功能范围、验收标准） |
| [tech-stack.md](tech-stack.md) | 技术栈选型理由 |
| [architecture.md](architecture.md) | 系统架构（基础设施、账号鉴权、AI Key 等） |
| [implementation-plan.md](implementation-plan.md) | 分步实施计划（阶段 0~3） |
| [progress.md](progress.md) | 开发进度日志（阶段 0~3） |
| [api-integration.md](api-integration.md) | 对外 REST API 集成说明 |
| [daily-plan/design.md](daily-plan/design.md) | 一日活动计划子系统设计文档 |
| [daily-plan/progress.md](daily-plan/progress.md) | 一日活动计划子系统开发进度（阶段 4+） |
| [game-observation/design.md](game-observation/design.md) | 游戏观察子系统设计文档 |
| [game-observation/progress.md](game-observation/progress.md) | 游戏观察子系统开发进度 |
| [docs/API.md](../docs/API.md) | 对外 REST API 完整参考 |
| [docs/DEVELOPER.md](../docs/DEVELOPER.md) | 开发者指南 |
| [docs/USER_MANUAL.md](../docs/USER_MANUAL.md) | 用户手册 |
