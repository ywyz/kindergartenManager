"""Prepare and verify the WP-E Windows native-observation handoff.

This helper is a stage-one Ubuntu utility.  It never installs a qualification,
changes the application schema, or marks a Word observation as complete.  A
candidate can only be regenerated after the coordinator supplies an exact,
clean Git SHA.  The generated package keeps LibreOffice runtime artifacts
separate from the PDF/PNG files returned by Microsoft Word in stage two.

The helper deliberately uses the old candidate manifest as an input ledger;
it does not trust its historical absolute ``source_body`` paths.  Body files
are resolved by case id below the explicitly supplied source root, and every
manifest-declared source artifact is checked before any new output is made.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

PROFILE = "shared-weekly-v3.v1"
TEMPLATE_SHA256 = "f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b"
QUALIFICATION_SCHEMA = "weekly-layout-qualification.v1"
NATIVE_OBSERVATION_SCHEMA = "weekly-layout-native-observation.v1"
HANDOFF_SCHEMA = "wp-e-windows-startup-handoff.v1"
HANDOFF_MANIFEST = "handoff-manifest.json"
DELIVERY_SCHEMA = "wp-e-startup-delivery.v1"
DELIVERY_MANIFEST = "delivery-manifest.json"

EXPECTED_CASE_IDS = (
    "five-normal",
    "five-long",
    "five-long-dedup",
    "five-holiday",
    "five-holiday-long",
    "five-holiday-long-dedup",
    "six-sunday-normal",
    "six-sunday-long",
    "six-sunday-long-dedup",
    "six-saturday-normal",
    "six-saturday-long",
    "six-saturday-long-dedup",
)

# This is the closed field set enforced by LayoutAuthority._read.  Keeping it
# explicit makes drift in the handoff visible in review; the helper does not
# replace or extend the product validator.
NATIVE_OBSERVATION_FIELDS = (
    "schema",
    "role",
    "client",
    "renderer",
    "columns",
    "body_sha256",
    "template_sha256",
    "profile",
    "pages",
    "page_observations",
    "font",
    "font_pt",
    "line_pt",
    "fixed_counts",
    "docx_sha256",
    "pdf_sha256",
    "png_sha256",
)

FIXED_COUNTS = [2, 1, 3, 1, 3, 3, 3, 3, 3, 1]
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SOURCE_MODULES = (
    "app.integration.word_export.shared_weekly_word",
    "app.integration.word_export.released_weekly_monthly_word_port",
    "app.service.shared_weekly.authoring_contracts",
    "app.service.shared_weekly.layout_contracts",
    "app.service.template_center.contracts",
)


class HandoffError(ValueError):
    """Stable user-facing failure for unsafe or incomplete handoff input."""


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HandoffError(f"invalid JSON: {path}") from exc
    if type(value) is not dict:
        raise HandoffError(f"JSON object required: {path}")
    return value


def _require_absolute_directory(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise HandoffError(f"{label} must be an absolute path: {path}")
    return path


def _reject_symlink_components(path: Path, root: Path) -> None:
    """Reject a symlink anywhere in a path relative to a trusted root."""

    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise HandoffError(f"path escapes root: {path}") from exc
    current = root
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise HandoffError(f"symlink is not accepted: {current}")


def _safe_relative(root: Path, relative: str, *, label: str) -> Path:
    if type(relative) is not str or not relative or "\\" in relative:
        raise HandoffError(f"unsafe {label} path: {relative!r}")
    candidate = Path(relative)
    if candidate.is_absolute() or candidate.name in ("", ".", ".."):
        raise HandoffError(f"unsafe {label} path: {relative!r}")
    root_path = root.absolute()
    lexical = root_path / candidate
    # Check the lexical path before resolving it.  Resolving first would erase
    # a symlink component and could turn an unsafe source file into an accepted
    # path inside the trusted root.
    _reject_symlink_components(lexical, root_path)
    try:
        resolved = lexical.resolve(strict=False)
        resolved.relative_to(root_path.resolve())
    except (OSError, ValueError) as exc:
        raise HandoffError(f"{label} escapes root: {relative!r}") from exc
    return resolved


def _safe_manifest_file(path: str, *, label: str, plain: bool = True) -> str:
    if type(path) is not str or not path or Path(path).is_absolute():
        raise HandoffError(f"unsafe manifest {label}: {path!r}")
    candidate = Path(path)
    if "\\" in path or path in (".", "..") or any(
        part in ("", ".", "..") for part in candidate.parts
    ):
        raise HandoffError(f"unsafe manifest {label}: {path!r}")
    if plain and candidate.name != path:
        raise HandoffError(f"manifest {label} must be a plain filename: {path!r}")
    return path


def _declared_hash(entry: Any, *, label: str) -> str:
    if type(entry) is not dict or set(entry) - {"file", "sha256", "bytes"}:
        raise HandoffError(f"invalid {label} declaration")
    digest = entry.get("sha256")
    if type(digest) is not str or not HEX64.fullmatch(digest):
        raise HandoffError(f"invalid {label} SHA256")
    if "bytes" in entry and (
        type(entry["bytes"]) is not int or entry["bytes"] < 0
    ):
        raise HandoffError(f"invalid {label} byte count")
    return digest


def _check_file(path: Path, expected: dict[str, Any], *, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise HandoffError(f"missing or symlinked {label}: {path}")
    raw = path.read_bytes()
    digest = _declared_hash(
        {key: expected[key] for key in ("sha256", "bytes") if key in expected},
        label=label,
    )
    expected_bytes = expected.get("bytes")
    if expected_bytes is not None and len(raw) != expected_bytes:
        raise HandoffError(f"size mismatch for {label}: {path}")
    if _sha256_bytes(raw) != digest:
        raise HandoffError(f"hash mismatch for {label}: {path}")
    return {"bytes": len(raw), "sha256": digest}


def _manifest_source_files(case: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    artifacts = case.get("artifacts")
    if type(artifacts) is not dict or not artifacts:
        raise HandoffError(f"case artifacts missing: {case.get('id')!r}")
    for name, entry in artifacts.items():
        if type(name) is not str or name == "" or "/" in name or "\\" in name:
            raise HandoffError(f"unsafe artifact name in {case.get('id')!r}")
        # The preserved WP-E manifest predates the richer declaration shape
        # used by this helper and stores artifact values as bare SHA256
        # strings.  Normalize that historical shape without changing the
        # source manifest on disk.
        if type(entry) is str:
            if not HEX64.fullmatch(entry):
                raise HandoffError(f"invalid artifact SHA256 in {case.get('id')!r}")
            entry = {"file": name, "sha256": entry}
        if type(entry) is not dict or entry.get("file") != name:
            raise HandoffError(f"artifact declaration filename differs: {name!r}")
        yield name, entry


def validate_source_manifest(manifest_path: Path, source_root: Path) -> dict[str, Any]:
    """Validate the twelve preserved source cases without touching them."""

    manifest_path = _require_absolute_directory(manifest_path, "source manifest")
    source_root = _require_absolute_directory(source_root, "source root")
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise HandoffError(f"source manifest is not a regular file: {manifest_path}")
    if not source_root.is_dir() or source_root.is_symlink():
        raise HandoffError(f"source root is not a regular directory: {source_root}")
    data = _json_read(manifest_path)
    cases = data.get("cases")
    if type(cases) is not list or len(cases) != len(EXPECTED_CASE_IDS):
        raise HandoffError("source manifest must contain exactly twelve cases")
    by_id: dict[str, dict[str, Any]] = {}
    for case in cases:
        if type(case) is not dict or type(case.get("id")) is not str:
            raise HandoffError("source case id missing")
        case_id = case["id"]
        if case_id in by_id:
            raise HandoffError(f"duplicate source case: {case_id}")
        by_id[case_id] = case
    if tuple(sorted(by_id)) != tuple(sorted(EXPECTED_CASE_IDS)):
        raise HandoffError("source case set differs from the twelve WP-E cases")

    for case_id in EXPECTED_CASE_IDS:
        case = by_id[case_id]
        source_body_digest = case.get("source_body_sha256")
        if type(source_body_digest) is not str or not HEX64.fullmatch(source_body_digest):
            raise HandoffError(f"invalid source body SHA256: {case_id}")
        case_dir = _safe_relative(source_root, case_id, label="case")
        if not case_dir.is_dir() or case_dir.is_symlink():
            raise HandoffError(f"missing source case directory: {case_dir}")
        body_path = _safe_relative(case_dir, "body.json", label="body")
        if not body_path.is_file() or body_path.is_symlink():
            raise HandoffError(f"missing source body: {body_path}")
        body_bytes = body_path.read_bytes()
        if _sha256_bytes(body_bytes) != source_body_digest:
            raise HandoffError(f"source body hash mismatch: {case_id}")
        declared = {"body.json": {"file": "body.json", "sha256": source_body_digest}}
        for name, entry in _manifest_source_files(case):
            safe_name = _safe_manifest_file(name, label="artifact")
            artifact_path = _safe_relative(case_dir, safe_name, label="artifact")
            _check_file(artifact_path, entry, label=f"{case_id}/{safe_name}")
            declared[safe_name] = entry
        if "body.json" in declared:
            digest = _declared_hash(declared["body.json"], label=f"{case_id}/body.json")
            if digest != source_body_digest:
                raise HandoffError(f"body declaration differs from source body hash: {case_id}")
    return data


def _git(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise HandoffError(f"git check failed: {' '.join(args)}") from exc
    return completed.stdout.strip()


def validate_frozen_repo(repo: Path, frozen_sha: str) -> None:
    """Require an exact clean Git worktree before candidate regeneration."""

    repo = _require_absolute_directory(repo, "repo")
    if type(frozen_sha) is not str or not HEX40.fullmatch(frozen_sha):
        raise HandoffError("--frozen-sha must be a 40-character lowercase SHA")
    root = _git(repo, "rev-parse", "--show-toplevel")
    if Path(root).resolve() != repo.resolve():
        raise HandoffError(f"repo is not the requested worktree: {repo}")
    actual = _git(repo, "rev-parse", "--verify", "HEAD")
    if actual != frozen_sha:
        raise HandoffError(f"frozen SHA mismatch: expected {frozen_sha}, got {actual}")
    if _git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise HandoffError("repo must be clean before candidate regeneration")


def _run_output(command: list[str], *, cwd: Path | None = None) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise HandoffError(f"command timed out: {command[0]}") from exc
    except (OSError, subprocess.CalledProcessError) as exc:
        raise HandoffError(f"command failed: {command[0]}") from exc
    return (completed.stdout or completed.stderr).strip()


def _runtime_tools() -> dict[str, str]:
    required = (
        "libreoffice",
        "pdftoppm",
        "pdfinfo",
        "pdftotext",
        "pdftocairo",
        "fc-match",
    )
    missing = [name for name in required if shutil.which(name) is None]
    if missing:
        raise HandoffError("required render tools missing: " + ", ".join(missing))
    lo_version = _run_output(["libreoffice", "--version"])
    poppler_version = _run_output(["pdftoppm", "-v"])
    resolved_family = _run_output(["fc-match", "-f", "%{family}", "SimSun"])
    resolved_file = _run_output(["fc-match", "-f", "%{file}", "SimSun"])
    if "SimSun" not in resolved_family.split(","):
        raise HandoffError(
            f"SimSun is not resolved by fc-match (got {resolved_family!r}); no substitute is accepted"
        )
    font_path = Path(resolved_file)
    if not font_path.is_file() or font_path.is_symlink():
        raise HandoffError(f"fc-match returned no regular SimSun file: {resolved_file!r}")
    return {
        "libreoffice": lo_version,
        "poppler": poppler_version,
        "font_family": resolved_family,
        "font_file": resolved_file,
        "font_file_sha256": _sha256_file(font_path),
    }


def _product_source_records(repo: Path) -> list[dict[str, str]]:
    """Import the renderer only from the requested frozen worktree."""

    repo = repo.resolve()
    repo_string = str(repo)
    if repo_string not in sys.path:
        sys.path.insert(0, repo_string)
    try:
        from app.integration.word_export import (
            released_weekly_monthly_word_port,
            shared_weekly_word,
        )
        from app.service.shared_weekly import authoring_contracts, layout_contracts
        from app.service.template_center import contracts as template_contracts
    except (ImportError, OSError) as exc:
        raise HandoffError(f"product imports failed from frozen repo: {repo}") from exc

    modules = (
        shared_weekly_word,
        released_weekly_monthly_word_port,
        authoring_contracts,
        layout_contracts,
        template_contracts,
    )
    records: list[dict[str, str]] = []
    for module in modules:
        module_file = getattr(module, "__file__", None)
        if not module_file:
            raise HandoffError(f"product module has no source file: {module.__name__}")
        path = Path(module_file).resolve()
        try:
            relative = path.relative_to(repo)
        except ValueError as exc:
            raise HandoffError(
                f"product module is outside requested repo: {module.__name__}"
            ) from exc
        records.append(
            {
                "module": module.__name__,
                "path": relative.as_posix(),
                "sha256": _sha256_file(path),
            }
        )
    seed_path = Path(shared_weekly_word.SEED_PATH).resolve()
    try:
        seed_path.relative_to(repo)
    except ValueError as exc:
        raise HandoffError("controlled template is outside requested repo") from exc
    if _sha256_file(seed_path) != TEMPLATE_SHA256:
        raise HandoffError("controlled template hash changed")
    return records


def _released_binding(repo: Path) -> dict[str, Any]:
    """Read the immutable released binding used by LayoutAuthority checks."""

    repo = repo.resolve()
    repo_string = str(repo)
    if repo_string not in sys.path:
        sys.path.insert(0, repo_string)
    try:
        from app.integration.word_export.released_weekly_monthly_word_port import (
            build_released_weekly_monthly_word_port,
        )
        from app.service.template_center.contracts import DocumentType

        binding = asyncio.run(
            build_released_weekly_monthly_word_port().resolve_active(
                11, DocumentType.WEEKLY_ACTIVITY_PLAN
            )
        )
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        raise HandoffError("released binding could not be resolved") from exc
    result = {
        "template_version_id": str(binding.template_version_id),
        "version": binding.version,
        "content_sha256": binding.content_sha256,
        "contract_id": binding.contract_id,
        "contract_version": binding.contract_version,
    }
    if result["content_sha256"] != TEMPLATE_SHA256:
        raise HandoffError("released binding template hash differs from controlled template")
    return result


def _relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _file_record(path: Path, root: Path, *, role: str, case_id: str | None = None) -> dict[str, Any]:
    raw = path.read_bytes()
    result: dict[str, Any] = {
        "path": _relative_posix(path, root),
        "bytes": len(raw),
        "sha256": _sha256_bytes(raw),
        "role": role,
    }
    if case_id is not None:
        result["case_id"] = case_id
    return result


def _native_observation_not_run() -> dict[str, Any]:
    return {field: "NOT_RUN" for field in NATIVE_OBSERVATION_FIELDS}


def _case_output(
    *,
    case: dict[str, Any],
    case_id: str,
    body_path: Path,
    target: Path,
    package_root: Path,
    runtime: dict[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Regenerate one body through the application renderer and LO."""

    # Imports stay behind the SHA/source checks so verify and Windows can use
    # the helper without importing the application or creating a database.
    from app.integration.word_export.shared_weekly_word import (
        SEED_PATH,
        SharedWeeklyWordPort,
        fill_document,
    )
    from app.service.shared_weekly.authoring_contracts import WeeklyAuthoringDraft
    from app.service.shared_weekly.layout_contracts import WeekDisplay

    raw_body = body_path.read_bytes()
    body = WeeklyAuthoringDraft.parse(raw_body.decode("utf-8"))
    display_data = case.get("display")
    if type(display_data) is not dict or set(display_data) != {
        "class_name",
        "term_name",
        "week_number",
    }:
        raise HandoffError(f"invalid display for {case_id}")
    display = WeekDisplay(**display_data)
    inspection = asyncio.run(SharedWeeklyWordPort().inspect_local(body, display))
    expected_columns = 5 if case_id.startswith("five-") else 6
    actual_columns = len(body.calendar.columns) if body.calendar else None
    if actual_columns != expected_columns:
        raise HandoffError(
            f"column count differs from case id for {case_id}: "
            f"{actual_columns} != {expected_columns}"
        )
    seed = SEED_PATH.read_bytes()
    if _sha256_bytes(seed) != TEMPLATE_SHA256:
        raise HandoffError("controlled template hash changed")
    docx = fill_document(seed, body, display)
    body_out = target / "input.body.json"
    docx_out = target / "runtime-candidate.docx"
    body_out.write_bytes(raw_body)
    docx_out.write_bytes(docx)

    profile_dir = target / "lo-profile"
    profile_dir.mkdir(mode=0o700)
    _run_output(
        [
            "libreoffice",
            "-env:UserInstallation=" + profile_dir.as_uri(),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(target),
            str(docx_out),
        ]
    )
    produced_pdf = target / "runtime-candidate.pdf"
    if not produced_pdf.is_file():
        raise HandoffError(f"LibreOffice did not produce PDF for {case_id}")
    runtime_pdf = target / "runtime-lo.pdf"
    produced_pdf.replace(runtime_pdf)
    prefix = target / "runtime-lo-page"
    _run_output(["pdftoppm", "-png", str(runtime_pdf), str(prefix)])
    page_pngs = sorted(target.glob("runtime-lo-page-*.png"))
    if not page_pngs:
        raise HandoffError(f"pdftoppm did not produce page PNG for {case_id}")
    if inspection.pages and len(page_pngs) != inspection.pages:
        raise HandoffError(
            f"runtime page count differs from inspect_local for {case_id}: "
            f"{len(page_pngs)} != {inspection.pages}"
        )
    # Profiles are process material only; they are never part of the handoff.
    shutil.rmtree(profile_dir)

    files = [
        _file_record(body_out, package_root, role="preserved-body-input", case_id=case_id),
        _file_record(docx_out, package_root, role="runtime-candidate-docx", case_id=case_id),
        _file_record(runtime_pdf, package_root, role="ubuntu-libreoffice-runtime-pdf", case_id=case_id),
    ]
    files.extend(
        _file_record(png, package_root, role="ubuntu-libreoffice-runtime-png", case_id=case_id)
        for png in page_pngs
    )
    source_artifacts = {
        name: _declared_hash(entry, label=f"{case_id}/{name}")
        for name, entry in _manifest_source_files(case)
    }
    generated = {
        "body": files[0],
        "runtime_docx": files[1],
        "runtime_pdf": files[2],
        "runtime_png": [item for item in files if item["role"].endswith("runtime-png")],
    }
    return (
        {
            "id": case_id,
            "columns": actual_columns,
            "source_body_sha256": case["source_body_sha256"],
            "source_body": case["source_body"],
            "source_artifact_sha256": source_artifacts,
            "generated": generated,
            "local_inspection": {
                "fits": inspection.fits,
                "pages": inspection.pages,
                "reason": inspection.reason,
                "role": "local-unqualified-inspection",
            },
            "windows_return": {
                "status": "NOT_RUN",
                "word_export_pdf": None,
                "word_page_png": [],
                "native_observation": _native_observation_not_run(),
            },
            "runtime_role": "Ubuntu LibreOffice auxiliary evidence; never Windows Word evidence",
            "runtime_environment": runtime,
        },
        files,
    )


def prepare(
    *, repo: Path, source_manifest: Path, source_root: Path, output: Path, frozen_sha: str
) -> Path:
    """Create a new stage-one package after all frozen/source checks pass."""

    validate_frozen_repo(repo, frozen_sha)
    source = validate_source_manifest(source_manifest, source_root)
    output = _require_absolute_directory(output, "output")
    if output.exists() or output.is_symlink():
        raise HandoffError(f"output must not already exist: {output}")
    if not output.parent.is_dir():
        raise HandoffError(f"output parent must exist: {output.parent}")
    runtime = _runtime_tools()
    source_code = _product_source_records(repo)
    released_binding = _released_binding(repo)
    temp = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    os.chmod(temp, 0o700)
    try:
        cases_by_id = {case["id"]: case for case in source["cases"]}
        case_rows: list[dict[str, Any]] = []
        files: list[dict[str, Any]] = []
        for case_id in EXPECTED_CASE_IDS:
            case_dir = _safe_relative(source_root, case_id, label="case")
            body_path = _safe_relative(case_dir, "body.json", label="body")
            target = temp / case_id
            target.mkdir(mode=0o700)
            row, row_files = _case_output(
                case=cases_by_id[case_id],
                case_id=case_id,
                body_path=body_path,
                target=target,
                package_root=temp,
                runtime=runtime,
            )
            case_rows.append(row)
            files.extend(row_files)

        manifest = {
            "schema": HANDOFF_SCHEMA,
            "role": "stage-one-ubuntu-input; Windows stage-two and qualification stage-three NOT_RUN",
            "tested_code_sha": frozen_sha,
            "template_sha256": TEMPLATE_SHA256,
            "profile": PROFILE,
            "source_manifest": {
                "path": source_manifest.name,
                "sha256": _sha256_file(source_manifest),
            },
            "renderer": {
                "product": "LibreOffice",
                "version": runtime["libreoffice"],
                "role": "Ubuntu runtime auxiliary; not Microsoft Word evidence",
            },
            "font": {
                "requested": "SimSun",
                "resolved_family": runtime["font_family"],
                "resolved_file": runtime["font_file"],
                "role": "fc-match diagnostic only; no font file copied",
            },
            "poppler": {
                "version": runtime["poppler"],
                "role": "Ubuntu runtime rasterization auxiliary",
            },
            "source_code": source_code,
            "released_binding_tenant_id": 11,
            "released_binding": released_binding,
            "released_binding_role": "local immutable port metadata; not production activation or proof",
            "cases": case_rows,
            "files": files,
            "native_observation_fields": list(NATIVE_OBSERVATION_FIELDS),
            "formal_qualification": "NOT_RUN",
            "windows_word_observation": "NOT_RUN",
        }
        (temp / HANDOFF_MANIFEST).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temp.replace(output)
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    return output


def _validate_handoff_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if manifest.get("schema") != HANDOFF_SCHEMA:
        raise HandoffError("unexpected handoff schema")
    sha = manifest.get("tested_code_sha")
    if type(sha) is not str or not HEX40.fullmatch(sha):
        raise HandoffError("handoff tested_code_sha is invalid")
    if manifest.get("template_sha256") != TEMPLATE_SHA256:
        raise HandoffError("handoff template hash is invalid")
    if manifest.get("profile") != PROFILE:
        raise HandoffError("handoff profile is invalid")
    fields = manifest.get("native_observation_fields")
    if fields != list(NATIVE_OBSERVATION_FIELDS):
        raise HandoffError("native observation field set drifted")
    files = manifest.get("files")
    if type(files) is not list or not files:
        raise HandoffError("handoff files list is missing")
    seen: set[str] = set()
    for item in files:
        if type(item) is not dict or set(item) != {"path", "bytes", "sha256", "role", "case_id"}:
            raise HandoffError("invalid handoff file entry")
        relative = item["path"]
        _safe_manifest_file(relative, label="handoff file", plain=False)
        if relative in seen or relative == HANDOFF_MANIFEST:
            raise HandoffError(f"duplicate handoff file: {relative}")
        seen.add(relative)
        if type(item["bytes"]) is not int or item["bytes"] < 1:
            raise HandoffError(f"invalid handoff file size: {relative}")
        if type(item["sha256"]) is not str or not HEX64.fullmatch(item["sha256"]):
            raise HandoffError(f"invalid handoff file hash: {relative}")
        if type(item["role"]) is not str or not item["role"]:
            raise HandoffError(f"invalid handoff file role: {relative}")
        if type(item["case_id"]) is not str or item["case_id"] not in EXPECTED_CASE_IDS:
            raise HandoffError(f"invalid handoff file case: {relative}")
    cases = manifest.get("cases")
    if (
        type(cases) is not list
        or len(cases) != len(EXPECTED_CASE_IDS)
        or any(type(case) is not dict for case in cases)
        or {case.get("id") for case in cases} != set(EXPECTED_CASE_IDS)
        or manifest.get("formal_qualification") != "NOT_RUN"
        or manifest.get("windows_word_observation") != "NOT_RUN"
    ):
        raise HandoffError("handoff cases or pending stage states are invalid")
    binding = manifest.get("released_binding")
    if (
        type(binding) is not dict
        or set(binding) != {"template_version_id", "version", "content_sha256", "contract_id", "contract_version"}
        or binding.get("content_sha256") != TEMPLATE_SHA256
        or any(type(binding[key]) is not int or binding[key] < 1 for key in ("version", "contract_version"))
        or not binding.get("template_version_id")
        or not binding.get("contract_id")
        or manifest.get("released_binding_role") != "local immutable port metadata; not production activation or proof"
    ):
        raise HandoffError("handoff released dependency metadata is invalid")
    referenced = set()
    source_code = manifest.get("source_code")
    if (
        type(source_code) is not list or len(source_code) != len(SOURCE_MODULES)
        or any(type(row) is not dict for row in source_code)
        or {row.get("module") for row in source_code} != set(SOURCE_MODULES)
    ):
        raise HandoffError("frozen product source records are incomplete")
    for row in source_code:
        if (
            set(row) != {"module", "path", "sha256"}
            or row["path"] != row["module"].replace(".", "/") + ".py"
            or type(row["sha256"]) is not str or not HEX64.fullmatch(row["sha256"])
        ):
            raise HandoffError("frozen product source record is invalid")
    for case in cases:
        generated = case.get("generated")
        if (
            type(generated) is not dict
            or set(generated) != {"body", "runtime_docx", "runtime_pdf", "runtime_png"}
            or type(generated["runtime_png"]) is not list
            or not generated["runtime_png"]
            or type(case.get("source_body")) is not str
            or not case["source_body"]
            or case.get("windows_return") != {
                "status": "NOT_RUN", "word_export_pdf": None, "word_page_png": [],
                "native_observation": _native_observation_not_run(),
            }
        ):
            raise HandoffError("case sources, roles or pending Word observations are invalid")
        grouped = [generated[key] for key in ("body", "runtime_docx", "runtime_pdf")]
        grouped.extend(generated["runtime_png"])
        roles = ["preserved-body-input", "runtime-candidate-docx", "ubuntu-libreoffice-runtime-pdf"]
        roles.extend(["ubuntu-libreoffice-runtime-png"] * len(generated["runtime_png"]))
        for item, role in zip(grouped, roles, strict=True):
            if (
                item not in files or item["role"] != role
                or item["case_id"] != case["id"] or item["path"] in referenced
                or not item["path"].startswith(case["id"] + "/")
            ):
                raise HandoffError("case artifact role or file relationship is invalid")
            referenced.add(item["path"])
        if generated["body"]["sha256"] != case.get("source_body_sha256"):
            raise HandoffError("preserved source body hash differs from generated input")
        sources = case.get("source_artifact_sha256")
        if (
            type(sources) is not dict
            or sources.get("body.json") != case["source_body_sha256"]
            or "candidate.docx" not in sources
            or any(type(value) is not str or not HEX64.fullmatch(value) for value in sources.values())
        ):
            raise HandoffError("source artifact hash records are invalid")
        for name in sources:
            _safe_manifest_file(name, label="source artifact")
    if referenced != seen:
        raise HandoffError("handoff contains unreferenced artifacts")
    return files


def _validate_delivery_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if set(manifest) != {
        "schema",
        "tested_code_sha",
        "evidence_closure_sha",
        "files",
    }:
        raise HandoffError("delivery manifest fields are invalid")
    if manifest.get("schema") != DELIVERY_SCHEMA:
        raise HandoffError("unexpected delivery schema")
    for field in ("tested_code_sha", "evidence_closure_sha"):
        value = manifest.get(field)
        if type(value) is not str or not HEX40.fullmatch(value):
            raise HandoffError(f"delivery {field} is invalid")
    files = manifest.get("files")
    if type(files) is not list or not files:
        raise HandoffError("delivery files list is missing")
    seen: set[str] = set()
    for item in files:
        if type(item) is not dict or set(item) != {
            "path",
            "bytes",
            "sha256",
            "role",
        }:
            raise HandoffError("invalid delivery file entry")
        relative = item["path"]
        _safe_manifest_file(relative, label="delivery file", plain=False)
        if relative in seen or relative == DELIVERY_MANIFEST:
            raise HandoffError(f"duplicate delivery file: {relative}")
        seen.add(relative)
        if type(item["bytes"]) is not int or item["bytes"] < 0:
            raise HandoffError(f"invalid delivery file size: {relative}")
        if type(item["sha256"]) is not str or not HEX64.fullmatch(item["sha256"]):
            raise HandoffError(f"invalid delivery file hash: {relative}")
        if type(item["role"]) is not str or not item["role"].strip():
            raise HandoffError(f"invalid delivery file role: {relative}")
    return files


def _verify_scope(package: Path, expected: set[str]) -> None:
    expected_dirs = {
        parent.as_posix()
        for name in expected for parent in Path(name).parents if parent != Path(".")
    }
    actual_files, actual_dirs = set(), set()
    for path in package.rglob("*"):
        name = path.relative_to(package).as_posix()
        if path.is_symlink():
            raise HandoffError(f"symlink in package: {name}")
        if path.is_file():
            actual_files.add(name)
        elif path.is_dir():
            actual_dirs.add(name)
        else:
            raise HandoffError(f"non-regular entry in package: {name}")
    if actual_files != expected or actual_dirs != expected_dirs:
        raise HandoffError("package scope mismatch, including directories")


def verify(package: Path, *, frozen_sha: str, manifest_sha256: str) -> int:
    """Verify a generated package using only its manifest and file bytes."""

    if type(frozen_sha) is not str or not HEX40.fullmatch(frozen_sha):
        raise HandoffError("verify requires a 40-character lowercase frozen SHA")
    if type(manifest_sha256) is not str or not HEX64.fullmatch(manifest_sha256):
        raise HandoffError("verify requires a 64-character lowercase manifest SHA256")
    package = _require_absolute_directory(package, "package")
    if not package.is_dir() or package.is_symlink():
        raise HandoffError(f"package is not a regular directory: {package}")
    manifest_path = _safe_relative(package, HANDOFF_MANIFEST, label="handoff manifest")
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise HandoffError(f"missing handoff manifest: {manifest_path}")
    manifest_bytes = manifest_path.read_bytes()
    if _sha256_bytes(manifest_bytes) != manifest_sha256:
        raise HandoffError("handoff manifest SHA256 differs from requested value")
    manifest = _json_read(manifest_path)
    files = _validate_handoff_manifest(manifest)
    if manifest["tested_code_sha"] != frozen_sha:
        raise HandoffError("handoff SHA differs from requested frozen SHA")

    expected_paths = {item["path"] for item in files}
    _verify_scope(package, expected_paths | {HANDOFF_MANIFEST})
    for item in files:
        path = _safe_relative(package, item["path"], label="handoff file")
        _check_file(path, item, label=item["path"])
    print(f"WP_E_WINDOWS_HANDOFF_INTEGRITY_OK: {len(files)} files; Word and qualification remain NOT_RUN")
    return len(files)


def verify_delivery(
    package: Path, *, frozen_sha: str, manifest_sha256: str
) -> int:
    """Verify the coordinator's complete delivery package scope."""

    if type(frozen_sha) is not str or not HEX40.fullmatch(frozen_sha):
        raise HandoffError("verify-delivery requires a 40-character lowercase frozen SHA")
    if type(manifest_sha256) is not str or not HEX64.fullmatch(manifest_sha256):
        raise HandoffError(
            "verify-delivery requires a 64-character lowercase manifest SHA256"
        )
    package = _require_absolute_directory(package, "delivery package")
    if not package.is_dir() or package.is_symlink():
        raise HandoffError(f"delivery package is not a regular directory: {package}")
    manifest_path = _safe_relative(
        package, DELIVERY_MANIFEST, label="delivery manifest"
    )
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise HandoffError(f"missing delivery manifest: {manifest_path}")
    raw = manifest_path.read_bytes()
    if _sha256_bytes(raw) != manifest_sha256:
        raise HandoffError("delivery manifest SHA256 differs from requested value")
    manifest = _json_read(manifest_path)
    files = _validate_delivery_manifest(manifest)
    if manifest["tested_code_sha"] != frozen_sha:
        raise HandoffError("delivery SHA differs from requested frozen SHA")
    expected_paths = {item["path"] for item in files}
    _verify_scope(package, expected_paths | {DELIVERY_MANIFEST})
    for item in files:
        path = _safe_relative(package, item["path"], label="delivery file")
        _check_file(path, item, label=item["path"])
    print(
        "WP_E_STARTUP_DELIVERY_INTEGRITY_OK: "
        f"{len(files)} files; source/review/evidence roles remain manifest-bound"
    )
    return len(files)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="regenerate the frozen-SHA stage-one package")
    prep.add_argument("--repo", required=True, type=Path)
    prep.add_argument("--source-manifest", required=True, type=Path)
    prep.add_argument("--source-root", required=True, type=Path)
    prep.add_argument("--output", required=True, type=Path)
    prep.add_argument("--frozen-sha", required=True)
    check = sub.add_parser("verify", help="verify an existing package without app imports")
    check.add_argument("--package", required=True, type=Path)
    check.add_argument("--frozen-sha", required=True)
    check.add_argument("--manifest-sha256", required=True)
    delivery = sub.add_parser(
        "verify-delivery", help="verify the coordinator's complete delivery package"
    )
    delivery.add_argument("--package", required=True, type=Path)
    delivery.add_argument("--frozen-sha", required=True)
    delivery.add_argument("--manifest-sha256", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(
                repo=args.repo,
                source_manifest=args.source_manifest,
                source_root=args.source_root,
                output=args.output,
                frozen_sha=args.frozen_sha,
            )
            print(f"WP_E_WINDOWS_HANDOFF_PREPARED: {result}")
            return 0
        if args.command == "verify":
            verify(
                args.package,
                frozen_sha=args.frozen_sha,
                manifest_sha256=args.manifest_sha256,
            )
        else:
            verify_delivery(
                args.package,
                frozen_sha=args.frozen_sha,
                manifest_sha256=args.manifest_sha256,
            )
        return 0
    except HandoffError as exc:
        print(f"WP_E_WINDOWS_HANDOFF_REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
