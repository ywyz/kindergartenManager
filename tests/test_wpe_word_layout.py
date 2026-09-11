"""Initial coverage: new independent v3 layout, not historical business RED."""

from dataclasses import replace
from datetime import date, timedelta
from hashlib import sha256
from io import BytesIO

import pytest
from docx import Document
from docx.oxml.ns import qn

from app.integration.word_export.shared_weekly_word import (
    SEED_PATH,
    SEED_SHA256,
    SharedWeeklyWordPort,
    fill_document,
)
from app.service.shared_weekly.authoring_contracts import (
    AuthoringCalendar,
    AuthoringSlot,
    WeeklyAuthoringDraft,
)
from app.service.shared_weekly.body_contracts import (
    CollaborationDay,
    WeeklyCollaborationDraft,
)
from app.service.shared_weekly.layout_contracts import WeekDisplay
from app.service.shared_weekly.people_contracts import People


def complete_body(count=5, long=False):
    days = tuple(
        CollaborationDay(
            date(2026, 9, 14) + timedelta(days=i), "晨谈", "问题", "名称", "", ""
        )
        for i in range(count)
    )
    base = WeeklyCollaborationDraft(
        "秋天", People(("甲老师", "乙老师"), "丙老师"), days, ()
    )
    body = WeeklyAuthoringDraft.from_collaboration(base)
    body = body.with_slots(
        tuple(
            (path, AuthoringSlot(("内容" * 30 if long else "项") + str(i)))
            for i, path in enumerate(body.paths)
        )
    )
    return replace(
        body,
        calendar=AuthoringCalendar(
            "test.v1",
            "a" * 64,
            tuple(
                (d.day, i != 3, "" if i != 3 else "中秋节放假")
                for i, d in enumerate(days)
            ),
        ),
    )


@pytest.mark.parametrize("count", [5, 6])
def test_controlled_seed_fill_roundtrip_fixed_format(count):
    body = complete_body(count)
    seed = SEED_PATH.read_bytes()
    assert sha256(seed).hexdigest() == SEED_SHA256
    doc = Document(
        BytesIO(fill_document(seed, body, WeekDisplay("小一班", "第一学期", 3)))
    )
    assert len(doc.tables) == 1
    table = doc.tables[0]
    assert len(table.columns) == count + 2
    assert len(table.rows) == 9
    assert table.cell(1, 5).text == "中秋节放假"
    assert table.cell(2, 5).text == "中秋节放假"
    assert "《秋天》" in doc.paragraphs[1].text
    assert "甲老师、乙老师" in doc.paragraphs[2].text
    paragraphs = list(doc.paragraphs) + [
        p for r in table.rows for c in r.cells for p in c.paragraphs
    ]
    for p in paragraphs:
        assert p.paragraph_format.line_spacing.pt == 20
        for run in p.runs:
            assert run.font.size.pt == 12
            assert run._element.rPr.rFonts.get(qn("w:eastAsia")) == "宋体"
    assert sha256(SEED_PATH.read_bytes()).hexdigest() == SEED_SHA256


@pytest.mark.parametrize("count", [5, 6])
async def test_real_local_render_long_fails_without_delivery(count):
    result = await SharedWeeklyWordPort().inspect_local(
        complete_body(count, long=True), WeekDisplay("小一班", "第一学期", 3)
    )
    assert result.reason == "layout_overflow"
    assert result.pages > 1
    assert not result.fits and result.data is None
    assert result.binding.active_version == "local-unqualified"


async def test_formal_qualification_not_inherited():
    with pytest.raises(ValueError, match="qualification_required"):
        await SharedWeeklyWordPort().resolve_binding(1)


async def test_incomplete_draft_refused_before_renderer():
    body = complete_body().with_slot("home", AuthoringSlot())
    result = await SharedWeeklyWordPort().inspect_local(
        body, WeekDisplay("小一班", "第一学期", 3)
    )
    assert not result.fits and result.pages == 0 and result.data is None


def test_consecutive_holiday_continuation_keeps_blank_cell():
    body = complete_body()
    columns = tuple(
        (day, False, "中秋节放假" if i == 3 else "")
        if i >= 3
        else (day, teaching, label)
        for i, (day, teaching, label) in enumerate(body.calendar.columns)
    )
    body = replace(body, calendar=replace(body.calendar, columns=columns))
    document = Document(
        BytesIO(
            fill_document(
                SEED_PATH.read_bytes(), body, WeekDisplay("小一班", "第一学期", 3)
            )
        )
    )
    assert document.tables[0].cell(1, 5).text == "中秋节放假"
    assert document.tables[0].cell(1, 6).text == ""
    assert document.tables[0].cell(2, 6).text == ""


@pytest.mark.parametrize("count", [5, 6])
async def test_local_short_reports_actual_render(count):
    result = await SharedWeeklyWordPort().inspect_local(
        complete_body(count), WeekDisplay("小一班", "第一学期", 3)
    )
    print({"columns": count, "pages": result.pages, "reason": result.reason})
    assert result.pages >= 1
    assert result.reason in ("fits", "layout_overflow")
    assert (result.data is not None) == result.fits


async def test_six_short_complete_content_renders_on_one_page():
    result = await SharedWeeklyWordPort().inspect_local(
        complete_body(6), WeekDisplay("小一班", "第一学期", 3)
    )
    assert result.fits, (result.pages, result.reason)
    assert result.data is not None


def test_emitted_table_keeps_controlled_template_cell_borders():
    doc = Document(
        BytesIO(
            fill_document(
                SEED_PATH.read_bytes(),
                complete_body(6),
                WeekDisplay("小一班", "第一学期", 3),
            )
        )
    )
    for row in doc.tables[0].rows:
        for cell in row.cells:
            borders = cell._tc.tcPr.find(qn("w:tcBorders"))
            assert borders is not None, "visible fixed template grid missing"
            assert all(
                borders.find(qn("w:" + side)) is not None
                for side in ("top", "left", "bottom", "right")
            )


async def test_actual_render_missing_duplicate_label_is_not_delivered(monkeypatch):
    import xml.etree.ElementTree as ET

    from app.integration.word_export import shared_weekly_word as module

    original = module._process

    async def lose_one_label(*args):
        output = await original(*args)
        if args[:2] == ("pdftotext", "-bbox"):
            tree = ET.parse(args[-1])
            label = next(
                word
                for word in tree.iter("{http://www.w3.org/1999/xhtml}word")
                if word.text == "名称"
            )
            label.text = ""
            tree.write(args[-1], encoding="utf-8", xml_declaration=True)
        return output

    monkeypatch.setattr(module, "_process", lose_one_label)
    result = await SharedWeeklyWordPort().inspect_local(
        complete_body(), WeekDisplay("小一班", "第一学期", 3)
    )
    assert result.reason == "layout_overflow"
    assert not result.fits and result.data is None


@pytest.mark.parametrize("axis", ["x", "y"])
async def test_renderer_text_crossing_cell_edge_is_not_delivered(monkeypatch, axis):
    import xml.etree.ElementTree as ET

    from app.integration.word_export import shared_weekly_word as module

    original = module._process

    async def cross_cell(*args):
        output = await original(*args)
        if args[:2] == ("pdftotext", "-bbox"):
            tree = ET.parse(args[-1])
            word = next(
                word
                for word in tree.iter("{http://www.w3.org/1999/xhtml}word")
                if word.text == "项"
            )
            # Extend past the first date column's right edge, while its center
            # stays inside that original column and the bbox stays on the page.
            word.set("xMax", "240") if axis == "x" else word.set("yMax", "165")
            tree.write(args[-1], encoding="utf-8", xml_declaration=True)
        return output

    monkeypatch.setattr(module, "_process", cross_cell)
    result = await SharedWeeklyWordPort().inspect_local(
        complete_body(6), WeekDisplay("小一班", "第一学期", 3)
    )
    assert not result.fits, "text crosses a cell border but is delivered"
    assert result.reason == "layout_overflow" and result.data is None
