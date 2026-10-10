"""Tests for GitHub REST API client (pipeline.http_client)."""

import os

import httpx
import pytest
from pipeline.http_client import (
    GitHubClient,
    TokenPool,
    get,
    get_paginated,
    load_env_file,
    resolve_tokens,
)


async def test_client_headers_and_auth(monkeypatch):
    """Verify that GitHubClient sets correct headers including Authorization."""
    recorded_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(token="secret-token-123", client=mock_httpx)
        resp = await client.get("/user")
        await client.close()

    assert resp.status_code == 200
    assert len(recorded_requests) == 1
    req = recorded_requests[0]
    assert req.headers["Authorization"] == "Bearer secret-token-123"
    assert req.headers["Accept"] == "application/vnd.github+json"
    assert req.headers["X-GitHub-Api-Version"] == "2022-11-28"
    assert str(req.url) == "https://api.github.com/user"


async def test_client_token_from_env(monkeypatch):
    """Verify token resolution from GITHUB_TOKEN and GITHUB_TOKENS env variables."""
    monkeypatch.setenv("GITHUB_TOKEN", "token-from-env")
    client = GitHubClient()
    assert client.token_pool.tokens[0].token == "token-from-env"
    await client.close()

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKENS", "token-a, token-b")
    client2 = GitHubClient()
    assert [t.token for t in client2.token_pool.tokens] == ["token-a", "token-b"]
    await client2.close()


def test_load_env_file(tmp_path, monkeypatch):
    """Verify loading key=values from .env files."""
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=bar\n# comment\nBAZ='qux'\n", encoding="utf-8")
    monkeypatch.delenv("FOO", raising=False)
    monkeypatch.delenv("BAZ", raising=False)
    loaded = load_env_file(env_file)
    assert loaded["FOO"] == "bar"
    assert loaded["BAZ"] == "qux"
    assert os.getenv("FOO") == "bar"
    assert os.getenv("BAZ") == "qux"


def test_resolve_tokens_from_env_file(tmp_path, monkeypatch):
    """Verify resolve_tokens loads GITHUB_TOKENS from specified env_file."""
    env_file = tmp_path / "tokens.env"
    env_file.write_text("GITHUB_TOKENS=t1,t2,t3\n", encoding="utf-8")
    monkeypatch.delenv("GITHUB_TOKENS", raising=False)
    tokens = resolve_tokens(env_file=env_file)
    assert tokens == ["t1", "t2", "t3"]


async def test_token_pool_401_disables_token_and_retries():
    """Verify that a 401 response permanently disables the token and retries with next token."""
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("Authorization", "")
        attempts.append(auth)
        if "bad-tok" in auth:
            return httpx.Response(401, text="Unauthorized", request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(tokens=["bad-tok", "good-tok"], client=mock_httpx)
        resp = await client.get("/auth-test")
        await client.close()

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert attempts == ["Bearer bad-tok", "Bearer good-tok"]
    assert client.token_pool.tokens[0].cooldown_until == float("inf")


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


async def test_exponential_backoff_on_5xx_eventual_success():
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
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(
            client=mock_httpx,
            sleep_fn=sleep_calls.append,
        )
        resp = await client.get("/test")
        await client.close()

    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    assert attempt_count == 3
    # Attempt 0: delay 1.0; Attempt 1: delay 2.0
    assert sleep_calls == [1.0, 2.0]


async def test_exponential_backoff_on_5xx_max_retries_exceeded():
    """Verify persistent 5xx responses exceed max_retries and raise HTTPStatusError."""
    sleep_calls: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(
            max_retries=3,
            client=mock_httpx,
            sleep_fn=sleep_calls.append,
        )
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await client.get("/test")
        await client.close()

    assert exc_info.value.response.status_code == 503
    assert sleep_calls == [1.0, 2.0, 4.0]


async def test_network_request_error_retry():
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
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx, sleep_fn=sleep_calls.append)
        resp = await client.get("/network-test")
        await client.close()

    assert resp.status_code == 200
    assert attempts == 2
    assert sleep_calls == [1.0]


async def test_rate_limit_403_and_retry():
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
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(
            client=mock_httpx,
            sleep_fn=sleep_calls.append,
            time_fn=lambda: simulated_now,
        )
        resp = await client.get("/rate-limited-endpoint")
        await client.close()

    assert resp.status_code == 200
    assert resp.json() == {"result": "data"}
    assert attempts == 2
    # 1050.0 - 1000.0 + 1.0 = 51.0 seconds
    assert sleep_calls == [51.0]


async def test_rate_limit_proactive_pause():
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
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(
            client=mock_httpx,
            sleep_fn=sleep_calls.append,
            time_fn=lambda: simulated_now,
        )
        # First call succeeds and discovers remaining is 0
        resp1 = await client.get("/first")
        assert resp1.status_code == 200
        assert sleep_calls == []

        # Before second call, client detects quota was 0 with reset at 1030
        resp2 = await client.get("/second")
        assert resp2.status_code == 200
        # Wait until 1030: 1030 - 1000 + 1.0 = 31.0
        assert sleep_calls == [31.0]
        await client.close()


async def test_client_error_404_raises_immediately():
    """Verify 4xx errors like 404 raise HTTPStatusError immediately without retrying or sleeping."""
    sleep_calls: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx, sleep_fn=sleep_calls.append)
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await client.get("/not-found")
        await client.close()

    assert exc_info.value.response.status_code == 404
    assert sleep_calls == []


async def test_pagination_single_page():
    """Verify single page responses without Link header yield exactly one page."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": 1}], request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx)
        pages = [p async for p in client.get_paginated("/items")]
        await client.close()

    assert len(pages) == 1
    assert pages[0].json() == [{"id": 1}]


async def test_pagination_multi_page_traversal():
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
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx)
        responses = [
            p
            async for p in client.get_paginated(
                "/items", params={"per_page": 1}
            )
        ]
        await client.close()

    assert len(responses) == 3
    items = [item for resp in responses for item in resp.json()]
    assert items == [{"id": 1}, {"id": 2}, {"id": 3}]


async def test_top_level_convenience_helpers(monkeypatch):
    """Verify module-level get and get_paginated helper functions."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        # Test standalone get()
        resp = await get("/test", client=mock_client)
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    async with httpx.AsyncClient(transport=transport) as mock_client2:
        # Test standalone get_paginated()
        pages = [p async for p in get_paginated("/test", client=mock_client2)]
        assert len(pages) == 1
        assert pages[0].json() == {"ok": True}


async def test_network_request_error_max_retries_exceeded():
    """Verify persistent network drops exceed max_retries and raise RequestError."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Network is down", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(
            max_retries=2, client=mock_httpx, sleep_fn=lambda _: None
        )
        with pytest.raises(httpx.RequestError):
            await client.get("/failing-network")
        await client.close()


async def test_rate_limit_fallback_wait_when_reset_missing():
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
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx, sleep_fn=sleep_calls.append)
        resp = await client.get("/missing-reset")
        await client.close()

    assert resp.status_code == 200
    assert len(sleep_calls) == 1
    assert sleep_calls[0] == pytest.approx(60.0, abs=0.1)


async def test_malformed_rate_limit_headers():
    """Verify malformed rate limit headers do not crash the client."""

    def handler(request: httpx.Request) -> httpx.Response:
        headers = {
            "X-RateLimit-Remaining": "invalid-int",
            "X-RateLimit-Reset": "invalid-float",
        }
        return httpx.Response(200, headers=headers, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx)
        resp = await client.get("/malformed")
        await client.close()

    assert resp.status_code == 200
    assert client.last_remaining is None
    assert client.last_reset is None


async def test_client_cache_hit_avoids_repeated_api_call(tmp_path):
    """Verify that repeated requests hit disk cache and do not call the API again."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"cached": True}, request=request)

    transport = httpx.MockTransport(handler)
    cache_db = tmp_path / "cache.sqlite"

    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx, cache_path=cache_db)
        # First request: cache miss, calls API
        r1 = await client.get("/repos/foo/bar")
        assert r1.status_code == 200
        assert len(calls) == 1
        assert "X-Cache" not in r1.headers

        # Second request: cache hit, does not call API
        r2 = await client.get("/repos/foo/bar")
        assert r2.status_code == 200
        assert len(calls) == 1  # No new API call!
        assert r2.headers["X-Cache"] == "HIT"
        assert r2.json() == {"cached": True}
        await client.close()


async def test_client_resumption_after_interrupted_pagination(tmp_path):
    """Verify acceptance criterion: interruption (Ctrl+C) and rerun resumes where it left off."""
    api_calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        api_calls.append(str(request.url))
        url_str = str(request.url)
        if "page=2" in url_str:
            headers = {"Link": '<https://api.github.com/runs?page=3>; rel="next"'}
            return httpx.Response(
                200, headers=headers, json=[{"run": 2}], request=request
            )
        if "page=3" in url_str:
            return httpx.Response(200, json=[{"run": 3}], request=request)
        # Page 1
        headers = {"Link": '<https://api.github.com/runs?page=2>; rel="next"'}
        return httpx.Response(200, headers=headers, json=[{"run": 1}], request=request)

    transport = httpx.MockTransport(handler)
    cache_db = tmp_path / "resumption_cache.sqlite"

    # --- Run 1: Interrupted after page 2 (simulating Ctrl+C midway) ---
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client1 = GitHubClient(client=mock_httpx, cache_path=cache_db)
        gen = client1.get_paginated("/runs")
        p1 = await anext(gen)
        assert p1.json() == [{"run": 1}]
        p2 = await anext(gen)
        assert p2.json() == [{"run": 2}]
        await gen.aclose()
        await client1.close()

    assert len(api_calls) == 2
    assert api_calls == [
        "https://api.github.com/runs",
        "https://api.github.com/runs?page=2",
    ]

    # --- Run 2: Restart pipeline with the same cache database ---
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client2 = GitHubClient(client=mock_httpx, cache_path=cache_db)
        all_pages = [p async for p in client2.get_paginated("/runs")]
        await client2.close()

    assert len(all_pages) == 3
    all_runs = [item for page in all_pages for item in page.json()]
    assert all_runs == [{"run": 1}, {"run": 2}, {"run": 3}]

    assert len(api_calls) == 3
    assert api_calls[2] == "https://api.github.com/runs?page=3"
    assert all_pages[0].headers["X-Cache"] == "HIT"
    assert all_pages[1].headers["X-Cache"] == "HIT"
    assert "X-Cache" not in all_pages[2].headers


async def test_client_force_refresh_bypasses_cache(tmp_path):
    """Verify force_refresh=True ignores cached entry and re-fetches from network."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"version": len(calls)}, request=request)

    transport = httpx.MockTransport(handler)
    cache_db = tmp_path / "cache.sqlite"

    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx, cache_path=cache_db)
        r1 = await client.get("/data")
        assert r1.json() == {"version": 1}
        assert len(calls) == 1

        # With force_refresh=True, it must query the API
        r2 = await client.get("/data", force_refresh=True)
        assert r2.json() == {"version": 2}
        assert len(calls) == 2
        await client.close()


async def test_client_cache_disabled_with_none_path():
    """Verify cache_path=None disables caching entirely."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(client=mock_httpx, cache_path=None)
        assert client.cache is None
        await client.get("/endpoint")
        await client.get("/endpoint")
        assert len(calls) == 2
        await client.close()


async def test_token_pool_rotation_and_cooldown():
    """Verify TokenPool round-robin rotation across multiple tokens and cooldown on 403."""
    recorded_tokens = []

    def handler(request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "")
        recorded_tokens.append(token)
        if token == "tok1" and len(recorded_tokens) == 1:
            return httpx.Response(
                403,
                headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "2000"},
                text="Rate limit exceeded",
                request=request,
            )
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(
            tokens=["tok1", "tok2"],
            client=mock_httpx,
            time_fn=lambda: 1000.0,
        )
        # First request uses tok1 -> gets 403 -> puts tok1 on cooldown -> retries with tok2 -> succeeds
        resp1 = await client.get("/test1")
        assert resp1.status_code == 200

        # Second request: tok1 still cooling down -> uses tok2 directly -> succeeds
        resp2 = await client.get("/test2")
        assert resp2.status_code == 200

    assert recorded_tokens == ["tok1", "tok2", "tok2"]


async def test_client_graphql_success():
    """Verify GitHubClient.graphql executes POST /graphql with JSON payload and returns data."""
    recorded_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(
            200,
            json={"data": {"repository": {"name": "test-repo", "stargazerCount": 42}}},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(token="tok-gql", client=mock_httpx)
        data = await client.graphql("query { repository { name } }", variables={"owner": "foo"})
        await client.close()

    assert data["data"]["repository"]["name"] == "test-repo"
    assert len(recorded_requests) == 1
    req = recorded_requests[0]
    assert req.method == "POST"
    assert str(req.url) == "https://api.github.com/graphql"
    assert req.headers["Authorization"] == "Bearer tok-gql"
    assert req.headers["Content-Type"] == "application/json"


async def test_client_graphql_errors_raise():
    """Verify GitHubClient.graphql raises GraphQLError when errors are present and data is missing."""
    from pipeline.http_client import GraphQLError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"errors": [{"message": "Field not found"}]},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = GitHubClient(token="tok-gql", client=mock_httpx)
        with pytest.raises(GraphQLError) as excinfo:
            await client.graphql("query { badField }")
        await client.close()

    assert "Field not found" in str(excinfo.value)


async def test_client_http2_enforce_fail_loud():
    """Verify that fail-loud policy raises RuntimeError when HTTP/2 negotiation fails against api.github.com."""
    def handler(request: httpx.Request) -> httpx.Response:
        # MockTransport returns HTTP/1.1 response
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        # Explicitly enforce HTTP/2
        client = GitHubClient(client=mock_httpx, enforce_http2=True)
        with pytest.raises(RuntimeError) as excinfo:
            await client.get("/zen")
        await client.close()

    assert "HTTP/2 negotiation failed" in str(excinfo.value)


async def test_client_http2_configuration_defaults():
    """Verify that client initializes with HTTP/2 enabled and expected limits."""
    client = GitHubClient(token="tok")
    # Underlying httpx client should have http2 enabled
    assert client.enforce_http2 is True
    await client.close()

