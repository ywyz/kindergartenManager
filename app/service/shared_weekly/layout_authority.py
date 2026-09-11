"""Operator-configured v3 qualification catalog and serialized active bindings.

This authority is intentionally not exposed as a teacher/UI API. The catalog
contains independently reviewed, content-addressed native-client evidence.
Local synthetic evidence is accepted only by an explicitly isolated authority;
its binding cannot be used by a production authority.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from app.service.shared_weekly.layout_contracts import PROFILE, LayoutBinding


class LayoutAuthorityRejected(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _reject():
    raise LayoutAuthorityRejected("qualification_invalid")


def _hash(value):
    if (
        type(value) is not str
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        _reject()


class LayoutAuthority:
    """One authority instance owns all activation and delivery linearization.

    Catalog entries are manifest path + expected manifest digest, installed by
    the application operator after independent review. A teacher cannot submit
    an arbitrary pass flag, path, manifest, or renderer/client observation.
    """

    def __init__(
        self,
        catalog: dict[str, tuple[Path, str]] | None = None,
        *,
        local_only: bool = False,
    ):
        self._catalog = dict(catalog or {})
        self.local_only = local_only
        self._lock = asyncio.Lock()
        self._active: dict[int, tuple[str, LayoutBinding]] = {}
        self._serial = 0

    async def _released_check(self, evidence, tenant_id):
        # The current deployed released port is immutable and has no activation
        # mutation API. Re-read its actual release binding, retaining old contract
        # identity solely as a dependency of the new independent qualification.
        from app.integration.word_export.released_weekly_monthly_word_port import (
            build_released_weekly_monthly_word_port,
        )
        from app.service.template_center.contracts import DocumentType

        try:
            current = await build_released_weekly_monthly_word_port().resolve_active(
                tenant_id, DocumentType.WEEKLY_ACTIVITY_PLAN
            )
        except (ValueError, RuntimeError, OSError):
            raise LayoutAuthorityRejected("template_changed") from None
        dependency = {
            "template_version_id": str(current.template_version_id),
            "version": current.version,
            "content_sha256": current.content_sha256,
            "contract_id": current.contract_id,
            "contract_version": current.contract_version,
        }
        if dependency != evidence["released_binding"]:
            raise LayoutAuthorityRejected("template_changed")
        return sha256(
            json.dumps(dependency, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def _read(self, qualification_id: str):
        entry = self._catalog.get(qualification_id)
        if entry is None:
            raise LayoutAuthorityRejected("qualification_required")
        manifest_path, expected = entry
        try:
            raw = manifest_path.read_bytes()
            if len(raw) > 65536 or sha256(raw).hexdigest() != expected:
                _reject()
            data = json.loads(raw)
            if (
                type(data) is not dict
                or set(data)
                != {
                    "schema",
                    "profile",
                    "template_sha256",
                    "renderer",
                    "client",
                    "role",
                    "fixtures",
                    "released_binding",
                }
                or data["schema"] != "weekly-layout-qualification.v1"
                or data["profile"] != PROFILE
            ):
                _reject()
            _hash(data["template_sha256"])
            dependency = data["released_binding"]
            if type(dependency) is not dict or set(dependency) != {
                "template_version_id",
                "version",
                "content_sha256",
                "contract_id",
                "contract_version",
            }:
                _reject()
            if (
                str(UUID(dependency["template_version_id"]))
                != dependency["template_version_id"]
                or dependency["content_sha256"] != data["template_sha256"]
                or type(dependency["contract_id"]) is not str
                or not dependency["contract_id"]
                or any(
                    type(dependency[key]) is not int or dependency[key] < 1
                    for key in ("version", "contract_version")
                )
            ):
                _reject()

            if data["role"] != (
                "local-synthetic" if self.local_only else "word-native"
            ):
                _reject()
            for field in ("renderer", "client"):
                if (
                    type(data[field]) is not dict
                    or set(data[field]) != {"product", "version"}
                    or any(
                        type(v) is not str or not v.strip()
                        for v in data[field].values()
                    )
                ):
                    _reject()
            if not self.local_only and not data["client"]["product"].startswith(
                "Microsoft Word"
            ):
                _reject()
            fixtures = data["fixtures"]
            if (
                type(fixtures) is not list
                or len(fixtures) != 2
                or {f.get("columns") for f in fixtures} != {5, 6}
            ):
                _reject()
            for fixture in fixtures:
                if set(fixture) != {
                    "columns",
                    "body_sha256",
                    "artifacts",
                    "observation",
                }:
                    _reject()
                _hash(fixture["body_sha256"])
                artifacts = fixture["artifacts"]
                if type(artifacts) is not dict or set(artifacts) != {
                    "docx",
                    "pdf",
                    "page-1.png",
                    "native-report.json",
                }:
                    _reject()
                verified = {}
                for kind, artifact in artifacts.items():
                    if type(artifact) is not dict or set(artifact) != {
                        "file",
                        "sha256",
                    }:
                        _reject()
                    name = artifact["file"]
                    if type(name) is not str or Path(name).name != name:
                        _reject()
                    _hash(artifact["sha256"])
                    path = manifest_path.parent / name
                    if path.is_symlink():
                        _reject()
                    content = path.read_bytes()
                    if not content or sha256(content).hexdigest() != artifact["sha256"]:
                        _reject()
                    verified[kind] = content
                observation = json.loads(verified["native-report.json"])
                required = {
                    "schema": "weekly-layout-native-observation.v1",
                    "role": data["role"],
                    "client": data["client"],
                    "renderer": data["renderer"],
                    "columns": fixture["columns"],
                    "body_sha256": fixture["body_sha256"],
                    "template_sha256": data["template_sha256"],
                    "profile": PROFILE,
                    "pages": 1,
                    "page_observations": ["all_text_visible_no_clipping_no_overflow"],
                    "font": "SimSun",
                    "font_pt": 12,
                    "line_pt": 20,
                    "fixed_counts": [2, 1, 3, 1, 3, 3, 3, 3, 3, 1],
                    "docx_sha256": artifacts["docx"]["sha256"],
                    "pdf_sha256": artifacts["pdf"]["sha256"],
                    "png_sha256": artifacts["page-1.png"]["sha256"],
                }
                if (
                    observation != required
                    or fixture["observation"]
                    != artifacts["native-report.json"]["sha256"]
                ):
                    _reject()
            return data
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            _reject()

    async def activate(
        self, tenant_id: int, qualification_id: str, *, expected: LayoutBinding | None
    ):
        async with self._lock:
            current = self._active.get(tenant_id)
            if (current[1] if current else None) != expected:
                raise LayoutAuthorityRejected("template_changed")
            evidence = self._read(qualification_id)
            dependency_hash = await self._released_check(evidence, tenant_id)
            self._serial += 1
            prefix = "local-synthetic" if self.local_only else "qualified"
            binding = LayoutBinding(
                tenant_id,
                evidence["template_sha256"],
                f"{prefix}:{qualification_id}:{self._serial}",
                released_dependency=dependency_hash,
            )
            self._active[tenant_id] = (qualification_id, binding)
            return binding

    async def deactivate(self, binding: LayoutBinding):
        async with self._lock:
            await self._check(binding)
            del self._active[binding.tenant_id]

    async def _check(self, binding):
        entry = self._active.get(binding.tenant_id)
        if entry is None or entry[1] != binding:
            raise LayoutAuthorityRejected("template_changed")
        evidence = self._read(entry[0])
        if evidence["template_sha256"] != binding.template_sha256:
            raise LayoutAuthorityRejected("template_changed")
        if (
            await self._released_check(evidence, binding.tenant_id)
            != binding.released_dependency
        ):
            raise LayoutAuthorityRejected("template_changed")
        return evidence

    async def resolve_binding(self, tenant_id: int):
        async with self._lock:
            entry = self._active.get(tenant_id)
            if entry is None:
                raise LayoutAuthorityRejected("qualification_required")
            await self._check(entry[1])
            return entry[1]

    async def renderer(self, binding: LayoutBinding):
        async with self._lock:
            return (await self._check(binding))["renderer"]

    @asynccontextmanager
    async def binding_guard(self, binding: LayoutBinding):
        async with self._lock:
            await self._check(binding)
            yield
