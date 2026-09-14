"""A compatible recovery image must be verified before recording restored state."""

import argparse
import json

import pytest

from scripts import deploy


def image(char):
    return "ghcr.io/example/app@sha256:" + char * 64


@pytest.mark.parametrize("failure", [None, "target", "both"])
def test_post_migration_compatible_recovery_records_only_verified_image(
    tmp_path, monkeypatch, failure
):
    state = tmp_path / "state.json"
    original = {"app": {"current_image": image("a"), "previous_image": None}}
    state.write_text(json.dumps(original))
    state.chmod(0o600)
    runner = tmp_path / "runner"
    args = argparse.Namespace(
        dry_run=False,
        acceptance_runner=runner,
        service="app",
        image_ref=image("b"),
        recovery_image=image("c"),
        protected_image=image("a"),
        acceptance_profile="weekly-plan",
        rollback_acceptance_profile="service-recovery",
        backup_evidence=tmp_path / "backup",
        migration_receipt=tmp_path / "receipt",
        source_sha="d" * 40,
        health_url="https://example.test/health",
        readiness_url="https://example.test/readiness",
    )
    starts, gates = [], []
    monkeypatch.setattr(deploy, "_require_acceptance_runner", lambda path: path)
    monkeypatch.setattr(deploy, "_require_post_migration_backup", lambda *a: None)
    monkeypatch.setattr(
        deploy, "_start_image", lambda **kw: starts.append(kw["image_ref"])
    )
    monkeypatch.setattr(deploy, "_wait_for_http_gate", lambda *a, **kw: None)

    def acceptance(path, **kw):
        gates.append((kw["phase"], kw["image_ref"], kw["profile"]))
        if kw["gate"] == "business" and (failure == "both" or failure == kw["phase"]):
            raise deploy.DeployError("synthetic gate failure")

    monkeypatch.setattr(deploy, "_run_acceptance_gate", acceptance)
    options = {
        "compose_file": tmp_path / "compose.yml",
        "project_dir": tmp_path,
        "override_file": tmp_path / "override.yml",
        "state_file": state,
        "current_image": image("a"),
    }
    if failure:
        with pytest.raises(deploy.DeployError):
            deploy._run_post_migration_deploy(args, **options)
    else:
        deploy._run_post_migration_deploy(args, **options)
    result = json.loads(state.read_text())
    if failure is None:
        assert starts == [image("b")]
        assert result["app"] == {
            "current_image": image("b"),
            "previous_image": image("c"),
        }
    else:
        assert starts == [image("b"), image("c")]
        assert ("rollback", image("c"), "service-recovery") in gates
        assert result == (
            original
            if failure == "both"
            else {"app": {"current_image": image("c"), "previous_image": None}}
        )
