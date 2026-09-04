"""T005 stable RED for content-addressed blobs and immutable upload versions.

All candidates are synthetic in-memory OOXML bytes.  This slice deliberately
does not exercise active pointers, lifecycle operations, exporters, previews,
backups, database models, or repository template files.
"""

from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from importlib import import_module
from inspect import signature
from pathlib import Path

import pytest

from _support import AllowPolicy, actor, docx_with_text, make_upload_center


def _api():
    return import_module("app.service.template_center")


async def _upload(center, *, session=None, content=None, document_type="daily_plan"):
    return await center.upload(
        session or actor(),
        document_type=document_type,
        filename="synthetic.docx",
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        content=content or docx_with_text("synthetic T005 candidate"),
    )


def test_t005_public_service_is_upload_only_and_has_no_caller_tenant_override():
    api = _api()
    public = {name for name in vars(api.TemplateCenter) if not name.startswith("_")}
    assert public == {"upload"}
    parameters = signature(api.TemplateCenter.upload).parameters
    assert "tenant_id" not in parameters
    assert not hasattr(api.TemplateCenter, "activate")
    assert not hasattr(api.TemplateCenter, "resolve_active")
    assert not hasattr(api.TemplateCenter, "project")


@pytest.mark.asyncio
async def test_each_authorized_upload_gets_a_new_immutable_version_while_blob_deduplicates():
    api = _api()
    center, effects = make_upload_center(api)
    content = docx_with_text("identical synthetic bytes")

    first = await _upload(center, content=content)
    second = await _upload(center, content=content)

    assert (first.version, second.version) == (1, 2)
    assert first.template_version_id != second.template_version_id
    assert first.content_sha256 == second.content_sha256 == sha256(content).hexdigest()
    assert first.blob_ref == second.blob_ref == f"sha256/{first.content_sha256}"
    assert len(effects["blobs"].blobs) == 1
    assert len(effects["versions"].versions) == 2
    assert len(effects["audit"].events) == 2
    with pytest.raises(FrozenInstanceError):
        first.version = 99


@pytest.mark.asyncio
async def test_version_numbers_are_monotonic_and_isolated_by_tenant_and_document_type():
    api = _api()
    center, _effects = make_upload_center(api)

    tenant_7_first = await _upload(center, session=actor(tenant_id=7))
    tenant_8_first = await _upload(center, session=actor(tenant_id=8))
    tenant_7_second = await _upload(center, session=actor(tenant_id=7))

    assert tenant_7_first.version == 1
    assert tenant_7_second.version == 2
    assert tenant_8_first.version == 1


@pytest.mark.asyncio
async def test_version_binds_exact_tenant_type_blob_and_full_validation_evidence():
    api = _api()
    center, _effects = make_upload_center(api)
    session = actor(tenant_id=23, user_id=41)
    content = docx_with_text("evidence-bound synthetic candidate")

    version = await _upload(center, session=session, content=content)
    evidence = version.validation_evidence

    assert version.tenant_id == 23
    assert version.created_by_user_id == 41
    assert version.document_type is api.DocumentType.DAILY_PLAN
    assert evidence.validation_receipt_id == version.validation_receipt_id
    assert (
        evidence.content_sha256 == version.content_sha256 == sha256(content).hexdigest()
    )
    assert evidence.size_bytes == version.size_bytes == len(content)
    assert evidence.contract_id == version.contract_id
    assert evidence.contract_version == version.contract_version
    assert evidence.structural_profile_id == "legacy_structural_v1.daily_plan"
    assert evidence.structural_profile_version == 1
    assert len(evidence.structure_summary_sha256) == 64
    assert evidence.validator_version == version.validator_version
    assert evidence.token_occurrences == ()
    assert not hasattr(version, "content")
    assert not hasattr(version, "path")
    assert not hasattr(version, "session")


@pytest.mark.asyncio
async def test_authorization_and_the_unique_t004_validator_run_before_persistence(
    monkeypatch,
):
    api = _api()
    center, effects = make_upload_center(api)
    service_module = import_module("app.service.template_center.service")
    real_validator = api.validate_upload

    def observed_validator(*args, **kwargs):
        effects["events"].append("validate_upload")
        return real_validator(*args, **kwargs)

    monkeypatch.setattr(service_module, "validate_upload", observed_validator)
    await _upload(center)

    assert effects["events"] == [
        "authorize",
        "validate_upload",
        "begin",
        "allocate_version",
        "put_blob",
        "stage_version",
        "stage_audit",
        "commit",
    ]


@pytest.mark.asyncio
async def test_default_deny_prevents_validation_blob_and_version_but_commits_one_safe_audit(
    monkeypatch,
):
    api = _api()
    events: list[str] = []
    center, effects = make_upload_center(
        api, policy=AllowPolicy(allowed={"read"}, events=events)
    )
    service_module = import_module("app.service.template_center.service")

    def forbidden_validator(*_args, **_kwargs):
        raise AssertionError("validator must not run before authorization")

    monkeypatch.setattr(service_module, "validate_upload", forbidden_validator)
    with pytest.raises(api.TemplateCenterError) as caught:
        await _upload(center, session=actor(role="teacher"))

    assert caught.value.code is api.TemplateErrorCode.PERMISSION_DENIED
    assert effects["blobs"].calls == []
    assert effects["versions"].versions == []
    assert len(effects["audit"].events) == 1
    assert effects["audit"].events[0].outcome is api.AuditOutcome.DENIED
    assert "stage_version" not in events


@pytest.mark.asyncio
async def test_noncanonical_permission_decision_fails_closed_before_validation_or_blob():
    api = _api()
    policy = AllowPolicy(force_invalid_decision=True)
    center, effects = make_upload_center(api, policy=policy)

    with pytest.raises(api.TemplateCenterError) as caught:
        await _upload(center)

    assert caught.value.code is api.TemplateErrorCode.PERMISSION_DENIED
    assert effects["blobs"].calls == []
    assert effects["versions"].versions == []


@pytest.mark.asyncio
async def test_forged_or_mismatched_validator_receipt_fails_closed(monkeypatch):
    api = _api()
    center, effects = make_upload_center(api)
    service_module = import_module("app.service.template_center.service")

    monkeypatch.setattr(service_module, "validate_upload", lambda *_a, **_k: object())
    with pytest.raises(api.TemplateCenterError) as caught:
        await _upload(center)

    assert caught.value.code is api.TemplateErrorCode.VALIDATION_FAILED
    assert effects["blobs"].calls == []
    assert effects["versions"].versions == []
    assert len(effects["audit"].events) == 1
    assert effects["audit"].events[0].outcome is api.AuditOutcome.REJECTED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("content_sha256", "0" * 64),
        ("size_bytes", 1),
        ("contract_id", "kg.template.other.v1"),
        ("structural_profile_id", "other.profile.v1"),
    ],
)
async def test_well_formed_but_content_or_contract_mismatched_receipt_is_rejected(
    monkeypatch, field, value
):
    api = _api()
    center, effects = make_upload_center(api)
    service_module = import_module("app.service.template_center.service")
    content = docx_with_text("receipt mismatch synthetic candidate")
    receipt = api.validate_upload(
        content,
        "synthetic.docx",
        api.DOCX_MIME_TYPE,
        api.build_initial_contract_registry().resolve("daily_plan"),
    )
    monkeypatch.setattr(
        service_module,
        "validate_upload",
        lambda *_args, **_kwargs: replace(receipt, **{field: value}),
    )

    with pytest.raises(api.TemplateCenterError) as caught:
        await _upload(center, content=content)

    assert caught.value.code is api.TemplateErrorCode.VALIDATION_FAILED
    assert effects["blobs"].calls == []
    assert effects["versions"].versions == []
    assert len(effects["audit"].events) == 1
    assert effects["audit"].events[0].outcome is api.AuditOutcome.REJECTED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("document_type", "error_code"),
    [
        ("weekly_activity_plan", "document_type_reserved_until_gate"),
        ("monthly_theme_activity_plan", "document_type_reserved_until_gate"),
        ("unknown_type", "unknown_document_type"),
        ("DAILY_PLAN", "unknown_document_type"),
    ],
)
async def test_disabled_unknown_and_alias_types_fail_closed_without_side_effects(
    document_type, error_code
):
    api = _api()
    center, effects = make_upload_center(api)

    with pytest.raises(api.TemplateCenterError) as caught:
        await _upload(center, document_type=document_type)

    assert caught.value.code.value == error_code
    assert effects["permissions"].calls == []
    assert effects["blobs"].calls == []
    assert effects["transactions"].units == []


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_tenant", [0, -1, True, "7"])
async def test_invalid_or_untrusted_tenant_scope_fails_closed(bad_tenant):
    api = _api()
    center, effects = make_upload_center(api)
    session = actor()
    object.__setattr__(session, "tenant_id", bad_tenant)

    with pytest.raises(api.TemplateCenterError):
        await _upload(center, session=session)

    assert effects["blobs"].calls == []
    assert effects["versions"].versions == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    ["blob", "stage_version", "stage_audit", "commit"],
)
async def test_every_storage_stage_failure_leaves_no_visible_version_audit_or_pointer(
    failure,
):
    api = _api()
    center, effects = make_upload_center(api)
    if failure == "blob":
        effects["blobs"].fail_put = True
    else:
        setattr(effects["transactions"], f"fail_{failure}", True)

    with pytest.raises(api.TemplateCenterError) as caught:
        await _upload(center)

    assert caught.value.code is api.TemplateErrorCode.STORAGE_FAILED
    assert effects["versions"].versions == []
    assert effects["versions"].transitions == []
    assert effects["audit"].events == []
    if failure == "blob":
        assert effects["blobs"].blobs == {}


@pytest.mark.asyncio
async def test_failed_upload_allocation_is_never_reused():
    api = _api()
    center, effects = make_upload_center(api)
    effects["transactions"].fail_commit = True

    with pytest.raises(api.TemplateCenterError):
        await _upload(center)

    effects["transactions"].fail_commit = False
    version = await _upload(center)
    assert version.version == 2
    assert len(effects["versions"].versions) == 1


@pytest.mark.asyncio
async def test_upload_audit_is_atomic_minimal_and_redacted_without_active_revision():
    api = _api()
    center, effects = make_upload_center(api)
    secret_text = "PRIVATE-SYNTHETIC-BODY"
    session = actor()

    version = await _upload(
        center, session=session, content=docx_with_text(secret_text)
    )
    event = effects["audit"].events[0]

    assert event.action is api.TemplateCapability.UPLOAD
    assert event.outcome is api.AuditOutcome.ACCEPTED
    assert event.template_version_id == version.template_version_id
    assert event.content_sha256 == version.content_sha256
    assert event.contract_id == version.contract_id
    assert event.contract_version == version.contract_version
    assert event.registry_revision is None
    assert (
        event.session_hash
        == sha256(str(session.session_id).encode("ascii")).hexdigest()
    )
    assert secret_text not in repr(event)
    assert "synthetic.docx" not in repr(event)
    assert effects["transactions"].units[-1].stage_calls == ["version", "audit"]


@pytest.mark.asyncio
async def test_upload_never_creates_or_changes_an_active_pointer():
    api = _api()
    center, effects = make_upload_center(api)
    await _upload(center)
    await _upload(center)

    assert effects["versions"].transitions == []
    assert effects["versions"].active == {}
    assert all(
        "transition" not in unit.stage_calls for unit in effects["transactions"].units
    )


@pytest.mark.asyncio
async def test_content_addressed_store_deduplicates_synthetic_bytes_and_rejects_hash_mismatch(
    tmp_path: Path,
):
    api = _api()
    root = tmp_path / "trusted-template-blobs"
    store = api.ContentAddressedTemplateBlobStore(root)
    content = docx_with_text("synthetic blob store candidate")
    digest = sha256(content).hexdigest()

    first = await store.put_if_absent(digest, content)
    second = await store.put_if_absent(digest, content)

    assert (
        first == second == api.BlobRef(value=f"sha256/{digest}", content_sha256=digest)
    )
    assert await store.read(first, digest) == content
    assert await store.exists(first, digest) is True
    assert len([path for path in root.rglob("*") if path.is_file()]) == 1
    assert root.stat().st_mode & 0o777 == 0o700
    with pytest.raises(api.TemplateCenterError) as caught:
        await store.put_if_absent("0" * 64, content)
    assert caught.value.code is api.TemplateErrorCode.STORAGE_FAILED


@pytest.mark.asyncio
async def test_content_addressed_store_rejects_unsafe_root_and_existing_blob_collision(
    tmp_path: Path,
):
    api = _api()
    real_root = tmp_path / "real-root"
    real_root.mkdir(mode=0o700)
    linked_root = tmp_path / "linked-root"
    linked_root.symlink_to(real_root, target_is_directory=True)

    with pytest.raises(api.TemplateCenterError):
        api.ContentAddressedTemplateBlobStore(linked_root)

    store = api.ContentAddressedTemplateBlobStore(real_root)
    content = docx_with_text("synthetic collision candidate")
    digest = sha256(content).hexdigest()
    blob_path = real_root / digest[:2] / digest
    blob_path.parent.mkdir(mode=0o700)
    blob_path.write_bytes(b"different bytes under claimed digest")
    blob_path.chmod(0o600)

    with pytest.raises(api.TemplateCenterError) as caught:
        await store.put_if_absent(digest, content)
    assert caught.value.code is api.TemplateErrorCode.STORAGE_FAILED


@pytest.mark.asyncio
async def test_missing_blob_lookup_is_read_only_and_does_not_create_a_shard(
    tmp_path: Path,
):
    api = _api()
    root = tmp_path / "trusted-template-blobs"
    store = api.ContentAddressedTemplateBlobStore(root)
    digest = "1" * 64
    reference = api.BlobRef(value=f"sha256/{digest}", content_sha256=digest)

    assert await store.exists(reference, digest) is False
    assert tuple(root.iterdir()) == ()


@pytest.mark.asyncio
async def test_blob_with_an_external_hard_link_is_rejected_as_mutable_alias(
    tmp_path: Path,
):
    api = _api()
    root = tmp_path / "trusted-template-blobs"
    store = api.ContentAddressedTemplateBlobStore(root)
    content = docx_with_text("synthetic hard-link candidate")
    digest = sha256(content).hexdigest()
    reference = await store.put_if_absent(digest, content)
    blob_path = root / digest[:2] / digest
    outside_alias = tmp_path / "outside-alias"
    outside_alias.hardlink_to(blob_path)

    with pytest.raises(api.TemplateCenterError) as caught:
        await store.read(reference, digest)
    assert caught.value.code is api.TemplateErrorCode.STORAGE_FAILED


def test_blob_root_owned_by_another_effective_user_is_rejected(
    tmp_path: Path, monkeypatch
):
    api = _api()
    blob_store_module = import_module("app.service.template_center.blob_store")
    root = tmp_path / "foreign-owner-root"
    root.mkdir(mode=0o700)
    actual_owner = root.stat().st_uid
    monkeypatch.setattr(blob_store_module.os, "geteuid", lambda: actual_owner + 1)

    with pytest.raises(api.TemplateCenterError) as caught:
        api.ContentAddressedTemplateBlobStore(root)
    assert caught.value.code is api.TemplateErrorCode.STORAGE_FAILED


def test_blob_root_rejects_a_symlink_in_an_intermediate_ancestor(tmp_path: Path):
    api = _api()
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir(mode=0o700)
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)

    with pytest.raises(api.TemplateCenterError) as caught:
        api.ContentAddressedTemplateBlobStore(linked_parent / "blob-root")
    assert caught.value.code is api.TemplateErrorCode.STORAGE_FAILED


@pytest.mark.asyncio
async def test_blob_put_fails_closed_when_plaintext_temporary_cleanup_fails(
    tmp_path: Path, monkeypatch
):
    api = _api()
    blob_store_module = import_module("app.service.template_center.blob_store")
    root = tmp_path / "trusted-template-blobs"
    store = api.ContentAddressedTemplateBlobStore(root)
    content = docx_with_text("synthetic cleanup failure candidate")
    digest = sha256(content).hexdigest()
    real_unlink = blob_store_module.os.unlink

    def fail_temporary_unlink(path, *args, **kwargs):
        if Path(path).name.startswith(".template-blob-"):
            raise OSError("synthetic temporary cleanup failure")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(blob_store_module.os, "unlink", fail_temporary_unlink)
    with pytest.raises(api.TemplateCenterError) as caught:
        await store.put_if_absent(digest, content)
    assert caught.value.code is api.TemplateErrorCode.STORAGE_FAILED
