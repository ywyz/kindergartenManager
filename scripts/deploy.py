#!/usr/bin/env python3
"""Production deploy/rollback utilities for digest-pinned Docker images."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import http.client
import json
import os
import posixpath
import re
import shlex
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from app.core.backup_evidence import BackupEvidenceError
from app.core.migration_receipt import (
    MigrationReceiptError,
    validate_migration_receipt,
)
from app.core.startup import (
    configured_database_identity_sha256,
    read_configured_database_revision,
)
from app.jobs.backup_restore import (
    validate_generated_attestation,
)
from scripts.r5_post_migration_rollback import run_post_migration_rollback

REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR_NAME = ".deploy"
STATE_FILE_NAME = "state.json"
LOCK_FILE_NAME = "deploy.lock"
DIGEST_RE = re.compile(r"^[a-z0-9][a-z0-9._:/-]*[a-z0-9]@sha256:[0-9a-f]{64}$")
SERVICE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")
DEFAULT_HEALTH_TIMEOUT_SECONDS = 120
DEFAULT_COMMAND_TIMEOUT_SECONDS = 300
MAX_ACCEPTANCE_RESULT_BYTES = 64 * 1024
OCI_INDEX_MEDIA_TYPE = "application/vnd.oci.image.index.v1+json"
REQUIRED_PLATFORMS = {("linux", "amd64"), ("linux", "arm64")}
ACCEPTANCE_RESULT_FIELDS = {
    "schema_version",
    "status",
    "phase",
    "image_ref",
    "gate",
    "checks",
}
ACCEPTANCE_CHECKS = {
    "login": {"login"},
    "business": {
        "daily_plan",
        "game_observation",
        "one_on_one_listening",
        "homemade_teaching",
        "course_review",
        "image_blob",
        "ai_key_decryption",
        "word_export",
        "data_snapshot",
    },
}


class DeployError(RuntimeError):
    """Raised for deployment flow errors."""


def is_immutable_image_ref(ref: str) -> bool:
    return bool(DIGEST_RE.fullmatch(ref))


def _is_safe_service_name(service: str) -> bool:
    return bool(SERVICE_NAME_RE.fullmatch(service))


def _load_state(state_path: Path) -> dict[str, dict[str, str | None]]:
    if not state_path.exists():
        return {}

    try:
        with state_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DeployError("Deployment state is unreadable or invalid") from exc
    if not isinstance(data, dict):
        raise DeployError("Deployment state must be a JSON object")
    return data


def _write_atomic_json(
    state_path: Path, state: dict[str, dict[str, str | None]]
) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, tmp_name = tempfile.mkstemp(
        prefix=f".{state_path.name}.", dir=state_path.parent
    )
    tmp_path = Path(tmp_name)
    try:
        os.fchmod(descriptor, 0o600)
        payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, state_path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if tmp_path.exists():
            tmp_path.unlink()


def _secure_dir(path: Path, mode: int) -> None:
    if path.is_symlink():
        raise DeployError(f"Deployment directory must not be a symlink: {path}")
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise DeployError(f"Deployment state path is not a directory: {path}")
    current_mode = stat.S_IMODE(path.stat().st_mode)
    if current_mode != mode:
        path.chmod(mode)


def _secure_state_file(path: Path) -> None:
    if path.is_symlink():
        raise DeployError(f"Deployment state file must not be a symlink: {path}")
    if not path.exists():
        _write_atomic_json(path, {})
    else:
        path.chmod(0o600)


def _ensure_file_permissions(state_file: Path) -> None:
    _secure_dir(state_file.parent, 0o700)
    if state_file.exists() or state_file.is_symlink():
        _secure_state_file(state_file)


def _compose_override(*, service: str, image_ref: str) -> str:
    return f"services:\n  {service}:\n    image: {json.dumps(image_ref)}\n"


def _resolve_within_project(base: Path, path: Path) -> Path:
    return path if path.is_absolute() else (base / path)


def _compose_base_cmd(
    compose_file: Path,
    project_dir: Path,
    override_file: Path | None,
    command: tuple[str, ...],
) -> list[str]:
    cmd: list[str] = [
        "docker",
        "compose",
        "--project-directory",
        str(project_dir),
        "-f",
        str(compose_file),
    ]
    if override_file is not None:
        cmd.extend(["-f", str(override_file)])
    cmd.extend(command)
    return cmd


def _run_command(command: list[str], *, dry_run: bool) -> subprocess.CompletedProcess:
    if dry_run:
        print(f"[dry-run] {shlex.join(command)}")
        return subprocess.CompletedProcess(command, 0, "", "")

    try:
        process = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            timeout=DEFAULT_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise DeployError(
            f"Deployment command timed out after {DEFAULT_COMMAND_TIMEOUT_SECONDS}s"
        ) from exc
    if process.returncode != 0:
        raise DeployError(
            f"Deployment command failed with exit status {process.returncode}"
        )
    return process


def _validate_oci_index_ref(image_ref: str, *, dry_run: bool) -> None:
    """Fail closed unless the ref resolves to the reviewed two-platform OCI index."""
    inspect = _run_command(
        ["docker", "buildx", "imagetools", "inspect", "--raw", image_ref],
        dry_run=dry_run,
    )
    if dry_run:
        return
    try:
        payload = json.loads(inspect.stdout)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DeployError(
            "Image reference did not return valid OCI index JSON"
        ) from exc
    if (
        not isinstance(payload, dict)
        or payload.get("mediaType") != OCI_INDEX_MEDIA_TYPE
    ):
        raise DeployError("Image reference is not an OCI image index")
    manifests = payload.get("manifests")
    if not isinstance(manifests, list):
        raise DeployError("OCI image index has no platform manifests")
    if len(manifests) != len(REQUIRED_PLATFORMS):
        raise DeployError(
            "OCI image index has missing required or unexpected manifests; "
            "it must contain the exactly required set of exactly two platforms"
        )
    platforms = {
        (platform.get("os"), platform.get("architecture"))
        for manifest in manifests
        if isinstance(manifest, dict)
        and isinstance((platform := manifest.get("platform")), dict)
    }
    if platforms != REQUIRED_PLATFORMS:
        raise DeployError(
            "OCI image index is missing required or has unexpected platforms; "
            "it must contain exactly required release platforms"
        )


def _validate_oci_source_revision(image_ref: str, source_sha: str) -> None:
    """Require every platform manifest to carry the exact source revision label."""
    inspected = _run_command(
        ["docker", "buildx", "imagetools", "inspect", "--raw", image_ref],
        dry_run=False,
    )
    try:
        index = json.loads(inspected.stdout)
    except json.JSONDecodeError as exc:
        raise DeployError("OCI image index metadata is invalid") from exc
    repository = image_ref.partition("@")[0]
    manifests = index.get("manifests") if isinstance(index, dict) else None
    if not isinstance(manifests, list) or len(manifests) != 2:
        raise DeployError("OCI source revision requires exactly two manifests")
    revisions: list[str] = []
    for manifest in manifests:
        digest = manifest.get("digest") if isinstance(manifest, dict) else None
        if not isinstance(digest, str):
            raise DeployError("OCI platform manifest digest is invalid")
        image = _run_command(
            [
                "docker",
                "buildx",
                "imagetools",
                "inspect",
                "--format",
                "{{json .Image}}",
                f"{repository}@{digest}",
            ],
            dry_run=False,
        )
        try:
            payload = json.loads(image.stdout)
            revision = payload["config"]["Labels"]["org.opencontainers.image.revision"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise DeployError("OCI platform source revision label is invalid") from exc
        revisions.append(revision)
    if revisions != [source_sha, source_sha]:
        raise DeployError("OCI platform source revision does not match release SHA")


def _run_compose(
    compose_file: Path,
    override_file: Path | None,
    project_dir: Path,
    *command: str,
    dry_run: bool,
) -> subprocess.CompletedProcess:
    return _run_command(
        _compose_base_cmd(
            compose_file=compose_file,
            project_dir=project_dir,
            override_file=override_file,
            command=command,
        ),
        dry_run=dry_run,
    )


def _wait_for_http_gate(
    url: str,
    *,
    timeout_seconds: int,
    dry_run: bool,
    gate: str,
) -> None:
    if dry_run:
        print(f"[dry-run] wait for {gate} URL: {url}")
        return

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with request.urlopen(url, timeout=4) as response:
                if _probe_response_is_valid(
                    response,
                    requested_url=url,
                    gate=gate,
                ):
                    return
        except (error.URLError, TimeoutError):
            pass
        time.sleep(2)

    raise DeployError(f"{gate.capitalize()} check timed out after {timeout_seconds}s.")


def _probe_response_is_valid(
    response: Any,
    *,
    requested_url: str,
    gate: str,
) -> bool:
    try:
        if response.status != 200 or response.geturl() != requested_url:
            return False
        raw_payload = response.read(1025)
        if len(raw_payload) > 1024:
            return False
        payload = json.loads(raw_payload)
    except (
        OSError,
        http.client.HTTPException,
        json.JSONDecodeError,
        UnicodeDecodeError,
        TypeError,
        ValueError,
    ):
        return False
    if not isinstance(payload, dict):
        return False
    if (
        payload.get("service") != "kindergarten-teaching-api"
        or payload.get("version") != "v1"
    ):
        return False
    if gate == "liveness":
        return payload.get("status") == "ok"
    if gate == "readiness":
        checks = payload.get("checks")
        return (
            payload.get("status") == "ready"
            and isinstance(checks, dict)
            and checks.get("database") == "ok"
        )
    return False


def _wait_for_deployment_gates(
    health_url: str,
    readiness_url: str,
    *,
    timeout_seconds: int,
    dry_run: bool,
) -> None:
    _wait_for_http_gate(
        health_url,
        timeout_seconds=timeout_seconds,
        dry_run=dry_run,
        gate="liveness",
    )
    _wait_for_http_gate(
        readiness_url,
        timeout_seconds=timeout_seconds,
        dry_run=dry_run,
        gate="readiness",
    )


def _running_service_id(
    compose_file: Path,
    project_dir: Path,
    service: str,
    *,
    dry_run: bool,
) -> str:
    ps = _run_command(
        _compose_base_cmd(
            compose_file=compose_file,
            project_dir=project_dir,
            override_file=None,
            command=("ps", "-q", service),
        ),
        dry_run=dry_run,
    )
    return ps.stdout.strip().splitlines()[0] if ps.stdout else ""


def _read_container_image(
    compose_file: Path,
    project_dir: Path,
    service: str,
    *,
    dry_run: bool,
) -> str:
    if dry_run:
        return ""

    container_id = _running_service_id(
        compose_file=compose_file,
        project_dir=project_dir,
        service=service,
        dry_run=False,
    )
    if not container_id:
        return ""

    inspect = _run_command(
        ["docker", "inspect", "-f", "{{.Config.Image}}", container_id],
        dry_run=dry_run,
    )
    image = inspect.stdout.strip()
    return image


def _snapshot_current_state(
    compose_file: Path,
    project_dir: Path,
    service: str,
    *,
    dry_run: bool,
) -> str | None:
    image = _read_container_image(
        compose_file=compose_file,
        project_dir=project_dir,
        service=service,
        dry_run=dry_run,
    )
    return image or None


def _update_service_state(
    state_path: Path,
    service: str,
    *,
    current_image: str,
    previous_image: str | None,
) -> None:
    state = _load_state(state_path)
    state[service] = {
        "current_image": current_image,
        "previous_image": previous_image,
    }
    _write_atomic_json(state_path, state)


def _load_service_state(
    state_path: Path, service: str
) -> tuple[str | None, str | None]:
    record = _load_state(state_path).get(service, {})
    if not isinstance(record, dict):
        raise DeployError(f"Deployment state for {service} is invalid")
    current_image = record.get("current_image")
    previous_image = record.get("previous_image")
    for field_name, image_ref in (
        ("current_image", current_image),
        ("previous_image", previous_image),
    ):
        if image_ref is not None and (
            not isinstance(image_ref, str) or not is_immutable_image_ref(image_ref)
        ):
            raise DeployError(
                f"Deployment state {field_name} for {service} is not an immutable image ref"
            )
    return current_image, previous_image


def _deploy_once(
    compose_file: Path,
    project_dir: Path,
    override_file: Path,
    service: str,
    image_ref: str,
    health_url: str,
    readiness_url: str,
    dry_run: bool,
) -> str:
    if dry_run:
        _run_compose(
            compose_file,
            override_file,
            project_dir,
            "pull",
            service,
            dry_run=True,
        )
        _run_compose(
            compose_file,
            override_file,
            project_dir,
            "up",
            "--no-build",
            "--no-deps",
            "-d",
            service,
            dry_run=True,
        )
        return image_ref

    _start_image(
        compose_file=compose_file,
        project_dir=project_dir,
        override_file=override_file,
        service=service,
        image_ref=image_ref,
        dry_run=False,
    )
    _wait_for_deployment_gates(
        health_url,
        readiness_url,
        timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
        dry_run=False,
    )
    return image_ref


def _start_image(
    *,
    compose_file: Path,
    project_dir: Path,
    override_file: Path,
    service: str,
    image_ref: str,
    dry_run: bool,
) -> None:
    """Start and bind one image without collapsing later acceptance gates."""
    descriptor = os.open(
        override_file,
        os.O_CREAT | os.O_TRUNC | os.O_WRONLY,
        0o600,
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(_compose_override(service=service, image_ref=image_ref))
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    try:
        _run_compose(
            compose_file,
            override_file,
            project_dir,
            "pull",
            service,
            dry_run=dry_run,
        )
        _run_compose(
            compose_file,
            override_file,
            project_dir,
            "up",
            "--no-build",
            "--no-deps",
            "-d",
            service,
            dry_run=dry_run,
        )

        current_image = _read_container_image(
            compose_file=compose_file,
            project_dir=project_dir,
            service=service,
            dry_run=dry_run,
        )
        if current_image != image_ref:
            raise DeployError(
                f"Deployed image mismatch for {service}. expected={image_ref} actual={current_image}"
            )

    finally:
        if override_file.exists():
            override_file.unlink()


def _with_state_dir(project_dir: Path, state_dir_arg: Path) -> Path:
    return (
        state_dir_arg if state_dir_arg.is_absolute() else (project_dir / state_dir_arg)
    )


def _require_compose_inputs(compose_file: Path) -> None:
    if not compose_file.exists():
        raise DeployError(f"Compose file not found: {compose_file}")


def _require_service(service: str) -> None:
    if not _is_safe_service_name(service):
        raise DeployError(f"Invalid compose service name: {service}")


def _require_verified_backup(
    evidence_path: Path | None,
    protected_image: str | None,
) -> None:
    if evidence_path is None or protected_image is None:
        raise DeployError(
            "Verified producer backup evidence and protected image are required"
        )
    try:
        verified = validate_generated_attestation(
            evidence_path,
            expected_protected_image=protected_image,
        )
        if (
            verified.database_identity_sha256 != configured_database_identity_sha256()
            or verified.database_revision != read_configured_database_revision()
        ):
            raise BackupEvidenceError(
                "Backup evidence does not match the configured database"
            )
    except Exception as exc:
        raise DeployError("Verified backup producer provenance is invalid") from exc


def _require_post_migration_backup(
    evidence_path: Path | None,
    protected_image: str | None,
    receipt_path: Path | None,
    target_image: str,
    source_sha: str | None,
) -> None:
    if (
        evidence_path is None
        or protected_image is None
        or receipt_path is None
        or source_sha is None
    ):
        raise DeployError(
            "Verified backup evidence and migration receipt binding are required"
        )
    try:
        verified = validate_generated_attestation(
            evidence_path,
            expected_protected_image=protected_image,
        )
        current_identity = configured_database_identity_sha256()
        current_revision = read_configured_database_revision()
        receipt = validate_migration_receipt(
            receipt_path,
            evidence_path=evidence_path,
            expected_protected_image=protected_image,
            expected_target_image=target_image,
            expected_source_sha=source_sha,
            expected_database_identity_sha256=current_identity,
            expected_after_revision=current_revision,
        )
        if (
            verified.database_identity_sha256 != current_identity
            or verified.database_revision != receipt.before_revision
            or verified.artifact_sha256 != receipt.backup_artifact_sha256
            or receipt.after_revision != current_revision
        ):
            raise MigrationReceiptError(
                "Migration receipt does not bridge the verified backup and current database"
            )
    except Exception as exc:
        raise DeployError("Verified post-migration backup binding is invalid") from exc


def _require_deploy_evidence(args: argparse.Namespace) -> None:
    post_migration_values = (
        args.migration_receipt,
        args.source_sha,
        args.acceptance_runner,
    )
    if any(post_migration_values) and not all(post_migration_values):
        raise DeployError(
            "Post-migration deploy requires migration receipt, source SHA, "
            "and acceptance runner together"
        )
    if not any(post_migration_values):
        _require_verified_backup(args.backup_evidence, args.protected_image)
        return
    _require_post_migration_backup(
        args.backup_evidence,
        args.protected_image,
        args.migration_receipt,
        args.image_ref,
        args.source_sha,
    )
    _require_acceptance_runner(args.acceptance_runner)


def _open_acceptance_runner(path: Path | None) -> int:
    if path is None or not path.is_absolute():
        raise DeployError("Post-migration acceptance runner path is unsafe")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise DeployError("Post-migration acceptance runner is unavailable") from exc
    info = os.fstat(descriptor)
    if (
        not stat.S_ISREG(info.st_mode)
        or (hasattr(os, "geteuid") and info.st_uid != os.geteuid())
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        os.close(descriptor)
        raise DeployError(
            "Post-migration acceptance runner must be owner-only executable mode 0700"
        )
    return descriptor


def _require_acceptance_runner(path: Path | None) -> Path:
    descriptor = _open_acceptance_runner(path)
    os.close(descriptor)
    assert path is not None
    return path


def _validate_acceptance_result(
    payload: object,
    *,
    phase: str,
    image_ref: str,
    gate: str,
) -> None:
    expected_checks = ACCEPTANCE_CHECKS.get(gate)
    if (
        expected_checks is None
        or not isinstance(payload, dict)
        or set(payload) != ACCEPTANCE_RESULT_FIELDS
        or payload.get("schema_version") != 1
        or payload.get("status") != "passed"
        or payload.get("phase") != phase
        or payload.get("image_ref") != image_ref
        or payload.get("gate") != gate
    ):
        raise DeployError("Post-migration acceptance result is invalid")
    checks = payload.get("checks")
    if (
        not isinstance(checks, dict)
        or set(checks) != expected_checks
        or any(value != "passed" for value in checks.values())
    ):
        raise DeployError("Post-migration acceptance result is incomplete")


def _run_acceptance_gate(path: Path, *, phase: str, image_ref: str, gate: str) -> None:
    descriptor = _open_acceptance_runner(path)
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "R5_ACCEPTANCE_PHASE": phase,
        "R5_ACCEPTANCE_IMAGE": image_ref,
        "R5_ACCEPTANCE_GATE": gate,
    }
    try:
        try:
            process = subprocess.run(
                [f"/proc/self/fd/{descriptor}"],
                check=False,
                text=False,
                capture_output=True,
                timeout=DEFAULT_COMMAND_TIMEOUT_SECONDS,
                env=environment,
                pass_fds=(descriptor,),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DeployError("Post-migration acceptance runner failed") from exc
    finally:
        os.close(descriptor)
    if process.returncode != 0:
        raise DeployError("Post-migration acceptance gates failed")
    if len(process.stdout) > MAX_ACCEPTANCE_RESULT_BYTES:
        raise DeployError("Post-migration acceptance result is too large")
    try:
        payload = json.loads(process.stdout)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DeployError("Post-migration acceptance result is invalid") from exc
    _validate_acceptance_result(payload, phase=phase, image_ref=image_ref, gate=gate)


def _run_post_migration_deploy(
    args: argparse.Namespace,
    *,
    compose_file: Path,
    project_dir: Path,
    override_file: Path,
    state_file: Path,
    current_image: str,
) -> None:
    acceptance_runner = _require_acceptance_runner(args.acceptance_runner)

    def start_image(image_ref: str) -> None:
        _start_image(
            compose_file=compose_file,
            project_dir=project_dir,
            override_file=override_file,
            service=args.service,
            image_ref=image_ref,
            dry_run=False,
        )

    def finalize_target() -> None:
        _require_post_migration_backup(
            args.backup_evidence,
            args.protected_image,
            args.migration_receipt,
            args.image_ref,
            args.source_sha,
        )
        _update_service_state(
            state_file,
            service=args.service,
            current_image=args.image_ref,
            previous_image=current_image,
        )

    result = run_post_migration_rollback(
        migrate=lambda: None,
        target_start=lambda: start_image(args.image_ref),
        target_liveness=lambda: _wait_for_http_gate(
            args.health_url,
            timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
            dry_run=False,
            gate="liveness",
        ),
        target_readiness=lambda: _wait_for_http_gate(
            args.readiness_url,
            timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
            dry_run=False,
            gate="readiness",
        ),
        target_login=lambda: _run_acceptance_gate(
            acceptance_runner,
            phase="target",
            image_ref=args.image_ref,
            gate="login",
        ),
        target_business=lambda: _run_acceptance_gate(
            acceptance_runner,
            phase="target",
            image_ref=args.image_ref,
            gate="business",
        ),
        rollback_start=lambda: start_image(current_image),
        rollback_liveness=lambda: _wait_for_http_gate(
            args.health_url,
            timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
            dry_run=False,
            gate="liveness",
        ),
        rollback_readiness=lambda: _wait_for_http_gate(
            args.readiness_url,
            timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
            dry_run=False,
            gate="readiness",
        ),
        rollback_login=lambda: _run_acceptance_gate(
            acceptance_runner,
            phase="rollback",
            image_ref=current_image,
            gate="login",
        ),
        rollback_business=lambda: _run_acceptance_gate(
            acceptance_runner,
            phase="rollback",
            image_ref=current_image,
            gate="business",
        ),
        finalize_deployment=finalize_target,
    )
    if result.status == "DEPLOYED":
        return
    if result.status == "ROLLED_BACK":
        raise DeployError(
            "Post-migration target failed; old image passed all rollback gates"
        )
    if result.status == "DATABASE_RESTORE_REQUIRED":
        raise DeployError(
            "Old image is incompatible with the migrated database; "
            f"DATABASE_RESTORE_REQUIRED primary={result.primary_failure} "
            f"rollback={result.rollback_failure}"
        )
    if result.status == "ROLLBACK_FAILED":
        raise DeployError(
            "Post-migration target and image rollback both failed; "
            f"primary={result.primary_failure} rollback={result.rollback_failure}"
        )
    raise DeployError("Post-migration deployment state requires manual reconciliation")


def _report_dry_run_not_image_bound() -> None:
    print("BLOCKED: dry-run is NOT_IMAGE_BOUND and cannot prove actual image binding.")


def _require_live_image_binding(
    live_image: str | None,
    protected_image: str | None,
    *,
    dry_run: bool,
) -> None:
    if dry_run or protected_image is None:
        return
    expected = live_image or "no-running-image"
    if protected_image != expected:
        raise DeployError(
            "Verified backup evidence is not bound to the currently running image"
        )


def _require_probe_url(url: str, *, gate: str) -> None:
    parsed = parse.urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise DeployError(
            f"{gate.capitalize()} URL must be an HTTP(S) URL without credentials, query, or fragment"
        )


def _require_health_url(health_url: str) -> None:
    _require_probe_url(health_url, gate="liveness")


def _require_readiness_url(readiness_url: str) -> None:
    _require_probe_url(readiness_url, gate="readiness")


def _probe_url_identity(url: str) -> tuple[str, str, int, str]:
    parsed = parse.urlsplit(url)
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme.lower() == "https" else 80
    decoded_path = parse.unquote(parsed.path or "/")
    normalized_path = posixpath.normpath("/" + decoded_path.lstrip("/"))
    return (
        parsed.scheme.lower(),
        (parsed.hostname or "").lower(),
        port,
        normalized_path.rstrip("/") or "/",
    )


def _require_distinct_probe_urls(health_url: str, readiness_url: str) -> None:
    _require_health_url(health_url)
    _require_readiness_url(readiness_url)
    if _probe_url_identity(health_url) == _probe_url_identity(readiness_url):
        raise DeployError("Liveness and readiness URLs must be different endpoints")


def _validate_snapshot_state(current_image: str | None) -> None:
    if current_image is None:
        return
    if not is_immutable_image_ref(current_image):
        raise DeployError(
            f"Current image is not immutable digest ref and cannot provide safe rollback: {current_image}"
        )


def _rollback_or_restore(
    service: str,
    *,
    compose_file: Path,
    project_dir: Path,
    override_file: Path,
    target_image: str,
    restore_image: str,
    health_url: str,
    readiness_url: str,
    dry_run: bool,
) -> None:
    try:
        _deploy_once(
            compose_file=compose_file,
            project_dir=project_dir,
            override_file=override_file,
            service=service,
            image_ref=target_image,
            health_url=health_url,
            readiness_url=readiness_url,
            dry_run=dry_run,
        )
        return
    except DeployError as exc:
        if dry_run:
            raise
        print(
            f"{service} action failed; attempting rollback to {restore_image} before reporting failure."
        )
        try:
            _deploy_once(
                compose_file=compose_file,
                project_dir=project_dir,
                override_file=override_file,
                service=service,
                image_ref=restore_image,
                health_url=health_url,
                readiness_url=readiness_url,
                dry_run=False,
            )
        except DeployError as restore_error:
            raise DeployError(
                f"Primary action failed: {exc}; rollback restore to {restore_image} also failed: {restore_error}"
            ) from restore_error
        raise


@contextlib.contextmanager
def _deploy_lock(state_dir: Path, timeout_seconds: int):
    lock_path = state_dir / LOCK_FILE_NAME
    _secure_dir(state_dir, 0o700)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise DeployError("Deployment lock file is unsafe or unavailable") from exc
    os.fchmod(fd, 0o600)

    start = time.monotonic()
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() - start > timeout_seconds:
                    raise DeployError(
                        "Failed to acquire deployment lock before timeout"
                    )
                time.sleep(0.25)
        yield
    finally:
        os.close(fd)


def _deploy(args: argparse.Namespace) -> None:
    _require_deploy_evidence(args)
    if not is_immutable_image_ref(args.image_ref):
        raise DeployError(
            f"Image must be immutable digest ref ending with @sha256:<64 lower hex>: {args.image_ref}"
        )

    _require_service(args.service)
    _require_distinct_probe_urls(args.health_url, args.readiness_url)
    _validate_oci_index_ref(args.image_ref, dry_run=args.dry_run)

    project_dir = args.project_dir
    compose_file = _resolve_within_project(project_dir, args.compose_file)
    _require_compose_inputs(compose_file)

    state_dir = _with_state_dir(project_dir, args.state_dir)
    state_file = state_dir / STATE_FILE_NAME
    override_file = state_dir / "compose.image.override.yml"

    lock = (
        contextlib.nullcontext()
        if args.dry_run
        else _deploy_lock(state_dir, args.lock_timeout)
    )
    with lock:
        if not args.dry_run:
            _ensure_file_permissions(state_file)
        current_image, previous_image = _load_service_state(state_file, args.service)
        if args.dry_run:
            _report_dry_run_not_image_bound()
            live_image = None
        else:
            live_image = _snapshot_current_state(
                compose_file=compose_file,
                project_dir=project_dir,
                service=args.service,
                dry_run=False,
            )
        _require_live_image_binding(
            live_image, args.protected_image, dry_run=args.dry_run
        )
        _require_deploy_evidence(args)
        _validate_snapshot_state(live_image)
        for rollback_ref in (current_image, previous_image, live_image):
            if rollback_ref:
                _validate_oci_index_ref(rollback_ref, dry_run=args.dry_run)
        if current_image is None and live_image:
            current_image = live_image
            previous_image = None
        elif live_image and current_image and live_image != current_image:
            raise DeployError(
                "Running image differs from deployment state; reconcile it explicitly"
            )

        if args.migration_receipt is not None:
            if args.dry_run:
                return
            if current_image is None:
                raise DeployError(
                    "Post-migration deploy requires a current immutable rollback image"
                )
            _run_post_migration_deploy(
                args,
                compose_file=compose_file,
                project_dir=project_dir,
                override_file=override_file,
                state_file=state_file,
                current_image=current_image,
            )
            return

        if args.image_ref == current_image:
            _wait_for_deployment_gates(
                args.health_url,
                args.readiness_url,
                timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
                dry_run=args.dry_run,
            )
            if not args.dry_run:
                _update_service_state(
                    state_file,
                    service=args.service,
                    current_image=current_image,
                    previous_image=previous_image,
                )
            print(f"{args.service} already at {args.image_ref}, no change.")
            return

        pre_deploy_image = current_image

        try:
            deployed_image = _deploy_once(
                compose_file=compose_file,
                project_dir=project_dir,
                override_file=override_file,
                service=args.service,
                image_ref=args.image_ref,
                health_url=args.health_url,
                readiness_url=args.readiness_url,
                dry_run=args.dry_run,
            )
            if args.dry_run:
                return
            _update_service_state(
                state_file,
                service=args.service,
                current_image=deployed_image,
                previous_image=pre_deploy_image,
            )
        except DeployError:
            if args.dry_run or pre_deploy_image is None:
                raise
            print(
                f"Deploy failed; rolling back {args.service} to pre-deploy immutable ref {pre_deploy_image}"
            )
            _rollback_or_restore(
                args.service,
                compose_file=compose_file,
                project_dir=project_dir,
                override_file=override_file,
                target_image=pre_deploy_image,
                restore_image=pre_deploy_image,
                health_url=args.health_url,
                readiness_url=args.readiness_url,
                dry_run=False,
            )
            raise


def _rollback(args: argparse.Namespace) -> None:
    if any((args.migration_receipt, args.source_sha, args.acceptance_runner)):
        raise DeployError(
            "Post-migration deploy options are valid only for the immediate "
            "post-migration deploy; rollback requires fresh current-database evidence"
        )
    _require_verified_backup(
        args.backup_evidence,
        args.protected_image,
    )
    if args.image_ref and not is_immutable_image_ref(args.image_ref):
        raise DeployError(
            f"Image must be immutable digest ref ending with @sha256:<64 lower hex>: {args.image_ref}"
        )

    _require_service(args.service)
    _require_distinct_probe_urls(args.health_url, args.readiness_url)

    project_dir = args.project_dir
    compose_file = _resolve_within_project(project_dir, args.compose_file)
    _require_compose_inputs(compose_file)

    state_dir = _with_state_dir(project_dir, args.state_dir)
    state_file = state_dir / STATE_FILE_NAME
    override_file = state_dir / "compose.image.override.yml"

    lock = (
        contextlib.nullcontext()
        if args.dry_run
        else _deploy_lock(state_dir, args.lock_timeout)
    )
    with lock:
        if not args.dry_run:
            _ensure_file_permissions(state_file)
        current_image, previous_image = _load_service_state(state_file, args.service)
        if args.dry_run:
            _report_dry_run_not_image_bound()
            live_image = None
        else:
            live_image = _snapshot_current_state(
                compose_file=compose_file,
                project_dir=project_dir,
                service=args.service,
                dry_run=False,
            )
        _require_live_image_binding(
            live_image, args.protected_image, dry_run=args.dry_run
        )
        _require_verified_backup(
            args.backup_evidence,
            args.protected_image,
        )
        _validate_snapshot_state(live_image)
        for rollback_ref in (current_image, previous_image, live_image):
            if rollback_ref:
                _validate_oci_index_ref(rollback_ref, dry_run=args.dry_run)
        if current_image is None and live_image:
            current_image = live_image
        elif live_image and current_image and live_image != current_image:
            raise DeployError(
                "Running image differs from deployment state; reconcile it explicitly"
            )
        target_image = args.image_ref or previous_image

        if not target_image:
            raise DeployError(
                f"Service {args.service} has no previous immutable image for rollback."
            )

        _validate_snapshot_state(target_image)
        _validate_oci_index_ref(target_image, dry_run=args.dry_run)

        if target_image == current_image:
            _wait_for_deployment_gates(
                args.health_url,
                args.readiness_url,
                timeout_seconds=DEFAULT_HEALTH_TIMEOUT_SECONDS,
                dry_run=args.dry_run,
            )
            print(f"{args.service} already at {target_image}, no change.")
            return

        if current_image is None:
            raise DeployError(
                f"Service {args.service} has no current immutable image to restore on failure."
            )

        _rollback_or_restore(
            args.service,
            compose_file=compose_file,
            project_dir=project_dir,
            override_file=override_file,
            target_image=target_image,
            restore_image=current_image,
            health_url=args.health_url,
            readiness_url=args.readiness_url,
            dry_run=args.dry_run,
        )
        restored = target_image

        if args.dry_run:
            return

        _update_service_state(
            state_file,
            service=args.service,
            current_image=restored,
            previous_image=current_image,
        )


def _migrate_legacy(args: argparse.Namespace) -> None:
    """Establish an index-only baseline from one explicitly accepted legacy ref."""
    if any((args.migration_receipt, args.source_sha, args.acceptance_runner)):
        raise DeployError(
            "Post-migration deploy options are not valid for legacy migration"
        )
    _require_verified_backup(
        args.backup_evidence,
        args.protected_image,
    )
    if not is_immutable_image_ref(args.image_ref):
        raise DeployError(
            f"Image must be immutable digest ref ending with @sha256:<64 lower hex>: {args.image_ref}"
        )
    if not is_immutable_image_ref(args.legacy_image_ref):
        raise DeployError("Legacy image must be an immutable digest ref")
    _require_service(args.service)
    _require_distinct_probe_urls(args.health_url, args.readiness_url)
    _validate_oci_index_ref(args.image_ref, dry_run=args.dry_run)

    project_dir = args.project_dir
    compose_file = _resolve_within_project(project_dir, args.compose_file)
    _require_compose_inputs(compose_file)
    state_dir = _with_state_dir(project_dir, args.state_dir)
    state_file = state_dir / STATE_FILE_NAME
    override_file = state_dir / "compose.image.override.yml"

    lock = (
        contextlib.nullcontext()
        if args.dry_run
        else _deploy_lock(state_dir, args.lock_timeout)
    )
    with lock:
        if not args.dry_run:
            _ensure_file_permissions(state_file)
        current_image, previous_image = _load_service_state(state_file, args.service)
        if current_image is not None or previous_image is not None:
            raise DeployError(
                "Legacy migration requires empty service deployment state"
            )
        legacy_image = args.legacy_image_ref
        if args.dry_run:
            _report_dry_run_not_image_bound()
        if not args.dry_run:
            live_image = _snapshot_current_state(
                compose_file=compose_file,
                project_dir=project_dir,
                service=args.service,
                dry_run=False,
            )
            _require_live_image_binding(live_image, args.protected_image, dry_run=False)
            _require_verified_backup(
                args.backup_evidence,
                args.protected_image,
            )
            if live_image != legacy_image:
                raise DeployError(
                    "Running image does not match the explicitly accepted legacy digest"
                )
        _validate_snapshot_state(legacy_image)
        if legacy_image == args.image_ref:
            raise DeployError("Running image is already the requested OCI index")

        try:
            migrated = _deploy_once(
                compose_file=compose_file,
                project_dir=project_dir,
                override_file=override_file,
                service=args.service,
                image_ref=args.image_ref,
                health_url=args.health_url,
                readiness_url=args.readiness_url,
                dry_run=args.dry_run,
            )
        except DeployError as target_error:
            if not args.dry_run:
                print(
                    "Legacy migration failed; restoring the exact pre-migration digest"
                )
                try:
                    _deploy_once(
                        compose_file=compose_file,
                        project_dir=project_dir,
                        override_file=override_file,
                        service=args.service,
                        image_ref=legacy_image,
                        health_url=args.health_url,
                        readiness_url=args.readiness_url,
                        dry_run=False,
                    )
                except DeployError as restore_error:
                    raise DeployError(
                        f"Legacy migration target failed: {target_error}; "
                        f"legacy restore also failed: {restore_error}"
                    ) from restore_error
            raise

        if not args.dry_run:
            _update_service_state(
                state_file,
                service=args.service,
                current_image=migrated,
                previous_image=None,
            )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deploy or rollback digest-pinned production images."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=REPO_ROOT,
        help="Project directory used for relative compose and state resolution.",
    )
    parser.add_argument(
        "--compose-file",
        type=Path,
        default=Path("docker-compose.yml"),
        help="Compose file path (relative to --project-dir).",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path(STATE_DIR_NAME),
        help="Directory to store deployment state and lock files.",
    )
    parser.add_argument(
        "--service",
        default="app",
        help="Compose service name to operate.",
    )
    parser.add_argument(
        "--health-url",
        required=True,
        help="Reachable liveness endpoint.",
    )
    parser.add_argument(
        "--readiness-url",
        required=True,
        help="Independent database readiness endpoint.",
    )
    parser.add_argument(
        "--lock-timeout",
        type=int,
        default=120,
        help="Maximum seconds to wait for deployment lock.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run validation and planning without Docker mutations.",
    )
    parser.add_argument(
        "--backup-evidence",
        type=Path,
        help="Absolute owner-only restore-verified backup evidence JSON.",
    )
    parser.add_argument(
        "--protected-image",
        help="Current immutable image digest, or no-running-image for first install.",
    )
    parser.add_argument(
        "--migration-receipt",
        type=Path,
        help="Owner-only receipt bridging pre-migration evidence to the current DB.",
    )
    parser.add_argument(
        "--source-sha",
        help="Exact release source SHA bound by --migration-receipt.",
    )
    parser.add_argument(
        "--acceptance-runner",
        type=Path,
        help=(
            "Absolute owner-only executable which checks login and critical business "
            "gates for post-migration target and rollback phases."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    deploy_parser = subparsers.add_parser("deploy", help="Deploy immutable image ref.")
    deploy_parser.add_argument(
        "image_ref",
        help="Full digest reference (e.g. ghcr.io/org/app@sha256:...)",
    )
    deploy_parser.set_defaults(func=_deploy)

    rollback_parser = subparsers.add_parser(
        "rollback", help="Rollback immutable image ref."
    )
    rollback_parser.add_argument(
        "image_ref",
        nargs="?",
        help="Optional explicit immutable image ref for rollback.",
    )
    rollback_parser.set_defaults(func=_rollback)

    migrate_parser = subparsers.add_parser(
        "migrate-legacy",
        help="Replace one legacy digest baseline with a reviewed OCI index.",
    )
    migrate_parser.add_argument(
        "legacy_image_ref",
        help="Exact currently running legacy digest accepted for this migration only.",
    )
    migrate_parser.add_argument(
        "image_ref",
        help="Reviewed two-platform OCI index ref used as the new baseline.",
    )
    migrate_parser.set_defaults(func=_migrate_legacy)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    args.project_dir = args.project_dir.resolve()
    args.compose_file = args.compose_file
    args.state_dir = args.state_dir

    try:
        args.func(args)
    except DeployError as exc:
        raise SystemExit(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
