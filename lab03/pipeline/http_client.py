"""Async GitHub REST API client with Link-header pagination, Token Rotation pool, and rate limit backoff."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

import httpx

from pipeline.cache import HttpCache

logger = logging.getLogger(__name__)


class GraphQLError(Exception):
    """Raised when GitHub GraphQL returns errors."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__(f"GraphQL error: {errors}")
        self.errors = errors


@dataclass
class TokenState:
    """Tracks rate limit state and cooldown for a single GitHub API token."""

    token: str
    remaining: int | None = None
    reset_ts: float | None = None
    cooldown_until: float = 0.0


class TokenPool:
    """Manages a pool of GitHub tokens with round-robin rotation and dynamic cooldown."""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens: list[TokenState] = [
            TokenState(token=t) for t in tokens if t.strip()
        ]
        self._current_index = 0
        self._lock = asyncio.Lock()

    @property
    def has_tokens(self) -> bool:
        return len(self.tokens) > 0

    @property
    def count(self) -> int:
        return len(self.tokens)

    async def get_next_token(
        self,
        time_fn: Callable[[], float] = time.time,
        sleep_fn: Callable[[float], Any] = asyncio.sleep,
    ) -> str | None:
        """Select next available token via round-robin, skipping tokens in cooldown."""
        if not self.tokens:
            return None

        async with self._lock:
            now = time_fn()
            # Filter out permanently disabled tokens (e.g. 401 Unauthorized)
            candidates = [t for t in self.tokens if t.cooldown_until != float("inf")]
            if not candidates:
                return None

            num_tokens = len(candidates)
            for _ in range(num_tokens):
                candidate = candidates[self._current_index % num_tokens]
                self._current_index = (self._current_index + 1) % num_tokens
                if candidate.cooldown_until <= now:
                    return candidate.token

            # All active tokens currently cooling down: find earliest reset and wait
            earliest_reset = min(t.cooldown_until for t in candidates)
            wait_time = max(0.0, earliest_reset - now)

            logger.warning(
                "All %d tokens in cooldown. Waiting %.1fs until earliest reset.",
                num_tokens,
                wait_time,
            )
            res = sleep_fn(wait_time)
            if asyncio.iscoroutine(res):
                await res

            # Token with earliest reset has now cooled down
            for t in candidates:
                if t.cooldown_until <= earliest_reset:
                    t.cooldown_until = 0.0
                    return t.token

            return candidates[0].token

    async def update_state(
        self,
        token_str: str,
        response: httpx.Response,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        """Record rate limit response headers and trigger cooldown if quota exhausted."""
        async with self._lock:
            target = next((t for t in self.tokens if t.token == token_str), None)
            if target is None:
                return

            if response.status_code == 401:
                target.cooldown_until = float("inf")
                logger.error(
                    "Token %s... returned 401 Unauthorized. Permanently disabled from pool.",
                    token_str[:8],
                )
                return

            remaining_hdr = response.headers.get("X-RateLimit-Remaining")
            reset_hdr = response.headers.get("X-RateLimit-Reset")

            if remaining_hdr is not None:
                try:
                    target.remaining = int(remaining_hdr)
                except ValueError:
                    pass

            if reset_hdr is not None:
                try:
                    target.reset_ts = float(reset_hdr)
                except ValueError:
                    pass

            # Detect rate limit depletion
            is_limited = (
                response.status_code in (403, 429)
                and (target.remaining == 0 or "rate limit" in response.text.lower())
            ) or (target.remaining is not None and target.remaining <= 0)

            if is_limited:
                now = time_fn()
                if target.reset_ts is not None and target.reset_ts > now:
                    target.cooldown_until = target.reset_ts + 1.0
                else:
                    target.cooldown_until = now + 60.0
                logger.warning(
                    "Token %s... quota exhausted. Placed in cooldown for %.1fs.",
                    token_str[:8],
                    target.cooldown_until - now,
                )


def load_env_file(path: Path | str) -> dict[str, str]:
    """Parse KEY=VALUE pairs from a .env file and set them in os.environ if unset."""
    p = Path(path)
    loaded: dict[str, str] = {}
    if not p.is_file():
        return loaded
    try:
        content = p.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key:
                    loaded[key] = val
                    if key not in os.environ:
                        os.environ[key] = val
    except Exception:
        pass
    return loaded


def resolve_tokens(
    token: str | None = None,
    tokens: list[str] | str | None = None,
    env_file: Path | str | None = None,
) -> list[str]:
    """Resolve token pool from explicit params, GITHUB_TOKENS, GITHUB_TOKEN, .env files, or gh CLI."""
    if isinstance(tokens, list) and tokens:
        return [t.strip() for t in tokens if t.strip()]
    if isinstance(tokens, str) and tokens.strip():
        return [t.strip() for t in tokens.split(",") if t.strip()]
    if token and token.strip():
        return [token.strip()]

    if env_file:
        load_env_file(env_file)

    # If environment doesn't have tokens yet, search candidate .env files unless disabled
    disable_dotenv = os.getenv("DISABLE_DOTENV", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if not disable_dotenv and "GITHUB_TOKENS" not in os.environ and "GITHUB_TOKEN" not in os.environ:
        here = Path(__file__).resolve()
        candidates = [
            Path(".env"),
            Path("lab03/.env"),
            here.parents[1] / ".env",
            here.parents[2] / "lab01" / ".env",
            Path("lab01/.env"),
        ]
        for candidate in candidates:
            if candidate.is_file():
                load_env_file(candidate)
                if "GITHUB_TOKENS" in os.environ or "GITHUB_TOKEN" in os.environ:
                    break

    if env_tokens := os.getenv("GITHUB_TOKENS"):
        tok_list = [t.strip() for t in env_tokens.split(",") if t.strip()]
        if tok_list:
            return tok_list
    if env_token := os.getenv("GITHUB_TOKEN"):
        return [env_token.strip()]
    try:
        import shutil
        import subprocess

        if shutil.which("gh"):
            res = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0 and res.stdout.strip():
                return [res.stdout.strip()]
    except Exception:
        pass
    return []


class GitHubClient:
    """Async client for interacting with the GitHub REST API.

    Features:
    - Multi-token rotation with automatic cooldown on 403 Rate Limit.
    - Automatic pagination via RFC 5988 Link headers.
    - Native async I/O via httpx.AsyncClient.
    - Exponential backoff on 5xx server errors and network drops.
    - Persistent SQLite disk cache with WAL mode via aiosqlite.
    """

    def __init__(
        self,
        token: str | None = None,
        tokens: list[str] | str | None = None,
        base_url: str = "https://api.github.com",
        max_retries: int = 5,
        backoff_factor: float = 1.0,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
        sleep_fn: Callable[[float], Any] = asyncio.sleep,
        time_fn: Callable[[], float] = time.time,
        cache: HttpCache | None = None,
        cache_path: str | Path | None = "cache/http_cache.sqlite",
        concurrency: int = 15,
        env_file: str | Path | None = None,
        http2: bool = True,
        enforce_http2: bool | None = None,
        max_connections: int = 100,
        max_keepalive_connections: int = 50,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.sleep_fn = sleep_fn
        self.time_fn = time_fn

        # When client is injected (e.g. tests with MockTransport), do not strictly enforce HTTP/2 unless requested
        if enforce_http2 is None:
            self.enforce_http2 = client is None
        else:
            self.enforce_http2 = enforce_http2

        resolved = resolve_tokens(token=token, tokens=tokens, env_file=env_file)
        self.token_pool = TokenPool(resolved)

        disable_cache = os.getenv("DISABLE_CACHE", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        self._owns_cache = False
        if cache is not None:
            self._cache = cache
        elif cache_path is None or (
            disable_cache and str(cache_path) == "cache/http_cache.sqlite"
        ):
            self._cache = None
        else:
            self._cache = HttpCache(cache_path)
            self._owns_cache = True

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        self._semaphore = asyncio.Semaphore(concurrency)
        self._default_headers = headers
        if client is not None:
            self._client = client
        else:
            limits = httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
            )
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
                http2=http2,
                limits=limits,
            )

        self.last_remaining: int | None = None
        self.last_reset: float | None = None

    @property
    def cache(self) -> HttpCache | None:
        return self._cache

    def _resolve_url(self, url: str) -> str:
        if url.startswith(("http://", "https://")):
            return url
        endpoint = url.lstrip("/")
        return f"{self.base_url}/{endpoint}"

    async def _sleep(self, delay: float) -> None:
        res = self.sleep_fn(delay)
        if asyncio.iscoroutine(res):
            await res

    def _update_rate_limit_state(self, response: httpx.Response) -> None:
        """Record rate limit headers from the response."""
        remaining_hdr = response.headers.get("X-RateLimit-Remaining")
        reset_hdr = response.headers.get("X-RateLimit-Reset")

        if remaining_hdr is not None:
            try:
                self.last_remaining = int(remaining_hdr)
            except ValueError:
                pass

        if reset_hdr is not None:
            try:
                self.last_reset = float(reset_hdr)
            except ValueError:
                pass

    def _validate_response_protocol(self, response: httpx.Response) -> None:
        """Ensure HTTP/2 was negotiated in production against api.github.com."""
        if self.enforce_http2 and "api.github.com" in str(response.url):
            if response.http_version != "HTTP/2":
                raise RuntimeError(
                    f"HTTP/2 negotiation failed for {response.url}: received {response.http_version} instead of HTTP/2"
                )

    async def _check_proactive_rate_limit(self) -> None:
        """If known unauthenticated quota is 0 and reset is still in the future, wait proactively."""
        if (
            self.token_pool.count == 0
            and self.last_remaining is not None
            and self.last_remaining <= 0
            and self.last_reset is not None
            and self.last_reset > self.time_fn()
        ):
            wait_seconds = (self.last_reset - self.time_fn()) + 1.0
            await self._sleep(wait_seconds)
            self.last_remaining = None

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        force_refresh: bool = False,
    ) -> httpx.Response:
        """Perform an async GET request with token rotation, rate limit retry, and disk cache."""
        full_url = self._resolve_url(url)
        cache_key = HttpCache.compute_key(full_url, params=params)

        if self._cache is not None and not force_refresh:
            cached_response = await self._cache.get(cache_key)
            if cached_response is not None:
                logger.debug("Cache hit for %s", full_url)
                return cached_response

        attempt = 0

        while True:
            await self._check_proactive_rate_limit()

            current_token = await self.token_pool.get_next_token(
                self.time_fn, self.sleep_fn
            )
            req_headers = dict(self._default_headers)
            if current_token:
                req_headers["Authorization"] = f"Bearer {current_token}"

            try:
                async with self._semaphore:
                    response = await self._client.get(
                        full_url, params=params, headers=req_headers
                    )
                self._validate_response_protocol(response)
                self._update_rate_limit_state(response)
                if current_token:
                    await self.token_pool.update_state(
                        current_token, response, self.time_fn
                    )

                # Check rate limit hit
                is_rate_limited = (
                    response.status_code in (403, 429)
                    and (
                        self.last_remaining == 0
                        or "rate limit" in response.text.lower()
                    )
                ) or (
                    response.status_code in (403, 429)
                    and response.headers.get("X-RateLimit-Remaining") == "0"
                )

                if is_rate_limited:
                    if current_token:
                        logger.warning(
                            "Rate limit encountered on token %s for %s. Token placed in cooldown.",
                            current_token[:8],
                            full_url,
                        )
                        # Token is already in cooldown; next iteration will pick next token or wait
                        continue
                    else:
                        now = self.time_fn()
                        if self.last_reset is not None and self.last_reset > now:
                            wait_seconds = (self.last_reset - now) + 1.0
                        else:
                            wait_seconds = 60.0
                        logger.warning(
                            "Rate limit hit on unauthenticated request. Waiting %.1fs until reset...",
                            wait_seconds,
                        )
                        await self._sleep(wait_seconds)
                        self.last_remaining = None
                if response.status_code == 401 and current_token:
                    logger.warning(
                        "Token %s returned 401 Unauthorized for %s. Retrying with next available token...",
                        current_token[:8],
                        full_url,
                    )
                    continue

                # 5xx server error retry with exponential backoff
                if 500 <= response.status_code < 600:
                    if attempt < self.max_retries:
                        delay = self.backoff_factor * (2**attempt)
                        logger.warning(
                            "Server error %d on %s. Retrying in %.1fs (attempt %d/%d)...",
                            response.status_code,
                            full_url,
                            delay,
                            attempt + 1,
                            self.max_retries,
                        )
                        await self._sleep(delay)
                        attempt += 1
                        continue
                    response.raise_for_status()

                response.raise_for_status()

                # Cache successful 2xx responses
                if self._cache is not None:
                    await self._cache.set(cache_key, full_url, response)

                return response

            except httpx.RequestError as exc:
                if attempt < self.max_retries:
                    delay = self.backoff_factor * (2**attempt)
                    logger.warning(
                        "Network error %s on %s. Retrying in %.1fs (attempt %d/%d)...",
                        exc,
                        full_url,
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    await self._sleep(delay)
                    attempt += 1
                    continue
                raise

    async def graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Perform an async GraphQL POST request with token rotation, rate limit retry, and disk cache."""
        full_url = f"{self.base_url}/graphql"
        clean_vars = variables or {}
        var_str = json.dumps(clean_vars, sort_keys=True)
        cache_key = HttpCache.compute_key(
            full_url, params={"query": query.strip(), "variables": var_str}
        )

        if self._cache is not None and not force_refresh:
            cached_response = await self._cache.get(cache_key)
            if cached_response is not None:
                logger.debug("Cache hit for GraphQL query")
                return cached_response.json()

        attempt = 0
        payload = {"query": query, "variables": clean_vars}

        while True:
            await self._check_proactive_rate_limit()

            current_token = await self.token_pool.get_next_token(
                self.time_fn, self.sleep_fn
            )
            req_headers = dict(self._default_headers)
            req_headers["Content-Type"] = "application/json"
            if current_token:
                req_headers["Authorization"] = f"Bearer {current_token}"

            try:
                async with self._semaphore:
                    response = await self._client.post(
                        full_url, json=payload, headers=req_headers
                    )
                self._validate_response_protocol(response)
                self._update_rate_limit_state(response)
                if current_token:
                    await self.token_pool.update_state(
                        current_token, response, self.time_fn
                    )

                # Check rate limit hit
                is_rate_limited = (
                    response.status_code in (403, 429)
                    and (
                        self.last_remaining == 0
                        or "rate limit" in response.text.lower()
                    )
                ) or (
                    response.status_code in (403, 429)
                    and response.headers.get("X-RateLimit-Remaining") == "0"
                )

                if is_rate_limited:
                    if current_token:
                        logger.warning(
                            "Rate limit encountered on token %s for GraphQL. Token placed in cooldown.",
                            current_token[:8],
                        )
                        continue
                    else:
                        now = self.time_fn()
                        if self.last_reset is not None and self.last_reset > now:
                            wait_seconds = (self.last_reset - now) + 1.0
                        else:
                            wait_seconds = 60.0
                        logger.warning(
                            "Rate limit hit on unauthenticated GraphQL request. Waiting %.1fs until reset...",
                            wait_seconds,
                        )
                        await self._sleep(wait_seconds)
                        self.last_remaining = None
                        continue

                if response.status_code == 401 and current_token:
                    logger.warning(
                        "Token %s returned 401 Unauthorized for GraphQL. Retrying with next available token...",
                        current_token[:8],
                    )
                    continue

                if 500 <= response.status_code < 600:
                    if attempt < self.max_retries:
                        delay = self.backoff_factor * (2**attempt)
                        logger.warning(
                            "Server error %d on GraphQL. Retrying in %.1fs (attempt %d/%d)...",
                            response.status_code,
                            delay,
                            attempt + 1,
                            self.max_retries,
                        )
                        await self._sleep(delay)
                        attempt += 1
                        continue
                    response.raise_for_status()

                response.raise_for_status()
                data = response.json()

                if "errors" in data and not data.get("data"):
                    errors = data["errors"]
                    is_gql_rate_limit = any(
                        "rate limit" in str(err.get("message", "")).lower()
                        for err in errors
                    )
                    if is_gql_rate_limit and current_token:
                        logger.warning(
                            "GraphQL body reported rate limit for token %s. Cooldown triggered.",
                            current_token[:8],
                        )
                        continue
                    raise GraphQLError(errors)

                if self._cache is not None:
                    await self._cache.set(cache_key, full_url, response)

                return data

            except httpx.RequestError as exc:
                if attempt < self.max_retries:
                    delay = self.backoff_factor * (2**attempt)
                    logger.warning(
                        "Network error %s on GraphQL. Retrying in %.1fs (attempt %d/%d)...",
                        exc,
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    await self._sleep(delay)
                    attempt += 1
                    continue
                raise

    async def get_paginated(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        force_refresh: bool = False,
    ) -> AsyncIterator[httpx.Response]:
        """Fetch all pages following RFC 5988 Link headers, yielding each Response asynchronously."""
        current_url: str | None = url
        current_params: dict[str, Any] | None = params

        while current_url:
            response = await self.get(
                current_url, params=current_params, force_refresh=force_refresh
            )
            yield response

            next_link = response.links.get("next")
            if next_link and "url" in next_link:
                current_url = next_link["url"]
                current_params = None
            else:
                current_url = None

    async def close(self) -> None:
        """Close HTTP client session and disk cache."""
        await self._client.aclose()
        if self._owns_cache and self._cache is not None:
            await self._cache.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


async def get(
    url: str,
    params: dict[str, Any] | None = None,
    force_refresh: bool = False,
    **kwargs: Any,
) -> httpx.Response:
    """Convenience function to perform a single GET request using a temporary GitHubClient."""
    async with GitHubClient(**kwargs) as client:
        return await client.get(url, params=params, force_refresh=force_refresh)


async def get_paginated(
    url: str,
    params: dict[str, Any] | None = None,
    force_refresh: bool = False,
    **kwargs: Any,
) -> AsyncIterator[httpx.Response]:
    """Convenience function to perform a paginated GET request using a temporary GitHubClient."""
    client = GitHubClient(**kwargs)
    try:
        async for item in client.get_paginated(
            url, params=params, force_refresh=force_refresh
        ):
            yield item
    finally:
        await client.close()


__all__ = [
    "GitHubClient",
    "GraphQLError",
    "TokenPool",
    "TokenState",
    "get",
    "get_paginated",
    "load_env_file",
    "resolve_tokens",
]
