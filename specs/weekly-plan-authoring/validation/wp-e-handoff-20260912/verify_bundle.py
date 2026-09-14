"""Verify portable evidence bytes with Python standard library; no app startup."""

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
errors = []
for item in manifest["files"]:
    path = root / item["path"]
    if not path.is_file():
        errors.append(item["path"] + ": missing")
        continue
    raw = path.read_bytes()
    if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
        errors.append(item["path"] + ": byte/hash mismatch")
if errors:
    raise SystemExit("BLOCKED\n" + "\n".join(errors))
print(f"INTEGRITY_OK: {len(manifest['files'])} files; not Word or WP-E PASS")
