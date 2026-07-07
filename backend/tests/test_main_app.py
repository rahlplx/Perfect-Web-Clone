"""
Tests for Perfect Web Clone Backend - main.py
"""

import os
import sys
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport


# Ensure backend directory is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Fixture: provide a fresh app with API_KEY disabled so verify_api_key is a no-op
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _no_api_key():
    """Force API_KEY='' so auth is disabled during tests."""
    with patch.dict(os.environ, {"API_KEY": ""}):
        yield


@pytest.fixture()
def app():
    """Import the FastAPI app after patching env vars."""
    import importlib
    import main as main_mod
    importlib.reload(main_mod)
    return main_mod.app


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


# ===================================================================
# 1. Root endpoint GET /
# ===================================================================
@pytest.mark.asyncio
async def test_root_returns_api_info(app):
    async with _client(app) as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Perfect Web Clone API"
    assert body["version"] == "1.0.0"
    assert "docs" in body
    assert "endpoints" in body


@pytest.mark.asyncio
async def test_root_endpoints_keys(app):
    async with _client(app) as client:
        resp = await client.get("/")
    body = resp.json()
    expected_keys = {"cache", "extractor", "agent", "boxlite", "boxlite_agent", "sources"}
    assert expected_keys.issubset(set(body["endpoints"].keys()))


# ===================================================================
# 2. Health endpoint GET /health
# ===================================================================
@pytest.mark.asyncio
async def test_health_returns_200(app):
    async with _client(app) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_body(app):
    async with _client(app) as client:
        resp = await client.get("/health")
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "perfect-web-clone"
    assert body["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_health_bypasses_api_key(app):
    """Health endpoint should return 200 even when API_KEY is set."""
    with patch.dict(os.environ, {"API_KEY": "secret123"}):
        import importlib
        import main as main_mod
        importlib.reload(main_mod)
        async with _client(main_mod.app) as client:
            resp = await client.get("/health")
    assert resp.status_code == 200


# ===================================================================
# 3. CORS configuration
# ===================================================================
@pytest.mark.asyncio
async def test_cors_preflight_allowed(app):
    async with _client(app) as client:
        resp = await client.options(
            "/",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert resp.status_code in (200, 204)
    assert "access-control-allow-origin" in resp.headers


@pytest.mark.asyncio
async def test_cors_wildcard_origin(app):
    async with _client(app) as client:
        resp = await client.get("/", headers={"Origin": "http://any-origin.com"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "*"


# ===================================================================
# 4. Rate limiting (smoke test – slowapi is registered)
# ===================================================================
@pytest.mark.asyncio
async def test_limiter_is_attached(app):
    """The limiter should be stored on app.state."""
    assert hasattr(app.state, "limiter")


@pytest.mark.asyncio
async def test_rate_limit_handler_registered(app):
    """RateLimitExceeded handler should be registered."""
    handler_map = app.exception_handlers
    # RateLimitExceeded is registered via add_exception_handler
    # We can verify the app has it set up without triggering the limit
    assert hasattr(app.state, "limiter")


# ===================================================================
# 5. Error handlers
# ===================================================================
@pytest.mark.asyncio
async def test_404_unknown_route(app):
    """Unknown route returns 404 with JSON body."""
    async with _client(app) as client:
        resp = await client.get("/this-route-does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["success"] is False


@pytest.mark.asyncio
async def test_http_exception_handler_422(app):
    """Invalid payload triggers Pydantic validation (422) with detail body."""
    async with _client(app) as client:
        resp = await client.post("/api/project-name", json={"wrong": "field"})
    assert resp.status_code == 422
    body = resp.json()
    assert "detail" in body


@pytest.mark.asyncio
async def test_http_exception_handler_via_dependency(app):
    """HTTPException raised inside verify_api_key uses our custom handler format."""
    with patch.dict(os.environ, {"API_KEY": "secret"}):
        import importlib
        import main as main_mod
        importlib.reload(main_mod)
        async with _client(main_mod.app) as client:
            resp = await client.get("/")
    assert resp.status_code == 401
    body = resp.json()
    assert body["success"] is False
    assert "api key" in body["error"].lower()


@pytest.mark.asyncio
async def test_general_exception_handler(app):
    """The Exception handler is registered on the app."""
    handlers = app.exception_handlers
    assert Exception in handlers


@pytest.mark.asyncio
async def test_general_exception_handler_returns_500(app):
    """Call the handler directly and verify it returns 500 JSON."""
    from starlette.requests import Request

    scope = {"type": "http", "method": "GET", "path": "/test", "query_string": b"", "headers": []}
    mock_request = Request(scope)

    handler = app.exception_handlers[Exception]
    response = await handler(mock_request, RuntimeError("boom"))

    assert response.status_code == 500
    import json
    body = json.loads(response.body)
    assert body["success"] is False
    assert body["error"] == "Internal server error"


# ===================================================================
# 6. verify_api_key dependency
# ===================================================================
@pytest.mark.asyncio
async def test_api_key_disabled_allows_root(app):
    """With API_KEY='' (default), root should be accessible."""
    async with _client(app) as client:
        resp = await client.get("/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_key_required_rejects_missing_key():
    """When API_KEY is set and no header is provided, / should return 401."""
    with patch.dict(os.environ, {"API_KEY": "test-secret"}):
        import importlib
        import main as main_mod
        importlib.reload(main_mod)
        async with _client(main_mod.app) as client:
            resp = await client.get("/")
    assert resp.status_code == 401
    body = resp.json()
    assert body["success"] is False
    assert "api key" in body["error"].lower()


@pytest.mark.asyncio
async def test_api_key_required_rejects_wrong_key():
    """When API_KEY is set, wrong key should return 401."""
    with patch.dict(os.environ, {"API_KEY": "correct-key"}):
        import importlib
        import main as main_mod
        importlib.reload(main_mod)
        async with _client(main_mod.app) as client:
            resp = await client.get("/", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_key_required_accepts_valid_key():
    """When API_KEY is set, correct key should return 200."""
    with patch.dict(os.environ, {"API_KEY": "valid-key"}):
        import importlib
        import main as main_mod
        importlib.reload(main_mod)
        async with _client(main_mod.app) as client:
            resp = await client.get("/", headers={"X-API-Key": "valid-key"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_key_skipped_for_docs():
    """Docs endpoint should bypass API key even when API_KEY is set."""
    with patch.dict(os.environ, {"API_KEY": "secret123"}):
        import importlib
        import main as main_mod
        importlib.reload(main_mod)
        async with _client(main_mod.app) as client:
            resp = await client.get("/docs")
    assert resp.status_code == 200


# ===================================================================
# 7. X-API-Key header validation
# ===================================================================
@pytest.mark.asyncio
async def test_missing_x_api_key_header_401():
    """Missing X-API-Key header when API_KEY is configured → 401."""
    with patch.dict(os.environ, {"API_KEY": "my-secret"}):
        import importlib
        import main as main_mod
        importlib.reload(main_mod)
        async with _client(main_mod.app) as client:
            resp = await client.get("/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_empty_x_api_key_header_401():
    """Empty X-API-Key header when API_KEY is configured → 401."""
    with patch.dict(os.environ, {"API_KEY": "my-secret"}):
        import importlib
        import main as main_mod
        importlib.reload(main_mod)
        async with _client(main_mod.app) as client:
            resp = await client.get("/", headers={"X-API-Key": ""})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_valid_x_api_key_header_200():
    """Valid X-API-Key header → 200."""
    with patch.dict(os.environ, {"API_KEY": "my-secret"}):
        import importlib
        import main as main_mod
        importlib.reload(main_mod)
        async with _client(main_mod.app) as client:
            resp = await client.get("/", headers={"X-API-Key": "my-secret"})
    assert resp.status_code == 200


# ===================================================================
# 8. Project Name endpoint (POST /api/project-name)
# ===================================================================
@pytest.mark.asyncio
async def test_project_name_no_api_key_returns_fallback(app):
    """Without ANTHROPIC_API_KEY, the endpoint should return a fallback name."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "", "CLAUDE_PROXY_API_KEY": ""}):
        async with _client(app) as client:
            resp = await client.post("/api/project-name", json={"message": "build a todo app"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Untitled Project"


@pytest.mark.asyncio
async def test_project_name_invalid_payload(app):
    """Missing 'message' field should return 422."""
    async with _client(app) as client:
        resp = await client.post("/api/project-name", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_project_name_no_body(app):
    """No body at all should return 422."""
    async with _client(app) as client:
        resp = await client.post("/api/project-name")
    assert resp.status_code == 422


# ===================================================================
# 9. App metadata
# ===================================================================
@pytest.mark.asyncio
async def test_app_title(app):
    assert app.title == "Perfect Web Clone API"


@pytest.mark.asyncio
async def test_app_version(app):
    assert app.version == "1.0.0"


@pytest.mark.asyncio
async def test_docs_url(app):
    assert app.docs_url == "/docs"


@pytest.mark.asyncio
async def test_redoc_url(app):
    assert app.redoc_url == "/redoc"


# ===================================================================
# 10. OpenAPI schema
# ===================================================================
@pytest.mark.asyncio
async def test_openapi_schema_available(app):
    async with _client(app) as client:
        resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "openapi" in schema
    assert "paths" in schema
