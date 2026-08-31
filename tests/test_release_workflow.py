"""Release workflow contracts for immutable image metadata convergence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import release_convergence


ROOT = Path(__file__).parents[1]
SOURCE_SHA = "e" * 40
DIGEST = "sha256:" + "a" * 64
REPOSITORY = "ghcr.io/ywyz/kindergartenmanager"
IMAGE_REF = f"{REPOSITORY}@{DIGEST}"
TAG = "v9.8.7"
MEDIA_TYPE = "application/vnd.oci.image.index.v1+json"
PLATFORMS = ["linux/amd64", "linux/arm64"]


def _workflow() -> dict[str, Any]:
    return yaml.safe_load(
        (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    )


def _descriptor() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "release_tag": TAG,
        "source_sha": SOURCE_SHA,
        "repository": REPOSITORY,
        "digest": DIGEST,
        "ref": IMAGE_REF,
        "media_type": MEDIA_TYPE,
        "platforms": PLATFORMS,
    }


def _release_body() -> str:
    return "\n".join(
        (TAG, SOURCE_SHA, REPOSITORY, DIGEST, IMAGE_REF, MEDIA_TYPE, *PLATFORMS)
    )


def test_release_workflow_builds_and_exports_immutable_oci_index() -> None:
    workflow = _workflow()
    build = workflow["jobs"]["build-docker"]
    outputs = build["outputs"]

    assert outputs == {
        "image_digest": "${{ steps.image_metadata.outputs.digest }}",
        "image_ref": "${{ steps.image_metadata.outputs.ref }}",
        "image_repository": "${{ steps.image_metadata.outputs.repository }}",
        "source_sha": "${{ github.sha }}",
        "image_media_type": "${{ steps.image_media.outputs.media_type }}",
    }

    steps = build["steps"]
    assert any(step.get("uses") == "docker/setup-qemu-action@v3" for step in steps)
    docker_build = next(step for step in steps if step.get("id") == "docker_build")
    assert docker_build["with"]["platforms"] == "linux/amd64,linux/arm64"
    assert docker_build["with"]["push"] is True

    repository_step = next(
        step for step in steps if step.get("id") == "image_repository"
    )
    assert "${owner,,}" in repository_step["run"]
    metadata_action = next(
        step for step in steps if step.get("uses") == "docker/metadata-action@v5"
    )
    assert (
        metadata_action["with"]["images"]
        == "${{ steps.image_repository.outputs.repository }}"
    )
    capture = next(step for step in steps if step.get("id") == "image_metadata")
    assert "${{ steps.image_repository.outputs.repository }}" in capture["run"]
    media = next(step for step in steps if step.get("id") == "image_media")
    assert "application/vnd.oci.image.index.v1+json" in media["run"]
    assert '("linux", "amd64")' in media["run"]
    assert '("linux", "arm64")' in media["run"]
    assert "missing required platforms" in media["run"]


def test_release_workflow_uploads_descriptor_as_artifact_and_release_asset() -> None:
    release_steps = _workflow()["jobs"]["create-release"]["steps"]
    materialize = next(
        step
        for step in release_steps
        if step.get("name") == "Materialize OCI image descriptor"
    )
    assert '"schema_version": 2' in materialize["run"]
    assert "${{ needs.build-docker.outputs.image_repository }}" in materialize["run"]
    assert '"platforms": ["linux/amd64", "linux/arm64"]' in materialize["run"]

    upload = next(
        step
        for step in release_steps
        if step.get("name") == "Upload docker-image descriptor"
    )
    assert upload["uses"] == "actions/upload-artifact@v4"
    assert upload["with"] == {
        "name": "docker-image",
        "path": "artifacts/docker-image/docker-image.json",
    }

    publish = next(
        step for step in release_steps if step.get("name") == "Create GitHub Release"
    )
    assert publish["with"]["files"] == "artifacts/**/*"
    assert publish["with"]["target_commitish"] == "${{ github.sha }}"
    body = publish["with"]["body"]
    for value in (
        "${{ github.ref_name }}",
        "${{ github.sha }}",
        "${{ needs.build-docker.outputs.image_digest }}",
        "${{ needs.build-docker.outputs.image_ref }}",
    ):
        assert value in body
    assert "deploy --service app" not in body
    assert body.index("--service app") < body.index("deploy ${{")


def test_release_workflow_runs_testable_post_release_convergence() -> None:
    verify = _workflow()["jobs"]["verify-release"]
    assert verify["needs"] == ["build-docker", "create-release"]
    steps = verify["steps"]
    assert any(step.get("uses") == "actions/checkout@v4" for step in steps)
    download = next(
        step for step in steps if step.get("name") == "Download docker-image descriptor"
    )
    assert download["uses"] == "actions/download-artifact@v4"
    assert download["with"]["name"] == "docker-image"

    convergence = next(
        step
        for step in steps
        if step.get("name")
        == "Verify release body and release artifacts match immutable refs"
    )
    assert "python scripts/release_convergence.py" in convergence["run"]
    for option in (
        "--repo",
        "--descriptor",
        "--tag",
        "--source-sha",
        "--repository",
        "--digest",
        "--ref",
        "--media-type",
        "--platform",
    ):
        assert option in convergence["run"]
    assert (
        convergence["env"]["EXPECTED_REPOSITORY"]
        == "${{ needs.build-docker.outputs.image_repository }}"
    )


def test_deployment_docs_keep_global_options_before_subcommands() -> None:
    for path in (
        ROOT / "README.md",
        ROOT / "docs/USER_MANUAL.md",
        ROOT / "docs/DEPLOYMENT.md",
        ROOT / ".github/workflows/release.yml",
    ):
        contents = path.read_text(encoding="utf-8")
        assert "deploy.py deploy --service" not in contents
        assert "deploy.py rollback --service" not in contents


def test_production_compose_commands_use_explicit_reachable_liveness_url() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    assert "ports" not in compose["services"]["app"]
    for path in (
        ROOT / "README.md",
        ROOT / "docs/USER_MANUAL.md",
        ROOT / "docs/DEPLOYMENT.md",
    ):
        contents = path.read_text(encoding="utf-8")
        assert "--health-url https://manager.ywyz.tech/api/v1/health" in contents


def test_release_convergence_accepts_exactly_matching_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor_path = tmp_path / "docker-image.json"
    descriptor_path.write_text(json.dumps(_descriptor()))
    release = {
        "tag_name": TAG,
        "target_commitish": SOURCE_SHA,
        "body": _release_body(),
        "assets": [
            {
                "name": "docker-image.json",
                "url": "https://api.github.com/assets/123",
            }
        ],
    }

    def fake_api(repo: str, path: str, token: str) -> dict[str, Any]:
        if path.startswith("git/ref/tags/"):
            return {"object": {"type": "commit", "sha": SOURCE_SHA}}
        if path.startswith("releases/tags/"):
            return release
        raise AssertionError(path)

    monkeypatch.setattr(release_convergence, "_api_json", fake_api)
    monkeypatch.setattr(
        release_convergence, "_asset_json", lambda url, token: _descriptor()
    )

    release_convergence.verify_release(
        repo="ywyz/kindergartenManager",
        token="synthetic-token",
        descriptor_path=descriptor_path,
        tag=TAG,
        source_sha=SOURCE_SHA,
        repository=REPOSITORY,
        digest=DIGEST,
        immutable_ref=IMAGE_REF,
        media_type=MEDIA_TYPE,
        platforms=PLATFORMS,
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("tag", "tag target"),
        ("asset", "Published Release asset"),
        ("body", "Release body"),
    ],
)
def test_release_convergence_fails_closed_on_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    message: str,
) -> None:
    descriptor_path = tmp_path / "docker-image.json"
    descriptor_path.write_text(json.dumps(_descriptor()))
    body = _release_body()
    if mutation == "body":
        body = TAG
    release = {
        "tag_name": TAG,
        "target_commitish": SOURCE_SHA,
        "body": body,
        "assets": [
            {
                "name": "docker-image.json",
                "url": "https://api.github.com/assets/123",
            }
        ],
    }

    def fake_api(repo: str, path: str, token: str) -> dict[str, Any]:
        if path.startswith("git/ref/tags/"):
            sha = "f" * 40 if mutation == "tag" else SOURCE_SHA
            return {"object": {"type": "commit", "sha": sha}}
        return release

    asset = _descriptor()
    if mutation == "asset":
        asset = {**asset, "digest": "sha256:" + "b" * 64}
    monkeypatch.setattr(release_convergence, "_api_json", fake_api)
    monkeypatch.setattr(release_convergence, "_asset_json", lambda url, token: asset)

    with pytest.raises(release_convergence.ConvergenceError, match=message):
        release_convergence.verify_release(
            repo="ywyz/kindergartenManager",
            token="synthetic-token",
            descriptor_path=descriptor_path,
            tag=TAG,
            source_sha=SOURCE_SHA,
            repository=REPOSITORY,
            digest=DIGEST,
            immutable_ref=IMAGE_REF,
            media_type=MEDIA_TYPE,
            platforms=PLATFORMS,
        )


def test_release_convergence_rejects_missing_platform() -> None:
    with pytest.raises(
        release_convergence.ConvergenceError, match="platforms are incomplete"
    ):
        release_convergence._validate_expected_values(
            tag=TAG,
            source_sha=SOURCE_SHA,
            repository=REPOSITORY,
            digest=DIGEST,
            immutable_ref=IMAGE_REF,
            media_type=MEDIA_TYPE,
            platforms=["linux/amd64"],
        )
