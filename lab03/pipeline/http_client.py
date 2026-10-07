"""GitHub REST API client with Link-header pagination, rate limit management, and exponential backoff."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Iterator
from typing import Any, Self

import httpx

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for interacting with the GitHub REST API.

    Features:
    - Automatic authorization with GITHUB_TOKEN or GITHUB_TOKENS.
    - Automatic pagination via RFC 5988 Link headers (`rel="next"`).
    - Rate limit pause & retry using `X-RateLimit-Remaining` and `X-RateLimit-Reset`.
    - Exponential backoff on 5xx server errors and network errors (1s, 2s, 4s, 8s, 16s...).
    """

    def __init__(
        self,
        token: str | None = None,
        base_url: str = "https://api.github.com",
        max_retries: int = 5,
        backoff_factor: float = 1.0,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.sleep_fn = sleep_fn
        self.time_fn = time_fn

        resolved_token = token or self._resolve_env_token()
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if resolved_token:
            headers["Authorization"] = f"Bearer {resolved_token}"

        self._default_headers = headers
        if client is not None:
            self._client = client
            self._client.headers.update(headers)
        else:
            self._client = httpx.Client(
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
            )

        self.last_remaining: int | None = None
        self.last_reset: float | None = None

    @staticmethod
    def _resolve_env_token() -> str | None:
        """Resolve token from GITHUB_TOKEN or GITHUB_TOKENS environment variables."""
        if token := os.getenv("GITHUB_TOKEN"):
            return token.strip()
        if tokens := os.getenv("GITHUB_TOKENS"):
            first = tokens.split(",")[0].strip()
            if first:
                return first
        return None

    def _resolve_url(self, url: str) -> str:
        """Resolve full URL if a relative path is provided."""
        if url.startswith(("http://", "https://")):
            return url
        endpoint = url.lstrip("/")
        return f"{self.base_url}/{endpoint}"

    def _wait_for_rate_limit(self, reset_ts: float | None) -> None:
        """Wait until rate limit resets with a safety buffer."""
        now = self.time_fn()
        if reset_ts is not None and reset_ts > now:
            wait_seconds = (reset_ts - now) + 1.0
        else:
            wait_seconds = 60.0  # fallback delay

        logger.warning(
            "Rate limit exhausted. Waiting %.1f seconds until reset.", wait_seconds
        )
        self.sleep_fn(wait_seconds)

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

    def _check_proactive_rate_limit(self) -> None:
        """If known quota is 0 and reset is still in the future, wait proactively."""
        if (
            self.last_remaining is not None
            and self.last_remaining <= 0
            and self.last_reset is not None
            and self.last_reset > self.time_fn()
        ):
            self._wait_for_rate_limit(self.last_reset)
            self.last_remaining = None

    def get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """Perform a GET request with rate limit handling and exponential backoff."""
        full_url = self._resolve_url(url)
        attempt = 0

        while True:
            self._check_proactive_rate_limit()

            try:
                response = self._client.get(full_url, params=params)
                self._update_rate_limit_state(response)

                # Check for rate limit hit (403/429 with remaining 0 or message)
                is_rate_limited = (
                    response.status_code in (403, 429) and self.last_remaining == 0
                ) or (
                    response.status_code == 403
                    and "rate limit" in response.text.lower()
                )

                if is_rate_limited:
                    self._wait_for_rate_limit(self.last_reset)
                    self.last_remaining = None
                    continue

                # Server error: 5xx retry with exponential backoff
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
                        self.sleep_fn(delay)
                        attempt += 1
                        continue
                    response.raise_for_status()

                # Raise for 4xx client errors (401, 404, etc.)
                response.raise_for_status()
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
                    self.sleep_fn(delay)
                    attempt += 1
                    continue
                raise

    def get_paginated(
        self, url: str, params: dict[str, Any] | None = None
    ) -> Iterator[httpx.Response]:
        """Fetch all pages following RFC 5988 Link headers, yielding each Response."""
        current_url: str | None = url
        current_params: dict[str, Any] | None = params

        while current_url:
            response = self.get(current_url, params=current_params)
            yield response

            # Check next link in Link header
            next_link = response.links.get("next")
            if next_link and "url" in next_link:
                current_url = next_link["url"]
                current_params = (
                    None  # URL in Link header already encodes query parameters
                )
            else:
                current_url = None

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def get(
    url: str, params: dict[str, Any] | None = None, **kwargs: Any
) -> httpx.Response:
    """Convenience function to perform a single GET request using a temporary GitHubClient."""
    with GitHubClient(**kwargs) as client:
        return client.get(url, params=params)


def get_paginated(
    url: str, params: dict[str, Any] | None = None, **kwargs: Any
) -> Iterator[httpx.Response]:
    """Convenience function to perform a paginated GET request using a temporary GitHubClient."""
    client = GitHubClient(**kwargs)
    try:
        yield from client.get_paginated(url, params=params)
    finally:
        client.close()
