"""tests/test_observation_ui_helpers.py — 游戏观察 UI 工具函数测试。

测试覆盖（3 项纯函数）：
  1. 导出文件名规则：{tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx
  2. 大环境值校验：只允许 户外/室内/公共，其他值校验失败
  3. 图片数量校验：0 张 → 校验失败；1~3 张 → 通过；>3 张 → 失败
"""

import pytest

from app.ui.pages.game_observation import (
    build_export_filename,
    validate_big_env,
    validate_image_count,
)


# ---------------------------------------------------------------------------
# 1. 导出文件名规则
# ---------------------------------------------------------------------------


def test_build_export_filename_format():
    """文件名格式为 {tenant_id}_{user_id}_{grade}_{class_name}_{obs_date}_游戏观察.docx。"""
    name = build_export_filename(
        tenant_id=1,
        user_id=42,
        grade="大班",
        class_name="阳光班",
        obs_date="2026-06-10",
    )
    assert name == "1_42_大班_阳光班_2026-06-10_游戏观察.docx"


# ---------------------------------------------------------------------------
# 2. 大环境校验
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("valid", ["户外", "室内", "公共"])
def test_validate_big_env_valid_values(valid):
    """户外/室内/公共 均通过校验。"""
    assert validate_big_env(valid) is True


@pytest.mark.parametrize("invalid", ["室外", "半室内", "", "   ", "unknown"])
def test_validate_big_env_invalid_values(invalid):
    """非法大环境值校验失败（返回 False 或抛异常）。"""
    result = validate_big_env(invalid)
    assert result is False


# ---------------------------------------------------------------------------
# 3. 图片数量校验
# ---------------------------------------------------------------------------


def test_validate_image_count_zero_fails():
    """0 张图片 → 校验失败。"""
    assert validate_image_count(0) is False


@pytest.mark.parametrize("count", [1, 2, 3])
def test_validate_image_count_valid_range(count):
    """1~3 张图片 → 通过。"""
    assert validate_image_count(count) is True


def test_validate_image_count_four_fails():
    """超过 3 张 → 校验失败。"""
    assert validate_image_count(4) is False
