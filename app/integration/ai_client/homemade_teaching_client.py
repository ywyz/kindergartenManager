"""自制教玩具 AI 客户端。"""

from app.core.exceptions import AiParseError
from app.core.logging import get_logger
from app.integration.ai_client.base import call_ai

logger = get_logger(__name__)

DEFAULT_HOMEMADE_TEACHING_PROMPT = """\
你是一名幼儿园自制教玩具设计专家。请根据教师提供的年级和班级信息，设计一份适合幼儿操作的自制教玩具方案。

请严格输出 JSON，不要输出任何其他内容：
{
  "toy_name": "教玩具名称",
  "materials": "所用材料",
  "play_methods": "玩法"
}

要求：
1. 教玩具名称简洁具体，适合填写到表格中。
2. 所用材料优先选择幼儿园常见、安全、低成本、易获得的材料。
3. 玩法需说明幼儿如何操作、可以发展的能力，以及教师支持要点。
4. 内容应符合当前年级幼儿年龄特点。
5. 禁止 Markdown 标记，禁止输出多余字段。
"""

_REQUIRED_KEYS = ("toy_name", "materials", "play_methods")


def _build_user_content(context: dict) -> str:
    grade = context.get("grade") or "未配置年级"
    class_name = context.get("class_name") or "未配置班级"
    teacher_name = context.get("teacher_name") or ""
    return (
        f"年级：{grade}\n"
        f"班级：{class_name}\n"
        f"教师姓名：{teacher_name or '未填写'}\n"
        "请生成一份自制教玩具方案。"
    )


async def generate_homemade_teaching(
    context: dict,
    api_base_url: str,
    api_key: str,
    model_name: str = "gpt-4o-mini",
    system_prompt: str | None = None,
    *,
    _client=None,
) -> dict[str, str]:
    """生成自制教玩具 JSON 内容。"""
    prompt = system_prompt if system_prompt is not None else DEFAULT_HOMEMADE_TEACHING_PROMPT
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
            "自制教玩具生成结果缺少必要字段",
            extra={"missing_keys": missing, "result_keys": list(result.keys())},
        )
        raise AiParseError(f"自制教玩具生成结果缺少必要字段: {missing}")

    normalized: dict[str, str] = {}
    empty_keys: list[str] = []
    for key in _REQUIRED_KEYS:
        value = result[key]
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        if not value:
            empty_keys.append(key)
        normalized[key] = value

    if empty_keys:
        logger.info("自制教玩具生成结果存在空字段", extra={"empty_keys": empty_keys})
        raise AiParseError(f"自制教玩具生成结果字段为空: {empty_keys}")

    logger.info("自制教玩具生成成功", extra={"keys": list(_REQUIRED_KEYS)})
    return normalized
