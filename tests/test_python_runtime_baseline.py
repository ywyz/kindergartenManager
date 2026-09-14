"""Keep all executable Python runtime pins on the reviewed patch release."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PYTHON_VERSION = "3.14.7"


def test_python_version_file_pins_reviewed_runtime():
    configured_version = (PROJECT_ROOT / ".python-version").read_text(encoding="utf-8").strip()

    assert configured_version == EXPECTED_PYTHON_VERSION


def test_docker_image_pins_reviewed_runtime():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM ghcr.io/ywyz/kindergartenmanager@sha256:f4c76e24375c129e3bc0ae2b97f3a60e21f18a832e9eca49ee27d4361f9c5d34" in dockerfile
    assert "COPY alembic/ /app/alembic/" in dockerfile
    assert "COPY app/" not in dockerfile
    assert "pip install" not in dockerfile



def test_release_jobs_pin_reviewed_runtime():
    workflow = (PROJECT_ROOT / ".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )

    expected_pin = f"python-version: '{EXPECTED_PYTHON_VERSION}'"
    assert workflow.count(expected_pin) == 2
