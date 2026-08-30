"""Stable RED for the tenth W007 Standards Review findings."""

from __future__ import annotations

from pathlib import Path
import re
import tomllib

from test_w007_review7_standards_findings_red import (
    _confirmation_flow_private_reads,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _normalized_dependency_names(requirements: list[str]) -> set[str]:
    return {
        re.split(r"[<>=!~\s\[]", requirement, maxsplit=1)[0]
        .strip()
        .lower()
        .replace("_", "-")
        for requirement in requirements
    }


def _locked_dependency_names(requirements: list[dict[str, object]]) -> set[str]:
    return {
        str(requirement["name"]).lower().replace("_", "-")
        for requirement in requirements
    }


def test_markdown_parser_is_in_the_reproducible_dev_dependency_set() -> None:
    """A test-only parser must be declared and locked with the dev environment."""
    project = tomllib.loads(
        (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    lock = tomllib.loads((REPOSITORY_ROOT / "uv.lock").read_text(encoding="utf-8"))

    dev_dependencies = _normalized_dependency_names(project["dependency-groups"]["dev"])
    locked_packages = {
        package["name"].lower().replace("_", "-") for package in lock["package"]
    }
    root_package = next(
        package
        for package in lock["package"]
        if package["name"] == project["project"]["name"]
    )

    assert {
        "pyproject_dev": "markdown-it-py" in dev_dependencies,
        "lock_package": "markdown-it-py" in locked_packages,
        "lock_dev_link": "markdown-it-py"
        in _locked_dependency_names(root_package["dev-dependencies"]["dev"]),
        "lock_dev_metadata": "markdown-it-py"
        in _locked_dependency_names(root_package["metadata"]["requires-dev"]["dev"]),
    } == {
        "pyproject_dev": True,
        "lock_package": True,
        "lock_dev_link": True,
        "lock_dev_metadata": True,
    }


def test_confirmation_flow_private_guard_has_a_shallow_explicit_scope() -> None:
    """The governance guard is not a general-purpose Python data-flow analyzer."""
    source = (
        "flow._direct\nharness.flow._nested\nsubject = harness.flow\nsubject._alias\n"
    )

    assert _confirmation_flow_private_reads(source) == {"_direct", "_nested"}
