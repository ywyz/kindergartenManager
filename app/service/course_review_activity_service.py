"""课程审议服务层。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import ConfigError
from app.core.logging import get_logger
from app.integration.ai_client.course_review_activity_client import (
    generate_course_review_activity,
)
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key
from app.repository.prompt_repository import get_active_prompt

logger = get_logger(__name__)


async def generate_course_review_activity_content(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    context: dict,
    _ai_client=None,
) -> dict[str, object]:
    """生成课程审议内容。"""
    ai_key_record = await get_active_ai_key(session, tenant_id, user_id, key_type="text")
    if ai_key_record is None:
        raise ConfigError("用户尚未配置 AI Key，请在设置页面配置后再使用")

    plain_api_key = get_decrypted_key(ai_key_record)

    prompt_template = await get_active_prompt(
        session,
        tenant_id,
        user_id,
        "course_review_activity",
    )
    system_prompt = prompt_template.content if prompt_template else None

    logger.info(
        "开始生成课程审议",
        extra={"tenant_id": tenant_id, "user_id": user_id},
    )

    result = await generate_course_review_activity(
        context=context,
        api_base_url=ai_key_record.api_base_url,
        api_key=plain_api_key,
        model_name=ai_key_record.model_name,
        system_prompt=system_prompt,
        _client=_ai_client,
    )

    logger.info(
        "课程审议生成完成",
        extra={"activity_name": context.get("activity_name", "")},
    )
    log_audit(
        "ai_course_review_activity",
        tenant_id=tenant_id,
        user_id=user_id,
        grade=context.get("grade"),
        class_name=context.get("class_name"),
    )
    return result
