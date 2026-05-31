---
applyTo: "app/integration/ai_client/**,app/service/**"
---

# AI 接口调用约定

## 接口标准

使用 OpenAI 兼容 Chat Completions 接口（`/v1/chat/completions`），通过 `httpx` 发送请求，`tenacity` 负责重试。

## 强制要求

1. **统一入口**：所有 AI 调用必须通过 `app/integration/ai_client/`，禁止在 service 层直接发 HTTP 请求
2. **超时设置**：每次调用必须设置 `timeout`（建议 60 秒）
3. **重试策略**：使用 tenacity 指数退避，最多重试 3 次

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_ai(messages: list[dict], schema: dict) -> dict:
    ...
```

4. **结构化输出**：请求必须携带 JSON schema 约束（`response_format` 或 system prompt 强制 JSON），解析失败时抛出业务异常并记录完整原始响应到日志
5. **API Key 安全**：从数据库读取时先解密，解密后的明文只在内存中使用，禁止打印到日志

## 教案拆分输出 Schema

```json
{
  "活动目标": "string",
  "活动准备": "string",
  "活动重点": "string",
  "活动难点": "string",
  "活动过程": "string"
}
```

## 年龄适配改写

- 改写后必须同时保存原文（`process_original`）与改写文（`process_adapted`）
- 两者均入库，供后续导出时差异标红使用

## 一日活动生成输入上下文

向 AI 传递以下上下文字段：
- `week_number`（第几周）
- `weekday`（周几，中文）
- `near_holiday`（是否临近节假日，bool）
- `indoor_areas`（室内区域内容描述）
- `outdoor_content`（户外内容描述）
- `grade`（年级）
- `class_name`（班级）
