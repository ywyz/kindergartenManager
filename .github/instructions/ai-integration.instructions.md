---
applyTo: "app/integration/ai_client/**,app/service/**"
---

# AI 接口调用约定

## 适用范围与接口

本文件约束幼儿园系统内部的 AI service，不约束开发工具 Codex 的模型或 API。
AI 调用经 `app/integration/ai_client/`，service 层不直接发送 HTTP；保留各用例的输入、输出与错误契约。

- 常规文本/视觉客户端使用现有 OpenAI-compatible Chat Completions/httpx 集成；是否重试、次数和超时按具体客户端契约，不能一律增加重试。
- `app/service/agent/` 与 `agent_provider.py` 受 ADR-0005、`docs/design/agent-runtime.md` 和 Foundation tests 约束：一次 Provider 调用只发一次请求、不自动重试，超时/取消由 Runtime 控制。
- JSON 用例保留其结构化输出校验，纯文本和 Tool 用例保留各自响应格式；解析失败返回净化的业务异常。
- Key 短命解密并仅在内存使用。日志不得记录原始请求/响应、system Context、Tool 参数、凭据或敏感业务正文；Agent 诊断只使用契约允许的阶段/原因枚举与状态码。

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

- 每日计划改写后必须同时保存原文（`activity_process_original`）与改写文（`activity_process_adapted`）
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
