"""一对一倾听单领域生成 AI 客户端。

针对某一领域（健康/语言/社会/艺术/科学），输入该领域 3 张幼儿绘画照片 +
班级信息 + 该领域二级指标清单，一次视觉调用输出结构化结果：
    goals               — 该领域观察目标（1~2 点）
    image_descriptions  — 每张图的描述（有字识别文字、无字描述绘画内容）
    indicators          — 各二级指标达成星级 [{"sort_order": int, "stars": 1~3}]
    evaluation          — 综合评价（约 200 字）
    support_strategy    — 支持策略（约 200 字）

提示词优先级：调用方传入 system_prompt（提示词管理激活版本）> 内置 DEFAULT_LISTENING_PROMPT。
"""

import base64

from app.core.exceptions import AiParseError, AppError
from app.core.logging import get_logger
from app.integration.ai_client.vision_base import call_ai_vision

logger = get_logger(__name__)

# 内置默认提示词（prompt_repository 无激活版本时使用）
DEFAULT_LISTENING_PROMPT = """\
你是一名专业幼儿园教研员，正在进行"一对一倾听"观察分析。请根据提供的幼儿绘画照片、班级信息与给定的二级指标，生成该领域的发展评价。

请严格按照以下 JSON 格式输出，不要输出任何其他内容：

{
  "goals": "该领域观察目标，1~2 点，纯文本",
  "image_descriptions": ["第1张图的内容", "第2张图的内容"],
  "indicators": [{"sort_order": 0, "stars": 3}, {"sort_order": 1, "stars": 2}],
  "evaluation": "综合评价，约200字",
  "support_strategy": "支持策略，约200字"
}

要求：
1. image_descriptions 数组长度必须与图片数量一致、顺序与图片一致。对每张图：先判断图上是否有文字，有文字则识别并返回文字内容；无文字或无法识别文字时，以幼儿园教育专家身份判断并描述绘画内容。
2. indicators 必须覆盖下方列出的全部二级指标，按 sort_order 标注；依据绘画内容评定 1~3 星；若绘画内容未涉及该指标，stars 默认填 3。
3. goals 给出该领域观察目标 1~2 点。
4. evaluation 与 support_strategy 各约 200 字。
5. 严格输出合法 JSON，key 名称不得修改，不要添加 markdown 代码块标记（禁止 ```json 等包裹）。
6. 所有字段值必须是纯文本，禁止使用任何 markdown 格式标记。"""

# 必须存在的字段列表
_REQUIRED_KEYS = [
    "goals",
    "image_descriptions",
    "indicators",
    "evaluation",
    "support_strategy",
]

# 图片格式 magic bytes 映射
_MIME_MAGIC: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),
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


def _build_context_text(context: dict, indicators: list[dict]) -> str:
    """构造给 AI 的说明文本（上下文 + 二级指标清单）。"""
    domain = context.get("domain", "")
    parts = [f'请完成"{domain}领域"的一对一倾听观察分析。']
    if grade := context.get("grade"):
        parts.append(f"年级：{grade}")
    if term := context.get("term"):
        parts.append(f"学期：{term}")
    if child_name := context.get("child_name"):
        parts.append(f"幼儿姓名：{child_name}")
    if child_age := context.get("child_age"):
        parts.append(f"幼儿年龄：{child_age}")

    parts.append("\n【待评定的二级指标】（请按 sort_order 对每个指标依据绘画评定 1~3 星，未涉及默认 3 星）：")
    for ind in indicators:
        so = ind.get("sort_order")
        level2 = ind.get("level2", "")
        parts.append(f"[{so}] {level2}")
        std = ind.get("standards") or {}
        if std.get("1"):
            parts.append(f"    ★: {std['1']}")
        if std.get("2"):
            parts.append(f"    ★★: {std['2']}")
        if std.get("3"):
            parts.append(f"    ★★★: {std['3']}")
    return "\n".join(parts)


async def generate_listening_domain(
    images: list[bytes],
    context: dict,
    indicators: list[dict],
    api_base_url: str,
    api_key: str,
    model_name: str = "gpt-4o",
    system_prompt: str | None = None,
    *,
    _client=None,
) -> dict:
    """调用视觉 AI 生成某领域的一对一倾听结构化内容。

    Args:
        images: 该领域绘画图片字节列表（经压缩后的 bytes，至少 1 张）。
        context: 上下文 dict（domain、grade、term、child_name、child_age）。
        indicators: 该领域二级指标清单 [{"sort_order", "level2", "standards": {"1","2","3"}}]。
        api_base_url: AI 接口基地址。
        api_key: 明文 API Key。
        model_name: 视觉模型名称。
        system_prompt: 系统提示词，优先级高于内置默认值。
        _client: 可选 httpx 客户端（测试用）。

    Returns:
        dict，含 goals / image_descriptions / indicators / evaluation / support_strategy。

    Raises:
        AppError: images 为空列表。
        AiParseError: 返回缺字段或 image_descriptions 数量与图片不符。
        AiCallError: HTTP 调用失败。
    """
    if not images:
        raise AppError("至少需要 1 张图片才能生成一对一倾听记录")

    prompt = system_prompt if system_prompt is not None else DEFAULT_LISTENING_PROMPT

    user_content: list[dict] = [
        {"type": "text", "text": _build_context_text(context, indicators)},
    ]
    for img_bytes in images:
        user_content.append(
            {"type": "image_url", "image_url": {"url": _image_to_data_url(img_bytes)}}
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
        logger.info("一对一倾听 AI 返回缺少必要字段", extra={"missing_keys": missing})
        raise AiParseError(f"一对一倾听 AI 返回缺少必要字段: {missing}")

    descriptions = result["image_descriptions"]
    if not isinstance(descriptions, list) or len(descriptions) != len(images):
        logger.info(
            "一对一倾听 AI 图片描述数量与图片不符",
            extra={"desc_count": len(descriptions) if isinstance(descriptions, list) else -1,
                   "image_count": len(images)},
        )
        raise AiParseError("一对一倾听 AI 返回的图片描述数量与图片数量不一致")

    if not isinstance(result["indicators"], list):
        raise AiParseError("一对一倾听 AI 返回的 indicators 不是数组")

    return {k: result[k] for k in _REQUIRED_KEYS}
