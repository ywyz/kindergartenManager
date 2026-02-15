"""
数据验证与转换模块
"""

import json
from pathlib import Path
from datetime import date
from .models import FIELD_ORDER, SUBFIELDS


def validate_plan_data(plan_data):
    """
    验证教案数据完整性
    
    Args:
        plan_data: 教案数据字典
        
    Returns:
        错误列表，若无错误则为空列表
    """
    errors = []

    for field, required in FIELD_ORDER:
        # 跳过自动计算的字段
        if field in {"周次", "日期"}:
            continue
        
        value = plan_data.get(field)
        
        # 检查必填字段
        if required and not value:
            errors.append(f"缺少必填字段：{field}")
            continue
        
        # 检查分组字段的结构
        if field in SUBFIELDS and value:
            if not isinstance(value, dict):
                errors.append(f"字段类型错误：{field} 需要字典")
                continue
            
            # 检查所有子字段
            for subfield in SUBFIELDS[field]:
                if not value.get(subfield):
                    errors.append(f"缺少子字段：{field}.{subfield}")

    return errors


def export_schema_json(schema_path):
    """
    导出教案字段Schema为JSON文件
    
    Args:
        schema_path: 输出JSON文件路径
    """
    schema = {
        "fields": [
            {
                "name": name,
                "required": required,
                "type": "group" if name in SUBFIELDS else "text",
                "widget": "group" if name in SUBFIELDS else "textarea",
                "placeholder": f"请输入{name}",
                "subfields": [
                    {
                        "name": sub,
                        "type": "text",
                        "widget": "textarea",
                        "placeholder": f"请输入{sub}",
                    }
                    for sub in SUBFIELDS.get(name, [])
                ],
            }
            for name, required in FIELD_ORDER
        ]
    }
    
    schema_path = Path(schema_path)
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def calculate_week_number(semester_start, target_date):
    """
    计算目标日期距离学期开始的周次
    
    Args:
        semester_start: 学期开始日期
        target_date: 目标日期
        
    Returns:
        周次（1-based）
    """
    delta_days = (target_date - semester_start).days
    return delta_days // 7 + 1


def weekday_cn(d):
    """
    返回日期的中文星期名
    
    Args:
        d: date对象
        
    Returns:
        中文星期名（"一"到"日"）
    """
    mapping = "一二三四五六日"
    return mapping[d.weekday()]


def build_week_text(week_number):
    """构建周次文本"""
    return f"第（{week_number}）周"


def build_date_text(target_date):
    """构建日期文本"""
    week_day = weekday_cn(target_date)
    return f"周（{week_day}） {target_date.month}月{target_date.day}日"
