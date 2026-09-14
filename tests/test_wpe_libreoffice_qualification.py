"""LibreOffice-rendered qualification through ordinary startup; tests only.

All fixture bytes are explicitly synthetic and labelled as such; none of them
is real qualification evidence. The renderer process probe may be mocked for
unit startup, and the positive startup test uses the actual local LibreOffice
version string reported by the real ``libreoffice --version`` process.
"""

import inspect
import json
from hashlib import sha256

import pytest

from app.integration.word_export.shared_weekly_word import (
    SEED_SHA256,
    _process,
)
from app.service.shared_weekly import layout_authority
from app.service.shared_weekly import production_composition as composition
from app.service.shared_weekly.layout_authority import LayoutAuthorityRejected
from app.service.shared_weekly.layout_contracts import PROFILE
from tests.test_wpe_word_authority import catalog as synthetic_catalog

KEYS = (
    "KM_WEEKLY_LAYOUT_MANIFEST",
    "KM_WEEKLY_LAYOUT_SHA256",
    "KM_WEEKLY_LAYOUT_TENANT_ID",
    "KM_WEEKLY_LAYOUT_ACTIVATE",
)


@pytest.fixture(autouse=True)
def isolate_startup(monkeypatch):
    from app.core import database

    for key in KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(composition, "_services", None)

    def no_database(*args, **kwargs):
        pytest.fail("qualification startup must not open a database session")

    monkeypatch.setattr(database, "AsyncSessionLocal", no_database)


async def startup():
    result = composition.configure_shared_weekly_production()
    if inspect.isawaitable(result):
        await result
    return composition.get_shared_weekly_services().exporting.word_port


def lo_catalog(
    tmp_path,
    *,
    manifest_role="libreoffice-rendered",
    client_product="LibreOffice",
    client_version=None,
    renderer_version=None,
    observation_role=None,
    observation_client=None,
    observation_renderer=None,
    released_version_delta=0,
):
    """Synthetic LibreOffice-rendered manifest; labelled tests only."""
    from app.integration.word_export import (
        released_weekly_monthly_word_port as released,
    )
    from app.service.template_center.contracts import DocumentType

    profile = released._profile(DocumentType.WEEKLY_ACTIVITY_PLAN)
    released_binding = {
        "template_version_id": str(
            released._RELEASED[DocumentType.WEEKLY_ACTIVITY_PLAN][1]
        ),
        "version": released._ACTIVE_VERSION + released_version_delta,
        "content_sha256": SEED_SHA256,
        "contract_id": profile.contract.contract_id,
        "contract_version": profile.contract.contract_version,
    }
    client = {
        "product": client_product,
        "version": client_version or "synthetic-lo-runtime-1",
    }
    renderer = {
        "product": "LibreOffice",
        "version": renderer_version or "synthetic-lo-runtime-1",
    }
    fixtures = []
    for columns in (5, 6):
        artifacts = {}
        for kind in ("docx", "pdf", "page-1.png"):
            raw = f"synthetic-lo-{columns}-{kind}".encode()
            name = f"{columns}-{kind}"
            (tmp_path / name).write_bytes(raw)
            artifacts[kind] = {"file": name, "sha256": sha256(raw).hexdigest()}
        observation = {
            "schema": "weekly-layout-native-observation.v1",
            "role": observation_role or manifest_role,
            "client": observation_client or client,
            "renderer": observation_renderer or renderer,
            "columns": columns,
            "body_sha256": "b" * 64,
            "template_sha256": SEED_SHA256,
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
        raw = json.dumps(observation).encode()
        name = f"{columns}-native-report.json"
        (tmp_path / name).write_bytes(raw)
        digest = sha256(raw).hexdigest()
        artifacts["native-report.json"] = {"file": name, "sha256": digest}
        fixtures.append(
            {
                "columns": columns,
                "body_sha256": "b" * 64,
                "artifacts": artifacts,
                "observation": digest,
            }
        )
    raw = json.dumps(
        {
            "schema": "weekly-layout-qualification.v1",
            "profile": PROFILE,
            "template_sha256": SEED_SHA256,
            "renderer": renderer,
            "client": client,
            "role": manifest_role,
            "fixtures": fixtures,
            "released_binding": released_binding,
        }
    ).encode()
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(raw)
    return manifest, sha256(raw).hexdigest()


def word_catalog(tmp_path, *, actual_renderer_version):
    """Historical Microsoft Word client catalog with the real LO renderer."""
    from app.integration.word_export import (
        released_weekly_monthly_word_port as released,
    )
    from app.service.template_center.contracts import DocumentType

    profile = released._profile(DocumentType.WEEKLY_ACTIVITY_PLAN)
    released_binding = {
        "template_version_id": str(
            released._RELEASED[DocumentType.WEEKLY_ACTIVITY_PLAN][1]
        ),
        "version": released._ACTIVE_VERSION,
        "content_sha256": SEED_SHA256,
        "contract_id": profile.contract.contract_id,
        "contract_version": profile.contract.contract_version,
    }
    client = {"product": "Microsoft Word 365", "version": "16.0.19000"}
    renderer = {"product": "LibreOffice", "version": actual_renderer_version}
    fixtures = []
    for columns in (5, 6):
        artifacts = {}
        for kind in ("docx", "pdf", "page-1.png"):
            raw = f"synthetic-word-{columns}-{kind}".encode()
            name = f"{columns}-{kind}"
            (tmp_path / name).write_bytes(raw)
            artifacts[kind] = {"file": name, "sha256": sha256(raw).hexdigest()}
        observation = {
            "schema": "weekly-layout-native-observation.v1",
            "role": "word-native",
            "client": client,
            "renderer": renderer,
            "columns": columns,
            "body_sha256": "c" * 64,
            "template_sha256": SEED_SHA256,
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
        raw = json.dumps(observation).encode()
        name = f"{columns}-native-report.json"
        (tmp_path / name).write_bytes(raw)
        digest = sha256(raw).hexdigest()
        artifacts["native-report.json"] = {"file": name, "sha256": digest}
        fixtures.append(
            {
                "columns": columns,
                "body_sha256": "c" * 64,
                "artifacts": artifacts,
                "observation": digest,
            }
        )
    raw = json.dumps(
        {
            "schema": "weekly-layout-qualification.v1",
            "profile": PROFILE,
            "template_sha256": SEED_SHA256,
            "renderer": renderer,
            "client": client,
            "role": "word-native",
            "fixtures": fixtures,
            "released_binding": released_binding,
        }
    ).encode()
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(raw)
    return manifest, sha256(raw).hexdigest()


def configured(monkeypatch, manifest, digest):
    for key, value in zip(KEYS, (str(manifest), digest, "11", "1"), strict=True):
        monkeypatch.setenv(key, value)
    return manifest


async def actual_lo_version():
    return (await _process("libreoffice", "--version")).decode().strip()


async def test_ordinary_startup_activates_libreoffice_rendered(monkeypatch, tmp_path):
    version = await actual_lo_version()
    manifest, digest = lo_catalog(
        tmp_path,
        client_version=version,
        renderer_version=version,
    )
    configured(monkeypatch, manifest, digest)
    word = await startup()
    binding = await word.resolve_binding(11)
    assert binding.tenant_id == 11
    assert binding.active_version.startswith("qualified:")
    await word.verify_runtime(binding)
    with pytest.raises(LayoutAuthorityRejected, match="qualification_required"):
        await word.resolve_binding(12)


async def test_missing_configuration_remains_unqualified():
    word = await startup()
    with pytest.raises(LayoutAuthorityRejected, match="qualification_required"):
        await word.resolve_binding(11)


@pytest.mark.parametrize(
    ("kwargs", "observation"),
    [
        # Masquerading LO as word-native.
        ({"manifest_role": "word-native"}, False),
        # Arbitrary product prefix must not infer the role.
        ({"client_product": "LibreOffice-fork 26.2"}, False),
        ({"client_product": "Microsoft Word 365"}, False),
        # Role/client mismatch.
        ({"client_product": "Microsoft Word 365", "client_version": "16"}, False),
        # LO client/renderer version mismatch.
        ({"renderer_version": "synthetic-lo-runtime-2"}, False),
        ({"client_version": "synthetic-lo-runtime-2"}, False),
        # Native report disagreement with the manifest.
        ({"observation_role": "word-native"}, True),
    ],
)
async def test_libreoffice_role_and_client_agreement_fail_closed(
    monkeypatch, tmp_path, kwargs, observation
):
    if observation:
        kwargs["observation_role"] = kwargs.get("observation_role", "word-native")
    manifest, digest = lo_catalog(tmp_path, **kwargs)
    configured(monkeypatch, manifest, digest)
    with pytest.raises(LayoutAuthorityRejected, match="qualification_invalid"):
        await startup()
    assert composition._services is None


async def test_libreoffice_report_client_mismatch_fail_closed(monkeypatch, tmp_path):
    manifest, digest = lo_catalog(
        tmp_path,
        observation_client={"product": "Microsoft Word 365", "version": "16"},
    )
    configured(monkeypatch, manifest, digest)
    with pytest.raises(LayoutAuthorityRejected, match="qualification_invalid"):
        await startup()
    assert composition._services is None


async def test_tamper_after_activation_revokes_binding(monkeypatch, tmp_path):
    version = await actual_lo_version()
    manifest, digest = lo_catalog(
        tmp_path,
        client_version=version,
        renderer_version=version,
    )
    configured(monkeypatch, manifest, digest)
    word = await startup()
    await word.resolve_binding(11)
    (tmp_path / "5-page-1.png").write_bytes(b"synthetic tamper; tests only")
    with pytest.raises(LayoutAuthorityRejected, match="qualification_invalid"):
        await word.resolve_binding(11)


async def test_released_binding_drift_revokes_binding(monkeypatch, tmp_path):
    from app.integration.word_export import (
        released_weekly_monthly_word_port as released,
    )

    version = await actual_lo_version()
    manifest, digest = lo_catalog(
        tmp_path,
        client_version=version,
        renderer_version=version,
    )
    configured(monkeypatch, manifest, digest)
    word = await startup()
    await word.resolve_binding(11)
    monkeypatch.setattr(released, "_ACTIVE_VERSION", released._ACTIVE_VERSION + 1)
    with pytest.raises(LayoutAuthorityRejected, match="template_changed"):
        await word.resolve_binding(11)


async def test_released_binding_drift_rejects_before_publish(monkeypatch, tmp_path):
    manifest, digest = lo_catalog(tmp_path, released_version_delta=1)
    configured(monkeypatch, manifest, digest)
    with pytest.raises(LayoutAuthorityRejected, match="template_changed"):
        await startup()
    assert composition._services is None


async def test_renderer_drift_rejects_before_publish(monkeypatch, tmp_path):
    from app.integration.word_export import shared_weekly_word

    manifest, digest = lo_catalog(tmp_path)
    configured(monkeypatch, manifest, digest)

    async def changed_runtime(*args):
        return b"different-runtime"

    monkeypatch.setattr(shared_weekly_word, "_process", changed_runtime)
    with pytest.raises(shared_weekly_word.LayoutRejected, match="renderer_changed"):
        await startup()
    assert composition._services is None


async def test_word_native_catalog_remains_accepted(monkeypatch, tmp_path):
    version = await actual_lo_version()
    manifest, digest = word_catalog(tmp_path, actual_renderer_version=version)
    configured(monkeypatch, manifest, digest)
    word = await startup()
    binding = await word.resolve_binding(11)
    assert binding.active_version.startswith("qualified:")
    await word.verify_runtime(binding)


async def test_production_startup_still_rejects_local_synthetic(monkeypatch, tmp_path):
    entries = synthetic_catalog(tmp_path)
    path, digest = entries["synthetic"]
    configured(monkeypatch, path, digest)
    with pytest.raises(LayoutAuthorityRejected, match="qualification_invalid"):
        await startup()
    assert composition._services is None


async def test_word_native_role_requires_word_client_prefix(tmp_path):
    authority = layout_authority.LayoutAuthority()
    manifest, digest = lo_catalog(
        tmp_path,
        manifest_role="word-native",
        client_product="LibreOffice 26.2",
    )
    authority._catalog = {"reviewed": (manifest, digest)}
    with pytest.raises(LayoutAuthorityRejected, match="qualification_invalid"):
        await authority.activate(1, "reviewed", expected=None)


@pytest.mark.parametrize(
    "role",
    ["libreoffice-rendered", "word-native"],
)
async def test_local_only_rejects_formal_roles(tmp_path, role):
    version = await actual_lo_version()
    if role == "libreoffice-rendered":
        manifest, digest = lo_catalog(
            tmp_path,
            client_version=version,
            renderer_version=version,
        )
    else:
        manifest, digest = word_catalog(tmp_path, actual_renderer_version=version)
    authority = layout_authority.LayoutAuthority(local_only=True)
    authority._catalog = {"reviewed": (manifest, digest)}
    with pytest.raises(LayoutAuthorityRejected, match="qualification_invalid"):
        await authority.activate(1, "reviewed", expected=None)
