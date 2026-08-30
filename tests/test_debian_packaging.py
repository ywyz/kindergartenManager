"""Debian packaging 安全与部署约束回归测试。"""

import re
from pathlib import Path


_ROOT = Path(__file__).parents[1]
_SERVICE = _ROOT / "packaging/debian/lib/systemd/system/kindergarten-manager.service"
_POSTINST = _ROOT / "packaging/debian/DEBIAN/postinst"
_ENV_PATH = "/etc/kindergarten-manager/env"
_DATA_DIR = "/var/lib/kindergarten-manager"
_SERVICE_USER = "kindergarten-manager"
_SERVICE_GROUP = "kindergarten-manager"


def test_service_uses_non_root_user_and_group() -> None:
    service = _SERVICE.read_text(encoding="utf-8")

    user = re.search(r"^User=(.*)$", service, flags=re.MULTILINE)
    group = re.search(r"^Group=(.*)$", service, flags=re.MULTILINE)
    assert user is not None
    assert group is not None
    assert user.group(1) == _SERVICE_USER
    assert group.group(1) == _SERVICE_GROUP
    assert user.group(1) != "root"
    assert group.group(1) != "root"

    assert f"EnvironmentFile={_ENV_PATH}" in service
    assert f"WorkingDirectory={_DATA_DIR}" in service
    assert "UMask=0077" in service
    assert "ProtectSystem=strict" in service
    assert "ProtectHome=true" in service
    assert f"ReadWritePaths={_DATA_DIR}" in service


def test_postinst_declares_service_identity_idempotently() -> None:
    postinst = _POSTINST.read_text(encoding="utf-8")

    assert f"SERVICE_USER={_SERVICE_USER}" in postinst
    assert f"SERVICE_GROUP={_SERVICE_GROUP}" in postinst
    assert 'if ! getent group "$SERVICE_GROUP"' in postinst
    assert 'groupadd -r "$SERVICE_GROUP"' in postinst
    assert 'if ! id -u "$SERVICE_USER"' in postinst
    assert 'useradd -r -g "$SERVICE_GROUP"' in postinst


def test_postinst_enforces_secure_env_and_data_permissions() -> None:
    postinst = _POSTINST.read_text(encoding="utf-8")

    assert f"DATA_DIR={_DATA_DIR}" in postinst
    assert "KINDERGARTEN_DATA_DIR=${DATA_DIR}" in postinst
    assert 'if [ ! -f "$CONFIG_DIR/env" ]' in postinst
    assert 'chown root:"$SERVICE_GROUP" "$CONFIG_DIR/env"' in postinst
    assert 'chmod 640 "$CONFIG_DIR/env"' in postinst

    assert 'mkdir -p "$DATA_DIR/exports"' in postinst
    assert "chown -R --no-dereference" in postinst
    assert 'find "$DATA_DIR" -type d -exec chmod 700 {} +' in postinst
    assert 'find "$DATA_DIR" -type f -exec chmod 600 {} +' in postinst


def test_postinst_init_command_uses_same_service_context() -> None:
    postinst = _POSTINST.read_text(encoding="utf-8")

    init_cmd = re.search(
        r"sudo systemd-run --wait --pty --collect .*--init",
        postinst,
    )
    assert init_cmd is not None
    init_cmd_line = init_cmd.group(0)
    assert "--property=User=$SERVICE_USER" in init_cmd_line
    assert "--property=EnvironmentFile=$CONFIG_DIR/env" in init_cmd_line
    assert "--property=WorkingDirectory=$DATA_DIR" in init_cmd_line


def test_postinst_restarts_the_service_after_a_security_upgrade() -> None:
    postinst = _POSTINST.read_text(encoding="utf-8")

    assert "systemctl restart kindergarten-manager.service || true" in postinst


def test_postinst_does_not_create_default_admin_or_place_password_on_cmdline() -> None:
    postinst = _POSTINST.read_text(encoding="utf-8")

    assert "bootstrap_admin" not in postinst
    assert "python -m app.jobs.bootstrap_admin" not in postinst
    assert "--password" not in postinst
    assert "init-admin" not in postinst
