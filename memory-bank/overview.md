# 幼儿园信息管理系统 — 顶层总览

本系统是面向幼儿园教研场景的 **教学管理平台**，提供日常教学计划生成、游戏观察记录等功能。

---

## 1. 系统定位

| 维度 | 说明 |
|------|------|
| 用户 | 幼儿园教师（当前为单用户模式，登录功能后续开发） |
| 核心价值 | AI 辅助生成日活动计划 → 一键导出标准 Word 模板 |
| 数据范围 | 单用户（默认 tenant_id=1, user_id=1）；后续恢复多用户 |
| 部署方式 | Docker Compose（AIO 编排：主系统 + 子系统 + Caddy + 可选 MySQL） |

---

## 2. 系统架构

### 2.1 整体架构（微服务 + Docker Compose AIO）

```
幼儿园信息管理系统（Monorepo）
├── 主系统（app/）— NiceGUI 前后端一体化
│   ├── 教学管理：一日活动计划、游戏观察记录
│   ├── 配置中心：学期、班级、AI接口、数据库、端口
│   └── 提示词管理
├── 子系统（services/）— 各为独立 FastAPI 容器
│   ├── ai-service/       — AI 调用服务（教案拆分、适配、生成）
│   ├── word-service/     — Word 导出服务
│   ├── holiday-service/  — 节假日判定服务
│   └── （未来扩展：学生出勤管理等）
├── 基础设施
│   ├── Caddy — 反向代理 + 自动 HTTPS
│   └── MySQL（可选）— 生产数据库
└── Docker Compose — AIO 编排
```

### 2.2 通信模式

```
互联网用户
    │
    ▼
  Caddy（HTTPS 反向代理，自动证书）
    │
    ▼
  主系统（NiceGUI，port 8080）
    │ HTTP REST API（Docker 内部网络）
    ├──→ ai-service:8001
    ├──→ word-service:8002
    └──→ holiday-service:8003
    │
    ▼
  数据库（SQLite 本地 / MySQL 容器 / 外部 RDS）
```

### 2.3 子系统接口规范

所有子系统遵循统一规范：

- **协议**：HTTP REST API（JSON）
- **认证**：Docker 内部网络免认证（不暴露外部端口）
- **健康检查**：`GET /health` → `{"status": "ok"}`
- **错误格式**：`{"error": "...", "detail": "..."}`
- **框架**：Python FastAPI
- **容器化**：每个子系统独立 Dockerfile + 独立 requirements.txt

---

## 3. 子系统地图

```
幼儿园信息管理系统
├── 教学管理（主系统）
│   └── 一日活动计划（主模块）
│       ├── 教案 AI 拆分 & 年龄适配 ──→ [ai-service]
│       ├── 一日活动 AI 生成（5 种类型）──→ [ai-service]
│       ├── Word 模板导出（差异标红）──→ [word-service]
│       └── 提示词多版本管理（7 种任务类型）
├── 游戏观察记录
│   ├── 多图上传 + 视觉 AI 生成观察报告 ──→ [ai-service]
│   ├── Word 模板导出 ──→ [word-service]
│   └── 历史查询与重新导出
├── 自制教玩具
│   ├── 读取年级 / 班级 / 教师姓名配置
│   ├── 文本 AI 生成教玩具名称 / 所用材料 / 玩法 ──→ [ai-service]
│   └── Word 模板导出与历史查询 ──→ [word-service]
├── 日历与节假日 ──→ [holiday-service]
│   └── 法定节假日判定、调班检测、特殊节日标签
└── 对外只读 REST API（/api/v1）
    └── 供外部系统读取教学计划数据
```

---

## 4. 角色与权限（当前为单用户模式）

| 角色 | 标识 | 权限 | 状态 |
|------|------|------|------|
| 默认管理员 | `sys_admin` | 所有功能 | ✅ 当前使用 |
| 教师 | `teacher` | 创建/编辑/导出/查看同班计划 | 🔜 登录恢复后启用 |
| 教研管理员 | `teaching_admin` | 管理教学计划与提示词 | 🔜 登录恢复后启用 |

---

## 5. 技术栈一览

| 层次 | 技术选型 |
|------|---------|
| 前后端（主系统） | NiceGUI（基于 FastAPI + uvicorn） |
| 子系统 | Python FastAPI（独立容器） |
| 数据库 | SQLite（默认/开发）、MySQL 8（生产可选）、外部 RDS |
| ORM / 迁移 | SQLAlchemy 2（AsyncSession）+ Alembic |
| 鉴权 | 单用户模式（默认管理员）；JWT/RBAC 模块保留待恢复 |
| AI 调用 | OpenAI 兼容接口（httpx + tenacity 重试） |
| 文档导出 | python-docx（主方案）+ 模板填充 |
| 定时任务 | APScheduler |
| 配置管理 | pydantic-settings（.env 文件） |
| 测试 | pytest + pytest-asyncio（SQLite 内存库 fixture） |
| 日志 | python-json-logger（结构化 JSON） |
| 反向代理 | Caddy（自动 HTTPS + 反向代理） |
| 容器编排 | Docker Compose（AIO 模式） |
| 部署 | Docker Compose（本地开发 + 远程生产） |

---

## 6. 核心约束速查

| 约束 | 说明 |
|------|------|
| 数据隔离 | 所有业务表保留 `tenant_id`、`user_id`、`created_at`、`updated_at` |
| 迁移规范 | 所有 schema 变更通过 Alembic；禁止应用启动时 `create_all()` |
| AI Key 安全 | Fernet 对称加密入库，明文禁止入库/写日志；展示时脱敏 |
| 密码安全 | Argon2（argon2-cffi），禁止 MD5/SHA1/bcrypt |
| 审计日志 | ai_split / ai_generate / export_word 等关键操作 |
| 单用户模式 | 当前无登录，根路径 `/` 重定向 `/home`；`app/auth/` 保留待恢复 |
| 子系统通信 | 主系统通过 Docker 内网 HTTP REST 调用子系统，子系统不暴露外部端口 |

---

## 6. 数据库表清单（Alembic head）

| 表名 | 用途 | 迁移版本 |
|------|------|---------|
| `users` | 账号、角色、密码哈希 | `5e03413fdeca` |
| `semester_config` | 学期配置 | `fd6d29f921b4` |
| `class_config` | 班级配置（年级/班级/教师姓名/室内区域/户外内容） | `67b4aef28796` / `2f7a9c1d4e8b` |
| `ai_api_key` | AI 接口配置（加密存储） | `1a0d0e46f700` / `46b9fd5613c3` |
| `daily_plan` | 每日活动计划（教案拆分+一日活动） | `f6d79ac6bf21` |
| `prompt_template` | 提示词版本管理（含自制教玩具） | `bcd07e51527d` / `e2a3f1b8c9d0` / `c8b6d4e2a931` |
| `export_record` | 导出记录（Word 文件路径） | `d60766786069` / `d5e4f3a2b1c0` |
| `game_observation` | 游戏观察记录 | dev3.0 |
| `game_observation_image` | 观察照片（MySQL BLOB） | dev3.0 |
| `homemade_teaching_toy` | 自制教玩具记录 | `7c1e2a9b5d4f` |

---

## 7. 部署拓扑

### 生产环境（Docker Compose AIO）

```
互联网
  │
  ▼
Caddy（自动 HTTPS + 反向代理）
  │
  ▼
Docker Compose 内部网络（kindergarten_net）
  │
  ├── app（主系统，NiceGUI，:8080）
  │   ├── 页面路由（/home、/daily-plan、/setup、/settings 等）
  │   ├── REST API（/api/v1/*）
  │   └── 调用子系统 via HTTP
  │
  ├── ai-service（AI 服务，FastAPI，:8001）
  │   └── 教案拆分 / 适配 / 生成 / 视觉分析
  │
  ├── word-service（Word 导出，FastAPI，:8002）
  │   └── 模板填充 / 差异标红 / 文件生成
  │
  ├── holiday-service（节假日，FastAPI，:8003）
  │   └── 法定节假日 / 调班 / 特殊节日
  │
  └── db（MySQL 8，可选）
       └── :3306，数据持久化到 volume
```

### 开发环境

```
本地开发（无 Caddy、无 MySQL）
  │
  └── app（主系统，SQLite 内嵌）
      └── 子系统可选：独立运行或 mock
```

---

## 8. Monorepo 目录结构

```
kindergartenManager/                  # 项目根（Monorepo）
├── app/                              # 主系统（NiceGUI）
│   ├── ui/pages/                     # 页面
│   ├── ui/components/                # 组件
│   ├── service/                      # 业务逻辑
│   ├── repository/                   # 数据访问
│   ├── integration/                  # 主系统调用子系统的客户端
│   │   ├── ai_client/               # → ai-service
│   │   ├── word_export/             # → word-service（渐进迁移）
│   │   └── holiday_client/          # → holiday-service（渐进迁移）
│   ├── auth/                         # JWT/RBAC（保留待恢复）
│   ├── core/                         # 配置、数据库、日志、引导
│   ├── api/                          # 对外 REST API
│   └── jobs/                         # 定时任务
├── services/                         # 子系统目录（每个子系统独立子目录）
│   ├── ai-service/                   # AI 调用微服务
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/                      # FastAPI 应用
│   ├── word-service/                 # Word 导出微服务
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/
│   └── holiday-service/              # 节假日微服务
│       ├── Dockerfile
│       ├── requirements.txt
│       └── app/
├── alembic/                          # 数据库迁移
├── templates/                        # Word 模板
├── tests/                            # 主系统测试
├── docker-compose.yml                # AIO 编排（生产）
├── docker-compose.dev.yml            # 开发环境（可选 override）
├── Caddyfile                         # Caddy 反向代理配置
├── Dockerfile                        # 主系统镜像
└── memory-bank/                      # 项目文档
```

---

## 9. 文档导航

| 文档 | 说明 |
|------|------|
| [PRD.md](PRD.md) | 产品需求文档（功能范围、验收标准） |
| [tech-stack.md](tech-stack.md) | 技术栈选型理由 |
| [architecture.md](architecture.md) | 系统架构（基础设施、数据库、子系统接口） |
| [implementation-plan.md](implementation-plan.md) | 分步实施计划 |
| [progress.md](progress.md) | 开发进度日志 |
| [api-integration.md](api-integration.md) | 对外 REST API 集成说明 |
| [daily-plan/design.md](daily-plan/design.md) | 一日活动计划子系统设计文档 |
| [game-observation/design.md](game-observation/design.md) | 游戏观察子系统设计文档 |
| [one-on-one-listening/design.md](one-on-one-listening/design.md) | 一对一倾听子系统设计文档 |
| [homemadeteaching/design.md](homemadeteaching/design.md) | 自制教玩具子系统设计文档 |
| [docs/API.md](../docs/API.md) | 对外 REST API 完整参考 |
| [docs/DEVELOPER.md](../docs/DEVELOPER.md) | 开发者指南 |
| [docs/USER_MANUAL.md](../docs/USER_MANUAL.md) | 用户手册 |
