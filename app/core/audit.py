"""审计日志：记录关键操作（登录、改密、AI 调用、Word 导出等）。

审计日志通过结构化 JSON logger 输出，统一携带 audit_action 与 tenant_id/user_id
字段，便于后续采集与检索。审计调用绝不抛出异常，避免影响主业务流程。
"""
from app.core.logging import get_logger

_logger = get_logger("audit")


def log_audit(
    action: str,
    *,
    tenant_id: int | None = None,
    user_id: int | None = None,
    **detail,
) -> None:
    """记录一条审计日志。

    Args:
        action: 操作标识（如 login_success / change_password / ai_split /
                ai_generate / export_word）。
        tenant_id / user_id: 操作所属租户与用户。
        **detail: 额外结构化字段（如 task_type、file_name、role 等）。

    审计失败（如日志后端异常）静默忽略，不影响主流程。
    """
    try:
        _logger.info(
            "audit",
            extra={
                "audit_action": action,
                "tenant_id": tenant_id,
                "user_id": user_id,
                **detail,
            },
        )
    except Exception:
        pass
