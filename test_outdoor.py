"""测试下午户外游戏填充问题"""
import kg_manager as kg
from pathlib import Path

# 准备测试数据
plan_data = {
    "室内区域游戏": {
        "游戏区域": "阅读区、建构区",
        "重点指导": "鼓励合作",
        "活动目标": "提升语言表达",
        "指导要点": "轮流表达",
        "支持策略": "提供图书",
    },
    "下午户外游戏": {
        "游戏区域": "操场接力区",
        "重点观察": "遵守规则",
        "活动目标": "提升协调",
        "指导要点": "交接规范",
        "支持策略": "分组示范",
    },
}

# 测试扁平化
from kg_manager.word import flatten_plan_data
flat = flatten_plan_data(plan_data)
print("=== 扁平化结果 ===")
for k, v in flat.items():
    print(f"{k}: {v}")

# 测试smart_lookup
from kg_manager.word import smart_lookup

print("\n=== 测试smart_lookup ===")
# 无上下文时查找"游戏区域"
result = smart_lookup(flat, "游戏区域", None)
print(f"查找'游戏区域'(无上下文): {result}")

# 有上下文时查找"游戏区域"
result = smart_lookup(flat, "游戏区域", "下午户外游戏")
print(f"查找'游戏区域'(上下文='下午户外游戏'): {result}")

result = smart_lookup(flat, "游戏区域", "室内区域游戏")
print(f"查找'游戏区域'(上下文='室内区域游戏'): {result}")
