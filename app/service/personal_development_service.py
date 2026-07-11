"""personal_development_service — 幼儿个体发展档案业务逻辑层。

职责：
  - extract_from_other_records：从一对一倾听、游戏观察提取数据
  - generate_content：AI生成发展情况分析和教师寄语
  - save_record：事务保存记录

安全约定：
  - AI Key 解密后仅内存使用，不写日志。
  - 查询全部携带 tenant_id + user_id。
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import AiCallError, AiParseError, AppError, ConfigError
from app.integration.ai_client.base import call_ai_text
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key
from app.repository.listening_repository import list_records as list_listening_records
from app.repository.observation_repository import list_observations
from app.repository.personal_development_repository import (
    get_record_by_child_semester,
    save_record as repo_save_record,
    update_record as repo_update_record,
)
from app.repository.prompt_repository import get_active_prompt

DEFAULT_ANALYSIS_PROMPT: str = """\
你是幼儿园教育专家。根据以下幼儿的倾听记录和游戏观察数据，分析该幼儿的发展情况。

请严格按照以下格式输出，禁止任何 Markdown 标记：

发展情况分析：
（请从健康、语言、社会、科学、艺术五个领域综合分析幼儿的发展水平和特点，50-100字）

采取措施：
（针对幼儿的发展情况，提出具体的教育建议和措施，30-60字）

家园联系：
（针对幼儿的发展情况，提出家园合作的建议，30-60字）

突出表现：
（总结幼儿在各领域中的突出表现和闪光点，30-60字）

进步情况：
（分析幼儿本学期的进步和成长，30-60字）

输出约束：
1.禁止使用任何 Markdown 格式标记
2.每个部分单独一行，以标题开头
3.语言简洁专业，符合幼儿园教育专业水平
"""

DEFAULT_MESSAGE_PROMPT: str = """\
你是幼儿园老师。请为以下幼儿写一段温馨的保教老师寄语。

幼儿信息：
姓名：{child_name}
性别：{gender}
年龄：{age}
班级：{grade}

请严格按照以下格式输出，禁止任何 Markdown 标记：

寄语：
（温馨、鼓励的话语，体现对幼儿的了解和关爱，50-100字）

输出约束：
1.禁止使用任何 Markdown 格式标记
2.语言亲切温暖，符合幼儿园老师的口吻
"""


async def extract_from_other_records(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    child_name: str,
) -> dict:
    """从一对一倾听和游戏观察记录中提取幼儿数据。

    Args:
        session: 异步数据库会话。
        tenant_id / user_id: 隔离字段。
        child_name: 幼儿姓名。

    Returns:
        dict，包含提取的数据：
          listening_records: 该幼儿的倾听记录列表
          observation_records: 该幼儿的游戏观察记录列表
          domain_summary: 各领域指标达成汇总
    """
    listening_records = await list_listening_records(
        session, tenant_id, user_id,
        child_name=child_name,
        limit=10,
    )

    observation_records = await list_observations(
        session, tenant_id, user_id,
        child_names=child_name,
        limit=10,
    )

    domain_summary = {}
    for lr in listening_records:
        if lr.grade and lr.term:
            key = f"{lr.grade}-{lr.term}"
            if key not in domain_summary:
                domain_summary[key] = []
            domain_summary[key].append(lr.child_name)

    return {
        "listening_records": listening_records,
        "observation_records": observation_records,
        "domain_summary": domain_summary,
    }


async def generate_content(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    *,
    child_name: str,
    gender: str | None = None,
    grade: str | None = None,
    child_age: str | None = None,
    extracted_data: dict | None = None,
    _ai_client=None,
) -> dict:
    """调用 AI 生成发展情况分析和教师寄语。

    Args:
        session: 异步数据库会话。
        tenant_id / user_id: 隔离字段。
        child_name: 幼儿姓名。
        gender: 性别。
        grade: 年级。
        child_age: 年龄。
        extracted_data: 从其他记录提取的数据。
        _ai_client: 可选 httpx 客户端（测试用）。

    Returns:
        dict，包含：
          development_status / measures_taken / home_contact
          outstanding_performance / progress / teacher_message

    Raises:
        ConfigError: 未配置 AI Key。
        AiCallError / AiParseError: AI 调用或解析失败。
    """
    ai_key_record = await get_active_ai_key(
        session, tenant_id=tenant_id, user_id=user_id, key_type="text"
    )
    if ai_key_record is None:
        ai_key_record = await get_active_ai_key(
            session, tenant_id=tenant_id, user_id=user_id, key_type="vision"
        )
    if ai_key_record is None:
        raise ConfigError("尚未配置 AI API Key，请先在设置页面配置")
    plain_key = get_decrypted_key(ai_key_record)

    prompt_record = await get_active_prompt(
        session, tenant_id=tenant_id, user_id=user_id,
        task_type="personal_development",
    )
    system_prompt = prompt_record.content if prompt_record else DEFAULT_ANALYSIS_PROMPT

    listening_info = []
    observation_info = []
    if extracted_data:
        for lr in extracted_data.get("listening_records", []):
            listening_info.append(
                f"倾听记录：{lr.obs_year}年{lr.obs_month}月，{lr.grade or ''}，{lr.child_name}"
            )
        for obs in extracted_data.get("observation_records", []):
            observation_info.append(
                f"观察记录：{obs.obs_date}，{obs.big_env}，{obs.game_area or ''}"
            )

    user_content = f"""幼儿信息：
姓名：{child_name}
性别：{gender or '未知'}
年级：{grade or '未知'}
年龄：{child_age or '未知'}

倾听记录：
{chr(10).join(listening_info) if listening_info else '暂无'}

游戏观察：
{chr(10).join(observation_info) if observation_info else '暂无'}
"""

    result = await call_ai_text(
        system_prompt=system_prompt,
        user_content=user_content,
        api_base_url=ai_key_record.api_base_url,
        api_key=plain_key,
        model_name=ai_key_record.model_name,
        _client=_ai_client,
    )

    parsed = _parse_analysis_result(result)

    message_prompt = DEFAULT_MESSAGE_PROMPT.format(
        child_name=child_name,
        gender=gender or "",
        age=child_age or "",
        grade=grade or "",
    )
    message_result = await call_ai_text(
        system_prompt="你是幼儿园老师，请写一段温馨的教师寄语。",
        user_content=message_prompt,
        api_base_url=ai_key_record.api_base_url,
        api_key=plain_key,
        model_name=ai_key_record.model_name,
        _client=_ai_client,
    )

    parsed["teacher_message"] = message_result.get("寄语", "").strip()

    log_audit(
        "ai_personal_development",
        tenant_id=tenant_id,
        user_id=user_id,
        detail={"child_name": child_name},
    )

    return parsed


def _parse_analysis_result(result: dict) -> dict:
    """解析 AI 返回的发展分析结果。"""
    content = result.get("content", "") if isinstance(result, dict) else str(result)

    sections = {
        "发展情况分析": "development_status",
        "采取措施": "measures_taken",
        "家园联系": "home_contact",
        "突出表现": "outstanding_performance",
        "进步情况": "progress",
    }

    parsed = {}
    current_section = None
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        found_section = False
        for title, key in sections.items():
            if line.startswith(title):
                current_section = key
                parsed[key] = line[len(title):].strip()
                found_section = True
                break
        if not found_section and current_section:
            if parsed[current_section]:
                parsed[current_section] += "\n" + line
            else:
                parsed[current_section] = line

    return {key: parsed.get(key, "") for key in sections.values()}


async def save_record(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    semester_id: int,
    child_name: str,
    **kwargs,
) -> dict:
    """保存发展档案（新建或更新）。

    Args:
        session: 异步数据库会话。
        tenant_id / user_id: 隔离字段。
        semester_id: 学期 ID。
        child_name: 幼儿姓名。
        kwargs: 其他字段（gender, birth_date, height, weight 等）。

    Returns:
        dict，包含操作类型和记录 ID。

    Raises:
        AppError: 保存失败。
    """
    existing = await get_record_by_child_semester(
        session, tenant_id, child_name, semester_id
    )

    if existing:
        record = await repo_update_record(session, existing, **kwargs)
        log_audit(
            "update_personal_development",
            tenant_id=tenant_id,
            user_id=user_id,
            detail={"record_id": record.id, "child_name": child_name},
        )
        return {"action": "updated", "record_id": record.id}
    else:
        record = await repo_save_record(
            session,
            tenant_id=tenant_id,
            user_id=user_id,
            semester_id=semester_id,
            child_name=child_name,
            **kwargs,
        )
        log_audit(
            "create_personal_development",
            tenant_id=tenant_id,
            user_id=user_id,
            detail={"record_id": record.id, "child_name": child_name},
        )
        return {"action": "created", "record_id": record.id}