"""Ordinary startup with explicitly isolated synthetic evidence; never Word PASS."""

import inspect
import json
from hashlib import sha256

import pytest

from app.integration.word_export.shared_weekly_word import SEED_PATH
from app.service.shared_weekly import layout_authority
from app.service.shared_weekly import production_composition as composition
from app.service.shared_weekly.layout_authority import LayoutAuthorityRejected
from tests.test_wpe_word_authority import catalog

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
    # This is exactly the callback registered by app.main. Supporting the old
    # synchronous callback lets the original behavior fail at a business assertion.
    result = composition.configure_shared_weekly_production()
    if inspect.isawaitable(result):
        await result
    return composition.get_shared_weekly_services().exporting.word_port


def configured(monkeypatch, tmp_path, *, isolated=True):
    entries = catalog(tmp_path, renderer_version="synthetic-runtime")
    path, digest = entries["synthetic"]
    for key, value in zip(KEYS, (str(path), digest, "11", "1"), strict=True):
        monkeypatch.setenv(key, value)
    if isolated:
        original = layout_authority.LayoutAuthority

        def explicitly_local_authority(*args, **kwargs):
            # Only this test replaces the constructor. The production environment
            # has no local_only setting and cannot install this material.
            return original(*args, **{**kwargs, "local_only": True})

        monkeypatch.setattr(layout_authority, "LayoutAuthority", explicitly_local_authority)
    from app.integration.word_export import shared_weekly_word

    async def actual_version(*args):
        assert args == ("libreoffice", "--version")
        return b"synthetic-runtime\n"

    monkeypatch.setattr(shared_weekly_word, "_process", actual_version)
    return path


async def test_ordinary_startup_activates_only_explicit_tenant(monkeypatch, tmp_path):
    configured(monkeypatch, tmp_path)
    before = sha256(SEED_PATH.read_bytes()).hexdigest()
    word = await startup()
    binding = await word.resolve_binding(11)
    assert binding.tenant_id == 11
    assert binding.active_version.startswith("local-synthetic:")
    with pytest.raises(LayoutAuthorityRejected, match="qualification_required"):
        await word.resolve_binding(12)
    assert sha256(SEED_PATH.read_bytes()).hexdigest() == before


async def test_missing_configuration_remains_unqualified():
    word = await startup()
    with pytest.raises(LayoutAuthorityRejected, match="qualification_required"):
        await word.resolve_binding(11)


async def test_production_startup_rejects_local_synthetic(monkeypatch, tmp_path):
    configured(monkeypatch, tmp_path, isolated=False)
    with pytest.raises(LayoutAuthorityRejected, match="qualification_invalid"):
        await startup()
    assert composition._services is None


@pytest.mark.parametrize("missing", KEYS)
async def test_partial_config_cannot_activate(monkeypatch, tmp_path, missing):
    configured(monkeypatch, tmp_path)
    monkeypatch.delenv(missing)
    with pytest.raises(LayoutAuthorityRejected, match="qualification_config_invalid"):
        await startup()


@pytest.mark.parametrize("field", ["profile", "template_sha256", "released_binding", "renderer", "native"])
async def test_trusted_hash_does_not_bypass_material_binding(monkeypatch, tmp_path, field):
    path = configured(monkeypatch, tmp_path)
    data = json.loads(path.read_bytes())
    if field == "released_binding":
        data[field]["version"] += 1
    elif field == "renderer":
        data[field]["version"] = "drifted-runtime"
    elif field == "native":
        artifact = data["fixtures"][0]["artifacts"]["native-report.json"]
        (tmp_path / artifact["file"]).write_text("{}")
        artifact["sha256"] = sha256(b"{}").hexdigest()
        data["fixtures"][0]["observation"] = artifact["sha256"]
    else:
        data[field] = "0" * 64 if field == "template_sha256" else "other-profile"
    path.write_text(json.dumps(data))
    monkeypatch.setenv(KEYS[1], sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError):
        await startup()
    assert composition._services is None


async def test_hash_is_not_read_from_untrusted_manifest(monkeypatch, tmp_path):
    path = configured(monkeypatch, tmp_path)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(LayoutAuthorityRejected, match="qualification_invalid"):
        await startup()


async def test_current_material_drift_revokes_started_authority(monkeypatch, tmp_path):
    path = configured(monkeypatch, tmp_path)
    word = await startup()
    await word.resolve_binding(11)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(LayoutAuthorityRejected, match="qualification_invalid"):
        await word.resolve_binding(11)


@pytest.mark.parametrize(
    ("key", "value"),
    [(KEYS[1], "bad-digest"), (KEYS[2], "0"), (KEYS[2], "11,12"),
     (KEYS[3], "0"), (KEYS[0], "relative.json")],
)
async def test_operator_config_is_explicit_and_strict(monkeypatch, tmp_path, key, value):
    configured(monkeypatch, tmp_path)
    monkeypatch.setenv(key, value)
    with pytest.raises(LayoutAuthorityRejected, match="qualification_config_invalid"):
        await startup()


async def test_manifest_symlink_rejected(monkeypatch, tmp_path):
    path = configured(monkeypatch, tmp_path)
    link = tmp_path / "alias.json"
    link.symlink_to(path)
    monkeypatch.setenv(KEYS[0], str(link))
    with pytest.raises(LayoutAuthorityRejected, match="qualification_config_invalid"):
        await startup()


async def test_actual_renderer_drift_rejects_before_services_publish(monkeypatch, tmp_path):
    from app.integration.word_export import shared_weekly_word

    configured(monkeypatch, tmp_path)

    async def changed_runtime(*args):
        return b"different-runtime"

    monkeypatch.setattr(shared_weekly_word, "_process", changed_runtime)
    with pytest.raises(shared_weekly_word.LayoutRejected, match="renderer_changed"):
        await startup()
    assert composition._services is None


async def test_seed_drift_rejects_before_services_publish(monkeypatch, tmp_path):
    from app.integration.word_export import shared_weekly_word

    configured(monkeypatch, tmp_path)
    seed = tmp_path / "modified-seed.docx"
    seed.write_bytes(b"local negative fixture; never a Word document")
    monkeypatch.setattr(shared_weekly_word, "SEED_PATH", seed)
    with pytest.raises(shared_weekly_word.LayoutRejected, match="template_changed"):
        await startup()
    assert composition._services is None


async def test_explicit_local_fixture_injection_remains_isolated(monkeypatch, tmp_path):
    from app.integration.word_export.shared_weekly_word import SharedWeeklyWordPort

    authority = layout_authority.LayoutAuthority(catalog(tmp_path), local_only=True)
    await authority.activate(11, "synthetic", expected=None)
    port = SharedWeeklyWordPort(authority)
    await composition.configure_shared_weekly_production(word_port=port)
    assert composition.get_shared_weekly_services().exporting.word_port is port
    assert (await port.resolve_binding(11)).active_version.startswith("local-synthetic:")
