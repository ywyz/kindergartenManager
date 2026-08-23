"""设置页 use-case 测试。"""


async def test_verify_saved_ai_connection_requires_scoped_configuration(async_session):
    from app.service.settings_service import verify_saved_ai_connection

    result = await verify_saved_ai_connection(
        async_session,
        tenant_id=1,
        user_id=1,
        key_type="text",
    )

    assert result.code == "not_configured"


async def test_verify_saved_ai_connection_passes_decrypted_key_to_adapter(async_session):
    from app.integration.ai_client.model_catalog import AiEndpointCheck
    from app.repository.ai_key_repository import save_ai_key
    from app.service.settings_service import verify_saved_ai_connection

    await save_ai_key(
        async_session,
        tenant_id=1,
        user_id=1,
        api_base_url="https://ai.example/v1",
        plain_api_key="fictional-test-key",
        key_type="vision",
    )
    captured: dict[str, str] = {}

    async def verifier(api_base_url: str, api_key: str) -> AiEndpointCheck:
        captured["api_base_url"] = api_base_url
        captured["api_key"] = api_key
        return AiEndpointCheck(code="ok", http_status=200)

    result = await verify_saved_ai_connection(
        async_session,
        tenant_id=1,
        user_id=1,
        key_type="vision",
        verifier=verifier,
    )

    assert result.code == "ok"
    assert captured == {
        "api_base_url": "https://ai.example/v1",
        "api_key": "fictional-test-key",
    }
