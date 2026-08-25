"""跨页面纯 UI 辅助函数测试。"""

from app.ui.helpers import mask_api_key


def test_mask_api_key_shows_last_four_for_long_key():
    assert mask_api_key("sk-abcdefghijklmnop") == "sk-****mnop"


def test_mask_api_key_hides_short_key():
    assert mask_api_key("short") == "sk-****"


def test_mask_api_key_shows_last_four_at_threshold():
    assert mask_api_key("12345678") == "sk-****5678"
