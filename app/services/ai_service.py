"""AI 服务封装 - 使用 openai 库连接兼容接口，含调用日志与多配置负载均衡"""
import json
import logging
import random
import re
import threading
import time
from typing import Optional

from openai import OpenAI

from app.db import execute_one, execute_query

# 轮询负载均衡计数器（模块级，进程内持久）
_rr_counter = [0]
_rr_lock = threading.Lock()

logger = logging.getLogger(__name__)


def _diversity_hint() -> str:
    """生成一段不影响主题的随机化提示，用于打破缓存与提高输出多样性。"""
    seed = random.randint(10000, 99999)
    ts = int(time.time())
    return (
        f"\n\n[多样性要求] 请避免与常见示例雷同，给出有新意的方案。"
        f"（随机种子：{seed}-{ts}，仅用于打破缓存，无需出现在输出中）"
    )


# ---------------------------------------------------------------------------
# 内置默认提示词
# ---------------------------------------------------------------------------

_DEFAULT_PROMPTS: dict[str, str] = {
    "lesson_split": (
        "你是一位专业的幼儿园教育专家。请将以下完整教案拆分为结构化的JSON格式，"
        "键名必须严格使用以下英文（不要使用中文键名）：\n"
        "- theme: 活动主题（短句）\n"
        "- goal: 活动目标（用换行或编号写在同一字符串里）\n"
        "- preparation: 活动准备\n"
        "- key_point: 活动重点\n"
        "- difficulty: 活动难点\n"
        "- process: 活动过程（保留所有环节、步骤、教师语言、幼儿反应等细节，"
        "尽量完整，不要省略；用换行分段，不要嵌套 JSON）\n"
        "只返回合法的JSON对象，不要添加任何解释或代码块标记。\n\n"
        "教案内容：\n{content}"
    ),
    "process_modify": (
        "你是一位专业的幼儿园教育专家。下面提供的是【一段“活动过程”纯文本】，"
        "不是 JSON。请根据{grade}幼儿的年龄特点和发展水平，对其进行【最小化】优化。\n"
        "【修改范围 · 必须严格遵守】\n"
        "1. 只允许从下面两种方式中【二选一】操作：\n"
        "   A. 修改原文中【某一个环节】的内容（仅改这一个环节，其他环节一字不动、原样保留）；\n"
        "   B. 在原有环节之间或末尾【新增一个环节】（其他原有环节一字不动、原样保留）。\n"
        "2. 严禁同时修改多个环节，严禁对未选中的环节做任何改写、润色、合并或调整顺序。\n"
        "3. 必须保留原文所有未改动环节的【原始文字、标点、序号、分段】，不可重写。\n"
        "4. 仅在你新增或修改的那个环节末尾追加【AI修改】标记，方便对比；其他环节绝不能出现该标记。\n"
        "【输出要求 · 必须严格遵守】\n"
        "1. 只输出修改后的【活动过程纯文本】（包含所有未改动的原环节 + 你修改/新增的那一个环节）。\n"
        "2. 禁止输出 JSON、键值对、Markdown 代码块、```、{ } 等结构化符号。\n"
        "3. 禁止输出“活动主题/活动目标/活动准备/活动重点/活动难点”等其它字段，"
        "只输出活动过程本身。\n\n"
        "原始活动过程：\n{content}"
    ),
    "morning_activity": (
        "你是一位专业的幼儿园教育专家。请为{grade}{class_name}设计一份晨间活动方案。\n"
        "当前是第{week}周，{day}。\n"
        "户外体育器材与场地内容：{outdoor_content}\n"
        "请生成以下JSON格式的晨间活动内容（必须包含一个集体活动和一个自选活动，"
        "并从中挑选一个作为重点指导对象）：\n"
        "{{\n"
        "  \"group_activity_name\": \"集体活动名称（一个具体的活动名）\",\n"
        "  \"self_selected_name\": \"自选活动名称（一个具体的活动名）\",\n"
        "  \"key_guidance\": \"重点指导名称（必须是上面两个活动之一）\",\n"
        "  \"activity_goal\": \"活动目标（2-3条）\",\n"
        "  \"guidance_points\": \"指导要点（2-3点）\"\n"
        "}}\n"
        "只返回合法的JSON对象。"
    ),
    "morning_talk": (
        "你是一位专业的幼儿园教育专家。请为{grade}{class_name}设计一段晨间谈话方案。\n"
        "当前是第{week}周，{day}。{holiday_tip}\n"
        "请生成以下JSON格式的晨间谈话内容：\n"
        "{{\n"
        "  \"topic\": \"谈话主题\",\n"
        "  \"questions\": \"问题设计（3-5个开放性问题）\"\n"
        "}}\n"
        "只返回合法的JSON对象。"
    ),
    "indoor_area": (
        "你是一位专业的幼儿园教育专家。请为{grade}{class_name}设计一份室内区域活动方案。\n"
        "当前班级的区域游戏内容设置为：{area_content}\n"
        "请生成以下JSON格式的室内区域活动内容：\n"
        "{{\n"
        "  \"game_area\": \"游戏区域名称\",\n"
        "  \"key_guidance\": \"重点指导内容\",\n"
        "  \"activity_goal\": \"活动目标（2-3条）\",\n"
        "  \"guidance_points\": \"指导要点\",\n"
        "  \"support_strategy\": \"教师支持策略（2-3点）\"\n"
        "}}\n"
        "只返回合法的JSON对象。"
    ),
    "outdoor_game": (
        "你是一位专业的幼儿园教育专家。请为{grade}{class_name}设计一份户外游戏活动方案。\n"
        "当前班级的户外游戏内容为：{outdoor_content}\n"
        "请生成以下JSON格式的户外游戏活动内容：\n"
        "{{\n"
        "  \"game_area\": \"游戏场地/区域\",\n"
        "  \"key_guidance\": \"重点指导内容\",\n"
        "  \"activity_goal\": \"活动目标（2-3条）\",\n"
        "  \"guidance_points\": \"指导要点\",\n"
        "  \"support_strategy\": \"教师支持策略（2-3点）\"\n"
        "}}\n"
        "只返回合法的JSON对象。"
    ),
    "weekly_morning_talk": (
        "你是一位专业的幼儿园教育专家。请为{grade}{class_name}设计{day}（{date}）的晨间谈话方案。\n"
        "当前是第{week}周，本周活动主题：{theme}。\n"
        "请围绕本周主题设计晨间谈话，生成以下JSON格式内容：\n"
        "{{\n"
        "  \"topic\": \"谈话主题（与本周主题呼应）\",\n"
        "  \"questions\": \"问题设计（3-5个开放性问题，用换行分隔）\"\n"
        "}}\n"
        "只返回合法的JSON对象。"
    ),
    "weekly_outdoor_game": (
        "你是一位专业的幼儿园教育专家。请为{grade}{class_name}设计{day}（{date}）的户外游戏方案。\n"
        "当前是第{week}周，本周活动主题：{theme}。\n"
        "户外体育器材与场地内容：{outdoor_content}\n"
        "请生成以下JSON格式的户外游戏内容（包含体能大循环、集体游戏、自主游戏三部分）：\n"
        "{{\n"
        "  \"outdoor_game_circuit\": \"体能大循环内容（简要描述）\",\n"
        "  \"outdoor_game_group\": \"集体游戏名称及玩法（2-3句）\",\n"
        "  \"outdoor_game_free\": \"自主游戏内容（2-3句）\"\n"
        "}}\n"
        "只返回合法的JSON对象。"
    ),
    "weekly_area_game": (
        "你是一位专业的幼儿园教育专家。请为{grade}{class_name}设计{day}（{date}）的区域游戏方案。\n"
        "当前是第{week}周，本周活动主题：{theme}。\n"
        "当前班级区域游戏内容设置为：{area_content}\n"
        "请生成以下JSON格式的区域游戏内容：\n"
        "{{\n"
        "  \"area_game_zone\": \"重点指导区域名称\",\n"
        "  \"area_game_goal\": \"活动目标（2-3条）\",\n"
        "  \"area_game_materials\": \"区域材料\",\n"
        "  \"area_game_guidance\": \"区域指导要点（2-3点）\"\n"
        "}}\n"
        "只返回合法的JSON对象。"
    ),
    "weekly_summary": (
        "你是一位专业的幼儿园教育专家。请为{grade}{class_name}制定第{week}周的教育教学要点。\n"
        "本周活动主题：{theme}\n"
        "请生成以下JSON格式的周级汇总内容：\n"
        "{{\n"
        "  \"week_focus\": \"本周重点（3条，每条换行）\",\n"
        "  \"env_setup\": \"环境创设（2-3条具体布置建议，换行分隔）\",\n"
        "  \"life_habits\": \"生活习惯培养（2-3条，换行分隔）\",\n"
        "  \"home_school\": \"家园共育建议（2-3条，换行分隔）\"\n"
        "}}\n"
        "只返回合法的JSON对象。"
    ),
}


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _get_active_prompt(category: str) -> str:
    """从数据库获取激活的提示词，若无则使用默认"""
    try:
        row = execute_one(
            "SELECT prompt_content FROM prompts WHERE prompt_category = %s AND is_active = 1 LIMIT 1",
            (category,),
        )
        if row and row.get("prompt_content"):
            return row["prompt_content"]
    except Exception:
        pass
    return _DEFAULT_PROMPTS.get(category, "")


def _get_ai_params() -> dict:
    """从 app_settings 读取用户配置的 AI 生成参数"""
    defaults = {"temperature": 0.95, "top_p": 0.95, "frequency_penalty": 0.3}
    keys_map = {
        "ai_temperature": "temperature",
        "ai_top_p": "top_p",
        "ai_frequency_penalty": "frequency_penalty",
    }
    try:
        for setting_key, param_name in keys_map.items():
            row = execute_one(
                "SELECT setting_val FROM app_settings WHERE setting_key = %s",
                (setting_key,),
            )
            if row and row.get("setting_val"):
                defaults[param_name] = float(row["setting_val"])
    except Exception:
        pass
    return defaults


def _build_client(api_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=api_url, api_key=api_key)


def _extract_json(text: str) -> dict | list:
    """从模型响应中提取 JSON（容错多种包裹格式）"""
    if text is None:
        raise ValueError("AI 返回为空")
    raw = text.strip()
    # 1) 如果存在 ``` 包裹代码块，取出其中的 JSON 部分
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    if fence:
        candidate = fence.group(1).strip()
    else:
        # 2) 否则提取从第一个 { 或 [ 到最后一个 } 或 ] 的范围
        m = re.search(r"[\{\[][\s\S]*[\}\]]", raw)
        candidate = m.group(0) if m else raw
    return json.loads(candidate)


# 中文 key -> 英文 key 映射（按业务字段汇总，重名安全）
_KEY_ALIASES: dict[str, str] = {
    # 晨间活动专用
    "集体活动名称": "group_activity_name",
    "集体活动": "group_activity_name",
    "集体游戏": "group_activity_name",
    "集体游戏名称": "group_activity_name",
    "自选活动名称": "self_selected_name",
    "自选活动": "self_selected_name",
    "自主游戏": "self_selected_name",
    "自主游戏名称": "self_selected_name",
    "自选游戏": "self_selected_name",
    "重点指导名称": "key_guidance",
    # 通用
    "活动类型": "activity_type",
    "活动目标": "activity_goal",
    "重点指导": "key_guidance",
    "重点指导内容": "key_guidance",
    "指导要点": "guidance_points",
    "支持策略": "support_strategy",
    "教师支持策略": "support_strategy",
    "游戏区域": "game_area",
    "游戏场地": "game_area",
    "游戏场地/区域": "game_area",
    "区域": "game_area",
    "谈话主题": "topic",
    "主题": "topic",
    "问题设计": "questions",
    "问题": "questions",
    # 教案拆分
    "活动主题": "theme",
    "活动准备": "preparation",
    "准备": "preparation",
    "活动重点": "key_point",
    "重点": "key_point",
    "活动难点": "difficulty",
    "难点": "difficulty",
    "活动过程": "process",
    "过程": "process",
    "目标": "goal",
}


def _normalize_keys(obj):
    """递归把中文 key 转换为约定的英文 key；list/value 中的字符串保持原样"""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            new_k = _KEY_ALIASES.get(str(k).strip(), k)
            result[new_k] = _normalize_keys(v)
        return result
    if isinstance(obj, list):
        return [_normalize_keys(x) for x in obj]
    return obj


# 业务上每类生成结果都是“扁平字段”，但模型可能多套一层 wrapper（如 {"result": {...}}
# 或 {"晨间活动": {...}}）。若顶层只有 1 个 key 且其值是 dict，则解包一层。
_KNOWN_FIELDS = {
    "activity_type", "activity_goal", "key_guidance", "guidance_points",
    "support_strategy", "game_area", "topic", "questions",
    "theme", "goal", "preparation", "key_point", "difficulty", "process",
    "group_activity_name", "self_selected_name",
}


def _unwrap_if_needed(data):
    """若顶层是 wrapper（无任何已知字段），尝试解包内部 dict。"""
    if not isinstance(data, dict):
        return data
    if any(k in _KNOWN_FIELDS for k in data.keys()):
        return data
    # 顶层只有一个键，且值是 dict 时解包
    if len(data) == 1:
        only_value = next(iter(data.values()))
        if isinstance(only_value, dict):
            return only_value
    return data


def _parse_json_response(raw: str) -> dict:
    """统一的解析入口：提取 -> 归一化 key -> 解包 wrapper，并打日志便于排查。"""
    logger.info("AI raw response: %s", (raw or "")[:1000])
    data = _extract_json(raw)
    data = _normalize_keys(data)
    data = _unwrap_if_needed(data)
    logger.info("AI parsed result: %s", data)
    return data


def _strip_to_process_text(raw: str) -> str:
    """
    process_modify 兜底：若模型违规返回 JSON 或包含代码块，
    尽量提取出 process 字段的纯文本；否则原样返回。
    """
    if not raw:
        return ""
    text = raw.strip()
    # 去掉 ```json ... ``` 或 ``` ... ``` 包裹
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    # 看起来像 JSON：尝试解析并取出 process 字段
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                data = _normalize_keys(data)
                for key in ("process", "activity_process"):
                    if key in data and isinstance(data[key], str):
                        return data[key].strip()
                # 拿不到 process 时，把所有字符串值拼接，避免完全丢内容
                texts = [v for v in data.values() if isinstance(v, str)]
                if texts:
                    return "\n".join(texts).strip()
        except json.JSONDecodeError:
            pass
    return text


def _build_anti_repeat_hint(category: str, grade: str, class_name: str, limit: int = 5) -> str:
    """
    读取近期同年级同班级的已保存内容，构造“避免重复”提示。
    若数据库不可用或无历史数据，则返回空字符串。
    """
    if not grade or not class_name:
        return ""

    category_to_column = {
        "morning_activity": "morning_activity_json",
        "morning_talk": "morning_talk_json",
        "indoor_area": "indoor_area_json",
        "outdoor_game": "outdoor_game_json",
    }
    col = category_to_column.get(category)
    if not col:
        return ""

    try:
        rows = execute_query(
            f"SELECT {col} AS payload FROM daily_plans "
            "WHERE grade=%s AND class_name=%s "
            "ORDER BY plan_date DESC, id DESC LIMIT %s",
            (grade, class_name, limit),
        )
    except Exception:
        return ""

    examples: list[str] = []
    for row in rows:
        payload = row.get("payload")
        if not payload:
            continue
        try:
            data = json.loads(payload) if isinstance(payload, str) else payload
            data = _normalize_keys(data) if isinstance(data, dict) else {}
        except Exception:
            continue

        if category == "morning_activity":
            a = (data.get("group_activity_name") or "").strip()
            b = (data.get("self_selected_name") or "").strip()
            item = f"集体:{a} / 自选:{b}".strip(" /")
        elif category == "morning_talk":
            item = (data.get("topic") or "").strip()
        else:
            area = (data.get("game_area") or "").strip()
            guidance = (data.get("key_guidance") or "").strip()
            if len(guidance) > 18:
                guidance = guidance[:18] + "..."
            item = f"区域:{area} / 指导:{guidance}".strip(" /")

        if item and item not in examples:
            examples.append(item)

    if not examples:
        return ""

    lines = "\n".join(f"- {x}" for x in examples[:limit])
    return (
        "\n\n[避免重复要求] 请避免与以下近期已使用内容重复，可借鉴主题方向但不要复用相同活动名/谈话主题/区域组合：\n"
        + lines
    )


def _chat(client: OpenAI, model: str, system_msg: str, user_msg: str,
          temperature: float = 0.7, top_p: float = 1.0,
          frequency_penalty: float = 0.0, max_retries: int = 2,
          json_mode: bool = False, category: str = "") -> str:
    """发送对话请求，带简单重试与调用日志。json_mode=True 时尝试启用 OpenAI JSON 模式。"""
    from app.db import log_ai_call
    last_err = None
    _start = time.time()
    for attempt in range(max_retries + 1):
        try:
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": temperature,
                "top_p": top_p,
                "frequency_penalty": frequency_penalty,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            try:
                response = client.chat.completions.create(**kwargs)
            except Exception as e:
                # 部分兼容网关不支持 response_format，回退一次
                if json_mode and "response_format" in str(e):
                    kwargs.pop("response_format", None)
                    response = client.chat.completions.create(**kwargs)
                else:
                    raise
            raw = response.choices[0].message.content or ""
            log_ai_call(
                category=category, model_name=model,
                prompt_text=user_msg, response_text=raw,
                status="success", duration_ms=int((time.time() - _start) * 1000),
            )
            return raw
        except Exception as e:
            last_err = e
            if attempt == max_retries:
                log_ai_call(
                    category=category, model_name=model,
                    prompt_text=user_msg, response_text="",
                    status="error", error_msg=str(e),
                    duration_ms=int((time.time() - _start) * 1000),
                )
                raise RuntimeError(f"AI调用失败（已重试{max_retries}次）：{e}") from e
    raise RuntimeError(f"AI调用失败：{last_err}")


# 强制 JSON 输出的统一格式约束（追加到 user prompt 末尾）
_JSON_FORMAT_RULES = (
    "\n\n【输出格式硬性要求 · 必须遵守】\n"
    "1. 只输出一个合法的 JSON 对象，不要任何多余说明、前后缀或 ``` 代码块标记。\n"
    "2. 所有键名和字符串值必须使用英文双引号 \"\"。\n"
    "3. 任意字段如有多项内容，必须写在【同一个字符串】内（用换行或编号），"
    "禁止把多项内容拆成顶层键的并列字符串（例如 \"key\": \"a\", \"b\" 是非法的）。\n"
    "4. 字符串内的换行用 \\n，禁止出现裸换行；禁止使用注释。\n"
    "5. 不要输出键模板里没有列出的额外键。"
)


def _call_json(client: OpenAI, model: str, system_msg: str, user_msg: str,
               temperature: float = 0.9, top_p: float = 1.0,
               frequency_penalty: float = 0.0, category: str = "") -> dict:
    """
    通用 JSON 生成调用：自动追加格式约束、启用 JSON 模式、解析失败时让模型自我修正。
    """
    full_user = user_msg + _JSON_FORMAT_RULES
    last_raw = ""
    last_err: Optional[Exception] = None
    # 第一次正常调用 + 最多 2 次"修复"重试
    for attempt in range(3):
        if attempt == 0:
            raw = _chat(client, model, system_msg, full_user,
                        temperature=temperature, top_p=top_p,
                        frequency_penalty=frequency_penalty, json_mode=True,
                        category=category)
        else:
            repair_prompt = (
                "你上一次的输出不是合法 JSON，错误信息：\n"
                f"{last_err}\n\n"
                "你上次输出的原始内容如下（截取前 1500 字符）：\n"
                f"{last_raw[:1500]}\n\n"
                "请严格按要求重新输出修正后的合法 JSON 对象，"
                "只输出 JSON 本身，不要任何解释。"
                + _JSON_FORMAT_RULES
            )
            raw = _chat(client, model, system_msg, repair_prompt,
                        temperature=0.2, json_mode=True,
                        category=f"{category}_repair")
        last_raw = raw
        try:
            return _parse_json_response(raw)
        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
            logger.warning("JSON 解析失败（尝试 %d/3）：%s", attempt + 1, e)
            continue
    raise ValueError(
        f"AI 多次返回的 JSON 仍无法解析：{last_err}\n原始内容：{last_raw[:500]}"
    )


# ---------------------------------------------------------------------------
# 对外 AI 服务方法
# ---------------------------------------------------------------------------

class AIService:
    """AI 服务，支持传入自定义 api_url/api_key/model"""

    def __init__(self, api_url: str, api_key: str, model: str):
        self.client = _build_client(api_url, api_key)
        self.model = model
        self._params = _get_ai_params()  # 用户配置的温度等参数

    # ---- 教案拆分 ----

    def split_lesson_plan(self, text: str, grade: str = "") -> dict:
        """
        拆分教案为结构化 JSON。
        返回：{theme, goal, preparation, key_point, difficulty, process}
        """
        prompt_tpl = _get_active_prompt("lesson_split")
        prompt = prompt_tpl.format(content=text, grade=grade)
        result = _call_json(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长教案分析与整理。",
            user_msg=prompt,
            temperature=0.3,
            category="lesson_split",
        )
        # 教案场景专属归一化：模型常把目标/主题写成"活动目标/活动主题"，
        # 全局别名会归到 activity_goal/activity_theme，这里再回退一次到 goal/theme。
        lesson_remap = {
            "activity_goal": "goal",
            "activity_theme": "theme",
            "activity_preparation": "preparation",
            "activity_key_point": "key_point",
            "activity_difficulty": "difficulty",
            "activity_process": "process",
        }
        for src, dst in lesson_remap.items():
            if src in result and dst not in result:
                result[dst] = result.pop(src)
        return result

    # ---- 活动过程修改 ----

    def modify_activity_process(self, original_process: str, grade: str) -> str:
        """根据年龄段修改活动过程，返回修改后文本，AI修改部分标注【AI修改】。
        若模型违规返回 JSON，将自动剥离仅保留 process 字段文本。
        """
        prompt_tpl = _get_active_prompt("process_modify")
        prompt = prompt_tpl.format(content=original_process, grade=grade)
        raw = _chat(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长根据年龄特点优化教学活动。"
                       "你只输出活动过程纯文本，绝不输出 JSON。",
            user_msg=prompt,
            temperature=0.5,
            category="process_modify",
        )
        return _strip_to_process_text(raw)

    # ---- 晨间活动生成 ----

    def generate_morning_activity(
        self, week: int, day: str, grade: str, class_name: str, outdoor_content: str
    ) -> dict:
        """生成晨间活动内容"""
        prompt_tpl = _get_active_prompt("morning_activity")
        prompt = prompt_tpl.format(
            week=week, day=day, grade=grade,
            class_name=class_name, outdoor_content=outdoor_content,
        )
        anti_repeat = _build_anti_repeat_hint("morning_activity", grade, class_name)
        return _call_json(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长设计晨间活动。每次生成请尽量提供不同的活动名称与内容，避免重复。",
            user_msg=prompt + _diversity_hint() + anti_repeat,
            temperature=self._params["temperature"],
            top_p=self._params["top_p"],
            frequency_penalty=self._params["frequency_penalty"],
            category="morning_activity",
        )

    # ---- 晨间谈话生成 ----

    def generate_morning_talk(
        self, week: int, day: str, grade: str, class_name: str,
        near_holiday: bool = False
    ) -> dict:
        """生成晨间谈话内容"""
        prompt_tpl = _get_active_prompt("morning_talk")
        holiday_tip = "（注意：近期有法定节假日，谈话内容可结合节日主题）" if near_holiday else ""
        prompt = prompt_tpl.format(
            week=week, day=day, grade=grade,
            class_name=class_name, holiday_tip=holiday_tip,
        )
        anti_repeat = _build_anti_repeat_hint("morning_talk", grade, class_name)
        return _call_json(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长设计晨间谈话。每次请选择不同主题，避免重复。",
            user_msg=prompt + _diversity_hint() + anti_repeat,
            temperature=self._params["temperature"],
            top_p=self._params["top_p"],
            frequency_penalty=self._params["frequency_penalty"],
            category="morning_talk",
        )

    # ---- 室内区域活动生成 ----

    def generate_indoor_area(
        self, grade: str, class_name: str, area_content: str
    ) -> dict:
        """生成室内区域活动内容"""
        prompt_tpl = _get_active_prompt("indoor_area")
        prompt = prompt_tpl.format(grade=grade, class_name=class_name, area_content=area_content)
        anti_repeat = _build_anti_repeat_hint("indoor_area", grade, class_name)
        return _call_json(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长设计区域游戏活动。每次请从可选区域中选择不同区域，提供多样化的内容。",
            user_msg=prompt + _diversity_hint() + anti_repeat,
            temperature=self._params["temperature"],
            top_p=self._params["top_p"],
            frequency_penalty=self._params["frequency_penalty"],
            category="indoor_area",
        )

    # ---- 户外游戏活动生成 ----

    def generate_outdoor_game(
        self, grade: str, class_name: str, outdoor_content: str
    ) -> dict:
        """生成户外游戏活动内容"""
        prompt_tpl = _get_active_prompt("outdoor_game")
        prompt = prompt_tpl.format(
            grade=grade, class_name=class_name, outdoor_content=outdoor_content
        )
        anti_repeat = _build_anti_repeat_hint("outdoor_game", grade, class_name)
        return _call_json(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长设计户外游戏活动。每次请提供不同场地、不同玩法的方案，避免重复。",
            user_msg=prompt + _diversity_hint() + anti_repeat,
            temperature=self._params["temperature"],
            top_p=self._params["top_p"],
            frequency_penalty=self._params["frequency_penalty"],
            category="outdoor_game",
        )

    # ---- 提示词测试 ----

    def test_prompt(self, prompt_content: str, test_input: str) -> str:
        """测试任意提示词，返回AI响应原始文本"""
        return _chat(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家。",
            user_msg=prompt_content.replace("{content}", test_input),
            category="prompt_test",
        )

    # ---- 一日活动反思生成 ----

    def generate_daily_reflection(self, plan_summary: str, grade: str, class_name: str) -> str:
        """根据当日活动内容生成一日活动反思，返回纯文本。"""
        prompt = (
            f"你是一位专业的幼儿园教育专家。请根据以下{grade}{class_name}的一日活动内容，"
            "撰写一份简洁的一日活动反思（200-400字），包含：\n"
            "1. 今日活动亮点与幼儿表现\n"
            "2. 存在的问题或需改进之处\n"
            "3. 后续调整方向\n\n"
            "请直接输出反思文本，不要输出 JSON 或其他格式。\n\n"
            f"今日活动内容概要：\n{plan_summary}"
        )
        return _chat(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长撰写教学反思。",
            user_msg=prompt,
            temperature=self._params["temperature"],
            top_p=self._params["top_p"],
            frequency_penalty=self._params["frequency_penalty"],
            category="daily_reflection",
        )


    # ---- 周计划：整周批量生成晨间谈话 ----

    def generate_weekly_morning_talks(
        self, week: int, grade: str, class_name: str, theme: str,
        day_infos: list[dict],
    ) -> list[dict]:
        """
        批量生成一周5天的晨间谈话。
        day_infos: [{"date_str": "2026-05-06", "day_of_week": "周一", "is_holiday": False}, ...]
        返回: [{"topic": ..., "questions": ...}, ...] 5个元素，放假天返回空dict
        """
        prompt_tpl = _get_active_prompt("weekly_morning_talk")
        results = []
        for day_info in day_infos:
            if day_info.get("is_holiday"):
                results.append({"topic": "", "questions": ""})
                continue
            prompt = prompt_tpl.format(
                week=week,
                day=day_info["day_of_week"],
                date=day_info["date_str"],
                grade=grade,
                class_name=class_name,
                theme=theme,
            )
            try:
                r = _call_json(
                    self.client, self.model,
                    system_msg="你是专业的幼儿园教育专家，擅长设计晨间谈话。",
                    user_msg=prompt + _diversity_hint(),
                    temperature=self._params["temperature"],
                    top_p=self._params["top_p"],
                    frequency_penalty=self._params["frequency_penalty"],
                    category="weekly_morning_talk",
                )
                results.append(r)
            except Exception as e:
                logger.warning("周晨间谈话生成失败（%s）：%s", day_info["day_of_week"], e)
                results.append({"topic": "", "questions": ""})
        return results

    # ---- 周计划：整周批量生成户外游戏 ----

    def generate_weekly_outdoor_games(
        self, week: int, grade: str, class_name: str, theme: str,
        outdoor_content: str, day_infos: list[dict],
    ) -> list[dict]:
        """
        批量生成一周5天的户外游戏。
        返回: [{"outdoor_game_circuit": ..., "outdoor_game_group": ..., "outdoor_game_free": ...}, ...]
        放假天返回空dict。
        """
        prompt_tpl = _get_active_prompt("weekly_outdoor_game")
        results = []
        for day_info in day_infos:
            if day_info.get("is_holiday"):
                results.append({})
                continue
            prompt = prompt_tpl.format(
                week=week,
                day=day_info["day_of_week"],
                date=day_info["date_str"],
                grade=grade,
                class_name=class_name,
                theme=theme,
                outdoor_content=outdoor_content,
            )
            try:
                r = _call_json(
                    self.client, self.model,
                    system_msg="你是专业的幼儿园教育专家，擅长设计户外游戏活动。",
                    user_msg=prompt + _diversity_hint(),
                    temperature=self._params["temperature"],
                    top_p=self._params["top_p"],
                    frequency_penalty=self._params["frequency_penalty"],
                    category="weekly_outdoor_game",
                )
                results.append(r)
            except Exception as e:
                logger.warning("周户外游戏生成失败（%s）：%s", day_info["day_of_week"], e)
                results.append({})
        return results

    # ---- 周计划：整周批量生成区域游戏 ----

    def generate_weekly_area_games(
        self, week: int, grade: str, class_name: str, theme: str,
        area_content: str, day_infos: list[dict],
    ) -> list[dict]:
        """
        批量生成一周5天的区域游戏。
        返回: [{"area_game_zone": ..., "area_game_goal": ..., "area_game_materials": ..., "area_game_guidance": ...}, ...]
        """
        prompt_tpl = _get_active_prompt("weekly_area_game")
        results = []
        for day_info in day_infos:
            if day_info.get("is_holiday"):
                results.append({})
                continue
            prompt = prompt_tpl.format(
                week=week,
                day=day_info["day_of_week"],
                date=day_info["date_str"],
                grade=grade,
                class_name=class_name,
                theme=theme,
                area_content=area_content,
            )
            try:
                r = _call_json(
                    self.client, self.model,
                    system_msg="你是专业的幼儿园教育专家，擅长设计区域游戏活动。",
                    user_msg=prompt + _diversity_hint(),
                    temperature=self._params["temperature"],
                    top_p=self._params["top_p"],
                    frequency_penalty=self._params["frequency_penalty"],
                    category="weekly_area_game",
                )
                results.append(r)
            except Exception as e:
                logger.warning("周区域游戏生成失败（%s）：%s", day_info["day_of_week"], e)
                results.append({})
        return results

    # ---- 周计划：生成周级汇总内容 ----

    def generate_weekly_summary(
        self, week: int, grade: str, class_name: str, theme: str,
    ) -> dict:
        """
        生成本周重点、环境创设、生活习惯培养、家园共育。
        返回: {"week_focus": ..., "env_setup": ..., "life_habits": ..., "home_school": ...}
        """
        prompt_tpl = _get_active_prompt("weekly_summary")
        prompt = prompt_tpl.format(
            week=week, grade=grade, class_name=class_name, theme=theme,
        )
        return _call_json(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长制定周教学要点。",
            user_msg=prompt + _diversity_hint(),
            temperature=self._params["temperature"],
            top_p=self._params["top_p"],
            frequency_penalty=self._params["frequency_penalty"],
            category="weekly_summary",
        )


def get_ai_service() -> Optional[AIService]:
    """
    从数据库读取所有 AI 配置，按负载均衡策略选取一条，返回 AIService 实例。
    策略存于 app_settings.ai_lb_mode：random（默认）/ round_robin / weighted。
    若无 DB 配置则回退到环境变量默认值；仍无则返回 None。
    """
    from app.config import AIConfig
    from app.services.crypto import decrypt
    try:
        rows = execute_query(
            "SELECT api_url, api_key, model_name, COALESCE(weight, 1) AS weight "
            "FROM ai_config ORDER BY id"
        )
        active = [r for r in rows if r.get("api_key")]
        if active:
            # 读取负载均衡策略
            from app.services.plan_service import get_setting
            mode = get_setting("ai_lb_mode", "random")

            if mode == "round_robin":
                with _rr_lock:
                    idx = _rr_counter[0] % len(active)
                    _rr_counter[0] += 1
                chosen = active[idx]
            elif mode == "weighted":
                weights = [max(int(r.get("weight") or 1), 1) for r in active]
                chosen = random.choices(active, weights=weights, k=1)[0]
            else:
                chosen = random.choice(active)

            return AIService(
                api_url=chosen["api_url"],
                api_key=decrypt(chosen["api_key"]),
                model=chosen["model_name"],
            )
    except Exception:
        pass

    # 回退：使用环境变量默认配置
    if AIConfig.DEFAULT_KEY:
        return AIService(
            api_url=AIConfig.DEFAULT_URL,
            api_key=AIConfig.DEFAULT_KEY,
            model=AIConfig.DEFAULT_MODEL,
        )
    return None
