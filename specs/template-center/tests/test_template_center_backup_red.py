"""模板中心备份、manifest 和隔离恢复的稳定 RED。"""

from datetime import datetime, timezone
from importlib import import_module

import pytest

from _support import actor, docx_with_text, make_center


def _api():
    return import_module("app.service.template_center")


@pytest.mark.asyncio
async def test_backup_is_created_from_current_template_snapshot_and_returns_closed_attestation():
    api = _api()
    center, effects = make_center(api)
    version = await center.upload(
        actor(),
        document_type="daily_plan",
        filename="backup.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=docx_with_text("backup fixture"),
    )
    await center.activate(
        actor(),
        document_type="daily_plan",
        version_id=version.template_version_id,
        expected_registry_revision=0,
        expected_active_version_id=None,
    )

    attestation = await center.create_backup(
        actor(),
        destination_handle="synthetic-backup-destination",
        protected_image="registry.example.invalid/app@sha256:abc",
        now=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
    )

    assert attestation.schema_version == 1
    assert attestation.status == "verified"
    assert attestation.artifact_sha256
    assert attestation.protected_image.endswith("sha256:abc")
    assert len(effects["backups"].created) == 1
    assert len(effects["versions"].versions) == 1
    assert len(effects["versions"].transitions) == 1
    assert "/tmp/template-center-test-backup" not in repr(attestation)


@pytest.mark.asyncio
async def test_restore_uses_isolated_target_and_does_not_accept_path_traversal_or_cross_tenant_input():
    api = _api()
    center, effects = make_center(api)

    with pytest.raises(api.TemplateCenterError):
        await center.restore_backup(
            actor(tenant_id=7),
            artifact_handle="../outside/template-backup.zip",
            target_handle="synthetic-restore-target",
        )

    assert effects["backups"].restored == []
    assert effects["versions"].versions == []
    assert effects["versions"].transitions == []


@pytest.mark.asyncio
async def test_restore_commit_is_not_visible_until_manifest_hashes_and_tenant_scope_are_verified():
    api = _api()
    center, effects = make_center(api)

    receipt = await center.restore_backup(
        actor(tenant_id=7),
        artifact_handle="verified-template-backup",
        target_handle="isolated-template-restore",
    )

    assert receipt.committed is True
    assert effects["backups"].restored
    restored = effects["backups"].restored[0]
    assert restored.expected_tenant_id == 7
    assert "verified-template-backup" not in repr(receipt)
    assert "isolated-template-restore" not in repr(receipt)
