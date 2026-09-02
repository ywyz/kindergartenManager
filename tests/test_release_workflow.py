"""Release workflow contracts for immutable image metadata convergence."""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import release_convergence


def test_release_api_read_retries_transient_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    sleeps: list[int] = []

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, *_args: object) -> bytes:
            return b'{"id": 42}'

    def open_request(*_args: object, **_kwargs: object) -> Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise urllib.error.URLError("synthetic transient failure")
        return Response()

    monkeypatch.setattr(release_convergence.urllib.request, "urlopen", open_request)
    monkeypatch.setattr(release_convergence.time, "sleep", sleeps.append)

    assert release_convergence._api_json("owner/repo", "releases/42", "token") == {
        "id": 42
    }
    assert attempts == 2
    assert sleeps == [1]


def test_release_api_read_does_not_retry_non_transient_http_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    def open_request(*_args: object, **_kwargs: object) -> None:
        nonlocal attempts
        attempts += 1
        raise urllib.error.HTTPError("url", 404, "missing", {}, None)

    monkeypatch.setattr(release_convergence.urllib.request, "urlopen", open_request)

    with pytest.raises(release_convergence.ConvergenceError, match="request failed"):
        release_convergence._api_json("owner/repo", "releases/42", "token")
    assert attempts == 1


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


def test_release_convergence_cli_maps_descriptor_to_public_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor_path = tmp_path / "docker-image.json"
    descriptor_path.write_text(json.dumps(_descriptor()), encoding="utf-8")
    captured: dict[str, Any] = {}

    def fake_verify_release(**values: Any) -> None:
        captured.update(values)

    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(release_convergence, "verify_release", fake_verify_release)
    result = release_convergence.main(
        [
            "--repo",
            "ywyz/kindergartenManager",
            "--release-id",
            "123",
            "--descriptor",
            str(descriptor_path),
            "--tag",
            TAG,
            "--source-sha",
            SOURCE_SHA,
            "--repository",
            REPOSITORY,
            "--digest",
            DIGEST,
            "--ref",
            IMAGE_REF,
            "--media-type",
            MEDIA_TYPE,
            "--platform",
            PLATFORMS[0],
            "--platform",
            PLATFORMS[1],
        ]
    )

    assert result == 0
    assert captured["descriptor_path"] == descriptor_path
    assert "descriptor" not in captured


def _release_body() -> str:
    return f"""### Docker 不可变引用说明

| 字段 | 值 |
|---|---|
| Release tag | `{TAG}` |
| Source SHA | `{SOURCE_SHA}` |
| Repository | `{REPOSITORY}` |
| OCI index digest | `{DIGEST}` |
| 不可变引用 | `{IMAGE_REF}` |
| Media type | `{MEDIA_TYPE}` |
| Platforms | `linux/amd64`, `linux/arm64` |

---"""


def _assert_release_rejects_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    body: str,
    message: str,
) -> None:
    descriptor_path = tmp_path / "docker-image.json"
    descriptor_path.write_text(json.dumps(_descriptor()))
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
            return {"object": {"type": "commit", "sha": SOURCE_SHA}}
        return release

    monkeypatch.setattr(release_convergence, "_api_json", fake_api)
    monkeypatch.setattr(
        release_convergence, "_asset_json", lambda url, token: _descriptor()
    )

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
    assert "scripts/deploy.py --service app" not in body
    assert body.index("--service app") < body.index("deploy ${{")
    assert "--acceptance-runner /secure/path/r5-acceptance-runner" in body


def test_release_workflow_runs_testable_post_release_convergence() -> None:
    verify = _workflow()["jobs"]["verify-release"]
    assert verify["needs"] == ["build-docker", "create-release"]
    assert verify["permissions"]["contents"] == "write"
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


def test_release_remains_draft_until_separate_production_closure() -> None:
    workflow = _workflow()
    create = workflow["jobs"]["create-release"]
    release = next(
        step for step in create["steps"] if step.get("name") == "Create GitHub Release"
    )
    assert release["id"] == "release"
    assert release["with"]["draft"] is True
    assert create["outputs"]["release_id"] == "${{ steps.release.outputs.id }}"

    verify = workflow["jobs"]["verify-release"]
    convergence = next(
        step
        for step in verify["steps"]
        if step.get("name")
        == "Verify release body and release artifacts match immutable refs"
    )
    assert "--release-id" in convergence["run"]

    assert "publish-release" not in workflow["jobs"]


def test_controlled_publish_re_reads_same_release_after_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool | None]] = []

    def verify(**kwargs: Any) -> None:
        calls.append((kwargs["release_id"], kwargs["expected_draft"]))

    monkeypatch.setattr(release_convergence, "verify_release", verify)
    monkeypatch.setattr(
        release_convergence,
        "_patch_api_json",
        lambda repo, path, token, payload: {"id": 123, "draft": False},
    )
    release_convergence.publish_verified_release(
        repo="ywyz/kindergartenManager",
        token="synthetic-token",
        descriptor_path=Path("docker-image.json"),
        tag=TAG,
        source_sha=SOURCE_SHA,
        repository=REPOSITORY,
        digest=DIGEST,
        immutable_ref=IMAGE_REF,
        media_type=MEDIA_TYPE,
        platforms=PLATFORMS,
        release_id="123",
    )

    assert calls == [("123", True), ("123", False)]


def test_controlled_publish_failure_restores_and_reverifies_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool | None]] = []
    mutations: list[bool] = []

    def verify(**kwargs: Any) -> None:
        calls.append((kwargs["release_id"], kwargs["expected_draft"]))
        if kwargs["expected_draft"] is False:
            raise release_convergence.ConvergenceError("post-publish mismatch")

    def patch(
        repo: str, path: str, token: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        mutations.append(payload["draft"])
        return {"id": 123, "draft": payload["draft"]}

    monkeypatch.setattr(release_convergence, "verify_release", verify)
    monkeypatch.setattr(release_convergence, "_patch_api_json", patch)
    with pytest.raises(release_convergence.ConvergenceError, match="restored to draft"):
        release_convergence.publish_verified_release(
            repo="ywyz/kindergartenManager",
            token="synthetic-token",
            descriptor_path=Path("docker-image.json"),
            tag=TAG,
            source_sha=SOURCE_SHA,
            repository=REPOSITORY,
            digest=DIGEST,
            immutable_ref=IMAGE_REF,
            media_type=MEDIA_TYPE,
            platforms=PLATFORMS,
            release_id="123",
        )

    assert mutations == [False, True]
    assert calls == [("123", True), ("123", False), ("123", True)]


def test_release_body_repository_is_an_explicit_tuple_member() -> None:
    facts = release_convergence._parse_release_body_facts(_release_body())

    assert facts["repository"] == REPOSITORY


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


def test_release_workflow_keeps_strict_docker_facts_section_and_direct_api() -> None:
    workflow_path = ROOT / ".github/workflows/release.yml"
    workflow = workflow_path.read_text(encoding="utf-8")
    platforms = "| Platforms | `linux/amd64`, `linux/arm64` |"
    separator = "\n            ---"
    explanation = "`docker-image.json` 已随 release 资产发布"
    assert (
        workflow.index(platforms)
        < workflow.index(separator)
        < workflow.index(explanation)
    )
    assert (
        "unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy"
        in workflow
    )
    parsed_workflow = yaml.safe_load(workflow)
    release_step = next(
        step
        for step in parsed_workflow["jobs"]["create-release"]["steps"]
        if "body" in step.get("with", {})
    )
    parsed_facts = release_convergence._parse_release_body_facts(
        release_step["with"]["body"]
    )
    assert set(parsed_facts) == release_convergence.EXPECTED_DOCKER_FACTS_KEYS


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
        ("body", "Release body does not match expected release tag"),
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
        body = body.replace(
            "| Release tag | `v9.8.7` |",
            "| Release tag | `wrong` |",
        )
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


def test_release_convergence_rejects_duplicate_docker_fact_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor_path = tmp_path / "docker-image.json"
    descriptor_path.write_text(json.dumps(_descriptor()))
    body = _release_body().replace(
        f"| Source SHA | `{SOURCE_SHA}` |",
        f"| Source SHA | `{SOURCE_SHA}` |\n| Source SHA | `{SOURCE_SHA}` |",
    )
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
            return {"object": {"type": "commit", "sha": SOURCE_SHA}}
        return release

    monkeypatch.setattr(release_convergence, "_api_json", fake_api)
    monkeypatch.setattr(
        release_convergence, "_asset_json", lambda url, token: _descriptor()
    )

    with pytest.raises(
        release_convergence.ConvergenceError, match="duplicate Docker fact field"
    ):
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


def test_release_convergence_rejects_duplicate_docker_facts_section_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = f"""{_release_body()}

### Docker 不可变引用说明

| 字段 | 值 |
|---|---|
| Release tag | `{TAG}` |
| Source SHA | `{SOURCE_SHA}` |
| OCI index digest | `{DIGEST}` |
| 不可变引用 | `{IMAGE_REF}` |
| Media type | `{MEDIA_TYPE}` |
| Platforms | `linux/amd64`, `linux/arm64` |
"""
    _assert_release_rejects_body(
        tmp_path,
        monkeypatch,
        body=body,
        message="duplicate Docker facts section headings",
    )


def test_release_convergence_rejects_missing_docker_facts_table_separator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _release_body().replace("|---|---|", "")
    _assert_release_rejects_body(
        tmp_path,
        monkeypatch,
        body=body,
        message="separator is missing",
    )


def test_release_convergence_rejects_inline_docker_facts_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _release_body().replace(
        "### Docker 不可变引用说明",
        "### Docker 不可变引用说明 (inline)",
    )
    _assert_release_rejects_body(
        tmp_path,
        monkeypatch,
        body=body,
        message="malformed Docker facts section heading",
    )


def test_release_convergence_rejects_fenced_code_docker_facts_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = "```bash\n### Docker 不可变引用说明\n```\n\n" + _release_body()
    _assert_release_rejects_body(
        tmp_path,
        monkeypatch,
        body=body,
        message="inside fenced code",
    )


def test_release_convergence_rejects_tilde_fenced_code_docker_facts_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = "~~~bash\n### Docker 不可变引用说明\n~~~\n\n" + _release_body()
    _assert_release_rejects_body(
        tmp_path,
        monkeypatch,
        body=body,
        message="inside fenced code",
    )


def test_release_convergence_rejects_four_space_indented_docker_facts_heading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _release_body().replace(
        "### Docker 不可变引用说明",
        "    ### Docker 不可变引用说明",
    )
    _assert_release_rejects_body(
        tmp_path,
        monkeypatch,
        body=body,
        message="missing the Docker facts section",
    )


def test_release_convergence_rejects_tab_or_mixed_indent_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _release_body().replace(
        f"| Release tag | `{TAG}` |",
        f" \t| Release tag | `{TAG}` |",
    )
    _assert_release_rejects_body(
        tmp_path,
        monkeypatch,
        body=body,
        message="non-table content",
    )


def test_release_convergence_rejects_long_fence_open_marker_mismatch_closing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = "````bash\n### Docker 不可变引用说明\n```\n\n" + _release_body()
    _assert_release_rejects_body(
        tmp_path,
        monkeypatch,
        body=body,
        message="inside fenced code",
    )


def test_release_convergence_rejects_conflicting_docker_fact_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    descriptor_path = tmp_path / "docker-image.json"
    descriptor_path.write_text(json.dumps(_descriptor()))
    body = _release_body().replace(
        f"| Source SHA | `{SOURCE_SHA}` |",
        "| Source SHA | `{}` |\n| Source SHA | `{}` |".format(SOURCE_SHA, "f" * 40),
    )
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
            return {"object": {"type": "commit", "sha": SOURCE_SHA}}
        return release

    monkeypatch.setattr(release_convergence, "_api_json", fake_api)
    monkeypatch.setattr(
        release_convergence, "_asset_json", lambda url, token: _descriptor()
    )

    with pytest.raises(
        release_convergence.ConvergenceError, match="duplicate Docker fact field"
    ):
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
        release_convergence.validate_expected_values(
            tag=TAG,
            source_sha=SOURCE_SHA,
            repository=REPOSITORY,
            digest=DIGEST,
            immutable_ref=IMAGE_REF,
            media_type=MEDIA_TYPE,
            platforms=["linux/amd64"],
        )
