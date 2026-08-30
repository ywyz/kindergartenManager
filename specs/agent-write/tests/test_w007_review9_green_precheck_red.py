"""Stable RED for the ninth W007 review-fix precheck findings."""

from __future__ import annotations

import pytest

from test_w007_review7_standards_findings_red import _w007_status_problems


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
