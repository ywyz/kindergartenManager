"""教案拆分 AI 客户端。

调用 OpenAI 兼容接口，将完整教案文本拆分为结构化字段。

输出 Schema（5 个必填键）：
    activity_goal      — 活动目标
    activity_prep      — 活动准备
    activity_key       — 活动重点
    activity_difficult — 活动难点
    activity_process   — 活动过程原文

提示词优先级：
    1. 从 prompt_repository 获取当前激活版本（task_type="split"）
    2. 若无，使用内置默认 prompt（DEFAULT_SPLIT_PROMPT）
"""

from app.core.exceptions import AiParseError
from app.core.logging import get_logger
from app.integration.ai_client.base import call_ai

logger = get_logger(__name__)

# 内置默认提示词（prompt_repository 无激活版本时使用）
DEFAULT_SPLIT_PROMPT = """你是一名专业幼儿园教研员，请将用户提供的完整教案文本拆分为以下5个结构化字段，\
以 JSON 格式输出，不要输出任何其他内容：

{
  "activity_goal": "活动目标（完整内容）",
  "activity_prep": "活动准备（完整内容）",
  "activity_key": "活动重点（完整内容）",
  "activity_difficult": "活动难点（完整内容）",
  "activity_process": "活动过程（完整内容，保留原文，需要按照教案格式，有换行。）"
}

要求：
1. 严格按照以上 JSON 格式输出，key 名称不得修改。
2. 若教案中某个字段明确缺失，对应 value 填写空字符串""。
3. 保留原文内容，不要总结或改写。
4. 输出必须是合法 JSON，不要添加 markdown 代码块标记（禁止 ```json 等包裹）。
5. 所有字段值必须是纯文本，禁止使用任何 markdown 格式标记（禁止 **加粗**、*斜体*、# 标题、- 列表前缀等）。
6. 步骤之间用句号结尾自然衔接，活动内容内每一句都需要另起一行。使用"1."、"（1）"等数字编号前缀另起一行。
7. 不添加多余的空行或首行缩进。
8. 如果没有给出教案活动重点和难点，请你根据内容撰写一点活动重点和活动难点。
9. 活动重点和难点需要根据教案内容撰写，不能没有内容或者直接写"无"。
"""

# 必须存在的字段列表
_REQUIRED_KEYS = [
    "activity_goal",
    "activity_prep",
    "activity_key",
    "activity_difficult",
    "activity_process",
]


async def split_lesson_plan(
    raw_text: str,
    api_base_url: str,
    api_key: str,
    model_name: str = "gpt-4o-mini",
    system_prompt: str | None = None,
    *,
    _client=None,
) -> dict:
    """将完整教案文本拆分为结构化字段。

    Args:
        raw_text: 用户粘贴的完整教案文本。
        api_base_url: AI 接口基地址。
        api_key: 明文 API Key。
        model_name: 模型名称。
        system_prompt: 自定义 system prompt；传 None 时使用内置默认。
        _client: 可选 httpx 客户端（测试用）。

    Returns:
        包含 5 个键的 dict：activity_goal / activity_prep /
        activity_key / activity_difficult / activity_process。

    Raises:
        AiParseError: AI 返回内容缺少必要字段或格式非法。
        AiCallError: AI 接口调用失败。
    """
    prompt = system_prompt if system_prompt is not None else DEFAULT_SPLIT_PROMPT

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"请拆分以下教案：\n\n{raw_text}"},
    ]

    result = await call_ai(
        messages=messages,
        api_base_url=api_base_url,
        api_key=api_key,
        model_name=model_name,
        _client=_client,
    )

    # 验证必要字段
    missing = [k for k in _REQUIRED_KEYS if k not in result]
    if missing:
        logger.info(
            "教案拆分结果缺少必要字段",
            extra={"missing_keys": missing, "result_keys": list(result.keys())},
        )
        raise AiParseError(f"教案拆分结果缺少必要字段: {missing}")

    # 确保所有值均为字符串
    for key in _REQUIRED_KEYS:
        if not isinstance(result[key], str):
            result[key] = str(result[key])

    logger.info("教案拆分成功", extra={"keys": _REQUIRED_KEYS})
    return {k: result[k] for k in _REQUIRED_KEYS}
