"""Agent error feedback exposes safe categories without echoing provider data."""

import pytest

from app.ui.components import agent_draft


@pytest.mark.parametrize(
    "code",
    [
        "agent.provider_failed",
        "agent.tool_schema_invalid",
        "agent.patch_invalid",
        "agent.limit_exceeded",
        "agent.response_too_large",
    ],
)
def test_runtime_failures_have_distinct_safe_diagnostic_codes(code):
    message = agent_draft.agent_error_message(code)
    assert code in message
    assert "关闭契约" not in message


def test_untrusted_failure_text_is_never_rendered():
    untrusted = "provider failed sk-secret https://private.example/path child-name"
    message = agent_draft.agent_error_message(untrusted)
    assert untrusted not in message
    assert "sk-secret" not in message
    assert "agent.unknown" in message


def test_non_string_failure_is_not_stringified():
    class Hostile:
        def __str__(self):
            raise AssertionError("must not format provider objects")

    assert "agent.unknown" in agent_draft.agent_error_message(Hostile())
