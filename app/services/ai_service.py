"""AI 服务封装 - 使用 openai 库连接兼容接口"""
import json
import re
from typing import Optional

from openai import OpenAI

from app.db import execute_one


# ---------------------------------------------------------------------------
# 内置默认提示词
# ---------------------------------------------------------------------------

_DEFAULT_PROMPTS: dict[str, str] = {
    "lesson_split": (
        "你是一位专业的幼儿园教育专家。请将以下完整教案拆分为结构化的JSON格式，"
        "包含以下字段：活动主题(theme)、活动目标(goal)、活动准备(preparation)、"
        "活动重点(key_point)、活动难点(difficulty)、活动过程(process)。\n"
        "只返回合法的JSON对象，不要添加任何解释或代码块标记。\n\n"
        "教案内容：\n{content}"
    ),
    "process_modify": (
        "你是一位专业的幼儿园教育专家。请根据{grade}幼儿的年龄特点和发展水平，"
        "对以下活动过程进行适当修改优化，使其更符合该年龄段幼儿的认知和行为特点。\n"
        "请在修改的内容末尾用【AI修改】标注，方便对比。\n"
        "只返回修改后的活动过程文本，不要添加其他解释。\n\n"
        "原始活动过程：\n{content}"
    ),
    "morning_activity": (
        "你是一位专业的幼儿园教育专家。请为{grade}{class_name}设计一份晨间活动方案。\n"
        "当前是第{week}周，{day}。\n"
        "户外体育器材与场地内容：{outdoor_content}\n"
        "请生成以下JSON格式的晨间活动内容：\n"
        "{{\n"
        "  \"activity_type\": \"活动类型（体能大循环/集体游戏/自选游戏）\",\n"
        "  \"key_guidance\": \"重点指导内容\",\n"
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


def _chat(client: OpenAI, model: str, system_msg: str, user_msg: str,
          temperature: float = 0.7, max_retries: int = 2) -> str:
    """发送对话请求，带简单重试"""
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            last_err = e
            if attempt == max_retries:
                raise RuntimeError(f"AI调用失败（已重试{max_retries}次）：{e}") from e
    raise RuntimeError(f"AI调用失败：{last_err}")


# ---------------------------------------------------------------------------
# 对外 AI 服务方法
# ---------------------------------------------------------------------------

class AIService:
    """AI 服务，支持传入自定义 api_url/api_key/model"""

    def __init__(self, api_url: str, api_key: str, model: str):
        self.client = _build_client(api_url, api_key)
        self.model = model

    # ---- 教案拆分 ----

    def split_lesson_plan(self, text: str, grade: str = "") -> dict:
        """
        拆分教案为结构化 JSON。
        返回：{theme, goal, preparation, key_point, difficulty, process}
        """
        prompt_tpl = _get_active_prompt("lesson_split")
        prompt = prompt_tpl.format(content=text, grade=grade)
        raw = _chat(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长教案分析与整理。",
            user_msg=prompt,
            temperature=0.3,
        )
        try:
            return _extract_json(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"AI返回的JSON格式有误：{e}\n原始内容：{raw[:500]}") from e

    # ---- 活动过程修改 ----

    def modify_activity_process(self, original_process: str, grade: str) -> str:
        """根据年龄段修改活动过程，返回修改后文本，AI修改部分标注【AI修改】"""
        prompt_tpl = _get_active_prompt("process_modify")
        prompt = prompt_tpl.format(content=original_process, grade=grade)
        return _chat(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长根据年龄特点优化教学活动。",
            user_msg=prompt,
            temperature=0.5,
        )

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
        raw = _chat(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长设计晨间活动。",
            user_msg=prompt,
        )
        try:
            return _extract_json(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"AI返回的JSON格式有误：{e}\n原始内容：{raw[:500]}") from e

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
        raw = _chat(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长设计晨间谈话。",
            user_msg=prompt,
        )
        try:
            return _extract_json(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"AI返回的JSON格式有误：{e}\n原始内容：{raw[:500]}") from e

    # ---- 室内区域活动生成 ----

    def generate_indoor_area(
        self, grade: str, class_name: str, area_content: str
    ) -> dict:
        """生成室内区域活动内容"""
        prompt_tpl = _get_active_prompt("indoor_area")
        prompt = prompt_tpl.format(grade=grade, class_name=class_name, area_content=area_content)
        raw = _chat(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长设计区域游戏活动。",
            user_msg=prompt,
        )
        try:
            return _extract_json(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"AI返回的JSON格式有误：{e}\n原始内容：{raw[:500]}") from e

    # ---- 户外游戏活动生成 ----

    def generate_outdoor_game(
        self, grade: str, class_name: str, outdoor_content: str
    ) -> dict:
        """生成户外游戏活动内容"""
        prompt_tpl = _get_active_prompt("outdoor_game")
        prompt = prompt_tpl.format(
            grade=grade, class_name=class_name, outdoor_content=outdoor_content
        )
        raw = _chat(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家，擅长设计户外游戏活动。",
            user_msg=prompt,
        )
        try:
            return _extract_json(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"AI返回的JSON格式有误：{e}\n原始内容：{raw[:500]}") from e

    # ---- 提示词测试 ----

    def test_prompt(self, prompt_content: str, test_input: str) -> str:
        """测试任意提示词，返回AI响应原始文本"""
        return _chat(
            self.client, self.model,
            system_msg="你是专业的幼儿园教育专家。",
            user_msg=prompt_content.replace("{content}", test_input),
        )


def get_ai_service() -> Optional[AIService]:
    """
    从数据库读取激活的AI配置，创建 AIService 实例。
    若无配置则返回 None。
    """
    from app.config import AIConfig
    from app.services.crypto import decrypt
    try:
        row = execute_one(
            "SELECT api_url, api_key, model_name FROM ai_config ORDER BY id DESC LIMIT 1"
        )
        if row and row.get("api_key"):
            return AIService(
                api_url=row["api_url"],
                api_key=decrypt(row["api_key"]),
                model=row["model_name"],
            )
    except Exception:
        pass

    # 回退到默认配置
    if AIConfig.DEFAULT_KEY:
        return AIService(
            api_url=AIConfig.DEFAULT_URL,
            api_key=AIConfig.DEFAULT_KEY,
            model=AIConfig.DEFAULT_MODEL,
        )
    return None
