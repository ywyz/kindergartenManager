# Weekplan layout evidence contract

Reference: `/home/ywyz/code/km-wpa-20260908/templates/weekplan.docx`

- Reference SHA-256: `f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b`
- Reference render: `template-reference-render/`
- Reference render pages: 2 A4 pages; the retained file contains two 9 x 7
  tables and two repeated title/header blocks.
- Reference style evidence: `template-style-evidence.json`
- Reference audits: Documents `render_docx.py`, `section_audit.py`,
  `style_lint.py`, `heading_audit.py`, `images_audit.py`, `fields_report.py`,
  and `content_controls.py list` were run read-only.

## Page system

The retained section is one portrait section with A4 page dimensions 8.268 x
11.693 inches. Margins are left/right 0.5 inches and top/bottom 0.197 inches
(the source XML uses 0.2-inch intent). There are no headers, footers, fields,
images, content controls, or heading styles. Each retained table uses the
source border and merge structure.

The first table is the task-local reference for the feasibility samples. Its
rows are: header, morning talk, collective activity, outdoor game, area game,
weekly focus, environment creation, life habits, and home-school cooperation.
The source first-table grid is 933, 920, 1842, 1776, 1845, 1766, and 1970 twips;
source row heights are 291, 90, 576, 1121, 3100, 1216, 834, 890, and 446 twips.
The second table is removed only in the task-local copies so the copy can test
one-page feasibility. The retained template is never changed and its hash is
rechecked after generation.

The reference source grid is 933, 920, 1842, 1776, 1845, 1766, and 1970
twips, totalling 11,052 twips. The A4 page width is 11,906 twips and the
retained side margins leave about 10,466 twips of usable text width, so the
source grid is 586 twips wider than that usable area. The source template was
not changed. Current task-local five-day candidates use
933, 920, 1722, 1722, 1723, 1723, and 1723 twips, totalling exactly 10,466.
Current six-day candidates add one date column and use 933, 920, 1435, 1435,
1435, 1436, 1436, and 1436 twips, also totalling exactly 10,466. Thus the
page geometry and usable table width are now aligned, while the five- and
six-day column widths differ. The added six-day cells explicitly copy the
retained border rules before horizontal merges; the current screenshots show
the top, bottom, and right rules on the added date column. The game and
summary rows remain horizontally merged across all date columns. This is a
layout candidate only; it is not the released 2 x 9 x 7 structural profile and
cannot be used as template qualification or formal export evidence.

The earlier `render-final-*` images and PDFs from the over-width/missing-border
iteration are superseded. Only the latest files under the same `render-final-*`
paths, whose hashes are recorded in `evidence-manifest.json`, are current
diagnostic evidence.

## Typography and slots

The retained title is centered, bold, 16 pt 宋体. Header, people, labels, and
editable text are 12 pt 宋体. Task-local samples set every paragraph to exact
20 pt line spacing and zero paragraph spacing, while preserving the title
size/boldness. The sample copies preserve the source labels `周次`, `学习活动`,
`晨间谈话`, `集体活动`, `游戏活动`, `户外游戏`, `区域游戏`, `本周重点`,
`环境创设`, `生活习惯培养`, and `家园共育`.

Editable slots are the first three body paragraphs (title, theme/class/week
header, teacher/caregiver line), six or five date header cells, the daily
morning and collective cells, merged outdoor and area cells, and the four
merged weekly summary cells. The outdoor slot contains exactly two collective
games and one autonomous game, with exactly three goals per game. The area
slot contains one focus area, exactly three goals, and exactly three guidance
items. Weekly focus, environment, and life-habit slots each contain exactly
three items; home-school cooperation is one paragraph.

## Fidelity gates

All six copies are synthetic layout fixtures. They must not be labeled formal
exports, active bindings, or qualification evidence. The first copy is retained
byte-for-byte at the recorded path and hash. All page counts and visual checks
are from the bundled Documents renderer and its private LibreOffice profile.
The container has no Microsoft Word and no 宋体 font: `fc-match 宋体` resolves
to Noto Serif CJK SC, and rendered PDFs embed Noto Serif CJK SC. Therefore page
geometry, merge, wrapping, and clipping observations are Linux renderer
observations only; font fidelity and Windows Word gates remain BLOCKED.

## Empirical length budget

The six retained fixtures are listed in `evidence-manifest.json`. With all
fixed slots and counts present, the shortest fixtures contain 362 table
characters for five days and 378 for six days; all three render to one A4
page. The long fixtures contain 1,407 and 1,488 table characters respectively;
all three render to two pages. A compact candidate at 491 characters renders
to one page for five days. The 523-character six-day compact candidates leave
only the final `家园共育` row on page 2, so they are a near-threshold diagnostic
and a confirmed one-page failure. These observations come from the bundled
Linux renderer and do not approve a product length limit.

The implementation follow-up must confirm any shortening policy by rendering
both five- and six-day fixtures under the bundled Linux runtime and Windows
Word after a real 宋体 environment is available. Candidate reductions may
shorten daily and merged-slot prose while preserving every fixed label,
content count, A4 geometry, 12 pt text, and exact 20 pt line spacing. The
check must reject clipping, overlap, orphan rows, automatic truncation, margin
reduction, or font reduction; a one-page claim requires every page to pass
visual inspection on both clients.
