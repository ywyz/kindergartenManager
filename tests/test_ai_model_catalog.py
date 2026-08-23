"""设置页 AI 模型端点连接 adapter 测试。"""
import httpx


async def test_check_ai_endpoint_uses_models_path_and_bearer_header():
    from app.integration.ai_client.model_catalog import check_ai_endpoint

    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        return httpx.Response(200, json={"data": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await check_ai_endpoint(
            "https://ai.example/v1/",
            "fictional-test-key",
            client=client,
        )

    assert result.code == "ok"
    assert result.http_status == 200
    assert captured == {
        "url": "https://ai.example/v1/models",
        "authorization": "Bearer fictional-test-key",
    }


async def test_check_ai_endpoint_returns_sanitized_http_failure():
    from app.integration.ai_client.model_catalog import check_ai_endpoint

    transport = httpx.MockTransport(lambda request: httpx.Response(503, text="secret body"))
    async with httpx.AsyncClient(transport=transport) as client:
        result = await check_ai_endpoint(
            "https://ai.example/v1",
            "fictional-test-key",
            client=client,
        )

    assert result.code == "http_error"
    assert result.http_status == 503
    assert "secret" not in repr(result)


async def test_check_ai_endpoint_returns_sanitized_timeout():
    from app.integration.ai_client.model_catalog import check_ai_endpoint

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out with sensitive request", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await check_ai_endpoint(
            "https://ai.example/v1",
            "fictional-test-key",
            client=client,
        )

    assert result.code == "timeout"
    assert result.http_status is None
    assert "sensitive" not in repr(result)
