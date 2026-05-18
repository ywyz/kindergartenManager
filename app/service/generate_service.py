"""一日活动内容生成服务。

编排 AI 调用与提示词版本查询，供 UI 层调用。
支持：晨间活动、晨间谈话、区域游戏、户外游戏、一日活动反思。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConfigError
from app.core.logging import get_logger
from app.integration.ai_client.generate_client import generate_activity
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key
from app.repository.prompt_repository import get_active_prompt

logger = get_logger(__name__)


async def generate_activity_content(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    task_type: str,
    context: dict,
    *,
    _ai_client=None,
) -> str:
    """生成单项活动内容。

    Args:
        session: 异步数据库会话（查询 AI Key 与自定义提示词）。
        tenant_id / user_id: 用于隔离查询。
        task_type: 任务类型（morning_exercise / morning_talk /
                   area_game / outdoor_game / daily_reflection）。
        context: 上下文信息 dict，含 grade、class_name、activity_goal 等。
        _ai_client: 可选 httpx 客户端（测试用）。

    Returns:
        生成的活动内容文本字符串。

    Raises:
        ConfigError: 用户未配置 AI Key。
        AiCallError: AI 接口调用失败。
        AiParseError: AI 返回内容为空或不支持的任务类型。
    """
    ai_key_record = await get_active_ai_key(session, tenant_id, user_id)
    if ai_key_record is None:
        raise ConfigError("用户尚未配置 AI Key，请在设置页面配置后再使用")

    plain_api_key = get_decrypted_key(ai_key_record)
    api_base_url = ai_key_record.api_base_url
    model_name = ai_key_record.model_name

    # 查询当前激活的自定义提示词（无则使用内置默认）
    prompt_template = await get_active_prompt(session, tenant_id, user_id, task_type)
    system_prompt = prompt_template.content if prompt_template else None

    logger.info(
        "开始生成活动内容",
        extra={"tenant_id": tenant_id, "user_id": user_id, "task_type": task_type},
    )

    result = await generate_activity(
        task_type=task_type,
        context=context,
        api_base_url=api_base_url,
        api_key=plain_api_key,
        model_name=model_name,
        system_prompt=system_prompt,
        _client=_ai_client,
    )

    logger.info(
        "活动内容生成完成",
        extra={"task_type": task_type, "length": len(result)},
    )
    return result
