"""年龄适配 AI 客户端。

将活动过程原文按年龄段（小班/中班/大班）改写，返回改写后文本。

输出 Schema：
    {"adapted_process": "改写后的活动过程文本"}

提示词优先级：
    1. 从 prompt_repository 获取当前激活版本（task_type="adapt"）
    2. 若无，使用内置默认 prompt（DEFAULT_ADAPT_PROMPT）
"""

from app.core.exceptions import AiParseError
from app.core.logging import get_logger
from app.integration.ai_client.base import call_ai

logger = get_logger(__name__)

# 内置默认适配提示词
DEFAULT_ADAPT_PROMPT = """你是一名经验丰富的幼儿园教研员，请将用户提供的活动过程根据指定年龄段进行适配改写。

改写要求：
- 小班（3-4岁）：语言简洁、操作简单、以教师引导为主，减少复杂步骤
- 中班（4-5岁）：适当增加探索环节，鼓励幼儿尝试，教师适时辅助
- 大班（5-6岁）：鼓励自主探索与合作，增加挑战性，教师以引导为主

输出格式（严格 JSON，不添加其他内容）：
{
  "adapted_process": "改写后的活动过程完整内容"
}

注意：
1. 保留原有活动步骤结构，仅调整语言难度和教师介入程度
2. 输出必须是合法 JSON
3. adapted_process 的值必须是字符串"""


async def adapt_activity_process(
    original: str,
    grade: str,
    api_base_url: str,
    api_key: str,
    model_name: str = "gpt-4o-mini",
    system_prompt: str | None = None,
    *,
    _client=None,
) -> str:
    """将活动过程按年龄段改写。

    Args:
        original: 活动过程原文。
        grade: 年龄段，如"小班"、"中班"、"大班"。
        api_base_url: AI 接口基地址。
        api_key: 明文 API Key。
        model_name: 模型名称。
        system_prompt: 自定义 system prompt；传 None 时使用内置默认。
        _client: 可选 httpx 客户端（测试用）。

    Returns:
        改写后的活动过程文本（字符串）。

    Raises:
        AiParseError: AI 返回内容缺少 adapted_process 字段或格式非法。
        AiCallError: AI 接口调用失败。
    """
    if not original.strip():
        raise AiParseError("活动过程原文不能为空")

    prompt = system_prompt if system_prompt is not None else DEFAULT_ADAPT_PROMPT

    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                f"年龄段：{grade}\n\n"
                f"活动过程原文：\n{original}\n\n"
                "请按以上年龄段改写活动过程，以 JSON 格式输出。"
            ),
        },
    ]

    result = await call_ai(
        messages=messages,
        api_base_url=api_base_url,
        api_key=api_key,
        model_name=model_name,
        _client=_client,
    )

    if "adapted_process" not in result:
        logger.info(
            "年龄适配结果缺少 adapted_process 字段",
            extra={"result_keys": list(result.keys())},
        )
        raise AiParseError("年龄适配结果缺少 adapted_process 字段")

    adapted = result["adapted_process"]
    if not isinstance(adapted, str):
        adapted = str(adapted)

    if not adapted.strip():
        raise AiParseError("年龄适配结果为空字符串")

    logger.info("年龄适配成功", extra={"grade": grade, "length": len(adapted)})
    return adapted
