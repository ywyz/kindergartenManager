"""Verify the portable synthetic WP-A bundle without opening the application."""

import hashlib
import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent / "wp-a-simsun-20260909"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    failures = []
    for relative, expected in manifest["files"].items():
        path = root / relative
        if not path.is_file():
            failures.append(f"missing: {relative}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
            failures.append(f"hash mismatch: {relative}")
        elif path.stat().st_size != expected["bytes"]:
            failures.append(f"size mismatch: {relative}")
    if failures:
        print("\n".join(failures))
        return 1
    print(
        f"Verified {len(manifest['files'])} files. This is integrity only, not Office PASS."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
