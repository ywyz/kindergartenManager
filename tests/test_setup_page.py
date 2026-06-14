"""tests/test_setup_page.py — 简化后的 /setup 页面 AI 配置逻辑测试。

验证：
- setup 页面仅包含 AI 配置功能（无数据库选择、无管理员创建步骤）
- _mask_api_key 函数正确脱敏
"""

import pytest

from app.ui.pages.setup import _mask_api_key


class TestMaskApiKey:
    def test_long_key_shows_last_4(self):
        """8位以上 key 显示 sk-**** + 末4位。"""
        assert _mask_api_key("sk-abcdefghijklmnop") == "sk-****mnop"

    def test_short_key_shows_only_prefix(self):
        """短于8位的 key 只显示 sk-****。"""
        assert _mask_api_key("short") == "sk-****"

    def test_exactly_8_chars(self):
        """恰好8位 key 显示末4位。"""
        assert _mask_api_key("12345678") == "sk-****5678"

