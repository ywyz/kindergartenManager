"""自制教玩具服务层。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import ConfigError
from app.core.logging import get_logger
from app.integration.ai_client.homemade_teaching_client import generate_homemade_teaching
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key
from app.repository.prompt_repository import get_active_prompt

logger = get_logger(__name__)


async def generate_homemade_teaching_content(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    context: dict,
    _ai_client=None,
) -> dict[str, str]:
    """生成自制教玩具内容。"""
    ai_key_record = await get_active_ai_key(session, tenant_id, user_id, key_type="text")
    if ai_key_record is None:
        raise ConfigError("用户尚未配置 AI Key，请在设置页面配置后再使用")

    plain_api_key = get_decrypted_key(ai_key_record)

    prompt_template = await get_active_prompt(
        session,
        tenant_id,
        user_id,
        "homemade_teaching",
    )
    system_prompt = prompt_template.content if prompt_template else None

    logger.info(
        "开始生成自制教玩具",
        extra={"tenant_id": tenant_id, "user_id": user_id},
    )

    result = await generate_homemade_teaching(
        context=context,
        api_base_url=ai_key_record.api_base_url,
        api_key=plain_api_key,
        model_name=ai_key_record.model_name,
        system_prompt=system_prompt,
        _client=_ai_client,
    )

    logger.info(
        "自制教玩具生成完成",
        extra={"toy_name": result.get("toy_name", "")},
    )
    log_audit(
        "ai_homemade_teaching",
        tenant_id=tenant_id,
        user_id=user_id,
        grade=context.get("grade"),
        class_name=context.get("class_name"),
    )
    return result
