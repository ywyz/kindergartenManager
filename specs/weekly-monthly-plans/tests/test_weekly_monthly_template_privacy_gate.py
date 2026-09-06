"""Artifact-only privacy gate for the two committed DOCX candidate files.

This is not part of the WMP-6 orchestration RED and does not qualify either
candidate. It only guards the user-authorized repository artifact sanitation.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORD_TEXT = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"

ALLOWED_TEXT = {
    "weekplan.docx": {
        "幼儿园每周工作计划表",
        "主题名称：____________    班级：____________    第（    ）周（____年__月__日——____年__月__日）",
        "教师：____________    保育员：____________",
        "周次",
        "周一",
        "周二",
        "周三",
        "周四",
        "周五",
        "学习",
        "活动",
        "晨间",
        "谈话",
        "游戏",
        "集体",
        "区域",
        "户外",
        "本周",
        "重点",
        "环境",
        "创设",
        "生活",
        "习惯",
        "培养",
        "家园",
        "共育",
    },
    "monthplan.docx": {
        "幼儿园主题教育活动计划",
        "班级：____________    执行年月：____.__    带班老师：____________    保育老师：____________",
        "上月分析及本月重点",
        "本月主题：",
        "上月分析：",
        "本月重点：",
        "主题目标",
        "生活习惯",
        "游戏",
        "活动",
        "环境创设",
        "家园",
        "共育",
        "其它",
        "领域",
        "活动内容",
    },
}


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1]


@pytest.mark.parametrize("filename", ["weekplan.docx", "monthplan.docx"])
def test_committed_candidate_contains_only_allowlisted_text_and_no_identity_metadata(
    filename,
):
    path = REPOSITORY_ROOT / "templates" / filename
    with ZipFile(path) as package:
        names = tuple(package.namelist())
        assert package.comment == b""
        assert all(
            entry.date_time == (1980, 1, 1, 0, 0, 0)
            and entry.extra == b""
            and entry.comment == b""
            for entry in package.infolist()
        )
        assert "docProps/app.xml" not in names
        assert "docProps/custom.xml" not in names
        assert not any(name.startswith("customXml/") for name in names)
        assert not any(
            marker in name.casefold()
            for name in names
            for marker in ("comments", "people")
        )

        visible_text = set()
        external_relationships = []
        revision_identifiers = []
        core_metadata = []
        for name in names:
            if not (name.endswith(".xml") or name.endswith(".rels")):
                continue
            root = ElementTree.fromstring(package.read(name))
            if name == "docProps/core.xml":
                core_metadata.extend(
                    (child.tag, child.text)
                    for child in root
                    if child.text and child.text.strip()
                )
            for element in root.iter():
                if element.tag == WORD_TEXT and element.text and element.text.strip():
                    visible_text.add(element.text.strip())
                if (
                    _local_name(element.tag) == "Relationship"
                    and element.attrib.get("TargetMode") == "External"
                ):
                    external_relationships.append(element.attrib.get("Target"))
                if _local_name(element.tag) in {"rsids", "docId", "docVars"}:
                    revision_identifiers.append(element.tag)
                revision_identifiers.extend(
                    key for key in element.attrib if _local_name(key).startswith("rsid")
                )

        assert core_metadata == []
        assert external_relationships == []
        assert revision_identifiers == []
        assert visible_text <= ALLOWED_TEXT[filename]
