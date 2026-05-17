"""教案拆分服务 — 编排完整教案拆分与年龄适配流程。

流程：
1. 从数据库获取用户 AI Key（解密）
2. 调用 split_lesson_plan() 拆分教案
3. 调用 adapt_activity_process() 对活动过程改写
4. 调用 compute_diff() 生成差异列表
5. 返回 LessonPlanResult dataclass

注意：此服务不负责入库，入库由 repository 层负责，由 UI 层触发。
"""

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConfigError
from app.core.logging import get_logger
from app.integration.ai_client.adapt_client import adapt_activity_process
from app.integration.ai_client.lesson_plan_client import split_lesson_plan
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key
from app.service.diff_service import compute_diff

logger = get_logger(__name__)


@dataclass
class LessonPlanResult:
    """教案拆分与年龄适配的完整结果。

    Attributes:
        activity_goal: 活动目标（AI 拆分原文）。
        activity_prep: 活动准备。
        activity_key: 活动重点。
        activity_difficult: 活动难点。
        activity_process_original: 活动过程原文（AI 拆分结果）。
        activity_process_adapted: 活动过程改写文（年龄适配后）。
        diff_result: 改写文与原文的差异列表，每项 {"text": str, "changed": bool}。
    """

    activity_goal: str
    activity_prep: str
    activity_key: str
    activity_difficult: str
    activity_process_original: str
    activity_process_adapted: str
    diff_result: list[dict] = field(default_factory=list)


async def process_lesson_plan(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    raw_text: str,
    grade: str,
    *,
    split_system_prompt: str | None = None,
    adapt_system_prompt: str | None = None,
    _ai_client=None,
) -> LessonPlanResult:
    """完整教案拆分与年龄适配流程。

    Args:
        session: 异步数据库会话（用于查询 AI Key）。
        tenant_id / user_id: 用于查询用户 AI Key。
        raw_text: 用户粘贴的完整教案文本。
        grade: 年龄段（小班/中班/大班），用于年龄适配。
        split_system_prompt: 自定义拆分 prompt（None 时使用内置默认）。
        adapt_system_prompt: 自定义适配 prompt（None 时使用内置默认）。
        _ai_client: 可选 httpx 客户端（测试用）。

    Returns:
        LessonPlanResult — 包含所有拆分字段 + 改写文 + 差异列表。

    Raises:
        ConfigError: 用户未配置 AI Key。
        AiCallError: AI 接口调用失败。
        AiParseError: AI 返回内容解析失败。
    """
    # 1. 获取 AI Key
    ai_key_record = await get_active_ai_key(session, tenant_id, user_id)
    if ai_key_record is None:
        raise ConfigError("用户尚未配置 AI Key，请在设置页面配置后再使用")

    plain_api_key = get_decrypted_key(ai_key_record)
    api_base_url = ai_key_record.api_base_url
    model_name = ai_key_record.model_name

    logger.info(
        "开始教案拆分流程",
        extra={"tenant_id": tenant_id, "user_id": user_id, "grade": grade},
    )

    # 2. 教案拆分
    split_result = await split_lesson_plan(
        raw_text=raw_text,
        api_base_url=api_base_url,
        api_key=plain_api_key,
        model_name=model_name,
        system_prompt=split_system_prompt,
        _client=_ai_client,
    )

    # 3. 年龄适配（对活动过程改写）
    original_process = split_result["activity_process"]
    adapted_process = await adapt_activity_process(
        original=original_process,
        grade=grade,
        api_base_url=api_base_url,
        api_key=plain_api_key,
        model_name=model_name,
        system_prompt=adapt_system_prompt,
        _client=_ai_client,
    )

    # 4. 差异比对
    diff_result = compute_diff(original_process, adapted_process)

    logger.info(
        "教案拆分流程完成",
        extra={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "diff_changed_count": sum(1 for d in diff_result if d["changed"]),
        },
    )

    return LessonPlanResult(
        activity_goal=split_result["activity_goal"],
        activity_prep=split_result["activity_prep"],
        activity_key=split_result["activity_key"],
        activity_difficult=split_result["activity_difficult"],
        activity_process_original=original_process,
        activity_process_adapted=adapted_process,
        diff_result=diff_result,
    )
