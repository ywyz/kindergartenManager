"""Contract tests for the immutable deploy script."""

from __future__ import annotations

import contextlib
import json
import stat
import subprocess
from pathlib import Path

import pytest

from scripts import deploy

HEALTH_ARGS = ("--health-url", "https://manager.ywyz.tech/api/v1/health")
VALIDATE_OCI_INDEX_REF = deploy._validate_oci_index_ref


@pytest.fixture(autouse=True)
def _avoid_registry_access(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deploy, "_validate_oci_index_ref", lambda *args, **kwargs: None)


def _image(character: str) -> str:
    return "ghcr.io/ywyz/kindergartenmanager@sha256:" + character * 64


def _compose(project_dir: Path) -> Path:
    path = project_dir / "docker-compose.yml"
    path.write_text("services:\n  app:\n    image: example.invalid/app:latest\n")
    return path


def test_is_immutable_image_ref_is_strict() -> None:
    assert deploy.is_immutable_image_ref(_image("a"))
    assert deploy.is_immutable_image_ref(
        "github.ywyz.tech/ghcr.io/ywyz/kindergartenmanager@sha256:" + "b" * 64
    )
    assert not deploy.is_immutable_image_ref("ghcr.io/ywyz/kindergartenmanager:latest")
    assert not deploy.is_immutable_image_ref(
        "GHCR.io/ywyz/kindergartenmanager@sha256:" + "a" * 64
    )
    assert not deploy.is_immutable_image_ref(
        "ghcr.io/ywyz/app\nservices:@sha256:" + "a" * 64
    )


def test_deploy_dry_run_does_not_execute_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)

    def forbidden_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess:
        raise AssertionError("dry-run must not execute subprocesses")

    monkeypatch.setattr(deploy.subprocess, "run", forbidden_run)

    assert (
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                "--dry-run",
                *HEALTH_ARGS,
                "deploy",
                _image("b"),
            ]
        )
        == 0
    )


def test_relative_compose_and_state_paths_resolve_from_project_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    compose = _compose(tmp_path)
    observed: dict[str, Path] = {}

    def fake_deploy_once(
        compose_file: Path,
        project_dir: Path,
        override_file: Path,
        service: str,
        image_ref: str,
        health_url: str,
        dry_run: bool,
    ) -> str:
        observed["compose"] = compose_file
        observed["project"] = project_dir
        observed["override"] = override_file
        return image_ref

    monkeypatch.setattr(deploy, "_deploy_once", fake_deploy_once)
    monkeypatch.setattr(deploy, "_snapshot_current_state", lambda *args, **kwargs: None)

    deploy.main(
        [
            "--project-dir",
            str(tmp_path),
            "--compose-file",
            "docker-compose.yml",
            "--state-dir",
            "persistent-state",
            *HEALTH_ARGS,
            "deploy",
            _image("c"),
        ]
    )

    assert observed["compose"] == compose
    assert observed["project"] == tmp_path
    assert observed["override"].parent == tmp_path / "persistent-state"


def test_first_deploy_snapshots_live_current_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    old_image = _image("a")
    new_image = _image("b")
    monkeypatch.setattr(
        deploy, "_snapshot_current_state", lambda *args, **kwargs: old_image
    )
    monkeypatch.setattr(
        deploy,
        "_deploy_once",
        lambda *args, image_ref, **kwargs: image_ref,
    )

    deploy.main(["--project-dir", str(tmp_path), *HEALTH_ARGS, "deploy", new_image])

    state_path = tmp_path / ".deploy" / "state.json"
    state = json.loads(state_path.read_text())
    assert state["app"] == {
        "current_image": new_image,
        "previous_image": old_image,
    }
    assert stat.S_IMODE((tmp_path / ".deploy").stat().st_mode) == 0o700
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600


def test_failed_deploy_rolls_back_to_pre_deploy_image_and_preserves_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    current_image = _image("a")
    previous_image = _image("b")
    failed_image = _image("c")
    state_path = tmp_path / ".deploy" / "state.json"
    deploy._ensure_file_permissions(state_path)
    deploy._update_service_state(
        state_path,
        "app",
        current_image=current_image,
        previous_image=previous_image,
    )
    monkeypatch.setattr(
        deploy, "_snapshot_current_state", lambda *args, **kwargs: current_image
    )
    calls: list[str] = []

    def fake_deploy_once(*args: object, image_ref: str, **kwargs: object) -> str:
        calls.append(image_ref)
        if image_ref == failed_image:
            raise deploy.DeployError("synthetic liveness failure")
        return image_ref

    monkeypatch.setattr(deploy, "_deploy_once", fake_deploy_once)

    with pytest.raises(SystemExit, match="synthetic liveness failure"):
        deploy.main(
            ["--project-dir", str(tmp_path), *HEALTH_ARGS, "deploy", failed_image]
        )

    assert calls == [failed_image, current_image]
    state = json.loads(state_path.read_text())
    assert state["app"] == {
        "current_image": current_image,
        "previous_image": previous_image,
    }


def test_rollback_reads_state_only_after_lock_is_held(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    lock_held = False
    current_image = _image("a")
    previous_image = _image("b")

    @contextlib.contextmanager
    def fake_lock(*args: object, **kwargs: object):
        nonlocal lock_held
        lock_held = True
        try:
            yield
        finally:
            lock_held = False

    def fake_load(*args: object, **kwargs: object) -> tuple[str, str]:
        assert lock_held
        return current_image, previous_image

    monkeypatch.setattr(deploy, "_deploy_lock", fake_lock)
    monkeypatch.setattr(deploy, "_load_service_state", fake_load)
    monkeypatch.setattr(
        deploy, "_snapshot_current_state", lambda *args, **kwargs: current_image
    )
    monkeypatch.setattr(
        deploy,
        "_deploy_once",
        lambda *args, image_ref, **kwargs: image_ref,
    )

    deploy.main(["--project-dir", str(tmp_path), *HEALTH_ARGS, "rollback"])


def test_rollback_rejects_legacy_current_manifest_before_explicit_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    current_image = _image("a")
    explicit_target = _image("b")
    state_path = tmp_path / ".deploy" / "state.json"
    deploy._ensure_file_permissions(state_path)
    deploy._update_service_state(
        state_path,
        "app",
        current_image=current_image,
        previous_image=None,
    )
    monkeypatch.setattr(
        deploy, "_snapshot_current_state", lambda *args, **kwargs: current_image
    )

    validated: list[str] = []

    def validate(ref: str, *, dry_run: bool) -> None:
        validated.append(ref)
        if ref == current_image:
            raise deploy.DeployError("Image reference is not an OCI image index")

    monkeypatch.setattr(deploy, "_validate_oci_index_ref", validate)
    with pytest.raises(SystemExit, match="not an OCI image index"):
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                *HEALTH_ARGS,
                "rollback",
                explicit_target,
            ]
        )
    assert validated == [current_image]


def test_migrate_legacy_establishes_index_only_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    legacy_image = _image("a")
    target_index = _image("b")
    monkeypatch.setattr(
        deploy, "_snapshot_current_state", lambda *args, **kwargs: legacy_image
    )
    monkeypatch.setattr(
        deploy,
        "_deploy_once",
        lambda *args, image_ref, **kwargs: image_ref,
    )

    deploy.main(
        [
            "--project-dir",
            str(tmp_path),
            *HEALTH_ARGS,
            "migrate-legacy",
            legacy_image,
            target_index,
        ]
    )

    state = json.loads((tmp_path / ".deploy" / "state.json").read_text())
    assert state["app"] == {
        "current_image": target_index,
        "previous_image": None,
    }


def test_failed_legacy_migration_restores_exact_legacy_without_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    legacy_image = _image("a")
    target_index = _image("b")
    monkeypatch.setattr(
        deploy, "_snapshot_current_state", lambda *args, **kwargs: legacy_image
    )
    calls: list[str] = []

    def fake_deploy_once(*args: object, image_ref: str, **kwargs: object) -> str:
        calls.append(image_ref)
        if image_ref == target_index:
            raise deploy.DeployError("synthetic migration failure")
        return image_ref

    monkeypatch.setattr(deploy, "_deploy_once", fake_deploy_once)

    with pytest.raises(SystemExit, match="synthetic migration failure"):
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                *HEALTH_ARGS,
                "migrate-legacy",
                legacy_image,
                target_index,
            ]
        )
    assert calls == [target_index, legacy_image]
    assert json.loads((tmp_path / ".deploy" / "state.json").read_text()) == {}


def test_rollback_to_explicit_target_restores_original_current_on_verify_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    current_image = _image("a")
    previous_image = _image("b")
    rollback_target = _image("c")
    state_path = tmp_path / ".deploy" / "state.json"
    deploy._ensure_file_permissions(state_path)
    deploy._update_service_state(
        state_path,
        "app",
        current_image=current_image,
        previous_image=previous_image,
    )

    monkeypatch.setattr(
        deploy, "_snapshot_current_state", lambda *args, **kwargs: current_image
    )
    calls: list[str] = []

    def fake_deploy_once(*args: object, image_ref: str, **kwargs: object) -> str:
        calls.append(image_ref)
        if image_ref == rollback_target:
            raise deploy.DeployError("synthetic rollback failure")
        return image_ref

    monkeypatch.setattr(deploy, "_deploy_once", fake_deploy_once)

    with pytest.raises(SystemExit, match="synthetic rollback failure"):
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                *HEALTH_ARGS,
                "rollback",
                rollback_target,
            ]
        )

    assert calls == [rollback_target, current_image]
    assert json.loads(state_path.read_text()) == {
        "app": {
            "current_image": current_image,
            "previous_image": previous_image,
        }
    }


def test_rollback_to_explicit_target_reports_double_failure_if_restore_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    current_image = _image("a")
    previous_image = _image("b")
    rollback_target = _image("c")
    state_path = tmp_path / ".deploy" / "state.json"
    deploy._ensure_file_permissions(state_path)
    deploy._update_service_state(
        state_path,
        "app",
        current_image=current_image,
        previous_image=previous_image,
    )

    monkeypatch.setattr(
        deploy, "_snapshot_current_state", lambda *args, **kwargs: current_image
    )
    calls: list[str] = []

    def fake_deploy_once(*args: object, image_ref: str, **kwargs: object) -> str:
        calls.append(image_ref)
        if image_ref == rollback_target:
            raise deploy.DeployError("synthetic rollback failure")
        if image_ref == current_image:
            raise deploy.DeployError("synthetic restore failure")
        return image_ref

    monkeypatch.setattr(deploy, "_deploy_once", fake_deploy_once)

    with pytest.raises(
        SystemExit,
        match="rollback restore to .* also failed: synthetic restore failure",
    ):
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                *HEALTH_ARGS,
                "rollback",
                rollback_target,
            ]
        )

    assert calls == [rollback_target, current_image]
    assert json.loads(state_path.read_text()) == {
        "app": {
            "current_image": current_image,
            "previous_image": previous_image,
        }
    }


def test_legacy_migration_dry_run_uses_explicit_legacy_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    legacy_image = _image("a")
    target_index = _image("b")
    monkeypatch.setattr(
        deploy,
        "_snapshot_current_state",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("dry-run must not inspect the live container")
        ),
    )
    assert (
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                "--dry-run",
                *HEALTH_ARGS,
                "migrate-legacy",
                legacy_image,
                target_index,
            ]
        )
        == 0
    )


def test_running_image_drift_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    state_path = tmp_path / ".deploy" / "state.json"
    deploy._ensure_file_permissions(state_path)
    deploy._update_service_state(
        state_path,
        "app",
        current_image=_image("a"),
        previous_image=_image("b"),
    )
    monkeypatch.setattr(
        deploy, "_snapshot_current_state", lambda *args, **kwargs: _image("c")
    )

    with pytest.raises(SystemExit, match="differs from deployment state"):
        deploy.main(
            ["--project-dir", str(tmp_path), *HEALTH_ARGS, "deploy", _image("d")]
        )


def test_corrupt_persisted_image_ref_fails_closed_before_deploy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    state_path = tmp_path / ".deploy" / "state.json"
    deploy._ensure_file_permissions(state_path)
    state_path.write_text(
        json.dumps(
            {
                "app": {
                    "current_image": "ghcr.io/ywyz/kindergartenmanager:latest",
                    "previous_image": _image("b"),
                }
            }
        )
    )
    state_path.chmod(0o600)
    monkeypatch.setattr(deploy, "_snapshot_current_state", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit, match="not an immutable image ref"):
        deploy.main(
            ["--project-dir", str(tmp_path), *HEALTH_ARGS, "deploy", _image("d")]
        )


def test_invalid_service_is_rejected(tmp_path: Path) -> None:
    _compose(tmp_path)
    with pytest.raises(SystemExit, match="Invalid compose service"):
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                "--service",
                "app\nmalicious",
                *HEALTH_ARGS,
                "deploy",
                _image("a"),
            ]
        )


def test_liveness_url_is_required_and_rejects_embedded_credentials(
    tmp_path: Path,
) -> None:
    _compose(tmp_path)
    with pytest.raises(SystemExit) as missing:
        deploy.main(
            ["--project-dir", str(tmp_path), "--dry-run", "deploy", _image("a")]
        )
    assert missing.value.code == 2

    with pytest.raises(SystemExit, match="without credentials"):
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                "--health-url",
                "https://user:password@manager.ywyz.tech/api/v1/health",
                "deploy",
                _image("a"),
            ]
        )


def test_non_digest_ref_is_rejected(tmp_path: Path) -> None:
    _compose(tmp_path)
    with pytest.raises(SystemExit, match="immutable"):
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                *HEALTH_ARGS,
                "deploy",
                "ghcr.io/ywyz/kindergartenmanager:latest",
            ]
        )


def test_command_failure_does_not_echo_captured_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "do-not-leak-this-value"
    monkeypatch.setattr(
        deploy.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 17, secret, secret
        ),
    )
    with pytest.raises(deploy.DeployError) as caught:
        deploy._run_command(["docker", "compose", "up"], dry_run=False)
    assert secret not in str(caught.value)


def test_command_timeout_fails_closed_without_command_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        deploy.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(args[0], timeout=kwargs["timeout"])
        ),
    )
    with pytest.raises(deploy.DeployError, match="timed out"):
        deploy._run_command(["docker", "compose", "pull"], dry_run=False)


def test_oci_index_validation_requires_both_release_platforms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "mediaType": deploy.OCI_INDEX_MEDIA_TYPE,
        "manifests": [
            {"platform": {"os": "linux", "architecture": "amd64"}},
        ],
    }
    monkeypatch.setattr(
        deploy,
        "_run_command",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, json.dumps(payload), ""
        ),
    )
    with pytest.raises(deploy.DeployError, match="missing required"):
        VALIDATE_OCI_INDEX_REF(_image("a"), dry_run=False)


def test_oci_index_validation_accepts_reviewed_platform_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "mediaType": deploy.OCI_INDEX_MEDIA_TYPE,
        "manifests": [
            {"platform": {"os": "linux", "architecture": "amd64"}},
            {"platform": {"os": "linux", "architecture": "arm64"}},
        ],
    }
    monkeypatch.setattr(
        deploy,
        "_run_command",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, json.dumps(payload), ""
        ),
    )
    VALIDATE_OCI_INDEX_REF(_image("a"), dry_run=False)


def test_documented_global_option_order_parses(tmp_path: Path) -> None:
    _compose(tmp_path)
    assert (
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                "--service",
                "app",
                "--dry-run",
                *HEALTH_ARGS,
                "deploy",
                _image("e"),
            ]
        )
        == 0
    )
