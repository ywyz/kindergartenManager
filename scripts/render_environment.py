#!/usr/bin/env python3
"""Render runtime environment verifier.

Reports the versions of the tools, fonts, and seed file used by the shared
weekly Word export pipeline. Fails closed if any required tool or font is
missing, or if the observed font family does not match the controlled contract.
"""

from __future__ import annotations

import asyncio
import json
import sys
from hashlib import sha256
from pathlib import Path

# Allow running the script directly from scripts/ before the package is on PATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.integration.word_export.shared_weekly_word import SEED_PATH, SEED_SHA256
from app.service.shared_weekly.layout_contracts import FONT_FAMILY

REQUIRED_TOOLS: list[tuple[str, list[str]]] = [
    ("libreoffice", ["--version"]),
    ("pdftotext", ["-v"]),
    ("pdfinfo", ["-v"]),
    ("pdftocairo", ["-v"]),
    ("fc-match", ["-f", "%{family}", FONT_FAMILY]),
]

REQUIRED_PACKAGES = [
    "libreoffice-writer",
    "poppler-utils",
    "fontconfig",
    "fonts-noto-cjk",
    "gcc",
]


async def _run(name: str, args: list[str]) -> str:
    """Run a tool and return its combined stdout/stderr text."""
    process = await asyncio.create_subprocess_exec(
        name,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise RuntimeError(f"{name} timed out") from None
    text = (stdout + b"\n" + stderr).decode("utf-8", errors="replace").strip()
    if process.returncode != 0:
        raise RuntimeError(f"{name} exited {process.returncode}")
    return text


async def _dpkg_version(package: str) -> str | None:
    """Return the installed dpkg version for a package, or None."""
    try:
        return await _run("dpkg-query", ["-W", "-f=${Version}", package]) or None
    except (OSError, RuntimeError):
        return None


async def verify() -> tuple[dict, list[str]]:
    """Collect tool/font/package evidence and return report plus errors."""
    errors: list[str] = []
    tools: dict[str, str | None] = {}

    for name, args in REQUIRED_TOOLS:
        try:
            tools[name] = await _run(name, args)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")
            tools[name] = None

    font_observed = tools.get("fc-match") or ""
    font_ok = FONT_FAMILY in (font_observed.split(",") if font_observed else [])
    if not font_ok:
        errors.append(
            f"font family mismatch: expected {FONT_FAMILY!r}, observed {font_observed!r}"
        )

    font_path = None
    font_sha256 = None
    try:
        font_path = await _run("fc-match", ["-f", "%{file}", FONT_FAMILY])
        font_sha256 = sha256(Path(font_path).read_bytes()).hexdigest()
    except (OSError, RuntimeError) as exc:
        errors.append(f"font file: {exc}")

    seed_path = Path(SEED_PATH)
    seed_ok = (
        seed_path.exists() and sha256(seed_path.read_bytes()).hexdigest() == SEED_SHA256
    )
    if not seed_ok:
        errors.append(f"seed file missing or sha256 mismatch: {SEED_PATH}")

    packages: dict[str, str | None] = {}
    for package in REQUIRED_PACKAGES:
        packages[package] = await _dpkg_version(package)
        if not packages[package]:
            errors.append(f"package missing: {package}")

    report = {
        "font_family": FONT_FAMILY,
        "font_observed": font_observed,
        "font_path": font_path,
        "font_sha256": font_sha256,
        "font_ok": font_ok,
        "seed_path": str(SEED_PATH),
        "seed_sha256_ok": seed_ok,
        "tools": tools,
        "packages": packages,
        "errors": errors,
    }
    return report, errors


def main() -> int:
    report, errors = asyncio.run(verify())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if errors:
        print(f"FAIL: {len(errors)} issue(s)", file=sys.stderr)
        return 1
    print("OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
