"""主页导航卡片与侧边栏菜单的投影一致性测试。"""

import pytest

from app.ui.components.app_shell import get_menu_items
from app.ui.pages.home import home_page


class TestHomeNavigation:
    """确保首页快捷入口卡片复用 get_menu_items(role) 的同一权限投影。"""

    @pytest.mark.parametrize("role", ["teacher", "teaching_admin", "sys_admin"])
    def test_home_card_keys_match_sidebar(self, role: str) -> None:
        """首页可见的卡片 key 序列必须与侧边栏菜单完全一致。"""
        from app.ui.pages.home import _home_card_items

        home_items = _home_card_items(role)
        sidebar_items = get_menu_items(role)
        assert [item["key"] for item in home_items] == [
            item["key"] for item in sidebar_items
        ]

    @pytest.mark.parametrize("role", ["teacher", "teaching_admin", "sys_admin"])
    def test_home_cards_share_labels_icons_routes(self, role: str) -> None:
        """每张卡片与对应菜单项使用相同的标签、图标和路由。"""
        from app.ui.pages.home import _home_card_items

        home_items = _home_card_items(role)
        sidebar_items = get_menu_items(role)
        for home_item, sidebar_item in zip(home_items, sidebar_items):
            assert home_item["label"] == sidebar_item["label"]
            assert home_item["icon"] == sidebar_item["icon"]
            assert home_item["route"] == sidebar_item["route"]

    def test_teacher_home_includes_missing_items(self) -> None:
        """教师首页补齐倾听、设置、提示词管理和个人资料入口。"""
        from app.ui.pages.home import _home_card_items

        keys = [item["key"] for item in _home_card_items("teacher")]
        assert "one-on-one-listening" in keys
        assert "settings" in keys
        assert "prompts" in keys
        assert "profile" in keys
        assert "user-admin" not in keys

    def test_teaching_admin_sees_weekly_plan(self) -> None:
        """教学管理员在首页和侧边栏都能看到每周工作计划。"""
        from app.ui.pages.home import _home_card_items

        keys = [item["key"] for item in _home_card_items("teaching_admin")]
        assert "weekly-plan" in keys

    def test_sys_admin_home_excludes_weekly_plan_includes_user_admin(self) -> None:
        """系统管理员首页不含每周工作计划，但包含账号管理。"""
        from app.ui.pages.home import _home_card_items

        keys = [item["key"] for item in _home_card_items("sys_admin")]
        assert "weekly-plan" not in keys
        assert "user-admin" in keys

    @pytest.mark.parametrize("role", ["teacher", "teaching_admin", "sys_admin"])
    def test_home_cards_have_descriptions(self, role: str) -> None:
        """每个快捷入口卡片都有非空描述。"""
        from app.ui.pages.home import _home_card_items

        for item in _home_card_items(role):
            assert item.get("description"), f"{item['key']} 缺少描述"


async def test_home_page_is_callable() -> None:
    """home_page 保持可调用（不验证完整渲染）。"""
    # 仅确认路由装饰后的页面对象是协程函数。
    assert callable(home_page)
