"""Shared fixed-SHA trust root for the W008 manual evidence runners.

This module intentionally uses only the Python standard library.  Application
imports remain the responsibility of each runner after this gate succeeds.
"""

from __future__ import annotations

from pathlib import Path
import re
import stat
import subprocess
import sys


_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")


class ManualHelperError(RuntimeError):
    """A content-free, fail-closed launcher refusal."""


def _sha(value: object) -> str:
    """Return one normalized complete commit SHA or fail closed."""
    if type(value) is not str:
        raise ManualHelperError("tested SHA must be complete 40-character hex")
    normalized = value.strip().casefold()
    if _SHA_PATTERN.fullmatch(normalized) is None:
        raise ManualHelperError("tested SHA must be complete 40-character hex")
    return normalized


def _git(root: Path, *args: str) -> bytes:
    """Run one read-only Git verification without exposing captured output."""
    try:
        result = subprocess.run(
            ("git", *args),
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        raise ManualHelperError("git verification failed") from None
    if result.returncode:
        raise ManualHelperError("git verification failed")
    return result.stdout


def require_isolated_worktree(
    tested_sha: object,
    *,
    clean: bool = True,
    protected_names: tuple[str, ...] = (),
) -> Path:
    """Require one linked worktree at the exact SHA and runtime policy."""
    expected = _sha(tested_sha)
    root = Path.cwd().resolve()
    try:
        top = Path(
            _git(root, "rev-parse", "--show-toplevel").decode().strip()
        ).resolve()
        actual = _git(root, "rev-parse", "HEAD").decode().strip().casefold()
        git_entry = (root / ".git").lstat()
    except ManualHelperError:
        raise
    except (OSError, UnicodeError):
        raise ManualHelperError("cannot inspect isolated worktree") from None

    if root != top or not stat.S_ISREG(git_entry.st_mode):
        raise ManualHelperError("run from a linked worktree root")
    if actual != expected:
        raise ManualHelperError("HEAD does not match tested SHA")

    for protected_name in protected_names:
        if (
            type(protected_name) is not str
            or not protected_name
            or Path(protected_name).name != protected_name
        ):
            raise ManualHelperError("invalid protected runtime policy")
        try:
            (root / protected_name).lstat()
        except FileNotFoundError:
            continue
        except OSError:
            raise ManualHelperError("cannot inspect protected runtime entry") from None
        raise ManualHelperError("refusing protected runtime entry")

    if clean and _git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ):
        raise ManualHelperError("isolated worktree is not clean")
    return root


def _activate_worktree_imports(root: Path) -> None:
    """Make the already verified worktree authoritative for delayed imports."""
    verified = str(root.resolve())
    sys.path[:] = [
        verified,
        *(
            entry
            for entry in sys.path
            if str(Path(entry or Path.cwd()).resolve()) != verified
        ),
    ]
