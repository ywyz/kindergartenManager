#!/bin/sh
set -eu

BASE=/home/ywyz/code/km-wpa-fonts-20260909/layout
PYTHON=/home/ywyz/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12
RENDERER=/home/ywyz/.codex/plugins/cache/openai-primary-runtime/documents/26.904.11930/skills/documents/render_docx.py
FONTCONFIG_FILE=$BASE/fontconfig/fonts.conf

"$PYTHON" "$BASE/make_layout_samples.py"
"$PYTHON" "$BASE/make_compact_candidates.py"

render_one() {
    stem=$1
    out=$2
    env FONTCONFIG_FILE="$FONTCONFIG_FILE" "$PYTHON" "$RENDERER" \
        "$BASE/$stem.docx" --output_dir "$BASE/$out" --emit_pdf --verbose
}

render_one normal-five-short render-final-normal-five-short
render_one normal-five-long render-final-normal-five-long
render_one preceding-sunday-six-short render-final-preceding-sunday-six-short
render_one preceding-sunday-six-long render-final-preceding-sunday-six-long
render_one saturday-six-short render-final-saturday-six-short
render_one saturday-six-long render-final-saturday-six-long
render_one normal-compact-candidate render-compact-normal
render_one sunday-compact-candidate render-compact-sunday
render_one saturday-compact-candidate render-compact-saturday

"$PYTHON" "$BASE/verify_layout.py"
"$PYTHON" "$BASE/write_layout_manifest.py"
