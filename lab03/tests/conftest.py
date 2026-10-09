"""Pytest configuration for lab03 tests."""

import pytest


@pytest.fixture(autouse=True)
def _default_disable_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable default global cache and auto dotenv loading in tests to isolate test state.

    Tests that test caching can pass `cache=...` or `cache_path=tmp_path / '...'`.
    Tests that test tokens can explicitly set environment variables or pass token args.
    """
    monkeypatch.setenv("DISABLE_CACHE", "1")
    monkeypatch.setenv("DISABLE_DOTENV", "1")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKENS", raising=False)
