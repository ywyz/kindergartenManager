# Word文档导出问题修复总结

## 问题描述
在导出Word文档时，上午室内区域游戏的填充内容会被错误地填充到下午户外游戏的对应位置中。

**示例**：
- 行15（下午户外游戏的第一个子字段行）应显示"【户外】操场接力区"，但实际显示"【室内】阅读区、建构区"
- 行16的活动目标应显示"【户外目标】提升速度"，但实际显示"【室内目标】提升表达"
- 行17的支持策略应显示"【户外策略】分组示范"，但实际显示"【室内策略】提供卡片"

## 根本原因分析

### 1. 标签规范化不完整
- **函数**: `normalize_label()` 在 `kg_manager/word.py`
- **问题**: 模板中某些标签包含中间的冒号和换行符（如"下午：户外游戏"），而字段名则没有（"下午户外游戏"）
- **原始代码**: 只用 `rstrip()` 去除后缀冒号，无法处理中间的冒号和换行符

### 2. 上下文父字段检测失效
- **函数**: `fill_table_by_labels()` 和 `fill_by_row_labels()` 在 `kg_manager/word.py`
- **问题**: 当遇到新的父字段（如"下午户外游戏"）时，代码未能正确识别它是新的父字段，导致 `context_parent` 仍然保持为旧值（"室内区域游戏"）
- **原始逻辑**: 仅在找到"父字段-子字段"前缀的key时才更新context，而"下午户外游戏"的标签可能因为不匹配而无法触发更新

## 修复方案

### 1. 改进 `normalize_label()` 函数
```python
def normalize_label(label):
    """标准化标签：去除空格、冒号和换行符"""
    # 先去除换行符和回车
    normalized = label.replace("\n", "").replace("\r", "")
    # 去除所有冒号（中英文）
    normalized = normalized.replace("：", "").replace(":", "")
    # 去除前后空格
    normalized = normalized.strip()
    return normalized
```

**改进点**:
- 添加了 `replace("\n", "")` 和 `replace("\r", "")` 处理换行符
- 使用 `replace("：", "")` 和 `replace(":", "")` 去除所有冒号（而非只去除后缀冒号）

### 2. 改进 `fill_table_by_labels()` 函数
通过逐一比对标签与所有扁平化数据中的父字段名，确保新的父字段能被正确识别和设置为上下文：

```python
detected_parent = None
for key in label_to_text.keys():
    if "-" in key:
        parent_name = key.split("-")[0]
        # 规范化比较，去除"："和换行符
        parent_normalized = normalize_label(parent_name)
        if parent_normalized == label_text:
            detected_parent = parent_name
            break

if detected_parent:
    context_parent = detected_parent
```

### 3. 改进 `fill_by_row_labels()` 函数
同样改进了父字段的检测逻辑，确保每个新的父字段都能被正确识别。

## 验证结果

修复后的导出结果正确显示：
- ✓ Row 15: 游戏区域 = 【户外】操场接力区（正确）
- ✓ Row 16: 活动目标 = 【户外目标】提升速度（正确）
- ✓ Row 16: 指导要点 = 【户外要点】规范动作（正确）
- ✓ Row 17: 支持策略 = 【户外策略】分组示范（正确）

所有现有测试（examples_usage.py, test_full_flow.py）均通过验证。

## 文件修改

**修改文件**: `kg_manager/word.py`

- `normalize_label()` - 第27-34行
- `fill_table_by_labels()` - 第236-260行
- `fill_by_row_labels()` - 第263-308行
