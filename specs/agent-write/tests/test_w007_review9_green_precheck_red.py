"""Stable RED for the ninth W007 review-fix precheck findings."""

from __future__ import annotations

import pytest

from test_w007_review7_standards_findings_red import (
    _confirmation_flow_private_reads,
    _w007_status_problems,
)


REVIEW_SHA = "1234567890abcdef1234567890abcdef12345678"
EXPECTED_STATUS_PROBLEMS = [
    "duplicated W007 review round",
    f"duplicated W007 review SHA: {REVIEW_SHA}",
]


@pytest.mark.parametrize(
    "content",
    (
        f"W007 当前状态如下：\n\n当前为第九轮 Review，SHA {REVIEW_SHA}。\n",
        (
            "## W007\n\n### W007 当前状态\n\n见 ledger。\n\n"
            f"### 交付门禁\n\n当前为第九轮 Review，SHA {REVIEW_SHA}。\n"
        ),
        (
            "## W007\n\n```markdown\n## 示例\n```\n\n"
            f"当前为第九轮 Review，SHA {REVIEW_SHA}。\n"
        ),
    ),
)
def test_w007_status_guard_keeps_the_full_current_status_scope(
    content: str,
) -> None:
    assert _w007_status_problems(content) == EXPECTED_STATUS_PROBLEMS


def test_w007_status_guard_ignores_headings_inside_fenced_code() -> None:
    content = (
        "## 其他\n\n```markdown\n## W007\n```\n\n"
        f"当前为第九轮 Review，SHA {REVIEW_SHA}。\n"
    )

    assert _w007_status_problems(content) == []


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        (
            'lookup = getattr\nlookup(flow, "_confirmation_id")\n',
            {"_confirmation_id"},
        ),
        (
            "(subject,) = (harness.flow,)\nsubject._pending\n",
            {"_pending"},
        ),
    ),
)
def test_confirmation_flow_private_guard_tracks_supported_alias_forms(
    source: str,
    expected: set[str],
) -> None:
    assert _confirmation_flow_private_reads(source) == expected


@pytest.mark.parametrize(
    "source",
    (
        "river.flow._velocity\n",
        (
            "def bind(harness):\n"
            "    subject = harness.flow\n\n"
            "def other(subject):\n"
            "    return subject._socket\n"
        ),
    ),
)
def test_confirmation_flow_private_guard_avoids_unrelated_scope_false_positives(
    source: str,
) -> None:
    assert _confirmation_flow_private_reads(source) == set()


def test_w007_status_guard_does_not_close_fence_on_an_info_string() -> None:
    content = (
        "## 其他\n\n```markdown\n```python\n## W007\n"
        f"当前为第九轮 Review，SHA {REVIEW_SHA}。\n```\n"
    )

    assert _w007_status_problems(content) == []


def test_w007_status_guard_treats_four_space_fence_as_indented_code() -> None:
    content = f"## W007\n\n    ```markdown\n\n当前为第九轮 Review，SHA {REVIEW_SHA}。\n"

    assert _w007_status_problems(content) == EXPECTED_STATUS_PROBLEMS


def test_w007_status_guard_honors_indented_peer_heading() -> None:
    content = (
        "  ## W007\n\n当前能力见 ledger。\n\n  ## W008\n\n"
        f"当前为第九轮 Review，SHA {REVIEW_SHA}。\n"
    )

    assert _w007_status_problems(content) == []


@pytest.mark.parametrize(
    "source",
    (
        "def check(value=flow._confirmation_id):\n    return value\n",
        "@mark(harness.flow._pending)\ndef check():\n    return None\n",
        ("subject = harness.flow\ndef check():\n    return subject._pending\n"),
        (
            "if condition:\n"
            "    subject = harness.flow\n"
            "else:\n"
            "    subject = object()\n"
            "subject._pending\n"
        ),
        ('lookup = getattr\ndef check():\n    return lookup(flow, "_pending")\n'),
    ),
)
def test_confirmation_flow_private_guard_covers_metadata_closure_and_branches(
    source: str,
) -> None:
    assert _confirmation_flow_private_reads(source)


@pytest.mark.parametrize(
    "source",
    (
        "def check(flow):\n    return flow._velocity\n",
        "network_harness.flow._socket\n",
    ),
)
def test_confirmation_flow_private_guard_ignores_unrelated_names(
    source: str,
) -> None:
    assert _confirmation_flow_private_reads(source) == set()


@pytest.mark.parametrize(
    "source",
    (
        (
            "try:\n"
            "    subject = harness.flow\n"
            "except RuntimeError:\n"
            "    subject = object()\n"
            "subject._pending\n"
        ),
        (
            "subject = harness.flow\n"
            "while condition:\n"
            "    subject = object()\n"
            "subject._pending\n"
        ),
        ("flow = harness.flow\nclass Fixture:\n    flow = object()\nflow._pending\n"),
    ),
)
def test_confirmation_flow_private_guard_joins_paths_and_isolates_class_scope(
    source: str,
) -> None:
    assert _confirmation_flow_private_reads(source) == {"_pending"}


@pytest.mark.parametrize(
    "source",
    (
        (
            "subject = harness.flow\n"
            "for subject in unrelated_items:\n"
            "    subject._cache\n"
        ),
        ("subject = harness.flow\nwith resource() as subject:\n    subject._cache\n"),
        (
            "subject = harness.flow\n"
            "try:\n"
            "    pass\n"
            "except RuntimeError as subject:\n"
            "    subject._cache\n"
        ),
        ("subject = harness.flow\n[subject._cache for subject in unrelated_items]\n"),
    ),
)
def test_confirmation_flow_private_guard_shadows_binding_targets(
    source: str,
) -> None:
    assert _confirmation_flow_private_reads(source) == set()
