"""Prepare real LibreOffice fixtures, then seal an explicitly reviewed catalog.

Runs inside the deployment image. Inputs are preserved application body JSON,
not synthetic authority artifacts. This command never activates a catalog.
"""

import argparse
import asyncio
import json
import subprocess
from hashlib import sha256
from pathlib import Path

from app.integration.word_export.shared_weekly_word import (
    SEED_PATH,
    SEED_SHA256,
    fill_document,
)
from app.service.shared_weekly.authoring_contracts import WeeklyAuthoringDraft
from app.service.shared_weekly.layout_contracts import FONT_FAMILY, PROFILE, WeekDisplay


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True, timeout=120).strip()


def record(path: Path) -> dict:
    return {"file": path.name, "sha256": digest(path)}


async def prepare(inputs: Path, output: Path) -> None:
    from app.integration.word_export.released_weekly_monthly_word_port import (
        build_released_weekly_monthly_word_port,
    )
    from app.service.template_center.contracts import DocumentType

    data = json.loads(inputs.read_text())
    if set(data) != {"cases"} or len(data["cases"]) != 2:
        raise ValueError("exactly five and six column inputs required")
    family = run("fc-match", "-f", "%{family}", FONT_FAMILY)
    if FONT_FAMILY not in family.split(","):
        raise ValueError("required font missing")
    font = Path(run("fc-match", "-f", "%{file}", FONT_FAMILY))
    version = run("libreoffice", "--version")
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    binding = await build_released_weekly_monthly_word_port().resolve_active(
        1, DocumentType.WEEKLY_ACTIVITY_PLAN
    )
    client = {"product": "LibreOffice", "version": version}
    candidate = {
        "schema": "weekly-layout-qualification.v1",
        "profile": PROFILE,
        "template_sha256": SEED_SHA256,
        "renderer": client,
        "client": client,
        "role": "libreoffice-rendered",
        "fixtures": [],
        "released_binding": {
            "template_version_id": str(binding.template_version_id),
            "version": binding.version,
            "content_sha256": binding.content_sha256,
            "contract_id": binding.contract_id,
            "contract_version": binding.contract_version,
        },
    }
    for case in data["cases"]:
        body_path = inputs.parent / case["body_file"]
        if (
            body_path.is_symlink()
            or body_path.resolve().parent != inputs.parent.resolve()
        ):
            raise ValueError("body must be a direct regular input file")
        if digest(body_path) != case["body_sha256"]:
            raise ValueError("body hash mismatch")
        body = WeeklyAuthoringDraft.parse(body_path.read_text())
        columns = len(body.calendar.columns)
        if columns not in (5, 6):
            raise ValueError("invalid column count")
        docx = output / f"{columns}.docx"
        if docx.exists():
            raise ValueError("duplicate column case")
        docx.write_bytes(
            fill_document(SEED_PATH.read_bytes(), body, WeekDisplay(**case["display"]))
        )
        run(
            "libreoffice",
            "-env:UserInstallation=" + (output / f"profile-{columns}").as_uri(),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output),
            str(docx),
        )
        pdf = docx.with_suffix(".pdf")
        info = run("pdfinfo", str(pdf))
        pages = int(
            next(
                line.split(":", 1)[1]
                for line in info.splitlines()
                if line.startswith("Pages:")
            )
        )
        run(
            "pdftocairo",
            "-png",
            "-singlefile",
            "-r",
            "110",
            str(pdf),
            str(output / f"{columns}-page-1"),
        )
        png = output / f"{columns}-page-1.png"
        run("pdftotext", "-layout", str(pdf), str(output / f"{columns}.txt"))
        (output / f"{columns}-pdfinfo.txt").write_text(info)
        if pages != 1:
            raise ValueError(
                f"{columns} column fixture has {pages} pages; no catalog sealed"
            )
        candidate["fixtures"].append(
            {
                "columns": columns,
                "body_sha256": case["body_sha256"],
                "artifacts": {
                    "docx": record(docx),
                    "pdf": record(pdf),
                    "page-1.png": record(png),
                },
            }
        )
    (output / "candidate.json").write_text(
        json.dumps(candidate, ensure_ascii=False, indent=2)
    )
    (output / "runtime.json").write_text(
        json.dumps(
            {
                "renderer": client,
                "font_family": family,
                "font_file_sha256": digest(font),
                "inputs_sha256": digest(inputs),
                "profile": PROFILE,
                "role": "actual-rendering-awaiting-operator-review",
            },
            indent=2,
        )
    )
    print(
        json.dumps(
            {
                "candidate_sha256": digest(output / "candidate.json"),
                "status": "PREPARED_NOT_ACTIVATED",
            }
        )
    )


def seal(output: Path, review: Path) -> None:
    candidate_path = output / "candidate.json"
    decision = json.loads(review.read_text())
    if decision != {
        "candidate_sha256": digest(candidate_path),
        "five_columns": "approved",
        "six_columns": "approved",
    }:
        raise ValueError("explicit candidate-bound operator review required")
    candidate = json.loads(candidate_path.read_text())
    for fixture in candidate["fixtures"]:
        artifacts = fixture["artifacts"]
        for item in artifacts.values():
            path = output / item["file"]
            if (
                path.is_symlink()
                or path.resolve().parent != output.resolve()
                or digest(path) != item["sha256"]
            ):
                raise ValueError("rendered artifact changed")
        observation = {
            "schema": "weekly-layout-native-observation.v1",
            "role": candidate["role"],
            "client": candidate["client"],
            "renderer": candidate["renderer"],
            "columns": fixture["columns"],
            "body_sha256": fixture["body_sha256"],
            "template_sha256": candidate["template_sha256"],
            "profile": PROFILE,
            "pages": 1,
            "page_observations": ["all_text_visible_no_clipping_no_overflow"],
            "font": FONT_FAMILY,
            "font_pt": 12,
            "line_pt": 20,
            "fixed_counts": [2, 1, 3, 1, 3, 3, 3, 3, 3, 1],
            "docx_sha256": artifacts["docx"]["sha256"],
            "pdf_sha256": artifacts["pdf"]["sha256"],
            "png_sha256": artifacts["page-1.png"]["sha256"],
        }
        report = output / f"{fixture['columns']}-observation.json"
        with report.open("x") as handle:
            json.dump(observation, handle, ensure_ascii=False, indent=2)
        artifacts["native-report.json"] = record(report)
        fixture["observation"] = digest(report)
    with (output / "manifest.json").open("x") as handle:
        json.dump(candidate, handle, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {
                "manifest_sha256": digest(output / "manifest.json"),
                "review_sha256": digest(review),
                "status": "SEALED_NOT_ACTIVATED",
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--inputs", type=Path, required=True)
    prepare_parser.add_argument("--output", type=Path, required=True)
    seal_parser = sub.add_parser("seal")
    seal_parser.add_argument("--output", type=Path, required=True)
    seal_parser.add_argument("--review", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        asyncio.run(prepare(args.inputs.resolve(), args.output.absolute()))
    else:
        seal(args.output.resolve(), args.review.resolve())


if __name__ == "__main__":
    main()
