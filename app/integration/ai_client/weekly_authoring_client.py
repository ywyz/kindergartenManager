"""Single-request Chat Completions transport for the weekly authoring application.

No retries, tools, provider history, logging or persistence. The application owns
closed field validation and current authorization before and after this await.
"""

import asyncio
import json
import os
import stat
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import _secrets_file_path
from app.repository.ai_key_repository import get_active_ai_key, get_decrypted_key
from app.service.academic_identity.contracts import IdentityRejected
from app.service.shared_weekly.prompt_contracts import SCHEMA_INSTRUCTION, PromptActor

REQUEST_BYTES = 16 * 1024
RESPONSE_BYTES = 64 * 1024
OUTPUT_BYTES = 16 * 1024


@dataclass(frozen=True, slots=True, repr=False)
class WeeklyAIConfig:
    api_base_url: str
    api_key: str
    model_name: str

    def __post_init__(self) -> None:
        try:
            url = urlsplit(self.api_base_url)
            if (
                url.scheme != "https"
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or url.fragment
                or url.query
                or any(c.isspace() for c in self.api_base_url)
                or not self.api_key.strip()
                or not self.model_name.strip()
                or len(self.api_key) > 8192
                or len(self.model_name) > 256
                or any(ord(c) < 32 for c in self.api_key + self.model_name)
            ):
                raise ValueError
            _ = url.port
        except Exception:  # noqa: BLE001 - sanitize the integration/config boundary
            raise IdentityRejected("config_invalid") from None


async def load_config(session: AsyncSession, actor: PromptActor) -> WeeklyAIConfig:
    try:
        if os.name == "posix":
            path = _secrets_file_path()
            if path.exists() or path.is_symlink():
                metadata = path.lstat()
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_uid != os.getuid()
                    or stat.S_IMODE(metadata.st_mode) != 0o600
                ):
                    raise ValueError
        row = await get_active_ai_key(session, actor.tenant_id, actor.user_id)
        if row is None:
            raise ValueError
        return WeeklyAIConfig(row.api_base_url, get_decrypted_key(row), row.model_name)
    except Exception:  # noqa: BLE001 - sanitize the integration/config boundary
        raise IdentityRejected("config_invalid") from None


def _pairs(items: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError
        value[key] = item
    return value


def _json(raw: bytes | str) -> object:
    return json.loads(
        raw,
        object_pairs_hook=_pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
    )


async def generate(
    prompt: str,
    payload: dict,
    config: WeeklyAIConfig,
    *,
    _client: httpx.AsyncClient | None = None,
) -> dict:
    """Return a syntactically closed patch; caller validates requested paths/budgets."""
    try:
        if (
            type(config) is not WeeklyAIConfig
            or type(prompt) is not str
            or type(payload) is not dict
        ):
            raise ValueError
        config.__post_init__()
        request = json.dumps(
            {
                "model": config.model_name,
                "messages": [
                    {"role": "system", "content": prompt + "\n" + SCHEMA_INSTRUCTION},
                    {
                        "role": "user",
                        "content": json.dumps(
                            payload, ensure_ascii=False, allow_nan=False
                        ),
                    },
                ],
                "response_format": {"type": "json_object"},
            },
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        if len(request) > REQUEST_BYTES:
            raise ValueError
    except IdentityRejected:
        raise
    except Exception:  # noqa: BLE001 - sanitize the integration/config boundary
        raise IdentityRejected("ai_invalid") from None

    async def send(client: httpx.AsyncClient) -> dict:
        try:
            async with client.stream(
                "POST",
                config.api_base_url.rstrip("/") + "/chat/completions",
                headers={
                    "Authorization": "Bearer " + config.api_key,
                    "Content-Type": "application/json",
                },
                content=request,
                timeout=60,
                follow_redirects=False,
            ) as response:
                if response.status_code != 200:
                    raise IdentityRejected("ai_unavailable")
                chunks = bytearray()
                async for chunk in response.aiter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > RESPONSE_BYTES:
                        raise IdentityRejected("ai_invalid")
            body = _json(bytes(chunks))
            choices = body["choices"]
            if type(choices) is not list or len(choices) != 1:
                raise ValueError
            choice = choices[0]
            message = choice["message"]
            if (
                choice.get("finish_reason") != "stop"
                or message.get("refusal")
                or message.get("tool_calls")
                or message.get("function_call")
            ):
                raise ValueError
            content = message["content"]
            if type(content) is not str or len(content.encode("utf-8")) > OUTPUT_BYTES:
                raise ValueError
            result = _json(content)
            if (
                type(result) is not dict
                or set(result) != {"values"}
                or type(result["values"]) is not dict
                or not result["values"]
                or any(type(v) is not str for v in result["values"].values())
            ):
                raise ValueError
            return result
        except httpx.TimeoutException:
            raise IdentityRejected("ai_timeout") from None
        except httpx.RequestError:
            raise IdentityRejected("ai_unavailable") from None
        except IdentityRejected:
            raise
        except Exception:  # noqa: BLE001 - sanitize the integration/config boundary
            raise IdentityRejected("ai_invalid") from None

    try:
        async with asyncio.timeout(60):
            if _client is not None:
                return await send(_client)
            async with httpx.AsyncClient() as client:
                return await send(client)
    except TimeoutError:
        raise IdentityRejected("ai_timeout") from None
