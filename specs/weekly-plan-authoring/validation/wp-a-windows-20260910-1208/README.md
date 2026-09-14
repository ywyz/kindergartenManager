# Windows Word WP-A measurement, 2026-09-10

Synthetic fixtures only. New Windows outputs; not Linux reference files, product exports,
qualified templates, application acceptance, or deployment evidence.

The original nine DOCX remain in `../wp-a-simsun-20260909/samples/` unchanged.
Each sample subdirectory contains its Word PDF, every page at 144 dpi (`page-N.png`),
`word.json`, Poppler `pdfinfo.txt`, PDF text, and read-only `inspection.json` diagnostics.

## Commands actually executed

From repository root, PowerShell:

```powershell
git status --short
git remote -v
git rev-parse HEAD
git fetch origin handoff/wp-a-windows-20260910
git rev-parse HEAD
git rev-parse FETCH_HEAD
py -3 specs/weekly-plan-authoring/validation/verify_wp_a_bundle.py
# py was unavailable; supported fallback used, no application dependencies installed:
uv python install 3.14
uv run --no-project --python 3.14 python specs/weekly-plan-authoring/validation/verify_wp_a_bundle.py
& specs/weekly-plan-authoring/validation/wp-a-windows-20260910-1208/word_measure.ps1
uv run --no-project --python 3.14 --with pymupdf --with fonttools python -X utf8 specs/weekly-plan-authoring/validation/wp-a-windows-20260910-1208/inspect_outputs.py
```

`uv` resolved Python 3.14.6. This standard-library integrity check did not require
the application's Python 3.14.7 environment, imports, configuration or database.
Read-only PDF/font analysis additionally used PyMuPDF 1.28.2 and fontTools.

Each Word PDF was inspected/rendered using the existing bundled Poppler executables:

```powershell
$poppler = 'C:/Users/yw980/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin'
$runRoot = 'specs/weekly-plan-authoring/validation/wp-a-windows-20260910-1208'
foreach ($pdf in (Get-ChildItem $runRoot -Recurse -Filter '*.pdf')) {
    & "$poppler/pdfinfo.exe" $pdf.FullName | Set-Content (Join-Path $pdf.DirectoryName 'pdfinfo.txt') -Encoding utf8
    & "$poppler/pdftoppm.exe" -r 144 -png $pdf.FullName (Join-Path $pdf.DirectoryName 'page')
}
```

Do not rerun into this frozen measurement directory. For a new measurement copy the
scripts into a fresh sibling directory and record its actual date, environment and hashes.
`word_measure.ps1` refuses existing sample output directories; no Save/SaveAs/PrintOut,
no OpenAndRepair, alerts enabled, read-only opening, no recent-file registration,
Close/ Quit with `wdDoNotSaveChanges`. PDF export was performed by Microsoft Word,
not by Poppler, Python or LibreOffice. Poppler only rasterized existing Word PDFs.

## Failed diagnostics retained as limitations

- Computer Use `@oai/sky.list_apps()` failed with native pipe os error 2 on initial,
  retry, and reset/reinitialize retry. No native screenshot was obtained or fabricated.
- The first bundled Python dependency probe lacked PyMuPDF; uv supplied isolated analysis dependencies.
- The initial inspection script mistook manual line breaks (`w:br`) for separate paragraphs
  and raised `ValueError: '目标：' is not in list`. The read-only parser now handles `w:br`.
  No DOCX/PDF/PNG was regenerated or changed for this correction.
- COM aggregate font/paragraph properties returned Word's mixed/undefined sentinel
  `9999999` and an empty Far East font name. These are not format PASS evidence;
  nonempty OOXML runs/paragraphs and actual PDF spans are separately inspected.

## User observation pending

The user agreed in this conversation to supply observations later; this is not a result.
For each of the nine originals, open read-only and enter Print Preview without saving.
Record actual observation time, any repair/conversion/compatibility/font-substitution warning,
page count, date-column order, right/bottom border, last outdoor line, area guidance 3,
and final home-school row. Long files require both pages. Distinguish compatibility mode
from a warning dialog; COM reports mode 15 for every file. Record observed preview zoom
and any difference from the measured default Brother A4 printer. No actual print job is needed.

Necessary screenshots must come from the actual Word window/preview and be checked
for account information before adding to evidence. Until supplied, native observation
and warning/font-substitution checks remain BLOCKED. PDF visual review is separate.

Main evidence: `../../evidence/WP-A-Windows-20260910.md`.
