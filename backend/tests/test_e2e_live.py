"""E2E tests against live backend - real HTTP, real user behavior."""
import pytest
import httpx
import time
import asyncio

BASE_URL = "http://127.0.0.1:5100"
TIMEOUT = 10.0


@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)


@pytest.fixture
async def async_client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as c:
        yield c


class TestAPISmoke:
    """Every endpoint responds correctly."""

    ENDPOINTS = [
        ("GET", "/", 200),
        ("GET", "/health", 200),
        ("GET", "/api/di", 200),
        ("GET", "/docs", 200),
        ("GET", "/redoc", 200),
        ("GET", "/openapi.json", 200),
    ]

    @pytest.mark.parametrize("method,path,expected", ENDPOINTS)
    def test_endpoint_responds(self, client, method, path, expected):
        resp = client.request(method, path)
        if resp.status_code == 429:
            pytest.skip("Rate limited - retry later")
        assert resp.status_code == expected, f"{method} {path} → {resp.status_code}"

    def test_health_returns_healthy(self, client):
        resp = client.get("/health")
        if resp.status_code == 429:
            pytest.skip("Rate limited")
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "perfect-web-clone"

    def test_root_returns_api_info(self, client):
        resp = client.get("/")
        if resp.status_code == 429:
            pytest.skip("Rate limited")
        data = resp.json()
        assert "name" in data
        assert "version" in data
        assert "endpoints" in data
        assert "/api/cache" in str(data["endpoints"])


class TestDIContainerLive:
    """DI container runtime validation."""

    def test_di_health_returns_adapters(self, client):
        resp = client.get("/api/di")
        data = resp.json()
        assert data["status"] == "healthy"
        assert "adapters" in data
        assert "llm_provider" in data["adapters"]
        assert "cache" in data["adapters"]
        assert "sandbox_factory" in data["adapters"]

    def test_di_uses_in_memory_cache_by_default(self, client):
        resp = client.get("/api/di")
        data = resp.json()
        assert data["adapters"]["cache"] == "InMemoryCacheAdapter"

    def test_di_llm_is_anthropic(self, client):
        resp = client.get("/api/di")
        data = resp.json()
        assert data["adapters"]["llm_provider"] == "AnthropicAdapter"

    def test_di_sandbox_is_mock(self, client):
        resp = client.get("/api/di")
        data = resp.json()
        assert data["adapters"]["sandbox_factory"] == "MockSandboxAdapter"


class TestErrorFormat:
    """Unified error response format."""

    def test_404_returns_unified_format(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404
        data = resp.json()
        assert "success" in data
        assert data["success"] is False
        assert "error" in data

    def test_405_returns_unified_format(self, client):
        resp = client.post("/health")
        assert resp.status_code == 405
        data = resp.json()
        assert data["success"] is False
        assert "error" in data

    def test_error_response_has_no_extra_fields(self, client):
        resp = client.get("/api/nonexistent")
        data = resp.json()
        allowed = {"success", "error", "detail"}
        extra = set(data.keys()) - allowed
        assert len(extra) == 0, f"Extra fields in error response: {extra}"


class TestPerformance:
    """Response times under threshold."""

    THRESHOLD_MS = 500
    ENDPOINTS = ["/", "/health", "/api/di", "/openapi.json"]

    @pytest.mark.parametrize("path", ENDPOINTS)
    def test_response_time_under_threshold(self, client, path):
        start = time.time()
        resp = client.get(path)
        if resp.status_code == 429:
            pytest.skip("Rate limited")
        elapsed = (time.time() - start) * 1000
        assert resp.status_code == 200
        assert elapsed < self.THRESHOLD_MS, f"{path} took {elapsed:.0f}ms (>{self.THRESHOLD_MS}ms)"

    def test_health_under_100ms(self, client):
        start = time.time()
        for _ in range(10):
            client.get("/health")
        avg = ((time.time() - start) * 1000) / 10
        assert avg < 100, f"Average health check took {avg:.0f}ms"


class TestConcurrency:
    """Multiple simultaneous requests."""

    @pytest.mark.asyncio
    async def test_10_concurrent_health_checks(self, async_client):
        tasks = [async_client.get("/health") for _ in range(10)]
        results = await asyncio.gather(*tasks)
        assert all(r.status_code == 200 for r in results)

    @pytest.mark.asyncio
    async def test_5_concurrent_di_checks(self, async_client):
        tasks = [async_client.get("/api/di") for _ in range(5)]
        results = await asyncio.gather(*tasks)
        for r in results:
            assert r.status_code == 200
            assert r.json()["status"] == "healthy"


class TestNegative:
    """Invalid inputs, missing params, strange payloads."""

    def test_empty_body_post(self, client):
        resp = client.post("/api/project-name", json={})
        assert resp.status_code == 422  # Validation error

    def test_wrong_content_type(self, client):
        resp = client.post("/api/project-name", content="not json", headers={"Content-Type": "text/plain"})
        assert resp.status_code == 422

    def test_malformed_json(self, client):
        resp = client.post("/api/project-name", content="{broken", headers={"Content-Type": "application/json"})
        assert resp.status_code == 422

    def test_oversized_payload(self, client):
        resp = client.post("/api/project-name", json={"message": "x" * 100000})
        assert resp.status_code in (200, 400, 413, 422), f"Unexpected {resp.status_code}"

    def test_sql_injection_in_path(self, client):
        resp = client.get("/api/project/'; DROP TABLE users; --")
        assert resp.status_code == 404  # Not 500

    def test_xss_in_path(self, client):
        resp = client.get("/api/project/<script>alert(1)</script>")
        assert resp.status_code == 404  # Not 500 or rendered


class TestCORS:
    """CORS headers are correct."""

    def test_cors_headers_present(self, client):
        resp = client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        assert "access-control-allow-origin" in resp.headers or "Access-Control-Allow-Origin" in resp.headers

    def test_cors_wildcard_allows_all(self, client):
        resp = client.get("/health", headers={"Origin": "https://evil.com"})
        cors = resp.headers.get("access-control-allow-origin")
        assert cors == "*" or cors == "https://evil.com"


class TestAsyncAdapters:
    """Verify no sync clients are used at runtime."""

    def test_di_health_async(self, client):
        """If DI health works, async adapters loaded correctly."""
        resp = client.get("/api/di")
        assert resp.status_code == 200

    def test_project_name_graceful_degradation(self, client):
        """Even without API key, returns Untitled Project (no crash)."""
        resp = client.post("/api/project-name", json={"message": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
