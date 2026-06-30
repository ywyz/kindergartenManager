"""面向用户的错误提示格式化。"""

from __future__ import annotations

from app.core.exceptions import AiCallError, AiParseError, ConfigError, CryptoError


def format_user_error(exc: Exception) -> str:
    """将常见业务异常转成可行动的中文提示。"""
    detail = getattr(exc, "message", str(exc))
    if isinstance(exc, ConfigError):
        return f"{detail}。请先进入 AI 配置页保存对应模型的 API 地址、API Key 和模型名称。"
    if isinstance(exc, AiCallError):
        return (
            f"AI 接口调用失败：{detail}。请检查 API Key、API 地址、模型名称和网络连接。"
        )
    if isinstance(exc, AiParseError):
        return (
            f"AI 返回内容解析失败：{detail}。请重试；若持续失败，请检查提示词是否要求模型按指定格式输出。"
        )
    if isinstance(exc, CryptoError):
        return f"Key 解密失败：{detail}。请重新配置对应的 AI Key。"
    return str(exc)
