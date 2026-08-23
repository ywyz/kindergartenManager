"""Regression guard for the dependency floors frozen in GitHub Issue #49."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path


REQUIREMENTS_PATH = Path(__file__).parents[1] / "requirements.txt"
UV_LOCK_PATH = Path(__file__).parents[1] / "uv.lock"
REQUIRED_SECURITY_FLOORS = {
    "aiohttp": "3.14.3",
    "cryptography": "50.0.0",
    "python-engineio": "4.13.2",
    "python-multipart": "0.0.31",
    "python-socketio": "5.16.2",
    "pyjwt": "2.13.0",
    "starlette": "1.3.1",
}
REQUIREMENT_PATTERN = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)(?:\[[^]]+\])?\s*>=\s*(?P<version>[0-9]+(?:\.[0-9]+)*)"
)


def _version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _minimum_versions() -> dict[str, str]:
    minimums: dict[str, str] = {}
    for raw_line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", maxsplit=1)[0].strip()
        match = REQUIREMENT_PATTERN.match(line)
        if match:
            minimums[match.group("name").lower()] = match.group("version")
    return minimums


def test_requirements_cover_frozen_dependabot_security_floors() -> None:
    """Vulnerable families must resolve no lower than their patched release."""
    minimums = _minimum_versions()
    failures = []

    for package, required_floor in REQUIRED_SECURITY_FLOORS.items():
        actual_floor = minimums.get(package)
        if actual_floor is None:
            failures.append(f"{package}: missing (need >= {required_floor})")
        elif _version_tuple(actual_floor) < _version_tuple(required_floor):
            failures.append(
                f"{package}: found >= {actual_floor} (need >= {required_floor})"
            )

    assert not failures, "Unsafe dependency floors:\n" + "\n".join(failures)


def test_lock_excludes_unpatched_python_ecdsa_runtime_dependency() -> None:
    """The exact runtime graph must not contain the unpatched python-ecdsa chain."""
    lock_data = tomllib.loads(UV_LOCK_PATH.read_text(encoding="utf-8"))
    locked_names = {package["name"].lower() for package in lock_data["package"]}
    prohibited = sorted({"ecdsa", "python-jose"} & locked_names)

    failures = []
    if prohibited:
        failures.append("prohibited locked packages: " + ", ".join(prohibited))
    if "pyjwt" not in locked_names:
        failures.append("replacement package missing: pyjwt")

    assert not failures, "Unsafe JWT dependency graph:\n" + "\n".join(failures)
