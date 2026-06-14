# 子系统目录

此目录存放所有独立微服务子系统。每个子系统是一个独立的 FastAPI 应用，拥有自己的 Dockerfile 和 requirements.txt。

## 子系统规范

### 通用要求
- **框架**：Python FastAPI
- **健康检查**：`GET /health` → `{"status": "ok"}`
- **错误格式**：`{"error": "错误类型", "detail": "详细信息"}`
- **容器化**：独立 Dockerfile + requirements.txt
- **网络**：仅通过 Docker 内部网络与主系统通信，不暴露外部端口

### 目录结构
```
services/
├── ai-service/           # AI 调用服务
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py       # FastAPI 入口
│       └── routers/      # API 路由
├── word-service/         # Word 导出服务
│   └── ...
├── holiday-service/      # 节假日判定服务
│   └── ...
└── README.md             # 本文件
```

### 拆分节奏（渐进式）
1. 先定义接口规范（OpenAPI schema）
2. 创建子系统骨架（Dockerfile + FastAPI 入口 + /health）
3. 将 `app/integration/` 中的逻辑迁移到对应子系统
4. 主系统 `app/integration/` 改为 HTTP 客户端调用子系统
5. 加入 docker-compose.yml 编排
