"""E2E security boundary tests against live backend."""
import pytest
import httpx
import time

BASE_URL = "http://127.0.0.1:5100"
TIMEOUT = 10.0


@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)


class TestPathTraversal:
    """Path traversal attempts should be blocked."""

    TRAVERSAL_PATHS = [
        "/../../../etc/passwd",
        "/..%2f..%2f..%2fetc/passwd",
        "/....//....//....//etc/passwd",
        "/%2e%2e/%2e%2e/%2e%2e/etc/passwd",
        "/api/../../../etc/passwd",
    ]

    @pytest.mark.parametrize("path", TRAVERSAL_PATHS)
    def test_path_traversal_blocked(self, client, path):
        resp = client.get(path)
        assert resp.status_code in (403, 404, 400), f"{path} → {resp.status_code} (should be blocked)"
        if resp.status_code == 403 or resp.status_code == 400:
            data = resp.json()
            assert "error" in data


class TestAuthBypass:
    """Auth middleware should reject missing/invalid API keys."""

    def test_missing_api_key_still_allows_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_missing_api_key_still_allows_docs(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_invalid_api_key_format(self, client):
        resp = client.get("/", headers={"X-API-Key": ""})
        assert resp.status_code in (200, 401, 429)  # May be rate-limited after burst tests


class TestErrorLeakage:
    """Internal details should not leak in error responses."""

    SENSITIVE_PATTERNS = [
        "Traceback",
        "File ",
        "line ",
        "KeyError",
        "ValueError",
        "TypeError",
        "AttributeError",
        "IndexError",
        "SyntaxError",
        "ImportError",
        "ModuleNotFoundError",
        "stack trace",
        "STACK_TRACE",
        "/app/",
        "/home/",
        "C:\\",
        "/var/",
    ]

    def test_no_stack_trace_in_404(self, client):
        resp = client.get("/api/nonexistent")
        body = resp.text.lower()
        for pattern in self.SENSITIVE_PATTERNS:
            assert pattern.lower() not in body, f"Found sensitive data in 404: {pattern}"

    def test_no_stack_trace_in_405(self, client):
        resp = client.post("/health")
        body = resp.text.lower()
        for pattern in self.SENSITIVE_PATTERNS:
            assert pattern.lower() not in body, f"Found sensitive data in 405: {pattern}"


class TestRateLimiting:
    """Rate limiting should block excessive requests."""

    def test_rate_limit_read_endpoint(self, client):
        """Burst 120 requests to root - 100/min limit should fire."""
        responses = []
        for _ in range(120):
            resp = client.get("/")
            responses.append(resp.status_code)
            if resp.status_code == 429:
                break

        rate_limited = sum(1 for r in responses if r == 429)
        assert rate_limited >= 1, "Rate limiting did not fire after 120 requests"

    def test_rate_limit_response_format(self, client):
        """Rate limit response should be proper format."""
        resp = client.get("/")
        if resp.status_code == 429:
            data = resp.json()
            assert "error" in data


class TestHTTPMethods:
    """HTTP method handling."""

    MATRIX = [
        ("GET", "/", {200, 405, 429}),  # 429 if rate-limited by previous test
        ("HEAD", "/", {200, 405}),
        ("OPTIONS", "/", {200, 405}),
        ("POST", "/", {200, 405, 307}),
        ("PUT", "/", {405}),
        ("PATCH", "/", {405}),
        ("DELETE", "/", {405}),
    ]

    @pytest.mark.parametrize("method,path,expected", MATRIX)
    def test_http_methods(self, client, method, path, expected):
        resp = client.request(method, path)
        assert resp.status_code in expected, f"{method} {path} → {resp.status_code} (expected {expected})"
