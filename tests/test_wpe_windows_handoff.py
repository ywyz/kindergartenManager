"""Focused integrity checks for the WP-E Windows handoff utility."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from scripts import wpe_windows_handoff as handoff


@pytest.mark.parametrize("kind", ["empty-directory", "fifo"])
def test_delivery_rejects_unlisted_non_file_entries(tmp_path, kind):
    package, frozen, digest = _write_delivery_package(tmp_path)
    extra = package / "extra"
    if kind == "fifo":
        os.mkfifo(extra)
    else:
        extra.mkdir()
    with pytest.raises(handoff.HandoffError):
        handoff.verify_delivery(package, frozen_sha=frozen, manifest_sha256=digest)


@pytest.mark.parametrize("change", ["missing-case", "word-pass", "wrong-role", "source-hash"])
def test_candidate_manifest_requires_complete_pending_case_relationships(tmp_path, change):
    package, frozen, _ = _write_package(tmp_path)
    path = package / handoff.HANDOFF_MANIFEST
    data = json.loads(path.read_bytes())
    if change == "missing-case":
        data["cases"].pop()
    elif change == "word-pass":
        data["cases"][0]["windows_return"]["status"] = "PASS"
    elif change == "wrong-role":
        data["cases"][0]["generated"]["runtime_pdf"]["role"] = "word-native-pdf"
    else:
        data["cases"][0]["source_body_sha256"] = "b" * 64
    path.write_text(json.dumps(data))
    with pytest.raises(handoff.HandoffError):
        handoff.verify(package, frozen_sha=frozen, manifest_sha256=_sha256(path.read_bytes()))


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _source_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    root = tmp_path / "source-root"
    root.mkdir()
    cases: list[dict[str, object]] = []
    body_hashes: dict[str, str] = {}
    for case_id in handoff.EXPECTED_CASE_IDS:
        case_dir = root / case_id
        case_dir.mkdir()
        body = json.dumps({"case": case_id}, ensure_ascii=False).encode()
        (case_dir / "body.json").write_bytes(body)
        body_hashes[case_id] = _sha256(body)
        artifacts: dict[str, str] = {}
        for name in ("body.json", "candidate.docx", "candidate.pdf", "page-1.png"):
            path = case_dir / name
            if name != "body.json":
                path.write_bytes(f"{case_id}:{name}".encode())
            artifacts[name] = _sha256(path.read_bytes())
        cases.append(
            {
                "id": case_id,
                "source_body": f"/historical/{case_id}.body.json",
                "source_body_sha256": body_hashes[case_id],
                "display": {
                    "class_name": "验收小一班",
                    "term_name": "2026年秋季学期",
                    "week_number": 3,
                },
                # The real preserved manifest uses this historical bare-hash
                # shape; validation must not rewrite it.
                "artifacts": artifacts,
            }
        )
        profile = case_dir / "lo-profile"
        profile.mkdir()
        (profile / "historical-extra.txt").write_text("keep out of package")
    manifest = tmp_path / "source-manifest.json"
    manifest.write_text(
        json.dumps({"created_utc": "2026-09-13T00:00:00Z", "cases": cases})
        + "\n",
        encoding="utf-8",
    )
    return manifest, root, body_hashes


def _write_package(tmp_path: Path, *, path: str = "five-normal/input.body.json") -> tuple[Path, str, str]:
    package = tmp_path / "handoff"
    files, cases = [], []
    for case_id in handoff.EXPECTED_CASE_IDS:
        records = []
        for name, role in (
            ("input.body.json", "preserved-body-input"),
            ("runtime-candidate.docx", "runtime-candidate-docx"),
            ("runtime-lo.pdf", "ubuntu-libreoffice-runtime-pdf"),
            ("runtime-lo-page-1.png", "ubuntu-libreoffice-runtime-png"),
        ):
            relative = case_id + "/" + name
            if case_id == "five-normal" and name == "input.body.json":
                relative = path
            target = package / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = b"preserved-body" if name == "input.body.json" else b"synthetic hash fixture"
            target.write_bytes(raw)
            record = {"path": relative, "bytes": len(raw), "sha256": _sha256(raw),
                      "role": role, "case_id": case_id}
            records.append(record)
            files.append(record)
        cases.append({
            "id": case_id, "source_body": "/historical/" + case_id + ".json",
            "source_body_sha256": records[0]["sha256"],
            "source_artifact_sha256": {"body.json": records[0]["sha256"], "candidate.docx": "b" * 64},
            "generated": {"body": records[0], "runtime_docx": records[1],
                          "runtime_pdf": records[2], "runtime_png": [records[3]]},
            "windows_return": {"status": "NOT_RUN", "word_export_pdf": None,
                               "word_page_png": [], "native_observation": handoff._native_observation_not_run()},
        })
    manifest = {
        "schema": handoff.HANDOFF_SCHEMA,
        "tested_code_sha": "a" * 40,
        "template_sha256": handoff.TEMPLATE_SHA256,
        "profile": handoff.PROFILE,
        "native_observation_fields": list(handoff.NATIVE_OBSERVATION_FIELDS),
        "formal_qualification": "NOT_RUN", "windows_word_observation": "NOT_RUN",
        "cases": cases, "files": files,
        "source_code": [{"module": name, "path": name.replace(".", "/") + ".py", "sha256": "a" * 64}
                        for name in handoff.SOURCE_MODULES],
        "released_binding_role": "local immutable port metadata; not production activation or proof",
        "released_binding": {"template_version_id": "00000000-0000-0000-0000-000000000801",
                             "version": 8, "content_sha256": handoff.TEMPLATE_SHA256,
                             "contract_id": "kg.template.weekly_activity_plan.candidate", "contract_version": 2},
    }
    manifest_path = package / handoff.HANDOFF_MANIFEST
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return package, manifest["tested_code_sha"], _sha256(manifest_path.read_bytes())


def _write_delivery_package(tmp_path: Path) -> tuple[Path, str, str]:
    package = tmp_path / "delivery"
    files = []
    for relative, role, raw in (
        ("source.bundle", "recoverable-source", b"bundle"),
        ("docs/README.md", "operation-instructions", b"read me"),
        ("evidence/review.json", "independent-review", b"review"),
        ("evidence/empty-stderr.txt", "original-empty-event-stream", b""),
    ):
        path = package / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        files.append(
            {
                "path": relative,
                "bytes": len(raw),
                "sha256": _sha256(raw),
                "role": role,
            }
        )
    manifest = {
        "schema": handoff.DELIVERY_SCHEMA,
        "tested_code_sha": "c" * 40,
        "evidence_closure_sha": "d" * 40,
        "files": files,
    }
    manifest_path = package / handoff.DELIVERY_MANIFEST
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return package, manifest["tested_code_sha"], _sha256(manifest_path.read_bytes())


def test_native_schema_field_set_is_explicit_and_closed() -> None:
    assert handoff.NATIVE_OBSERVATION_FIELDS == (
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
    assert handoff.FIXED_COUNTS == [2, 1, 3, 1, 3, 3, 3, 3, 3, 1]


def test_source_manifest_accepts_historical_hash_shape_and_ignores_lo_profile(
    tmp_path: Path,
) -> None:
    manifest, root, expected = _source_fixture(tmp_path)
    validated = handoff.validate_source_manifest(manifest, root)
    assert [case["id"] for case in validated["cases"]] == list(handoff.EXPECTED_CASE_IDS)
    assert {
        case["id"]: case["source_body_sha256"] for case in validated["cases"]
    } == expected


def test_source_manifest_rejects_symlinked_body(tmp_path: Path) -> None:
    manifest, root, _ = _source_fixture(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text("outside", encoding="utf-8")
    body = root / "five-normal" / "body.json"
    body.unlink()
    try:
        body.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are unavailable on this filesystem")
    with pytest.raises(handoff.HandoffError, match="symlink"):
        handoff.validate_source_manifest(manifest, root)


def test_verify_accepts_nested_manifest_paths_and_rejects_drift(tmp_path: Path) -> None:
    package, frozen_sha, manifest_sha = _write_package(tmp_path)
    assert handoff.verify(
        package, frozen_sha=frozen_sha, manifest_sha256=manifest_sha
    ) == 48

    (package / "five-normal" / "input.body.json").write_bytes(b"changed")
    with pytest.raises(handoff.HandoffError, match="(size|hash) mismatch"):
        handoff.verify(
            package, frozen_sha=frozen_sha, manifest_sha256=manifest_sha
        )


def test_verify_rejects_unlisted_files_and_manifest_path_traversal(tmp_path: Path) -> None:
    package, frozen_sha, manifest_sha = _write_package(tmp_path)
    (package / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(handoff.HandoffError, match="scope mismatch"):
        handoff.verify(
            package, frozen_sha=frozen_sha, manifest_sha256=manifest_sha
        )

    package, frozen_sha, _ = _write_package(tmp_path / "second")
    manifest_path = package / handoff.HANDOFF_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../outside"
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    with pytest.raises(handoff.HandoffError, match="unsafe manifest"):
        handoff.verify(
            package,
            frozen_sha=frozen_sha,
            manifest_sha256=_sha256(manifest_path.read_bytes()),
        )


def test_verify_requires_manifest_and_frozen_sha_binding(tmp_path: Path) -> None:
    package, frozen_sha, manifest_sha = _write_package(tmp_path)
    with pytest.raises(handoff.HandoffError, match="manifest SHA256"):
        handoff.verify(
            package, frozen_sha=frozen_sha, manifest_sha256="b" * 64
        )
    with pytest.raises(handoff.HandoffError, match="frozen SHA"):
        handoff.verify(
            package, frozen_sha="b" * 40, manifest_sha256=manifest_sha
        )


def test_verify_delivery_checks_complete_manifest_scope(tmp_path: Path) -> None:
    package, frozen_sha, manifest_sha = _write_delivery_package(tmp_path)
    assert handoff.verify_delivery(
        package, frozen_sha=frozen_sha, manifest_sha256=manifest_sha
    ) == 4

    (package / "unlisted.log").write_text("unlisted", encoding="utf-8")
    with pytest.raises(handoff.HandoffError, match="scope mismatch"):
        handoff.verify_delivery(
            package, frozen_sha=frozen_sha, manifest_sha256=manifest_sha
        )


def test_verify_delivery_rejects_wrong_evidence_shape_and_file_hash(
    tmp_path: Path,
) -> None:
    package, frozen_sha, _ = _write_delivery_package(tmp_path)
    manifest_path = package / handoff.DELIVERY_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["evidence_closure_sha"] = "not-a-sha"
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    with pytest.raises(handoff.HandoffError, match="evidence_closure_sha"):
        handoff.verify_delivery(
            package,
            frozen_sha=frozen_sha,
            manifest_sha256=_sha256(manifest_path.read_bytes()),
        )

    package, frozen_sha, _ = _write_delivery_package(tmp_path / "hash")
    manifest_path = package / handoff.DELIVERY_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["sha256"] = "e" * 64
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    with pytest.raises(handoff.HandoffError, match="hash mismatch"):
        handoff.verify_delivery(
            package,
            frozen_sha=frozen_sha,
            manifest_sha256=_sha256(manifest_path.read_bytes()),
        )


def test_windows_return_template_is_unrun_and_covers_exact_cases() -> None:
    template_path = (
        Path(__file__).parents[1]
        / "specs/weekly-plan-authoring/evidence/WP-E-Windows-return-template-20260913.json"
    )
    template = json.loads(template_path.read_text(encoding="utf-8"))
    assert template["status"] == "NOT_RUN"
    assert [case["id"] for case in template["cases"]] == list(
        handoff.EXPECTED_CASE_IDS
    )
    assert template["formal_qualification"] == "NOT_RUN"
    for case in template["cases"]:
        assert case["native_observation"] == {
            field: "NOT_RUN" for field in handoff.NATIVE_OBSERVATION_FIELDS
        }
