"""游戏观察生成 AI 客户端。

调用 OpenAI 兼容多模态接口，输入 1~3 张游戏照片 + 元数据，
输出「观察目标 / 观察记录 / 评价分析 / 支持策略」四段内容。

输出 Schema（4 个必填键）：
    observation_goal     — 观察目标
    observation_record   — 观察记录
    evaluation_analysis  — 评价分析
    support_strategy     — 支持策略

提示词优先级：
    1. 调用方传入 system_prompt（来自 prompt_repository 激活版本）
    2. 若无，使用内置默认 DEFAULT_OBSERVATION_PROMPT

图片处理：
    - 图片字节转为 base64 data-url（data:image/jpeg;base64,...）
    - 支持 JPEG / PNG 格式（自动检测文件头）
    - 至少需要 1 张，最多 3 张；空列表抛 AppError
"""

import base64

from app.core.exceptions import AiParseError, AppError
from app.core.logging import get_logger
from app.integration.ai_client.vision_base import call_ai_vision

logger = get_logger(__name__)

# 内置默认提示词（prompt_repository 无激活版本时使用）
DEFAULT_OBSERVATION_PROMPT = """\
你是一名专业幼儿园教研员，请根据提供的游戏照片和班级信息，生成一份游戏观察记录。

请严格按照以下 JSON 格式输出，不要输出任何其他内容：

{
  "observation_goal": "观察目标（根据游戏情境描述观察的重点，2~3句话）",
  "observation_record": "观察记录（详细描述幼儿游戏过程中的行为表现，3~5句话）",
  "evaluation_analysis": "评价分析（分析幼儿在游戏中的发展水平和学习特点，2~3句话）",
  "support_strategy": "支持策略（提出具体的教师支持建议，2~3条）"
}

要求：
1. 严格按照以上 JSON 格式输出，key 名称不得修改。
2. 内容应基于照片中观察到的真实情况，结合幼儿年龄特点撰写。
3. 输出必须是合法 JSON，不要添加 markdown 代码块标记（禁止 ```json 等包裹）。
4. 所有字段值必须是纯文本，禁止使用任何 markdown 格式标记。
5. 内容客观、专业，符合幼儿教育理论。"""

# 必须存在的字段列表
_REQUIRED_KEYS = [
    "observation_goal",
    "observation_record",
    "evaluation_analysis",
    "support_strategy",
]

# 图片格式 magic bytes 映射
_MIME_MAGIC: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),  # RIFF....WEBP
]


def _detect_mime(image_bytes: bytes) -> str:
    """根据文件头检测图片 MIME 类型，无法识别时默认 image/jpeg。"""
    for magic, mime in _MIME_MAGIC:
        if image_bytes[:len(magic)] == magic:
            return mime
    return "image/jpeg"


def _image_to_data_url(image_bytes: bytes) -> str:
    """将图片字节转为 base64 data-url 字符串。"""
    mime = _detect_mime(image_bytes)
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime};base64,{b64}"


async def generate_observation(
    images: list[bytes],
    context: dict,
    api_base_url: str,
    api_key: str,
    model_name: str = "gpt-4o",
    system_prompt: str | None = None,
    *,
    _client=None,
) -> dict:
    """调用视觉 AI 生成游戏观察记录四段内容。

    Args:
        images: 图片字节列表（1~3 张，经压缩后的 bytes）。
        context: 上下文 dict，通常包含 grade（年龄段）、game_area（游戏区域）等。
        api_base_url: AI 接口基地址。
        api_key: 明文 API Key。
        model_name: 视觉模型名称（如 gpt-4o、qwen-vl-plus）。
        system_prompt: 系统提示词，优先级高于内置默认值。
        _client: 可选 httpx 客户端（测试用）。

    Returns:
        包含 observation_goal / observation_record / evaluation_analysis / support_strategy 的 dict。

    Raises:
        AppError: images 为空列表。
        AiParseError: AI 返回结果缺少必要字段。
        AiCallError: HTTP 调用失败。
    """
    if not images:
        raise AppError("至少需要 1 张图片才能生成游戏观察记录")

    prompt = system_prompt if system_prompt is not None else DEFAULT_OBSERVATION_PROMPT

    # 构造 user 消息的 content 列表（文本 + 图片）
    context_text = _build_context_text(context)
    user_content: list[dict] = [
        {"type": "text", "text": context_text},
    ]

    for img_bytes in images:
        data_url = _image_to_data_url(img_bytes)
        user_content.append(
            {"type": "image_url", "image_url": {"url": data_url}}
        )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_content},
    ]

    result = await call_ai_vision(
        messages=messages,
        api_base_url=api_base_url,
        api_key=api_key,
        model_name=model_name,
        _client=_client,
    )

    # 校验必要字段
    missing = [k for k in _REQUIRED_KEYS if k not in result or result[k] is None]
    if missing:
        logger.info(
            "游戏观察 AI 返回结果缺少必要字段",
            extra={"missing_keys": missing},
        )
        raise AiParseError(f"游戏观察 AI 返回结果缺少必要字段: {missing}")

    return {k: result[k] for k in _REQUIRED_KEYS}


def _build_context_text(context: dict) -> str:
    """将上下文 dict 转为给 AI 的说明文本。"""
    parts = ["请根据以下图片和班级信息生成游戏观察记录："]
    if grade := context.get("grade"):
        parts.append(f"年龄段/年级：{grade}")
    if game_area := context.get("game_area"):
        parts.append(f"游戏区域：{game_area}")
    if big_env := context.get("big_env"):
        parts.append(f"游戏大环境：{big_env}")
    if child_names := context.get("child_names"):
        parts.append(f"观察幼儿：{child_names}")
    if child_age := context.get("child_age"):
        parts.append(f"幼儿年龄：{child_age}")
    return "\n".join(parts)
