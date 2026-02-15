"""测试修复：下午户外游戏填充问题"""
import kg_manager as kg
from pathlib import Path
from datetime import date

# 准备测试数据
test_plan = {
    "室内区域游戏": {
        "游戏区域": "阅读区、建构区",
        "重点指导": "鼓励合作",
        "活动目标": "提升语言表达",
        "指导要点": "轮流表达、倾听他人",
        "支持策略": "提供图书卡片",
    },
    "下午户外游戏": {
        "游戏区域": "操场接力区",
        "重点观察": "遵守规则",
        "活动目标": "提升协调与速度",
        "指导要点": "交接动作规范",
        "支持策略": "分组示范、同伴互评",
    },
    "集体活动": {
        "活动主题": "小班美术《彩色雨点》",
        "活动目标": "体验点画",
    }
}

# 生成Word文档
output_file = kg.generate_plan_docx(
    template_path="examples/teacherplan.docx",
    plan_data=test_plan,
    week_text="第（1）周",
    date_text="周（一） 2月15日",
    output_path="output/test_fix.docx",
)

print(f"✓ 已生成测试文档: {output_file}")

# 读取并验证内容
from docx import Document
doc = Document(output_file)

print("\n=== 验证填充内容 ===")
for i, row in enumerate(doc.tables[0].rows):
    if len(row.cells) >= 2:
        label = row.cells[0].text.strip()
        content = row.cells[1].text.strip()
        
        # 检查关键行
        if label == "下午户外游戏":
            print(f"\n行 {i}: {label}")
        elif "游戏区域" in content or "操场接力区" in content or "阅读区" in content:
            print(f"行 {i}: [{label}]")
            print(f"  内容: {content[:50]}...")
            if label == "游戏区域" and i > 10:  # 大概是下午户外游戏的部分
                if "操场接力区" in content:
                    print("  ✓ 正确！填充了下午户外游戏的内容")
                elif "阅读区" in content:
                    print("  ✗ 错误！填充了室内区域游戏的内容")
