"""tests/test_audit.py — 审计日志测试。"""

from unittest.mock import patch

from app.core.audit import log_audit


@patch("app.core.audit._logger")
def test_log_audit_emits_structured_fields(mock_logger):
    """审计日志携带 audit_action / tenant_id / user_id 及附加字段。"""
    log_audit("login_success", tenant_id=1, user_id=2, role="teacher")

    mock_logger.info.assert_called_once()
    _, kwargs = mock_logger.info.call_args
    extra = kwargs["extra"]
    assert extra["audit_action"] == "login_success"
    assert extra["tenant_id"] == 1
    assert extra["user_id"] == 2
    assert extra["role"] == "teacher"


@patch("app.core.audit._logger")
def test_log_audit_defaults_none_ids(mock_logger):
    """未提供 tenant_id / user_id 时默认为 None。"""
    log_audit("system_event")

    _, kwargs = mock_logger.info.call_args
    extra = kwargs["extra"]
    assert extra["audit_action"] == "system_event"
    assert extra["tenant_id"] is None
    assert extra["user_id"] is None


@patch("app.core.audit._logger")
def test_log_audit_never_raises(mock_logger):
    """日志后端异常时审计调用静默忽略，不抛出。"""
    mock_logger.info.side_effect = RuntimeError("logging backend down")
    # 不应抛出异常
    log_audit("export_word", tenant_id=1, user_id=2, file_name="x.docx")
