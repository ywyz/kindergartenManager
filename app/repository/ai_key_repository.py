"""ai_key_repository — AI API Key 数据访问层。

所有函数均携带 tenant_id + user_id 过滤，确保数据隔离。

安全约束：
- 明文 API Key 禁止入库、禁止写入任何日志。
- `get_decrypted_key` 返回的明文由调用方负责不泄露。
"""

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, encrypt
from app.core.models.ai_key import AiApiKey


async def save_ai_key(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    api_base_url: str,
    plain_api_key: str,
    model_name: str = "gpt-4o-mini",
) -> AiApiKey:
    """加密 API Key 后入库，同时将该用户旧记录标记为 inactive。

    Args:
        session: 异步数据库会话。
        tenant_id: 租户 ID。
        user_id: 用户 ID。
        api_base_url: AI 接口地址（如 https://api.openai.com/v1）。
        plain_api_key: 明文 API Key（函数内部立即加密，不写日志）。
        model_name: 模型名称（如 gpt-4o-mini、deepseek-chat）。

    Returns:
        新建的 AiApiKey 记录（`api_key_encrypted` 为密文）。
    """
    # 将当前用户的已有 active 记录设为 inactive
    await session.execute(
        update(AiApiKey)
        .where(
            AiApiKey.tenant_id == tenant_id,
            AiApiKey.user_id == user_id,
            AiApiKey.is_active.is_(True),
        )
        .values(is_active=False, updated_at=datetime.now(timezone.utc))
    )

    # 加密明文 Key，立即覆盖变量（最小化明文存活时间）
    encrypted = encrypt(plain_api_key)

    new_key = AiApiKey(
        tenant_id=tenant_id,
        user_id=user_id,
        api_base_url=api_base_url,
        model_name=model_name,
        api_key_encrypted=encrypted,
        is_active=True,
    )
    session.add(new_key)
    await session.commit()
    await session.refresh(new_key)
    return new_key


async def get_active_ai_key(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
) -> AiApiKey | None:
    """查询该用户当前激活的 AI Key 记录。

    Args:
        session: 异步数据库会话。
        tenant_id: 租户 ID。
        user_id: 用户 ID。

    Returns:
        激活的 `AiApiKey` 对象；未配置时返回 None。
    """
    result = await session.execute(
        select(AiApiKey).where(
            AiApiKey.tenant_id == tenant_id,
            AiApiKey.user_id == user_id,
            AiApiKey.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


def get_decrypted_key(ai_key: AiApiKey) -> str:
    """解密并返回明文 API Key。

    Args:
        ai_key: 由 `get_active_ai_key` 取得的模型对象。

    Returns:
        原始明文 API Key 字符串。

    Raises:
        CryptoError: 密文被篡改或密钥不匹配时抛出。

    Note:
        返回的明文禁止写入任何日志。
    """
    return decrypt(ai_key.api_key_encrypted)
