"""Load reviewed qualification from trusted process environment, never teacher settings.

The expected digest must be provided independently after operator review.
Nothing is read from the application's editable dotenv or teaching database.
No configuration means no qualification. Partial or invalid configuration aborts
assembly before any services are published. This module never installs evidence.
"""

import os
import re
from pathlib import Path

from app.integration.word_export.shared_weekly_word import SharedWeeklyWordPort
from app.service.shared_weekly.layout_authority import LayoutAuthorityRejected


async def load_operator_word_port() -> SharedWeeklyWordPort:
    from app.service.shared_weekly.layout_authority import LayoutAuthority

    names = (
        "KM_WEEKLY_LAYOUT_MANIFEST",
        "KM_WEEKLY_LAYOUT_SHA256",
        "KM_WEEKLY_LAYOUT_TENANT_ID",
        "KM_WEEKLY_LAYOUT_ACTIVATE",
    )
    values = tuple(os.environ.get(name) for name in names)
    if all(value is None for value in values):
        return SharedWeeklyWordPort()
    manifest, expected_hash, tenant, activate = values
    if (
        any(not value for value in values)
        or re.fullmatch(r"[0-9a-f]{64}", expected_hash or "") is None
        or re.fullmatch(r"[1-9][0-9]{0,17}", tenant or "") is None
        or activate != "1"
    ):
        raise LayoutAuthorityRejected("qualification_config_invalid")
    path = Path(manifest)
    if not path.is_absolute() or any(part == ".." for part in path.parts):
        raise LayoutAuthorityRejected("qualification_config_invalid")
    # Avoid operator path aliases and directories/devices; artifacts have their
    # own content and symlink checks in the unchanged qualification validator.
    if any(part.is_symlink() for part in (path, *path.parents)) or not path.is_file():
        raise LayoutAuthorityRejected("qualification_config_invalid")
    authority = LayoutAuthority(
        {"operator-reviewed": (path, expected_hash)}, local_only=False
    )
    binding = await authority.activate(int(tenant), "operator-reviewed", expected=None)
    port = SharedWeeklyWordPort(authority)
    await port.verify_runtime(binding)
    return port
