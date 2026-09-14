"""Read-only verification of the WP-A closure bytes and recorded sample matrix."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = "specs/weekly-plan-authoring/evidence/"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", help="Verify committed Git bytes instead of worktree")
    parser.add_argument("--pdf", action="store_true", help="Read existing PDFs with PyMuPDF")
    args = parser.parse_args()

    def read(relative: str) -> bytes:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe manifest path: {relative}")
        if args.revision:
            return subprocess.run(
                ["git", "show", f"{args.revision}:{relative}"],
                cwd=ROOT,
                capture_output=True,
                check=True,
            ).stdout
        return (ROOT / path).read_bytes()

    count = 0
    for name in (
        "WP-A-Windows-20260910-manifest.json",
        "WP-A-LibreOffice-Windows-20260910-manifest.json",
        "WP-A-closure-20260910-manifest.json",
    ):
        manifest = json.loads(read(EVIDENCE + name))
        for path, expected in manifest["files"].items():
            data = read(path)
            if len(data) != expected["bytes"]:
                raise ValueError(f"Size mismatch: {path}")
            if hashlib.sha256(data).hexdigest() != expected["sha256"]:
                raise ValueError(f"Hash mismatch: {path}")
        count += len(manifest["files"])
        if "samples" not in manifest:
            continue
        if len(manifest["samples"]) != 9:
            raise ValueError(f"Expected nine samples: {name}")
        for sample in manifest["samples"]:
            pages = 2 if "-long" in sample["pdf"] else 1
            if sample["pdf_pages"] != pages or len(sample["pngs"]) != pages:
                raise ValueError(f"Page matrix mismatch: {sample['pdf']}")
            if "word_pages" in sample and (
                sample["word_pages"] != pages
                or sample["native_preview_pages"] != pages
                or len(sample["native_screenshots"]) != pages + 1
            ):
                raise ValueError(f"Native page matrix mismatch: {sample['pdf']}")
            if args.pdf:
                import pymupdf

                with pymupdf.open(stream=read(sample["pdf"]), filetype="pdf") as pdf:
                    if len(pdf) != pages:
                        raise ValueError(f"Actual PDF page mismatch: {sample['pdf']}")
        print(f"{name}: nine samples, six one-page and three two-page results")
    print(f"Verified {count} manifest entries; integrity only, not product/Office PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
