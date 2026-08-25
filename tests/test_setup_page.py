"""旧 /setup 路由只保留为 /settings 兼容入口。"""

from unittest.mock import patch

import pytest

from app.ui.pages.setup import setup_page


@pytest.mark.asyncio
async def test_setup_redirects_to_settings():
    with patch("app.ui.pages.setup.ui.navigate.to") as navigate:
        await setup_page()

    navigate.assert_called_once_with("/settings")
