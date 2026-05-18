"""一日活动生成客户端 — 包含 5 种活动类型的内置默认提示词。

任务类型对应关系：
- morning_exercise  →  晨间活动
- morning_talk      →  晨间谈话
- area_game         →  区域游戏
- outdoor_game      →  户外游戏
- daily_reflection  →  一日活动反思
"""

from app.core.exceptions import AiParseError
from app.core.logging import get_logger
from app.integration.ai_client.base import call_ai_text

logger = get_logger(__name__)

# ── 晨间活动 ────────────────────────────────────────────────────────────────
DEFAULT_MORNING_EXERCISE_PROMPT: str = """\
你是幼儿园晨间活动设计专家。根据提供的班级信息和教案内容，设计一份晨间活动方案。

严格按照以下格式逐行输出，禁止任何 Markdown 标记（禁止 **加粗**、*斜体*、# 标题、- 列表前缀等）：

体能大循环：
集体游戏：（游戏名称）
自主游戏：（游戏名称）
重点指导：（集体游戏名称）/（自主游戏名称）（从两个游戏中任选一个）
活动目标：
1.（目标一）
2.（目标二）
3.（目标三）
指导要点：
1.（要点一）
2.（要点二）
3.（要点三）

输出约束：
1.禁止使用任何 Markdown 格式标记
2.活动目标和指导要点各写3条，每条单独一行，以"1.""2.""3."起头
3.重点指导格式固定为"集体游戏名称/自主游戏名称"，从两个游戏中任选一个
4.内容应符合幼儿年龄特点，紧扣体能发展与游戏趣味性
5.步骤之间不添加多余空行
"""

# ── 晨间谈话 ────────────────────────────────────────────────────────────────
DEFAULT_MORNING_TALK_PROMPT: str = """\
你是幼儿园晨间谈话设计专家。根据提供的班级信息和教案活动主题，设计一份晨间谈话方案。

严格按照以下格式逐行输出，禁止任何 Markdown 标记：

谈话主题：（主题）
问题设计：
1.（问题一）
2.（问题二）
3.（问题三）

输出约束：
1.禁止使用任何 Markdown 格式标记（禁止 **加粗**、# 标题、- 列表前缀等）
2.问题设计写3个，每条单独一行，以"1.""2.""3."起头
3.谈话主题应与当天教案活动主题紧密关联
4.问题由浅入深，能引导幼儿积极思考与表达
5.不添加多余空行
"""

# ── 区域游戏 ────────────────────────────────────────────────────────────────
DEFAULT_AREA_GAME_PROMPT: str = """\
你是幼儿园区域游戏设计专家。根据提供的班级区域信息和教案内容，设计一份区域游戏方案。
可供选择的游戏区域由用户在班级配置中填写，请从中任选两个。

严格按照以下格式逐行输出，禁止任何 Markdown 标记（禁止 **加粗**、*斜体*、# 标题、- 列表前缀等）：

游戏区域：（区域一） 、 （区域二）
重点指导：（区域一）/（区域二）（从两个区域中任选一个）
活动目标：
1.（目标一）
2.（目标二）
3.（目标三）
指导要点：
1.（要点一）
2.（要点二）
3.（要点三）

输出约束：
1.禁止使用任何 Markdown 格式标记
2.游戏区域从可用区域中选择两个，之间用" 、 "（空格、顿号、空格）分隔
3.重点指导从两个选定区域中任选一个，格式为"区域一/区域二"
4.活动目标和指导要点各写3条，每条单独一行，以"1.""2.""3."起头
5.不添加多余空行
"""

# ── 户外游戏 ────────────────────────────────────────────────────────────────
DEFAULT_OUTDOOR_GAME_PROMPT: str = """\
你是幼儿园户外游戏设计专家。根据提供的户外区域信息和教案内容，设计一份户外游戏方案。
可供选择的户外区域由用户在班级配置中填写，请从中任选两个。

严格按照以下格式逐行输出，禁止任何 Markdown 标记（禁止 **加粗**、*斜体*、# 标题、- 列表前缀等）：

游戏区域：（区域一） 、 （区域二）
重点指导：（区域一）/（区域二）（从两个区域中任选一个）
活动目标：
1.（目标一）
2.（目标二）
3.（目标三）
指导要点：
1.（要点一）
2.（要点二）
3.（要点三）

输出约束：
1.禁止使用任何 Markdown 格式标记
2.游戏区域从可用户外区域中选择两个，之间用" 、 "（空格、顿号、空格）分隔
3.重点指导从两个选定区域中任选一个，格式为"区域一/区域二"
4.活动目标和指导要点各写3条，每条单独一行，以"1.""2.""3."起头
5.不添加多余空行
"""

# ── 一日活动反思 ─────────────────────────────────────────────────────────────
DEFAULT_DAILY_REFLECTION_PROMPT: str = """\
你是幼儿园教学反思专家。根据今日开展的各项活动内容，撰写一日活动反思。

以自然段落形式书写，内容需涵盖以下三个方面：
一、今日亮点：哪些活动环节幼儿参与度高、效果好
二、存在问题：哪些环节需要改进，幼儿遇到了哪些困难
三、调整策略：下次活动如何改进

输出约束：
1.禁止使用任何 Markdown 格式标记（禁止 **加粗**、# 标题、- 列表前缀等）
2.以自然段落形式书写，不使用"一、二、三"等数字或标题标签单独成行
3.语言真实具体，结合当天活动实际情况
4.篇幅控制在100~200字之间
5.不添加多余空行
"""

# 任务类型 → 默认提示词 映射
GENERATE_DEFAULTS: dict[str, str] = {
    "morning_exercise": DEFAULT_MORNING_EXERCISE_PROMPT,
    "morning_talk": DEFAULT_MORNING_TALK_PROMPT,
    "area_game": DEFAULT_AREA_GAME_PROMPT,
    "outdoor_game": DEFAULT_OUTDOOR_GAME_PROMPT,
    "daily_reflection": DEFAULT_DAILY_REFLECTION_PROMPT,
}


def _build_user_content(task_type: str, context: dict) -> str:
    """根据任务类型和上下文构建发送给 AI 的用户消息。

    context 支持以下字段：
        grade, class_name, activity_goal, activity_process,
        indoor_areas, outdoor_content,
        morning_activity, morning_talk, indoor_area, outdoor_activity
        content (通用原始文本，用于测试模式)
    """
    # 通用原始文本（测试模式）
    if "content" in context:
        return context["content"]

    grade = context.get("grade", "")
    class_name = context.get("class_name", "")
    activity_goal = context.get("activity_goal", "")
    activity_process = context.get("activity_process", "")

    prefix = f"班级：{grade}{class_name}\n"

    if task_type == "morning_exercise":
        return (
            f"{prefix}"
            f"今日教案活动目标：{activity_goal or '（未填写）'}\n"
            f"今日活动过程：{activity_process or '（未填写）'}\n"
            "请设计今日晨间活动方案。"
        )
    if task_type == "morning_talk":
        return (
            f"{prefix}"
            f"今日教案活动目标：{activity_goal or '（未填写）'}\n"
            "请设计今日晨间谈话方案。"
        )
    if task_type == "area_game":
        indoor_areas = context.get("indoor_areas", "")
        return (
            f"{prefix}"
            f"可用室内游戏区域：{indoor_areas or '（未配置，请自行选择合适区域）'}\n"
            f"今日教案活动目标：{activity_goal or '（未填写）'}\n"
            f"今日活动过程：{activity_process or '（未填写）'}\n"
            "请设计今日区域游戏方案。"
        )
    if task_type == "outdoor_game":
        outdoor_content = context.get("outdoor_content", "")
        return (
            f"{prefix}"
            f"可用户外区域：{outdoor_content or '（未配置，请自行选择合适区域）'}\n"
            f"今日教案活动目标：{activity_goal or '（未填写）'}\n"
            "请设计今日户外游戏方案。"
        )
    if task_type == "daily_reflection":
        return (
            f"{prefix}"
            f"今日教案活动目标：{activity_goal or '（未填写）'}\n"
            f"晨间活动：{context.get('morning_activity', '') or '（未填写）'}\n"
            f"晨间谈话：{context.get('morning_talk', '') or '（未填写）'}\n"
            f"区域游戏：{context.get('indoor_area', '') or '（未填写）'}\n"
            f"户外游戏：{context.get('outdoor_activity', '') or '（未填写）'}\n"
            "请撰写今日一日活动反思。"
        )
    return f"{prefix}请根据以上信息生成内容。"


async def generate_activity(
    task_type: str,
    context: dict,
    api_base_url: str,
    api_key: str,
    model_name: str = "gpt-4o-mini",
    system_prompt: str | None = None,
    *,
    _client=None,
) -> str:
    """生成单项一日活动内容（纯文本输出）。

    Args:
        task_type: 任务类型（morning_exercise / morning_talk / area_game /
                   outdoor_game / daily_reflection）。
        context: 上下文信息 dict（grade、class_name、indoor_areas 等）。
        api_base_url / api_key / model_name: AI 接口参数。
        system_prompt: 自定义 system prompt；传 None 时使用对应内置默认。
        _client: 可选 httpx 客户端（测试用）。

    Returns:
        生成的活动内容文本字符串。

    Raises:
        AiParseError: 不支持的任务类型或返回内容为空。
        AiCallError: AI 接口调用失败。
    """
    prompt = system_prompt if system_prompt is not None else GENERATE_DEFAULTS.get(task_type)
    if not prompt:
        raise AiParseError(f"不支持的活动生成任务类型: {task_type}")

    user_content = _build_user_content(task_type, context)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_content},
    ]

    result = await call_ai_text(
        messages=messages,
        api_base_url=api_base_url,
        api_key=api_key,
        model_name=model_name,
        _client=_client,
    )
    logger.info("活动内容生成成功", extra={"task_type": task_type, "length": len(result)})
    return result
