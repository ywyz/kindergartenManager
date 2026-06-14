# 对外 REST API 集成说明

本系统作为「幼儿园信息管理主系统」的**教学管理子系统**，对外提供只读教学计划数据接口，供主系统实时读取。

完整 API 参考文档见 [docs/API.md](../docs/API.md)。

---

## 1. 适用场景

| 场景 | 说明 |
|------|------|
| 主系统集成 | 幼儿园信息管理主系统通过 API Key 读取指定租户的教学计划数据 |
| 数据看板 | 教研管理人员通过主系统查看各班级每日活动计划 |
| 多系统同步 | 子系统的计划数据实时同步到主系统展示 |

---

## 2. 接口概览

- 基础 URL：`https://<host>/api/v1`
- 数据格式：JSON（UTF-8）
- 仅提供 `GET`（只读）

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/v1/health` | 健康检查 | 免鉴权 |
| GET | `/api/v1/daily-plans` | 分页查询每日活动计划 | API Key（必填）|
| GET | `/api/v1/daily-plans/{id}` | 按 ID 查询单条计划 | API Key（必填）|
| GET | `/api/v1/semesters` | 查询学期配置 | API Key（必填）|
| GET | `/api/v1/classes` | 查询班级配置 | API Key（必填）|

---

## 3. 鉴权方式

### 3.1 API Key（必填）

每个主系统（调用方）分配一个 API Key，在请求头携带：

```
X-Api-Key: <your-api-key>
```

服务端依据配置 `API_KEYS`（格式：`"key1:tenant_id1,key2:tenant_id2"`）解析出该 Key 绑定的 `tenant_id`，**所有查询强制以此 tenant_id 过滤**，调用方无法读取其他租户数据。

> ⚠️ 若服务端未配置 `API_KEYS`，对外接口默认关闭，所有业务端点返回 `401`。

### 3.2 HMAC-SHA256 签名（可选，生产环境强烈建议启用）

当服务端配置了 `API_SIGNING_SECRET` 时，所有业务端点**强制**校验签名。请求需额外携带：

```
X-Timestamp: <unix 秒级时间戳>
X-Signature: <hex(hmac_sha256(secret, signing_string))>
```

**待签名串格式**：
```
{timestamp}\n{METHOD}\n{path}\n{query}
```

- 时间戳与服务器时间偏差须在 `API_SIGNATURE_MAX_SKEW` 秒内（默认 300 秒）

**Python 签名示例**：
```python
import hashlib, hmac, time, httpx

API_KEY = "svc-abc"
SECRET = "your-signing-secret"

ts = str(int(time.time()))
path = "/api/v1/daily-plans"
query = "grade=%E4%B8%AD%E7%8F%AD&limit=10"
signing_string = f"{ts}\nGET\n{path}\n{query}"

sig = hmac.new(SECRET.encode(), signing_string.encode(), hashlib.sha256).hexdigest()

resp = httpx.get(
    f"https://<host>{path}?{query}",
    headers={
        "X-Api-Key": API_KEY,
        "X-Timestamp": ts,
        "X-Signature": sig,
    }
)
```

---

## 4. 租户隔离说明

每个 API Key 绑定唯一 `tenant_id`：
- 调用方**无需**在请求中传递租户标识，服务端从 API Key 自动解析
- 所有查询结果仅返回该租户的数据，越权访问返回 `404`（不暴露其他租户数据的存在）

---

## 5. 主要端点说明

### 5.1 查询每日活动计划列表

```
GET /api/v1/daily-plans
```

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `user_id` | int（可选）| 按教师 ID 过滤 |
| `start_date` | str（可选）| 开始日期，格式 `YYYY-MM-DD` |
| `end_date` | str（可选）| 结束日期，格式 `YYYY-MM-DD` |
| `grade` | str（可选）| 年级，如 `中班` |
| `class_name` | str（可选）| 班级名称，如 `阳光班` |
| `limit` | int（默认20，最大100）| 每页条数 |
| `offset` | int（默认0）| 分页偏移 |

**响应示例**：
```json
{
  "items": [
    {
      "id": 42,
      "user_id": 3,
      "plan_date": "2025-10-08",
      "week_number": 5,
      "weekday_cn": "周二",
      "grade": "中班",
      "class_name": "阳光班",
      "activity_goal": "...",
      "morning_activity": "...",
      "daily_reflection": "..."
    }
  ],
  "meta": {"total": 1, "limit": 20, "offset": 0}
}
```

### 5.2 查询单条计划

```
GET /api/v1/daily-plans/{id}
```

跨租户访问返回 `404`（不泄露他人数据存在性）。

---

## 6. 错误码说明

| HTTP 状态码 | 含义 |
|------------|------|
| 200 | 成功 |
| 401 | API Key 缺失或无效；或签名校验失败 |
| 403 | 签名时间戳超出允许偏差 |
| 404 | 资源不存在或跨租户越权 |
| 422 | 请求参数格式错误 |
| 500 | 服务器内部错误 |

---

## 7. 部署配置

在服务端 `.env` 中配置：

```ini
# API Key 映射（格式：key:tenant_id，多个用逗号分隔）
API_KEYS=svc-abc123:1,svc-def456:2

# 可选：HMAC 签名密钥（配置后所有业务端点强制验签）
API_SIGNING_SECRET=your-random-secret-string

# 可选：签名时间戳最大偏差秒数（默认 300）
API_SIGNATURE_MAX_SKEW=300
```

**安全建议**：
- 生产环境务必配置 `API_SIGNING_SECRET` 防重放攻击
- 通过 Nginx 限制 `/api/v1/*` 路径的来源 IP，仅允许主系统服务器访问
- 定期轮换 API Key，旧 Key 立即失效（修改 `API_KEYS` 配置后重启服务）

---

## 8. 与子系统的关系

```
幼儿园信息管理主系统
    │
    │  GET /api/v1/daily-plans  （X-Api-Key: svc-abc123）
    │
    ▼
教学管理子系统（本系统）
    │
    └── 返回 tenant_id=1 的教学计划数据（只读）
```

本子系统不依赖主系统；主系统通过 API Key 单向读取本子系统数据。
