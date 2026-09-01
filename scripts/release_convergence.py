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
DOCKER_FACTS_SECTION_TITLE = "### Docker 不可变引用说明"
DOCKER_FACTS_HEADER_TO_KEY = {
    "release tag": "release_tag",
    "source sha": "source_sha",
    "repository": "repository",
    "oci index digest": "digest",
    "不可变引用": "ref",
    "media type": "media_type",
    "platforms": "platforms",
}
EXPECTED_DOCKER_FACTS_KEYS = set(DOCKER_FACTS_HEADER_TO_KEY.values())


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


def _patch_api_json(
    repo: str, path: str, token: str, payload: dict[str, Any]
) -> dict[str, Any]:
    api_request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/{path}",
        data=json.dumps(payload).encode("utf-8"),
        method="PATCH",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(api_request, timeout=30) as response:
            result = json.load(response)
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as exc:
        raise ConvergenceError("GitHub Release publish request failed") from exc
    if not isinstance(result, dict):
        raise ConvergenceError("GitHub Release publish returned an invalid payload")
    return result


def _asset_json(url: str, token: str) -> dict[str, Any]:
    return _request_json(url, token, accept="application/octet-stream")


def validate_expected_values(
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


def _normalize_field_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().strip("`").casefold()


def _parse_release_body_facts(body: str) -> dict[str, str | list[str]]:
    heading_re = re.compile(r"^ {0,3}###\s+Docker 不可变引用说明\s*$")
    heading_line_re = re.compile(r"^ {0,3}#{1,6}\s+.+$")
    separator_re = re.compile(r"^ {0,3}---\s*$")
    in_fence = False
    fence_char: str | None = None
    fence_length = 0
    section_starts: list[int] = []

    def open_fence_marker(line: str) -> tuple[str, int] | None:
        # Supports fenced code blocks with >=3 backticks or tildes.
        leading = len(line) - len(line.lstrip(" "))
        if leading > 3:
            return None
        stripped = line[leading:]
        if len(stripped) < 3:
            return None
        marker_char = stripped[0]
        if marker_char not in {"`", "~"}:
            return None

        index = 0
        while index < len(stripped) and stripped[index] == marker_char:
            index += 1
        if index < 3:
            return None
        return marker_char, index

    def is_closing_fence(line: str, marker_char: str, marker_length: int) -> bool:
        leading = len(line) - len(line.lstrip(" "))
        if leading > 3:
            return False
        stripped = line.lstrip(" ")
        if not stripped.startswith(marker_char):
            return False
        if stripped[0:1] != marker_char:
            return False
        index = 0
        while index < len(stripped) and stripped[index] == marker_char:
            index += 1
        if index < marker_length:
            return False
        return stripped[index:].strip() == ""

    lines = body.splitlines()

    for index, line in enumerate(lines):
        if not in_fence:
            opener = open_fence_marker(line)
            if opener is not None:
                in_fence = True
                fence_char, fence_length = opener
                continue
        else:
            if fence_char is not None and is_closing_fence(
                line, fence_char, fence_length
            ):
                in_fence = False
                fence_char = None
                fence_length = 0
                continue
        if in_fence:
            if heading_re.match(line):
                raise ConvergenceError(
                    "Release body Docker section title is inside fenced code"
                )
            continue
        if heading_re.match(line):
            section_starts.append(index)
        elif heading_line_re.match(line) and DOCKER_FACTS_SECTION_TITLE in line:
            raise ConvergenceError(
                "Release body has malformed Docker facts section heading"
            )

    if len(section_starts) == 0:
        raise ConvergenceError("Release body is missing the Docker facts section")
    if len(section_starts) > 1:
        raise ConvergenceError(
            "Release body has duplicate Docker facts section headings"
        )

    start = section_starts[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if heading_line_re.match(line) or separator_re.match(line):
            end = index
            break

    section = "\n".join(lines[start + 1 : end])
    row_re = re.compile(r"^ {0,3}\|\s*(?P<field>.*?)\s*\|\s*(?P<value>.*?)\s*\|\s*$")
    header_re = re.compile(r"^ {0,3}\|\s*字段\s*\|\s*值\s*\|\s*$", re.IGNORECASE)
    separator_row_re = re.compile(r"^ {0,3}\|\s*:?-{3,}:?\s*\|\s*:?-{3,}:?\s*\|\s*$")
    parsed: dict[str, str | list[str]] = {}

    section_lines = [line for line in section.splitlines() if line.strip()]
    if len(section_lines) == 0:
        raise ConvergenceError("Release body Docker facts section is incomplete")
    if len(section_lines) == 1:
        raise ConvergenceError("Release body Docker facts section header is missing")

    if not header_re.match(section_lines[0]):
        raise ConvergenceError("Release body Docker facts section header is missing")
    if len(section_lines) == 2 or not separator_row_re.match(section_lines[1]):
        raise ConvergenceError("Release body Docker facts section separator is missing")

    for line in section_lines[2:]:
        match = row_re.match(line)
        if not match:
            raise ConvergenceError(
                "Release body Docker facts section contains non-table content"
            )

        normalized_field = _normalize_field_name(match.group("field"))
        value = match.group("value").strip()

        if normalized_field in {"字段", "field"}:
            continue
        if normalized_field not in DOCKER_FACTS_HEADER_TO_KEY:
            raise ConvergenceError(
                f"Release body contains an unexpected Docker fact field: {match.group('field').strip()}"
            )

        canonical_key = DOCKER_FACTS_HEADER_TO_KEY[normalized_field]
        if canonical_key in parsed:
            raise ConvergenceError(
                f"Release body has duplicate Docker fact field: {match.group('field').strip()}"
            )

        cleaned = value.strip().strip("`")
        if canonical_key == "platforms":
            values = [
                entry.strip(" `") for entry in cleaned.split(",") if entry.strip()
            ]
            if not values:
                raise ConvergenceError("Release body Platforms value is invalid")
            parsed[canonical_key] = values
        else:
            parsed[canonical_key] = cleaned

    if set(parsed) != EXPECTED_DOCKER_FACTS_KEYS:
        missing = sorted(EXPECTED_DOCKER_FACTS_KEYS - set(parsed))
        raise ConvergenceError(
            "Release body Docker facts are malformed or incomplete: "
            f"missing={','.join(missing)}"
        )
    return parsed


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
    release_id: str | None = None,
    expected_draft: bool | None = None,
) -> None:
    """Verify workflow artifact, tag, release body, and Release asset agree."""
    validate_expected_values(
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
    if release_id is not None:
        if not release_id.isdecimal():
            raise ConvergenceError("Release id is invalid")
        release = _api_json(repo, f"releases/{release_id}", token)
        required_draft = True if expected_draft is None else expected_draft
        if release.get("draft") is not required_draft:
            expected = "draft" if required_draft else "published"
            raise ConvergenceError(f"Release must be {expected} during convergence")
    else:
        release = _api_json(repo, f"releases/tags/{quoted_tag}", token)
    if release.get("tag_name") != tag:
        raise ConvergenceError("Release tag name does not match workflow tag")

    target_commitish = release.get("target_commitish")
    if target_commitish != source_sha:
        raise ConvergenceError("Release target_commitish does not match source SHA")

    body = release.get("body")
    if not isinstance(body, str):
        raise ConvergenceError("Release body is missing")
    release_facts = _parse_release_body_facts(body)
    if release_facts.get("release_tag") != tag:
        raise ConvergenceError("Release body does not match expected release tag")
    if release_facts.get("source_sha") != source_sha:
        raise ConvergenceError("Release body does not match expected source SHA")
    if release_facts.get("repository") != repository:
        raise ConvergenceError("Release body does not match expected repository")
    if release_facts.get("digest") != digest:
        raise ConvergenceError("Release body does not match expected image digest")
    if release_facts.get("ref") != immutable_ref:
        raise ConvergenceError(
            "Release body does not match expected immutable image ref"
        )
    if release_facts.get("media_type") != media_type:
        raise ConvergenceError("Release body does not match expected image media type")
    if (
        not isinstance(release_facts.get("platforms"), list)
        or release_facts.get("platforms") != platforms
    ):
        raise ConvergenceError(
            "Release body does not match expected immutable platforms"
        )

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


def publish_verified_release(**facts: Any) -> None:
    """Publish one converged draft, then re-read the same release id."""
    release_id = facts.get("release_id")
    if not isinstance(release_id, str) or not release_id.isdecimal():
        raise ConvergenceError("Release id is required for controlled publish")
    verify_release(**facts, expected_draft=True)
    try:
        published = _patch_api_json(
            facts["repo"],
            f"releases/{release_id}",
            facts["token"],
            {"draft": False},
        )
        if (
            published.get("id") != int(release_id)
            or published.get("draft") is not False
        ):
            raise ConvergenceError("GitHub Release publish acknowledgement is invalid")
        verify_release(**facts, expected_draft=False)
    except Exception as publish_error:
        try:
            restored = _patch_api_json(
                facts["repo"],
                f"releases/{release_id}",
                facts["token"],
                {"draft": True},
            )
            if (
                restored.get("id") != int(release_id)
                or restored.get("draft") is not True
            ):
                raise ConvergenceError("Draft restore acknowledgement is invalid")
            verify_release(**facts, expected_draft=True)
        except Exception as restore_error:
            raise ConvergenceError("PUBLISH_RECONCILE_REQUIRED") from restore_error
        raise ConvergenceError(
            "Release publish failed and was restored to draft"
        ) from (publish_error)


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
    parser.add_argument("--release-id")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish the converged draft and re-read the exact release id.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    try:
        values = vars(args)
        publish = values.pop("publish")
        if publish:
            publish_verified_release(token=token, **values)
        else:
            verify_release(token=token, **values)
    except ConvergenceError as exc:
        raise SystemExit(f"Release convergence failed: {exc}") from exc
    print("Release metadata convergence checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
