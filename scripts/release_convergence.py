#!/usr/bin/env python3
"""Fail-closed verification for immutable Docker release metadata."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
DESCRIPTOR_KEYS = {
    "schema_version",
    "release_tag",
    "source_sha",
    "repository",
    "digest",
    "ref",
    "media_type",
    "platforms",
}
OCI_INDEX_MEDIA_TYPE = "application/vnd.oci.image.index.v1+json"
REQUIRED_PLATFORMS = ("linux/amd64", "linux/arm64")


class ConvergenceError(RuntimeError):
    """Raised when release facts do not converge."""


def _request_json(url: str, token: str, *, accept: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": accept,
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise ConvergenceError("GitHub API request failed") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConvergenceError("GitHub API returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ConvergenceError("GitHub API returned an unexpected payload")
    return payload


def _api_json(repo: str, path: str, token: str) -> dict[str, Any]:
    return _request_json(
        f"https://api.github.com/repos/{repo}/{path}",
        token,
        accept="application/vnd.github+json",
    )


def _asset_json(url: str, token: str) -> dict[str, Any]:
    return _request_json(url, token, accept="application/octet-stream")


def _validate_expected_values(
    *,
    tag: str,
    source_sha: str,
    repository: str,
    digest: str,
    immutable_ref: str,
    media_type: str,
    platforms: list[str],
) -> None:
    if not tag or any(character.isspace() for character in tag):
        raise ConvergenceError("Expected release tag is invalid")
    if not SHA_RE.fullmatch(source_sha):
        raise ConvergenceError("Expected source SHA is invalid")
    if not DIGEST_RE.fullmatch(digest):
        raise ConvergenceError("Expected image digest is invalid")
    if not repository or repository.lower() != repository:
        raise ConvergenceError("Expected image repository must be lowercase")
    if immutable_ref != f"{repository}@{digest}":
        raise ConvergenceError("Expected immutable image ref is inconsistent")
    if media_type != OCI_INDEX_MEDIA_TYPE:
        raise ConvergenceError("Expected media type is not an OCI image index")
    if tuple(platforms) != REQUIRED_PLATFORMS:
        raise ConvergenceError("Expected release platforms are incomplete or unordered")


def validate_descriptor(
    descriptor: dict[str, Any],
    *,
    tag: str,
    source_sha: str,
    repository: str,
    digest: str,
    immutable_ref: str,
    media_type: str,
    platforms: list[str],
) -> None:
    """Validate the descriptor schema and every expected release fact."""
    expected = {
        "schema_version": 2,
        "release_tag": tag,
        "source_sha": source_sha,
        "repository": repository,
        "digest": digest,
        "ref": immutable_ref,
        "media_type": media_type,
        "platforms": platforms,
    }
    if set(descriptor) != DESCRIPTOR_KEYS:
        raise ConvergenceError("Descriptor fields do not match schema version 2")
    if descriptor != expected:
        raise ConvergenceError("Descriptor does not match expected release facts")


def _resolve_tag_target(repo: str, tag: str, token: str) -> str:
    quoted_tag = urllib.parse.quote(tag, safe="")
    tagged_object = _api_json(repo, f"git/ref/tags/{quoted_tag}", token).get(
        "object", {}
    )
    for _ in range(8):
        if not isinstance(tagged_object, dict):
            break
        object_type = tagged_object.get("type")
        object_sha = tagged_object.get("sha")
        if object_type == "commit" and isinstance(object_sha, str):
            return object_sha
        if object_type != "tag" or not isinstance(object_sha, str):
            break
        tagged_object = _api_json(repo, f"git/tags/{object_sha}", token).get(
            "object", {}
        )
    raise ConvergenceError("Release tag does not resolve to a commit")


def verify_release(
    *,
    repo: str,
    token: str,
    descriptor_path: Path,
    tag: str,
    source_sha: str,
    repository: str,
    digest: str,
    immutable_ref: str,
    media_type: str,
    platforms: list[str],
) -> None:
    """Verify workflow artifact, tag, release body, and Release asset agree."""
    _validate_expected_values(
        tag=tag,
        source_sha=source_sha,
        repository=repository,
        digest=digest,
        immutable_ref=immutable_ref,
        media_type=media_type,
        platforms=platforms,
    )
    try:
        workflow_descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConvergenceError("Workflow descriptor is missing or invalid") from exc
    if not isinstance(workflow_descriptor, dict):
        raise ConvergenceError("Workflow descriptor must be a JSON object")
    validate_descriptor(
        workflow_descriptor,
        tag=tag,
        source_sha=source_sha,
        repository=repository,
        digest=digest,
        immutable_ref=immutable_ref,
        media_type=media_type,
        platforms=platforms,
    )

    tag_target = _resolve_tag_target(repo, tag, token)
    if tag_target != source_sha:
        raise ConvergenceError("Release tag target does not match source SHA")

    quoted_tag = urllib.parse.quote(tag, safe="")
    release = _api_json(repo, f"releases/tags/{quoted_tag}", token)
    if release.get("tag_name") != tag:
        raise ConvergenceError("Release tag name does not match workflow tag")

    target_commitish = release.get("target_commitish")
    if target_commitish != source_sha:
        raise ConvergenceError("Release target_commitish does not match source SHA")

    body = release.get("body")
    if not isinstance(body, str):
        raise ConvergenceError("Release body is missing")
    for expected_token in (
        tag,
        source_sha,
        repository,
        digest,
        immutable_ref,
        media_type,
        *platforms,
    ):
        if expected_token not in body:
            raise ConvergenceError("Release body is missing immutable release facts")

    assets = release.get("assets")
    if not isinstance(assets, list):
        raise ConvergenceError("Release assets are missing")
    descriptor_assets = [
        asset
        for asset in assets
        if isinstance(asset, dict) and asset.get("name") == "docker-image.json"
    ]
    if len(descriptor_assets) != 1:
        raise ConvergenceError(
            "Release must contain exactly one docker-image.json asset"
        )
    asset_url = descriptor_assets[0].get("url")
    if not isinstance(asset_url, str) or not asset_url.startswith(
        "https://api.github.com/"
    ):
        raise ConvergenceError("Release descriptor asset URL is invalid")
    release_descriptor = _asset_json(asset_url, token)
    try:
        validate_descriptor(
            release_descriptor,
            tag=tag,
            source_sha=source_sha,
            repository=repository,
            digest=digest,
            immutable_ref=immutable_ref,
            media_type=media_type,
            platforms=platforms,
        )
    except ConvergenceError as exc:
        raise ConvergenceError(
            "Published Release asset does not match expected release facts"
        ) from exc
    if release_descriptor != workflow_descriptor:
        raise ConvergenceError(
            "Workflow descriptor and published Release asset do not match"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify immutable Docker release metadata convergence."
    )
    parser.add_argument("--repo", required=True)
    parser.add_argument("--descriptor", required=True, type=Path)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--ref", required=True, dest="immutable_ref")
    parser.add_argument("--media-type", required=True)
    parser.add_argument("--platform", required=True, action="append", dest="platforms")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    try:
        verify_release(token=token, **vars(args))
    except ConvergenceError as exc:
        raise SystemExit(f"Release convergence failed: {exc}") from exc
    print("Release metadata convergence checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
