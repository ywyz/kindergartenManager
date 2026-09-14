from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

from lxml import etree


BASE = Path("/home/ywyz/code/km-wpa-fonts-20260909/layout")
REPO = Path("/home/ywyz/code/km-wpa-20260908")
FONTCONFIG = BASE / "fontconfig" / "fonts.conf"
PYTHON = Path("/home/ywyz/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12")
SOFFICE = Path("/home/ywyz/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice")
PDFINFO = Path("/home/ywyz/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/pdfinfo")
PDFFONTS = Path("/usr/bin/pdffonts")
RENDERER = Path("/home/ywyz/.codex/plugins/cache/openai-primary-runtime/documents/26.904.11930/skills/documents/render_docx.py")
W_URI = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_URI}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str, env: dict[str, str] | None = None) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, env=env).strip()


def isolated_font_env() -> dict[str, str]:
    env = os.environ.copy()
    home = BASE / "fontcheck-home"
    cache = BASE / "fontcheck-cache"
    home.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    env.update({
        "HOME": str(home),
        "XDG_CACHE_HOME": str(cache),
        "FONTCONFIG_FILE": str(FONTCONFIG),
    })
    return env


def read_xml(path: Path):
    with ZipFile(path) as archive:
        return etree.fromstring(archive.read("word/document.xml"))


def table_info(root) -> list[dict]:
    out = []
    for table in root.xpath(".//w:tbl", namespaces=NS):
        grid = [int(node.get(f"{{{W_URI}}}w")) for node in table.xpath("./w:tblGrid/w:gridCol", namespaces=NS)]
        rows = table.xpath("./w:tr", namespaces=NS)
        physical = [len(row.xpath("./w:tc", namespaces=NS)) for row in rows]
        spans = []
        border_ok = []
        for row in rows:
            row_spans = []
            row_borders = []
            for cell in row.xpath("./w:tc", namespaces=NS):
                cell_pr = cell.find("./w:tcPr", namespaces=NS)
                span = cell_pr.find("./w:gridSpan", namespaces=NS) if cell_pr is not None else None
                row_spans.append(int(span.get(f"{{{W_URI}}}val")) if span is not None else 1)
                borders = cell_pr.find("./w:tcBorders", namespaces=NS) if cell_pr is not None else None
                row_borders.append({
                    side: bool(borders is not None and borders.find(f"./w:{side}", namespaces=NS) is not None)
                    for side in ("top", "bottom", "left", "right")
                })
            spans.append(row_spans)
            border_ok.append(row_borders)
        out.append({
            "grid_twips": grid,
            "grid_sum_twips": sum(grid),
            "tblW_twips": int(table.find("./w:tblPr/w:tblW", namespaces=NS).get(f"{{{W_URI}}}w")),
            "rows": len(rows),
            "physical_cells_per_row": physical,
            "spans": spans,
            "borders": border_ok,
        })
    return out


def section_info(root) -> dict:
    sect = root.xpath(".//w:sectPr", namespaces=NS)[-1]
    page = sect.find("./w:pgSz", namespaces=NS)
    margins = sect.find("./w:pgMar", namespaces=NS)
    return {
        "page_width_twips": int(page.get(f"{{{W_URI}}}w")),
        "page_height_twips": int(page.get(f"{{{W_URI}}}h")),
        "margins_twips": {key: int(margins.get(f"{{{W_URI}}}{key}")) for key in ("left", "right", "top", "bottom")},
    }


def typography_info(root) -> dict:
    fonts = set()
    sizes = set()
    line_values = set()
    line_rules = set()
    for run_font in root.xpath(".//w:rFonts", namespaces=NS):
        for key in ("ascii", "hAnsi", "eastAsia"):
            value = run_font.get(f"{{{W_URI}}}{key}")
            if value:
                fonts.add(value)
    for size in root.xpath(".//w:sz", namespaces=NS):
        value = size.get(f"{{{W_URI}}}val")
        if value:
            sizes.add(int(value))
    for spacing in root.xpath(".//w:pPr/w:spacing", namespaces=NS):
        line = spacing.get(f"{{{W_URI}}}line")
        rule = spacing.get(f"{{{W_URI}}}lineRule")
        if line:
            line_values.add(int(line))
        if rule:
            line_rules.add(rule)
    return {
        "font_names": sorted(fonts),
        "run_sizes_half_points": sorted(sizes),
        "paragraph_line_values_twentieth_points": sorted(line_values),
        "paragraph_line_rules": sorted(line_rules),
    }


def doc_info(path: Path) -> dict:
    root = read_xml(path)
    table_text = root.xpath(".//w:tbl//w:t/text()", namespaces=NS)
    chars = sum(len(text) for text in table_text)
    chars_without_whitespace = sum(len(re.sub(r"\s+", "", text)) for text in table_text)
    return {
        "path": str(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "section": section_info(root),
        "typography": typography_info(root),
        "table_text_chars": chars,
        "table_text_chars_excluding_whitespace": chars_without_whitespace,
        "tables": table_info(root),
    }


def pdf_info(pdf: Path) -> dict:
    info = run(str(PDFINFO), str(pdf))
    pages = re.search(r"^Pages:\s+(\d+)$", info, re.M)
    size = re.search(r"^Page size:\s+(.+)$", info, re.M)
    font_lines = [line.strip() for line in run(str(PDFFONTS), str(pdf)).splitlines()[2:] if line.strip()]
    names = []
    for line in font_lines:
        names.append(line.split()[0].split("+", 1)[-1])
    return {
        "path": str(pdf),
        "sha256": sha256(pdf),
        "bytes": pdf.stat().st_size,
        "pages": int(pages.group(1)) if pages else None,
        "page_size": size.group(1).strip() if size else None,
        "pdffonts_diagnostic": str(PDFFONTS),
        "font_rows": font_lines,
        "font_names": names,
        "all_fonts_are_simsun": bool(names) and all(name == "SimSun" for name in names),
    }


def render_info(render_dir: Path, stem: str) -> dict:
    pdf = render_dir / f"{stem}.pdf"
    return {
        "directory": str(render_dir),
        "pdf": pdf_info(pdf),
        "pngs": [
            {"path": str(image), "sha256": sha256(image), "bytes": image.stat().st_size}
            for image in sorted(render_dir.glob("page-*.png"))
        ],
    }


def main() -> None:
    base_specs = [
        ("normal-five-short", "render-final-normal-five-short"),
        ("normal-five-long", "render-final-normal-five-long"),
        ("preceding-sunday-six-short", "render-final-preceding-sunday-six-short"),
        ("preceding-sunday-six-long", "render-final-preceding-sunday-six-long"),
        ("saturday-six-short", "render-final-saturday-six-short"),
        ("saturday-six-long", "render-final-saturday-six-long"),
    ]
    compact_specs = [
        ("normal-compact-candidate", "render-compact-normal"),
        ("sunday-compact-candidate", "render-compact-sunday"),
        ("saturday-compact-candidate", "render-compact-saturday"),
    ]
    all_specs = base_specs + compact_specs
    render_commands = [
        f"env FONTCONFIG_FILE={FONTCONFIG} {PYTHON} {RENDERER} {BASE / (stem + '.docx')} --output_dir {BASE / render_dir} --emit_pdf --verbose"
        for stem, render_dir in all_specs
    ]
    font_env = isolated_font_env()
    font_match = {
        "宋体": run("fc-match", "宋体", env=font_env),
        "SimSun": run("fc-match", "SimSun", env=font_env),
    }
    font_inputs = {}
    for path in (
        Path("/home/ywyz/.local/share/fonts/km-simsun-20260909/simsun.ttc"),
        Path("/home/ywyz/.local/share/fonts/km-simsun-20260909/simsunb.ttf"),
    ):
        font_inputs[str(path)] = {"sha256": sha256(path), "bytes": path.stat().st_size}

    # This manifest is intentionally generated in the persistent layout root;
    # it never updates the repository evidence files.
    data = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "new synthetic WP-A layout feasibility evidence; independent rebuild, not a hash rerun of the removed /tmp/km-wpa-layout-20260908 tree",
        "write_root": str(BASE),
        "source_template": {
            "path": str(REPO / "templates/weekplan.docx"),
            "sha256": sha256(REPO / "templates/weekplan.docx"),
            "task_local_copy": str(BASE / "weekplan.docx"),
            "task_local_copy_sha256": sha256(BASE / "weekplan.docx"),
        },
        "runtime": {
            "python": str(PYTHON),
            "python_version": run(str(PYTHON), "--version"),
            "renderer": str(RENDERER),
            "soffice": str(SOFFICE),
            "soffice_version": run(str(SOFFICE), "--version"),
            "pdfinfo": str(PDFINFO),
            "pdffonts": str(PDFFONTS),
            "pdffonts_role": "post-render diagnostic only; DOCX conversion used bundled render_docx.py and bundled soffice",
            "loader_tool": "load_workspace_dependencies was not exposed; verified bundled runtime paths were used explicitly",
            "fontconfig_file": str(FONTCONFIG),
            "fontconfig_sha256": sha256(FONTCONFIG),
            "isolated_font_home": str(BASE / "fontcheck-home"),
            "microsoft_word": shutil.which("winword") or shutil.which("WINWORD.EXE"),
            "platform": platform.platform(),
            "python_locale": {key: os.environ.get(key) for key in ("LANG", "LC_ALL", "LC_CTYPE")},
            "render_commands": render_commands,
        },
        "scripts": {
            name: {
                "path": str(BASE / name),
                "sha256": sha256(BASE / name),
            }
            for name in (
                "make_layout_samples.py",
                "make_compact_candidates.py",
                "write_layout_manifest.py",
                "verify_layout.py",
                "reproduce.sh",
            )
        },
        "artifact_report": {
            "path": str(BASE / "layout-artifact.md"),
            "sha256": sha256(BASE / "layout-artifact.md"),
        },
        "font_environment": {
            "font_inputs": font_inputs,
            "isolated_home_fc_match": font_match,
            "note": "The renderer's per-run temporary HOME cannot see the user font by default. Every current sample render set FONTCONFIG_FILE to the dedicated config, which includes the installed SimSun directory; actual PDF font embedding is checked below with pdffonts.",
        },
        "template_and_product_boundaries": {
            "template_modified": False,
            "product_renderer_modified": False,
            "qualification_profile_modified": False,
            "formal_export": False,
            "active_binding": False,
            "database_or_deployment": False,
            "windows_word_gate": "BLOCKED: winword is unavailable in this environment",
        },
        "documents": {},
        "renders": {},
        "budget_observation": {
            "short_fixture_chars": "362 (normal five), 378 (each six-day)",
            "long_fixture_chars": "1407 (normal five), 1488 (each six-day)",
            "short_pages": "1 page for all three variants in the current SimSun-configured bundled Linux render",
            "long_pages": "2 pages for all three variants in the current SimSun-configured bundled Linux render",
            "compact_candidate": "491 characters/1 page for five days; 523 characters/1 page for both six-day variants with SimSun (the prior Noto-only render was 2 pages for the six-day candidates and is not this evidence)",
            "shrink_confirmation": "The compact candidates preserve all fixed counts. Any product shortening policy still requires a field-level diff and fresh visual review under target Linux and Windows Word; do not auto-truncate, remove counts, or reduce the requested type/spacing/page geometry.",
        },
    }
    for stem, render_dir in all_specs:
        path = BASE / f"{stem}.docx"
        data["documents"][stem] = doc_info(path)
        data["renders"][stem] = render_info(BASE / render_dir, stem)
    probe_pdf = BASE / "render-fontcheck-six-short" / "preceding-sunday-six-short.pdf"
    data["font_probe"] = {
        "sample_docx": str(BASE / "preceding-sunday-six-short.docx"),
        "sample_docx_sha256": sha256(BASE / "preceding-sunday-six-short.docx"),
        "pdf": pdf_info(probe_pdf),
        "command": f"env FONTCONFIG_FILE={FONTCONFIG} {PYTHON} {RENDERER} {BASE / 'preceding-sunday-six-short.docx'} --output_dir {BASE / 'render-fontcheck-six-short'} --emit_pdf --verbose",
    }
    (BASE / "layout-manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(BASE / "layout-manifest.json")


if __name__ == "__main__":
    main()
