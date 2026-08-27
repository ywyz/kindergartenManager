"""Stable RED for combined origin-capture and validator failures."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "scenario",
    ["self-close", "external-close-finally"],
)
def test_capture_and_validator_failure_still_closes_composite_lifecycle(
    scenario: str,
) -> None:
    """Validation diagnostics cannot skip cleanup or restore a task cycle."""

    probe = textwrap.dedent(
        f"""
        import asyncio
        import runpy
        from types import SimpleNamespace
        import sys

        sys.path.insert(0, {str(REPOSITORY_ROOT / "specs/agent-write/tests")!r})
        namespace = runpy.run_path(
            {str(REPOSITORY_ROOT / "specs/agent-write/tests/test_w007_review5_lifecycle_red.py")!r}
        )
        draft_ui = __import__(
            "app.ui.components.agent_draft",
            fromlist=["DailyPlanAgentPanel"],
        )
        confirmation_ui = __import__(
            "app.ui.components.agent_write_confirmation",
            fromlist=["DailyPlanPatchConfirmationPanel"],
        )

        async def outcome(task):
            try:
                await task
            except asyncio.CancelledError:
                return "cancelled"
            except RuntimeError as error:
                return str(error)
            return "returned"

        async def main():
            scenario = {scenario!r}
            fake_ui = namespace["_FakeUi"]()
            draft_ui.ui = fake_ui
            confirmation_ui.ui = fake_ui
            draft_ui.context = SimpleNamespace(client=namespace["_FakeClient"]())
            patch = confirmation_ui.AgentPatchSnapshot(
                patch_id=namespace["PATCH_ID"],
                patch_sha256=namespace["PATCH_SHA256"],
                daily_plan_id=namespace["PLAN_ID"],
                plan_date=namespace["PLAN_DATE"],
                tool_name="draft_daily_plan_fields",
                operations=(),
                warnings=(),
            )
            confirmation_controller = namespace["_ImmediateAppliedController"](patch)
            target = namespace["DailyPlanUiTarget"](
                selection=namespace["DateSelection"](
                    generation=1,
                    selected_date=namespace["PLAN_DATE"],
                ),
                plan_id=namespace["PLAN_ID"],
                revision=1,
                form_generation=0,
            )
            session = namespace["trusted_ui_session"]()
            coordinator = namespace["_LifecycleCoordinator"]()
            coordinator.allow_cancel.set()
            agent_controller = namespace["DailyPlanAgentController"](
                coordinator=coordinator,
                actor=namespace["TrustedActor"](
                    tenant_id=namespace["ACTOR_TENANT_ID"],
                    user_id=namespace["ACTOR_USER_ID"],
                ),
            )
            callback_started = asyncio.Event()
            never_release = asyncio.Event()
            outer_panel = None
            publications = 0

            async def authorize():
                return session

            async def on_applied(_snapshot, _target):
                nonlocal publications
                if scenario == "self-close":
                    await outer_panel.close()
                else:
                    callback_started.set()
                    try:
                        await never_release.wait()
                    finally:
                        await outer_panel.close()
                publications += 1

            patch_actions = confirmation_ui.DailyPlanPatchConfirmationPanel(
                confirmation_controller,
                authorize_confirmation=authorize,
                capture_target=lambda: target,
                is_current_target=lambda candidate: candidate == target,
                on_applied=on_applied,
            )

            def fail_origin_capture():
                raise RuntimeError("origin_capture_failed")

            def fail_origin_validation(_origin):
                raise RuntimeError("origin_validation_failed")

            patch_actions.capture_lifecycle_origin = fail_origin_capture
            patch_actions.owns_lifecycle_origin = fail_origin_validation
            outer_panel = draft_ui.DailyPlanAgentPanel(
                agent_controller,
                patch_actions=patch_actions,
            )
            patch_actions.render_patch_actions(patch)
            view = fake_ui.latest_column()
            await namespace["_press"](
                fake_ui.latest_button("准备确认", within=view)
            )
            apply_button = fake_ui.latest_button("确认采用", within=view)
            if scenario == "self-close":
                result = apply_button.on_click()
                assert result is not None
                await result
            else:
                apply_task = asyncio.create_task(namespace["_press"](apply_button))
                await callback_started.wait()
                close_task = asyncio.create_task(outer_panel.close())
                close_outcome, apply_outcome = await asyncio.gather(
                    outcome(close_task),
                    outcome(apply_task),
                )
                assert close_outcome == "agent_panel_lifecycle_failed"
                assert apply_outcome == "cancelled"

            assert confirmation_controller.shutdown_calls == ["close"]
            assert patch_actions._closed is True
            assert coordinator.invalidations == 1
            assert coordinator.cancellations == 1
            assert publications == 0
            print(f"CAPTURE_VALIDATOR_FAILURE_PASS:{{scenario}}")

        asyncio.run(main())
        """
    )

    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == f"CAPTURE_VALIDATOR_FAILURE_PASS:{scenario}"
