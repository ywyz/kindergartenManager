"""Contract tests for the immutable deploy script."""

from __future__ import annotations

import contextlib
import http.client
import json
import stat
import subprocess
from pathlib import Path
from typing import Self

import pytest

from scripts import deploy

LIVENESS_ARGS = ("--health-url", "https://manager.ywyz.tech/api/v1/health")
READINESS_ARGS = (
    "--readiness-url",
    "https://manager.ywyz.tech/api/v1/readiness",
)
HEALTH_ARGS = (*LIVENESS_ARGS, *READINESS_ARGS)
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
        readiness_url: str,
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


def test_first_deploy_does_not_persist_live_snapshot_before_dual_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    old_image = _image("a")
    failed_image = _image("b")
    state_path = tmp_path / ".deploy" / "state.json"
    monkeypatch.setattr(
        deploy, "_snapshot_current_state", lambda *args, **kwargs: old_image
    )
    calls: list[tuple[str, str, str]] = []

    def fake_deploy_once(
        *args: object,
        image_ref: str,
        health_url: str,
        readiness_url: str,
        **kwargs: object,
    ) -> str:
        calls.append((image_ref, health_url, readiness_url))
        assert json.loads(state_path.read_text()) == {}
        if image_ref == failed_image:
            raise deploy.DeployError("synthetic readiness failure")
        return image_ref

    monkeypatch.setattr(deploy, "_deploy_once", fake_deploy_once)

    with pytest.raises(SystemExit, match="synthetic readiness failure"):
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                *HEALTH_ARGS,
                "deploy",
                failed_image,
            ]
        )

    assert calls == [
        (failed_image, LIVENESS_ARGS[1], READINESS_ARGS[1]),
        (old_image, LIVENESS_ARGS[1], READINESS_ARGS[1]),
    ]
    assert json.loads(state_path.read_text()) == {
        "app": {"current_image": old_image, "previous_image": None}
    }


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


def test_failed_legacy_migration_reports_target_and_restore_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    legacy_image = _image("a")
    target_index = _image("b")
    monkeypatch.setattr(
        deploy, "_snapshot_current_state", lambda *args, **kwargs: legacy_image
    )

    def fake_deploy_once(*args: object, image_ref: str, **kwargs: object) -> str:
        if image_ref == target_index:
            raise deploy.DeployError("synthetic target readiness failure")
        raise deploy.DeployError("synthetic legacy restore failure")

    monkeypatch.setattr(deploy, "_deploy_once", fake_deploy_once)

    with pytest.raises(
        SystemExit,
        match=(
            "synthetic target readiness failure.*"
            "legacy restore.*synthetic legacy restore failure"
        ),
    ):
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
                *READINESS_ARGS,
                "deploy",
                _image("a"),
            ]
        )


def test_readiness_url_is_independently_required(tmp_path: Path) -> None:
    _compose(tmp_path)

    with pytest.raises(SystemExit) as missing:
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                "--dry-run",
                *LIVENESS_ARGS,
                "deploy",
                _image("a"),
            ]
        )
    assert missing.value.code == 2

    with pytest.raises(SystemExit, match="Readiness URL must be .*without credentials"):
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                *LIVENESS_ARGS,
                "--readiness-url",
                "https://user:password@manager.ywyz.tech/api/v1/readiness",
                "deploy",
                _image("a"),
            ]
        )


@pytest.mark.parametrize(
    "readiness_alias",
    [
        LIVENESS_ARGS[1],
        LIVENESS_ARGS[1] + "/",
        "https://manager.ywyz.tech/api/v1/%68ealth",
    ],
)
def test_liveness_and_readiness_urls_must_be_distinct(
    tmp_path: Path, readiness_alias: str
) -> None:
    _compose(tmp_path)

    with pytest.raises(SystemExit, match="must be different"):
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                "--dry-run",
                *LIVENESS_ARGS,
                "--readiness-url",
                readiness_alias,
                "deploy",
                _image("a"),
            ]
        )


def test_explicit_noop_rollback_still_requires_both_gates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _compose(tmp_path)
    current_image = _image("a")
    previous_image = _image("b")
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

    def failed_gates(*args: object, **kwargs: object) -> None:
        raise deploy.DeployError("synthetic readiness failure")

    monkeypatch.setattr(deploy, "_wait_for_deployment_gates", failed_gates)

    with pytest.raises(SystemExit, match="synthetic readiness failure"):
        deploy.main(
            [
                "--project-dir",
                str(tmp_path),
                *HEALTH_ARGS,
                "rollback",
                current_image,
            ]
        )

    assert json.loads(state_path.read_text()) == {
        "app": {
            "current_image": current_image,
            "previous_image": previous_image,
        }
    }


def test_deployment_gates_check_liveness_then_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_wait(url: str, *, timeout_seconds: int, dry_run: bool, gate: str) -> None:
        calls.append((gate, url))

    monkeypatch.setattr(deploy, "_wait_for_http_gate", fake_wait)

    deploy._wait_for_deployment_gates(
        LIVENESS_ARGS[1],
        READINESS_ARGS[1],
        timeout_seconds=17,
        dry_run=False,
    )

    assert calls == [
        ("liveness", LIVENESS_ARGS[1]),
        ("readiness", READINESS_ARGS[1]),
    ]


class _ProbeResponse:
    def __init__(
        self,
        url: str,
        payload: object | bytes,
        *,
        status: int = 200,
        read_error: Exception | None = None,
    ) -> None:
        self.status = status
        self._url = url
        self._payload = (
            payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        )
        self._read_error = read_error

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def geturl(self) -> str:
        return self._url

    def read(self, _limit: int) -> bytes:
        if self._read_error is not None:
            raise self._read_error
        return self._payload


def test_readiness_gate_rejects_a_liveness_only_200_response() -> None:
    response = _ProbeResponse(
        READINESS_ARGS[1],
        {
            "status": "ok",
            "service": "kindergarten-teaching-api",
            "version": "v1",
            "time": "2026-09-01T00:00:00Z",
        },
    )

    assert not deploy._probe_response_is_valid(
        response,
        requested_url=READINESS_ARGS[1],
        gate="readiness",
    )


def test_probe_gates_require_their_exact_safe_json_contracts() -> None:
    liveness = _ProbeResponse(
        LIVENESS_ARGS[1],
        {"status": "ok", "service": "kindergarten-teaching-api", "version": "v1"},
    )
    readiness = _ProbeResponse(
        READINESS_ARGS[1],
        {
            "status": "ready",
            "service": "kindergarten-teaching-api",
            "version": "v1",
            "checks": {"database": "ok"},
        },
    )

    assert deploy._probe_response_is_valid(
        liveness, requested_url=LIVENESS_ARGS[1], gate="liveness"
    )
    assert deploy._probe_response_is_valid(
        readiness, requested_url=READINESS_ARGS[1], gate="readiness"
    )


@pytest.mark.parametrize(
    "response",
    [
        _ProbeResponse(
            "https://redirected.invalid/api/v1/health",
            {
                "status": "ok",
                "service": "kindergarten-teaching-api",
                "version": "v1",
            },
        ),
        _ProbeResponse(LIVENESS_ARGS[1], b"not-json"),
        _ProbeResponse(LIVENESS_ARGS[1], b"x" * 1025),
    ],
)
def test_probe_gate_rejects_redirect_invalid_json_and_oversize_body(
    response: _ProbeResponse,
) -> None:
    assert not deploy._probe_response_is_valid(
        response,
        requested_url=LIVENESS_ARGS[1],
        gate="liveness",
    )


def test_body_disconnect_becomes_gate_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _ProbeResponse(
        LIVENESS_ARGS[1],
        b"",
        read_error=http.client.IncompleteRead(b'{"status":', 100),
    )
    times = iter((0.0, 0.0, 2.0))
    monkeypatch.setattr(deploy.request, "urlopen", lambda *_args, **_kwargs: response)
    monkeypatch.setattr(deploy.time, "time", lambda: next(times))
    monkeypatch.setattr(deploy.time, "sleep", lambda _seconds: None)

    with pytest.raises(deploy.DeployError, match="Liveness check timed out"):
        deploy._wait_for_http_gate(
            LIVENESS_ARGS[1],
            timeout_seconds=1,
            dry_run=False,
            gate="liveness",
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
