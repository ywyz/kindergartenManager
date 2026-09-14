"""Hash-gated lint policy for changed Python files.

CI invokes this stdlib-only checker unconditionally with the changed Python
list. It first verifies the two pinned sealed-evidence manifests (exact byte
size and sha256), then every listed member (schema, safe relative path, no
symlinks, regular file, exact byte size and sha256, no duplicate paths or
JSON keys) and fails closed before Ruff runs. Only after verification are the
six sealed historical scripts removed from the Ruff argument list; every
other changed path stays active and is linted via
[sys.executable, "-m", "ruff", "check", *active] with the repository root as
cwd and the exit code propagated. An empty active list never invokes bare
Ruff. Output is limited to counts and excluded paths, never file contents.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[1]

WP_A_DIR = PurePosixPath("specs/weekly-plan-authoring/validation/wp-a-simsun-20260909")
WP_E_DIR = PurePosixPath("specs/weekly-plan-authoring/validation/wp-e-native-20260913")

_PINNED_MANIFESTS: dict[PurePosixPath, tuple[PurePosixPath, int, str]] = {
    WP_A_DIR: (
        WP_A_DIR / "manifest.json",
        6549,
        "9924066807b9d8354ac4648874680089137d2c26c9442bb4fad3b778f6765442",
    ),
    WP_E_DIR: (
        WP_E_DIR / "delivery-evidence-manifest.json",
        41773,
        "c5dfc4516cea4ab3a47d82a76c9783b6f2b7ba9129ff5e3e351a47d73dab0641",
    ),
}

EXCLUDED_CHANGED_FILES = frozenset(
    {
        "specs/weekly-plan-authoring/validation/wp-a-simsun-20260909/historical-linux-scripts/make_layout_samples.py",
        "specs/weekly-plan-authoring/validation/wp-a-simsun-20260909/historical-linux-scripts/make_compact_candidates.py",
        "specs/weekly-plan-authoring/validation/wp-a-simsun-20260909/historical-linux-scripts/write_layout_manifest.py",
        "specs/weekly-plan-authoring/validation/wp-a-simsun-20260909/historical-linux-scripts/verify_layout.py",
        "specs/weekly-plan-authoring/validation/wp-e-native-20260913/build_delivery.py",
        "specs/weekly-plan-authoring/validation/wp-e-native-20260913/seal_evidence.py",
    }
)

POLICY_EXIT_CODE = 2
_HEX_DIGITS = frozenset("0123456789abcdef")


class PolicyError(Exception):
    """Static fail-closed policy failure; never carries file body content."""


def load_strict_json(raw: bytes) -> object:
    """Parse manifest JSON, rejecting duplicate keys and malformed input."""

    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise PolicyError("duplicate JSON key in sealed manifest")
            result[key] = value
        return result

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise PolicyError("sealed manifest is not valid UTF-8") from None
    try:
        return json.loads(text, object_pairs_hook=reject_duplicate_keys)
    except json.JSONDecodeError:
        raise PolicyError("sealed manifest JSON is malformed") from None


def _validate_member_digest(member: str, size: object, sha256: object) -> None:
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise PolicyError(f"member byte size is malformed: {member}")
    if (
        not isinstance(sha256, str)
        or len(sha256) != 64
        or any(digit not in _HEX_DIGITS for digit in sha256)
    ):
        raise PolicyError(f"member sha256 is malformed: {member}")


def wp_a_members(document: object) -> dict[str, tuple[int, str]]:
    """Extract the 37 wp-a members (files object mapping paths to digests)."""
    if not isinstance(document, dict):
        raise PolicyError("wp-a manifest root is not a JSON object")
    files = document.get("files")
    if not isinstance(files, dict) or len(files) != 37:
        raise PolicyError("wp-a manifest files must map exactly 37 members")
    members: dict[str, tuple[int, str]] = {}
    for member_rel, entry in files.items():
        if not isinstance(member_rel, str) or not isinstance(entry, dict):
            raise PolicyError("wp-a manifest member entry is malformed")
        if set(entry) != {"bytes", "sha256"}:
            raise PolicyError("wp-a manifest member keys are unexpected")
        _validate_member_digest(member_rel, entry["bytes"], entry["sha256"])
        members[member_rel] = (entry["bytes"], entry["sha256"])
    return members


def wp_e_members(document: object) -> dict[str, tuple[int, str]]:
    """Extract the 233 wp-e members (files list of file/bytes/sha256)."""
    if not isinstance(document, dict):
        raise PolicyError("wp-e manifest root is not a JSON object")
    files = document.get("files")
    if not isinstance(files, list) or len(files) != 233:
        raise PolicyError("wp-e manifest files must list exactly 233 members")
    members: dict[str, tuple[int, str]] = {}
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"file", "bytes", "sha256"}:
            raise PolicyError("wp-e manifest member entry is malformed")
        member = entry["file"]
        if not isinstance(member, str):
            raise PolicyError("wp-e manifest member path is malformed")
        _validate_member_digest(member, entry["bytes"], entry["sha256"])
        if member in members:
            raise PolicyError(f"duplicate member path in wp-e manifest: {member}")
        members[member] = (entry["bytes"], entry["sha256"])
    return members


def _verify_regular_nonsymlink_path(root: Path, relative: PurePosixPath) -> None:
    """Require every ancestor and the leaf of a repo-relative path to be a
    non-symlink regular directory/file (leaf must be a regular file)."""
    current = root
    for part in relative.parts:
        current = current / part
        try:
            info = os.lstat(current)
        except OSError:
            raise PolicyError(f"pinned path missing or unreadable: {relative}") from None
        if stat.S_ISLNK(info.st_mode):
            raise PolicyError(f"pinned path contains a symlink: {relative}")
        if not stat.S_ISDIR(info.st_mode) and not stat.S_ISREG(info.st_mode):
            raise PolicyError(f"pinned path has a non-directory component: {relative}")
    if not stat.S_ISREG(info.st_mode):
        raise PolicyError(f"pinned manifest is not a regular file: {relative}")


def _read_pinned_manifest(
    root: Path,
    manifest_rel: PurePosixPath,
    expected_bytes: int,
    expected_sha256: str,
) -> object:
    _verify_regular_nonsymlink_path(root, manifest_rel)
    path = root.joinpath(*manifest_rel.parts)
    try:
        raw = path.read_bytes()
    except OSError:
        raise PolicyError(f"pinned manifest missing or unreadable: {manifest_rel}") from None
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if len(raw) != expected_bytes or actual_sha256 != expected_sha256:
        raise PolicyError(f"pinned manifest size/sha256 mismatch: {manifest_rel}")
    return load_strict_json(raw)


def verify_member(
    root: Path,
    sealed_dir: PurePosixPath,
    member_rel: str,
    expected_bytes: int,
    expected_sha256: str,
) -> None:
    """Verify one member is a safe, symlink-free regular file matching bytes/hash."""
    if (
        not member_rel
        or "\\" in member_rel
        or member_rel.startswith("/")
        or any(part in ("", ".", "..") for part in member_rel.split("/"))
    ):
        raise PolicyError(f"unsafe member path in sealed manifest: {member_rel}")
    current = root
    for part in (*sealed_dir.parts, *member_rel.split("/")):
        current = current / part
        try:
            info = os.lstat(current)
        except OSError:
            raise PolicyError(
                f"sealed member missing or unreadable: {sealed_dir / member_rel}"
            ) from None
        if stat.S_ISLNK(info.st_mode):
            raise PolicyError(
                f"sealed member path contains a symlink: {sealed_dir / member_rel}"
            )
    if not stat.S_ISREG(info.st_mode):
        raise PolicyError(
            f"sealed member is not a regular file: {sealed_dir / member_rel}"
        )
    sealed_dir_real = os.path.realpath(root.joinpath(*sealed_dir.parts))
    if not os.path.realpath(current).startswith(sealed_dir_real + os.sep):
        raise PolicyError(
            f"sealed member escapes its manifest directory: {sealed_dir / member_rel}"
        )
    try:
        data = current.read_bytes()
    except OSError:
        raise PolicyError(
            f"sealed member unreadable: {sealed_dir / member_rel}"
        ) from None
    actual_sha256 = hashlib.sha256(data).hexdigest()
    if len(data) != expected_bytes or actual_sha256 != expected_sha256:
        raise PolicyError(f"sealed member size/sha256 mismatch: {sealed_dir / member_rel}")


def verify_sealed_manifests(root: Path) -> frozenset[str]:
    """Verify both pinned manifests and every member; return repo-relative paths."""
    verified: set[str] = set()
    collectors = ((WP_A_DIR, wp_a_members), (WP_E_DIR, wp_e_members))
    for sealed_dir, collect in collectors:
        manifest_rel, expected_bytes, expected_sha256 = _PINNED_MANIFESTS[sealed_dir]
        document = _read_pinned_manifest(
            root, manifest_rel, expected_bytes, expected_sha256
        )
        for member_rel, digest in collect(document).items():
            verify_member(root, sealed_dir, member_rel, *digest)
            verified.add((sealed_dir / member_rel).as_posix())
    return frozenset(verified)


def select_active_files(
    changed: Sequence[str],
    verified: frozenset[str],
) -> tuple[list[str], list[str]]:
    """Filter only the six sealed scripts; keep all other paths as arguments."""
    if not EXCLUDED_CHANGED_FILES <= verified:
        raise PolicyError("sealed exclusion set is not covered by verified manifests")
    active = [path for path in changed if path not in EXCLUDED_CHANGED_FILES]
    excluded = [path for path in changed if path in EXCLUDED_CHANGED_FILES]
    return active, excluded


def main(
    changed: Sequence[str],
    root: Path = REPO_ROOT,
    run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> int:
    """Verify sealed evidence, then lint the active changed files via Ruff."""
    try:
        verified = verify_sealed_manifests(root)
        active, excluded = select_active_files(changed, verified)
    except PolicyError as error:
        print(f"quality-lint-policy: {error}", file=sys.stderr)
        return POLICY_EXIT_CODE
    print(f"changed={len(changed)} active={len(active)} excluded={len(excluded)}")
    for member in excluded:
        print(f"excluded: {member}")
    if not active:
        print("no active changed Python files; ruff not invoked")
        return 0
    completed = run([sys.executable, "-m", "ruff", "check", *active], cwd=root)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
