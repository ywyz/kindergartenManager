"""完整测试：模拟Word填充流程"""
import sys
sys.path.insert(0, '.')
from kg_manager.word import flatten_plan_data, smart_lookup, normalize_label

# 测试数据
plan_data = {
    "室内区域游戏": {
        "游戏区域": "阅读区、建构区",
        "重点指导": "鼓励合作",
        "活动目标": "提升语言表达",
    },
    "下午户外游戏": {
        "游戏区域": "操场接力区",
        "重点观察": "遵守规则",
        "活动目标": "提升协调",
    },
}

# 扁平化
flat_data = flatten_plan_data(plan_data)
print("=== 扁平化数据 ===")
for k, v in sorted(flat_data.items()):
    print(f"  {k}: {v}")

# 模拟Word表格的行标签
template_rows = [
    "室内区域游戏",
    "游戏区域",      # 应该填充"阅读区、建构区"
    "重点指导",
    "活动目标",      # 应该填充"提升语言表达"
    "下午户外游戏",
    "游戏区域",      # 应该填充"操场接力区"
    "重点观察",
    "活动目标",      # 应该填充"提升协调"
]

print("\n=== 模拟 fill_by_row_labels 逻辑 ===")
context_parent = None

for label_text_raw in template_rows:
    label_text = normalize_label(label_text_raw)
    
    # 检查是否是父字段标签（更新上下文）
    is_parent = False
    for key in flat_data.keys():
        if "-" in key and key.startswith(f"{label_text}-"):
            context_parent = label_text
            is_parent = True
            break
    
    # 智能查找对应的值
    value = smart_lookup(flat_data, label_text, context_parent)
    
    status = "(父字段)" if is_parent else ""
    print(f"  行: '{label_text}' {status}")
    print(f"    → context_parent = {context_parent}")
    print(f"    → 查找结果 = {value}")
    print()
