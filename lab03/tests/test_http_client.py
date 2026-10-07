"""Tests for GitHub REST API client (pipeline.http_client)."""

import httpx
import pytest
from pipeline.http_client import GitHubClient, get, get_paginated


def test_client_headers_and_auth(monkeypatch):
    """Verify that GitHubClient sets correct headers including Authorization."""
    recorded_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_httpx:
        client = GitHubClient(token="secret-token-123", client=mock_httpx)
        resp = client.get("/user")

    assert resp.status_code == 200
    assert len(recorded_requests) == 1
    req = recorded_requests[0]
    assert req.headers["Authorization"] == "Bearer secret-token-123"
    assert req.headers["Accept"] == "application/vnd.github+json"
    assert req.headers["X-GitHub-Api-Version"] == "2022-11-28"
    assert str(req.url) == "https://api.github.com/user"


def test_client_token_from_env(monkeypatch):
    """Verify token resolution from GITHUB_TOKEN and GITHUB_TOKENS env variables."""
    monkeypatch.setenv("GITHUB_TOKEN", "token-from-env")
    client = GitHubClient()
    assert client._client.headers["Authorization"] == "Bearer token-from-env"

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKENS", "token-a, token-b")
    client2 = GitHubClient()
    assert client2._client.headers["Authorization"] == "Bearer token-a"


def test_resolve_relative_and_absolute_urls():
    """Verify relative endpoints are resolved against base_url while absolute URLs remain untouched."""
    client = GitHubClient(base_url="https://api.github.com")
    assert (
        client._resolve_url("repos/owner/repo")
        == "https://api.github.com/repos/owner/repo"
    )
    assert (
        client._resolve_url("/repos/owner/repo")
        == "https://api.github.com/repos/owner/repo"
    )
    assert (
        client._resolve_url("https://custom.api/repos/foo")
        == "https://custom.api/repos/foo"
    )


def test_exponential_backoff_on_5xx_eventual_success():
    """Verify 5xx responses trigger exponential backoff delays and retry until success."""
    sleep_calls: list[float] = []
    attempt_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            return httpx.Response(500, request=request)
        if attempt_count == 2:
            return httpx.Response(502, request=request)
        return httpx.Response(200, json={"success": True}, request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_httpx:
        client = GitHubClient(
            client=mock_httpx,
            sleep_fn=sleep_calls.append,
        )
        resp = client.get("/test")

    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    assert attempt_count == 3
    # Attempt 0: delay 1.0; Attempt 1: delay 2.0
    assert sleep_calls == [1.0, 2.0]


def test_exponential_backoff_on_5xx_max_retries_exceeded():
    """Verify persistent 5xx responses exceed max_retries and raise HTTPStatusError."""
    sleep_calls: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_httpx:
        client = GitHubClient(
            max_retries=3,
            client=mock_httpx,
            sleep_fn=sleep_calls.append,
        )
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            client.get("/test")

    assert exc_info.value.response.status_code == 503
    assert sleep_calls == [1.0, 2.0, 4.0]


def test_network_request_error_retry():
    """Verify network drops (RequestError) retry with backoff and succeed."""
    sleep_calls: list[float] = []
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("Connection lost", request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx, sleep_fn=sleep_calls.append)
        resp = client.get("/network-test")

    assert resp.status_code == 200
    assert attempts == 2
    assert sleep_calls == [1.0]


def test_rate_limit_403_and_retry():
    """Verify that a 403 response with remaining=0 calculates sleep until reset + 1s and retries."""
    sleep_calls: list[float] = []
    attempts = 0
    simulated_now = 1000.0
    reset_epoch = 1050.0  # 50 seconds in the future

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            headers = {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_epoch)),
            }
            return httpx.Response(
                403,
                headers=headers,
                text="API rate limit exceeded",
                request=request,
            )
        return httpx.Response(200, json={"result": "data"}, request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_httpx:
        client = GitHubClient(
            client=mock_httpx,
            sleep_fn=sleep_calls.append,
            time_fn=lambda: simulated_now,
        )
        resp = client.get("/rate-limited-endpoint")

    assert resp.status_code == 200
    assert resp.json() == {"result": "data"}
    assert attempts == 2
    # 1050.0 - 1000.0 + 1.0 = 51.0 seconds
    assert sleep_calls == [51.0]


def test_rate_limit_proactive_pause():
    """Verify proactive rate-limit sleep when client knows quota is exhausted before call."""
    sleep_calls: list[float] = []
    simulated_now = 1000.0

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/first":
            return httpx.Response(
                200,
                headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1030"},
                json={"first": True},
                request=request,
            )
        return httpx.Response(200, json={"second": True}, request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_httpx:
        client = GitHubClient(
            client=mock_httpx,
            sleep_fn=sleep_calls.append,
            time_fn=lambda: simulated_now,
        )
        # First call succeeds and discovers remaining is 0
        resp1 = client.get("/first")
        assert resp1.status_code == 200
        assert sleep_calls == []

        # Before second call, client detects quota was 0 with reset at 1030
        resp2 = client.get("/second")
        assert resp2.status_code == 200
        # Wait until 1030: 1030 - 1000 + 1.0 = 31.0
        assert sleep_calls == [31.0]


def test_client_error_404_raises_immediately():
    """Verify 4xx errors like 404 raise HTTPStatusError immediately without retrying or sleeping."""
    sleep_calls: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx, sleep_fn=sleep_calls.append)
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            client.get("/not-found")

    assert exc_info.value.response.status_code == 404
    assert sleep_calls == []


def test_pagination_single_page():
    """Verify single page responses without Link header yield exactly one page."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": 1}], request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx)
        pages = list(client.get_paginated("/items"))

    assert len(pages) == 1
    assert pages[0].json() == [{"id": 1}]


def test_pagination_multi_page_traversal():
    """Verify multi-page traversal seamlessly follows RFC 5988 Link headers."""

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "page=2" in url_str:
            headers = {"Link": '<https://api.github.com/items?page=3>; rel="next"'}
            return httpx.Response(
                200, headers=headers, json=[{"id": 2}], request=request
            )
        if "page=3" in url_str:
            return httpx.Response(200, json=[{"id": 3}], request=request)
        # First page
        headers = {
            "Link": '<https://api.github.com/items?page=2>; rel="next", <https://api.github.com/items?page=3>; rel="last"'
        }
        return httpx.Response(200, headers=headers, json=[{"id": 1}], request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx)
        responses = list(client.get_paginated("/items", params={"per_page": 1}))

    assert len(responses) == 3
    items = [item for resp in responses for item in resp.json()]
    assert items == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_top_level_convenience_helpers(monkeypatch):
    """Verify module-level get and get_paginated helper functions."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=transport)

    # Test standalone get()
    resp = get("/test", client=mock_client)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    # Test standalone get_paginated()
    mock_client2 = httpx.Client(transport=transport)
    pages = list(get_paginated("/test", client=mock_client2))
    assert len(pages) == 1
    assert pages[0].json() == {"ok": True}


def test_network_request_error_max_retries_exceeded():
    """Verify persistent network drops exceed max_retries and raise RequestError."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Network is down", request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_httpx:
        client = GitHubClient(max_retries=2, client=mock_httpx, sleep_fn=lambda _: None)
        with pytest.raises(httpx.RequestError):
            client.get("/failing-network")


def test_rate_limit_fallback_wait_when_reset_missing():
    """Verify fallback sleep of 60s when reset timestamp header is missing."""
    sleep_calls: list[float] = []
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            # 403 with remaining 0 but NO reset header
            return httpx.Response(
                403, headers={"X-RateLimit-Remaining": "0"}, request=request
            )
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx, sleep_fn=sleep_calls.append)
        resp = client.get("/missing-reset")

    assert resp.status_code == 200
    assert sleep_calls == [60.0]


def test_malformed_rate_limit_headers():
    """Verify malformed rate limit headers do not crash the client."""

    def handler(request: httpx.Request) -> httpx.Response:
        headers = {
            "X-RateLimit-Remaining": "invalid-int",
            "X-RateLimit-Reset": "invalid-float",
        }
        return httpx.Response(200, headers=headers, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx)
        resp = client.get("/malformed")

    assert resp.status_code == 200
    assert client.last_remaining is None
    assert client.last_reset is None
