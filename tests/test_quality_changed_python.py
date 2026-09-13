"""Hash-gated changed-Python lint policy regression tests.

Exercises the real pristine repository verification plus tamper scenarios on
isolated temp copies. Originals are never mutated. A spy Ruff runner proves
exactly the six sealed scripts are removed from lint args while ordinary app
files, this checker, the existing active portable verifier, and new
neighboring Python in both sealed dirs stay linted; empty active lists never
invoke bare Ruff; Ruff exit codes propagate.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from scripts.check_changed_python import (
    EXCLUDED_CHANGED_FILES,
    PolicyError,
    main,
    verify_sealed_manifests,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WP_A_DIR = "specs/weekly-plan-authoring/validation/wp-a-simsun-20260909"
WP_E_DIR = "specs/weekly-plan-authoring/validation/wp-e-native-20260913"
WP_A_MANIFEST = Path(WP_A_DIR) / "manifest.json"
WP_E_MANIFEST = Path(WP_E_DIR) / "delivery-evidence-manifest.json"
WP_A_MEMBER = "historical-linux-scripts/verify_layout.py"
WP_E_MEMBER = "environment.json"
ACTIVE_PORTABLE_VERIFIER = (
    "specs/weekly-plan-authoring/verify_wp_e_handoff_20260913.py"
)


class SpyRuff:
    """Record ruff invocations and return a canned exit code."""

    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.calls: list[tuple[Sequence[str], Path]] = []

    def __call__(self, args: Sequence[str], cwd: Path):
        self.calls.append((list(args), cwd))
        return subprocess.CompletedProcess(args, self.returncode)


@pytest.fixture()
def pristine_verified() -> frozenset[str]:
    """Verify the real repository once; originals are only read."""
    return verify_sealed_manifests(REPO_ROOT)


def _copy_sealed_tree(tmp_root: Path) -> Path:
    root = tmp_root / "repo"
    (root / WP_A_DIR).mkdir(parents=True)
    (root / WP_E_DIR).mkdir(parents=True)
    shutil.copytree(
        REPO_ROOT / WP_A_DIR,
        root / WP_A_DIR,
        dirs_exist_ok=True,
        symlinks=False,
    )
    shutil.copytree(
        REPO_ROOT / WP_E_DIR,
        root / WP_E_DIR,
        dirs_exist_ok=True,
        symlinks=False,
    )
    return root


def _assert_pristine_members_untouched() -> None:
    """Prove the real sealed trees still match their manifests after tests."""
    verify_sealed_manifests(REPO_ROOT)


def test_pristine_repository_verifies_all_270_members(
    pristine_verified: frozenset[str],
) -> None:
    assert len(pristine_verified) == 270
    assert EXCLUDED_CHANGED_FILES <= pristine_verified


def test_active_change_is_linted_and_sealed_six_are_excluded(
    pristine_verified: frozenset[str],
) -> None:
    spy = SpyRuff()
    exit_code = main(
        (
            "app/service/agent/confirmed_write.py",
            *sorted(EXCLUDED_CHANGED_FILES),
            "scripts/check_changed_python.py",
            ACTIVE_PORTABLE_VERIFIER,
            f"{WP_A_DIR}/historical-linux-scripts/new_neighbor.py",
            f"{WP_E_DIR}/new_neighbor.py",
        ),
        run=spy,
    )
    assert exit_code == 0
    assert len(spy.calls) == 1
    args, cwd = spy.calls[0]
    assert cwd == REPO_ROOT
    assert args[:4] == [sys.executable, "-m", "ruff", "check"]
    linted = args[4:]
    assert linted == [
        "app/service/agent/confirmed_write.py",
        "scripts/check_changed_python.py",
        ACTIVE_PORTABLE_VERIFIER,
        f"{WP_A_DIR}/historical-linux-scripts/new_neighbor.py",
        f"{WP_E_DIR}/new_neighbor.py",
    ]
    assert not (set(EXCLUDED_CHANGED_FILES) & set(linted))


def test_empty_active_list_never_invokes_bare_ruff(
    pristine_verified: frozenset[str],
) -> None:
    spy = SpyRuff()
    exit_code = main(sorted(EXCLUDED_CHANGED_FILES), run=spy)
    assert exit_code == 0
    assert spy.calls == []


def test_ruff_nonzero_exit_is_propagated(pristine_verified: frozenset[str]) -> None:
    spy = SpyRuff(returncode=7)
    exit_code = main(("app/core/models/user.py",), run=spy)
    assert exit_code == 7


def test_member_tamper_fails_closed_on_isolated_copy(
    tmp_path: Path, pristine_verified: frozenset[str]
) -> None:
    root = _copy_sealed_tree(tmp_path)
    member = root / WP_A_DIR / WP_A_MEMBER
    member.write_bytes(member.read_bytes() + b"\n")
    with pytest.raises(PolicyError):
        verify_sealed_manifests(root)
    spy = SpyRuff()
    assert main((), root=root, run=spy) == 2
    assert spy.calls == []
    _assert_pristine_members_untouched()


def test_manifest_tamper_fails_closed_on_isolated_copy(
    tmp_path: Path, pristine_verified: frozenset[str]
) -> None:
    root = _copy_sealed_tree(tmp_path)
    manifest_path = root / WP_E_MANIFEST
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    document["files"][0]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(PolicyError):
        verify_sealed_manifests(root)
    spy = SpyRuff()
    assert main((), root=root, run=spy) == 2
    assert spy.calls == []
    _assert_pristine_members_untouched()


def test_pinned_manifest_bytes_tamper_fails_before_member_parsing(
    tmp_path: Path, pristine_verified: frozenset[str]
) -> None:
    root = _copy_sealed_tree(tmp_path)
    manifest_path = root / WP_A_MANIFEST
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    document["files"][WP_A_MEMBER]["sha256"] = "1" * 64
    manifest_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(PolicyError):
        verify_sealed_manifests(root)
    spy = SpyRuff()
    assert main((), root=root, run=spy) == 2
    assert spy.calls == []
    _assert_pristine_members_untouched()


def test_deleted_member_fails_closed_on_isolated_copy(
    tmp_path: Path, pristine_verified: frozenset[str]
) -> None:
    root = _copy_sealed_tree(tmp_path)
    (root / WP_E_DIR / WP_E_MEMBER).unlink()
    with pytest.raises(PolicyError):
        verify_sealed_manifests(root)
    spy = SpyRuff()
    assert main((), root=root, run=spy) == 2
    assert spy.calls == []
    _assert_pristine_members_untouched()


def test_pristine_empty_changed_list_verifies_then_skips_ruff(
    tmp_path: Path, pristine_verified: frozenset[str]
) -> None:
    root = _copy_sealed_tree(tmp_path)
    spy = SpyRuff()
    assert main((), root=root, run=spy) == 0
    assert spy.calls == []


def test_symlinked_pinned_manifest_fails_closed_on_isolated_copy(
    tmp_path: Path, pristine_verified: frozenset[str]
) -> None:
    root = _copy_sealed_tree(tmp_path)
    manifest_path = root / WP_A_MANIFEST
    identical_copy = tmp_path / "identical-manifest.json"
    shutil.copyfile(manifest_path, identical_copy)
    manifest_path.unlink()
    manifest_path.symlink_to(identical_copy)
    with pytest.raises(PolicyError):
        verify_sealed_manifests(root)
    spy = SpyRuff()
    assert main((), root=root, run=spy) == 2
    assert spy.calls == []
    _assert_pristine_members_untouched()


def test_real_ruff_invocation_verifies_and_lints_active_file() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_changed_python.py",
            "scripts/check_changed_python.py",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "active=1" in result.stdout
    assert "excluded=0" in result.stdout
    assert "All checks passed" in result.stdout


def test_real_checker_excludes_sealed_files_from_real_ruff() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_changed_python.py",
            *sorted(EXCLUDED_CHANGED_FILES),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "active=0" in result.stdout
    assert "excluded=6" in result.stdout
    for member in sorted(EXCLUDED_CHANGED_FILES):
        assert f"excluded: {member}" in result.stdout
