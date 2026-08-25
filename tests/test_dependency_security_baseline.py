"""Regression guard for dependency versions raised by Dependabot."""

from pathlib import Path


EXPECTED_SECURITY_FLOORS = {
    "nicegui": "3.16.0",
    "fastapi": "0.141.1",
    "cryptography": "50.0.0",
    "aiohttp": "3.14.3",
    "python-socketio": "5.16.4",
    "python-engineio": "4.13.5",
    "python-multipart": "0.0.32",
    "starlette": "1.6.0",
}


def _requirements_by_name() -> dict[str, str]:
    requirements_path = Path(__file__).resolve().parents[1] / "requirements.txt"
    requirements: dict[str, str] = {}
    for raw_line in requirements_path.read_text(encoding="utf-8").splitlines():
        requirement = raw_line.split("#", maxsplit=1)[0].strip()
        if ">=" not in requirement:
            continue
        package, minimum_version = requirement.split(">=", maxsplit=1)
        normalized_name = package.split("[", maxsplit=1)[0].strip().lower()
        requirements[normalized_name] = minimum_version.strip()
    return requirements


def test_dependabot_security_floors_are_not_downgraded():
    requirements = _requirements_by_name()

    for package, expected_version in EXPECTED_SECURITY_FLOORS.items():
        assert requirements.get(package) == expected_version, (
            f"{package} must keep the reviewed security floor {expected_version}"
        )
