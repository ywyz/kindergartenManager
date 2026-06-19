"""一对一倾听服务层 — 单领域生成与整记录持久化。

职责：
  - generate_domain_content：取 vision Key → 查提示词 → 查指标目录 → 压缩图片
    → AI 调用 → 指标星级归一化（缺失补默认 3 星）→ 审计
  - save_record_with_all：事务写 listening_record + 5×listening_domain
    + 各领域图片 + 指标结果

安全约定：
  - AI Key 解密后仅内存使用，不写日志。
  - 查询全部携带 tenant_id + user_id。
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import ConfigError
from app.integration.ai_client.listening_client import generate_listening_domain
from app.integration.image_processing import CompressedImage, compress_image
from app.integration.image_storage.base import ImageStorageBackend
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key
from app.repository.indicator_repository import list_indicators
from app.repository.listening_image_repository import add_image
from app.repository.listening_repository import (
    save_domain,
    save_indicator_result,
    save_record,
)
from app.repository.prompt_repository import get_active_prompt


def _clamp_star(value, default: int = 3) -> int:
    """将星级归一化为 1~3 的整数，非法值回退默认。"""
    try:
        s = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(3, s))


async def generate_domain_content(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    *,
    domain: str,
    images: list[bytes],
    context: dict,
    _ai_client=None,
) -> dict:
    """调用视觉 AI 生成某领域的一对一倾听内容，返回结构化结果。

    Args:
        session: 异步数据库会话。
        tenant_id / user_id: 隔离字段。
        domain: 领域（健康/语言/社会/艺术/科学）。
        images: 该领域原始图片字节列表（至少 1 张）。
        context: 上下文 dict，须含 grade、term；可含 child_name、child_age。
        _ai_client: 可选 httpx 客户端（测试用）。

    Returns:
        dict，包含：
          goals / image_descriptions / evaluation / support_strategy
          indicator_results: list[{catalog_id, sort_order, level2_name, stars}]
          compressed_images: list[CompressedImage]

    Raises:
        ConfigError: 未配置视觉 AI Key。
        AiCallError / AiParseError: AI 调用或解析失败。
    """
    # 1. 取视觉 Key
    ai_key_record = await get_active_ai_key(
        session, tenant_id=tenant_id, user_id=user_id, key_type="vision"
    )
    if ai_key_record is None:
        raise ConfigError("尚未配置视觉模型 API Key，请先在设置页面配置")
    plain_key = get_decrypted_key(ai_key_record)

    # 2. 查提示词激活版本
    prompt_record = await get_active_prompt(
        session, tenant_id=tenant_id, user_id=user_id,
        task_type="one_on_one_listening",
    )
    system_prompt = prompt_record.content if prompt_record else None

    # 3. 查该领域二级指标目录
    grade = context.get("grade") or ""
    term = context.get("term") or ""
    catalog = await list_indicators(session, tenant_id, grade, term, domain)
    indicators_for_ai = [
        {
            "sort_order": c.sort_order,
            "level2": c.level2_name,
            "standards": {
                "1": c.standard_star1,
                "2": c.standard_star2,
                "3": c.standard_star3,
            },
        }
        for c in catalog
    ]

    # 4. 压缩图片
    compressed_images: list[CompressedImage] = [compress_image(b) for b in images]
    compressed_bytes = [ci.data for ci in compressed_images]

    # 5. 调用视觉 AI
    result = await generate_listening_domain(
        images=compressed_bytes,
        context={"domain": domain, **context},
        indicators=indicators_for_ai,
        api_base_url=ai_key_record.api_base_url,
        api_key=plain_key,
        model_name=ai_key_record.model_name,
        system_prompt=system_prompt,
        _client=_ai_client,
    )

    # 6. 指标星级归一化：覆盖全部目录指标，AI 未给的默认 3 星
    ai_stars = {
        item.get("sort_order"): item.get("stars")
        for item in result["indicators"]
        if isinstance(item, dict)
    }
    indicator_results = [
        {
            "catalog_id": c.id,
            "sort_order": c.sort_order,
            "level2_name": c.level2_name,
            "stars": _clamp_star(ai_stars.get(c.sort_order, 3)),
        }
        for c in catalog
    ]

    # 7. 审计
    log_audit(
        "ai_listening",
        tenant_id=tenant_id,
        user_id=user_id,
        domain=domain,
        model_name=ai_key_record.model_name,
        image_count=len(images),
    )

    return {
        "goals": result["goals"],
        "image_descriptions": result["image_descriptions"],
        "indicator_results": indicator_results,
        "evaluation": result["evaluation"],
        "support_strategy": result["support_strategy"],
        "compressed_images": compressed_images,
    }


async def save_record_with_all(
    session: AsyncSession,
    *,
    record_data: dict,
    domains: list[dict],
    storage: ImageStorageBackend,
) -> int:
    """事务写入整条记录（主表 + 各领域 + 图片 + 指标结果），返回 record_id。

    Args:
        session: 异步数据库会话。
        record_data: listening_record 字段 dict（含 tenant_id / user_id 等）。
        domains: 领域 payload 列表，每项含 domain / obs_year / obs_month /
            date_1..3 / goals / evaluation / support_strategy /
            compressed_images(list[CompressedImage]) / image_descriptions(list[str]) /
            indicator_results(list[{catalog_id, stars}])。
        storage: 图片存储后端实例。

    Returns:
        新建的 listening_record.id。
    """
    rec = await save_record(session, **record_data)
    tenant_id: int = record_data["tenant_id"]
    user_id: int = record_data["user_id"]

    for dom in domains:
        domain_name = dom["domain"]
        await save_domain(
            session,
            tenant_id=tenant_id,
            user_id=user_id,
            record_id=rec.id,
            domain=domain_name,
            obs_year=dom.get("obs_year"),
            obs_month=dom.get("obs_month"),
            date_1=dom.get("date_1"),
            date_2=dom.get("date_2"),
            date_3=dom.get("date_3"),
            goals=dom.get("goals"),
            evaluation=dom.get("evaluation"),
            support_strategy=dom.get("support_strategy"),
        )

        compressed = dom.get("compressed_images") or []
        descriptions = dom.get("image_descriptions") or []
        for idx, ci in enumerate(compressed, start=1):
            stored_ref = storage.put(ci.data, mime_type=ci.mime_type)
            desc = descriptions[idx - 1] if idx - 1 < len(descriptions) else None
            await add_image(
                session,
                tenant_id=tenant_id,
                user_id=user_id,
                record_id=rec.id,
                domain=domain_name,
                image_index=idx,
                storage_backend=stored_ref.get("storage_backend", "mysql_blob"),
                blob_content=stored_ref.get("blob_content"),
                mime_type=stored_ref.get("mime_type", ci.mime_type),
                file_size=ci.file_size,
                width=ci.width,
                height=ci.height,
                image_description=desc,
            )

        for ind in dom.get("indicator_results") or []:
            await save_indicator_result(
                session,
                tenant_id=tenant_id,
                user_id=user_id,
                record_id=rec.id,
                domain=domain_name,
                catalog_id=ind["catalog_id"],
                stars=ind.get("stars", 3),
            )

    return rec.id
