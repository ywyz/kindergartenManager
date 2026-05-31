# 幼儿园教学管理系统推荐技术栈（简单且健壮）

## 结论（首推）
采用 **Python 单体应用**：
- 前后端：NiceGUI（基于 FastAPI）
- 数据库：MySQL 8
- ORM 与迁移：SQLAlchemy 2 + Alembic
- 鉴权：JWT + RBAC（角色权限）
- AI 调用：OpenAI 兼容接口（httpx + tenacity 重试）
- 文档导出：python-docx（Word 模板填充与红字标注）
- 部署：Ubuntu + systemd + Nginx（反向代理）
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
- Ubuntu 22.04 LTS
- systemd 托管应用进程
- Nginx 做 HTTPS 与反向代理
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

## 升级路线（不改栈，只扩边界）
1. 阶段 1（现在）
- 单体上线，先做教学管理核心闭环（可用优先）。

2. 阶段 2（稳定后）
- 增加对外 REST API + 数据库只读视图。
- 增加 API Key + 签名鉴权（服务间调用）。

3. 阶段 3（规模增长后）
- 将耗时任务（导出、批量生成）拆到独立 worker。
- 需要时再引入 Redis/Celery，而不是首期提前复杂化。

## 不推荐首期采用的方案
- 微服务 + K8s：运维成本过高，不符合“最简单”。
- Node/Java 多语言混合：团队负担和维护复杂度上升。
- 首期就上消息队列与事件总线：收益小于复杂度。

## 一句话建议
先用 Python 单体（NiceGUI + MySQL + SQLAlchemy + Alembic + python-docx + systemd+Nginx）把系统做稳做通，再在同一代码基线上逐步拆分能力，这是你当前阶段性价比最高的路线。
