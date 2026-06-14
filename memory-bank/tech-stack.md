# 幼儿园教学管理系统推荐技术栈（简单且健壮）

## 结论（首推）
采用 **Python 单体应用**：
- 前后端：NiceGUI（基于 FastAPI）
- 数据库：MySQL 8
- ORM 与迁移：SQLAlchemy 2 + Alembic
- 鉴权：JWT + RBAC（角色权限）
- AI 调用：OpenAI 兼容接口（httpx + tenacity 重试）
- 文档导出：python-docx（Word 模板填充与红字标注）
- 部署：Docker Compose AIO（Caddy 反向代理 + 自动 HTTPS）
- 任务调度：APScheduler（先替代消息队列，降低复杂度）
- 测试：pytest
- 配置管理：pydantic-settings（.env 分环境）

这套方案在你的需求下是“最简单且足够健壮”的平衡点：
- 简单：一个代码仓库、一个服务进程、一个主数据库，学习与运维成本最低。
- 健壮：有数据库迁移、权限控制、重试机制、可观测日志、可回滚部署。
- 可升级：后续可平滑拆分 API 服务、任务服务、报表服务，不需要推倒重写。

## 为什么是这套
1. 与当前需求高度匹配
- 你核心是 NiceGUI 页面 + AI 调用 + Word 导出 + MySQL 存储。
- Python 生态对这些能力都成熟，且集成成本低。

2. 复杂度可控
- 不引入微服务、K8s、复杂消息系统，首期上线更快。
- 先保证“能稳定使用”，再扩展对外 API 与系统集成。

3. 后期升级路径清晰
- 当前单体保留清晰分层（ui/service/repository/integration）。
- 将来可把对外 API、异步任务、报表导出独立出来。

## 最小可落地版本（建议直接按此启动）

### 1) 运行时与框架
- Python 3.14（生产环境实际版本，开发环境与云端一致）
- NiceGUI（UI）
- FastAPI（由 NiceGUI 生态直接复用）
- Uvicorn（ASGI 服务器）

### 2) 数据层
- MySQL 8
- SQLAlchemy 2（ORM）
- Alembic（迁移）
- 关键约束：所有业务表包含 tenant_id、user_id、created_at、updated_at

### 3) 安全层
- 密码哈希：Argon2（argon2-cffi，替代 passlib；Python 3.13+ 移除了 crypt 模块，passlib 在 3.14 下崩溃）
- 登录态：JWT（短期 access token + 可选 refresh token）
- 权限：RBAC（教师、教研管理员、系统管理员）
- AI Key：应用层 Fernet 对称加密后入库（密钥来自环境变量，不落库）

### 4) AI 与外部依赖
- HTTP 客户端：httpx
- 重试与超时：tenacity（指数退避）
- 节假日 API：本地缓存 + 失败降级（避免外部接口波动影响主流程）

### 5) 文档导出
- python-docx 作为主方案
- docxtpl 保留为备选
- 差异标红：基于“原活动过程 vs 年龄适配后活动过程”逐段比对后写入红色字体

### 6) 部署与运维
- Docker Compose AIO 编排（本地开发 + 远程生产）
- Caddy 做 HTTPS 终止与反向代理（替代 Nginx，自动证书管理）
- 日志：JSON 格式（便于后续接日志平台）
- 备份：MySQL 每日备份 + 导出文件目录定期归档

## 目录结构建议（单体但可演进）

```text
app/
  ui/                 # NiceGUI 页面与组件
  api/                # 预留：后续对外 API（首期可先内部使用）
  service/            # 业务逻辑（教案拆分、年龄适配、生成建议）
  repository/         # 数据访问层
  integration/
    ai_client/        # OpenAI 兼容调用
    holiday_client/   # 节假日接口
    word_export/      # Word 导出
  auth/               # JWT、RBAC、密码策略
  core/               # 配置、日志、异常、常量
  jobs/               # APScheduler 定时任务
alembic/
tests/
```

## 演进路线（渐进式微服务化）

### 阶段 1（已完成）— 单体上线
- NiceGUI 单体应用，教学管理核心闭环。
- 默认 SQLite，可选 MySQL。单用户模式。

### 阶段 2（当前）— Docker Compose AIO + 子系统拆分
- Docker Compose 编排：主系统 + Caddy + 可选 MySQL。
- 渐进式拆分 `app/integration/` 为独立 FastAPI 子系统容器。
- 子系统顺序：holiday-service → ai-service → word-service。
- Caddy 替代 Nginx，提供自动 HTTPS。

### 阶段 3（后续）— 功能扩展
- 恢复登录与多用户。新增子系统（学生出勤等）。

### 阶段 4（规模增长后）
- 如需引入 Redis/Celery 或 Kubernetes。

## 不推荐当前采用的方案
- Kubernetes：Docker Compose 满足当前需求。
- 多语言混合：统一 Python 降低维护成本。
- 消息队列/事件总线：当前收益不足。

## 一句话建议
Docker Compose AIO 编排 Python 微服务（NiceGUI 主系统 + FastAPI 子系统 + Caddy），Monorepo 渐进式拆分，是当前阶段最优路线。
