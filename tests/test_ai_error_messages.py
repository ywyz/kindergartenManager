"""UI 错误提示格式化测试。"""

from app.core.exceptions import AiCallError, AiParseError, ConfigError, CryptoError


def test_config_error_message_points_to_ai_config():
    from app.ui.error_messages import format_user_error

    msg = format_user_error(ConfigError("尚未配置文本模型 API Key"))

    assert "AI 配置" in msg
    assert "尚未配置文本模型 API Key" in msg


def test_ai_call_error_message_mentions_network_or_key():
    from app.ui.error_messages import format_user_error

    msg = format_user_error(AiCallError("HTTP 401"))

    assert "AI 接口调用失败" in msg
    assert "API Key" in msg


def test_ai_parse_error_message_mentions_prompt_or_model():
    from app.ui.error_messages import format_user_error

    msg = format_user_error(AiParseError("缺少字段"))

    assert "AI 返回内容解析失败" in msg
    assert "提示词" in msg


def test_crypto_error_message_mentions_reconfigure_key():
    from app.ui.error_messages import format_user_error

    msg = format_user_error(CryptoError("解密失败"))

    assert "Key 解密失败" in msg
    assert "重新配置" in msg
