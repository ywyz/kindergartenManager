"""Initial coverage of explicit immutable-source parsing, without AI or I/O."""

from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.authoring_contracts import (
    WeeklyAuthoringDraft,
    reference_for,
)
from app.service.shared_weekly.body_contracts import (
    CollaborationDay,
    SourceSnapshot,
    TargetPath,
    WeeklyCollaborationDraft,
    import_value_hash,
)
from app.service.shared_weekly.people_contracts import People
from app.service.shared_weekly.source_structure import extract_options


def body(text, field="outdoor_activity", source_id=1):
    target = TargetPath(date(2026, 9, 7), field)
    days = tuple(
        CollaborationDay(target.day + timedelta(days=i), "", "", "", "", "")
        for i in range(5)
    )
    base = WeeklyCollaborationDraft("秋天", People(), days, ()).with_value(target, text)
    source = SourceSnapshot(
        source_id,
        3,
        target.day,
        1,
        1,
        1,
        field,
        target,
        text,
        import_value_hash(text),
        import_value_hash(text),
    )
    return WeeklyAuthoringDraft.from_collaboration(replace(base, sources=(source,)))


def test_explicit_multiple_games_and_individual_goals_are_exact_substrings():
    text = "集体游戏：1.《追球》（目标：①练习追球②学会等待③合作分享）\n2.《跳圈》（目标：①双脚跳跃②保持平衡③遵守规则）\n自主游戏：《沙水》（目标：①探索流动②使用工具③整理材料）"
    draft = body(text)
    before = draft.serialize()
    choices = extract_options(draft)
    assert [(c.kind, c.name) for c in choices] == [
        ("collective", "追球"),
        ("collective", "跳圈"),
        ("autonomous", "沙水"),
    ]
    assert dict(choices[1].values) == {
        "name": "跳圈",
        "goals.0": "双脚跳跃",
        "goals.1": "保持平衡",
        "goals.2": "遵守规则",
    }
    assert all(value in text for choice in choices for _, value in choice.values)
    assert all(c.reference == reference_for(draft.sources[0]) for c in choices)
    assert extract_options(draft) == choices and draft.serialize() == before
    assert len({c.option_id for c in choices}) == 3


def test_single_area_goals_guidance_but_never_materials():
    text = "本周重点指导区域：建构区\n目标：\n1.合作搭建\n2.认识形状\n3.表达想法\n材料：木积木与纸盒\n指导要点：\n1.观察幼儿\n2.提供支持\n3.鼓励交流"
    (choice,) = extract_options(body(text, "indoor_area"))
    assert choice.kind == "area" and choice.name == "建构区"
    assert dict(choice.values) == {
        "name": "建构区",
        "goals.0": "合作搭建",
        "goals.1": "认识形状",
        "goals.2": "表达想法",
        "guidance.0": "观察幼儿",
        "guidance.1": "提供支持",
        "guidance.2": "鼓励交流",
    }
    assert all(value in text for _, value in choice.values)


def test_daily_default_shared_goals_never_assigned_to_multiple_names():
    text = "游戏区域：建构区 、 美工区\n重点指导：建构区/美工区\n活动目标：\n1.合作交流\n2.体验快乐\n3.整理材料\n指导要点：\n1.观察\n2.支持\n3.交流"
    choices = extract_options(body(text, "indoor_area"))
    assert [(c.name, c.values) for c in choices] == [
        ("建构区", (("name", "建构区"),)),
        ("美工区", (("name", "美工区"),)),
    ]
    games = "集体游戏：追球\n自主游戏：沙水\n重点指导：追球/沙水\n活动目标：\n1.合作\n2.交流\n3.等待"
    assert [c.values for c in extract_options(body(games))] == [
        (("name", "追球"),),
        (("name", "沙水"),),
    ]


def test_only_original_source_values_and_permitted_fields():
    draft = body("集体游戏：《追球》")
    choices = extract_options(draft)
    edited = draft.with_value(draft.sources[0].target, "集体游戏：《手工不同名称》")
    assert extract_options(edited) == choices
    assert extract_options(body("集体游戏：《追球》", "indoor_area")) == ()
    assert extract_options(body("集体游戏：《追球》", "morning_talk_topic")) == ()
    assert extract_options(body("在户外开展快乐的游戏。" * 30)) == ()


def test_source_identity_and_repeated_explicit_names_are_distinct_choices():
    text = "集体游戏：1.《追球》\n2.《追球》"
    first = extract_options(body(text))
    second = extract_options(body(text, source_id=2))
    assert len(first) == 2 and first[0].option_id != first[1].option_id
    assert first[0].option_id != second[0].option_id


def test_option_capacity_rejects_instead_of_truncating():
    text = "集体游戏：" + "\n".join(f"{i}.《游戏{i}》" for i in range(1, 65))
    assert len(extract_options(body(text))) == 64
    with pytest.raises(IdentityRejected, match="content_invalid"):
        extract_options(body(text + "\n65.《游戏65》"))
    with pytest.raises(IdentityRejected, match="content_invalid"):
        extract_options(None)


def test_incomplete_or_ambiguous_goals_are_not_fabricated():
    (choice,) = extract_options(body("集体游戏：《追球》（目标：①第一条②第二条）"))
    assert dict(choice.values) == {
        "name": "追球",
        "goals.0": "第一条",
        "goals.1": "第二条",
    }
    (choice,) = extract_options(body("集体游戏：《追球》（目标：①同一条②同一条③其他）"))
    assert choice.values == (("name", "追球"),)
    (choice,) = extract_options(body("集体游戏：《追球》（目标：①一②二③三④四）"))
    assert choice.values == (("name", "追球"),)


def test_source_goal_parenthetical_content_is_preserved_exactly():
    text = "本周重点指导区域：建构区\n目标：\n1.合作搭建（两人一组）\n2.认识形状\n3.表达想法"
    (choice,) = extract_options(body(text, "indoor_area"))
    assert dict(choice.values)["goals.0"] == "合作搭建（两人一组）"
