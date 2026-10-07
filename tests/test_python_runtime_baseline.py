"""Keep all executable Python runtime pins on the reviewed patch release."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PYTHON_VERSION = "3.14.7"


def test_python_version_file_pins_reviewed_runtime():
    configured_version = (
        (PROJECT_ROOT / ".python-version").read_text(encoding="utf-8").strip()
    )

    assert configured_version == EXPECTED_PYTHON_VERSION


def test_docker_image_pins_reviewed_runtime():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert f"FROM python:{EXPECTED_PYTHON_VERSION}-slim@sha256:" in dockerfile
    final_stage = dockerfile.split("FROM ")[-1]
    assert final_stage.startswith(
        "ghcr.io/ywyz/kindergartenmanager@sha256:"
        "792eee66a96b0dd62a1f2e57a70ddcaf738b019cf323ec4e1cdb87a29e1e2e56"
        " AS production-hotfix\n"
    )
    # This repair inherits the reviewed runtime; its only new instructions
    # must be the explicitly reviewed application files, without installs.
    assert final_stage.splitlines()[1:] == [
        f"COPY {path} {path}" for path in (
            "app/main.py", "app/ui/auth_context.py", "app/ui/pages/daily_plan.py",
            "app/integration/ai_client/base.py",
            "app/integration/ai_client/lesson_plan_client.py",
            "app/integration/ai_client/adapt_client.py",
        )
    ]
    assert "ARG PIP_INDEX_URL=https://pypi.org/simple" in dockerfile
    assert (
        'pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" -r requirements.txt'
        in dockerfile
    )


def test_release_jobs_pin_reviewed_runtime():
    workflow = (PROJECT_ROOT / ".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )

    expected_pin = f"python-version: '{EXPECTED_PYTHON_VERSION}'"
    assert workflow.count(expected_pin) == 1
    assert expected_pin in workflow.split("  verify-release:", 1)[1]
