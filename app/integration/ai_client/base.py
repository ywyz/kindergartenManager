"""AI 客户端基础模块 — 通用 Chat Completions 调用。

所有 AI 调用必须通过此模块，禁止在 service 层直接发 HTTP 请求。

特性：
- httpx.AsyncClient 异步请求，超时 60 秒
- tenacity 重试：最多 3 次，指数退避（2s → 4s → 8s）
- 结构化输出：强制要求 JSON 格式，解析失败抛出 AiParseError
- 4xx/5xx 抛出 AiCallError
- API Key 明文禁止写入日志
"""

import json

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import AiCallError, AiParseError
from app.core.logging import get_logger

logger = get_logger(__name__)

# 强制 JSON 输出的 system prompt 补充说明
_JSON_INSTRUCTION = "\n\n请严格按照要求的 JSON 格式输出，不要输出任何其他内容。"


def _make_retry_decorator():
    """构造 tenacity 重试装饰器：最多 3 次，指数退避 2s → 4s → 8s。"""
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )


async def call_ai(
    messages: list[dict],
    api_base_url: str,
    api_key: str,
    model_name: str = "gpt-4o-mini",
    response_schema: dict | None = None,
    *,
    _client: httpx.AsyncClient | None = None,
) -> dict:
    """发送 Chat Completions 请求，返回解析后的 dict。

    Args:
        messages: 消息列表，格式为 [{"role": "...", "content": "..."}]。
        api_base_url: AI 接口基地址（如 https://api.openai.com/v1）。
        api_key: 明文 API Key（函数内部使用，禁止写日志）。
        model_name: 模型名称（如 gpt-4o-mini、deepseek-chat）。
        response_schema: 期望的 JSON schema（当前仅用于文档约束，不传给 API）。
        _client: 可选的 httpx 客户端（用于测试 Mock，生产环境留空）。

    Returns:
        解析后的 dict（AI 返回的 JSON 内容）。

    Raises:
        AiCallError: HTTP 请求失败（4xx/5xx）或超过重试次数。
        AiParseError: AI 返回内容不是有效 JSON 或缺少必要字段。
    """
    url = api_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }

    async def _do_request(client: httpx.AsyncClient) -> dict:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        except httpx.TimeoutException as exc:
            raise AiCallError(f"AI 请求超时: {exc}") from exc
        except httpx.RequestError as exc:
            raise AiCallError(f"AI 请求网络错误: {exc}") from exc

        if response.status_code >= 400:
            # 提取响应体中的错误描述（脱敏：不含 Authorization header）
            try:
                err_body = response.json()
                # 常见 OpenAI 兼容格式：{"error": {"message": "..."}}
                err_detail = (
                    err_body.get("error", {}).get("message")
                    or err_body.get("message")
                    or err_body.get("detail")
                    or str(err_body)[:200]
                )
            except Exception:
                err_detail = response.text[:200]
            logger.error(
                "AI 接口返回错误",
                extra={
                    "status_code": response.status_code,
                    "url": url,
                    "error_detail": err_detail,
                },
            )
            raise AiCallError(
                f"AI 接口返回 HTTP {response.status_code}: {err_detail}"
            )

        raw_text = response.text
        try:
            body = response.json()
        except Exception as exc:
            logger.info("AI 返回内容解析失败（非 JSON）", extra={"raw": raw_text[:500]})
            raise AiParseError(f"AI 返回内容不是有效 JSON: {exc}") from exc

        # 提取 choices[0].message.content
        try:
            content_str = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.info(
                "AI 响应结构异常，缺少 choices/message/content",
                extra={"raw": raw_text[:500]},
            )
            raise AiParseError(f"AI 响应结构异常: {exc}") from exc

        # 解析 content 为 dict
        try:
            result = json.loads(content_str)
        except json.JSONDecodeError as exc:
            logger.info(
                "AI content 字段不是有效 JSON",
                extra={"content": content_str[:500]},
            )
            raise AiParseError(f"AI content 不是有效 JSON: {exc}") from exc

        if not isinstance(result, dict):
            logger.info("AI 返回内容不是 JSON 对象", extra={"content": content_str[:200]})
            raise AiParseError("AI 返回内容不是 JSON 对象")

        return result

    # 使用带重试的内层函数
    @_make_retry_decorator()
    async def _request_with_retry(client: httpx.AsyncClient) -> dict:
        return await _do_request(client)

    if _client is not None:
        return await _request_with_retry(_client)

    async with httpx.AsyncClient() as client:
        return await _request_with_retry(client)
