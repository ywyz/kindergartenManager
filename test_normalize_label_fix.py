"""测试 normalize_label 修复"""
import kg_manager as kg
from kg_manager.word import normalize_label, flatten_plan_data, smart_lookup
from pathlib import Path

print("=" * 60)
print("测试 1: normalize_label 函数")
print("=" * 60)

test_cases = [
    ('下午：\n户外游戏', '下午户外游戏'),
    ('室内区域游戏：', '室内区域游戏'),
    ('  晨间活动：  ', '晨间活动'),
    ('集体活动', '集体活动'),
    ('重点指导： ', '重点指导'),
    ('话题：', '话题'),
    ('游戏区域：', '游戏区域'),
]

all_pass = True
for input_label, expected in test_cases:
    result = normalize_label(input_label)
    status = '✓' if result == expected else '✗'
    if result != expected:
        all_pass = False
    print(f'{status} {repr(input_label):30} -> {repr(result):20} (expected: {repr(expected)})')

print(f'\n结果: {"所有测试通过 ✓" if all_pass else "部分测试失败 ✗"}')

print("\n" + "=" * 60)
print("测试 2: 扁平化数据结构")
print("=" * 60)

plan_data = {
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
}

flat_data = flatten_plan_data(plan_data)
print("扁平化后的数据:")
for key, value in flat_data.items():
    print(f"  {key}: {value}")

print("\n" + "=" * 60)
print("测试 3: smart_lookup 智能查找")
print("=" * 60)

# 测试上下文感知查找
test_lookups = [
    ("游戏区域", None, "阅读区、建构区"),  # 无上下文时，应该返回第一个匹配
    ("游戏区域", "下午户外游戏", "操场接力区"),  # 有上下文时，应该返回对应的值
    ("游戏区域", "室内区域游戏", "阅读区、建构区"),
    ("重点观察", None, "遵守规则"),  # 这个字段只存在于下午户外游戏
    ("重点指导", None, "鼓励合作"),  # 这个字段只存在于室内区域游戏
    ("活动目标", "下午户外游戏", "提升协调与速度"),
    ("活动目标", "室内区域游戏", "提升语言表达"),
]

all_lookup_pass = True
for label, context, expected in test_lookups:
    result = smart_lookup(flat_data, label, context)
    status = '✓' if result == expected else '✗'
    if result != expected:
        all_lookup_pass = False
    context_str = f"'{context}'" if context else "None"
    print(f'{status} 查找 "{label}" (上下文={context_str:20}): {result}')
    if result != expected:
        print(f'   期望: {expected}')

print(f'\n结果: {"所有查找测试通过 ✓" if all_lookup_pass else "部分查找测试失败 ✗"}')

print("\n" + "=" * 60)
print("测试 4: 模拟 Word 模板标签匹配")
print("=" * 60)

# 模拟从 Word 模板读取的标签（包含换行和冒号）
template_labels = [
    "下午：\n户外游戏",
    "室内区域游戏：",
]

print("模板标签标准化后的匹配测试:")
for template_label in template_labels:
    normalized = normalize_label(template_label)
    # 检查是否能在扁平化数据的键中找到匹配
    matching_keys = [key for key in flat_data.keys() if key.startswith(f"{normalized}-")]
    
    status = '✓' if len(matching_keys) > 0 else '✗'
    print(f'{status} 模板标签: {repr(template_label):30}')
    print(f'   标准化为: {repr(normalized):30}')
    print(f'   匹配的键: {matching_keys}')
    
    # 验证是否能正确设置 context_parent
    if matching_keys:
        # 模拟 fill_table_by_labels 的逻辑
        context_parent = normalized
        # 测试查找子字段
        test_subfield = "游戏区域"
        result = smart_lookup(flat_data, test_subfield, context_parent)
        print(f'   使用上下文 "{context_parent}" 查找 "{test_subfield}": {result}')

print("\n" + "=" * 60)
print("总结")
print("=" * 60)
print(f"normalize_label 测试: {'通过 ✓' if all_pass else '失败 ✗'}")
print(f"smart_lookup 测试: {'通过 ✓' if all_lookup_pass else '失败 ✗'}")
print(f"\n整体测试: {'全部通过 ✓✓✓' if all_pass and all_lookup_pass else '存在失败 ✗✗✗'}")
