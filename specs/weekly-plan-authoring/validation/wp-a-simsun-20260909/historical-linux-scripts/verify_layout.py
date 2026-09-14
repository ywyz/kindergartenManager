from __future__ import annotations

import re
import subprocess
from pathlib import Path
from zipfile import ZipFile

from lxml import etree


BASE = Path("/home/ywyz/code/km-wpa-fonts-20260909/layout")
PDFINFO = "/home/ywyz/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/pdfinfo"
PDFFONTS = "/usr/bin/pdffonts"
W_URI = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_URI}
EXPECTED_TEMPLATE_SHA = "f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b"
BASE_SPECS = {
    "normal-five-short": (7, 5),
    "normal-five-long": (7, 5),
    "preceding-sunday-six-short": (8, 6),
    "preceding-sunday-six-long": (8, 6),
    "saturday-six-short": (8, 6),
    "saturday-six-long": (8, 6),
}
COMPACT_SPECS = {
    "normal-compact-candidate": (7, 5),
    "sunday-compact-candidate": (8, 6),
    "saturday-compact-candidate": (8, 6),
}


def xml(path: Path):
    with ZipFile(path) as archive:
        return etree.fromstring(archive.read("word/document.xml"))


def text_of(cell) -> str:
    return "".join(cell.xpath(".//w:t/text()", namespaces=NS))


def check_doc(path: Path, expected_columns: int, day_count: int) -> None:
    root = xml(path)
    sect = root.xpath(".//w:sectPr", namespaces=NS)[-1]
    page = sect.find("./w:pgSz", namespaces=NS)
    assert (int(page.get(f"{{{W_URI}}}w")), int(page.get(f"{{{W_URI}}}h"))) == (11906, 16838)
    margins = sect.find("./w:pgMar", namespaces=NS)
    assert [int(margins.get(f"{{{W_URI}}}{key}")) for key in ("left", "right", "top", "bottom")] == [720, 720, 284, 284]
    tables = root.xpath(".//w:tbl", namespaces=NS)
    assert len(tables) == 1
    table = tables[0]
    grid = [int(node.get(f"{{{W_URI}}}w")) for node in table.xpath("./w:tblGrid/w:gridCol", namespaces=NS)]
    assert len(grid) == expected_columns and sum(grid) == 10466
    assert int(table.find("./w:tblPr/w:tblW", namespaces=NS).get(f"{{{W_URI}}}w")) == 10466
    rows = table.xpath("./w:tr", namespaces=NS)
    assert len(rows) == 9
    assert [len(row.xpath("./w:tc", namespaces=NS)) for row in rows] == ([7, 7, 7, 3, 3, 2, 2, 2, 2] if expected_columns == 7 else [8, 8, 8, 3, 3, 2, 2, 2, 2])
    if expected_columns == 8:
        for row in rows[:3]:
            cell = row.xpath("./w:tc", namespaces=NS)[-1]
            borders = cell.find("./w:tcPr/w:tcBorders", namespaces=NS)
            assert borders is not None
            assert all(borders.find(f"./w:{side}", namespaces=NS) is not None for side in ("top", "bottom", "right"))

    fonts = {value for node in root.xpath(".//w:rFonts", namespaces=NS) for key in ("ascii", "hAnsi", "eastAsia") if (value := node.get(f"{{{W_URI}}}{key}"))}
    sizes = {int(node.get(f"{{{W_URI}}}val")) for node in root.xpath(".//w:sz", namespaces=NS)}
    line_values = {int(node.get(f"{{{W_URI}}}line")) for node in root.xpath(".//w:pPr/w:spacing", namespaces=NS) if node.get(f"{{{W_URI}}}line")}
    rules = {node.get(f"{{{W_URI}}}lineRule") for node in root.xpath(".//w:pPr/w:spacing", namespaces=NS)}
    assert fonts == {"宋体"} and sizes == {24, 32} and line_values == {400} and rules == {"exact"}

    body_paragraphs = root.xpath("./w:body/w:p", namespaces=NS)
    assert "教师：张老师、李老师、王老师" in "".join(text_of(p) for p in body_paragraphs)
    outdoor = text_of(rows[3].xpath("./w:tc", namespaces=NS)[-1])
    assert outdoor.count("集体游戏：") == 1 and outdoor.count("自主游戏：") == 1
    assert outdoor.count("①") == outdoor.count("②") == outdoor.count("③") == 3
    area = text_of(rows[4].xpath("./w:tc", namespaces=NS)[-1])
    assert area.count("目标：") == 1 and area.count("指导：") == 1
    assert len(re.findall(r"(?<!\d)[123]\.", area.split("材料：", 1)[0])) >= 3
    assert len(re.findall(r"(?<!\d)[123]\.", area.split("指导：", 1)[1])) == 3
    for row in rows[5:8]:
        assert len(re.findall(r"(?<!\d)[123]\.", text_of(row.xpath("./w:tc", namespaces=NS)[-1]))) == 3
    home_cell = rows[8].xpath("./w:tc", namespaces=NS)[-1]
    assert len(home_cell.xpath("./w:p", namespaces=NS)) == 1


def check_pdf(render_dir: Path, stem: str) -> None:
    pdf = render_dir / f"{stem}.pdf"
    info = subprocess.check_output([PDFINFO, str(pdf)], text=True)
    assert re.search(r"^Pages:\s+[12]$", info, re.M)
    assert re.search(r"^Page size:\s+595\.304 x 841\.89 pts \(A4\)$", info, re.M)
    pages = int(re.search(r"^Pages:\s+(\d+)$", info, re.M).group(1))
    assert len(list(render_dir.glob("page-*.png"))) == pages
    font_rows = subprocess.check_output([PDFFONTS, str(pdf)], text=True).splitlines()[2:]
    names = [line.split()[0].split("+", 1)[-1] for line in font_rows if line.strip()]
    assert names and all(name == "SimSun" for name in names), names


def main() -> None:
    import hashlib

    template = BASE / "weekplan.docx"
    assert hashlib.sha256(template.read_bytes()).hexdigest() == EXPECTED_TEMPLATE_SHA
    for stem, (columns, days) in {**BASE_SPECS, **COMPACT_SPECS}.items():
        check_doc(BASE / f"{stem}.docx", columns, days)
    for stem in BASE_SPECS:
        check_pdf(BASE / f"render-final-{stem}", stem)
    for stem in COMPACT_SPECS:
        check_pdf(BASE / {"normal-compact-candidate": "render-compact-normal", "sunday-compact-candidate": "render-compact-sunday", "saturday-compact-candidate": "render-compact-saturday"}[stem], stem)
    print("VERIFY_OK: geometry, borders, fixed counts, typography, A4 and SimSun PDF embedding")


if __name__ == "__main__":
    main()
