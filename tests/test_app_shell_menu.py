"""测试 app_shell 纯函数逻辑。

测试策略：将菜单项生成和显示名逻辑抽为纯函数，脱离 NiceGUI 渲染独立测试。
"""
import pytest

from app.ui.components.app_shell import get_display_name, get_menu_items


class TestGetMenuItems:
    def test_teacher_sees_core_items(self):
        """role=teacher 时，菜单包含业务项和个人项，不含管理项。"""
        items = get_menu_items("teacher")
        keys = [item["key"] for item in items]
        assert "daily-plan" in keys
        assert "homemade-teaching" in keys
        assert "course-review-activity" in keys
        assert "setup" in keys
        assert "profile" in keys
        assert "settings" not in keys
        assert "user-admin" not in keys
        assert "prompts" not in keys

    def test_sys_admin_sees_management_items(self):
        """系统管理员可见系统设置和账号管理。"""
        admin_items = get_menu_items("sys_admin")
        keys = [item["key"] for item in admin_items]
        assert "settings" in keys
        assert "user-admin" in keys
        assert "prompts" in keys

    def test_teaching_admin_sees_prompts_but_not_user_admin(self):
        """教研管理员可维护提示词，但不能管理账号或系统设置。"""
        items = get_menu_items("teaching_admin")
        keys = [item["key"] for item in items]
        assert "prompts" in keys
        assert "user-admin" not in keys
        assert "settings" not in keys

    def test_all_roles_see_core_items(self):
        """所有角色均可见核心教学菜单和个人 AI 配置。"""
        for role in ("teacher", "teaching_admin", "sys_admin"):
            items = get_menu_items(role)
            keys = [item["key"] for item in items]
            assert "daily-plan" in keys, f"role={role} 缺少 daily-plan"
            assert "homemade-teaching" in keys, f"role={role} 缺少 homemade-teaching"
            assert "course-review-activity" in keys, f"role={role} 缺少 course-review-activity"
            assert "setup" in keys, f"role={role} 缺少 setup"
            assert "profile" in keys, f"role={role} 缺少 profile"

    def test_active_item_is_highlighted(self):
        """传入 active='daily-plan' 时，该菜单项 selected=True，其他项 selected=False。"""
        items = get_menu_items("teacher", active="daily-plan")
        selected = [item for item in items if item.get("selected")]
        assert len(selected) == 1
        assert selected[0]["key"] == "daily-plan"

    def test_no_active_means_none_selected(self):
        """不传 active 时，所有菜单项 selected=False。"""
        items = get_menu_items("teacher")
        assert all(not item.get("selected") for item in items)


class TestGetDisplayName:
    def test_returns_display_name_when_set(self):
        """display_name 有值时返回 display_name。"""
        user = {"display_name": "张老师", "username": "zhangsan"}
        assert get_display_name(user) == "张老师"

    def test_falls_back_to_username_when_display_name_none(self):
        """display_name 为 None 时返回 username。"""
        user = {"display_name": None, "username": "zhangsan"}
        assert get_display_name(user) == "zhangsan"

    def test_falls_back_to_username_when_display_name_empty(self):
        """display_name 为空字符串时返回 username。"""
        user = {"display_name": "", "username": "zhangsan"}
        assert get_display_name(user) == "zhangsan"

    def test_missing_display_name_key(self):
        """user dict 中无 display_name 键时返回 username。"""
        user = {"username": "zhangsan"}
        assert get_display_name(user) == "zhangsan"
