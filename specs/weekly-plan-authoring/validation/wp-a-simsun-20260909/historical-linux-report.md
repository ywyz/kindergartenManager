# Week plan layout feasibility evidence

This directory is a new, persistent WP-A diagnostic run on 2026-09-09. It was
rebuilt from the read-only template at
`/home/ywyz/code/km-wpa-20260908/templates/weekplan.docx`; it is not a rerun of
the removed `/tmp/km-wpa-layout-20260908` files and none of the removed sample
hashes are reused. The complete file, render, font, and command inventory is
`layout-manifest.json`.

## Reference and boundaries

The source template SHA-256 is
`f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b`. It is
A4 portrait with 11,906 × 16,838 twips and margins 720/720/284/284 twips. It
contains two 9 × 7 table copies and therefore renders as two pages. The source
template, released renderer, qualification profile, database, and deployment
were not changed. The task-local copy is retained as `weekplan.docx` with the
same hash.

The original source grid totals 11,052 twips, while the page body after the
retained side margins is about 10,466 twips. The synthetic candidates use a
width-capped grid so the table is inside that body width:

- Five days: `933, 920, 1722, 1722, 1723, 1723, 1723` = 10,466 twips.
- Six days: `933, 920, 1435, 1435, 1435, 1436, 1436, 1436` = 10,466 twips.

Six-day cells copy the retained rightmost-cell borders before adding the
column. The current XML and renders show continuous top, bottom, internal,
and right borders; game and summary rows remain merged across all date
columns. The 5/6-day task-local tables are layout candidates, not the
released 2 × 9 × 7 profile and not qualification or formal export evidence.

## Synthetic content and observed pages

Every sample contains the fixed labels, three teacher names, A4 geometry,
12 pt body text, 16 pt centered bold title, exact 20 pt paragraph line
spacing, two collective outdoor games and one autonomous game with three goals
each, one area with three goals and three guidance items, three weekly focus
items, three environment items, three life-habit items, and one home-school
paragraph. The short, long, and compact text are synthetic fixtures; character
counts describe these fixtures and are not a product limit.

| Candidate | Table characters (including literal spaces) | Pages in current SimSun-configured bundled render |
| --- | ---: | ---: |
| Normal five-day short | 362 | 1 |
| Normal five-day long Chinese | 1,407 | 2 |
| Preceding-Sunday six-day short | 378 | 1 |
| Preceding-Sunday six-day long Chinese | 1,488 | 2 |
| Saturday six-day short | 378 | 1 |
| Saturday six-day long Chinese | 1,488 | 2 |
| Normal compact candidate | 491 | 1 |
| Sunday compact candidate | 523 | 1 |
| Saturday compact candidate | 523 | 1 |

All 12 current page PNGs were opened at original resolution. The short and
compact pages show all table borders and content inside the A4 page, including
the last outdoor line, the third area guidance line, and the final home-school
row. Long pages split the large area/summary content across two pages with
complete glyphs and borders; the split is a two-page result, not a single-page
pass. No visual overlap or clipping was observed in this bundled render.

## Font and renderer evidence

The Documents skill was used with its bundled runtime:

- Python: `/home/ywyz/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12`
- Renderer: `/home/ywyz/.codex/plugins/cache/openai-primary-runtime/documents/26.904.11930/skills/documents/render_docx.py`
- LibreOffice: `/home/ywyz/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice`
- LibreOffice version: `LibreOfficeDev 26.8.0.0.alpha0 2c87e51eeaa2b413ff4ae097b2705eea1995d8e5`

The renderer changes `HOME` to a per-run temporary directory. A control check
with that temporary-home model and no extra font configuration resolved both
`宋体` and `SimSun` to Noto Serif CJK SC. A dedicated config at
`fontconfig/fonts.conf` was therefore used only for this run; it includes the
installed user-level SimSun directory and a cache inside this write root.
The exact current render commands include
`env FONTCONFIG_FILE=/home/ywyz/code/km-wpa-fonts-20260909/layout/fontconfig/fonts.conf`.
Under an isolated HOME with that config, `fc-match` resolves both names to
SimSun. Post-render `/usr/bin/pdffonts` diagnostics show `SimSun` with
`emb=yes`, `sub=yes`, and `uni=yes` for every current PDF. `pdffonts` is only a
font inspection diagnostic; conversion used bundled `render_docx.py` and
bundled `soffice`.

Microsoft Word is unavailable on this host. The Linux SimSun evidence does
not close the Windows Word gate or establish dual-platform acceptance. A
formal one-page decision also requires the target Windows Word render and
independent page inspection. The long samples remain two pages even with real
SimSun; any later shortening must preserve every fixed count, label, fact,
font, line spacing, and page geometry and must be approved through a field
level diff plus fresh rendering.

## Reproduction and output discipline

Run the two builders from this directory with the bundled Python, then run the
nine commands recorded in `layout-manifest.json`. The builders write only
this directory. The render PDFs and PNGs are QA evidence, not product exports.
The current manifest records each DOCX, PDF, PNG, script, fontconfig file,
and supplied font file hash. No hash from the removed `/tmp` run is claimed as
the current sample evidence.
