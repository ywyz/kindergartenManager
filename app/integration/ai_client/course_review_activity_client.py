"""课程审议 AI 客户端。"""

from app.core.exceptions import AiParseError
from app.core.logging import get_logger
from app.integration.ai_client.base import call_ai

logger = get_logger(__name__)

DEFAULT_COURSE_REVIEW_ACTIVITY_PROMPT = """\
你是一名幼儿园课程审议教研员。请根据教师提供的年龄段、活动信息和原始教案，完成课程审议记录。

请严格输出 JSON，不要输出任何其他内容：
{
  "activity_goal": "从原始教案中拆分出的活动目标",
  "activity_prep": "从原始教案中拆分出的活动准备",
  "activity_process": "从原始教案中拆分出的活动过程",
  "goal_adjusted": true,
  "goal_adjustment": "活动目标调整内容；不调整时为空字符串",
  "activity_goal_revised": "调整后的活动目标；不调整时保持原活动目标",
  "prep_adjusted": false,
  "prep_adjustment": "活动准备调整内容；不调整时为空字符串",
  "activity_prep_revised": "调整后的活动准备；不调整时保持原活动准备",
  "process_adjustment": "活动过程必须调整，请写清具体增加、删减或优化的环节",
  "activity_process_revised": "调整后的完整活动过程",
  "review_reason": "简要说明课程审议后调整的理由",
  "revised_lesson_plan": "完整二次修改稿"
}

要求：
1. 根据年龄段判断活动目标、活动准备是否需要调整；布尔字段必须输出 true 或 false。
2. 活动过程一定需要调整，process_adjustment 不得为空。
3. 若目标或准备有所调整，对应 adjustment 字段不得为空；若保持原设计，可为空字符串。
4. revised_lesson_plan 必须是一篇完整修改稿，包含活动名称、活动目标、活动准备、活动过程等内容。
5. 内容符合幼儿年龄特点和幼儿园课程审议表达习惯。
6. 禁止 Markdown 标记，禁止输出多余字段。
"""

_REQUIRED_STRING_KEYS = (
    "activity_goal",
    "activity_prep",
    "activity_process",
    "goal_adjustment",
    "activity_goal_revised",
    "prep_adjustment",
    "activity_prep_revised",
    "process_adjustment",
    "activity_process_revised",
    "review_reason",
    "revised_lesson_plan",
)
_REQUIRED_BOOL_KEYS = ("goal_adjusted", "prep_adjusted")
_REQUIRED_KEYS = _REQUIRED_STRING_KEYS + _REQUIRED_BOOL_KEYS
_NON_EMPTY_STRING_KEYS = (
    "activity_goal",
    "activity_prep",
    "activity_process",
    "activity_goal_revised",
    "activity_prep_revised",
    "process_adjustment",
    "activity_process_revised",
    "review_reason",
    "revised_lesson_plan",
)


def _build_user_content(context: dict) -> str:
    grade = context.get("grade") or "未配置年龄段"
    class_name = context.get("class_name") or "未配置班级"
    teacher_name = context.get("teacher_name") or "未填写"
    activity_name = context.get("activity_name") or "未填写活动名称"
    child_count = context.get("child_count") or "未填写"
    activity_time = context.get("activity_time") or "未填写"
    lesson_plan_original = context.get("lesson_plan_original") or ""

    return (
        f"年龄段：{grade}\n"
        f"班级名称：{class_name}\n"
        f"教师姓名：{teacher_name}\n"
        f"活动名称：{activity_name}\n"
        f"幼儿人数：{child_count}\n"
        f"活动时间：{activity_time}\n"
        "原始教案：\n"
        f"{lesson_plan_original}"
    )


async def generate_course_review_activity(
    context: dict,
    api_base_url: str,
    api_key: str,
    model_name: str = "gpt-4o-mini",
    system_prompt: str | None = None,
    *,
    _client=None,
) -> dict[str, object]:
    """生成课程审议 JSON 内容。"""
    prompt = (
        system_prompt
        if system_prompt is not None
        else DEFAULT_COURSE_REVIEW_ACTIVITY_PROMPT
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": _build_user_content(context)},
    ]

    result = await call_ai(
        messages=messages,
        api_base_url=api_base_url,
        api_key=api_key,
        model_name=model_name,
        _client=_client,
    )

    missing = [key for key in _REQUIRED_KEYS if key not in result]
    if missing:
        logger.info(
            "课程审议生成结果缺少必要字段",
            extra={"missing_keys": missing, "result_keys": list(result.keys())},
        )
        raise AiParseError(f"课程审议生成结果缺少必要字段: {missing}")

    normalized: dict[str, object] = {}
    empty_keys: list[str] = []
    for key in _REQUIRED_STRING_KEYS:
        value = result[key]
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        if key in _NON_EMPTY_STRING_KEYS and not value:
            empty_keys.append(key)
        normalized[key] = value

    bool_errors: list[str] = []
    for key in _REQUIRED_BOOL_KEYS:
        value = result[key]
        if not isinstance(value, bool):
            bool_errors.append(key)
        normalized[key] = value

    if bool_errors:
        logger.info("课程审议生成结果布尔字段类型错误", extra={"keys": bool_errors})
        raise AiParseError(f"课程审议生成结果布尔字段类型错误: {bool_errors}")

    if normalized["goal_adjusted"] and not normalized["goal_adjustment"]:
        empty_keys.append("goal_adjustment")
    if normalized["prep_adjusted"] and not normalized["prep_adjustment"]:
        empty_keys.append("prep_adjustment")

    if empty_keys:
        logger.info("课程审议生成结果存在空字段", extra={"empty_keys": empty_keys})
        raise AiParseError(f"课程审议生成结果字段为空: {empty_keys}")

    logger.info("课程审议生成成功", extra={"keys": list(_REQUIRED_KEYS)})
    return {key: normalized[key] for key in _REQUIRED_KEYS}
