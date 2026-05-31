"""对外 REST API 鉴权：API Key + 可选 HMAC 签名。

鉴权模型（服务间调用）：
1. **API Key**（必填）：调用方在 `X-Api-Key` 请求头携带；服务端依据
   `settings.API_KEYS`（"apikey:tenant_id" 映射）解析出绑定的 tenant_id。
   每个 Key 绑定唯一租户，调用方只能读取本租户数据，实现租户隔离。
2. **HMAC 签名**（可选）：当 `settings.API_SIGNING_SECRET` 非空时强制校验。
   调用方需携带 `X-Timestamp` 与 `X-Signature`：
   - 待签名串：``f"{timestamp}\\n{METHOD}\\n{path}\\n{query}"``（query 为原始查询串，可空）
   - 签名值：``hmac_sha256(secret, 待签名串)`` 的十六进制小写。
   - 时间戳与服务器时间偏差需在 `API_SIGNATURE_MAX_SKEW` 秒内，用于防重放。
"""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass

from fastapi import Request
from fastapi import status as http_status
from fastapi.exceptions import HTTPException

from app.core.config import settings


@dataclass(frozen=True)
class ApiPrincipal:
    """通过鉴权的调用方主体。"""

    tenant_id: int
    api_key: str


def parse_api_keys(raw: str) -> dict[str, int]:
    """解析 `API_KEYS` 配置为 {api_key: tenant_id} 映射。

    格式："key1:1,key2:2"；忽略空段与格式非法段（tenant_id 非整数）。
    """
    mapping: dict[str, int] = {}
    for segment in raw.split(","):
        segment = segment.strip()
        if not segment or ":" not in segment:
            continue
        key, _, tenant = segment.rpartition(":")
        key = key.strip()
        tenant = tenant.strip()
        if not key or not tenant.isdigit():
            continue
        mapping[key] = int(tenant)
    return mapping


def _build_signing_string(timestamp: str, method: str, path: str, query: str) -> str:
    return f"{timestamp}\n{method.upper()}\n{path}\n{query}"


def verify_signature(
    secret: str,
    timestamp: str,
    method: str,
    path: str,
    query: str,
    provided_signature: str,
    *,
    max_skew: int,
    now: float | None = None,
) -> bool:
    """校验 HMAC-SHA256 请求签名与时间戳新鲜度。"""
    if not timestamp or not provided_signature:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    current = int(now if now is not None else time.time())
    if abs(current - ts) > max_skew:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        _build_signing_string(timestamp, method, path, query).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, provided_signature)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "ApiKey"},
    )


async def get_api_principal(request: Request) -> ApiPrincipal:
    """FastAPI 依赖：校验 API Key（必填）与签名（按配置可选），返回调用方主体。"""
    api_keys = parse_api_keys(settings.API_KEYS)
    if not api_keys:
        # 未配置任何 API Key 时，对外接口默认关闭，避免误开放。
        raise _unauthorized("对外 API 未启用（未配置 API_KEYS）")

    api_key = request.headers.get("X-Api-Key", "")
    tenant_id = api_keys.get(api_key)
    if tenant_id is None:
        raise _unauthorized("无效的 API Key")

    signing_secret = settings.API_SIGNING_SECRET
    if signing_secret:
        ok = verify_signature(
            secret=signing_secret,
            timestamp=request.headers.get("X-Timestamp", ""),
            method=request.method,
            path=request.url.path,
            query=request.url.query,
            provided_signature=request.headers.get("X-Signature", ""),
            max_skew=settings.API_SIGNATURE_MAX_SKEW,
        )
        if not ok:
            raise _unauthorized("请求签名校验失败")

    return ApiPrincipal(tenant_id=tenant_id, api_key=api_key)
