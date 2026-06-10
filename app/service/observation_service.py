"""游戏观察服务层 — 生成与持久化。

职责：
  - generate_observation_content：取 vision Key → 查提示词 → 压缩图片 → AI 调用 → 审计
  - save_observation_with_images：事务写 game_observation + 逐图存储

安全约定：
  - AI Key 解密后仅内存使用，不写日志。
  - 查询全部携带 tenant_id + user_id。
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import ConfigError
from app.integration.ai_client.observation_client import generate_observation
from app.integration.image_processing import CompressedImage, compress_image
from app.integration.image_storage.base import ImageStorageBackend
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key
from app.repository.observation_image_repository import add_image
from app.repository.observation_repository import save_observation
from app.repository.prompt_repository import get_active_prompt


async def generate_observation_content(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    images: list[bytes],
    context: dict,
    *,
    _ai_client=None,
) -> dict:
    """调用视觉 AI 生成游戏观察四段内容，返回结果 dict（含 compressed_images）。

    Args:
        session: 异步数据库会话。
        tenant_id: 租户 ID。
        user_id: 用户 ID。
        images: 原始图片字节列表（1~3 张）。
        context: 上下文 dict（grade、game_area、big_env 等）。
        _ai_client: 可选 httpx 客户端（测试用）。

    Returns:
        dict，包含：
          observation_goal / observation_record / evaluation_analysis / support_strategy
          compressed_images: list[CompressedImage]

    Raises:
        ConfigError: 未配置视觉 AI Key。
        AiCallError: AI HTTP 调用失败。
        AiParseError: AI 返回结果解析失败。
    """
    # 1. 取视觉 Key
    ai_key_record = await get_active_ai_key(
        session, tenant_id=tenant_id, user_id=user_id, key_type="vision"
    )
    if ai_key_record is None:
        raise ConfigError("尚未配置视觉模型 API Key，请先在设置页面配置")

    plain_key = get_decrypted_key(ai_key_record)

    # 2. 查 game_observation 提示词激活版本
    prompt_record = await get_active_prompt(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        task_type="game_observation",
    )
    system_prompt = prompt_record.content if prompt_record else None

    # 3. 压缩图片
    compressed_images: list[CompressedImage] = []
    compressed_bytes: list[bytes] = []
    for img_bytes in images:
        ci = compress_image(img_bytes)
        compressed_images.append(ci)
        compressed_bytes.append(ci.data)

    # 4. 调用视觉 AI
    result = await generate_observation(
        images=compressed_bytes,
        context=context,
        api_base_url=ai_key_record.api_base_url,
        api_key=plain_key,
        model_name=ai_key_record.model_name,
        system_prompt=system_prompt,
        _client=_ai_client,
    )

    # 5. 审计
    log_audit(
        "ai_observation",
        tenant_id=tenant_id,
        user_id=user_id,
        model_name=ai_key_record.model_name,
        image_count=len(images),
    )

    return {
        "observation_goal": result["observation_goal"],
        "observation_record": result["observation_record"],
        "evaluation_analysis": result["evaluation_analysis"],
        "support_strategy": result["support_strategy"],
        "compressed_images": compressed_images,
    }


async def save_observation_with_images(
    session: AsyncSession,
    obs_data: dict,
    compressed_images: list[CompressedImage],
    storage: ImageStorageBackend,
) -> int:
    """事务写入观察记录 + 图片，返回 observation_id。

    Args:
        session: 异步数据库会话。
        obs_data: 观察记录字段 dict（含 tenant_id / user_id 等全部字段）。
        compressed_images: 压缩后图片列表（顺序即 image_index 顺序，1-based）。
        storage: 图片存储后端实例。

    Returns:
        新建的 game_observation.id。
    """
    obs = await save_observation(session, **obs_data)

    tenant_id: int = obs_data["tenant_id"]
    user_id: int = obs_data["user_id"]

    for idx, ci in enumerate(compressed_images, start=1):
        stored_ref = storage.put(ci.data, mime_type=ci.mime_type)
        await add_image(
            session,
            tenant_id=tenant_id,
            user_id=user_id,
            observation_id=obs.id,
            image_index=idx,
            storage_backend=stored_ref.get("storage_backend", "mysql_blob"),
            blob_content=stored_ref.get("blob_content"),
            mime_type=stored_ref.get("mime_type", ci.mime_type),
            file_size=ci.file_size,
            width=ci.width,
            height=ci.height,
        )

    return obs.id
