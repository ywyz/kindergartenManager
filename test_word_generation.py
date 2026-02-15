"""端到端测试：生成 Word 文档验证下午户外游戏内容正确性"""
import kg_manager as kg
from pathlib import Path
from docx import Document

# 准备完整的测试数据
plan_data = {
    "周次": "第（1）周",
    "日期": "周（一） 2月26日",
    "晨间活动": {
        "集体游戏": "捉迷藏",
        "自主游戏": "建构区自由搭建",
    },
    "晨间活动指导": {
        "重点指导": "规则意识与安全",
        "活动目标": "提升动作协调性",
        "指导要点": "控制速度、保持间距",
    },
    "晨间谈话": {
        "话题": "我喜欢的颜色",
        "问题设计": "你为什么喜欢这种颜色？",
    },
    "集体活动": {
        "活动主题": "小班美术《彩色雨点》",
        "活动目标": "体验点画，感受色彩变化",
        "活动准备": "彩笔、白纸、围裙",
        "活动重点": "掌握点画节奏",
        "活动难点": "颜色搭配",
        "活动过程": "导入-示范-操作-分享",
    },
    "室内区域游戏": {
        "游戏区域": "阅读区、建构区",
        "重点指导": "鼓励合作",
        "活动目标": "提升语言表达",
        "指导要点": "轮流表达、倾听他人",
        "支持策略": "提供图书卡片和积木",
    },
    "下午户外游戏": {
        "游戏区域": "操场接力区",
        "重点观察": "遵守规则",
        "活动目标": "提升协调与速度",
        "指导要点": "交接动作规范",
        "支持策略": "分组示范、同伴互评",
    },
    "一日活动反思": "幼儿参与度高，但个别幼儿注意力分散。",
}

# 生成 Word 文档
template_path = Path("examples/teacherplan.docx")
output_path = Path("output/test_outdoor_fix.docx")

print("=" * 60)
print("端到端测试：生成 Word 文档")
print("=" * 60)
print(f"模板路径: {template_path}")
print(f"输出路径: {output_path}")

# 验证模板存在
if not template_path.exists():
    print(f"❌ 错误：模板文件不存在: {template_path}")
    exit(1)

# 生成文档
result_path = kg.generate_plan_docx(
    template_path=str(template_path),
    plan_data=plan_data,
    week_text="第（1）周",
    date_text="周（一） 2月26日",
    output_path=str(output_path),
)

print(f"✓ Word 文档已生成: {result_path}")

# 读取生成的文档并验证内容
print("\n" + "=" * 60)
print("验证生成的文档内容")
print("=" * 60)

doc = Document(output_path)
table = doc.tables[0]

# 关键验证点：检查第15、16、17行（下午户外游戏）的内容
print("\n检查下午户外游戏部分 (行 15-17):")
print("-" * 60)

row_15 = table.rows[15]
row_16 = table.rows[16]
row_17 = table.rows[17]

# Row 15: 游戏区域
label_15 = row_15.cells[0].text.strip()
content_15 = row_15.cells[1].text.strip()
print(f"行 15 - 标签: {repr(label_15)}")
print(f"行 15 - 内容: {repr(content_15)}")

# Row 16: 重点观察、活动目标、指导要点
label_16 = row_16.cells[0].text.strip()
content_16 = row_16.cells[1].text.strip()
print(f"行 16 - 标签: {repr(label_16)}")
print(f"行 16 - 内容: {repr(content_16)}")

# Row 17: 支持策略
label_17 = row_17.cells[0].text.strip()
content_17 = row_17.cells[1].text.strip()
print(f"行 17 - 标签: {repr(label_17)}")
print(f"行 17 - 内容: {repr(content_17)}")

print("\n" + "=" * 60)
print("验证结果")
print("=" * 60)

# 验证期望的内容
expected_checks = [
    ("行 15 应包含 '操场接力区'", "操场接力区" in content_15),
    ("行 15 不应包含 '阅读区、建构区'", "阅读区" not in content_15 and "建构区" not in content_15),
    ("行 16 应包含 '遵守规则'", "遵守规则" in content_16),
    ("行 16 应包含 '提升协调与速度'", "提升协调" in content_16 or "协调与速度" in content_16),
    ("行 16 应包含 '交接动作规范'", "交接" in content_16 or "规范" in content_16),
    ("行 16 不应包含 '鼓励合作'", "鼓励合作" not in content_16),
    ("行 16 不应包含 '提升语言表达'", "提升语言表达" not in content_16),
    ("行 17 应包含 '分组示范'", "分组示范" in content_17 or "同伴互评" in content_17),
    ("行 17 不应包含 '提供图书'", "图书" not in content_17),
]

all_pass = True
for description, check in expected_checks:
    status = "✓" if check else "✗"
    if not check:
        all_pass = False
    print(f"{status} {description}")

print("\n" + "=" * 60)
if all_pass:
    print("🎉 测试通过！下午户外游戏内容填充正确！")
else:
    print("❌ 测试失败！下午户外游戏内容填充仍有问题！")
print("=" * 60)

# 对比验证：检查室内区域游戏部分是否也正确
print("\n" + "=" * 60)
print("对比验证：室内区域游戏部分 (行 12-14)")
print("=" * 60)

row_12 = table.rows[12]
row_13 = table.rows[13]
row_14 = table.rows[14]

content_12 = row_12.cells[1].text.strip()
content_13 = row_13.cells[1].text.strip()
content_14 = row_14.cells[1].text.strip()

print(f"行 12 - 内容: {repr(content_12)}")
print(f"行 13 - 内容: {repr(content_13)}")
print(f"行 14 - 内容: {repr(content_14)}")

indoor_checks = [
    ("行 12 应包含 '阅读区、建构区'", "阅读区" in content_12 and "建构区" in content_12),
    ("行 13 应包含 '鼓励合作'", "鼓励合作" in content_13),
    ("行 13 应包含 '提升语言表达'", "提升语言表达" in content_13),
    ("行 14 应包含 '提供图书'", "图书" in content_14 or "积木" in content_14),
]

all_indoor_pass = True
for description, check in indoor_checks:
    status = "✓" if check else "✗"
    if not check:
        all_indoor_pass = False
    print(f"{status} {description}")

print("\n" + "=" * 60)
print("最终结果")
print("=" * 60)
print(f"下午户外游戏: {'通过 ✓' if all_pass else '失败 ✗'}")
print(f"室内区域游戏: {'通过 ✓' if all_indoor_pass else '失败 ✗'}")
print(f"\n整体测试: {'全部通过 ✓✓✓' if all_pass and all_indoor_pass else '存在失败 ✗✗✗'}")
print("=" * 60)

# 返回退出码
exit(0 if (all_pass and all_indoor_pass) else 1)
