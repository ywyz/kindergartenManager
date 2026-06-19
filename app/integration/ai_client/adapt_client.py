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
- 小班（3-4岁）：适合幼儿年龄特征
- 中班（4-5岁）：适当增加探索环节，鼓励幼儿尝试，教师适时辅助
- 大班（5-6岁）：鼓励自主探索与合作，增加挑战性，教师以引导为主，
以上内容都需要详案即老师说的话，活动过程仅仅需要新增一个环节，以 JSON 格式输出，不要输出任何其他内容：

{
  "activity_goal": "活动目标（完整内容）",
  "activity_prep": "活动准备（完整内容）",
  "activity_key": "活动重点（完整内容）",
  "activity_difficult": "活动难点（完整内容）",
  "activity_process": "活动过程（完整内容，需要详案，包含老师说的话，但是不需要包含以上活动目标、活动准备、活动重点、活动难点，要按照教案格式，有换行。）"
}

要求：
1. 严格按照以上 JSON 格式输出，key 名称不得修改。
2. 若教案中某个字段明确缺失，对应 value 填写空字符串""。
3. 保留原活动目标、活动重点、活动难点内容，不要总结或改写，活动内容只需要新增或者改写一个环节，其余不变。
4. 输出必须是合法 JSON，不要添加 markdown 代码块标记（禁止 ```json 等包裹）。
5. 所有字段值必须是纯文本，禁止使用任何 markdown 格式标记（禁止 **加粗**、*斜体*、# 标题、- 列表前缀等）。
6. 步骤之间用句号结尾自然衔接，同时每一句都需要换行。使用"1."、"（1）"等数字编号前缀另起一行。
7. 不添加多余的空行或首行缩进。
8.活动过程格式如下：
一.......\n
     1......\n
      师:.....\n
     2......\n
      师:.....\n
     3......\n
二.......\n
     1....\n
     2....\n
三、四、五......"""


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
        # 兼容常见误配置：用户可能将拆分提示词的 schema 复制到适配 tab
        # 导致 AI 返回 activity_process 等非标准字段名，此处降级处理并记录警告
        for _fallback in ("activity_process", "adapted", "process", "content"):
            _val = result.get(_fallback)
            if isinstance(_val, str) and _val.strip():
                logger.warning(
                    "年龄适配提示词 schema 有误，使用了备用字段（建议到提示词管理页修正）",
                    extra={"fallback_key": _fallback, "result_keys": list(result.keys())},
                )
                adapted = _val
                if not isinstance(adapted, str):
                    adapted = str(adapted)
                logger.info("年龄适配成功（备用字段）", extra={"grade": grade, "length": len(adapted)})
                return adapted
        logger.info(
            "年龄适配结果缺少 adapted_process 字段",
            extra={"result_keys": list(result.keys())},
        )
        raise AiParseError(
            "年龄适配结果缺少 adapted_process 字段。"
            "请在【提示词管理 → 年龄适配】检查提示词，"
            "确保 JSON 输出包含 adapted_process 字段"
        )

    adapted = result["adapted_process"]
    if not isinstance(adapted, str):
        adapted = str(adapted)

    if not adapted.strip():
        raise AiParseError("年龄适配结果为空字符串")

    logger.info("年龄适配成功", extra={"grade": grade, "length": len(adapted)})
    return adapted
