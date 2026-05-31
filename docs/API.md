# 对外 REST API 参考（v1）

本系统作为「幼儿园信息管理主系统」的子系统，对外提供**只读**的教学计划数据接口，供主系统实时读取。所有端点以 `/api/v1` 为前缀。

- 基础 URL：`https://<host>/api/v1`
- 数据格式：JSON（UTF-8）
- 仅提供 `GET`（只读）

---

## 1. 鉴权

### 1.1 API Key（必填）

每个调用方分配一个 API Key，并在请求头携带：

```
X-Api-Key: <your-api-key>
```

服务端依据配置 `API_KEYS`（`"key:tenant_id"` 映射）解析出该 Key 绑定的 `tenant_id`，**所有查询强制以此 tenant_id 隔离**，调用方无法读取其他租户数据。

> 若服务端未配置 `API_KEYS`，对外接口默认关闭，所有业务端点返回 `401`。

### 1.2 HMAC 签名（可选，强烈建议生产启用）

当服务端配置了 `API_SIGNING_SECRET` 时，所有业务端点**强制**校验签名。请求需额外携带：

```
X-Timestamp: <unix 秒级时间戳>
X-Signature: <hex(hmac_sha256(secret, signing_string))>
```

**待签名串**（`signing_string`）格式：

```
{timestamp}\n{METHOD}\n{path}\n{query}
```

- `METHOD`：大写 HTTP 方法，如 `GET`
- `path`：请求路径，如 `/api/v1/daily-plans`
- `query`：原始查询串（不含 `?`），如 `grade=%E4%B8%AD%E7%8F%AD&limit=10`；无查询参数时为空串
- 时间戳与服务器时间偏差须在 `API_SIGNATURE_MAX_SKEW` 秒内（默认 300），用于防重放

**Python 签名示例**：

```python
import hashlib, hmac, time, httpx

API_KEY = "svc-abc"
SECRET = "topsecret"
BASE = "https://host/api/v1"

def signed_get(path: str, query: str = ""):
    ts = str(int(time.time()))
    msg = f"{ts}\nGET\n/api/v1{path}\n{query}"
    sig = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    headers = {"X-Api-Key": API_KEY, "X-Timestamp": ts, "X-Signature": sig}
    url = f"{BASE}{path}" + (f"?{query}" if query else "")
    return httpx.get(url, headers=headers)

resp = signed_get("/daily-plans", "grade=中班&limit=10")
print(resp.json())
```

### 错误码

| HTTP | 含义 |
|------|------|
| `200` | 成功 |
| `401` | API Key 缺失/无效，或签名校验失败 |
| `404` | 资源不存在（或跨租户访问被隔离） |
| `422` | 查询参数校验失败（如 limit 越界） |

---

## 2. 端点

### 2.1 健康检查

```
GET /api/v1/health
```

免鉴权。响应：

```json
{
  "status": "ok",
  "service": "kindergarten-teaching-api",
  "version": "v1",
  "time": "2026-05-31T08:00:00Z"
}
```

### 2.2 查询每日活动计划（分页）

```
GET /api/v1/daily-plans
```

查询参数（均可选）：

| 参数 | 类型 | 说明 |
|------|------|------|
| `user_id` | int | 按用户（教师）过滤 |
| `start_date` | date(`YYYY-MM-DD`) | 计划日期下界（含） |
| `end_date` | date | 计划日期上界（含） |
| `grade` | str | 年级，如 `小班`/`中班`/`大班` |
| `class_name` | str | 班级名 |
| `limit` | int | 每页条数，1~200，默认 50 |
| `offset` | int | 偏移量，默认 0 |

响应（按 `plan_date` 降序）：

```json
{
  "meta": { "total": 2, "limit": 50, "offset": 0 },
  "items": [
    {
      "id": 12,
      "tenant_id": 1,
      "user_id": 11,
      "plan_date": "2026-03-09",
      "week_number": 2,
      "weekday_cn": "周一",
      "grade": "中班",
      "class_name": "星星班",
      "activity_goal": "...",
      "activity_prep": "...",
      "activity_key": "...",
      "activity_difficult": "...",
      "activity_process_original": "...",
      "activity_process_adapted": "...",
      "morning_activity": "...",
      "indoor_area": "...",
      "outdoor_activity": "...",
      "morning_talk_topic": "...",
      "morning_talk_questions": "...",
      "daily_reflection": "...",
      "created_at": "2026-03-08T10:00:00Z",
      "updated_at": "2026-03-08T10:00:00Z"
    }
  ]
}
```

### 2.3 按 ID 查询单条计划

```
GET /api/v1/daily-plans/{id}
```

返回单个 `DailyPlan` 对象（字段同上 `items[]` 元素）。当 `id` 不存在或属于其他租户时返回 `404`。

### 2.4 查询学期配置

```
GET /api/v1/semesters
```

查询参数：`user_id`（可选）、`active_only`（bool，默认 false，仅返回当前激活学期）。响应：

```json
[
  {
    "id": 3,
    "tenant_id": 1,
    "user_id": 11,
    "semester_name": "2026春季",
    "start_date": "2026-02-23",
    "end_date": "2026-07-01",
    "is_active": true
  }
]
```

### 2.5 查询班级配置

```
GET /api/v1/classes
```

查询参数：`user_id`（可选）。响应：

```json
[
  {
    "id": 5,
    "tenant_id": 1,
    "user_id": 11,
    "grade": "小班",
    "class_name": "阳光班",
    "indoor_areas": "积木区、阅读区",
    "outdoor_content": "攀爬、平衡"
  }
]
```

---

## 3. 服务端配置

在 `.env` 中：

```dotenv
# 多个调用方用逗号分隔，每个 Key 绑定一个 tenant_id
API_KEYS=svc-abc:1,svc-xyz:2
# 启用 HMAC 签名（留空则不校验签名，仅 API Key）
API_SIGNING_SECRET=please-change-me
# 签名时间戳允许偏移（秒）
API_SIGNATURE_MAX_SKEW=300
```

> 生产环境建议同时启用 API Key 与 HMAC 签名，并在反向代理层（Nginx）对 `/api/` 限制来源 IP 与速率。
