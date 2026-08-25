"""OpenAI-compatible model catalog connection adapter."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import httpx

AiEndpointCode = Literal[
    "ok",
    "http_error",
    "timeout",
    "transport_error",
    "not_configured",
    "key_decryption_failed",
]


@dataclass(frozen=True, slots=True)
class AiEndpointCheck:
    """Sanitized endpoint check result with no response body or credential data."""

    code: AiEndpointCode
    http_status: int | None = None


async def check_ai_endpoint(
    api_base_url: str,
    api_key: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout_seconds: float = 10.0,
) -> AiEndpointCheck:
    """Call the provider's ``/models`` endpoint and return a sanitized result."""
    endpoint = f"{api_base_url.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        if client is None:
            async with httpx.AsyncClient(timeout=timeout_seconds) as owned_client:
                response = await owned_client.get(endpoint, headers=headers)
        else:
            response = await client.get(endpoint, headers=headers, timeout=timeout_seconds)
    except httpx.TimeoutException:
        return AiEndpointCheck(code="timeout")
    except httpx.HTTPError:
        return AiEndpointCheck(code="transport_error")

    if response.is_success:
        return AiEndpointCheck(code="ok", http_status=response.status_code)
    return AiEndpointCheck(code="http_error", http_status=response.status_code)
