"""跨页面复用的纯 UI 辅助函数。"""

from __future__ import annotations


def clean_filename_part(value: object, fallback: str) -> str:
    """移除文件名片段中的跨平台非法字符和空格。"""
    text = str(value or "").strip() or fallback
    for char in ('/', '\\', ':', '*', '?', '"', '<', '>', '|', " "):
        text = text.replace(char, "")
    return text or fallback


def validate_generation_context(context: dict) -> list[str]:
    """校验依赖班级设置的内容生成上下文。"""
    errors: list[str] = []
    if not str(context.get("grade") or "").strip():
        errors.append("请先在设置页选择年级")
    if not str(context.get("class_name") or "").strip():
        errors.append("请先在设置页填写班级名称")
    if not str(context.get("teacher_name") or "").strip():
        errors.append("请先在设置页填写教师姓名")
    return errors


def format_setting_summary(context: dict) -> str:
    """格式化班级设置摘要。"""
    grade = str(context.get("grade") or "").strip()
    class_name = str(context.get("class_name") or "").strip()
    teacher_name = str(context.get("teacher_name") or "").strip()
    if not grade and not class_name and not teacher_name:
        return "当前设置：未配置"
    class_part = f"{grade} {class_name}".strip() or "未配置班级"
    teacher_part = teacher_name or "未配置教师"
    return f"当前设置：{class_part} / {teacher_part}"


def mask_api_key(plain: str) -> str:
    """脱敏 API Key，仅对较长密钥保留末四位。"""
    if len(plain) >= 8:
        return "sk-****" + plain[-4:]
    return "sk-****"


def validate_image_count(count: int) -> bool:
    """校验单次或单领域图片数量是否在 1 至 3 张。"""
    return 1 <= count <= 3
