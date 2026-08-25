"""当前单用户根路由测试。"""

from unittest.mock import patch

import pytest

from app.ui.pages.root import root_page


@pytest.mark.asyncio
async def test_root_redirects_to_home():
    with patch("app.ui.pages.root.ui.navigate.to") as navigate:
        await root_page()

    navigate.assert_called_once_with("/home")
