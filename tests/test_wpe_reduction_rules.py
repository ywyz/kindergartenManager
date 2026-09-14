"""Closed Chinese predicate shortening: real application, synthetic layout/AI."""

from uuid import uuid4

import pytest

from app.integration.ai_client import weekly_authoring_client as client
from app.repository.shared_weekly_repository import VERSION
from app.service.shared_weekly.authoring_application import SlotChange
from app.service.shared_weekly.reduction_application import ReductionApplication
from tests.test_wpc_identity import world as _world
from tests.test_wpc_shared_root import rows
from tests.test_wpd_application import ready
from tests.test_wpe_reduction_application import LayoutSeam

world = _world

ORIGINAL = (
    "围绕秋天落叶进行观察，围绕颜色进行比较，围绕形状进行分类，围绕发现进行记录。"
)
SHORT = "围绕秋天落叶观察，围绕颜色比较，围绕形状分类，围绕发现记录。"


async def prepared(world, monkeypatch, original=ORIGINAL):
    app, edit, _, calls = await ready(world, monkeypatch)
    edit = await app.update_slots(
        world[2][3], edit.page_id, edit.page, (SlotChange("focus.0", original),)
    )
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    edit = await app.begin_authoring(world[2][3], saved.plan_id)
    reduction = ReductionApplication(app, LayoutSeam(app))
    app._reduction = reduction
    return app, edit, reduction, calls


async def test_chinese_prose_without_spaces_has_explicit_shortening_candidate(
    world, monkeypatch
):
    app, edit, reduction, calls = await prepared(world, monkeypatch)

    async def shortened(prompt, payload, config):
        calls.append(payload)
        return {"values": {"focus.0": SHORT}}

    monkeypatch.setattr(client, "generate", shortened)
    before = await rows(world, VERSION)
    candidate = await reduction.propose(
        world[2][3], "synthetic-overflow", edit.page_id, edit.page
    )
    assert [
        (d.path, d.current_value, d.candidate_value) for d in candidate.differences
    ] == [("focus.0", ORIGINAL, SHORT)]
    assert len(SHORT) < len(ORIGINAL)
    assert app._page(world[2][3], edit.page_id).view == edit
    assert await rows(world, VERSION) == before
    changed = await reduction.adopt(
        world[2][3], candidate.candidate_id, edit.page, confirmed=True
    )
    assert changed.body.value_at("focus.0") == SHORT
    assert await rows(world, VERSION) == before
    saved = await app.save_edit(world[2][3], changed.page_id, changed.page, uuid4())
    assert (await app.load(world[2][3], saved.plan_id)).body.value_at(
        "focus.0"
    ) == SHORT
    assert len(calls) == 1


@pytest.mark.parametrize(
    "original, expected",
    [
        (
            "进行观察。进行讨论；进行比较！进行分类？进行记录，进行交流\n做出选择",
            "观察。讨论；比较！分类？记录，交流\n选择",
        ),
        (
            "组织幼儿进行观察，引导幼儿共同进行讨论。",
            "组织幼儿观察，引导幼儿共同讨论。",
        ),
        (
            "围绕2026年9月12日的3片叶子进行观察，围绕2个方案做出选择。",
            "围绕2026年9月12日的3片叶子观察，围绕2个方案选择。",
        ),
        (
            "不进行观察，禁止幼儿进行讨论，围绕不能触碰的物体进行观察。",
            "不进行观察，禁止幼儿进行讨论，围绕不能触碰的物体进行观察。",
        ),
        (
            "进行观察活动，进行观察站建设，活动名为进行观察。",
            "进行观察活动，进行观察站建设，活动名为进行观察。",
        ),
        (
            "进行观察的时间，进行讨论后再记录，先进行比较再进行分类。",
            "进行观察的时间，进行讨论后再记录，先进行比较再进行分类。",
        ),
        (
            "“进行观察。  进行讨论。”围绕叶子进行比较。",
            "“进行观察。  进行讨论。”围绕叶子进行比较。",
        ),
        ("围绕《进行观察》进行讨论。", "围绕《进行观察》讨论。"),
        ("进行观察。“未闭合，进行讨论。", "观察。“未闭合，进行讨论。"),
        (
            "'进行观察'；\"进行讨论\"；「进行比较」；『进行分类』",
            "'进行观察'；\"进行讨论\"；「进行比较」；『进行分类』",
        ),
    ],
)
def test_closed_predicate_rules_keep_numbers_negation_quotes_and_grammar(
    original, expected
):
    from app.service.shared_weekly.reduction_application import shorten_preserving_facts

    assert shorten_preserving_facts(original) == expected


@pytest.mark.parametrize(
    "original",
    [
        "进行观察活动，进行讨论后再记录。",
        "不进行观察，禁止幼儿进行讨论。",
        "“进行观察。进行讨论。”",
    ],
)
async def test_no_safe_rule_sends_zero_requests(world, monkeypatch, original):
    from app.service.academic_identity.contracts import IdentityRejected

    app, edit, reduction, calls = await prepared(world, monkeypatch, original)
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected, match="reduction_manual_required"):
        await reduction.propose(
            world[2][3], "synthetic-overflow", edit.page_id, edit.page
        )
    assert calls == []
    assert app._page(world[2][3], edit.page_id).view == edit
    assert await rows(world, VERSION) == before


@pytest.mark.parametrize("name_kind", ["activity", "game", "area", "habit"])
async def test_confirmed_names_are_protected_everywhere(world, monkeypatch, name_kind):
    from dataclasses import replace

    from app.service.shared_weekly.editor_contracts import ManualWeekEdit
    from app.service.shared_weekly.prompt_contracts import REDUCTION_RULE_VERSION

    original = "进行观察，围绕3片叶子进行比较。"
    expected = "进行观察，围绕3片叶子比较。"
    app, edit, _, calls = await prepared(world, monkeypatch, original)
    if name_kind == "activity":
        days = tuple(replace(day, activity_name="进行观察") for day in edit.body.days)
        edit = await app.update_edit(
            world[2][3],
            edit.page_id,
            edit.page,
            ManualWeekEdit(edit.body.theme, edit.body.people, days),
        )
    else:
        path = {
            "game": "games.collective.0.name",
            "area": "area.name",
            "habit": "habits.0.name",
        }[name_kind]
        edit = await app.update_slots(
            world[2][3], edit.page_id, edit.page, (SlotChange(path, "进行观察"),)
        )
    saved = await app.save_edit(world[2][3], edit.page_id, edit.page, uuid4())
    edit = await app.begin_authoring(world[2][3], saved.plan_id)
    reduction = ReductionApplication(app, LayoutSeam(app))

    async def shortened(prompt, payload, config):
        calls.append(payload)
        assert REDUCTION_RULE_VERSION in prompt
        assert payload["reduction_rule_version"] == REDUCTION_RULE_VERSION
        assert payload["fields"]["focus.0"]["protected_spans"] == ((0, 4),)
        return {"values": {"focus.0": expected}}

    monkeypatch.setattr(client, "generate", shortened)
    candidate = await reduction.propose(
        world[2][3], "synthetic-overflow", edit.page_id, edit.page
    )
    changed = await reduction.adopt(
        world[2][3], candidate.candidate_id, edit.page, confirmed=True
    )
    assert changed.body.value_at("focus.0") == expected
    assert changed.body.days == edit.body.days
    assert all(
        changed.body.value_at(path) == edit.body.value_at(path)
        for path in edit.body.paths
        if path.endswith(".name")
    )


@pytest.mark.parametrize(
    "bad_value",
    [
        "围绕秋天落叶观察，围绕颜色比较。",
        "围绕秋天落叶观察，围绕颜色比较，围绕形状分类，围绕发现不记录。",
        "围绕3片叶子观察，围绕颜色比较，围绕形状分类，围绕发现记录。",
    ],
)
async def test_free_semantic_or_numeric_change_rejected(world, monkeypatch, bad_value):
    from app.service.academic_identity.contracts import IdentityRejected

    app, edit, reduction, calls = await prepared(world, monkeypatch)

    async def bad(prompt, payload, config):
        calls.append(payload)
        return {"values": {"focus.0": bad_value}}

    monkeypatch.setattr(client, "generate", bad)
    before = await rows(world, VERSION)
    with pytest.raises(IdentityRejected, match="reduction_facts_changed"):
        await reduction.propose(
            world[2][3], "synthetic-overflow", edit.page_id, edit.page
        )
    assert app._page(world[2][3], edit.page_id).view == edit
    assert await rows(world, VERSION) == before
    assert len(calls) == 1
