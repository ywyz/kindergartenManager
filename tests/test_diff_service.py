"""tests/test_diff_service.py — 差异比对服务测试。"""

import pytest

from app.service.diff_service import compute_diff


# -------------------------------------------------------------------
# 基础场景
# -------------------------------------------------------------------

def test_identical_text_all_unchanged():
    """完全相同的文本，所有句子 changed 为 False。"""
    text = "第一步：出示积木。第二步：数积木。第三步：总结。"
    result = compute_diff(text, text)
    assert len(result) > 0
    assert all(not item["changed"] for item in result)


def test_one_sentence_changed():
    """修改一句后，该句 changed 为 True，其余句子不变。"""
    original = "第一步：出示积木。第二步：数积木。第三步：总结。"
    adapted = "第一步：出示积木。第二步：和小朋友一起数积木，教师引导。第三步：总结。"
    result = compute_diff(original, adapted)

    texts = [item["text"] for item in result]
    changed = [item["changed"] for item in result]

    # 第二句已改变
    second_sentence_idx = next(i for i, t in enumerate(texts) if "小朋友" in t)
    assert changed[second_sentence_idx] is True

    # 其他句子未改变（第一和第三句相同）
    unchanged_count = sum(1 for c in changed if not c)
    assert unchanged_count >= 2


def test_empty_input_returns_empty_list():
    """空字符串输入返回空列表。"""
    assert compute_diff("", "") == []
    assert compute_diff("  ", "  ") == []


def test_empty_adapted_returns_empty_list():
    """改写文为空时，返回空列表。"""
    result = compute_diff("原文有内容。这是第二句。", "")
    assert result == []


# -------------------------------------------------------------------
# 边界场景
# -------------------------------------------------------------------

def test_all_sentences_changed():
    """原文与改写文完全不同时，所有句子 changed 为 True。"""
    original = "苹果是红色的。香蕉是黄色的。"
    adapted = "今天天气很好。小朋友们开心地玩耍。"
    result = compute_diff(original, adapted)
    assert len(result) > 0
    assert all(item["changed"] for item in result)


def test_added_sentences_are_marked_changed():
    """改写文新增句子时，新增句子 changed 为 True。"""
    original = "第一步：出示材料。"
    adapted = "第一步：出示材料。第二步：新增探索环节。第三步：总结分享。"
    result = compute_diff(original, adapted)

    changed_items = [item for item in result if item["changed"]]
    # 至少有 2 个新增句子被标记为 changed
    assert len(changed_items) >= 2


def test_result_contains_all_adapted_sentences():
    """结果中所有句子均来自改写文（不包含被删除的原文句子）。"""
    original = "第一步。第二步。第三步。"
    adapted = "步骤A。步骤B。"  # 完全替换
    result = compute_diff(original, adapted)

    result_text = "".join(item["text"] for item in result)
    assert "步骤A" in result_text
    assert "步骤B" in result_text
    # 原文内容不应出现在结果中
    assert "第一步" not in result_text


def test_multiline_text():
    """多行文本（换行分句）正常处理。"""
    original = "第一步：准备材料\n第二步：操作\n第三步：总结"
    adapted = "第一步：准备材料\n第二步：幼儿自主操作，教师观察\n第三步：总结"
    result = compute_diff(original, adapted)

    assert len(result) == 3
    # 第二行（索引1）已改变
    assert result[1]["changed"] is True
    # 第一、三行未改变
    assert result[0]["changed"] is False
    assert result[2]["changed"] is False
