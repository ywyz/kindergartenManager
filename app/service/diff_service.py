"""差异比对服务 — 使用 difflib 对原文与改写文进行逐句比对。

分句规则：以句号（。）、问号（？）、感叹号（！）、换行符为分隔符，
保留分隔符到句子末尾。

返回格式：
    [
        {"text": "句子内容", "changed": True/False},
        ...
    ]

changed=True 表示该句在改写文中与原文不同（新增、修改或删除）。
"""

import difflib
import re


def _split_sentences(text: str) -> list[str]:
    """将文本按标点符号或换行符拆分为句子列表，过滤空串。"""
    if not text.strip():
        return []
    # 在句末标点后分割，保留标点符号
    parts = re.split(r"(?<=[。？！\n])", text)
    return [p for p in parts if p.strip()]


def compute_diff(original: str, adapted: str) -> list[dict]:
    """对原文与改写文按句比对，返回带 changed 标记的句子列表。

    Args:
        original: 活动过程原文。
        adapted: 年龄适配改写文。

    Returns:
        列表，每项为 {"text": str, "changed": bool}。
        - 改写文中新增或修改的句子 changed=True。
        - 与原文相同的句子 changed=False。
        - 空输入返回空列表。

    Note:
        返回的是改写文视角的结果（以 adapted 为主），
        原文中被删除的句子不出现在结果中。
    """
    if not original.strip() and not adapted.strip():
        return []

    orig_sentences = _split_sentences(original)
    adap_sentences = _split_sentences(adapted)

    if not adap_sentences:
        return []

    # 使用 SequenceMatcher 比对句子序列
    matcher = difflib.SequenceMatcher(None, orig_sentences, adap_sentences, autojunk=False)

    result: list[dict] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            # 完全相同的句子
            for sentence in adap_sentences[j1:j2]:
                result.append({"text": sentence, "changed": False})
        elif tag in ("replace", "insert"):
            # 改写文中新增或替换的句子
            for sentence in adap_sentences[j1:j2]:
                result.append({"text": sentence, "changed": True})
        # tag == "delete"：原文中有但改写文中删除的句子，不出现在结果中

    return result
