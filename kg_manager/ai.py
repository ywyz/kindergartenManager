"""
AI集成模块：用于教案内容拆分等功能
"""

import os
import json
from openai import OpenAI


# AI配置
AI_MODEL = "gpt-4o-mini"

# AI系统提示词
AI_SYSTEM_PROMPT = (
    "你是幼儿园教案助理。请将用户提供的集体活动原稿拆分为固定字段："
    "活动主题、活动目标、活动准备、活动重点、活动难点、活动过程。"
    "请只输出 JSON 对象，不要包含多余文字或 Markdown。"
    "输出示例："
    "{"
    '"活动主题":"...",'
    '"活动目标":"...",'
    '"活动准备":"...",'
    '"活动重点":"...",'
    '"活动难点":"...",'
    '"活动过程":"..."'
    "}"
)


def get_ai_client(api_key=None, base_url=None):
    """获取OpenAI客户端
    
    Args:
        api_key: OpenAI API密钥（如果不提供，则从环境变量读取）
        base_url: API基础URL（如果不提供，则从环境变量读取）
    
    Returns:
        OpenAI客户端实例
    """
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("未检测到 OPENAI_API_KEY 环境变量或参数")

    url = base_url or os.getenv("OPENAI_BASE_URL")
    if url:
        return OpenAI(api_key=key, base_url=url)
    return OpenAI(api_key=key)


def split_collective_activity(draft_text, system_prompt=None, api_key=None, base_url=None, model=None):
    """
    使用AI拆分集体活动原稿
    
    Args:
        draft_text: 完整的集体活动原稿
        system_prompt: 自定义系统提示词（None则使用默认）
        api_key: OpenAI API密钥（如果不提供，则从环境变量读取）
        base_url: API基础URL（如果不提供，则从环境变量读取）
        model: AI模型名称（如果不提供，则从环境变量读取或使用默认）
        
    Returns:
        {活动主题: ..., 活动目标: ..., ...} 字典，若解析失败返回None
    """
    if not draft_text or not draft_text.strip():
        raise ValueError("原稿不能为空")
    
    try:
        client = get_ai_client(api_key=api_key, base_url=base_url)
        ai_model = model or os.getenv("OPENAI_MODEL") or AI_MODEL
        response = client.chat.completions.create(
            model=ai_model,
            messages=[
                {"role": "system", "content": system_prompt or AI_SYSTEM_PROMPT},
                {"role": "user", "content": draft_text},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content.strip()
        return parse_ai_json(content)
    except Exception as e:
        raise RuntimeError(f"AI处理失败：{str(e)}")


def parse_ai_json(content):
    """
    解析AI返回的JSON内容
    
    Args:
        content: AI返回的文本
        
    Returns:
        解析后的字典，若失败返回None
    """
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 尝试提取JSON对象
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def set_custom_system_prompt(new_prompt):
    """
    设置自定义系统提示词（全局）
    
    Args:
        new_prompt: 新的系统提示词
    """
    global AI_SYSTEM_PROMPT
    AI_SYSTEM_PROMPT = new_prompt
