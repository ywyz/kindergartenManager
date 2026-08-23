"""设置页逐步抽离的应用用例。"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CryptoError
from app.integration.ai_client.model_catalog import AiEndpointCheck, check_ai_endpoint
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key

AiEndpointVerifier = Callable[[str, str], Awaitable[AiEndpointCheck]]


async def verify_saved_ai_connection(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    key_type: str,
    verifier: AiEndpointVerifier = check_ai_endpoint,
) -> AiEndpointCheck:
    """验证当前用户已保存的 AI 配置，不把明文 Key 返回给 UI。"""
    record = await get_active_ai_key(session, tenant_id, user_id, key_type=key_type)
    if record is None:
        return AiEndpointCheck(code="not_configured")

    try:
        plain_key = get_decrypted_key(record)
    except CryptoError:
        return AiEndpointCheck(code="key_decryption_failed")

    return await verifier(record.api_base_url, plain_key)
